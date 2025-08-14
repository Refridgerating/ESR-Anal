"""Application entry point for ESR-Lab."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure 'src' is on sys.path when running as a script: python src/esr_lab/app.py
_here = Path(__file__).resolve()
_src = _here.parents[2]  # .../repo/src
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from PySide6.QtWidgets import QApplication

from esr_lab.gui.main_window import MainWindow


def main() -> None:
    """Launch the ESR-Lab GUI."""

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()

