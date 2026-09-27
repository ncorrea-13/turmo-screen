#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ $# -lt 1 ]; then
  echo "Usage: ./play_gif_cli.sh file.gif"
  exit 1
fi
if [ -d .venv ]; then
  source .venv/bin/activate
fi
python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --protocol reva --width 320 --height 480 --pixel-format rgb565le \
  --gif "$1" --gif-loop --gif-fps 8
