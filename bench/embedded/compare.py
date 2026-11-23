#!/usr/bin/env python3
"""Collect same-source benchmark timings and peak memory; validate exact JS results."""
import json
import sys
from pathlib import Path
from statistics import median

cases = ("numeric", "keyed_reorder", "proxied_visible_window", "scoped_css_substitution")
root = Path("results/embedded")

def collect(kind, engine, trial):
    prefix = root / kind / f"{engine}-{trial}"
    lines = prefix.with_suffix(".log").read_text().splitlines()
    matches = [line.split("STATIC_HERMES_KERNEL=", 1)[1]
               for line in lines if line.startswith("STATIC_HERMES_KERNEL=")]
    assert len(matches) == 1, f"Missing or ambiguous result: {prefix}"
    data = json.loads(matches[0])
    assert data["workload"] == "gpui-inspired-pure-js-not-native-ui"
    assert [x["name"] for x in data["cases"]] == list(cases)
    resources = dict(line.strip().split("=", 1)
                     for line in prefix.with_suffix(".resources.txt").read_text().splitlines()
                     if "=" in line)
    data.update(engine=engine, trial=int(trial),
                max_rss_kib=int(resources["max_rss_kib"]),
                wall_seconds=float(resources["wall_seconds"]))
    prefix.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n")

def compare(kind):
    assert kind in ("primjs", "escargot")
    modes = ("bun-jsc", "primjs-source", "primjs-bytecode") if kind == "primjs" else (
        "bun-jsc", "escargot-source", "escargot-cached-source")
    samples = {}
    for engine in modes:
        samples[engine] = [json.loads((root / kind / f"{engine}-{trial}.json").read_text())
                           for trial in range(3)]
    expected = tuple((x["name"], x["rounds"], x["checksum"])
                     for x in samples["bun-jsc"][0]["cases"])
    for mode, runs in samples.items():
        for trial, run in enumerate(runs):
            assert run["engine"] == mode and run["trial"] == trial
            got = tuple((x["name"], x["rounds"], x["checksum"]) for x in run["cases"])
            assert got == expected, f"JS semantics mismatch: {mode}/{trial}"
            assert all(x["elapsedMs"] >= 0 for x in run["cases"])
            assert run["max_rss_kib"] > 0 and run["wall_seconds"] >= 0
    rows = [
        f"# {kind} benchmark — validated Linux JS execution", "",
        "Same JS source, three independent processes per mode;",
        "all numeric checksums and iteration counts verified.",
        "In-program time: Date.now() millisecond resolution after JS warmup.",
        "Resource: /usr/bin/time process peak RSS KiB; not JS heap or leak.",
        "Measurements are three-trial medians, not confidence intervals.", "",
        "| Case | " + " | ".join(modes) + " |",
        "|---|" + "---:|" * len(modes),
    ]
    medians = {}
    for case in cases:
        medians[case] = {mode: median(next(x["elapsedMs"] for x in run["cases"]
                                           if x["name"] == case) for run in samples[mode])
                         for mode in modes}
        rows.append("| " + case + " | " +
                    " | ".join(str(medians[case][mode]) for mode in modes) + " |")
    rows += ["", "| Resource | " + " | ".join(modes) + " |",
             "|---|" + "---:|" * len(modes)]
    for key, label in (("wall_seconds", "Wall seconds"), ("max_rss_kib", "Peak RSS KiB")):
        rows.append("| " + label + " | " +
                    " | ".join(str(median(run[key] for run in samples[mode])) for mode in modes) + " |")
    if kind == "primjs":
        rows += ["", "Precompiled mode loads an independent disk bytecode file in a",
                 "fresh process without taking the JavaScript source path.",
                 "Linux x86-64 does not enable PrimJS ARM64 template interpreter."]
    else:
        rows += ["", "Escargot cached-source mode has separately verified disk cache",
                 "store and fresh-process HIT. The identical source must still",
                 "be supplied for cache lookup. THIS IS NOT SOURCE-FREE BYTECODE",
                 "and cannot be treated as an independent bytecode executable."]
    rows += ["", "Scope: pure JS kernels, not GPUIX native windows or Rust FFI."]
    (root / kind / "REPORT.md").write_text("\n".join(rows) + "\n")
    (root / kind / "REPORT.json").write_text(json.dumps(
        {"kind": kind, "modes": modes, "trials": 3, "medians_ms": medians,
         "samples": samples}, indent=2) + "\n")
    print("\n".join(rows))

if __name__ == "__main__":
    if sys.argv[1] == "collect":
        collect(*sys.argv[2:])
    elif sys.argv[1] == "compare":
        compare(sys.argv[2])
    else:
        raise SystemExit("Usage: compare.py collect KIND MODE TRIAL | compare KIND")
