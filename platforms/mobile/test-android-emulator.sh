#!/usr/bin/env bash
# A booted KVM-accelerated AVD must show the actual Hermes/GPUI Home scene.
# Capture diagnostics AFTER startup so later native crashes are not missed.
set -euo pipefail
root="$(pwd)"
mkdir -p "$root/results/android-emulator"
adb wait-for-device
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1
for f in svelte solid; do
    adb install -r "$root/results/android-emulator/$f.apk"
    adb logcat -c
    adb shell am start -n dev.gpui.mobile.example/dev.gpui.mobile.GpuiActivity \
        > "$root/results/android-emulator/$f-activity.txt" 2>&1 || true
    # Screenshot evidence is polled until a valid GPUI Hermes Home frame or a
    # hard timeout. Neither pidof nor am start can signal rendering success.
    accepted=false
    if python3 platforms/mobile/g1_probe.py android \
        --framework "$f" --output-dir "$root/results/android-emulator" \
        --timeout-sec 90 --interval-sec 3; then
        accepted=true
    fi
    adb shell dumpsys activity activities > "$root/results/android-emulator/$f-activity-state.txt" || true
    adb shell dumpsys window windows > "$root/results/android-emulator/$f-window-state.txt" || true
    adb logcat -d -v time > "$root/results/android-emulator/$f-logcat.txt" || true
    adb logcat -d -b crash -v time > "$root/results/android-emulator/$f-crash.txt" || true
    live="$(adb shell pidof dev.gpui.mobile.example | tr -d '\r' || true)"
    echo "ANDROID_GPUI_PROCESS_DIAGNOSTIC:$f:after_probe=$live"
    # The screenshot proves pixels; the in-app marker proves this framework's
    # Rust Home view constructed those nodes, rather than a stale app surface.
    scene_logged=false
    if grep -Fq "BENCH_G1_SCENE_BUILT:$f:" "$root/results/android-emulator/$f-logcat.txt"; then
        scene_logged=true
    fi
    echo "ANDROID_GPUI_SCENE_LOG_DIAGNOSTIC:$f:$scene_logged"
    if [[ "$accepted" != true || -z "$live" || "$scene_logged" != true ]]; then
        grep -i -E 'ResumedActivity|mCurrentFocus|topResumedActivity' \
            "$root/results/android-emulator/$f-activity-state.txt" \
            "$root/results/android-emulator/$f-window-state.txt" | tail -12 || true
        grep -E 'gpui-mobile-example|FATAL|AndroidRuntime|Fatal signal|signal 11' \
            "$root/results/android-emulator/$f-logcat.txt" | tail -90 || true
        echo "GPUI_ANDROID_G1_NOT_VERIFIED:$f" >&2
        exit 1
    fi
    echo "GPUI_ANDROID_EMULATOR_HERMES_SCENE_RENDER_PASS:$f:pid=$live"
    adb shell am force-stop dev.gpui.mobile.example
done
