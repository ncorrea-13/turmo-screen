#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
IMG="${1:-picture.png}"
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --pixel-format rgb565le \
  --image "$IMG" --pink-bg --green-to-bg --red-to-blue --force-black --fit contain --safe-margin 25 --once "${@:2}"
