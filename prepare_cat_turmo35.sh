#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
IN="${1:-picture.png}"
OUT="${2:-prepared_cat_320x480.png}"
python turmo_lite.py --image "$IN" --pink-bg --green-to-bg --red-to-blue --force-black --fit contain --dry-run "$OUT"
printf 'Saved %s
' "$OUT"
