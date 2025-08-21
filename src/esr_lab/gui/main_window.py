"""Main application window for ESR-Lab."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QEvent, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMainWindow

from esr_lab.core.spectrum import ESRSpectrum
from esr_lab.io import loader

from esr_lab.gui.plot_view import PlotView
from esr_lab.utils.logging import get_logger, get_log_path


class MainWindow(QMainWindow):
    """Main GUI window holding menus and the central :class:`PlotView`."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESR-Lab")

        self.log = get_logger(__name__)
        self.plot = PlotView(log=self.log, raise_if_missing=True)
        self.setCentralWidget(self.plot)

        self._spectra: List[ESRSpectrum] = []
        self._last_dir: str | None = None

        self._create_menus()
        self.statusBar()

        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    def _create_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open…", self)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        open_multi_action = QAction("Open Multiple…", self)
        open_multi_action.triggered.connect(self._open_files)
        file_menu.addAction(open_multi_action)

        file_menu.addSeparator()

        clear_action = QAction("Clear Plot", self)
        clear_action.triggered.connect(self.clear_plot)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")
        self.show_derivative_action = QAction("Show Derivative", self, checkable=True, checked=True)
        self.show_absorption_action = QAction("Show Absorption", self, checkable=True, checked=False)
        self.overlay_action = QAction("Overlay Mode", self, checkable=True, checked=True)

        view_menu.addAction(self.show_derivative_action)
        view_menu.addAction(self.show_absorption_action)
        view_menu.addAction(self.overlay_action)

        help_menu = menubar.addMenu("Help")
        view_log = QAction("View Log File", self)
        view_log.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_log_path()))))
        help_menu.addAction(view_log)

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
            self.add_spectrum(sp, name=path.stem)
            self._last_dir = str(path.parent)
            self._update_title()
            self.log.info("Loaded %s with %d points", path, sp.field_B.size)
        except Exception:
            self.log.exception("Failed to load/plot %s", path)

    # ------------------------------------------------------------------
    def add_spectrum(self, sp: ESRSpectrum, name: str | None = None) -> None:
        self._spectra.append(sp)
        clear_flag = not self.overlay_action.isChecked()
        plot_name = name or Path(sp.meta.source_path or "spectrum").stem
        self.plot.plot_derivative(sp, name=plot_name, clear=clear_flag)
        if self.show_absorption_action.isChecked():
            self.plot.plot_absorption(sp, name=(name or "absorption"))
        self.plot.auto_range()
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

