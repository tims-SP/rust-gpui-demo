#!/usr/bin/env bash
set -euo pipefail
kind="$1"
root="results/embedded/$kind"
mkdir -p "$root"

if [[ "$kind" == primjs ]]; then
  git -C .primjs-src rev-parse HEAD > "$root/upstream-sha.txt"
  python3 bench/embedded/patch_primjs.py
  cmake -S .primjs-src -B .primjs-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DENABLE_UNITTESTS=ON -DENABLE_PRIMJS_SNAPSHOT=OFF
  cmake --build .primjs-build --target qjs --parallel 2
  test -x .primjs-build/qjs
  cp bench/static-hermes/kernels.js "$root/compiler-input.js"
  .primjs-build/qjs --emit-bytecode "$root/compiler-input.js" "$root/kernel.primjs.bc" \
    > "$root/compile.log" 2>&1
  grep -q '^PRIMJS_BYTECODE_COMPILED=' "$root/compile.log"
  test -s "$root/kernel.primjs.bc"
  mv "$root/compiler-input.js" "$root/compiler-input.js.removed"
  .primjs-build/qjs --run-bytecode "$root/kernel.primjs.bc" > "$root/load-proof.log" 2>&1
  grep -q '^PRIMJS_BYTECODE_LOADED=' "$root/load-proof.log"
  grep -q '^STATIC_HERMES_KERNEL=' "$root/load-proof.log"
  sha256sum "$root/kernel.primjs.bc" > "$root/bytecode-sha256.txt"
  cat "$root/load-proof.log"
  modes="bun-jsc primjs-source primjs-bytecode"
elif [[ "$kind" == escargot ]]; then
  git -C .escargot-src rev-parse HEAD > "$root/upstream-sha.txt"
  python3 bench/embedded/patch_escargot.py
  cmake -S .escargot-src -B .escargot-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DESCARGOT_ENABLE_SHELL=ON -DESCARGOT_CODE_CACHE=ON
  cmake --build .escargot-build --target escargot --parallel 2
  test -x .escargot-build/escargot
  export ESCARGOT_BENCH_CACHE_DIR="$(pwd)/$root/cache"
  mkdir -p "$ESCARGOT_BENCH_CACHE_DIR"
  .escargot-build/escargot bench/static-hermes/kernels.js > "$root/cache-store.log" 2>&1
  grep -q '^ESCARGOT_BENCH_CACHE_STORE' "$root/cache-store.log"
  find "$ESCARGOT_BENCH_CACHE_DIR" -type f -size +0c > "$root/cache-files.txt"
  test -s "$root/cache-files.txt"
  .escargot-build/escargot bench/static-hermes/kernels.js > "$root/cache-hit.log" 2>&1
  grep -q '^ESCARGOT_BENCH_CACHE_HIT' "$root/cache-hit.log"
  grep -q '^STATIC_HERMES_KERNEL=' "$root/cache-hit.log"
  cat "$root/cache-hit.log"
  modes="bun-jsc escargot-source escargot-cached-source"
else
  echo "unknown engine: $kind" >&2
  exit 2
fi

for trial in 0 1 2; do
  for engine in $modes; do
    prefix="$root/$engine-$trial"
    case "$engine" in
      bun-jsc) cmd=(bun bench/static-hermes/kernels.js);;
      primjs-source) cmd=(.primjs-build/qjs bench/static-hermes/kernels.js);;
      primjs-bytecode) cmd=(.primjs-build/qjs --run-bytecode "$root/kernel.primjs.bc");;
      escargot-source|escargot-cached-source) cmd=(.escargot-build/escargot bench/static-hermes/kernels.js);;
    esac
    if [[ "$engine" == escargot-cached-source ]]; then
      export ESCARGOT_BENCH_CACHE_DIR="$(pwd)/results/embedded/escargot/cache"
    else
      unset ESCARGOT_BENCH_CACHE_DIR || true
    fi
    /usr/bin/time -f 'wall_seconds=%e\nmax_rss_kib=%M' \
      -o "$prefix.resources.txt" timeout 150s "${cmd[@]}" > "$prefix.log" 2>&1
    if [[ "$engine" == escargot-cached-source ]]; then
      grep -q '^ESCARGOT_BENCH_CACHE_HIT' "$prefix.log"
    fi
    python3 bench/embedded/compare.py collect "$kind" "$engine" "$trial"
  done
done
python3 bench/embedded/compare.py compare "$kind"
cat "$root/REPORT.md" >> "$GITHUB_STEP_SUMMARY"
