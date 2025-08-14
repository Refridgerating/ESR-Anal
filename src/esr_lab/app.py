"""Minimal ESR-Lab GUI."""

from __future__ import annotations

import sys

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


def main() -> int:
    """Launch the ESR-Lab GUI."""
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("ESR-Lab")
    label = QLabel("ESR-Lab GUI – Under Construction")
    window.setCentralWidget(label)

    menubar = window.menuBar()
    file_menu = menubar.addMenu("File")
    quit_action = QAction("Quit", window)
    quit_action.triggered.connect(app.quit)
    file_menu.addAction(quit_action)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
