#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
IN="${1:-picture.png}"
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --pixel-format rgbx   --image "$IN" --pink-bg --green-to-bg --red-to-blue --force-black --fit contain --clear --reset-before-frame --once
