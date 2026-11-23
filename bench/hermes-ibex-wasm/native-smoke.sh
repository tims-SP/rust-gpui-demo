#!/usr/bin/env bash
set -euo pipefail

mkdir -p results/ibex-hermes-wasm/native
cp bench/hermes-ibex-wasm/shared.js .ibex-source/shared.js
git -C .ibex-source rev-parse HEAD > results/ibex-hermes-wasm/native/ibex-commit.txt

# Real Ibex2 Rust engine host, not an independent Hermes CLI substitute.
cargo build --manifest-path .ibex-source/Cargo.toml --locked --release \
  -p ibex2-runtime --bin ibex2
test -x .ibex-source/target/release/ibex2

# Ibex2 precompiles its module graph with an engine-matched compiler.
.ibex-source/target/release/ibex2 build .ibex-source/shared.js \
  --root .ibex-source > results/ibex-hermes-wasm/native/build.log 2>&1
find .ibex-source/.ibex2/cache -type f -size +0c \
  > results/ibex-hermes-wasm/native/cache-files.txt
test -s results/ibex-hermes-wasm/native/cache-files.txt

.ibex-source/target/release/ibex2 run .ibex-source/shared.js \
  --root .ibex-source --precompiled \
  > results/ibex-hermes-wasm/native/run.log 2>&1
grep -q 'HERMES_SHARED_OK=479820' results/ibex-hermes-wasm/native/run.log
echo 'IBEX2_NATIVE_PRECOMPILED_PASS' | tee results/ibex-hermes-wasm/native/status.txt
cat results/ibex-hermes-wasm/native/run.log
