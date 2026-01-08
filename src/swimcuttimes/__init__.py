"""Swim cut times tracking for club, high school, and college swimmers."""

__version__ = "0.1.0"

from swimcuttimes.logging import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
)

__all__ = [
    "configure_logging",
    "get_logger",
    "bind_context",
    "clear_context",
]
