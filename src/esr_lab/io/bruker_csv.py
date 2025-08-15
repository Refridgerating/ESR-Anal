"""Advanced Bruker CSV loader.

This module contains a more feature complete importer for Bruker ESR5000
CSV files.  The format used in the wild is quite flexible – files may either
contain multiple columns with a standard delimiter *or* be saved as a single
column where each row packs several values separated by commas, semicolons or
whitespace.  The loader attempts to automatically handle both cases and will
request user interaction via :class:`AxisSelectionNeeded` if it cannot
unambiguously determine which columns represent the magnetic field and the
signal.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from esr_lab.core.spectrum import ESRMeta, ESRSpectrum
from esr_lab.core import units
from esr_lab.utils.logging import get_logger

log = get_logger(__name__)

__all__ = [
    "AxisSelectionNeeded",
    "parse_metadata_from_header",
    "detect_delimiter_and_header",
    "read_dataframe",
    "resolve_axes",
    "normalize_units_for_axes",
    "load_bruker_csv",
]


# ---------------------------------------------------------------------------
# Exceptions


class AxisSelectionNeeded(Exception):
    """Raised when the loader cannot determine X/Y columns automatically."""

    def __init__(self, candidates: Iterable[str]) -> None:
        self.candidates = list(candidates)
        super().__init__(
            "Ambiguous axis columns; user selection required (candidates: "
            + ", ".join(self.candidates)
            + ")"
        )


# ---------------------------------------------------------------------------
# Metadata parsing


def _to_number(text: str) -> float:
    """Parse ``text`` into a float handling decimal commas."""

    return float(text.strip().replace(",", "."))


def parse_metadata_from_header(lines: List[str]) -> dict:
    """Extract metadata from header ``lines``.

    Parameters
    ----------
    lines:
        List of strings preceding the data section of the file.

    Returns
    -------
    dict
        Mapping suitable for initialising :class:`ESRMeta`.
    """

    meta: dict = {}

    freq_re = re.compile(r"(?i)frequency[^0-9]*([\d.,]+)\s*(GHz|MHz|Hz)?")
    mod_re = re.compile(r"(?i)modulat(?:ion)?[^0-9]*([\d.,]+)\s*(mT|G|T)?")
    pow_re = re.compile(r"(?i)(?:microwave|mw)\s*power[^0-9]*([\d.,]+)\s*(mW|W)?")
    temp_re = re.compile(r"(?i)temp(?:erature)?[^0-9]*([\d.,]+)\s*(K|C|°C)?")
    phase_re = re.compile(r"(?i)phase[^0-9\-+]*([\-+]?\d+(?:\.\d+)?)\s*(deg|rad)?")

    for line in lines:
        line = line.strip().lstrip("#").strip()

        if (m := freq_re.search(line)):
            val = _to_number(m.group(1))
            unit = (m.group(2) or "Hz").lower()
            factor = {"ghz": 1e9, "mhz": 1e6, "hz": 1.0}[unit]
            meta["frequency_Hz"] = val * factor
        if (m := mod_re.search(line)):
            val = _to_number(m.group(1))
            unit = (m.group(2) or "T").lower()
            factor = {"t": 1.0, "mt": 1e-3, "g": 1e-4}[unit]
            meta["mod_amp_T"] = val * factor
        if (m := pow_re.search(line)):
            val = _to_number(m.group(1))
            unit = (m.group(2) or "W").lower()
            factor = {"w": 1.0, "mw": 1e-3}[unit]
            meta["mw_power_W"] = val * factor
        if (m := temp_re.search(line)):
            val = _to_number(m.group(1))
            unit = (m.group(2) or "K").lower()
            if unit.startswith("c") or "°" in unit:
                val = val + 273.15
            meta["temperature_K"] = val
        if (m := phase_re.search(line)):
            val = _to_number(m.group(1))
            unit = (m.group(2) or "rad").lower()
            if unit.startswith("deg"):
                val = np.deg2rad(val)
            meta["phase_rad"] = val

    return meta


# ---------------------------------------------------------------------------
# Delimiter and header detection


def _is_mostly_numeric(tokens: List[str]) -> bool:
    numeric = 0
    total = 0
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        total += 1
        try:
            float(tok.replace(",", "."))
            numeric += 1
        except ValueError:
            pass
    return total > 0 and numeric / total >= 0.8


def detect_delimiter_and_header(path: str | Path) -> Tuple[str | None, int, List[str]]:
    """Detect delimiter and header line for ``path``.

    Returns ``(delimiter, header_row_index, raw_lines)``.  ``delimiter`` may be
    ``None`` if detection failed.
    """

    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    log.debug("Detecting delimiter for %s", path)

    delimiter: str | None
    sample = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", " "])
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = None

    header_idx = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if delimiter:
            tokens = [t for t in re.split(re.escape(delimiter), stripped)]
        else:
            tokens = re.split(r"[\s,;]+", stripped)
        if _is_mostly_numeric(tokens):
            header_idx = max(0, idx - 1)
            break

    log.debug(
        "Detected delimiter=%r header_row=%d for %s", delimiter, header_idx, path
    )
    return delimiter, header_idx, lines


# ---------------------------------------------------------------------------
# DataFrame creation


def read_dataframe(path: str | Path) -> pd.DataFrame:
    """Read the numeric data from ``path`` into a :class:`DataFrame`."""

    delimiter, header_idx, lines = detect_delimiter_and_header(path)
    log.debug("Reading %s with delimiter=%r header_idx=%d", path, delimiter, header_idx)

    try:
        if delimiter:
            df = pd.read_csv(path, sep=delimiter, header=header_idx, engine="python")
        else:
            df = pd.read_csv(path, header=header_idx, engine="python")
    except Exception as e:
        log.exception("Failed to read CSV %s: %s", path, e)
        df = pd.read_csv(path, header=None, engine="python")

    # Handle packed single-column case
    if df.shape[1] == 1:
        col = df.columns[0]
        data = df.iloc[:, 0].astype(str).str.strip().str.split(r"[\s,;]+", expand=True)
        header_line = lines[header_idx] if header_idx < len(lines) else col
        header_tokens = re.split(r"[\s,;]+", header_line.strip())
        if len(header_tokens) == 1 and "," in header_tokens[0]:
            header_tokens = [h.strip() for h in header_tokens[0].split(",")]
        data.columns = header_tokens[: data.shape[1]]
        log.debug("Single-column CSV detected; first row split: %s", data.iloc[0].tolist())
        log.debug("Final column names: %s", list(data.columns))
        df = data

    # Clean column names and convert to numeric
    df = df.rename(columns=lambda c: str(c).strip())
    df = df.drop(columns=[c for c in df.columns if not str(c).strip()])
    for c in df.columns:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")
    df = df.dropna(how="all")

    return df


# ---------------------------------------------------------------------------
# Axis selection


_FIELD_RE = re.compile(r"(?i)^(b\s*field|field|mag(?:netic)?\s*field|B)$")
_SIGNAL_RE = re.compile(
    r"(?i)^(signal|MW_Absorption|dabs|deriv|first\s*derivative|y)(?:\b|[^a-z])"
)
_UNIT_ONLY_RE = re.compile(r"^\s*[\[\(]?\s*(mT|G|T)\s*[\]\)]?\s*$", re.IGNORECASE)


def _is_numeric_col(s: pd.Series) -> bool:
    return pd.to_numeric(s, errors="coerce").notna().mean() >= 0.9


def resolve_axes(df: pd.DataFrame) -> tuple[str, str, dict]:
    """Return ``(x_col, y_col, hints)`` resolving axes without raising."""

    hints: dict = {"ignored": []}
    numeric_cols = [c for c in df.columns if _is_numeric_col(df[c])]
    log.info("Numeric columns: %s", numeric_cols)

    # Remove unit-only columns and collect unit hints
    for col in list(numeric_cols):
        m = _UNIT_ONLY_RE.match(str(col))
        if m:
            numeric_cols.remove(col)
            hints["ignored"].append(col)
            if "x_unit_hint" not in hints:
                hints["x_unit_hint"] = m.group(1)
    if hints["ignored"]:
        log.info("Ignored unit-only columns: %s", hints["ignored"])

    def _clean(name: str) -> str:
        return re.sub(r"[\[\(].*", "", name).strip()

    x_candidates = [c for c in numeric_cols if _FIELD_RE.match(_clean(str(c)))]
    y_candidates = [c for c in numeric_cols if _SIGNAL_RE.match(_clean(str(c)))]

    x_col: str | None = None
    y_col: str | None = None

    if len(x_candidates) == 1:
        x_col = x_candidates[0]
    if len(y_candidates) == 1:
        y_col = y_candidates[0]

    if x_col and y_col:
        pass
    elif x_col and len(numeric_cols) >= 2:
        y_col = next(c for c in numeric_cols if c != x_col)
        if not y_candidates:
            log.warning("No obvious signal column; using %s as Y", y_col)
    elif y_col and len(numeric_cols) >= 2:
        x_col = next(c for c in numeric_cols if c != y_col)
    elif len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[:2]
        if not _FIELD_RE.match(_clean(str(x_col))) and _FIELD_RE.match(
            _clean(str(y_col))
        ):
            x_col, y_col = y_col, x_col
        hints["reason"] = "defaulted to first two numeric columns"
    elif len(numeric_cols) == 1:
        x_col = y_col = numeric_cols[0]
        hints["reason"] = "only one numeric column"
    else:
        x_col = y_col = ""
        hints["reason"] = "no numeric columns"

    log.info("Resolved axes x=%s y=%s", x_col, y_col)
    if "x_unit_hint" in hints:
        log.info("Unit hint for X: %s", hints["x_unit_hint"])

    return x_col, y_col, hints


# Backwards compatibility helper
def select_axes_from_columns(df: pd.DataFrame) -> Tuple[str, str]:
    x, y, _ = resolve_axes(df)
    return x, y


# ---------------------------------------------------------------------------
# Unit normalisation


def normalize_units_for_axes(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    hints: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Return arrays for field and signal in SI units."""

    hints = hints or {}
    unit_source = "header"
    header = str(x_col)
    unit = None
    for tok in ("mT", "G", "T"):
        if re.search(rf"(?i)\b{tok}\b", header):
            unit = tok
            break
    if unit is None:
        unit = hints.get("x_unit_hint")
        unit_source = "hint" if unit else "assumed"

    factor = 1.0
    if unit == "mT":
        factor = 1e-3
    elif unit == "G":
        factor = 1e-4
    field = df[x_col].to_numpy(dtype=float) * factor
    signal = df[y_col].to_numpy(dtype=float)

    mask = np.isfinite(field) & np.isfinite(signal)
    dropped = field.size - mask.sum()
    if dropped:
        log.info("Dropped %d rows during unit normalisation", dropped)
    log.info("Field unit %s from %s (factor=%s)", unit or "T", unit_source, factor)
    return field[mask], signal[mask], unit_source


