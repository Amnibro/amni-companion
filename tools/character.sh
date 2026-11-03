#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 4 ] || { echo "usage: tools/character.sh <id> <concept.png> <female|male> <height-m> [out.glb]"; exit 2; }
${PY:-.venv/bin/python} tools/image3d.py "$2" "$3" "$4" "${5:-web/models/$1.glb}"
rm -rf .stock/img3d
