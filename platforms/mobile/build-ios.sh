#!/usr/bin/env bash
# Build actual Hermes-derived GPUI Mobile scene variants as independent iOS Simulator
# .app bundles. Simulator RUN/screenshot is attempted and separately reported.
set -euo pipefail
root="$(pwd)"
example="$root/.gpui-mobile/example"
project="$example/ios/project.yml"
test -f "$project"
test -s "$example/src/screens/hermes-svelte.json"
test -s "$example/src/screens/hermes-solid.json"
mkdir -p "$root/results/ios"
rustup target add aarch64-apple-ios-sim
python3 - "$project" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
data=p.read_text()
old='cargo build --lib --target "${RUST_TARGET}" ${CARGO_FLAGS} 2>&1'
new='cargo build --lib --target "${RUST_TARGET}" ${CARGO_FLAGS} ${GPUI_HERMES_FEATURES:-} 2>&1'
if old not in data:
    raise SystemExit("Unknown upstream iOS Cargo build phase: refusing silent feature mismatch")
p.write_text(data.replace(old,new))
PY
(
    cd "$example/ios"
    xcodegen generate --spec project.yml
)
# GitHub hosted macOS uses -D warnings; the pinned mobile fork has harmless
# platform-specific dead_code (open_main_window). Keep source unchanged.
export RUSTFLAGS="-A dead_code"
for framework in svelte solid; do
    export GPUI_HERMES_FEATURES=""
    if [[ "$framework" == "solid" ]]; then
        export GPUI_HERMES_FEATURES="--features solid-demo"
    fi
    # Xcode checks the absolute .a input before running the upstream prebuild
    # phase. Build it first and resolve the *actual* Cargo target directory.
    rust_opts=()
    if [[ "$framework" == solid ]]; then rust_opts+=(--features solid-demo); fi
    target_dir="$(cd "$example" && cargo metadata --no-deps --format-version 1 | python3 -c 'import json,sys;print(json.load(sys.stdin)["target_directory"])')"
    (cd "$example" && cargo build --lib --target aarch64-apple-ios-sim "${rust_opts[@]}") \
        > "$root/results/ios/$framework-rust-build.log" 2>&1 || {
          tail -100 "$root/results/ios/$framework-rust-build.log"; exit 1;
        }
    staticlib="$target_dir/aarch64-apple-ios-sim/debug/libgpui_mobile_example.a"
    test -s "$staticlib" || {
       echo "Expected iOS static library missing: $staticlib" >&2; exit 1;
    }
    echo "GPUI_IOS_RUST_STATICLIB_PASS:$framework:$staticlib"
    derived="$root/results/ios/DerivedData-$framework"
    log="$root/results/ios/$framework-build.log"
    if ! xcodebuild -project "$example/ios/GpuiExample.xcodeproj" \
        -scheme GpuiExample -configuration Debug \
        -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
        -derivedDataPath "$derived" CODE_SIGNING_ALLOWED=NO \
        EXAMPLE_STATIC_LIB="$staticlib" \
        build > "$log" 2>&1; then
        tail -100 "$log"
        exit 1
    fi
    app="$derived/Build/Products/Debug-iphonesimulator/GpuiExample.app"
    test -f "$app/Info.plist"
    /usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$app/Info.plist" | grep -Fx dev.gpui.mobile.example
    ditto -c -k --sequesterRsrc --keepParent "$app" "$root/results/ios/$framework.app.zip"
    echo "GPUI_IOS_MOBILE_HERMES_SCENE_APP_BUILD_PASS:$framework"
done

# Simulator is an independent acceptance gate. A build cannot imply a launch.
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "GPUI_IOS_SIMULATOR_RUN_UNVERIFIED:non_arm64_runner"
    exit 0
fi
device="$(xcrun simctl list devices available -j | python3 -c '
import json,sys
r=json.load(sys.stdin)
for group in r.get("devices",{}).values():
    for d in group:
        if d.get("isAvailable") and "iPhone" in d.get("name",""):
            print(d["udid"]);sys.exit(0)
')"
if [[ -z "$device" ]]; then
    echo "GPUI_IOS_SIMULATOR_RUN_UNVERIFIED:no_iphone_simulator"
    exit 0
fi
state="$(xcrun simctl list devices available -j | python3 -c '
import json,sys
r=json.load(sys.stdin)
for group in r.get("devices",{}).values():
    for d in group:
        if d.get("udid")==sys.argv[1]:print(d.get("state",""));sys.exit(0)
' "$device")"
if [[ "$state" != "Booted" ]]; then xcrun simctl boot "$device"; fi
xcrun simctl bootstatus "$device" -b
for framework in svelte solid; do
    app="$root/results/ios/DerivedData-$framework/Build/Products/Debug-iphonesimulator/GpuiExample.app"
    xcrun simctl install "$device" "$app"
    xcrun simctl launch "$device" dev.gpui.mobile.example
    sleep 8
    image="$root/results/ios/$framework-simulator.png"
    xcrun simctl io "$device" screenshot "$image"
    test "$(stat -f%z "$image")" -gt 20000
    echo "GPUI_IOS_SIMULATOR_LAUNCH_AND_SCREENSHOT_CAPTURED:$framework"
    xcrun simctl terminate "$device" dev.gpui.mobile.example || true
done