# ---------------------------------------------------------------------------
# High level loader


def load_bruker_csv(
    path: str | Path,
    x_override: str | None = None,
    y_override: str | None = None,
) -> ESRSpectrum:
    """Load ``path`` into an :class:`ESRSpectrum`.

    This function glues the helper steps together and may raise
    :class:`AxisSelectionNeeded` if axis detection is ambiguous.  If
    ``x_override`` and ``y_override`` are provided, they are used directly
    instead of attempting automatic axis detection.
    """

    log.debug("Loading Bruker CSV %s", path)
    delimiter, header_idx, lines = detect_delimiter_and_header(path)
    meta = parse_metadata_from_header(lines[:header_idx])

    df = read_dataframe(path)

    if x_override is not None and y_override is not None:
        x_col, y_col, hints = x_override, y_override, {}
    else:
        x_col, y_col, hints = resolve_axes(df)

    if not x_col or not y_col or x_col == y_col:
        raise ValueError("No valid Y column found")

    field, signal, unit_source = normalize_units_for_axes(df, x_col, y_col, hints)
    if field.size < 2:
        log.error("Not enough data points in %s", path)
        raise ValueError("Not enough data points")
    log.info(
        "Using columns x=%s y=%s (unit source=%s); %d points",
        x_col,
        y_col,
        unit_source,
        field.size,
    )

    return ESRSpectrum(field_B=field, signal_dAbs=signal, meta=ESRMeta(**meta))


