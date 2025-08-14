"""PyQtGraph based plot widget for ESR spectra."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
import pyqtgraph as pg

from esr_lab.core.spectrum import ESRSpectrum


class PlotView(pg.PlotWidget):
    """Fast plotting canvas for ESR spectra using :mod:`pyqtgraph`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        pg.setConfigOptions(antialias=True)
        self.plotItem.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel("bottom", "Field (T)")
        self.setLabel("left", "d(Abs)/dB (arb.)")
        self._legend: pg.LegendItem | None = None

    # ------------------------------------------------------------------
    def set_background(self, clear: bool = True) -> None:
        """Clear the plot and restore axis labels and grid."""

        if clear:
            self.clear()
        self.setLabel("bottom", "Field (T)")
        self.setLabel("left", "d(Abs)/dB (arb.)")
        self.plotItem.showGrid(x=True, y=True, alpha=0.3)

    # ------------------------------------------------------------------
    def plot_derivative(
        self, sp: ESRSpectrum, name: str | None = None, clear: bool = False
    ) -> None:
        """Plot a derivative spectrum."""

        if clear:
            self.clear()
        self.setLabel("left", "d(Abs)/dB (arb.)")
        self.plot(sp.field_B, sp.signal_dAbs, pen=None, name=name)

    # ------------------------------------------------------------------
    def plot_absorption(
        self, sp: ESRSpectrum, name: str | None = None, clear: bool = False
    ) -> None:
        """Plot an absorption spectrum, computing it if necessary."""

        if sp.absorption is None:
            sp.to_absorption()
        if sp.absorption is None:
            return
        if clear:
            self.clear()
        self.setLabel("left", "Absorption (arb.)")
        pen = pg.mkPen(style=Qt.DashLine)
        self.plot(sp.field_B, sp.absorption, pen=pen, name=name)

    # ------------------------------------------------------------------
    def enable_legend(self, show: bool = True) -> None:
        """Show or hide the legend."""

        if show:
            if self._legend is None:
                self._legend = self.addLegend()
        else:
            if self._legend is not None:
                self._legend.scene().removeItem(self._legend)
                self._legend = None

    # ------------------------------------------------------------------
    def auto_range(self) -> None:
        """Auto scale the view to show all data."""

        self.plotItem.enableAutoRange("xy", True)


__all__ = ["PlotView"]

