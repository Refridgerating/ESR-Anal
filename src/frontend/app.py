"""Application entry point for ESR-Lab."""

from __future__ import annotations

import sys
from pathlib import Path

from backend.utils.logging import get_logger

# Allow running as script: python src/frontend/app.py
_here = Path(__file__).resolve()
_src = _here.parents[2]  # repo/src
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

log = get_logger(__name__)


def main() -> None:
    from PySide6.QtWidgets import QApplication
    from frontend.gui.main_window import MainWindow

    log.info("Application starting")

    def _excepthook(etype, value, tb):
        log.exception("Uncaught exception", exc_info=(etype, value, tb))
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(None, "Unexpected Error", str(value))

    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    log.info("Application exiting")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
