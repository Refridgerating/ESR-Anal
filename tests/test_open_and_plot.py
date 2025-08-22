"""Smoke tests for loading and plotting."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.core.spectrum import ESRSpectrum  # noqa: E402
from backend.io import loader  # noqa: E402
import pytest


@pytest.fixture
def qtbot():  # type: ignore[ann-type]
    pytest.importorskip("PySide6")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        pytest.skip("QtWidgets not available")

    app = QApplication.instance() or QApplication([])

    class _Bot:
        def addWidget(self, w):  # noqa: D401 - simple helper
            w.show()

    return _Bot()


def test_loader_parses_example_csv(tmp_path: Path) -> None:
    sample = Path(__file__).resolve().parents[1] / "data" / "examples" / "sample.csv"
    dest = tmp_path / "sample.csv"
    shutil.copy(sample, dest)
    sp = loader.load_any(dest)
    assert sp.field_B.size > 10


def test_plot_view_handles_single_and_overlay(qtbot) -> None:  # type: ignore[ann-type]
    pytest.importorskip("PySide6")
    pytest.importorskip("pyqtgraph")
    from frontend.gui.plot_view import PlotView

    view = PlotView()
    qtbot.addWidget(view)

    x = np.linspace(0.0, 1.0, 5)
    sp1 = ESRSpectrum(field_B=x, signal_dAbs=np.sin(x))
    sp2 = ESRSpectrum(field_B=x, signal_dAbs=np.cos(x))

    view.plot_derivative(sp1, clear=True)
    view.plot_derivative(sp2)

    assert len(view.plotItem.listDataItems()) >= 2

