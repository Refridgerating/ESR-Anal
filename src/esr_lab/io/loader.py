"""Convenience loader dispatching based on file extension."""

from __future__ import annotations

from pathlib import Path

from esr_lab.core.spectrum import ESRSpectrum

from esr_lab.io import bruker_csv


def load_any(path: str | Path) -> ESRSpectrum:
    """Load a spectrum from ``path``.

    Supported file types are ``.csv``, ``.tsv`` and ``.txt`` which are all
    parsed using :func:`esr_lab.io.bruker_csv.load_bruker_csv`.
    """

    path = Path(path)
    if path.suffix.lower() in {".csv", ".tsv", ".txt"}:
        return bruker_csv.load_bruker_csv(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


__all__ = ["load_any"]

