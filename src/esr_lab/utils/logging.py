"""Application-wide logging utilities."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

__all__ = ["get_logger", "get_log_path"]


def _resolve_log_path() -> Path:
    """Return path to the log file creating directories if needed."""

    try:
        root = Path(__file__).resolve().parents[3]
    except Exception:
        root = Path.cwd()
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "esr-lab.log"


_LOG_PATH = _resolve_log_path()


def get_log_path() -> Path:
    """Return the path of the application log file."""

    return _LOG_PATH


def get_logger(name: str = "esr_lab") -> logging.Logger:
    """Return a configured :class:`logging.Logger`.

    The logger writes to both STDERR and a rotating log file located in
    ``logs/esr-lab.log`` relative to the repository root.
    """

    logger = logging.getLogger(name)
    if getattr(logger, "_esr_configured", False):
        return logger

    level_name = os.getenv("ESR_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt)

    file_handler = RotatingFileHandler(_LOG_PATH, maxBytes=1_000_000, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger._esr_configured = True  # type: ignore[attr-defined]
    logger.log_path = _LOG_PATH  # type: ignore[attr-defined]
    return logger
