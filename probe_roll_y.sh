#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
sudo chmod a+rw /dev/ttyACM0 2>/dev/null || true
for y in 0 -48 -96 -120 -144 -192 48 96 120 144 192; do
  echo "=== roll-y $y ==="
  python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --test-pattern --pixel-format rgb565le --roll-y "$y" --once
  read -p "Enter = next, Ctrl+C = stop" _
done
