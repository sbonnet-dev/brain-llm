"""Logging configuration driven by environment variables."""

import logging
import sys

from app.core.config import get_settings

_CONFIGURED = False


def setup_logging() -> logging.Logger:
    """Initialize the root logger using settings from environment variables."""
    global _CONFIGURED
    settings = get_settings()

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(settings.log_format))
        root_logger.addHandler(handler)
        _CONFIGURED = True

    # Reduce verbosity of chatty third-party libraries unless DEBUG is enabled.
    if level > logging.DEBUG:
        for noisy in ("uvicorn.access", "httpx", "httpcore"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger after ensuring the root logger is configured."""
    setup_logging()
    return logging.getLogger(name)
