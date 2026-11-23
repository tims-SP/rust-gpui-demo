import json, statistics
from pathlib import Path
root=Path("results")
results={}
for framework in ("solid","svelte"):
    for engine in ("bun","hermes","hermes-opt","hermes-aot"):
        rows=[]
        for trial in range(3):
            path=root/f"{engine}-{framework}-{trial}.json"
            assert path.is_file(),path
            j=json.loads(path.read_text())
            assert j["engine"]==engine and j["framework"]==framework
            assert j["visibleRows"]==48 and j["screenshotDeviation"]>0
            assert (j["runtime"]["bun"] is not None)==(engine=="bun"),j
            if engine!="bun": assert "hermes" in j["runtime"]["execPath"].lower(),j
            for key in ("single","theme","offscreen","reorder","window"):
                count=j["phases"][key]["mutations"]
                assert count==0 if key=="offscreen" else count>0,(engine,framework,key,count)
            rows.append(j)
        results[engine+"-"+framework]=rows
for fw in ("solid","svelte"):
    a=results["bun-"+fw]
    for engine in ("hermes","hermes-opt","hermes-aot"):
        b=results[engine+"-"+fw]
        for key in ("single","theme","offscreen","reorder","window"):
            aa=[r["phases"][key]["mutations"] for r in a]
            bb=[r["phases"][key]["mutations"] for r in b]
            assert aa==bb,(fw,key,engine,aa,bb)
lines=["# Hermes / JSC real Linux GPUIX engine comparison","",
    "Exactly the same prebuilt CommonJS files per framework are run by Bun and three Hermes modes.",
    "All modes load the same GPUIX 0.11 Node-API addon and require real Rust retained-tree, nonblank X11 screenshots and matching Native Mutation counts.",
    "Three separate processes per engine/framework; 512 theme + 192 reorder + 240 window-shift operations warmed before measurement. All times exclude startup.","",
    "| Framework | Scenario | Bun JSC ms | Hermes no-cache ms | Hermes optimized ms | Hermes AOT bytecode ms | AOT/Bun | Native mutations |",
    "|---|---|---:|---:|---:|---:|---:|---:|"]
for fw in ("solid","svelte"):
    for key in ("single","theme","offscreen","reorder","window"):
        med=lambda eng:statistics.median(x["phases"][key]["elapsedMs"] for x in results[eng+"-"+fw])
        bun=med("bun");h=med("hermes");o=med("hermes-opt");a=med("hermes-aot")
        n=results["bun-"+fw][0]["phases"][key]["mutations"]
        lines.append(f"| {fw} | {key} | {bun:.4f} | {h:.4f} | {o:.4f} | {a:.4f} | {a/bun:.2f}× | {n} |")
lines+=["","Hermes no-cache disables optimizer; hermes-opt explicitly enables optimization without compile-cache; hermes-aot precompiles bytecode into a bundle using the same CJS source.",
"This isolates steady-state update performance; the AOT startup and binary distribution sizes are separate considerations.",
"Software Vulkan under Xvfb is not hardware GPU performance. Memory numbers are one-time RSS snapshots, not leak analyses."]
(root/"HERMES.md").write_text("\n".join(lines)+"\n")
(root/"HERMES.json").write_text(json.dumps(results,indent=2)+"\n")
print("\n".join(lines))
