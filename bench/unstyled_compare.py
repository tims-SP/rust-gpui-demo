import json
import statistics
from pathlib import Path

root = Path("results")
cases = {}
for framework in ("solid", "svelte"):
    baseline = [json.loads((root / f"{framework}-{i}.json").read_text()) for i in range(5)]
    no_style = [json.loads((root / f"{framework}-nostyle-{i}.json").read_text()) for i in range(11, 14)]
    for sample in no_style:
        assert sample["testCase"] == "nostyle"
        assert sample["visibleSongs"] == 48 and sample["screenshotDeviation"] > 0
        assert (root / sample["screenshot"].split("/")[-1]).exists()
        assert "theme" not in sample["phases"]
    cases[framework] = {"withStyle": baseline, "noStyle": no_style}

scenarios = ("single", "offscreen", "reorder", "window")
details = {}
lines = [
    "# Impact of removing all component styles",
    "",
    "The unstyled variants have no `<style>`, classes, CSS custom properties, or host style props.",
    "Both retain identical data state, 48 visible rows, list keys and update operations.",
    "Theme changes are intentionally omitted: an unused theme variable has no visible work to perform.",
    "Five baseline processes and three no-style processes, interleaved across frameworks on the same runner.",
    "",
    "| Framework | Workload | Styled median ms | Unstyled median ms | Change | Styled mutations | Unstyled mutations |",
    "|---|---|---:|---:|---:|---:|---:|",
]
for framework, variant in cases.items():
    details[framework] = {}
    for name in scenarios:
        a = [p["phases"][name] for p in variant["withStyle"]]
        b = [p["phases"][name] for p in variant["noStyle"]]
        assert all(p["iterations"] == a[0]["iterations"] for p in a+b)
        assert all(p["mutations"] == 0 for p in b) if name == "offscreen" else all(p["mutations"] > 0 for p in b)
        ma = statistics.median(p["elapsedMs"] for p in a)
        mb = statistics.median(p["elapsedMs"] for p in b)
        mutations_a = statistics.median(p["mutations"] for p in a)
        mutations_b = statistics.median(p["mutations"] for p in b)
        change = round((mb / ma - 1) * 100, 1) if ma else None
        details[framework][name] = {
            "styledMedianMs": round(ma, 4), "unstyledMedianMs": round(mb, 4),
            "changePct": change, "styledMutations": mutations_a, "unstyledMutations": mutations_b,
            "unstyledRuns": b
        }
        lines.append(
            f"| {framework} | {name} | {ma:.3f} | {mb:.3f} | {change:+.1f}% | {mutations_a:g} | {mutations_b:g} |"
        )
lines += [
    "", "Negative change means fewer milliseconds (faster).",
    "Style removal can alter native layout, so this isolates framework/adapter update cost rather than proving pixel-equivalent user experience.",
    "The Svelte native renderer may still process empty style objects even with no authored CSS.",
    "The measurements include the existing per-batch JSON instrumentation and synchronous native calls; GPU frame time is not measured.",
]
(root / "UNSTYLED.json").write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n")
(root / "UNSTYLED.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
