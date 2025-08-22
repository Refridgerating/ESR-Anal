from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QFileDialog  # noqa: E402
from frontend.gui.main_window import MainWindow  # noqa: E402
from backend.core.spectrum import ESRSpectrum, ESRMeta  # noqa: E402
from backend.io import loader  # noqa: E402


# ---------------------------------------------------------------------------

def test_open_and_overlay_mode(qtbot, tmp_path: Path, monkeypatch) -> None:
    """Open spectra and toggle overlay mode in the GUI."""

    window = MainWindow()
    qtbot.addWidget(window)

    # Prepare spectrum returned by loader
    x = np.linspace(0.0, 1.0, 10)
    sp = ESRSpectrum(
        field_B=x,
        signal_dAbs=np.sin(x),
        meta=ESRMeta(frequency_Hz=9e9, mod_amp_T=1e-4, mw_power_W=2e-3),
    )

    calls: list[Path] = []

    def fake_load_any(path: Path) -> ESRSpectrum:
        calls.append(path)
        return sp

    monkeypatch.setattr(loader, "load_any", fake_load_any)

    # Create a temporary CSV file
    csv1 = tmp_path / "sp1.csv"
    csv1.write_text("field,signal\n1,0.1\n", encoding="utf-8")

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *a, **k: (str(csv1), ""),
    )

    # Trigger File -> Open…
    open_action = window.menuBar().actions()[0].menu().actions()[0]
    open_action.trigger()

    assert calls == [csv1]
    assert len(window.plot.plotItem.listDataItems()) == 1
    assert "10 pts" in window.statusBar().currentMessage()

    # Disable overlay mode
    overlay_action = window.overlay_action
    overlay_action.trigger()  # unchecked

    csv2 = tmp_path / "sp2.csv"
    csv2.write_text("field,signal\n2,0.2\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *a, **k: (str(csv2), ""),
    )
    open_action.trigger()

    assert len(window.plot.plotItem.listDataItems()) == 1

    # Re-enable overlay mode
    overlay_action.trigger()  # checked

    csv3 = tmp_path / "sp3.csv"
    csv3.write_text("field,signal\n3,0.3\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *a, **k: (str(csv3), ""),
    )
    open_action.trigger()

    assert len(window.plot.plotItem.listDataItems()) == 2
