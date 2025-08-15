"""Main application window for ESR-Lab."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from esr_lab.core.spectrum import ESRMeta, ESRSpectrum
from esr_lab.io import bruker_csv, loader
from esr_lab.gui.panels.import_panel import FieldMappingDialog

from esr_lab.gui.plot_view import PlotView


class MainWindow(QMainWindow):
    """Main GUI window holding menus and the central :class:`PlotView`."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ESR-Lab")

        self.plot = PlotView()
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
        self._show_deriv_action = QAction("Show Derivative", self, checkable=True, checked=True)
        self._show_abs_action = QAction("Show Absorption", self, checkable=True, checked=False)
        self._overlay_action = QAction("Overlay Mode", self, checkable=True, checked=True)

        view_menu.addAction(self._show_deriv_action)
        view_menu.addAction(self._show_abs_action)
        view_menu.addAction(self._overlay_action)

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
        except bruker_csv.AxisSelectionNeeded:
            df = bruker_csv.read_dataframe(path)
            dlg = FieldMappingDialog(df, self)
            if dlg.exec() != QDialog.Accepted:
                return
            x_col, y_col = dlg.selected_axes()
            delimiter, header_idx, lines = bruker_csv.detect_delimiter_and_header(path)
            meta = bruker_csv.parse_metadata_from_header(lines[:header_idx])
            field, signal = bruker_csv.normalize_units_for_axes(
                df, x_col, y_col, lines[:header_idx], meta
            )
            sp = ESRSpectrum(field_B=field, signal_dAbs=signal, meta=ESRMeta(**meta))
        except Exception as exc:  # pragma: no cover - GUI feedback
            QMessageBox.critical(self, "Error", f"Failed to load {path}:\n{exc}")
            return

        self._last_dir = str(path.parent)
        self._spectra.append(sp)

        name = path.name
        self.plot_current(sp, name)
        self._update_status(sp)
        self._update_title()

    # ------------------------------------------------------------------
    def plot_current(self, sp: ESRSpectrum, name: str | None = None) -> None:
        overlay = self._overlay_action.isChecked()
        if not overlay or len(self._spectra) == 1:
            self.plot.set_background(clear=True)

        if self._show_deriv_action.isChecked():
            self.plot.plot_derivative(sp, name=name, clear=False)
        if self._show_abs_action.isChecked():
            abs_name = f"{name} (abs)" if name else None
            self.plot.plot_absorption(sp, name=abs_name, clear=False)

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

