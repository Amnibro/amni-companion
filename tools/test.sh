#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../core"
H=${HELIUM:-$HOME/ai/amni-lang/helium-gold}
out=$(mktemp -d "${XDG_RUNTIME_DIR:-/tmp}/companion-test.XXXXXX")
trap 'rm -rf "$out"' EXIT
fail=0
for g in *_test.gold; do
  t=${g%.gold}
  HC_LIB=$H/hc/lib "$H/build/hc" build "$t.amni" -o "$out/$t" >/dev/null
  sed -n '/^expect:$/,$p' "$g" | tail -n +2 > "$out/$t.want"
  if "$out/$t" | diff -u "$out/$t.want" - > "$out/$t.diff"; then echo "pass $t"; else echo "FAIL $t"; cat "$out/$t.diff"; fail=1; fi
done
HC_LIB=$H/hc/lib "$H/build/hc" companion.amni ../web/companion.wasm --web >/dev/null
echo "wasm $(stat -c%s ../web/companion.wasm) bytes"
exit $fail
