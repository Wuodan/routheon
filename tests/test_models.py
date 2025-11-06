"""Tests for routheon_server.models."""

from __future__ import annotations

import io
import json
from typing import Dict, Optional
from urllib.error import URLError

import pytest

from routheon_server.models import (
    ModelsResponse,
    aggregate_all,
    fetch_models_payload,
    normalize_model_id,
)


class _FakeResponse:
    """Context manager emulating urllib response."""

    def __init__(self, payload: Dict[str, object]) -> None:
        self._stream = io.StringIO(json.dumps(payload))

    def __enter__(self) -> io.StringIO:

        return self._stream

    def __exit__(self, *_exc: object) -> None:
        self._stream.close()


def test_fetch_models_payload_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_models_payload should parse JSON content."""

    payload: ModelsResponse = {"models": [{"model": "m"}], "data": []}

    def fake_urlopen(url: str, timeout: int) -> _FakeResponse:
        assert url == "http://srv/v1/models"
        assert timeout == 2
        return _FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result: ModelsResponse = fetch_models_payload("http://srv", 2)
    assert result == payload


def test_fetch_models_payload_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetch_models_payload should return empty dict on URLError."""

    def fake_urlopen(url: str, timeout: int) -> None:
        raise URLError("down")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result: ModelsResponse = fetch_models_payload("http://srv", 1)
    assert result == {}


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"model": "model-1"}, "model-1"),
        ({"name": "name-1"}, "name-1"),
        ({"model": 123}, "123"),
        ("not-a-mapping", None),
        ({}, None),
    ],
)
def test_normalize_model_id(entry: object, expected: Optional[str]) -> None:
    """normalize_model_id should prioritise 'model' then 'name'."""

    assert normalize_model_id(entry) == expected


def test_aggregate_all_merges_unique_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """aggregate_all should align ids across models and data."""

    responses: Dict[str, ModelsResponse] = {
        "http://one": {
            "models": [{"model": "a", "name": "A"}],
            "data": [{"id": "a"}],
        },
        "http://two": {
            "models": [{"model": "b", "name": "B"}],
            "data": [{"id": "b"}],
        },
    }

    def fake_fetch(url: str, timeout: int) -> ModelsResponse:
        assert timeout == 5
        return responses[url]

    monkeypatch.setattr("routheon_server.models.fetch_models_payload", fake_fetch)

    payload: ModelsResponse = aggregate_all(
        ["http://one", "http://two"],
        mapping_timeout=5,
    )
    assert payload["models"] == [
        {"model": "a", "name": "A"},
        {"model": "b", "name": "B"},
    ]
    assert payload["data"] == [{"id": "a"}, {"id": "b"}]


def test_aggregate_all_handles_fetch_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """aggregate_all should continue when fetch raises."""

    call_count: Dict[str, int] = {"calls": 0}

    def fake_fetch(url: str, timeout: int) -> ModelsResponse:
        call_count["calls"] += 1
        if url == "http://bad":
            raise RuntimeError("oops")
        return {"models": [{"model": "good"}], "data": [{"id": "good"}]}

    monkeypatch.setattr("routheon_server.models.fetch_models_payload", fake_fetch)

    payload: ModelsResponse = aggregate_all(["http://bad", "http://good"], 1)
    assert call_count["calls"] == 2
    assert payload["models"] == [{"model": "good"}]
    assert payload["data"] == [{"id": "good"}]
