from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esr_lab.gui.plot_view import PlotView
from esr_lab.io import loader


def test_validate_xy_drops_bad_rows_and_logs(caplog):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    view = PlotView()
    x = np.arange(12, dtype=float)
    y = np.arange(12, dtype=float)
    x[3] = np.nan
    y[5] = np.inf
    with caplog.at_level(logging.WARNING):
        xv, yv = view._validate_xy(x, y)
    assert len(xv) == 10
    assert any("Dropped" in r.message for r in caplog.records)


def test_loader_logs_error_on_bad_csv(tmp_path: Path, caplog):
    bad = tmp_path / "bad.csv"
    bad.write_text("a;b;c\n1;2;3\n")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            loader.load_any(bad)
    assert any("bad.csv" in r.message for r in caplog.records)
