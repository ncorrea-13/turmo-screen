#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
PORT="${1:-/dev/ttyACM0}"
BAUD="${2:-4000000}"
for S in 160 200 240 280 300 320 360 400 480; do
  echo
  echo "=== STRIDE $S ==="
  python turmo_stride_probe.py --port "$PORT" --baud "$BAUD" --stride "$S"
  echo "Посмотри на экран: если вертикальные линии ПРЯМЫЕ и не заворачиваются — это правильный stride."
  echo "Нажми Enter для следующего теста..."
  read -r _
done
