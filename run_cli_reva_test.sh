#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
python turmo_lite.py --protocol reva --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --pixel-format rgb565le --test-pattern --once
