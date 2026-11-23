#!/usr/bin/env python3
"""Verify checksums for identical kernel source; compare pre-warmed in-program durations."""
import json
from pathlib import Path
from statistics import median

p = Path("results/static-hermes")
engines = ("bun-jsc", "hermes-bytecode", "static-hermes-native")
scenarios = ("numeric", "keyed_reorder", "proxied_visible_window", "scoped_css_substitution")
samples = {}
for engine in engines:
    rows = []
    for trial in range(3):
        f = p / f"{engine}-{trial}.json"
        assert f.is_file(), f"Missing test result {f}"
        rec = json.loads(f.read_text())
        assert rec["engine"] == engine and rec["trial"] == trial
        assert rec["workload"] == "gpui-inspired-pure-js-not-native-ui"
        assert [x["name"] for x in rec["cases"]] == list(scenarios)
        for case in rec["cases"]:
            assert case["elapsedMs"] >= 0 and case["rounds"] > 0
        rows.append(rec)
    samples[engine] = rows
for scenario in scenarios:
    ref = {(x["name"], x["rounds"], x["checksum"]) for x in samples["bun-jsc"][0]["cases"] if x["name"] == scenario}
    for engine in engines:
        for run in samples[engine]:
            v = {(x["name"], x["rounds"], x["checksum"]) for x in run["cases"] if x["name"] == scenario}
            assert v == ref, f"JS semantics mismatch for {engine}/{scenario}: {v} != {ref}"

def field(run, scenario):
    return next(x for x in run["cases"] if x["name"] == scenario)

rows = [
    "# Static Hermes REAL machine-code benchmark (Linux x86-64)", "",
    "Three independent processes per engine, same unchanged JS source, with two untimed warm-up loops.",
    "The shermes program is compiled with `shermes -O -o` to an ELF executable.",
    "The bytecode comparison is emitted by the *same checkout* of Hermes and run under its `hermes` CLI.",
    "The Bun reference uses JavaScriptCore. No native GPUI window or Node-API bridge is exercised.",
    "Measurements are `Date.now()` within JS, with millisecond resolution; very small timings are noisy.",
    "Each engine produces **matching deterministic checksums** in all cases.", "",
    "| JS kernel | Bun/JSC ms | Hermes bytecode ms | Static Hermes native ms | Native / Bun | Native / bytecode |",
    "|---|---:|---:|---:|---:|---:|",
]
for scene in scenarios:
    values = {eng: median(field(x, scene)["elapsedMs"] for x in samples[eng]) for eng in engines}
    b, h, s = (values[eng] for eng in engines)
    rows.append(f"| {scene} | {b:.1f} | {h:.1f} | {s:.1f} | {s / b if b else float('nan'):.2f}× | {s / h if h else float('nan'):.2f}× |")
rows += [
    "", "Scope restriction: ordinary untyped JS AOT machine code, **not** Static Hermes soundly typed Flow code.",
    "Static Hermes does not provide the hermes-node Node-API runtime automatically; this benchmark cannot determine actual GPUIX window or FFI performance.",
    "To prove a GPUIX result, an explicit Node-API/JSI embedding layer or equivalent host is required and must be evaluated separately.",
]
(p / "REPORT.md").write_text("\n".join(rows) + "\n")
(p / "REPORT.json").write_text(json.dumps(samples, indent=2) + "\n")
print("\n".join(rows))
