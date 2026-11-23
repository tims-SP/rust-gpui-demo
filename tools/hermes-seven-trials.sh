#!/usr/bin/env bash
set -euo pipefail
mkdir -p results/perf
echo '{"runner":"ubuntu-24.04","architecture":"x86_64","frameworks":["svelte","solid"],"trials":7}' > results/perf/plan.json
uname -a > results/perf/uname.txt
lscpu > results/perf/lscpu.txt
ibex=".ibex-source/target/release/ibex2"
test -x "$ibex"
for f in svelte solid; do
  mkdir -p "results/perf/work/$f"
  cp "dist/$f.js" "results/perf/work/$f/app.js"
  "$ibex" build "results/perf/work/$f/app.js" --root "results/perf/work/$f" > "results/perf/$f-build.log" 2>&1
  # Independent module manifests prevent one framework overwriting the other.
  "$ibex" run "results/perf/work/$f/app.js" --root "results/perf/work/$f" --precompiled > "results/perf/$f-warmup.log" 2>&1
  grep -q "GPUI_SCENE_OK:$f" "results/perf/$f-warmup.log"
done
for i in $(seq 1 7); do
  if (( i % 2 == 0 )); then order="solid svelte"; else order="svelte solid"; fi
  for f in $order; do
    logfile="results/perf/$i-$f.log"
    /usr/bin/time -f 'PROCESS_SECONDS=%e\nPEAK_RSS_KIB=%M' \
      -o "results/perf/$i-$f.time" \
      "$ibex" run "results/perf/work/$f/app.js" --root "results/perf/work/$f" --precompiled > "$logfile" 2>&1
    grep -q '^BENCH_RESULT:' "$logfile"
    grep -q "GPUI_SCENE_OK:$f" "$logfile"
  done
done
python3 tools/hermes-perf-report.py
