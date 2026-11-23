#!/usr/bin/env bash
# Separate x86_64 emulator build; ARM64 APKs remain the authoritative physical-device builds.
set -euo pipefail
root="$(pwd)"
example="$root/.gpui-mobile/example"
test -s "$example/src/screens/hermes-svelte.json"
test -s "$example/src/screens/hermes-solid.json"
python3 - "$example/android/gradle/app/build.gradle.kts" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
needle='abiFilters += listOf("arm64-v8a")'
if needle not in s: raise SystemExit("Unknown upstream Android ABI filter")
p.write_text(s.replace(needle,'abiFilters += listOf("x86_64")'))
PY
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export ANDROID_NDK_HOME="$(find "$ANDROID_SDK_ROOT/ndk" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
test -d "$ANDROID_NDK_HOME"
rustup target add x86_64-linux-android
cargo install cargo-ndk --locked
mkdir -p "$root/results/android-emulator"
for f in svelte solid; do
    features=(--features bench-auto)
    if [[ "$f" == solid ]]; then features+=(--features solid-demo); fi
    (
        cd "$example"
        cargo ndk -t x86_64 -P 31 -o android/gradle/app/src/main/jniLibs build --lib "${features[@]}"
        test -s android/gradle/app/src/main/jniLibs/x86_64/libgpui_mobile_example.so
        cd android/gradle
        chmod +x ./gradlew
        ./gradlew :app:assembleDebug --no-daemon
    )
    cp "$example/android/gradle/app/build/outputs/apk/debug/app-debug.apk" "$root/results/android-emulator/$f.apk"
    python3 - "$root/results/android-emulator/$f.apk" <<'PY'
import sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    assert 'AndroidManifest.xml' in z.namelist()
    assert 'lib/x86_64/libgpui_mobile_example.so' in z.namelist()
print("GPUI_ANDROID_X86_64_APK_BUILD_PASS")
PY
done
