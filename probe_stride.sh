#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
STRIDE="${1:-320}"
PORT="${2:-/dev/ttyACM0}"
python turmo_stride_probe.py --port "$PORT" --baud 4000000 --stride "$STRIDE"
