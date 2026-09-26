#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 480 --height 320 --pixel-format rgbx --test-pattern --clear --reset-before-frame --once
