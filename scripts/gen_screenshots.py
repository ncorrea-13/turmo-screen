#!/usr/bin/env python3
"""Render README screenshots of the fleet dashboard from sample data (no hub, no screen needed).

Usage: python scripts/gen_screenshots.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from turmo.renderers import render_fleet_dashboard  # noqa: E402

OUT = ROOT / "pictures"
DAY = 86400


def host(name: str, state: str = "online", **m) -> dict:
    return {"id": name, "state": state, "metrics": m}


HEALTHY = [
    host("pi", **{"cpu.util": 12, "mem.used": 39, "disk.used": 34, "temp.pkg": 48, "cpu.load": 0.42, "net.latency": 18, "host.uptime": 17 * DAY}),
    host("nas", **{"cpu.util": 6, "mem.used": 51, "disk.used": 72, "temp.pkg": 41, "cpu.load": 0.20, "net.latency": 12, "host.uptime": 63 * DAY}),
    host("desktop", **{"cpu.util": 34, "mem.used": 58, "disk.used": 46, "temp.pkg": 55, "cpu.load": 1.90, "net.latency": 9, "host.uptime": 2 * DAY}),
    host("phone", **{"cpu.util": 27, "mem.used": 62, "disk.used": 34, "temp.pkg": 33, "cpu.load": 2.83, "net.latency": 41, "host.uptime": 17 * DAY}),
]

DEGRADED = [
    host("pi", **{"cpu.util": 12, "mem.used": 39, "disk.used": 34, "temp.pkg": 48, "cpu.load": 0.42, "net.latency": 18, "host.uptime": 17 * DAY}),
    host("nas", "stale", **{"cpu.util": 6, "mem.used": 51, "disk.used": 91, "temp.pkg": 41, "cpu.load": 0.20, "net.latency": 12, "host.uptime": 63 * DAY}),
    host("desktop", **{"cpu.util": 91, "mem.used": 88, "disk.used": 46, "temp.pkg": 78, "cpu.load": 7.90, "net.latency": 9, "host.uptime": 3600 * 2}),
    host("phone", "offline"),
]


def gradient(path: Path, w: int = 480, h: int = 320) -> None:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (40 + 120 * x // w, 60 + 80 * y // h, 200 - 120 * y // h)
    img.save(path)


def render(name: str, hosts: list[dict], w: int, h: int, bg: str | None = None) -> None:
    with patch("turmo.renderers.fetch_fleet_hosts", return_value=hosts):
        render_fleet_dashboard(w, h, bg_image=bg).save(OUT / name)
    print("wrote", OUT / name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        bg = Path(tmp) / "bg.png"
        gradient(bg)
        render("fleet-landscape.png", HEALTHY, 480, 320)
        render("fleet-degraded.png", DEGRADED, 480, 320)
        render("fleet-background.png", HEALTHY, 480, 320, str(bg))
        render("fleet-portrait.png", HEALTHY, 320, 480)


if __name__ == "__main__":
    main()
