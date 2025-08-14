"""Spectrum data model for ESR-Lab."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
from pydantic import BaseModel, Field


class ESRMeta(BaseModel):
    """Metadata for an ESR spectrum."""

    frequency_Hz: Optional[float] = None
    mod_amp_T: Optional[float] = None
    mw_power_W: Optional[float] = None
    temperature_K: Optional[float] = None
    phase_rad: Optional[float] = None
    instrument: Optional[str] = None
    operator: Optional[str] = None
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None


class ESRSpectrum(BaseModel):
    """Core spectrum object holding data and metadata."""

    field_B: np.ndarray
    signal_dAbs: np.ndarray
    absorption: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    meta: ESRMeta = Field(default_factory=ESRMeta)

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_bruker_csv(cls, path: str | "Path") -> "ESRSpectrum":
        """Create a spectrum from a Bruker CSV file."""
        from pathlib import Path

        from esr_lab.io.bruker_csv import load_bruker_csv

        return load_bruker_csv(Path(path))

    def baseline(self, method: str = "poly", order: int = 2, knots: Optional[np.ndarray] = None) -> "ESRSpectrum":
        """Placeholder for baseline correction."""
        return self

    def smooth(self, method: str = "savgol", window: int = 5, polyorder: int = 2) -> "ESRSpectrum":
        """Placeholder for smoothing."""
        return self

    def phase_correct(self, delta_rad: float) -> "ESRSpectrum":
        """Placeholder for phase correction."""
        return self

    def to_absorption(self) -> "ESRSpectrum":
        """Placeholder for converting to absorption spectrum."""
        return self

    def to_area(self) -> float:
        """Return the area under the spectrum (placeholder)."""
        return float(np.trapz(self.signal_dAbs, self.field_B))

    def subset(self, Bmin: float, Bmax: float) -> "ESRSpectrum":
        """Return a subset of the spectrum between ``Bmin`` and ``Bmax``."""
        mask = (self.field_B >= Bmin) & (self.field_B <= Bmax)
        return ESRSpectrum(
            field_B=self.field_B[mask],
            signal_dAbs=self.signal_dAbs[mask],
            meta=self.meta,
        )

    def export_results(self) -> Dict[str, Any]:
        """Export results as a dictionary (placeholder)."""
        return self.meta.model_dump() if hasattr(self.meta, "model_dump") else self.meta.dict()
