#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
IMG="${1:-picture.png}"
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 480 --height 320 --pixel-format rgbx \
  --image "$IMG" --content-rotate 270 --pink-bg --green-to-bg --red-to-blue --force-black --fit contain --clear --reset-before-frame --once
