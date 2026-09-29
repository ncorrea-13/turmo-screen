"""System metrics collection used by the default dashboard renderer."""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Optional

try:
    import psutil
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: psutil. Install with: pip install -r requirements.txt") from exc

from .models import Metrics

_last_net = None
_last_net_time = None

def first_cpu_temp() -> Optional[float]:
    try:
        temps = psutil.sensors_temperatures(fahrenheit=False)
    except Exception:
        return None
    for entries in temps.values():
        for item in entries:
            if item.current is not None:
                return float(item.current)
    return None

def nvidia_stats() -> tuple[Optional[float], Optional[float]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=0.5,
        )
    except Exception:
        return None, None
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if not line:
        return None, None
    parts = [p.strip() for p in line.split(",")]
    try:
        return float(parts[0]), float(parts[1])
    except Exception:
        return None, None

def collect_metrics() -> Metrics:
    global _last_net, _last_net_time
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    cpu_temp = first_cpu_temp()
    gpu, gpu_temp = nvidia_stats()

    now = time.time()
    net = psutil.net_io_counters()
    if _last_net is None or _last_net_time is None:
        up = down = 0.0
    else:
        dt = max(0.001, now - _last_net_time)
        up = max(0.0, (net.bytes_sent - _last_net.bytes_sent) / 1024 / dt)
        down = max(0.0, (net.bytes_recv - _last_net.bytes_recv) / 1024 / dt)
    _last_net = net
    _last_net_time = now

    return Metrics(cpu, ram, disk, cpu_temp, gpu, gpu_temp, up, down)

def fetch_fleet_hosts(hub: Optional[str] = None, token: Optional[str] = None, wait: str = "400ms") -> list[dict]:
    """Read-only snapshot of a Heimdall fleet via heimdall-cli. Empty list on any failure."""
    hub = hub or os.environ.get("HEIMDALL_HUB", "localhost:9090")
    token = token if token is not None else os.environ.get("HEIMDALL_TOKEN")
    cmd = ["heimdall-cli", "--hub", hub, "--wait", wait, "hosts"]
    env = {**os.environ, "HEIMDALL_TOKEN": token} if token else None
    try:
        result = subprocess.run(cmd, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=3.0)
    except Exception:
        return []
    try:
        hosts = json.loads(result.stdout) if result.stdout.strip() else []
    except Exception:
        return []
    return hosts if isinstance(hosts, list) else []

def remember_hosts(hosts: list[dict]) -> list[dict]:
    """Persist every host id ever seen; ids missing from `hosts` come back as offline placeholders."""
    path = os.environ.get("TURMO_FLEET_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "turmo", "fleet.json")
    try:
        with open(path) as f:
            known = set(json.load(f))
    except Exception:
        known = set()
    seen = {h["id"] for h in hosts if "id" in h}
    if not seen <= known:
        known |= seen
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(sorted(known), f)
        except OSError:
            pass  # cache is best-effort; fleet still renders
    return hosts + [{"id": i, "state": "offline", "metrics": {}} for i in sorted(known - seen)]
