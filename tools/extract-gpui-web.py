#!/usr/bin/env python3
"""Validate actual Chromium DOM mutations from GPUI Web Wasm update replay.

The GPUI Web application publishes JSON into a hidden <pre> after its own
real Entity updates and Render callbacks. Parse the browser's --dump-dom
output, never a script literal or a fabricated benchmark.
"""
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

class BenchMarker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.active = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "pre" and attrs.get("id") == "gpui-bench-result":
            self.active = {"attrs": attrs, "text": ""}
            self.nodes.append(self.active)
    def handle_data(self, data):
        if self.active is not None:
            self.active["text"] += data
    def handle_endtag(self, tag):
        if tag == "pre":
            self.active = None

def extract(html: str, framework: str) -> dict:
    doc = BenchMarker()
    doc.feed(html)
    if len(doc.nodes) != 1:
        raise ValueError(f"expected one live GPUI result node, found {len(doc.nodes)}")
    marker = doc.nodes[0]
    if marker["attrs"].get("data-status") != "pass":
        raise ValueError("GPUI did not assert replay complete")
    metrics = json.loads(marker["text"])
    if metrics.get("schema") != "gpui-render-replay/v1" or metrics.get("platform") != "web":
        raise ValueError("wrong benchmark schema")
    if metrics.get("framework") != framework:
        raise ValueError("wrong framework")
    if metrics.get("scheduled_updates") != 120 or metrics.get("applied_updates") != 120:
        raise ValueError("partial web scene updates")
    if metrics.get("render_callbacks_with_pending_update", 0) < 20:
        raise ValueError("render callback evidence insufficient")
    is_live_vm = metrics.get("live_hermes_vm")
    is_live_bridge = metrics.get("live_jsi_to_gpui")
    if not isinstance(is_live_vm, bool) or not isinstance(is_live_bridge, bool):
        raise ValueError("invalid live bridge flags")
    if is_live_vm != is_live_bridge:
        raise ValueError("mismatched live_hermes_vm and live_jsi_to_gpui flags")
    if is_live_vm and metrics.get("source") != "live-Hermes-WASM-in-browser":
        raise ValueError("unverified live bridge claim without live-Hermes-WASM-in-browser source")
    if not all(isinstance(metrics.get(k), int) for k in ("p50_us","p95_us","p99_us")):
        raise ValueError("missing measured latency quantiles")
    if not (0 <= metrics["p50_us"] <= metrics["p95_us"] <= metrics["p99_us"]):
        raise ValueError("invalid p50/p95/p99")
    return metrics

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dom", required=True, type=Path)
    ap.add_argument("--framework", required=True, choices=("svelte","solid"))
    ap.add_argument("--out", required=True, type=Path)
    opts = ap.parse_args()
    record = extract(opts.dom.read_text(encoding="utf-8"), opts.framework)
    record["status"] = "PASS"
    record["browser_measurement_note"] = "DOM and screenshot are separate Chromium invocations"
    opts.out.parent.mkdir(exist_ok=True, parents=True)
    opts.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"GPUI_WEB_REPLAY_METRICS_VERIFIED:{opts.framework} p50={record['p50_us']}us p95={record['p95_us']}us")

if __name__ == "__main__":
    main()
