#!/usr/bin/env bash
set -euo pipefail
mkdir -p results/ibex-hermes-wasm/browser results/ibex-hermes-wasm/diagnostics
git -C .hermes-source rev-parse HEAD > results/ibex-hermes-wasm/diagnostics/hermes-commit.txt
emcc --version | head -n 2 > results/ibex-hermes-wasm/diagnostics/emscripten.txt

# Upstream Hermes requires a host compiler before compiling its VM with Emscripten.
cmake -S .hermes-source -B .hermes-host -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DHERMES_ENABLE_TEST_SUITE=OFF -DHERMES_ENABLE_NAPI=OFF
cmake --build .hermes-host --target hermesc hermes --parallel 2
test -x .hermes-host/bin/hermesc
test -f .hermes-host/ImportHostCompilers.cmake

# Compile the entire Hermes VM to Wasm: NOT "JS-to-Wasm" Static Hermes.
# Browser fetches bytecode into MEMFS, so NODERAWFS is deliberately disabled.
flags="-sMODULARIZE=1 -sEXPORT_NAME=CreateHermesVM -sENVIRONMENT=web,node"
flags="$flags -sEXPORTED_RUNTIME_METHODS=FS,callMain -sINVOKE_RUN=0"
flags="$flags -sFORCE_FILESYSTEM=1 -sALLOW_MEMORY_GROWTH=1 -sSTACK_SIZE=262144 -sEXIT_RUNTIME=1"
emcmake cmake -S .hermes-source -B .hermes-wasm -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DIMPORT_HOST_COMPILERS="$(pwd)/.hermes-host/ImportHostCompilers.cmake" \
  -DHERMES_ENABLE_TEST_SUITE=OFF -DHERMES_ENABLE_NAPI=OFF \
  -DHAVE_SYS_IOCTL_H=0 -DCMAKE_EXE_LINKER_FLAGS="$flags"
cmake --build .hermes-wasm --target hermes --parallel 2
test -s .hermes-wasm/bin/hermes.js
test -s .hermes-wasm/bin/hermes.wasm

# Both VM and compiler are built from Ibex2's pinned vanilla Hermes commit.
.hermes-host/bin/hermesc -O -emit-binary \
  -out results/ibex-hermes-wasm/browser/shared.hbc bench/hermes-ibex-wasm/shared.js
test -s results/ibex-hermes-wasm/browser/shared.hbc
cp .hermes-wasm/bin/hermes.js .hermes-wasm/bin/hermes.wasm results/ibex-hermes-wasm/browser/
cp bench/hermes-ibex-wasm/index.html results/ibex-hermes-wasm/browser/index.html
sha256sum results/ibex-hermes-wasm/browser/hermes.* \
  results/ibex-hermes-wasm/browser/shared.hbc \
  > results/ibex-hermes-wasm/diagnostics/sha256.txt

node bench/hermes-ibex-wasm/node-smoke.cjs \
  2>&1 | tee results/ibex-hermes-wasm/diagnostics/node-wasm.log
grep -q 'HERMES_NODE_WASM_OK=479820' results/ibex-hermes-wasm/diagnostics/node-wasm.log

python3 -m http.server 8765 --bind 127.0.0.1 --directory results/ibex-hermes-wasm/browser \
  > results/ibex-hermes-wasm/diagnostics/http-server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8765/index.html >/dev/null; then break; fi
  sleep 1
done

chrome="$(command -v google-chrome || command -v chromium || true)"
test -n "$chrome" || { echo 'Chrome missing' >&2; exit 1; }
timeout 120s "$chrome" --headless=new --no-sandbox --disable-gpu \
  --disable-dev-shm-usage --virtual-time-budget=30000 \
  --dump-dom http://127.0.0.1:8765/index.html \
  > results/ibex-hermes-wasm/diagnostics/browser-dom.txt \
  2> results/ibex-hermes-wasm/diagnostics/browser-stderr.txt
grep -q 'PASS HERMES_SHARED_OK=479820' results/ibex-hermes-wasm/diagnostics/browser-dom.txt
echo HERMES_BROWSER_VM_HBC_PASS | tee results/ibex-hermes-wasm/diagnostics/status.txt
