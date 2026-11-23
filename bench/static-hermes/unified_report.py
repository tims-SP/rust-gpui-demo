#!/usr/bin/env python3
"""One-runner same-source JS performance + memory; never combine independent CI runs."""
import json
from pathlib import Path
from statistics import median

ROOT = Path("results/static-hermes")
ENGINES = (
    "bun-jsc", "node-v8", "spidermonkey-115", "quickjs-2021",
    "quickjs-ng-source", "quickjs-ng-bytecode", "primjs-source",
    "primjs-bytecode", "escargot-source", "escargot-cached-source",
    "hermes-bytecode", "static-hermes-native",
)
CASES = (
    "numeric", "keyed_reorder", "proxied_visible_window",
    "scoped_css_substitution",
)
TRIALS = 5
samples = {}

def case(run, name):
    return next(item for item in run["cases"] if item["name"] == name)

def signature(run):
    return tuple((x["name"], x["rounds"], x["checksum"]) for x in run["cases"])

for engine in ENGINES:
    rows = []
    for trial in range(TRIALS):
        prefix = ROOT / f"{engine}-{trial}"
        path = prefix.with_suffix(".json")
        assert path.is_file(), f"Missing result: {path}"
        run = json.loads(path.read_text())
        assert run["engine"] == engine and run["trial"] == trial
        assert run["workload"] == "gpui-inspired-pure-js-not-native-ui"
        assert tuple(x["name"] for x in run["cases"]) == CASES
        assert all(x["rounds"] > 0 and x["elapsedMs"] >= 0 for x in run["cases"])
        metrics = {}
        for line in prefix.with_suffix(".resources.txt").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                metrics[k] = v.strip()
        run["max_rss_kib"] = int(metrics["max_rss_kib"])
        run["wall_seconds"] = float(metrics["wall_seconds"])
        assert run["max_rss_kib"] > 0 and run["wall_seconds"] >= 0
        rows.append(run)
    samples[engine] = rows

truth = signature(samples["bun-jsc"][0])
for engine, runs in samples.items():
    for run in runs:
        assert signature(run) == truth, f"Checksum mismatch: {engine} trial {run['trial']}"

# Revalidate the offline bytecode/cache claims independently of checksums.
assert (ROOT / "primjs.bc").stat().st_size > 0
assert "PRIMJS_BYTECODE_LOADED=" in (ROOT / "primjs-load-proof.log").read_text()
assert (ROOT / "quickjs-ng-raw.qbc").stat().st_size > 0
assert "ESCARGOT_BENCH_CACHE_HIT" in (ROOT / "escargot-cache-hit.log").read_text()
assert (ROOT / "kernels.hbc").stat().st_size > 0
assert (ROOT / "kernels-native").stat().st_size > 0

medians = {
    engine: {
        "cases_ms": {name: median(case(r, name)["elapsedMs"] for r in runs) for name in CASES},
        "rss_mib": median(r["max_rss_kib"] for r in runs) / 1024,
        "wall_s": median(r["wall_seconds"] for r in runs),
    }
    for engine, runs in samples.items()
}
lines = [
    "# Unified Linux x86-64 embedded JS comparison — same runner", "",
    f"**{len(ENGINES)} modes × {TRIALS} independent processes = {len(ENGINES)*TRIALS} valid runs**.",
    "One GitHub Actions Ubuntu 24.04 job: identical JS file, exact checksum",
    "verification, alternating execution order, two untimed warm-up invocations",
    "per case, five-process median. All engines share the same runner and host.",
    "In-JS Date.now() timing resolution 1 ms; lower is better.",
    "RSS is /usr/bin/time max resident set size (process KiB -> MiB),",
    "not JS heap; wall time includes entire process startup + work, not",
    "a standalone startup-latency measurement.", "",
    "| Engine / mode | Numeric ms | Reorder ms | Proxy ms | CSS ms | Wall s | Peak RSS MiB |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for engine in ENGINES:
    m = medians[engine]
    lines.append(
        f"| {engine} | " +
        " | ".join(f"{m['cases_ms'][c]:.1f}" for c in CASES) +
        f" | {m['wall_s']:.2f} | {m['rss_mib']:.1f} |"
    )
lines += [
    "", "## Relative time versus Bun / JSC (1.00x is same speed)",
    "| Engine / mode | Numeric | Reorder | Proxy | CSS |",
    "|---|---:|---:|---:|---:|",
]
ref = medians["bun-jsc"]["cases_ms"]
for engine in ENGINES:
    row = medians[engine]["cases_ms"]
    lines.append("| " + engine + " | " +
                 " | ".join(f"{row[c]/ref[c]:.2f}x" if ref[c] else "N/A" for c in CASES) + " |")
lines += [
    "", "## Offline artifact modes, not interchangeable",
    "- **QuickJS-NG bytecode:** independently built raw .qbc and standalone qjs executable with appended bytecode; independent launch.",
    "- **PrimJS bytecode:** independent disk bytecode file executed in a fresh process via test-only LEPUS_ReadObject adapter; its compiler-input JS file was deleted before the load proof.",
    "- **Hermes bytecode:** optimized HBC built and loaded by matching Hermes VM.",
    "- **Static Hermes:** native x86-64 ELF executable; *not* VM bytecode.",
    "- **Escargot:** persistent disk bytecode *cache hit* in new process,",
    "  **but still requires source at runtime**. Not source-free offline bytecode.",
    "- Bun/JSC, Node/V8 and SpiderMonkey are source-based comparisons here.",
    "", "Scope: ordinary untyped JS kernels. No GPUIX windows, Rust FFI,",
    "cross-platform behavior or soundly typed Flow Static Hermes tests.",
    "Same runner does not remove CPU frequency changes, runtime tiering,",
    "GC or scheduler variance. Five samples cannot establish tight confidence intervals.",
]
(ROOT / "UNIFIED_REPORT.md").write_text("\n".join(lines) + "\n")
(ROOT / "UNIFIED_REPORT.json").write_text(
    json.dumps({"runner": "one ubuntu-24.04 GitHub Actions job",
                "engines": ENGINES, "trials": TRIALS,
                "medians": medians, "samples": samples}, indent=2) + "\n"
)
print("\n".join(lines))
