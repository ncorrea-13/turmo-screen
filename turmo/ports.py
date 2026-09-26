"""Serial port discovery helpers."""

from __future__ import annotations

import glob
import os
from pathlib import Path

def find_candidate_ports() -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()

    for link in sorted(glob.glob("/dev/serial/by-id/*")):
        try:
            real = os.path.realpath(link)
        except OSError:
            continue
        label = Path(link).name
        if real not in seen:
            seen.add(real)
            candidates.append((real, label))

    for pattern in ["/dev/ttyACM*", "/dev/ttyUSB*", "/dev/ttyS*"]:
        for port in sorted(glob.glob(pattern)):
            if port not in seen:
                seen.add(port)
                candidates.append((port, "generic serial device"))

    return candidates

def print_ports() -> None:
    ports = find_candidate_ports()
    if not ports:
        print("No serial ports found. Check USB cable and: lsusb && ls -l /dev/ttyACM* /dev/ttyUSB* 2>&1")
        return
    print("Detected serial ports:")
    for port, label in ports:
        marker = ""
        low = f"{port} {label}".lower()
        if any(x in low for x in ["turmo", "usb35", "usbmonitor", "inchips", "1a86", "5722", "screen"]):
            marker = "  <-- likely TURMO"
        print(f"  {port:18s}  {label}{marker}")
