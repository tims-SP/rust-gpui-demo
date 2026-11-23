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
    pid=""
    for i in $(seq 1 35); do
        pid="$(adb shell pidof dev.gpui.mobile.example | tr -d '\r' || true)"
        if [[ -n "$pid" ]]; then break; fi
        sleep 2
    done
    # Android's native rendering startup can continue after the activity
    # launch command returns; don't snapshot the launcher prematurely.
    sleep 25
    adb exec-out screencap -p > "$root/results/android-emulator/$f.png"
    adb shell dumpsys activity activities > "$root/results/android-emulator/$f-activity-state.txt" || true
    adb shell dumpsys window windows > "$root/results/android-emulator/$f-window-state.txt" || true
    adb logcat -d -v time > "$root/results/android-emulator/$f-logcat.txt" || true
    adb logcat -d -b crash -v time > "$root/results/android-emulator/$f-crash.txt" || true
    live="$(adb shell pidof dev.gpui.mobile.example | tr -d '\r' || true)"
    echo "ANDROID_GPUI_PROCESS_DIAGNOSTIC:$f:start=$pid:after_25s=$live"
    grep -i -E 'ResumedActivity|mCurrentFocus|topResumedActivity' \
        "$root/results/android-emulator/$f-activity-state.txt" \
        "$root/results/android-emulator/$f-window-state.txt" | tail -12 || true
    if [[ -z "$live" ]]; then
        echo "GPUI_ANDROID_NATIVE_APP_EXITED:$f" >&2
        grep -E 'gpui-mobile-example|FATAL|AndroidRuntime|Fatal signal|signal 11' \
           "$root/results/android-emulator/$f-logcat.txt" | tail -90 || true
        exit 1
    fi
    python3 platforms/mobile/verify-android-image.py "$root/results/android-emulator/$f.png"
    echo "GPUI_ANDROID_EMULATOR_HERMES_SCENE_RENDER_PASS:$f:pid=$live"
    adb shell am force-stop dev.gpui.mobile.example
done
