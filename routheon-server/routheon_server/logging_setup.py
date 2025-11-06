"""Logging helpers."""

from __future__ import annotations

import logging
from typing import Optional


def configure_logging(level: str) -> None:
    """Configure logging based on the provided level name."""
    numeric_level: Optional[int] = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

