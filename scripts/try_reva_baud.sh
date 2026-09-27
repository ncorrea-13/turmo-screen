#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
for B in 115200 921600 2000000 4000000; do
  echo "=== baud $B ==="
  python turmo_lite.py --protocol reva --port /dev/ttyACM0 --baud "$B" --width 320 --height 480 --test-pattern --pixel-format rgb565le --clear --once
  read -r -p "Press Enter for next baud..." _
done
