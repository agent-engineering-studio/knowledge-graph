"""Structured logging setup using structlog."""

import logging
import sys

import structlog

from config.settings import settings


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON rendering for production.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if log_level <= logging.DEBUG else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


configure_logging(settings.LOG_LEVEL)
logger = structlog.get_logger()
