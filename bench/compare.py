import json
from pathlib import Path

root = Path("results")
solid = json.loads((root / "solid.json").read_text())
svelte = json.loads((root / "svelte.json").read_text())
assert solid["platform"] == svelte["platform"] == "linux"
assert solid["rows"] == svelte["rows"] == 48
rows = []
for name in ("single", "theme", "reorder"):
    a, b = solid["phases"][name], svelte["phases"][name]
    assert a["iterations"] == b["iterations"] and a["iterations"] > 0
    assert a["batches"] and b["batches"]
    rows.append({
        "scenario": name,
        "solid": { k: a[k] for k in ("elapsedMs", "batches", "mutations", "bytes") },
        "svelte": { k: b[k] for k in ("elapsedMs", "batches", "mutations", "bytes") }
    })
report = {
    "status": "passed",
    "scope": "Linux software Vulkan native-window mutation and JS scheduling comparison",
    "limitations": [
        "GitHub-hosted Ubuntu runner uses Mesa software Vulkan, not a hardware GPU",
        "Each framework runs in a separate process, and time samples are not a rigorous confidence interval",
        "Style strategies differ by design (Svelte CSS variable versus Solid reactive inline style)",
        "No actual custom Rust ArtworkFlow element or mobile test in this phase",
    ],
    "results": rows
}
(root / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
lines = ["# Linux GPUIX native Svelte / Solid comparison", "",
         "Runner: GitHub-hosted Ubuntu 24.04, Xvfb, Mesa software Vulkan, Bun", "",
         "| Scenario | Solid ms | Svelte ms | Solid native mutations | Svelte native mutations |",
         "|---|---:|---:|---:|---:|"]
for item in rows:
    a, b = item["solid"], item["svelte"]
    lines.append(f"| {item['scenario']} | {a['elapsedMs']} | {b['elapsedMs']} | {a['mutations']} | {b['mutations']} |")
lines += ["", "**Limits**: timings include JavaScript scheduling and FFI submission, not controlled native GPU-frame throughput. Both applications use the real Linux GPUIX window; images are X11 captures. Do not infer a universal winner from this run."]
(root / "SUMMARY.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines), flush=True)
