#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
G=art/.mosaic/assets/gen
for id in holo dex; do
  PYTHONPATH=${MOSAIC:-$HOME/ai/mosaic} python3 -c "import json,sys;from mosaic import assets as a;g=next(x for x in json.load(open('art/gen.json')) if x['id']=='$id');r=a.art_build('$id','.stock',src='$G/$id/high.glb',kind='humanoid',desc=g['desc'],source='ai-gen',tris=70000,size=2048,height=g['height'],ref=g['image'],project='$G/$id/cutout.png');sys.exit(0 if r.get('ok') else print(r) or 1)"
  .venv/bin/python tools/reskin.py --graft .stock/assets/gen/$id/$id.glb .stock/assets/gen/$id/$id.glb web/models/$id.glb
done
rm -rf .stock
