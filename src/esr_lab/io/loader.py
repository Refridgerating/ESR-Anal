"""Convenience loader dispatching based on file extension."""

from __future__ import annotations

from pathlib import Path

from esr_lab.core.spectrum import ESRSpectrum

from . import bruker_csv


def load_any(path: str | Path) -> ESRSpectrum:
    """Load a spectrum from ``path``.

    Currently only ``.csv`` files are understood and are parsed using
    :func:`bruker_csv.load_bruker_csv`.  The function is intentionally simple
    to keep the loader pluggable for future importers.
    """

    path = Path(path)
    if path.suffix.lower() == ".csv":
        return bruker_csv.load_bruker_csv(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


__all__ = ["load_any"]

