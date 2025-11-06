"""Tests for routheon_server.cli."""

from __future__ import annotations

from typing import List

import pytest

from routheon_server.cli import main, run
from routheon_server.config import ServerConfig


def test_run_invokes_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """run should configure logging then start server."""

    calls: List[str] = []
    config = ServerConfig(
        mappings="/tmp",
        host="127.0.0.1",
        port=8000,
        skip_mapping=[],
        mapping_timeout=2,
        log_level="DEBUG",
        stats_config_file=None,
    )

    def fake_configure(level: str) -> None:
        calls.append(f"log:{level}")

    def fake_run_server(conf: ServerConfig) -> None:
        calls.append(f"server:{conf.port}")

    monkeypatch.setattr("routheon_server.cli.configure_logging", fake_configure)
    monkeypatch.setattr("routheon_server.cli.run_server", fake_run_server)

    run(config)
    assert calls == ["log:DEBUG", "server:8000"]


def test_main_parses_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """main should parse args and delegate to run."""

    config = ServerConfig(
        mappings="/tmp",
        host="127.0.0.1",
        port=8081,
        skip_mapping=[],
        mapping_timeout=5,
        log_level="INFO",
        stats_config_file=None,
    )

    def fake_parse(argv: List[str] | None) -> ServerConfig:
        assert argv == ["--port", "8081"]
        return config

    called: List[ServerConfig] = []

    def fake_run(conf: ServerConfig) -> None:
        called.append(conf)

    monkeypatch.setattr("routheon_server.cli.parse_args", fake_parse)
    monkeypatch.setattr("routheon_server.cli.run", fake_run)

    main(["--port", "8081"])
    assert called == [config]
