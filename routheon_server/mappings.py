"""Helpers for reading Traefik mapping files."""

from __future__ import annotations

import logging
import os
import re
from typing import List, Pattern, Set

import yaml


def urls_from_mapping(path: str) -> List[str]:
    """Extract backend URLs from a single Traefik mapping yaml file."""

    with open(path, encoding="utf-8") as file:
        mapping = yaml.safe_load(file) or {}

    try:
        return [
            server["url"].rstrip("/")
            for service in mapping["http"]["services"].values()
            for server in service["loadBalancer"]["servers"]
        ]
    except KeyError as exc:
        logging.error("KeyError in urls_from_mapping for %s: %s", path, exc)
        return []
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Unexpected error in urls_from_mapping for %s: %s", path, exc)
        return []


def discover_backend_urls(
    mappings_dir: str,
    skip_patterns: List[str],
) -> Set[str]:
    """Collect all unique backend URLs from mapping files."""

    skip_regexes: List[Pattern[str]] = [re.compile(pattern) for pattern in skip_patterns]
    urls: Set[str] = set()
    for file_name in os.listdir(mappings_dir):
        if not file_name.endswith((".yml", ".yaml")):
            continue
        if any(regex.search(file_name) for regex in skip_regexes):
            continue
        path: str = os.path.join(mappings_dir, file_name)
        urls.update(urls_from_mapping(path))
    return urls
