#!/usr/bin/env bash
# Overlay the same actual Hermes final scenes on the GPUI Mobile community
# example, which uses gpui-pre rather than the official desktop GPUI revision.
set -euo pipefail
mobile_root="${1:?path to gpui-mobile source required}"
scene_root="${2:?path to archived Hermes native results required}"
screen_dir="$mobile_root/example/src/screens"
test -f "$screen_dir/home.rs"
test -s "$scene_root/svelte.json"
test -s "$scene_root/solid.json"
python3 platforms/mobile/verify-scenes.py "$scene_root/svelte.json" "$scene_root/solid.json"
cp platforms/mobile/home.rs "$screen_dir/home.rs"
cp "$scene_root/svelte.json" "$screen_dir/hermes-svelte.json"
cp "$scene_root/solid.json" "$screen_dir/hermes-solid.json"

manifest="$mobile_root/example/Cargo.toml"
python3 - "$manifest" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); source=p.read_text()
if 'serde_json = "1"' not in source:
    source=source.replace('[dependencies]\n','[dependencies]\nserde_json = "1"\n',1)
if '[features]' not in source:
    source+='\n[features]\nsolid-demo = []\n'
elif 'solid-demo = []' not in source:
    source=source.replace('[features]\n','[features]\nsolid-demo = []\n',1)
p.write_text(source)
PY
echo GPUI_MOBILE_SCENE_OVERLAY_READY
