#!/usr/bin/env python3
"""Independent semantic parity check before a mobile native build."""
import json
import sys
from pathlib import Path

def find(node, wanted):
    if not isinstance(node, dict):
        return None
    if node.get("attrs", {}).get("id") == wanted:
        return node
    for child in node.get("children", []):
        result = find(child, wanted)
        if result is not None:
            return result
    return None

def stringify(node):
    if node.get("type") == "text":
        return node.get("text", "")
    return "".join(stringify(c) for c in node.get("children", []) if isinstance(c, dict))

assert len(sys.argv) == 3, "Expected svelte.json and solid.json from Hermes"
for framework, name in zip(("svelte", "solid"), sys.argv[1:]):
    payload = json.loads(Path(name).read_text())
    assert payload["framework"] == framework
    assert payload["final"] == dict(count=256, start=40, theme="light", renderedRows=48)
    tracks = find(payload["scene"], "tracks")
    assert tracks, "Missing Hermes track list"
    rows = [stringify(c) for c in tracks["children"] if c.get("name") == "row"]
    assert rows == [f"Track {i}" for i in range(40, 88)], "Incorrect 48 Hermes rows"
    print(f"GPUI_MOBILE_HERMES_SCENE_PARITY_PASS:{framework}:48")
