"""Command line interface for routheon-server."""

from __future__ import annotations

from typing import List, Optional

from .config import ServerConfig, parse_args
from .logging_setup import configure_logging
from .server import run_server


def run(config: ServerConfig) -> None:
    """Configure logging and run server with provided config."""

    configure_logging(config.log_level)
    run_server(config)


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entrypoint."""

    config = parse_args(argv)
    run(config)


if __name__ == "__main__":
    main()

