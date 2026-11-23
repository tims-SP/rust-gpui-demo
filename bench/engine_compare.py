import json
import statistics
from pathlib import Path

root = Path("results")
variants = ("svelte-cli", "svelte-dev", "svelte-prod", "solid")
frameworks = {"svelte-cli": "svelte", "svelte-dev": "svelte", "svelte-prod": "svelte", "solid": "solid"}
scenarios = ("single", "theme", "offscreen", "reorder", "window")
samples = {}
for name in variants:
    sample = []
    for trial in range(4):
        file = root / f"{frameworks[name]}-{name}-{trial}.json"
        assert file.exists(), f"Missing real native benchmark {file}"
        data = json.loads(file.read_text())
        assert data["framework"] == frameworks[name] and data["testCase"] == name and data["trial"] == trial
        assert data["platform"] == "linux" and data["visibleSongs"] == 48
        assert data["runtime"]["versions"]["bun"] == "1.4.5", (name, data["runtime"])
        assert data["runtime"]["bunVersion"] == "1.4.5"
        assert data["screenshotDeviation"] > 0
        assert (root / f"{frameworks[name]}-{name}-{trial}.png").stat().st_size > 500
        for phase in scenarios:
            stats = data["phases"][phase]
            if phase == "offscreen":
                assert stats["mutations"] == stats["batches"] == 0
            else:
                assert stats["mutations"] > 0 and stats["batches"] > 0
        sample.append(data)
    samples[name] = sample

details = {}
lines = ["# JavaScript engine / Svelte development-mode isolation", "",
    "4 separate native GPUIX window processes per variant; execution order alternated.",
    "All cases must report the same Bun 1.4.5 JavaScriptCore runtime via `process.versions.bun`.",
    "",
    "| Variant | Bun runtime | JS execPath | Single ×120 ms | Theme ×24 ms | Reorder ×24 ms | Window ×120 ms |",
    "|---|---|---|---:|---:|---:|---:|"]
for name, runs in samples.items():
    p = runs[0]["runtime"]
    assert all(x["runtime"]["execPath"] == p["execPath"] for x in runs), name
    details[name] = {"runtime": p, "runs": []}
    for run in runs:
        details[name]["runs"].append({"trial": run["trial"], "phases": run["phases"], "runtime": run["runtime"]})
    m = lambda phase: round(statistics.median(x["phases"][phase]["elapsedMs"] for x in runs), 4)
    lines.append(f"| {name} | {p['versions']['bun']} | `{p['execPath']}` | {m('single')} | {m('theme')} | {m('reorder')} | {m('window')} |")

for phase in scenarios:
    ref = [x["phases"][phase]["mutations"] for x in samples["svelte-cli"]]
    for variant in ("svelte-dev", "svelte-prod"):
        got = [x["phases"][phase]["mutations"] for x in samples[variant]]
        assert got == ref, f"Native mutation volume differs for {variant}/{phase}: {got} != {ref}"

lines += ["", "**Method:** `svelte-cli` launches via `bunx gpuix-svelte --bun` (CLI explicitly adds development condition); `svelte-dev` uses direct Bun + custom-renderer + development; `svelte-prod` uses same direct Bun loader without development; `solid` uses the existing Bun JSX plugin.",
    "Each run checks actual Rust retained tree, order, native mutations and nonblank X11 screenshot.",
    "Startup/compiler time is excluded from timed update loops; differences reflect evaluated code, runtime scheduling or adapter behavior, not build startup.",
    "This is **not** a controlled hardware GPU frame benchmark.",
]
(root / "ENGINE.json").write_text(json.dumps(details, indent=2) + "\n")
(root / "ENGINE.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
