"""Bruker CSV loader.

This module provides a small parser for the simple Bruker ESR5000 style
CSV files used throughout the tests. It performs basic unit conversions so
the resulting :class:`ESRSpectrum` is normalised to SI units.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from io import StringIO

import pandas as pd

from esr_lab.core.spectrum import ESRMeta, ESRSpectrum

# ---------------------------------------------------------------------------
# Helpers

_FREQ_UNITS = {"hz": 1.0, "ghz": 1e9}
_FIELD_UNITS = {"t": 1.0, "mt": 1e-3, "g": 1e-4}
_POWER_UNITS = {"w": 1.0, "mw": 1e-3}


def _parse_header_value(value: str, units: Dict[str, float]) -> float:
    """Return the numeric value applying a unit conversion if present."""

    parts = value.strip().split()
    if len(parts) == 2:
        number, unit = parts
        factor = units.get(unit.lower())
        if factor is None:
            raise ValueError(f"Unknown unit '{unit}' in header")
        return float(number) * factor
    return float(parts[0])


# ---------------------------------------------------------------------------
# Public API

def load_bruker_csv(path: str | Path) -> ESRSpectrum:
    """Load a Bruker-format CSV file into an :class:`ESRSpectrum`.

    Parameters
    ----------
    path:
        Path to the CSV file.

    Returns
    -------
    ESRSpectrum
        Parsed spectrum with metadata in SI units.

    Raises
    ------
    ValueError
        If the file cannot be parsed or lacks the expected columns.
    """

    path = Path(path)
    header: Dict[str, str] = {}
    data_lines: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                parts = line[1:].strip().split(":", 1)
                if len(parts) == 2:
                    key, value = parts
                    header[key.strip()] = value.strip()
            else:
                data_lines.append(line)

    if not data_lines:
        raise ValueError("No data section found in CSV")

    try:
        df = pd.read_csv(StringIO("".join(data_lines)))
    except Exception as exc:  # pragma: no cover - unlikely
        raise ValueError(f"Failed to parse CSV data: {exc}") from exc

    if df.shape[1] < 2:
        raise ValueError("CSV must contain at least two columns")

    field_col = df.columns[0]
    field_factor = 1.0
    col_lower = field_col.lower()
    if "mt" in col_lower:
        field_factor = _FIELD_UNITS["mt"]
    elif "g" in col_lower:
        field_factor = _FIELD_UNITS["g"]

    field_B = df.iloc[:, 0].to_numpy(dtype=float) * field_factor
    signal_dabs = df.iloc[:, 1].to_numpy(dtype=float)

    meta_kwargs = {}
    if "Frequency" in header:
        meta_kwargs["frequency_Hz"] = _parse_header_value(
            header["Frequency"], _FREQ_UNITS
        )
    if "ModAmp" in header:
        meta_kwargs["mod_amp_T"] = _parse_header_value(
            header["ModAmp"], _FIELD_UNITS
        )
    if "MWPower" in header:
        meta_kwargs["mw_power_W"] = _parse_header_value(
            header["MWPower"], _POWER_UNITS
        )

    meta = ESRMeta(**meta_kwargs)

    return ESRSpectrum(field_B=field_B, signal_dAbs=signal_dabs, meta=meta)


__all__ = ["load_bruker_csv"]

