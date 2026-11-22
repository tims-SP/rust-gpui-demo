import json
import statistics
from pathlib import Path

root = Path("results")
trials = range(5)
results = {}
for framework in ("solid", "svelte"):
    reports = []
    for trial in trials:
        path = root / f"{framework}-{trial}.json"
        assert path.exists(), f"Missing native run {path}"
        r = json.loads(path.read_text())
        assert r["framework"] == framework and r["trial"] == trial
        assert r["platform"] == "linux" and r["rows"] == 48 and r["datasetRows"] == 10000
        assert r["visibleSongs"] == 48 and r["screenshotDeviation"] > 0
        assert (root / f"{framework}-{trial}.png").stat().st_size > 500
        reports.append(r)
    results[framework] = reports

scenarios = ("single", "theme", "reorder", "window")
table = []
for scenario in scenarios:
    cases = {}
    for framework, reports in results.items():
        phases = [r["phases"][scenario] for r in reports]
        assert len({p["iterations"] for p in phases}) == 1
        assert all(p["batches"] > 0 and p["mutations"] > 0 for p in phases)
        med = lambda key: round(statistics.median(p[key] for p in phases), 4)
        cases[framework] = {
            "iterations": phases[0]["iterations"],
            "elapsedMsMedian": med("elapsedMs"),
            "elapsedMsMin": min(p["elapsedMs"] for p in phases),
            "elapsedMsMax": max(p["elapsedMs"] for p in phases),
            "p95MsMedian": med("p95Ms"),
            "mutationsMedian": med("mutations"),
            "bytesMedian": med("bytes"),
            "allTrials": phases,
        }
    assert cases["solid"]["iterations"] == cases["svelte"]["iterations"]
    table.append({"scenario": scenario, **cases})

summary = {
    "status": "passed",
    "runsPerFramework": len(trials),
    "platform": "Linux Xvfb + Mesa llvmpipe software Vulkan",
    "renderer": "GPUIX native 0.11.0",
    "dataset": 10000,
    "visible": 48,
    "results": table,
    "limitations": [
        "Software Vulkan is not a hardware GPU benchmark.",
        "5 independent processes help expose noise but do not equal hardware-controlled confidence intervals.",
        "Measurements include instrumented mutation JSON parsing and synchronous FFI, not native frame time.",
        "Window scenario uses 48-row application windowing over 10000 data records, not GPUI native virtual-list.",
        "Svelte CSS variable/theme versus Solid inline reactive style is an end-to-end strategy comparison.",
        "Custom Rust ArtworkFlow component and Android/iOS are not covered."
    ]
}
(root / "comparison.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
lines = [
    "# Svelte vs Solid — 5 independent Linux native-window runs",
    "",
    "Environment: Ubuntu 24.04, Bun 1.4.5, GPUIX 0.11, Xvfb + Mesa software Vulkan",
    "",
    "| Scenario | Updates | Solid median ms | Svelte median ms | Solid median P95 (ms/op) | Svelte median P95 | Solid median mutation | Svelte median mutation |",
    "|---|---:|---:|---:|---:|---:|---:|---:|"
]
for case in table:
    a, b = case["solid"], case["svelte"]
    lines.append(
        f"| {case['scenario']} | {a['iterations']} | {a['elapsedMsMedian']} | "
        f"{b['elapsedMsMedian']} | {a['p95MsMedian']} | {b['p95MsMedian']} | "
        f"{a['mutationsMedian']} | {b['mutationsMedian']} |"
    )
lines += [
    "",
    "Each figure is a median of **5 independent Linux processes**, not a single run.",
    "See comparison.json for all samples, per-operation details and RSS/heap from individual JSON files.",
    "Source data is a 10,000-song dataset with a 48-row visible window (not GPUI's native virtual-list).",
    "Pass requires nonzero mutations, live GPUI tree/order checks, and non-blank X11 screenshots for **all** 10 runs.",
    "This is a JS + FFI comparison with sampling overhead, not a GPU hardware performance ranking.",
]
(root / "SUMMARY.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines), flush=True)
