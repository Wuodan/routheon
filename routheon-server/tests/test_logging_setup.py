"""Tests for routheon_server.logging_setup."""

from __future__ import annotations

import logging
from typing import List

import pytest

from routheon_server.logging_setup import configure_logging


def _reset_root_logger() -> None:
    """Clear root logger handlers to allow reconfiguration."""

    root_logger = logging.getLogger()
    handlers: List[logging.Handler] = list(root_logger.handlers)
    for handler in handlers:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.NOTSET)


def test_configure_logging_valid_level() -> None:
    """configure_logging should set the numeric log level."""

    _reset_root_logger()
    configure_logging("info")
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_invalid_level() -> None:
    """configure_logging should reject unknown levels."""

    _reset_root_logger()
    with pytest.raises(ValueError):
        configure_logging("invalid-level")
