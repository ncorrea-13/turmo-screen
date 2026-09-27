#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ -d .venv ]; then
  source .venv/bin/activate
fi
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --protocol reva --width 320 --height 480 --pixel-format rgb565le \
  --gif assets/sample_spinner.gif --gif-loop --gif-fps 8
