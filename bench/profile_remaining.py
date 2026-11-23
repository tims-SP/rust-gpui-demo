import json
import statistics
from pathlib import Path

root = Path("results")
variants = ("scoped", "raw")
scenes = ("single", "theme", "reorder", "window")
def kind(path):
    s = path.replace("\\\\", "/").lower()
    if "/svelte/src/internal/" in s or "/svelte/internal/" in s or "/node_modules/svelte/" in s:
        return "Svelte core"
    if "/gpuix-svelte/" in s:
        if s.endswith("/style.js") or s.endswith("/style.ts"): return "gpuix-svelte style"
        if s.endswith("/renderer.js") or s.endswith("/renderer.ts"): return "gpuix-svelte shadow host"
        # Svelte 5 is bundled by the adapter: pinned svelte internal source maps land here.
        if s.rsplit("/",1)[-1] in ("proxy.js","each.js","runtime.js","effects.js","batch.js",
                                   "render.js","deriveds.js","sources.js","dom.js","block.js"):
            return "Svelte core"
        return "gpuix-svelte other"
    if "/solid-js/" in s: return "Solid core"
    if "/bench/" in s: return "benchmark/app"
    if "node:" in s or "bun:" in s or "jsc" in s: return "runtime/builtin"
    return "other/no URL"

data = {}
for variant in variants:
    items = []
    for trial in (41, 42, 43):
        profile_trial = trial + (10 if variant == "raw" else 0)
        cases = {}
        for scene in scenes:
            file = root / f"hotpath-svelte-{scene}-{profile_trial}.json"
            assert file.exists(), file
            result = json.loads(file.read_text())
            assert result["framework"] == "svelte" and result["scenario"] == scene
            assert result["runtime"]["bun"] == "1.4.5"
            stack = result["cpu"]["stackTraces"]
            sources = {v["sourceID"]: v.get("url", v.get("sourceURL", "")) for v in stack["sources"]}
            counts = {}
            functions = {}
            valid = 0
            for item in stack["traces"]:
                frames = item.get("frames", [])
                if not frames: continue
                frame = frames[0]
                source = frame.get("sourceURL") or sources.get(frame["sourceID"], "")
                category = kind(source)
                counts[category] = counts.get(category, 0) + 1
                key = category + " :: " + frame.get("name","?") + " :: " + source.rsplit("/",1)[-1]
                functions[key] = functions.get(key,0) + 1
                valid += 1
            assert valid > 40, f"Too few CPU samples in {file}: {valid}"
            cases[scene] = {
                "sampleCount": valid, "elapsedMs":result["elapsedMs"],
                "selfSamplesByModule":counts,
                "topSelfFunctions":sorted(functions.items(), key=lambda kv:kv[1], reverse=True)[:15]
            }
        reports = root / f"svelte-{variant}-{profile_trial}.json"
        run = json.loads(reports.read_text())
        assert run["visibleSongs"] == 48 and run["screenshotDeviation"] > 0
        assert Path(run["screenshot"]).stat().st_size > 500
        expected_component = "SvelteApp.svelte" if variant == "scoped" else "SvelteRawList.svelte"
        sampled_sources = " ".join(
            src.get("url",src.get("sourceURL",""))
            for src in json.loads((root / f"hotpath-svelte-window-{profile_trial}.json").read_text())["cpu"]["stackTraces"]["sources"]
        )
        assert expected_component in sampled_sources, f"Wrong compiled component in {variant}: {expected_component}"
        items.append({"trial":trial,"profileTrial":profile_trial,"scenes":cases})
    data[variant]=items

(root / "REMAINING_HOTPATH.json").write_text(json.dumps(data,indent=2)+"\n")
lines = ["# Isolate remaining Svelte Core vs GPUI host CPU self-samples", "",
    "3 warmed JavaScriptCore sampling profiles per implementation; production Svelte, real Linux native window.",
    "Only CPU samples inside warm update loops; no compile or startup samples.",
    "Self-sample percentages are **sampling shares**, not decomposed wall-clock time.",
    "",
    "| Variant | Scene | Samples | Median Svelte Core | Median GPUI shadow host | Median GPUI style | Median elapsed ms (profiler active) |",
    "|---|---|---:|---:|---:|---:|---:|"]
for variant in variants:
    for scene in scenes:
        recs=[x["scenes"][scene] for x in data[variant]]
        c=lambda k:round(statistics.median(100*r["selfSamplesByModule"].get(k,0)/r["sampleCount"] for r in recs),1)
        ms=round(statistics.median(r["elapsedMs"] for r in recs),3)
        lines.append(f"| {variant} | {scene} | {statistics.median(r['sampleCount'] for r in recs):g} | {c('Svelte core')}% | {c('gpuix-svelte shadow host')}% | {c('gpuix-svelte style')}% | {ms} |")
for variant in variants:
    for scene in ("window","reorder"):
        lines.extend(["",f"### {variant}: {scene}, top self-sampled functions (first trial)",""])
        for name,cnt in data[variant][0]["scenes"][scene]["topSelfFunctions"][:12]:
            lines.append(f"- {cnt} samples: `{name}`")
lines += ["", "The new analysis intentionally avoids interpreting whole-process profile time as a latency benchmark; measure latency with the separate non-profiled CI.",
    "The same native GPUIX renderer and screenshot/tree assertions are used for each variant."]
(root / "REMAINING_HOTPATH.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
