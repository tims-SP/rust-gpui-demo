#!/usr/bin/env bash
set -euo pipefail
engine="${1:?engine bun/hermes}"
framework="${2:?solid/svelte}"
trial="${3:?trial}"
export BENCH_ENGINE="$engine" BENCH_TRIAL="$trial"
export NODE_PATH="$PWD/node_modules"
out="results/$engine-$framework-$trial"
mkdir -p results
case "$engine" in
  hermes)
    launch=("${HERMES_NODE:?hermes-node path missing}" "--no-compile-cache" "dist/engines/$framework.cjs")
    ;;
  hermes-opt)
    launch=("${HERMES_NODE:?hermes-node path missing}" "--no-compile-cache" "--optimize=on" "dist/engines/$framework.cjs")
    ;;
  hermes-aot)
    launch=("${HERMES_NODE:?hermes-node path missing}" "--bundle=dist/engines/$framework.bundle")
    ;;
  bun)
    launch=(bun "dist/engines/$framework.cjs")
    ;;
  *)
    echo "Unknown engine: $engine" >&2
    exit 2
    ;;
esac
"${launch[@]}" > "$out.log" 2>&1 &
pid=$!
ready=0
for i in $(seq 1 100); do
  if grep -q '^ENGINE_BENCH=' "$out.log"; then ready=1; break; fi
  if ! kill -0 "$pid" 2>/dev/null; then break; fi
  sleep 0.1
done
if (( ready == 0 )); then
  cat "$out.log"
  wait "$pid" || true
  echo "Native benchmark failed to reach report stage: $out" >&2
  exit 1
fi
import -window root "$out.png"
identify -format '%[standard-deviation]' "$out.png" > "$out.deviation"
wait "$pid"
cat "$out.log" | grep '^ENGINE_BENCH='
python3 - "$out" <<'PY'
import sys,json
from pathlib import Path
path=Path(sys.argv[1]); log=path.with_suffix('.log').read_text()
j=json.loads(next(line.split("ENGINE_BENCH=",1)[1] for line in log.splitlines() if line.startswith("ENGINE_BENCH=")))
d=float(path.with_suffix('.deviation').read_text())
assert d>0, f"Blank real Linux GPUI frame: {path}"
assert path.with_suffix('.png').stat().st_size>1000
assert j["visibleRows"]==48
assert j["phases"]["offscreen"]["mutations"]==0
path.with_suffix('.json').write_text(json.dumps({**j,"screenshotDeviation":d},indent=2)+"\n")
PY
