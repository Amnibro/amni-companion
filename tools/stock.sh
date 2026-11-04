#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
tools/character.sh holo art/holo_17.png female 1.7
tools/character.sh dex art/engineer_27.png male 1.8
echo "review sheets: .stock/review/"
