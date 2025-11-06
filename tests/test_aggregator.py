"""Tests for routheon_server.aggregator."""

from __future__ import annotations

from typing import List, Set

import pytest

from routheon_server.aggregator import ModelAggregator
from routheon_server.models import ModelsResponse


def test_model_aggregator_get_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """ModelAggregator should discover and aggregate models."""

    discovered_urls: Set[str] = {"http://one", "http://two"}
    expected_payload: ModelsResponse = {"models": [], "data": []}

    def fake_discover(mappings_dir: str, skip_patterns: List[str]) -> Set[str]:
        assert mappings_dir == "/tmp/mappings"
        assert skip_patterns == ["skip-this.yml"]
        return discovered_urls

    def fake_aggregate(urls: List[str], timeout: int) -> ModelsResponse:
        assert urls == ["http://one", "http://two"]
        assert timeout == 3
        return expected_payload

    monkeypatch.setattr(
        "routheon_server.aggregator.discover_backend_urls",
        fake_discover,
    )
    monkeypatch.setattr(
        "routheon_server.aggregator.aggregate_all",
        fake_aggregate,
    )

    aggregator = ModelAggregator(
        mappings_dir="/tmp/mappings",
        skip_patterns=["skip-this.yml"],
        mapping_timeout=3,
    )

    payload: ModelsResponse = aggregator.get_models()
    assert payload == expected_payload
