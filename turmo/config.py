"""CLI/config parsing helpers."""

from __future__ import annotations

import argparse

def parse_bg(value: str) -> tuple[int, int, int]:
    value = value.strip().lower()
    named = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "gray": (32, 32, 32),
        "grey": (32, 32, 32),
    }
    if value in named:
        return named[value]
    if value.startswith("#") and len(value) == 7:
        return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    raise argparse.ArgumentTypeError("background must be black/white/gray or #RRGGBB")
