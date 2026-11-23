#!/usr/bin/env python3
"""Verify Hermes-executed HBC mutations and export a Rust-readable trace.

Accepts only actual Hermes log files from Ibex2's --precompiled path.
"""
import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: parse-hermes-mutations.py FRAMEWORK LOG OUT")
    framework, logpath, outpath = sys.argv[1:]
    if framework not in ("svelte", "solid"):
        raise SystemExit("Unknown framework")
    lines = Path(logpath).read_text().splitlines()
    def records(prefix):
        return [json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    results = records("BENCH_RESULT:")
    batches = records("HERMES_MUTATION_BATCH:")
    if len(results) != 1 or len(batches) != 7:
        raise SystemExit(f"Hermes missing result or batches: {framework}, results={len(results)}, batches={len(batches)}")
    if "GPUI_SCENE_OK:" + framework not in lines:
        raise SystemExit("Missing executed Hermes parity marker")
    result = results[0]
    assert result["framework"] == framework
    assert result["final"] == dict(count=256, start=40, theme="light", renderedRows=48)
    assert all(isinstance(b, list) and b for b in batches)
    assert all(isinstance(m, list) for b in batches for m in b)
    operations = sum(map(len, batches))
    expected = result["initMutations"] + result["mutations"]
    if operations != expected:
        raise SystemExit(f"HBC mutation mismatch {framework}: {operations} vs {expected}")
    Path(outpath).write_text(json.dumps({
        "framework": framework,
        "operations": operations,
        "scene": result["scene"],
        "batches": batches,
        "engine": "actual-native-ibex2-hermes-hbc-not-v8",
    }))
    print(f"HERMES_NATIVE_HBC_MUTATION_TRACE_PASS:{framework}:{operations}:{len(batches)}")

if __name__ == "__main__":
    main()
