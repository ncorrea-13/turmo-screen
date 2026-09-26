#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --test-pattern --pixel-format rgb565le --once "$@"
