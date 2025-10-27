#!/usr/bin/env python3

"""
Copyright (c) 2025 Stefan Kuhn.

Licensed under Apache License 2.0.
See: https://github.com/Wuodan/routheon
"""

import argparse
import json
import logging
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Dict, Any, Optional

import yaml


def configure_logging(level: str):
    """Configure logging based on the provided level."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s')


def urls_from_mapping(path: str) -> List[str]:
    """Extract backend URLs from a single traefik mapping yaml file."""
    with open(path, encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}
    try:
        return [
            s["url"].rstrip("/")
            for s in y["http"]["services"].values()
            for s in s["loadBalancer"]["servers"]
        ]
    except KeyError as e:
        logging.error(f"KeyError in urls_from_mapping: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in urls_from_mapping: {e}")
        return []


def fetch_models_payload(url: str, mapping_timeout: int) -> Dict[str, Any]:
    """
    Call <url>/v1/models and return the parsed JSON, or {} on error.
    Expected shape:
    {
      "models": [...],
      "data": [...]
    }
    """
    try:
        with urllib.request.urlopen(f"{url}/v1/models", timeout=mapping_timeout) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        logging.info(f"URL not available, server probably down. Received URLError in fetch_models_payload: {e}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"JSONDecodeError in fetch_models_payload: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error in fetch_models_payload: {e}")
        return {}


def normalize_model_id(m: Any) -> Optional[str]:
    """
    Get the model's id string from a 'models' entry.
    Prefer 'model', else 'name', else None.
    """
    if not isinstance(m, dict):
        return None
    if m.get("model"):
        return m["model"]
    if m.get("name"):
        return m["name"]
    return None


def aggregate_all(urls: set[str], mapping_timeout: int) -> Dict[str, Any]:
    """
    1. read all traefik mapping files
    2. call /v1/models on each backend
    3. merge all results:
       data_map[id]   (from .data[].id)
       models_map[id] (from .models[].model / .name)
    4. align indices and return one flat JSON
    """

    data_map = {}
    models_map = {}

    for u in urls:
        # don't let one dead backend kill the loop
        try:
            payload = fetch_models_payload(u, mapping_timeout)
        except Exception:
            continue

        if not payload:
            continue

        # merge data[]
        try:
            for d in payload.get("data", []):
                mid = d.get("id")
                if mid and mid not in data_map:
                    data_map[mid] = d
        except KeyError as e:
            logging.error(f"KeyError in aggregate_all while processing data: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in aggregate_all while processing data: {e}")

        # merge models[]
        try:
            for m in payload.get("models", []):
                mid = normalize_model_id(m)
                if mid and mid not in models_map:
                    models_map[mid] = m
        except KeyError as e:
            logging.error(f"KeyError in aggregate_all while processing models: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in aggregate_all while processing models: {e}")

    # align indexes
    all_ids = sorted(set(data_map.keys()) | set(models_map.keys()))
    aligned_data = [data_map.get(mid, {"id": mid}) for mid in all_ids]
    aligned_models = [models_map.get(mid, {"model": mid, "name": mid}) for mid in all_ids]

    return {
        "models": aligned_models,
        "data": aligned_data,
    }


class OneShotHandler(BaseHTTPRequestHandler):
    mappings: str
    skip_mapping: list[str]
    mapping_timeout: int

    # collect all unique backend URLs from all mapping files
    def get_urls(self) -> set[str]:
        return {
            u
            for file_name in os.listdir(self.mappings)
            if file_name.endswith((".yml", ".yaml"))
               and
               not any(re.search(pattern, file_name) for pattern in self.skip_mapping)
            for u in urls_from_mapping(os.path.join(self.mappings, file_name))
        }

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return

        urls = self.get_urls()

        result = aggregate_all(urls, self.mapping_timeout)
        body = json.dumps(result).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate /v1/models from all Traefik backends.")
    parser.add_argument("--mappings",
                        default="/etc/traefik/mappings",
                        help="Directory containing Traefik mapping files")
    parser.add_argument("--host",
                        default="127.0.0.1",
                        help="Host to bind the HTTP server to (e.g. 127.0.0.1)")
    parser.add_argument("--port",
                        type=int,
                        default=9080,
                        help="Port to listen on (e.g. 9080)")
    parser.add_argument("--skip-mapping",
                        action='append',
                        default=["all-models.yml"],
                        help="YAML filenames to skip (regex patterns, e.g. all-models.yml)")
    parser.add_argument("--mapping-timeout",
                        type=int,
                        default=2,
                        help="Timeout in seconds for a request to a mapping")
    parser.add_argument("--log-level",
                        default="WARNING",
                        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    args = parser.parse_args()

    # Configure logging
    configure_logging(args.log_level)

    # Set class attributes on OneShotHandler so instances can access them
    OneShotHandler.mappings = args.mappings
    OneShotHandler.skip_mapping = args.skip_mapping
    OneShotHandler.mapping_timeout = args.mapping_timeout

    httpd = HTTPServer((args.host, args.port), OneShotHandler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
