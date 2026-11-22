import json
import statistics
from pathlib import Path

r = Path("results")
scenarios = ("single", "theme", "offscreen", "reorder", "window")
variants = {
    "solid": [json.loads((r / f"solid-{i}.json").read_text()) for i in range(5)],
    "solid_ids": [json.loads((r / f"solid-ids-{i}.json").read_text()) for i in range(5, 8)],
    "svelte": [json.loads((r / f"svelte-{i}.json").read_text()) for i in range(5)],
    "svelte_inline": [json.loads((r / f"svelte-inline-{i}.json").read_text()) for i in range(5, 8)],
}
stats = {}
for name, items in variants.items():
    assert len(items) >= 3
    assert all(item["visibleSongs"] == 48 and item["screenshotDeviation"] > 0 for item in items)
    stats[name] = {}
    for scenario in scenarios:
        phases = [i["phases"][scenario] for i in items]
        calc = lambda k: round(statistics.median(p[k] for p in phases), 4)
        stats[name][scenario] = {k: calc(k) for k in (
            "elapsedMs", "updateMs", "settleMs", "probeMs", "nativeMs", "mutations", "bytes")}
        if scenario == "offscreen":
            assert all(p["mutations"] == 0 for p in phases)
        else:
            assert all(p["mutations"] > 0 for p in phases)
(r / "DIAGNOSIS.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n")
lines = ["# Root-cause isolation: adapter versus framework", "",
    "Totals are median of 5 baseline processes or 3 isolation processes. All units are ms except mutations/bytes.",
    "",
    "| Variant | Scenario | Total | Update | Flush+commit | Probe overhead | Native addon call | Mutations |",
    "|---|---|---:|---:|---:|---:|---:|---:|"]
for name, cases in stats.items():
    for scenario, v in cases.items():
        lines.append(f"| {name} | {scenario} | {v['elapsedMs']} | {v['updateMs']} | {v['settleMs']} | {v['probeMs']} | {v['nativeMs']} | {v['mutations']} |")
lines += [
    "", "solid_ids replaces <For each={visibleRows()}> with <For each={visible numeric IDs}>.",
    "svelte_inline replaces CSS variable/theme inheritance with a direct style:color directive.",
    "A controlled style experiment is still not a framework-only speed contest: the two templates also differ in style parsing and generated code.",
    "Live Linux GPUI windows, native automation tree assertions, and X11 screenshots are required for every variant.",
]
report = "\n".join(lines) + "\n"
(r / "DIAGNOSIS.md").write_text(report)
print(report)
