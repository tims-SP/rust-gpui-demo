#!/usr/bin/env python3
"""Validate real Ibex2 precompiled-HBC samples before reporting any ranking."""
import json
import re
import statistics
from pathlib import Path
base=Path("results/perf")
cases=["counter","window","theme","event_roundtrip","keyed_reorder"]
summary={}
for framework in ("svelte","solid"):
    records=[]
    for i in range(1,8):
        lines=(base/f"{i}-{framework}.log").read_text().splitlines()
        candidates=[l.removeprefix("BENCH_RESULT:") for l in lines if l.startswith("BENCH_RESULT:")]
        if len(candidates)!=1 or f"GPUI_SCENE_OK:{framework}" not in lines:
            raise SystemExit(f"Missing valid real Hermes sample {i}-{framework}")
        data=json.loads(candidates[0])
        if data["framework"]!=framework or data["final"]!={"count":256,"start":40,"theme":"light","renderedRows":48}:
            raise SystemExit(f"Incorrect actual node tree {i}-{framework}")
        if list(data["measurements"])!=cases:
            raise SystemExit(f"Unexpected workloads {i}-{framework}")
        sizes={"counter":256,"window":40,"theme":50,"event_roundtrip":1000,"keyed_reorder":20}
        if any(data["measurements"][c]["iterations"]!=sizes[c] for c in cases):
            raise SystemExit(f"Invalid iterations {i}-{framework}")
        t=(base/f"{i}-{framework}.time").read_text()
        wall=float(re.search(r"PROCESS_SECONDS=([0-9.]+)",t).group(1))
        rss=int(re.search(r"PEAK_RSS_KIB=(\d+)",t).group(1))
        records.append({"trial":i,"wall_seconds":wall,"rss_kib":rss,
            "mutations":data["mutations"],
            "cases":{c: data["measurements"][c] for c in cases}})
    metrics={}
    for c in cases:
        times=[r["cases"][c]["ms"] for r in records]
        mutation_counts={r["cases"][c]["mutations"] for r in records}
        if len(mutation_counts)!=1:
            raise SystemExit(f"Mutation count changes nondeterministically: {framework} {c}")
        metrics[c]={"median_ms":statistics.median(times),"min_ms":min(times),
                    "max_ms":max(times),"mutations":mutation_counts.pop()}
    summary[framework]={
      "trials":records,
      "median_process_seconds":statistics.median(r["wall_seconds"] for r in records),
      "median_peak_rss_mib":round(statistics.median(r["rss_kib"] for r in records)/1024,2),
      "metrics":metrics
    }
(base/"report.json").write_text(json.dumps(summary,indent=2))
md=["# True native Hermes HBC benchmark — seven alternating process trials",
    "Same Ubuntu Runner, pinned Ibex2/Hermes; no Node/V8 execution of benchmark payload.",
    "This is non-DOM reactive scene-graph performance, **not GPUI GPU frame latency**.",
    "",
    "| Case | Svelte median ms | Solid median ms | Svelte mutations | Solid mutations |",
    "|---|---:|---:|---:|---:|"]
for c in cases:
    a=summary["svelte"]["metrics"][c]
    b=summary["solid"]["metrics"][c]
    md.append(f"| {c} | {a['median_ms']} | {b['median_ms']} | {a['mutations']} | {b['mutations']} |")
md+=["","| Mode | Median process wall s | Median peak RSS MiB |",
      "|---|---:|---:|"]
for f in ("svelte","solid"):
    x=summary[f]
    md.append(f"| {f} | {x['median_process_seconds']} | {x['median_peak_rss_mib']} |")
md+=["","Per-trial raw JSON and /usr/bin/time receipts are in this artifact.",
      "Date.now has 1ms granularity; coarse zeroes are below timing resolution.",
      "A single synthetic workload cannot establish general framework superiority."]
(base/"REPORT.md").write_text("\n".join(md)+"\n")
print("\n".join(md))
print("HERMES_SEVEN_TRIAL_BOTH_FRAMEWORKS_PASS")
