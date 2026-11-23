#!/usr/bin/env python3
"""Download and validate independent six-platform Svelte/Solid CI evidence.

Produces a 12-cell matrix with missing data explicitly represented as null.
A GPUI replay is not an end-to-end Hermes→JSI→GPU frame measurement.
Run with a GH account that can read this repository's Actions artifacts.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

REPO = "tims-SP/rust-gpui-demo"
SOURCES = {
    "linux": ("Real GPUI Linux windows from Hermes Svelte and Solid scenes",
              "gpui-linux-svelte-solid-real-windows", "gpui-linux"),
    "windows": ("Real Windows GPUI Hermes Svelte Solid windows",
                "windows-gpui-svelte-solid-real-window-evidence", "windows-gpui"),
    "macos": ("Real macOS GPUI Hermes Svelte Solid windows",
              "gpui-macos-svelte-solid-real-window-evidence", "macos-gpui"),
    "web": ("Real GPUI Web Canvas from Hermes Svelte and Solid scenes",
            "gpui-web-official-canvas-svelte-solid", "gpui-web"),
    "ios": ("GPUI Windows macOS iOS Android build feasibility",
            "gpui-mobile-hermes-svelte-solid-ios-simulator", "ios"),
    "android": ("GPUI Windows macOS iOS Android build feasibility",
                "android-emulator-hermes-svelte-solid-evidence", "android-emulator"),
}
FRAMEWORKS = ("svelte","solid")

def github(args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout

def find_runs(repo):
    return json.loads(github(["gh","run","list","-R",repo,"--limit","100",
        "--json","databaseId,headSha,headBranch,name,status,conclusion,createdAt"]))

def download_sources(root: Path, repo: str, recent_runs: list):
    metadata = {}
    for platform,(name,artifact,directory) in SOURCES.items():
        selected = [run for run in recent_runs
                    if run["name"] == name and run["status"] == "completed"
                    and run.get("conclusion") == "success"]
        # Most recent successful, but a successful platform-probe workflow may
        # contain only iOS or Android (scope-specific jobs).
        errors = []
        for run in selected:
            target = root / directory
            if target.exists() and any(target.iterdir()):
                raise RuntimeError(f"dirty output folder {target}")
            target.mkdir(parents=True, exist_ok=True)
            cmd = ["gh","run","download",str(run["databaseId"]),"-R",repo,
                   "-n",artifact,"-D",str(target)]
            p=subprocess.run(cmd,capture_output=True,text=True)
            if p.returncode == 0:
                metadata[platform] = {"run_id":run["databaseId"],
                                      "sha":run["headSha"],
                                      "branch":run["headBranch"],
                                      "created_at":run["createdAt"],
                                      "artifact":artifact}
                break
            errors.append(f"{run['databaseId']}: {p.stderr.strip()[:140]}")
            # A run with skipped scoped job has no artifact; clean and try older.
            for item in target.iterdir():
                if item.is_file(): item.unlink()
        if platform not in metadata:
            metadata[platform] = {"run_id":None,"error":"; ".join(errors[:3]) or "no successful run"}
    return metadata

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def is_valid_replay(m, p, f):
    return (isinstance(m,dict) and m.get("schema")=="gpui-render-replay/v1"
        and m.get("framework")==f and m.get("platform")==p
        and m.get("scheduled_updates")==120 and m.get("applied_updates")==120
        and m.get("render_callbacks_with_pending_update",0)>=20
        and m.get("live_jsi_to_gpui") is False
        and m.get("live_hermes_vm") is False
        and all(isinstance(m.get(k),int) and m[k]>=0
                for k in ("p50_us","p95_us","p99_us"))
        and m["p50_us"]<=m["p95_us"]<=m["p99_us"])

def cell(root,platform,framework,meta):
    base=root/SOURCES[platform][2]
    replay=read_json(base/f"{framework}-metrics.json")
    g1=read_json(base/f"{framework}-g1.json") if platform in ("ios","android") else None
    # Rust logs and screenshot evidence for desktop/Web are validated by
    # the corresponding successful workflow; do not re-infer pixel authenticity.
    runtime=meta.get("run_id") is not None
    if platform in ("ios","android"):
        rendered=bool(g1 and g1.get("schema")=="gpui-mobile-g1/v1"
                      and g1.get("platform")==platform and g1.get("framework")==framework
                      and g1.get("stage")=="RENDER_PASS" and g1.get("status")=="PASS")
    else:
        rendered=runtime and (base/f"{framework}.png").is_file()
    measured=is_valid_replay(replay,platform,framework)
    return {
        "platform":platform,"framework":framework,
        "ci_run_id":meta.get("run_id"),"ci_sha":meta.get("sha"),
        "gpui_render_verified":bool(rendered),
        "metric_status":"MEASURED" if measured else "NOT_MEASURED",
        "gpui_replay_p50_us":replay["p50_us"] if measured else None,
        "gpui_replay_p95_us":replay["p95_us"] if measured else None,
        "gpui_replay_p99_us":replay["p99_us"] if measured else None,
        "g1_screenshot_readiness_ms":g1.get("elapsed_ms") if rendered and g1 else None,
        "g1_screenshot_attempts":g1.get("attempts") if rendered and g1 else None,
        "scene_source":"precomputed-Hermes-JSON",
        "hermes_running_in_same_gpui_app":False,
        "live_jsi_to_gpui":False,
        "gpu_present_latency_ms":None,
        "end_to_end_latency_ms":None,
    }

def render_markdown(cells, metadata):
    lines=["# Six-platform Hermes + Svelte/Solid evidence matrix",
           "",
           "This report separates real GPUI render proof from measured GPUI timer-driven",
           "rebuild latency. It **does not** claim complete live Hermes→JSI→GPU performance.",
           "The source for every GPUI view is a precomputed Hermes scene JSON.",
           "",
           "| Platform | Framework | Actual GPUI scene | Update→Render P50 | P95 | Mobile G1 readiness | CI evidence |",
           "|---|---|---|---:|---:|---:|---|"]
    for c in cells:
        link = f"[Run {c['ci_run_id']}](https://github.com/{REPO}/actions/runs/{c['ci_run_id']})" if c["ci_run_id"] else "Unverified"
        value = lambda x,suffix: f"{x} {suffix}" if x is not None else "—"
        lines.append(f"| {c['platform']} | {c['framework']} | "
          f"{'PASS' if c['gpui_render_verified'] else 'UNVERIFIED'} | "
          f"{value(c['gpui_replay_p50_us'],'µs')} | "
          f"{value(c['gpui_replay_p95_us'],'µs')} | "
          f"{value(c['g1_screenshot_readiness_ms'],'ms')} | {link} |")
    lines += ["",
      "**Metric definitions:** P50/P95 = elapsed microseconds between scheduled",
      "GPUI state mutation and the next `Render` callback. This excludes real",
      "GPU submission/presentation and any Hermes runtime/JSI propagation.",
      "Each platform uses different runner hardware: compare Svelte/Solid only",
      "within the same run and don't treat mobile G1 polling time as FPS or",
      "framework latency. iOS/Android G1 includes screenshot polling and cold",
      "boot effects, and is not a clean Svelte-vs-Solid speed comparison.",
      "",
      f"**Measured cells:** {sum(c['metric_status']=='MEASURED' for c in cells)}/12.",
      f"**Rendered cells:** {sum(c['gpui_render_verified'] for c in cells)}/12.",
      "**Full six-platform end-to-end benchmark:** NOT COMPLETE.",
      ]
    return "\n".join(lines)+"\n"

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--repo",default=REPO)
    a.add_argument("--out",type=Path,default=Path("results/six-platform"))
    a.add_argument("--no-download",action="store_true")
    args=a.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if args.no_download:
        meta=read_json(args.out/"sources.json")
        if not isinstance(meta,dict): raise SystemExit("missing sources.json")
    else:
        meta=download_sources(args.out,args.repo,find_runs(args.repo))
        (args.out/"sources.json").write_text(json.dumps(meta,indent=2)+"\n")
    cells=[cell(args.out,p,f,meta[p]) for p in SOURCES for f in FRAMEWORKS]
    data={"schema":"six-platform-benchmark/v1",
          "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
          "repo":args.repo,"cells":cells,"sources":meta,
          "complete":all(c["end_to_end_latency_ms"] is not None for c in cells)}
    (args.out/"matrix.json").write_text(json.dumps(data,indent=2)+"\n")
    (args.out/"REPORT.md").write_text(render_markdown(cells,meta))
    print(render_markdown(cells,meta))
    print("SIX_PLATFORM_REPORT_WRITTEN:"+str(args.out))

if __name__ == "__main__":
    main()
