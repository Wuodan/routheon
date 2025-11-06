"""System statistics helper."""

from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass
from typing import Dict, List, Mapping, MutableMapping, Optional, Set

import psutil
import yaml


StatsPayload = Dict[str, object]


@dataclass(slots=True, frozen=True)
class StatsFilter:
    """Defines which sections and fields should be omitted from /stats."""

    disabled_sections: Set[str]
    disabled_fields: Mapping[str, Set[str]]

    def apply(self, stats: StatsPayload) -> StatsPayload:
        filtered: MutableMapping[str, object] = {
            key: value
            for key, value in stats.items()
            if key not in self.disabled_sections
        }

        for section, fields in self.disabled_fields.items():
            section_payload = filtered.get(section)
            if isinstance(section_payload, dict):
                filtered[section] = {
                    key: value
                    for key, value in section_payload.items()
                    if key not in fields
                }
        return dict(filtered)


@dataclass(slots=True)
class StatsCollector:
    """Collects system stats and applies an optional filter."""

    stats_filter: Optional[StatsFilter] = None

    def collect(self) -> StatsPayload:
        stats = _collect_raw_stats()
        if self.stats_filter:
            return self.stats_filter.apply(stats)
        return stats


def _collect_raw_stats() -> StatsPayload:
    try:
        boot_time = psutil.boot_time()
        uptime: float = time.time() - boot_time

        cpu_percent: float = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)
        core_count_val = int(cpu_count) if cpu_count is not None else 0
        core_count_logical_val = (
            int(cpu_count_logical) if cpu_count_logical is not None else 0
        )
        load_avg: List[float] = (
            list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [0.0] * 3
        )

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        net_io = psutil.net_io_counters()
        process_count: int = len(psutil.pids())

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
                "uptime_human": (
                    f"{int(uptime // 86400)}d "
                    f"{int((uptime % 86400) // 3600)}h "
                    f"{int((uptime % 3600) // 60)}m"
                ),
            },
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "load_average": {
                    "1min": round(load_avg[0], 2),
                    "5min": round(load_avg[1], 2),
                    "15min": round(load_avg[2], 2),
                },
                "core_count": core_count_val,
                "core_count_logical": core_count_logical_val,
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
                "free_gb": round(memory.free / (1024**3), 2),
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": round(swap.percent, 2),
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2),
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": round(disk.percent, 2),
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
            },
            "processes": {"count": process_count},
        }
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Error collecting system stats: %s", exc)
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error": f"Failed to collect system stats: {exc}",
        }


def load_stats_filter(path: str) -> Optional[StatsFilter]:
    """Load stats filter configuration from YAML."""

    try:
        with open(path, encoding="utf-8") as file:
            raw_config = yaml.safe_load(file) or {}
    except FileNotFoundError:
        logging.warning("Stats config file not found: %s", path)
        return None
    except yaml.YAMLError as exc:
        logging.error("Failed to parse stats config file %s: %s", path, exc)
        return None
    except OSError as exc:
        logging.error("Error reading stats config file %s: %s", path, exc)
        return None

    disabled_sections = raw_config.get("disabled_sections", [])
    disabled_fields = raw_config.get("disabled_fields", {})

    if not isinstance(disabled_sections, list):
        logging.error("disabled_sections must be a list in %s", path)
        return None
    if not isinstance(disabled_fields, dict):
        logging.error("disabled_fields must be a mapping in %s", path)
        return None

    section_set: Set[str] = {str(item) for item in disabled_sections}
    field_map: Dict[str, Set[str]] = {}
    for section, fields in disabled_fields.items():
        if not isinstance(fields, list):
            logging.error(
                "disabled_fields.%s must be a list in %s", section, path
            )
            continue
        field_map[str(section)] = {str(field) for field in fields}

    if not section_set and not field_map:
        return None

    return StatsFilter(disabled_sections=section_set, disabled_fields=field_map)
