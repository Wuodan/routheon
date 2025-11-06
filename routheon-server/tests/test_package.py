"""Tests for routheon_server package exports."""

from __future__ import annotations

import runpy
from typing import List

import pytest

import routheon_server


def test_package_all() -> None:
    """Ensure routheon_server exposes expected symbols."""

    exported: List[str] = list(routheon_server.__all__)
    assert exported == ["ServerConfig", "main"]


def test_module_main_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    """python -m routheon_server should invoke cli.main."""

    calls: List[List[str] | None] = []

    def fake_main(argv: List[str] | None = None) -> None:
        calls.append(argv)

    monkeypatch.setattr("routheon_server.cli.main", fake_main)
    runpy.run_module("routheon_server.__main__", run_name="__main__")
    assert calls == [None]
