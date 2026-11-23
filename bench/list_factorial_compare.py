import json
import statistics
from pathlib import Path

root = Path("results")
variants = ("scoped", "raw-order", "indexed-window", "raw", "solid")
results = {}
for name in variants:
    fw = "solid" if name == "solid" else "svelte"
    records = []
    for trial in range(4):
        file = root / f"{fw}-{name}-{trial}.json"
        assert file.is_file(), f"Missing {file}"
        x = json.loads(file.read_text())
        assert x["framework"] == fw and x["trial"] == trial and x["testCase"] == name
        assert x["runtime"]["versions"]["bun"] == "1.4.5"
        assert x["visibleSongs"] == 48 and x["screenshotDeviation"] > 0
        assert Path(x["screenshot"]).stat().st_size > 500
        records.append(x)
    results[name] = records

scenes = ("single", "theme", "offscreen", "reorder", "window")
median = lambda values: round(statistics.median(values), 4)
summary = {}
for name, records in results.items():
    summary[name] = {}
    for scene in scenes:
        phases = [r["phases"][scene] for r in records]
        if scene == "offscreen":
            assert all(p["mutations"] == 0 for p in phases)
        else:
            assert all(p["mutations"] > 0 for p in phases)
        summary[name][scene] = {
            "ms": median(p["elapsedMs"] for p in phases),
            "mutations": median(p["mutations"] for p in phases),
            "samplesMs": [p["elapsedMs"] for p in phases],
            "operations": phases[0]["iterations"]
        }
for scene in scenes:
    baseline = summary["scoped"][scene]["mutations"]
    for name in ("raw-order", "indexed-window", "raw"):
        assert summary[name][scene]["mutations"] == baseline, f"Mutation count differs: {scene}/{name}"

report = {
    "frameworkAndNative": "Svelte5 & GPUIX 0.11, Bun 1.4.5, Ubuntu 24.04",
    "warmup": "512 themes, 192 keyed rotations, 240 window shifts",
    "factors": {
      "scoped": {"rawOrder": False, "indexedWindow": False},
      "raw-order": {"rawOrder": True, "indexedWindow": False},
      "indexed-window": {"rawOrder": False, "indexedWindow": True},
      "raw": {"rawOrder": True, "indexedWindow": True}
    },
    "result": summary
}
(root / "LIST_FACTORIAL.json").write_text(json.dumps(report, indent=2) + "\n")
lines = ["# Svelte raw-order vs indexed-window factorial experiment", "",
    "Four independent pre-warmed Linux native GPUIX processes per variant; same 10k dataset and 48 rows.",
    "No changes to authored CSS, Native backend, rendered text, insertion or mutation count.",
    "",
    "| Variant | Single ×120 ms | Theme ×24 ms | Reorder ×24 ms | Window ×120 ms | Reorder mutations | Window mutations |",
    "|---|---:|---:|---:|---:|---:|---:|"]
for name in variants:
    d = summary[name]
    lines.append(
      f"| {name} | {d['single']['ms']} | {d['theme']['ms']} | "
      f"{d['reorder']['ms']} | {d['window']['ms']} | "
      f"{d['reorder']['mutations']:g} | {d['window']['mutations']:g} |"
    )
for scene in ("reorder", "window"):
    b = summary["scoped"][scene]["ms"]
    lines.append("")
    lines.append(f"**{scene} ablation:**")
    for name in ("raw-order","indexed-window","raw"):
        v = summary[name][scene]["ms"]
        lines.append(f"- {name}: {(v/b - 1)*100:+.1f}% relative to original baseline")
lines.extend(["",
    "This ablation changes JavaScript state access only. Profiling flags are disabled; timings still include the normal Mutation probe.",
    "Native ordering and nonempty screenshot are verified by each process. Percentages are across medians of 4 processes, not confidence intervals.",
    "No GPU frame times are measured."])
(root / "LIST_FACTORIAL.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
