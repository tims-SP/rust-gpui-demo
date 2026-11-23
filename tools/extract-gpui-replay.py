#!/usr/bin/env python3
"""Extract a verified GPUI timer-driven update -> Render callback benchmark.

This is not GPU presentation latency or JS→Rust live bridge performance.
"""
import argparse
import json
from pathlib import Path

def extract(raw: str, framework: str) -> dict:
    prefix = "GPUI_REPLAY_BENCH_RESULT:"
    lines = [s.strip() for s in raw.splitlines() if s.startswith(prefix)]
    if len(lines) != 1:
        raise ValueError(f"expected exactly one real GPUI result, got {len(lines)}")
    data = json.loads(lines[0][len(prefix):])
    if data.get("framework") != framework:
        raise ValueError("framework mismatch")
    if data.get("schema") != "gpui-render-replay/v1":
        raise ValueError("schema mismatch")
    if data.get("live_jsi_to_gpui") is not False or data.get("live_hermes_vm") is not False:
        raise ValueError("invalid source claims")
    if data.get("scheduled_updates") != 120 or data.get("applied_updates") != 120:
        raise ValueError("incomplete update sequence")
    if data.get("render_callbacks_with_pending_update", 0) < 20:
        raise ValueError("insufficient actually scheduled render callbacks")
    for metric in ("p50_us", "p95_us", "p99_us"):
        if not isinstance(data.get(metric), int) or data[metric] < 0:
            raise ValueError(f"invalid measured {metric}")
    if data["p95_us"] < data["p50_us"] or data["p99_us"] < data["p95_us"]:
        raise ValueError("percentile ordering invalid")
    if f"GPUI_REPLAY_BENCH_PASS:{framework}" not in raw:
        raise ValueError("runtime did not assert benchmark passed")
    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--framework", choices=("svelte", "solid"), required=True)
    parser.add_argument("--platform", choices=("linux", "windows", "macos"), required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    metrics = extract(args.log.read_text(encoding="utf-8"), args.framework)
    metrics["platform"] = args.platform
    metrics["status"] = "PASS"
    args.out.parent.mkdir(exist_ok=True, parents=True)
    args.out.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    print(f"GPUI_REPLAY_METRICS_VERIFIED:{args.platform}:{args.framework} p50={metrics['p50_us']}us p95={metrics['p95_us']}us")

if __name__ == "__main__":
    main()
