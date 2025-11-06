"""Tests for routheon_server.stats."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, MutableMapping, Optional

import pytest

from routheon_server.stats import (
    _collect_raw_stats,
    StatsCollector,
    StatsConfig,
    load_stats_config,
)


def test_stats_config_apply_filters_sections() -> None:
    """StatsConfig should limit sections and fields."""

    config = StatsConfig(
        enabled_sections={"cpu", "memory"},
        enabled_fields={"memory": {"used"}},
    )
    raw_stats: Dict[str, object] = {
        "cpu": {"usage_percent": 10},
        "memory": {"used": 1, "free": 2},
        "extra": {"ignored": True},
    }
    filtered: Dict[str, object] = config.apply(raw_stats)
    assert filtered == {
        "cpu": {"usage_percent": 10},
        "memory": {"used": 1},
    }


def test_stats_collector_respects_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """StatsCollector should call config.apply when present."""

    raw_stats: Dict[str, object] = {"cpu": {"usage_percent": 5}}
    collector = StatsCollector(config=StatsConfig(enabled_sections={"cpu"}))

    def fake_collect() -> Dict[str, object]:
        return raw_stats

    monkeypatch.setattr("routheon_server.stats._collect_raw_stats", fake_collect)
    assert collector.collect() == {"cpu": {"usage_percent": 5}}


def test_load_stats_config_success(tmp_path: Path) -> None:
    """load_stats_config should parse YAML into StatsConfig."""

    config_path: Path = tmp_path / "config.yml"
    config_path.write_text(
        """enabled_sections:
  - cpu
  - memory
  - disk
enabled_fields:
  memory:
    - used
  disk: []
""",
        encoding="utf-8",
    )
    config: Optional[StatsConfig] = load_stats_config(str(config_path))
    assert config is not None
    applied = config.apply(
        {
            "cpu": {"usage_percent": 1},
            "memory": {"used": 2, "free": 3},
            "disk": {"total": 4},
        }
    )
    assert applied == {
        "cpu": {"usage_percent": 1},
        "memory": {"used": 2},
        "disk": {},
    }


def test_load_stats_config_invalid_sections(tmp_path: Path) -> None:
    """load_stats_config should handle malformed configuration."""

    config_path: Path = tmp_path / "bad.yml"
    config_path.write_text("enabled_sections: not-a-list", encoding="utf-8")
    config: Optional[StatsConfig] = load_stats_config(str(config_path))
    assert config is None


def test_collect_raw_stats_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """_collect_raw_stats should return error payload on exception."""

    def raise_error() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("psutil.boot_time", raise_error)
    result: MutableMapping[str, object] = _collect_raw_stats()
    assert "error" in result
