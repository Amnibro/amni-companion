#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../core"
H=${HELIUM:-$HOME/ai/amni-lang/helium-gold}
command -v gold >/dev/null && { (cd cv && for m in qm rig motion sense talk; do gold build $m.gold; done); gold pack companion "$PWD" lang=amni main=companion.amni; gold build companion.gold; }
HC_LIB=$H/hc/lib "$H/build/hc" companion.amni ../web/companion.wasm --web && rm -f ../web/helium.js
echo "web/companion.wasm $(stat -c%s ../web/companion.wasm) bytes"
