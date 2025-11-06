"""Model aggregation helpers."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, List, Mapping, MutableMapping, Optional, TypedDict


class DataItem(TypedDict, total=False):
    """Representation of a /v1/models data entry."""

    id: str


class ModelItem(TypedDict, total=False):
    """Representation of a /v1/models model entry."""

    model: str
    name: str


class ModelsResponse(TypedDict, total=False):
    """Payload returned by /v1/models aggregation."""

    models: List[ModelItem]
    data: List[DataItem]


def fetch_models_payload(url: str, mapping_timeout: int) -> ModelsResponse:
    """Call <url>/v1/models and return the parsed JSON, or {} on error."""

    try:
        with urllib.request.urlopen(
            f"{url}/v1/models", timeout=mapping_timeout
        ) as response:  # nosec - URLs controlled via Traefik mappings
            return json.load(response)
    except urllib.error.URLError as exc:
        logging.info(
            "URL not available for %s, server probably down. (URLError: %s)", url, exc
        )
        return {}
    except json.JSONDecodeError as exc:
        logging.error("JSONDecodeError from %s: %s", url, exc)
        return {}
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Unexpected error fetching %s: %s", url, exc)
        return {}


def normalize_model_id(model_entry: Mapping[str, object]) -> Optional[str]:
    """Get the model's id string from a 'models' entry."""

    if not isinstance(model_entry, Mapping):
        return None
    if model_entry.get("model"):
        return str(model_entry["model"])
    if model_entry.get("name"):
        return str(model_entry["name"])
    return None


def aggregate_all(urls: List[str], mapping_timeout: int) -> ModelsResponse:
    """Fetch /v1/models from all URLs and merge the payloads."""

    data_map: MutableMapping[str, DataItem] = {}
    models_map: MutableMapping[str, ModelItem] = {}

    with ThreadPoolExecutor() as executor:
        futures: Dict[Future[ModelsResponse], str] = {
            executor.submit(fetch_models_payload, url, mapping_timeout): url
            for url in urls
        }
        for future, url in futures.items():
            try:
                payload: ModelsResponse = future.result()
            except Exception as exc:  # pylint: disable=broad-except
                logging.error("Error fetching models from %s: %s", url, exc)
                continue

            if not payload:
                continue

            for data in payload.get("data", []):
                model_id = data.get("id")
                if model_id and model_id not in data_map:
                    data_map[str(model_id)] = data

            for model in payload.get("models", []):
                model_id = normalize_model_id(model)
                if model_id and model_id not in models_map:
                    models_map[model_id] = model

    # align indexes
    all_ids = sorted(set(data_map.keys()) | set(models_map.keys()))
    aligned_data: List[DataItem] = [
        data_map.get(model_id, {"id": model_id}) for model_id in all_ids
    ]
    aligned_models: List[ModelItem] = [
        models_map.get(model_id, {"model": model_id, "name": model_id})
        for model_id in all_ids
    ]

    return {"models": aligned_models, "data": aligned_data}
