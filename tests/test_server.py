"""Tests for routheon_server.server."""

from __future__ import annotations

import io
from typing import Dict, Tuple, Type, cast

import pytest

from routheon_server.aggregator import ModelAggregator
from routheon_server.config import ServerConfig
from routheon_server.server import RequestHandler, _json_bytes, run_server
from routheon_server.stats import StatsCollector


def test_json_bytes() -> None:
    """_json_bytes should encode JSON as UTF-8."""

    payload: Dict[str, object] = {"a": 1}
    assert _json_bytes(payload) == b'{"a": 1}'


def test_request_handler_do_get_models() -> None:
    """RequestHandler should return aggregated models."""

    class DummyAggregator:
        def get_models(self) -> Dict[str, object]:
            return {"models": []}

    class DummyStats:
        def collect(self) -> Dict[str, object]:
            return {"stats": True}

    handler = RequestHandler.__new__(RequestHandler)
    handler.path = "/v1/models"
    handler.model_aggregator = cast(ModelAggregator, DummyAggregator())
    handler.stats_collector = cast(StatsCollector, DummyStats())
    handler.server_config = ServerConfig(
        mappings="/tmp",
        host="127.0.0.1",
        port=0,
        skip_mapping=[],
        mapping_timeout=1,
        log_level="INFO",
        stats_config_file=None,
    )

    responses: Dict[str, int] = {}
    headers: Dict[str, str] = {}
    body_stream = io.BytesIO()

    def send_response(status: int) -> None:
        responses["status"] = status

    def send_header(key: str, value: str) -> None:
        headers[key] = value

    def end_headers() -> None:
        headers["ended"] = "yes"

    handler.send_response = send_response
    handler.send_header = send_header
    handler.end_headers = end_headers
    handler.wfile = body_stream

    handler.do_GET()

    assert responses["status"] == 200
    assert headers["Content-Type"] == "application/json"
    assert body_stream.getvalue() == b'{"models": []}'

    body_stream.truncate(0)
    body_stream.seek(0)
    handler.path = "/stats"
    handler.do_GET()
    assert body_stream.getvalue() == b'{"stats": true}'

    handler.path = "/unknown"
    handler.do_GET()
    assert responses["status"] == 404


def test_run_server_configures_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_server should configure handler dependencies and start HTTP server."""

    captured: Dict[str, object] = {}

    class DummyHTTPServer:
        def __init__(
            self,
            address: Tuple[str, int],
            handler_cls: Type[RequestHandler],
        ) -> None:
            captured["address"] = address
            captured["handler"] = handler_cls

        def serve_forever(self) -> None:
            raise RuntimeError("stop")

    monkeypatch.setattr("routheon_server.server.HTTPServer", DummyHTTPServer)

    config = ServerConfig(
        mappings="/tmp/maps",
        host="0.0.0.0",
        port=9999,
        skip_mapping=["skip.yml"],
        mapping_timeout=7,
        log_level="INFO",
        stats_config_file=None,
    )

    with pytest.raises(RuntimeError):
        run_server(config)

    handler_cls = captured["handler"]
    aggregator: ModelAggregator = handler_cls.model_aggregator
    stats_collector: StatsCollector = handler_cls.stats_collector

    assert captured["address"] == ("0.0.0.0", 9999)
    assert aggregator.mappings_dir == "/tmp/maps"
    assert aggregator.skip_patterns == ["skip.yml"]
    assert aggregator.mapping_timeout == 7
    assert isinstance(stats_collector, StatsCollector)
