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


_NUM_RE = re.compile(r"^[\s\+\-]?(?:\d+\.?\d*|\.\d+)(?:[eE][\+\-]?\d+)?\s*$")


def _strip_units(label: str) -> str:
    """Return ``label`` without a trailing unit specifier like ``" [mT]"``."""

    return re.sub(r"\s*\[[^\]]*\]\s*$", "", str(label).strip())


def _coerce_numeric_series(s: pd.Series) -> pd.Series:
    """Return a numeric series by cleaning common artifacts (thousands sep, stray units)."""
    if s.dtype.kind in "if":
        return s
    cleaned = (
        s.astype(str)
        .str.strip()
        .str.replace("\u00A0", " ", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(r"[^\d\.\+\-eE]", "", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _is_mostly_numeric(s: pd.Series, thresh: float = 0.9) -> bool:
    v = _coerce_numeric_series(s)
    return v.notna().mean() >= thresh


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


def _tokens_mostly_numeric(tokens: List[str]) -> bool:
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
        if _tokens_mostly_numeric(tokens):
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
        data = (
            df.iloc[:, 0]
            .astype(str)
            .str.strip()
            .str.split(";", expand=True)
            .apply(lambda s: s.str.strip())
        )
        header_line = lines[header_idx] if header_idx < len(lines) else col
        header_tokens = [h.strip() for h in header_line.split(";")]
        if len(header_tokens) == 1 and "," in header_tokens[0]:
            header_tokens = [h.strip() for h in header_tokens[0].split(",")]
        data.columns = header_tokens[: data.shape[1]]
        log.debug(
            "Single-column CSV detected; first row split by semicolon: %s",
            data.iloc[0].tolist(),
        )
        log.debug(
            "Column names after semicolon split: %s", list(data.columns)
        )
        df = data

    # Clean column names and convert to numeric
    df = df.rename(columns=lambda c: str(c).strip())
    df = df.drop(columns=[c for c in df.columns if not str(c).strip()])
    for c in df.columns:
        df[c] = _coerce_numeric_series(df[c])
    df = df.dropna(how="all")

    return df


# ---------------------------------------------------------------------------
# Axis selection


FIELD_RX = re.compile(r"(?i)^(?:b\s*field|bfield|BField|field|mag(?:netic)?\s*field|B)$")
UNITS_ONLY_RX = re.compile(r"^\s*[\[\(]?\s*(mT|G|T)\s*[\]\)]?\s*$")
SIGNAL_RX = re.compile(
    r"(?i)^(?:signal|dabs|deriv|first\s*derivative|mw[_\s-]*absorption|MW_Absorption|absorption|intensity|y)(?:\b|[^a-z])"
)


def resolve_axes(df: pd.DataFrame) -> tuple[str, str, dict]:
    cols = list(df.columns)
    numeric_cols = [c for c in cols if _is_mostly_numeric(df[c])]
    log.info("Numeric columns: %s", numeric_cols)
    units_only = [c for c in numeric_cols if UNITS_ONLY_RX.match(str(c).strip() or "")]
    data_numeric = [c for c in numeric_cols if c not in units_only]

    hints: dict = {}
    if units_only:
        hints["x_unit_hint"] = UNITS_ONLY_RX.match(units_only[0]).group(1)
        log.info("Ignoring unit-only columns: %s", units_only)

    # Prefer explicit field/signal names
    field_candidates = [
        c for c in data_numeric if FIELD_RX.search(_strip_units(str(c)))
    ]
    signal_candidates = [
        c for c in data_numeric if SIGNAL_RX.search(_strip_units(str(c)))
    ]

    # Case A: clear names
    if field_candidates and signal_candidates:
        x_col, y_col = field_candidates[0], signal_candidates[0]
    # Case B: one field-like + some other numeric
    elif field_candidates and data_numeric:
        x_col = field_candidates[0]
        y_col = next((cand for cand in signal_candidates if cand != x_col), None)
        if y_col is None:
            y_col = next((cand for cand in data_numeric if cand != x_col), None)
        if y_col is None:
            raise ValueError("No valid Y column found")
    # Case C: exactly two data columns
    elif len(data_numeric) == 2:
        a, b = data_numeric
        if FIELD_RX.search(_strip_units(str(a))) and not FIELD_RX.search(
            _strip_units(str(b))
        ):
            x_col, y_col = a, b
        elif FIELD_RX.search(_strip_units(str(b))) and not FIELD_RX.search(
            _strip_units(str(a))
        ):
            x_col, y_col = b, a
        elif SIGNAL_RX.search(_strip_units(str(b))):
            x_col, y_col = a, b
        elif SIGNAL_RX.search(_strip_units(str(a))):
            x_col, y_col = b, a
        else:
            x_col, y_col = a, b
    # Case D: 2+ numerics, pick best effort
    elif len(data_numeric) >= 2:
        x_col = field_candidates[0] if field_candidates else data_numeric[0]
        y_col = None
        for cand in signal_candidates:
            if cand != x_col:
                y_col = cand
                break
        if y_col is None:
            for cand in data_numeric:
                if cand != x_col:
                    y_col = cand
                    break
    else:
        raise ValueError("No valid Y column found")

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
    df,
    x_col,
    y_col,
    header_lines,
    meta,
    hints,
) -> tuple[np.ndarray, np.ndarray]:
    x_name = str(x_col)
    unit = None
    m = re.search(r"(?i)(?:\(|\[|{)\s*(mT|G|T)\s*(?:\)|\]|})", x_name)
    if m:
        unit = m.group(1)
    if unit is None:
        unit = hints.get("x_unit_hint") or "T"
        if "x_unit_hint" in hints:
            log.info("Unit hint applied: %s", unit)
    x = _coerce_numeric_series(df[x_col]).to_numpy(dtype=float)
    if unit.lower() == "mt":
        field_B = x * 1e-3
    elif unit.upper() == "G":
        field_B = x * 1e-4
    else:
        field_B = x
    y = _coerce_numeric_series(df[y_col]).to_numpy(dtype=float)
    return field_B, y


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
    header_lines = lines[:header_idx]
    meta = parse_metadata_from_header(header_lines)

    df = read_dataframe(path)

    if x_override is not None and y_override is not None:
        x_col, y_col, hints = x_override, y_override, {}
    else:
        x_col, y_col, hints = resolve_axes(df)

    field_B, y_deriv = normalize_units_for_axes(
        df, x_col, y_col, header_lines, meta, hints
    )

    mask = np.isfinite(field_B) & np.isfinite(y_deriv)
    valid = mask.sum()
    if valid < 10:
        log.error("Not enough valid points in %s: %d", path, valid)
        raise ValueError("Not enough valid points after cleaning")
    field_B, y_deriv = field_B[mask], y_deriv[mask]
    log.info("Points after cleaning: %d", valid)

    return ESRSpectrum(field_B=field_B, signal_dAbs=y_deriv, meta=ESRMeta(**meta))


