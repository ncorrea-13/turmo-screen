#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
python turmo_lite.py --protocol reva --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --pixel-format rgb565le --safe-margin 10
