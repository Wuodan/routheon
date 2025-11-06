"""Tests for routheon_server.config."""

from __future__ import annotations

from typing import List

import pytest

from routheon_server.config import ServerConfig, parse_args


def test_parse_args_defaults() -> None:
    """Ensure default CLI arguments are applied."""

    config: ServerConfig = parse_args([])
    assert config.mappings == "/etc/traefik/mappings"
    assert config.host == "127.0.0.1"
    assert config.port == 9080
    assert config.skip_mapping == ["routheon-server.yml"]
    assert config.mapping_timeout == 2
    assert config.log_level == "WARNING"
    assert config.stats_config_file is None


def test_parse_args_overrides() -> None:
    """Ensure CLI overrides are parsed correctly."""

    argv: List[str] = [
        "--mappings",
        "/tmp/mappings",
        "--host",
        "0.0.0.0",
        "--port",
        "9090",
        "--skip-mapping",
        "skip-1.yml",
        "--skip-mapping",
        "skip-2.yml",
        "--mapping-timeout",
        "5",
        "--log-level",
        "DEBUG",
        "--stats-config-file",
        "/tmp/stats.yml",
    ]

    config: ServerConfig = parse_args(argv)
    assert config.mappings == "/tmp/mappings"
    assert config.host == "0.0.0.0"
    assert config.port == 9090
    assert config.skip_mapping == [
        "routheon-server.yml",
        "skip-1.yml",
        "skip-2.yml",
    ]
    assert config.mapping_timeout == 5
    assert config.log_level == "DEBUG"
    assert config.stats_config_file == "/tmp/stats.yml"


def test_parse_args_invalid_port() -> None:
    """Ensure argparse surfaces invalid values."""

    with pytest.raises(SystemExit):
        parse_args(["--port", "not-an-int"])
