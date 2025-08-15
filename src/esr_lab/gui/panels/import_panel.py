"""Import panel providing a basic field mapping dialog."""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from esr_lab.core.spectrum import ESRMeta, ESRSpectrum
from esr_lab.io import bruker_csv, loader


class FieldMappingDialog(QDialog):
    """Dialog asking the user to choose X and Y columns."""

    def __init__(self, df: pd.DataFrame, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Axes")

        numeric_cols = [
            c for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().mean() >= 0.9
        ]

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        for c in numeric_cols:
            self.x_combo.addItem(c)
            self.y_combo.addItem(c)
        form.addRow("X Axis", self.x_combo)
        form.addRow("Y Axis", self.y_combo)
        layout.addLayout(form)

        table = QTableWidget(min(8, len(df)), len(df.columns))
        table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for i in range(min(8, len(df))):
            for j, col in enumerate(df.columns):
                table.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_axes(self) -> tuple[str, str]:
        return self.x_combo.currentText(), self.y_combo.currentText()


class ImportPanel(QWidget):
    """Thin wrapper used by :class:`MainWindow` to handle imports."""

    spectrumLoaded = Signal(ESRSpectrum)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def load_file(self, path: str) -> None:
        """Load ``path`` emitting ``spectrumLoaded`` on success."""

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
        except Exception:
            return

        self.spectrumLoaded.emit(sp)


__all__ = ["ImportPanel", "FieldMappingDialog"]

