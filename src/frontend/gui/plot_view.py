"""PyQtGraph based plot widget for ESR spectra."""

from __future__ import annotations

import numpy as np
try:  # pragma: no cover - optional Qt dependency
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget
    import pyqtgraph as pg
except Exception as exc:  # noqa: BLE001 - handle missing Qt
    Qt = None  # type: ignore[assignment]
    QWidget = object  # type: ignore[assignment]
    pg = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from backend.core.spectrum import ESRSpectrum
from backend.utils.logging import get_logger


if pg is None:  # pragma: no cover - raise on usage when Qt/pyqtgraph are missing

    class PlotView:  # type: ignore[misc]
        """Stub that raises if plotting dependencies are missing."""

        def __init__(self, *_, **__) -> None:  # noqa: D401 - always raises
            msg = (
                "Plotting requires the 'PySide6' and 'pyqtgraph' packages. "
                "Install them to enable plotting."
            )
            raise RuntimeError(msg) from _IMPORT_ERROR

else:

    class PlotView(pg.PlotWidget):
        """Fast plotting canvas for ESR spectra using :mod:`pyqtgraph`."""

        def __init__(self, parent: QWidget | None = None, log=None, raise_if_missing: bool = False) -> None:
            # raise_if_missing is accepted for API compatibility
            super().__init__(parent=parent)
            self.log = log or get_logger(__name__)
            # Explicitly set a dark theme so traces remain visible regardless of
            # the user's global configuration.
            pg.setConfigOptions(antialias=True, background="k", foreground="w")
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
        def _validate_xy(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            x = np.asarray(x).ravel()
            y = np.asarray(y).ravel()
            if x.size != y.size:
                n = min(x.size, y.size)
                self.log.warning("Mismatched array lengths; truncating to %d", n)
                x = x[:n]
                y = y[:n]
            mask = np.isfinite(x) & np.isfinite(y)
            dropped = x.size - mask.sum()
            if dropped:
                self.log.warning("Dropped %d invalid rows", dropped)
            x = x[mask]
            y = y[mask]
            if x.size < 10:
                raise ValueError("Not enough valid data to plot")
            return x, y

        def plot_derivative(
            self, sp: ESRSpectrum, name: str | None = None, clear: bool = False
        ) -> None:
            """Plot a derivative spectrum."""

            if clear:
                self.clear()
            x, y = self._validate_xy(sp.field_B, sp.signal_dAbs)
            self.log.debug("plot_derivative with %d points", x.size)
            self.setLabel("left", "d(Abs)/dB (arb.)")
            # Use a visible pen so the derivative trace renders as a line
            self.plot(x, y, pen=pg.mkPen(color="w"), name=name)

        # ------------------------------------------------------------------
        def plot_absorption(
            self, sp: ESRSpectrum, name: str | None = None, clear: bool = False
        ) -> None:
            """Plot an absorption spectrum, computing it if necessary."""

            if sp.absorption is None:
                try:
                    sp.to_absorption()
                except Exception as e:
                    self.log.warning("Failed to compute absorption: %s", e)
            if sp.absorption is None:
                raise ValueError("Not enough valid data to plot")
            if clear:
                self.clear()
            x, y = self._validate_xy(sp.field_B, sp.absorption)
            self.log.debug("plot_absorption with %d points", x.size)
            self.setLabel("left", "Absorption (arb.)")
            # Dash the absorption line and use a contrasting color
            pen = pg.mkPen(color="y", style=Qt.DashLine)
            self.plot(x, y, pen=pen, name=name)

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
            self.plotItem.autoRange()
            self.plotItem.enableAutoRange("xy", False)


__all__ = ["PlotView"]

