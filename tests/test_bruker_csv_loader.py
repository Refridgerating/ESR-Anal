from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esr_lab.io import bruker_csv


def _write_file(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_multi_column_with_headers_detects_axes_and_units(tmp_path: Path) -> None:
    lines = ["Field (mT), Signal (dAbs)"] + [f"{i*100}, {i}" for i in range(1, 11)]
    file = _write_file(tmp_path / "multi.csv", lines)
    sp = bruker_csv.load_bruker_csv(file)
    assert sp.field_B.size == 10
    assert np.allclose(sp.field_B, np.linspace(0.1, 1.0, 10))
    assert np.allclose(sp.signal_dAbs, np.arange(1.0, 11.0))


def test_single_column_packed_splits_into_two_columns(tmp_path: Path) -> None:
    lines = ['"Field(mT),Signal"'] + [f'"{i*100}, {i}"' for i in range(1, 11)]
    file = _write_file(tmp_path / "packed.csv", lines)
    sp = bruker_csv.load_bruker_csv(file)
    assert sp.field_B.size == 10
    assert np.allclose(sp.field_B, np.linspace(0.1, 1.0, 10))
    assert np.allclose(sp.signal_dAbs, np.arange(1.0, 11.0))


def test_ambiguous_columns_default_to_first_two(tmp_path: Path) -> None:
    lines = ["Col1,Col2"] + [f"{2*i-1},{2*i}" for i in range(1, 11)]
    file = _write_file(tmp_path / "amb.csv", lines)
    sp = bruker_csv.load_bruker_csv(file)
    assert sp.field_B.size == 10
    assert np.allclose(sp.field_B, np.arange(1.0, 20.0, 2))
    assert np.allclose(sp.signal_dAbs, np.arange(2.0, 22.0, 2))

