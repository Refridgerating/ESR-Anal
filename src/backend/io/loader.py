"""Convenience loader dispatching based on file extension."""

from __future__ import annotations

from pathlib import Path

from ..core.spectrum import ESRSpectrum

from . import bruker_csv
from ..utils.logging import get_logger

log = get_logger(__name__)


def load_any(path: str | Path) -> ESRSpectrum:
    """Load a spectrum from ``path``.

    Supported file types are ``.csv``, ``.tsv`` and ``.txt`` which are all
    parsed using :func:`backend.io.bruker_csv.load_bruker_csv`.
    """

    path = Path(path)
    suffix = path.suffix.lower()
    log.debug("Loading %s (suffix %s)", path, suffix)
    if suffix in {".csv", ".tsv", ".txt"}:
        log.debug("Dispatching to bruker_csv loader")
        return bruker_csv.load_bruker_csv(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


__all__ = ["load_any"]

