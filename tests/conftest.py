"""Pytest configuration ensuring local package import precedence."""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_ROOT: Path = Path(__file__).resolve().parents[1]

if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
