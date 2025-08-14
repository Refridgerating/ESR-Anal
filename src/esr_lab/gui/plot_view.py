"""Simple Matplotlib based plot view for ESR spectra."""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QWidget
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from esr_lab.core.spectrum import ESRSpectrum


class PlotView(FigureCanvas):
    """Matplotlib canvas for plotting ESR spectra."""

    def __init__(self, parent: QWidget | None = None) -> None:
        fig = Figure()
        super().__init__(fig)
        self.setParent(parent)
        self.ax = fig.add_subplot(111)

    def plot_derivative(self, sp: ESRSpectrum, clear: bool = False) -> None:
        """Plot derivative spectrum."""

        if clear:
            self.ax.cla()
        self.ax.plot(sp.field_B, sp.signal_dAbs, label="Derivative")
        self.ax.set_xlabel("Field (T)")
        self.ax.set_ylabel("d(Abs)/dB")
        self.ax.legend()
        self.draw()

    def plot_absorption(self, sp: ESRSpectrum) -> None:
        """Plot absorption spectrum."""

        self.ax.cla()
        if sp.absorption is not None:
            self.ax.plot(sp.field_B, sp.absorption, label="Absorption")
        self.ax.set_xlabel("Field (T)")
        self.ax.set_ylabel("Absorption (arb.)")
        self.ax.legend()
        self.draw()

