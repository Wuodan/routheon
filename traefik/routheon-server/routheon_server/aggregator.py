"""Model aggregation façade used by the HTTP layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

from .mappings import discover_backend_urls
from .models import ModelsResponse, aggregate_all


@dataclass(slots=True)
class ModelAggregator:
    """Resolve backend URLs and aggregate the combined /v1/models payload."""

    mappings_dir: str
    skip_patterns: List[str]
    mapping_timeout: int

    def get_models(self) -> ModelsResponse:
        urls: Set[str] = discover_backend_urls(self.mappings_dir, self.skip_patterns)
        ordered_urls: List[str] = sorted(urls)
        return aggregate_all(ordered_urls, self.mapping_timeout)
