import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.utils import logging as logging_utils


def test_get_log_path(tmp_path, monkeypatch):
    custom_log = tmp_path / "logs" / "esr-lab.log"
    monkeypatch.setattr(logging_utils, "_LOG_PATH", custom_log)
    path = logging_utils.get_log_path()
    assert path == custom_log
    assert path.parent.name == "logs"


def test_get_logger_writes_and_reuses_instance(tmp_path, monkeypatch):
    log_file = tmp_path / "logs" / "esr-lab.log"
    log_file.parent.mkdir(parents=True)
    monkeypatch.setattr(logging_utils, "_LOG_PATH", log_file)
    monkeypatch.setenv("ESR_LOG_LEVEL", "WARNING")

    logger1 = logging_utils.get_logger("temp_logger")
    logger2 = logging_utils.get_logger("temp_logger")

    assert logger1 is logger2
    assert any(isinstance(h, RotatingFileHandler) for h in logger1.handlers)

    logger1.info("should not appear")
    logger1.warning("important message")

    for handler in logger1.handlers:
        if hasattr(handler, "flush"):
            handler.flush()
    content = log_file.read_text()
    assert "important message" in content
    assert "should not appear" not in content
    assert logger1.level == logging.WARNING

    for handler in list(logger1.handlers):
        handler.close()
        logger1.removeHandler(handler)
