#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../core"
H=${HELIUM:-$HOME/ai/amni-lang/helium-gold}
command -v gold >/dev/null && { (cd cv && for m in qm rig motion sense talk; do gold build $m.gold; done); gold pack companion "$PWD" lang=amni main=companion.amni; gold build companion.gold; }
HC_LIB=$H/hc/lib "$H/build/hc" companion.amni ../web/companion.wasm --web && rm -f ../web/helium.js
echo "web/companion.wasm $(stat -c%s ../web/companion.wasm) bytes"
V=${HELIUM_VIEW:-$HOME/ai/amni-lang/helium-webgpu}
[ -x "$V/build/hc" ] && { command -v gold >/dev/null && GOLD_HELIUM=$V gold build view.gold; HC_LIB=$V/hc/lib "$V/build/hc" build --web view.amni -o ../web/heview/view.wasm && echo "web/heview/view.wasm $(stat -c%s ../web/heview/view.wasm) bytes"; }
