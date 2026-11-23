import json, statistics
from pathlib import Path
root=Path("results")
results={}
for framework in ("solid","svelte"):
    for engine in ("bun","hermes"):
        rows=[]
        for trial in range(3):
            path=root/f"{engine}-{framework}-{trial}.json"
            assert path.is_file(),path
            j=json.loads(path.read_text())
            assert j["engine"]==engine and j["framework"]==framework
            assert j["visibleRows"]==48 and j["screenshotDeviation"]>0
            assert (j["runtime"]["bun"] is not None)==(engine=="bun"),j
            if engine=="hermes": assert "hermes" in j["runtime"]["execPath"].lower(),j
            for key in ("single","theme","offscreen","reorder","window"):
                count=j["phases"][key]["mutations"]
                assert count==0 if key=="offscreen" else count>0,(engine,framework,key,count)
            rows.append(j)
        results[engine+"-"+framework]=rows
for fw in ("solid","svelte"):
    a=results["bun-"+fw];b=results["hermes-"+fw]
    for key in ("single","theme","offscreen","reorder","window"):
        aa=[r["phases"][key]["mutations"] for r in a]
        bb=[r["phases"][key]["mutations"] for r in b]
        assert aa==bb,(fw,key,aa,bb)
lines=["# Hermes/JavaScriptCore GPUIX end-to-end Linux engine comparison","",
    "Same CJS bundle for each framework is executed by Bun and hermes-node; same Node-API GPUIX 0.11, native tree correctness and X11 screenshot verification.",
    "Both frameworks have 10k source rows, 48 visible rows, identical update schedules and warm-up.",
    "Medians of 3 separate processes for each engine/framework pair, time only synchronous JS+Native update loops; startup excluded.","",
    "| Framework | Phase | Bun/JSC median ms | Hermes median ms | Hermes/Bun ratio | Native mutations (both) |",
    "|---|---|---:|---:|---:|---:|"]
for fw in ("solid","svelte"):
    for key in ("single","theme","offscreen","reorder","window"):
        a=statistics.median(x["phases"][key]["elapsedMs"] for x in results["bun-"+fw])
        b=statistics.median(x["phases"][key]["elapsedMs"] for x in results["hermes-"+fw])
        n=results["bun-"+fw][0]["phases"][key]["mutations"]
        lines.append(f"| {fw} | {key} | {a:.4f} | {b:.4f} | {b/a:.2f}x | {n} |")
lines+=["","Hermes CJS source is compiled at startup by hermes-node with --no-compile-cache; timed work excludes startup. Production AOT bundle startup/memory is a separate future experiment.",
"Results describe these integration versions only. No inference on hardware GPU frame time or Android/iOS, and CI llvmpipe is software Vulkan."]
(root/"HERMES.md").write_text("\n".join(lines)+"\n")
(root/"HERMES.json").write_text(json.dumps(results,indent=2)+"\n")
print("\n".join(lines))
