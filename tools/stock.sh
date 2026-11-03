#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
G=art/.mosaic/assets/gen
FACE=1 HAIR=1 tools/character.sh holo $G/holo/high.glb $G/holo/cutout.png female 1.7
tools/character.sh dex $G/dex/high.glb $G/dex/cutout.png male 1.8
rmdir .stock 2>/dev/null || true
