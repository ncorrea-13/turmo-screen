#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
sudo chmod a+rw /dev/ttyACM0 2>/dev/null || true
for p in 0 1 2 4 8 16 32 64 128 256 512 1024 2048 4096 8192 16384 30720; do
  echo "=== raw-tail-pixels $p ==="
  python turmo_lite.py --port /dev/ttyACM0 --baud 4000000 --width 320 --height 480 --test-pattern --pixel-format rgb565le --raw-tail-pixels "$p" --once
  read -p "Run same command again manually if you want to see drift. Enter = next" _
done
