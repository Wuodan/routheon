"""System statistics helper."""

from __future__ import annotations

import logging
import platform
import time
from typing import Dict, List

import psutil


def get_system_stats() -> Dict[str, object]:
    """Collect system statistics including CPU, memory, disk usage, and system info."""

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

