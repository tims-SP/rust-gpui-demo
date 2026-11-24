#!/usr/bin/env python3
"""Extract verified GPUI Render-callback metrics for replay or live Hermes/JSI.

The measured endpoint is a real GPUI Render callback, never GPU Present.
"""
import argparse
import json
from pathlib import Path

def extract(raw: str, framework: str) -> dict:
    prefix = "GPUI_REPLAY_BENCH_RESULT:"
    # macOS/iOS unified logging prepends timestamp, process and subsystem
    # metadata before Rust log payloads. Find the marker inside each line so
    # the same strict one-record validation works for both stdout and os_log.
    lines = [line[line.index(prefix):].strip()
             for line in raw.splitlines() if prefix in line]
    if len(lines) != 1:
        raise ValueError(f"expected exactly one real GPUI result, got {len(lines)}")
    data = json.loads(lines[0][len(prefix):])
    if data.get("framework") != framework:
        raise ValueError("framework mismatch")
    if data.get("schema") != "gpui-render-replay/v1":
        raise ValueError("schema mismatch")
    live = data.get("live_hermes_vm") is True and data.get("live_jsi_to_gpui") is True
    replay = data.get("live_jsi_to_gpui") is False and data.get("live_hermes_vm") is False
    if not (live or replay):
        raise ValueError("inconsistent Hermes/JSI source claims")
    if live and data.get("source") != "live-Hermes-HBC-in-process":
        raise ValueError("live Hermes run has an invalid source marker")
    if replay:
        if data.get("source") != "precomputed-Hermes-scene":
            raise ValueError("replay run has an invalid source marker")
        if data.get("driver") != "gpui-timer-internal":
            raise ValueError("replay run did not use the GPUI timer driver")
        if data.get("metric") != "notify_to_render_callback_us_NOT_GPU_present":
            raise ValueError("replay run metric does not end at the Render callback")
    if live:
        if data.get("driver") not in (
            "gpui-timer-repeated-framework-click-hbc",
            "gpui-mobile-timer-repeated-framework-click-hbc",
        ):
            raise ValueError("live run did not use repeated framework HBC events")
        if data.get("metric") != "jsi_mutation_to_render_callback_us_NOT_GPU_present":
            raise ValueError("live run metric does not end at the JSI-to-Render boundary")
        if data.get("interactive_hermes_mutation_batches") != 120:
            raise ValueError("live run must deliver exactly one JSI mutation batch for each of 120 framework events")
        if data.get("hermes_mutation_batches", 0) < data.get("interactive_hermes_mutation_batches", 0):
            raise ValueError("live HBC mutation batch accounting is inconsistent")
        if data.get("gpu_present_latency_ms") is not None or data.get("end_to_end_latency_ms") is not None:
            raise ValueError("live Render callback run must not claim GPU Present or E2E")
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
    parser.add_argument("--platform", choices=("linux", "windows", "macos", "ios", "android"), required=True)
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
