#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 4 ] || { echo "usage: tools/character.sh <id> <concept.png> <female|male> <height-m> [out.glb] [--back back.png]"; exit 2; }
id=$1 img=$2 body=$3 hgt=$4;shift 4;out=web/models/$id.glb;[ $# -gt 0 ] && [ "$1" != --back ] && { out=$1;shift; }
${PY:-.venv/bin/python} tools/image3d.py "$img" "$body" "$hgt" "$out" "$@"
rm -rf .stock/img3d;mkdir -p .stock/review;node tools/review.mjs "$out" ".stock/review/$id.png"
