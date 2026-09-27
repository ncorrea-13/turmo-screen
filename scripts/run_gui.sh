#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
  echo "No .venv found. Run ./install.sh first."
  exit 1
fi
source .venv/bin/activate
exec python turmo_gui.py "$@"
