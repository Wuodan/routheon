"""HTTP server wiring."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar, Dict, Type

from .aggregator import ModelAggregator
from .config import ServerConfig
from .models import ModelsResponse
from .stats import StatsCollector, load_stats_config

JsonDict = Dict[str, object]


def _json_bytes(payload: JsonDict) -> bytes:
    return json.dumps(payload).encode("utf-8")


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for routheon-server."""

    server_config: ClassVar[ServerConfig]
    model_aggregator: ClassVar[ModelAggregator]
    stats_collector: ClassVar[StatsCollector]

    def _write_json(self, payload: JsonDict, status_code: int = 200) -> None:
        body = _json_bytes(payload)
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/v1/models":
            payload: ModelsResponse = self.model_aggregator.get_models()
            self._write_json(payload)
        elif self.path == "/stats":
            payload = self.stats_collector.collect()
            self._write_json(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: D401
        """Route BaseHTTPRequestHandler logs through logging module."""

        logging.info("%s - %s", self.address_string(), fmt % args)


def run_server(config: ServerConfig) -> None:
    """Instantiate and start the HTTP server."""

    handler_class: Type[RequestHandler] = RequestHandler
    handler_class.server_config = config
    handler_class.model_aggregator = ModelAggregator(
        mappings_dir=config.mappings,
        skip_patterns=config.skip_mapping,
        mapping_timeout=config.mapping_timeout,
    )
    stats_config = (
        load_stats_config(config.stats_config_file)
        if config.stats_config_file
        else None
    )
    handler_class.stats_collector = StatsCollector(config=stats_config)

    httpd: HTTPServer = HTTPServer((config.host, config.port), handler_class)
    logging.info("Starting routheon-server on %s:%s", config.host, config.port)
    httpd.serve_forever()
