#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
B=${AMNI_SCIENT:-$HOME/ai/Amni-Scient}/tools/build-characters.py
[ -f "$B" ] || { echo "needs the Amni-CAD character builder: set AMNI_SCIENT to an Amni-Scient checkout"; exit 2; }
${PY:-.venv/bin/python} -I "$B" web/models art/holo.json art/dex.json
mkdir -p .stock/review;for id in holo dex;do node tools/review.mjs web/models/$id.glb .stock/review/$id.png;done
echo "review sheets: .stock/review/"
