"""Logging configuration driven by environment variables.

Features:
    * Colored console output (toggle via ``LOG_USE_COLORS``).
    * Always-silenced noisy loggers (hpack/h2/httpcore/...) — these emit
      binary/unreadable DEBUG spam even when the rest of the app is in DEBUG.
    * Log level is controlled by the ``LOG_LEVEL`` env variable.
"""

import logging
import sys

from app.core.config import get_settings

_CONFIGURED = False


# ANSI colour codes per log level.
_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[1;31m",  # bold red
}
_RESET = "\033[0m"
_DIM = "\033[2m"


class _ColorFormatter(logging.Formatter):
    """Formatter that wraps the level name (and logger name) in ANSI colors."""

    def __init__(self, fmt: str, use_colors: bool) -> None:
        super().__init__(fmt)
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        if not self.use_colors:
            return super().format(record)

        color = _COLORS.get(record.levelname, "")
        original_levelname = record.levelname
        original_name = record.name
        record.levelname = f"{color}{record.levelname}{_RESET}"
        record.name = f"{_DIM}{record.name}{_RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname
            record.name = original_name


def setup_logging() -> logging.Logger:
    """Initialize the root logger using settings from environment variables."""
    global _CONFIGURED
    settings = get_settings()

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not _CONFIGURED:
        # Drop any handlers added by uvicorn/pytest before us so we control output.
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_ColorFormatter(settings.log_format, settings.log_use_colors))
        root_logger.addHandler(handler)
        _CONFIGURED = True

    # Always silence chatty libs that produce unreadable wire-level output.
    for name in (n.strip() for n in settings.log_silenced_loggers.split(",") if n.strip()):
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        lg.propagate = True

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger after ensuring the root logger is configured."""
    setup_logging()
    return logging.getLogger(name)
