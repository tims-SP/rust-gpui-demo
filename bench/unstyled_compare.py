import json
import statistics
from pathlib import Path

root = Path("results")
cases = {}
for framework in ("solid", "svelte"):
    baseline = [json.loads((root / f"{framework}-{i}.json").read_text()) for i in range(5)]
    static = [json.loads((root / f"{framework}-static-{i}.json").read_text()) for i in range(11, 14)]
    for sample in static:
        assert sample["testCase"] == "static"
        assert sample["visibleSongs"] == 48 and sample["screenshotDeviation"] > 0
        assert (root / sample["screenshot"].split("/")[-1]).exists()
        assert "theme" not in sample["phases"]
    cases[framework] = {"styled": baseline, "static": static}

scenarios = ("single", "offscreen", "reorder", "window")
details = {}
lines = [
    "# Removing authored CSS stylesheets and dynamic styles",
    "",
    "The control variants retain *fixed* layout and color inline styles so that their GPU-rendered windows remain visible.",
    "They have **no <style> blocks, class selectors, CSS variables or reactive style bindings**.",
    "Both retain identical 10,000-song backing data, 48 visible rows, keys and update operations.",
    "Theme changes are intentionally omitted: theme with no consumers is an invalid workload.",
    "Five styled baseline processes vs three static-style processes, interleaved across the same Linux runner.",
    "",
    "| Framework | Workload | Styled median ms | Static-style median ms | Change | Styled mutations | Static mutations |",
    "|---|---|---:|---:|---:|---:|---:|",
]
for framework, variant in cases.items():
    details[framework] = {}
    for name in scenarios:
        a = [p["phases"][name] for p in variant["styled"]]
        b = [p["phases"][name] for p in variant["static"]]
        assert all(p["iterations"] == a[0]["iterations"] for p in a+b)
        if name == "offscreen":
            assert all(p["mutations"] == 0 for p in b)
        else:
            assert all(p["mutations"] > 0 for p in b)
        ma = statistics.median(p["elapsedMs"] for p in a)
        mb = statistics.median(p["elapsedMs"] for p in b)
        mutations_a = statistics.median(p["mutations"] for p in a)
        mutations_b = statistics.median(p["mutations"] for p in b)
        change = round((mb / ma - 1) * 100, 1) if ma else None
        details[framework][name] = {
            "styledMedianMs": round(ma, 4), "staticMedianMs": round(mb, 4),
            "changePct": change, "styledMutations": mutations_a, "staticMutations": mutations_b,
            "staticRuns": b,
        }
        lines.append(
            f"| {framework} | {name} | {ma:.3f} | {mb:.3f} | {change:+.1f}% | {mutations_a:g} | {mutations_b:g} |"
        )
lines += [
    "", "Negative change means fewer milliseconds (faster).",
    "Retained fixed styles preserve meaningful UI output. The completely unstyled zero-style attempt rendered a blank image and was rejected.",
    "Static style parsing on native mount is still possible. This test isolates removal of CSS stylesheets/dynamic style wiring, not a style-free native engine.",
    "These are JS/FFI timings with mutation instrumentation, not GPU frame-time measurements.",
]
(root / "UNSTYLED.json").write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n")
(root / "UNSTYLED.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
