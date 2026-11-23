#!/usr/bin/env bash
set -euo pipefail
mkdir -p results/ibex-hermes-wasm/browser results/ibex-hermes-wasm/diagnostics
git -C .hermes-source rev-parse HEAD > results/ibex-hermes-wasm/diagnostics/hermes-commit.txt
emcc --version | head -n 2 > results/ibex-hermes-wasm/diagnostics/emscripten.txt

# Upstream Hermes requires a host compiler before compiling its VM with Emscripten.
cmake -S .hermes-source -B .hermes-host -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DHERMES_ENABLE_TEST_SUITE=OFF -DHERMES_ENABLE_NAPI=OFF
cmake --build .hermes-host --target hermesc --parallel 2
test -x .hermes-host/bin/hermesc
test -f .hermes-host/ImportHostCompilers.cmake

# Compile Hermes VM to Wasm, *not* the CLI (whose teardown aborts under Emscripten).
# Keep the host compiler from the identical version for the generated HBC.
emcmake cmake -S .hermes-source -B .hermes-wasm -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DIMPORT_HOST_COMPILERS="$(pwd)/.hermes-host/ImportHostCompilers.cmake" \
  -DHERMES_ENABLE_TEST_SUITE=OFF -DHERMES_ENABLE_NAPI=OFF \
  -DHAVE_SYS_IOCTL_H=0
cmake --build .hermes-wasm --target hermesvm_a jsi --parallel 2
test -s .hermes-wasm/lib/libhermesvm_a.a
test -s .hermes-wasm/jsi/libjsi.a

# A minimal C++ JSI embedding host; no Hermes CLI main() / exit().
# It holds the VM while a browser page evaluates native Hermes HBC.
em++ -std=c++17 -O2 -DNDEBUG -fno-exceptions -fno-rtti \
  -I.hermes-source/include -I.hermes-source/API -I.hermes-source/API/jsi \
  -I.hermes-wasm/lib/config -I.hermes-wasm/include \
  bench/hermes-ibex-wasm/hermes-web-host.cpp \
  .hermes-wasm/lib/libhermesvm_a.a .hermes-wasm/jsi/libjsi.a \
  -o results/ibex-hermes-wasm/browser/hermes.js \
  --no-entry -sMODULARIZE=1 -sEXPORT_NAME=CreateHermesVM \
  -sENVIRONMENT=web,node \
  -sEXPORTED_FUNCTIONS=_hermes_run_hbc_file,_malloc,_free \
  -sEXPORTED_RUNTIME_METHODS=FS,ccall \
  -sFORCE_FILESYSTEM=1 -sALLOW_MEMORY_GROWTH=1 \
  -sSTACK_SIZE=262144 -sASSERTIONS=1
test -s results/ibex-hermes-wasm/browser/hermes.js
test -s results/ibex-hermes-wasm/browser/hermes.wasm

# Both VM and compiler are built from Ibex2's pinned vanilla Hermes commit.
.hermes-host/bin/hermesc -O -emit-binary \
  -out results/ibex-hermes-wasm/browser/shared.hbc bench/hermes-ibex-wasm/shared.js
test -s results/ibex-hermes-wasm/browser/shared.hbc
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
python3 bench/hermes-ibex-wasm/verify-browser.py results/ibex-hermes-wasm/diagnostics/browser-dom.txt
echo HERMES_BROWSER_VM_HBC_PASS | tee results/ibex-hermes-wasm/diagnostics/status.txt
