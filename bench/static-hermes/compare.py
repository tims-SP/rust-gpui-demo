#!/usr/bin/env python3
"""Validate identical JS semantics and report eight engine modes incl precompiled QuickJS-NG."""
import json
from pathlib import Path
from statistics import median

ROOT = Path("results/static-hermes")
ENGINES = (
    "bun-jsc",
    "node-v8",
    "spidermonkey-115",
    "quickjs-2021",
    "quickjs-ng-source",
    "quickjs-ng-bytecode",
    "hermes-bytecode",
    "static-hermes-native",
)
SCENARIOS = (
    "numeric",
    "keyed_reorder",
    "proxied_visible_window",
    "scoped_css_substitution",
)
TRIALS = 3
samples = {}
for engine in ENGINES:
    rows = []
    for trial in range(TRIALS):
        path = ROOT / f"{engine}-{trial}.json"
        assert path.is_file(), f"Missing benchmark: {path}"
        rec = json.loads(path.read_text())
        assert (rec["engine"], rec["trial"]) == (engine, trial)
        assert rec["workload"] == "gpui-inspired-pure-js-not-native-ui"
        assert [case["name"] for case in rec["cases"]] == list(SCENARIOS)
        assert all(case["elapsedMs"] >= 0 and case["rounds"] > 0 for case in rec["cases"])
        rows.append(rec)
    samples[engine] = rows

def field(run, scenario):
    return next(c for c in run["cases"] if c["name"] == scenario)

def signature(run, scenario):
    c = field(run, scenario)
    return (c["name"], c["rounds"], c["checksum"])

for scenario in SCENARIOS:
    expected = signature(samples["bun-jsc"][0], scenario)
    for engine in ENGINES:
        for rec in samples[engine]:
            actual = signature(rec, scenario)
            assert actual == expected, (
                f"JS checksum mismatch: {engine}/{scenario}: {actual} != {expected}"
            )

medians = {}
for scenario in SCENARIOS:
    medians[scenario] = {
        eng: median(field(run, scenario)["elapsedMs"] for run in samples[eng])
        for eng in ENGINES
    }

rows = [
    "# Eight-mode Linux x86-64 JavaScript kernel comparison", "",
    "All 24 independent processes successfully executed the same JS workload.",
    "Each process uses two untimed warm-up invocations per kernel; all output checksums match.",
    "Bun 1.4.5 uses JavaScriptCore; Node 24.22.2 uses V8; Ubuntu 24.04 packages",
    "provide SpiderMonkey 115 and QuickJS 2021. QuickJS-NG has source and verified",
    "precompiled bytecode modes; Hermes bytecode and native AOT are",
    "built from the same pinned upstream source commit (shermes produces ELF machine code).",
    "Measurements use in-JS Date.now() millisecond resolution and three-process medians.",
    "Older SpiderMonkey and QuickJS versions are reference points, not current-engine rankings.",
    "No actual GPUIX native UI, Rust FFI, or GPU frames are included.", "",
    "| Kernel (lower is better) | Bun / JSC | Node / V8 | SpiderMonkey 115 | QuickJS 2021 | QuickJS-NG source | QuickJS-NG bytecode | Hermes bytecode | Static Hermes native | Native / Node | Native / Bun |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for scenario, x in medians.items():
    bun = x["bun-jsc"]
    node = x["node-v8"]
    native = x["static-hermes-native"]
    parts = [x[e] for e in ENGINES]
    rows.append(
        f"| {scenario} | " +
        " | ".join(f"{v:.1f}" for v in parts) +
        f" | {native / node if node else float('nan'):.2f}x | {native / bun if bun else float('nan'):.2f}x |"
    )
rows += [
    "", "Interpretation: compares sampled *untyped* JS execution throughput only.",
    "Do not extrapolate to soundly typed Static Hermes, Node-API interop, start-up,",
    "end-to-end GPUIX/Svelte/Solid native updates, or actual device workloads.",
    "Engine startup and memory are captured as per-process resource files, not",
    "used to claim comparable production memory footprints.",
]
(ROOT / "REPORT.md").write_text("\n".join(rows) + "\n")
(ROOT / "REPORT.json").write_text(json.dumps(
    {"engines": ENGINES, "trials": TRIALS, "medians_ms": medians,
     "samples": samples}, indent=2) + "\n")
print("\n".join(rows))
