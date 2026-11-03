#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 5 ] || { echo "usage: [FACE=1] [HAIR=1] [RIG=rigged.glb] tools/character.sh <id> <trellis.glb> <concept.png> <female|male> <height-m> [out.glb]"; exit 2; }
id=$1 src=$2 art=$3 body=$4 h=$5 out=${6:-web/models/$1.glb} T=.stock/$1 py=${PY:-.venv/bin/python}
mkdir -p "$T"
[ -n "${RIG:-}" ] || PYTHONPATH=${MOSAIC:-$HOME/ai/mosaic} ${MPY:-python3} -c "import sys;from mosaic import assets as a;r=a.art_build('$id','$T',src='$src',kind='humanoid',desc='$id',source='ai-gen',tris=70000,size=2048,height=$h);sys.exit(0 if r.get('ok') else print(r) or 1)" || { echo "Mosaic art_build is needed for decimation and the auto-rig; or pass RIG=<rigged glb of the same mesh>"; exit 1; }
b=${RIG:-$T/assets/gen/$id/$id.glb}
$py tools/reskin.py --graft "$b" "$b" "$out" art/proportions_$body.json
[ "${FACE:-0}" != 1 ] || { node tools/marks.mjs "$out" "$T/marks.json"; $py tools/reskin.py --face "$out" "$T/marks.json" art/face_$body.npz; }
[ "${HAIR:-0}" != 1 ] || $py tools/reskin.py --hairback "$out"
$py tools/reskin.py --rebake "$out" "$b" "$src" "$art"
rm -rf "$T"
