#!/usr/bin/env bash
# Overlay the same actual Hermes final scenes on GPUI Mobile's community
# renderer. Fail closed if upstream iOS registration changes: the upstream
# demo currently hardcodes an AiChat root instead of its Home/Router screen.
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

# Unlike Android, upstream iOS uses gpui_ios_register_app and installs
# AiChat directly, bypassing Router::Home and thus the overlaid Home view.
# Replace ONLY the exact known callback; never accept the original screen.
app="$mobile_root/example/src/lib.rs"
python3 - "$app" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
old='let content = cx.new(|cx| screens::ai_chat::AiChat::new(window, cx));'
new='let content = cx.new(|_| Router::with_initial_screen(screens::Screen::Home));'
if s.count(old)!=1:
    raise SystemExit(f"Unknown upstream iOS root registration: expected one AiChat callback, saw {s.count(old)}")
s=s.replace(old,new,1)
old_name='.expect("open embedded Markdown view");'
if s.count(old_name)!=1:
    raise SystemExit("Unknown upstream iOS root expect marker")
s=s.replace(old_name,'.expect("open Hermes Home scene");',1)
p.write_text(s)
PY
echo GPUI_MOBILE_SCENE_OVERLAY_READY
echo GPUI_IOS_HOME_ROUTER_REGISTERED
