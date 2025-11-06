"""Argument parsing and configuration dataclasses."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class ServerConfig:
    """Runtime configuration for routheon-server."""

    mappings: str
    host: str
    port: int
    skip_mapping: List[str]
    mapping_timeout: int
    log_level: str
    stats_config_file: Optional[str]


def parse_args(argv: Optional[List[str]] = None) -> ServerConfig:
    """Parse CLI arguments and return a ServerConfig."""

    parser = argparse.ArgumentParser(
        description="Aggregate /v1/models from all Traefik backends."
    )
    parser.add_argument(
        "--mappings",
        default="/etc/traefik/mappings",
        help="Directory containing Traefik mapping files",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the HTTP server to (e.g. 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9080,
        help="Port to listen on (e.g. 9080)",
    )
    parser.add_argument(
        "--skip-mapping",
        action="append",
        default=["routheon-server.yml"],
        help="YAML filenames to skip (regex patterns, e.g. routheon-server.yml)",
    )
    parser.add_argument(
        "--mapping-timeout",
        type=int,
        default=2,
        help="Timeout in seconds for a request to a mapping",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "--stats-config-file",
        default=None,
        help="Path to YAML file controlling which /stats fields to expose",
    )
    args = parser.parse_args(argv)
    skip_mapping: List[str] = list(args.skip_mapping or [])

    return ServerConfig(
        mappings=args.mappings,
        host=args.host,
        port=args.port,
        skip_mapping=skip_mapping,
        mapping_timeout=args.mapping_timeout,
        log_level=args.log_level,
        stats_config_file=args.stats_config_file,
    )
