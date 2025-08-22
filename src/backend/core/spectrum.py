"""Spectrum data model for ESR-Lab."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, PrivateAttr

from . import processing


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

        from ..io.bruker_csv import load_bruker_csv

        return load_bruker_csv(Path(path))

    _baseline: Optional[np.ndarray] = PrivateAttr(default=None)

    def baseline(
        self,
        method: str = "poly",
        order: int = 2,
        knots: Optional[np.ndarray] = None,
    ) -> "ESRSpectrum":
        """Baseline correction using polynomial or spline methods."""

        if method == "poly":
            baseline, y_corr = processing.poly_baseline(
                self.field_B, self.signal_dAbs, order=order, mask=self.mask
            )
        elif method == "spline":
            baseline, y_corr = processing.spline_baseline(
                self.field_B, self.signal_dAbs, knots=knots
            )
        else:
            raise ValueError(f"Unknown baseline method: {method}")
        self._baseline = baseline
        self.signal_dAbs = y_corr
        return self

    def smooth(
        self, method: str = "savgol", window: int = 5, polyorder: int = 2
    ) -> "ESRSpectrum":
        """Smooth the derivative signal in-place."""

        if method == "savgol":
            self.signal_dAbs = processing.savgol_smooth(
                self.signal_dAbs, window, polyorder
            )
        else:
            raise ValueError(f"Unknown smoothing method: {method}")
        return self

    def phase_correct(self, delta_rad: float) -> "ESRSpectrum":
        """Apply phase correction to derivative signal."""

        self.signal_dAbs = processing.phase_correct(self.signal_dAbs, delta_rad)
        base_phase = self.meta.phase_rad or 0.0
        self.meta.phase_rad = base_phase + float(delta_rad)
        return self

    def phase_auto(self) -> "ESRSpectrum":
        """Automatically determine and apply optimal phase."""

        delta = processing.phase_auto(self.signal_dAbs)
        return self.phase_correct(delta)

    def to_absorption(self) -> "ESRSpectrum":
        """Integrate derivative signal to obtain absorption spectrum."""

        self.absorption = processing.integrate_absorption(
            self.field_B, self.signal_dAbs
        )
        return self

    _last_area_roi: Optional[Tuple[float, float]] = PrivateAttr(default=None)

    def to_area(self, roi: Tuple[float, float] | None = None) -> float:
        """Return the area under the absorption spectrum."""

        if self.absorption is None:
            self.to_absorption()
        area = processing.integrate_area(self.field_B, self.absorption, roi)
        self._last_area_roi = roi
        return area

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
