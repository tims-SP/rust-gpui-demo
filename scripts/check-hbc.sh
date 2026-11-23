#!/usr/bin/env bash
set -euo pipefail
mkdir -p results/hermes
test -x .hermes-host/bin/hermesc
test -x .hermes-host/bin/hermes
for framework in svelte solid; do
  { cat scripts/hermes-prelude.js; printf 'globalThis.__framework="%s";\n' "$framework"; cat "dist/$framework.js" scripts/hermes-check.js; } > "results/hermes/$framework.js"
  .hermes-host/bin/hermesc -O -emit-binary -out "results/hermes/$framework.hbc" "results/hermes/$framework.js"
  test -s "results/hermes/$framework.hbc"
  .hermes-host/bin/hermes -b "results/hermes/$framework.hbc" | tee "results/hermes/$framework.log"
  grep -Fq "HERMES_HBC_CUSTOM_RENDERER_PASS=$framework" "results/hermes/$framework.log"
done
sha256sum results/hermes/*.hbc > results/hermes/sha256.txt
echo HERMES_TWO_FRAMEWORKS_HBC_PASS
