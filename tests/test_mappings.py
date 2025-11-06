"""Tests for routheon_server.mappings."""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

import pytest

from routheon_server.mappings import discover_backend_urls, urls_from_mapping


def _write_mapping(path: Path, body: str) -> None:
    """Write YAML mapping to disk."""

    path.write_text(body, encoding="utf-8")


def test_urls_from_mapping_success(tmp_path: Path) -> None:
    """urls_from_mapping should extract URLs from a valid mapping."""

    mapping_path: Path = tmp_path / "service.yml"
    _write_mapping(
        mapping_path,
        """http:
  services:
    svc:
      loadBalancer:
        servers:
          - url: "http://one"
          - url: "http://two/"
""",
    )

    urls: List[str] = urls_from_mapping(str(mapping_path))
    assert urls == ["http://one", "http://two"]


def test_urls_from_mapping_handles_missing_keys(tmp_path: Path) -> None:
    """urls_from_mapping should tolerate malformed files."""

    mapping_path: Path = tmp_path / "bad.yml"
    mapping_path.write_text("{}", encoding="utf-8")
    urls: List[str] = urls_from_mapping(str(mapping_path))
    assert urls == []


def test_discover_backend_urls_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """discover_backend_urls should honor file suffixes and skip patterns."""

    mappings_dir: Path = tmp_path
    _write_mapping(
        mappings_dir / "include.yml",
        """http:
  services:
    svc:
      loadBalancer:
        servers:
          - url: "http://include"
""",
    )
    _write_mapping(
        mappings_dir / "skip-me.yml",
        """http:
  services:
    svc:
      loadBalancer:
        servers:
          - url: "http://skip"
""",
    )
    (mappings_dir / "not-a-yaml.txt").write_text("ignored", encoding="utf-8")

    urls: Set[str] = discover_backend_urls(
        mappings_dir=str(mappings_dir),
        skip_patterns=["skip-.*"],
    )
    assert urls == {"http://include"}
