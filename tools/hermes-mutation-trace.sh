#!/usr/bin/env bash
# Execute ACTUAL precompiled HBC through Ibex2 Hermes, exporting the same
# JSON Mutation payload that the real native host/JSI would receive.
set -euo pipefail
ibex=".ibex-source/target/release/ibex2"
test -x "$ibex"
mkdir -p results/hermes-mutations
for f in svelte solid; do
  source="results/hermes-mutations/$f.js"
  {
    printf '%s\n' '// Captures actual Hermes UI mutation transport. Never run under Node/V8.'
    printf '%s\n' 'globalThis.gpuiEmit = function(json) { console.log("HERMES_MUTATION_BATCH:" + json); };'
    cat "dist/$f.js"
  } > "$source"
  "$ibex" build "$source" --root . > "results/hermes-mutations/$f-build.log" 2>&1
  "$ibex" run "$source" --root . --precompiled > "results/hermes-mutations/$f-run.log" 2>&1
  python3 tools/parse-hermes-mutations.py "$f" \
    "results/hermes-mutations/$f-run.log" "results/hermes-mutations/$f.json"
  cargo run --manifest-path crates/ui-mutation/Cargo.toml --bin verify-trace -- \
    "results/hermes-mutations/$f.json"
done
echo HERMES_NATIVE_HBC_RUST_MUTATION_PARITY_PASS
