"""Structured logging configuration for swimcuttimes.

Usage:
    from swimcuttimes.logging import get_logger, configure_logging

    # Call once at application startup
    configure_logging()

    # Get a logger in any module
    logger = get_logger(__name__)
    logger.info("user_logged_in", user_id="123", email="user@example.com")

Environment variables:
    LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
    LOG_FORMAT: json, console (default: console for dev, json for prod)
    ENVIRONMENT: development, production, test (default: development)
"""

import logging
import os
import sys
from typing import Any

import structlog


def _get_environment() -> str:
    """Get current environment."""
    return os.getenv("ENVIRONMENT", "development").lower()


def _get_log_level() -> int:
    """Get log level from environment."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level, logging.INFO)


def _get_log_format() -> str:
    """Get log format - json for prod, console for dev."""
    explicit = os.getenv("LOG_FORMAT")
    if explicit:
        return explicit.lower()
    return "json" if _get_environment() == "production" else "console"


def _add_environment(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add environment to all log entries."""
    event_dict["environment"] = _get_environment()
    return event_dict


def configure_logging() -> None:
    """Configure structlog for the application.

    Call this once at application startup (e.g., in main.py or app factory).
    """
    log_format = _get_log_format()
    log_level = _get_log_level()

    # Shared processors for all formats
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_environment,
    ]

    if log_format == "json":
        # Production: JSON output
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to match
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        A configured structlog logger

    Example:
        logger = get_logger(__name__)
        logger.info("processing_request", request_id="abc123", user_id="456")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables that will be included in all subsequent logs.

    Useful for adding request_id, user_id, etc. at the start of a request.

    Args:
        **kwargs: Key-value pairs to bind to the logging context

    Example:
        bind_context(request_id="abc123", user_id="456")
        logger.info("processing")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables.

    Call this at the end of a request to prevent context leaking.
    """
    structlog.contextvars.clear_contextvars()
