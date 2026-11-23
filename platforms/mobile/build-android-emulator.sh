#!/usr/bin/env bash
# Separate x86_64 emulator build; ARM64 APKs remain the authoritative physical-device builds.
set -euo pipefail
root="$(pwd)"
example="$root/.gpui-mobile/example"
test -s "$example/src/screens/hermes-svelte.json"
test -s "$example/src/screens/hermes-solid.json"
# This is the one opt-in point for GLES-only. All production ARM64 Android
# builds retain the default Vulkan-first backend, and iOS retains Metal.
python3 - "$root/.gpui-mobile/Cargo.toml" <<'PYBACKEND'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
old='gpui_wgpu = { package = "gpui-pre-wgpu", version = "=0.3.6" }'
new='gpui_wgpu = { package = "gpui-pre-wgpu", version = "=0.3.6", features = ["android-gles-only"] }'
if s.count(old)!=1:
    raise SystemExit(f'Unknown upstream Android renderer dependency in {p}')
p.write_text(s.replace(old,new,1))
print('GPUI_ANDROID_EMULATOR_GLES_ONLY_ENABLED')
PYBACKEND
python3 - "$example/android/gradle/app/build.gradle.kts" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
needle='abiFilters += listOf("arm64-v8a")'
if needle not in s: raise SystemExit("Unknown upstream Android ABI filter")
p.write_text(s.replace(needle,'abiFilters += listOf("x86_64")'))
PY
# Maven Central sometimes rate-limits GitHub-hosted runners (HTTP 429).
# Keep Google's Android repository first, and route Central artifacts through
# Google's read-only mirror before falling back to repo.maven.apache.org.
python3 - "$example/android/gradle/settings.gradle.kts" "$example/android/gradle/build.gradle.kts" <<'PYMIRROR'
from pathlib import Path
import sys
mirror='maven { url = uri("https://maven-central.storage-download.googleapis.com/maven2/") }'
for name in sys.argv[1:]:
    p=Path(name); s=p.read_text()
    if mirror in s:
        continue
    if 'mavenCentral()' not in s:
        raise SystemExit(f"Expected Maven Central repository declaration in {p}")
    p.write_text(s.replace('mavenCentral()', mirror+'\n        mavenCentral()'))
    print(f"GPUI_ANDROID_MAVEN_CENTRAL_MIRROR_ENABLED:{p}")
PYMIRROR
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export ANDROID_NDK_HOME="$(find "$ANDROID_SDK_ROOT/ndk" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
test -d "$ANDROID_NDK_HOME"
# Fail closed if Cargo resolves the registry build instead of the patched
# crate. The no-deps metadata mode does NOT include transitive dependencies.
cargo metadata --manifest-path "$example/Cargo.toml" --format-version 1 \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); p=[p for p in d["packages"] if p["name"] == "gpui-pre-wgpu"]; assert len(p)==1 and "benchmark-gpui-pre-wgpu" in p[0]["manifest_path"], p; print("GPUI_ANDROID_PATCH_RESOLVED:",p[0]["manifest_path"])'
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
        # A GitHub hosted runner can receive Maven Central HTTP 429 even after
        # Rust and the GPUI renderer have compiled. Retry *only* known transient
        # dependency-fetch failures; compiler or source errors fail immediately.
        for gradle_attempt in 1 2 3; do
            gradle_log="$root/results/android-emulator/$f-gradle-attempt-$gradle_attempt.log"
            if ./gradlew :app:assembleDebug --no-daemon 2>&1 | tee "$gradle_log"; then
                echo "GPUI_ANDROID_GRADLE_BUILD_PASS:$f:attempt=$gradle_attempt"
                break
            fi
            if [[ "$gradle_attempt" -eq 3 ]] || ! grep -Eiq \
                'status code 429|Too Many Requests|status code 50[0234]|status code 503|Read timed out|Connection reset' "$gradle_log"; then
                echo "GPUI_ANDROID_GRADLE_HARD_FAILURE:$f:attempt=$gradle_attempt" >&2
                exit 1
            fi
            echo "GPUI_ANDROID_GRADLE_FETCH_BACKOFF:$f:attempt=$gradle_attempt" >&2
            sleep $(( 10 * gradle_attempt ))
        done
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
