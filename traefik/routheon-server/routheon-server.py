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
import platform
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Dict, Any, Optional

import psutil
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


def get_system_stats() -> Dict[str, Any]:
    """
    Collect system statistics including CPU, memory, disk usage, and system info.
    Returns a dictionary with all the metrics.
    """
    try:
        # System information
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # Memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk information (root partition)
        disk = psutil.disk_usage('/')
        
        # Network information
        net_io = psutil.net_io_counters()
        
        # Process count
        process_count = len(psutil.pids())
        
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "hostname": platform.node(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "uptime_seconds": int(uptime),
                "uptime_human": f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m"
            },
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "load_average": {
                    "1min": round(load_avg[0], 2),
                    "5min": round(load_avg[1], 2),
                    "15min": round(load_avg[2], 2)
                },
                "core_count": cpu_count,
                "core_count_logical": psutil.cpu_count(logical=True)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": round(memory.percent, 2),
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.free / (1024**3), 2)
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": round(swap.percent, 2),
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2)
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": round(disk.percent, 2),
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2)
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            },
            "processes": {
                "count": process_count
            }
        }
    except Exception as e:
        logging.error(f"Error collecting system stats: {e}")
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": f"Failed to collect system stats: {str(e)}"
        }


def aggregate_all(urls: set[str], mapping_timeout: int) -> Dict[str, Any]:
    """
    1. read all traefik mapping files
    2. call /v1/models on each backend in parallel
    3. merge all results:
       data_map[id]   (from .data[].id)
       models_map[id] (from .models[].model / .name)
    4. align indices and return one flat JSON
    """

    data_map = {}
    models_map = {}

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_models_payload, u, mapping_timeout): u for u in urls}
        for future in futures:
            u = futures[future]
            try:
                payload = future.result()
            except Exception as e:
                logging.error(f"Error fetching models from {u}: {e}")
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
                logging.error(f"KeyError in aggregate_all while processing data from {u}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in aggregate_all while processing data from {u}: {e}")

            # merge models[]
            try:
                for m in payload.get("models", []):
                    mid = normalize_model_id(m)
                    if mid and mid not in models_map:
                        models_map[mid] = m
            except KeyError as e:
                logging.error(f"KeyError in aggregate_all while processing models from {u}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in aggregate_all while processing models from {u}: {e}")

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
        if self.path == "/v1/models":
            urls = self.get_urls()
            result = aggregate_all(urls, self.mapping_timeout)
            body = json.dumps(result).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/stats":
            result = get_system_stats()
            body = json.dumps(result, indent=2).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
            return


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
                        default=["routheon-server.yml"],
                        help="YAML filenames to skip (regex patterns, e.g. routheon-server.yml)")
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
