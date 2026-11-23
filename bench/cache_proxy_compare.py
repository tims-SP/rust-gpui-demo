import json
import statistics
from pathlib import Path

root = Path("results")
variants = {"scoped": "svelte", "global": "svelte", "raw": "svelte", "solid": "solid"}
scenarios = ("single", "theme", "offscreen", "reorder", "window")
runs = {}
for variant, framework in variants.items():
    group = []
    for trial in range(4):
        filename = root / f"{framework}-{variant}-{trial}.json"
        assert filename.exists(), f"Missing real GPUI benchmark {filename}"
        run = json.loads(filename.read_text())
        assert run["trial"] == trial and run["framework"] == framework
        assert run["runtime"]["versions"]["bun"] == "1.4.5"
        assert run["visibleSongs"] == 48 and run["screenshotDeviation"] > 0
        assert (root / run["screenshot"]).exists()
        for scenario in scenarios:
            stats = run["phases"][scenario]
            if scenario == "offscreen":
                assert stats["mutations"] == 0
            else:
                assert stats["mutations"] > 0
        group.append(run)
    runs[variant] = group
median = lambda values: round(statistics.median(values), 4)
summary = {
    "source": "Ubuntu 24.04, Bun 1.4.5, same GPUIX 0.11 native addon, four independent processes per variant",
    "variants": {},
}
lines = ["# Svelte CSS variable cache and deep-proxy array isolation", "",
    "Production Svelte 0.6 custom renderer without development condition; Solid 1.9 as a reference.",
    "Each process prewarms 512 theme changes, 192 rotations, and 240 window shifts before measurement.",
    "",
    "| Variant | Single ×120 | Theme ×24 | Reorder ×24 | Window ×120 | Theme mutations | Window mutations |",
    "|---|---:|---:|---:|---:|---:|---:|"]
for variant, group in runs.items():
    values = {scene: {
        "medianMs": median([r["phases"][scene]["elapsedMs"] for r in group]),
        "medianMutations": median([r["phases"][scene]["mutations"] for r in group]),
        "samples": [r["phases"][scene] for r in group],
    } for scene in scenarios}
    summary["variants"][variant] = values
    lines.append(f"| {variant} | {values['single']['medianMs']} | {values['theme']['medianMs']} | {values['reorder']['medianMs']} | {values['window']['medianMs']} | {values['theme']['medianMutations']} | {values['window']['medianMutations']} |")
g = summary["variants"]["global"]["theme"]["medianMs"]
s = summary["variants"]["scoped"]["theme"]["medianMs"]
rr = summary["variants"]["raw"]["reorder"]["medianMs"]
rb = summary["variants"]["scoped"]["reorder"]["medianMs"]
rw = summary["variants"]["raw"]["window"]["medianMs"]
sw = summary["variants"]["scoped"]["window"]["medianMs"]
lines += [
    "", f"Global set_css_vars theme vs scoped inline variable: {(g / s - 1) * 100:+.1f}% (negative is faster)",
    f"Raw order array + proxy-free window slice vs scoped baseline: rotation {(rr / rb - 1) * 100:+.1f}%, window {(rw / sw - 1) * 100:+.1f}%",
    "", "The global var is not equivalent to per-component/multiwindow variable isolation; it tests rule-style cache feasibility in a single-window app.",
    "SvelteRawList preserves deep-proxy tracks for title reactivity but avoids proxied order and array slicing when updating the visible window.",
    "Native mutation counts and window order must still pass. These are CPU/FFI update-loop timings, not hardware GPU frame times.",
]
(root / "CACHE_PROXY.json").write_text(json.dumps(summary, indent=2) + "\n")
(root / "CACHE_PROXY.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
