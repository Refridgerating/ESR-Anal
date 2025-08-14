"""Bruker CSV loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from esr_lab.core.spectrum import ESRMeta, ESRSpectrum


def load_bruker_csv(path: str | Path) -> ESRSpectrum:
    """Load a Bruker-format CSV file into an ``ESRSpectrum``."""
    path = Path(path)
    header: Dict[str, Any] = {}
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
    from io import StringIO

    df = pd.read_csv(StringIO("".join(data_lines)))
    meta_kwargs: Dict[str, Any] = {}
    if "Frequency" in header:
        try:
            meta_kwargs["frequency_Hz"] = float(header["Frequency"])
        except ValueError:
            pass
    if "ModAmp" in header:
        try:
            meta_kwargs["mod_amp_T"] = float(header["ModAmp"])
        except ValueError:
            pass
    if "MWPower" in header:
        try:
            meta_kwargs["mw_power_W"] = float(header["MWPower"])
        except ValueError:
            pass
    meta = ESRMeta(**meta_kwargs)
    field_B = df.iloc[:, 0].to_numpy(dtype=float)
    signal_dAbs = df.iloc[:, 1].to_numpy(dtype=float)
    return ESRSpectrum(field_B=field_B, signal_dAbs=signal_dAbs, meta=meta)
