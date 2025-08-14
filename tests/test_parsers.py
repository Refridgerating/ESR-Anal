"""Tests for CSV parsers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esr_lab.io.bruker_csv import load_bruker_csv  # noqa: E402


def test_load_bruker_csv() -> None:
    sample = Path(__file__).resolve().parents[1] / "data" / "examples" / "sample.csv"
    spectrum = load_bruker_csv(sample)
    assert spectrum.field_B.size > 0
    assert spectrum.signal_dAbs.size > 0
