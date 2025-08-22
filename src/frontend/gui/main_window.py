"""Main application window for ESR-Lab."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from backend.core.spectrum import ESRSpectrum
from backend.io import loader

from .plot_view import PlotView
from backend.utils.logging import get_logger, get_log_path


class MainWindow(QMainWindow):
    """Main GUI window holding menus and the central :class:`PlotView`."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESR-Lab")

        self.log = get_logger(__name__)
        try:
            self.plot = PlotView(log=self.log, raise_if_missing=True)
        except RuntimeError as e:
            QMessageBox.critical(
                self,
                "Plotting Unavailable",
                "Plotting requires the 'PySide6' and 'pyqtgraph' packages.",
            )
            self.log.error("Plot initialization failed: %s", e)
            raise
        self.setCentralWidget(self.plot)

        self._spectra: List[ESRSpectrum] = []
        self._last_dir: str | None = None

        self._create_menus()
        self.statusBar()

        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    def _create_menus(self) -> None:
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu("File")
        # Keep a reference to the QAction backing the menu to avoid PySide
        # garbage collecting the underlying C++ object.
        self.file_menu_action = self.file_menu.menuAction()
        open_action = QAction("Open…", self)
        open_action.triggered.connect(self._open_file)
        self.file_menu.addAction(open_action)

        open_multi_action = QAction("Open Multiple…", self)
        open_multi_action.triggered.connect(self._open_files)
        self.file_menu.addAction(open_multi_action)

        self.file_menu.addSeparator()

        clear_action = QAction("Clear Plot", self)
        clear_action.triggered.connect(self.clear_plot)
        self.file_menu.addAction(clear_action)

        self.file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.view_menu = menubar.addMenu("View")
        self.view_menu_action = self.view_menu.menuAction()
        self.show_derivative_action = QAction(
            "Show Derivative", self, checkable=True, checked=True
        )
        self.show_absorption_action = QAction(
            "Show Absorption", self, checkable=True, checked=False
        )
        self.overlay_action = QAction(
            "Overlay Mode", self, checkable=True, checked=True
        )

        self.view_menu.addAction(self.show_derivative_action)
        self.view_menu.addAction(self.show_absorption_action)
        self.view_menu.addAction(self.overlay_action)

        self.help_menu = menubar.addMenu("Help")
        self.help_menu_action = self.help_menu.menuAction()
        view_log = QAction("View Log File", self)
        view_log.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_log_path())))
        )
        self.help_menu.addAction(view_log)

    # ------------------------------------------------------------------
    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Spectrum",
            self._last_dir or "",
            "CSV (*.csv);;All Files (*)",
        )
        if path:
            self._load_and_plot(Path(path))

    def _open_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Spectra",
            self._last_dir or "",
            "CSV (*.csv);;All Files (*)",
        )
        for p in paths:
            self._load_and_plot(Path(p))

    # ------------------------------------------------------------------
    def _load_and_plot(self, path: Path) -> None:
        try:
            sp = loader.load_any(path)
        except Exception:
            self.log.exception("Failed to load %s", path)
            return

        try:
            self.add_spectrum(sp, name=path.stem)
            self._last_dir = str(path.parent)
            self._update_title()
            self.log.info("Loaded %s with %d points", path, sp.field_B.size)
        except Exception:
            self.log.exception(
                "Loaded %s with %d points but plotting failed", path, sp.field_B.size
            )

    # ------------------------------------------------------------------
    def add_spectrum(self, sp: ESRSpectrum, name: str | None = None) -> None:
        """Add a spectrum and plot it via the unified entry point."""

        self._spectra.append(sp)
        plot_name = name or Path(sp.meta.source_path or "spectrum").stem
        self.plot_current(sp, name=plot_name)
        self._update_status(sp)

    # ------------------------------------------------------------------
    def plot_current(self, sp: ESRSpectrum, name: str | None = None) -> None:
        overlay = self.overlay_action.isChecked()
        self.plot.set_background(clear=not overlay or len(self._spectra) == 1)

        if self.show_derivative_action.isChecked():
            try:
                self.plot.plot_derivative(sp, name=name, clear=False)
            except Exception as e:  # pragma: no cover - validation logging
                self.log.warning("Derivative plot skipped: %s", e)
        if self.show_absorption_action.isChecked():
            abs_name = f"{name} (abs)" if name else None
            try:
                self.plot.plot_absorption(sp, name=abs_name, clear=False)
            except Exception as e:  # pragma: no cover - validation logging
                self.log.warning("Absorption plot skipped: %s", e)

        self.plot.enable_legend(overlay)
        self.plot.auto_range()

    # ------------------------------------------------------------------
    def clear_plot(self) -> None:
        self._spectra.clear()
        self.plot.set_background(clear=True)
        self._update_title()

    # ------------------------------------------------------------------
    def _update_status(self, sp: ESRSpectrum) -> None:
        freq = (sp.meta.frequency_Hz or 0.0) / 1e9
        mod = (sp.meta.mod_amp_T or 0.0) * 1e3
        power = (sp.meta.mw_power_W or 0.0) * 1e3
        pts = sp.field_B.size
        self.statusBar().showMessage(
            f"{freq:.3g} GHz, {mod:.3g} mT, {power:.3g} mW, {pts} pts"
        )

    def _update_title(self) -> None:
        base = "ESR-Lab"
        if len(self._spectra) > 1:
            base += " [*]"
        self.setWindowTitle(base)

    # ------------------------------------------------------------------
    # Drag and drop support
    def dragEnterEvent(self, event: QEvent) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".csv"):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QEvent) -> None:  # type: ignore[override]
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".csv"):
                self._load_and_plot(Path(path))
        event.acceptProposedAction()


__all__ = ["MainWindow"]
