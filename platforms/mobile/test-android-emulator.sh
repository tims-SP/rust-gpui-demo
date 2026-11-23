#!/usr/bin/env bash
# A genuinely booted, hardware-accelerated AVD must show the *actual* GPUI
# Hermes scene. Capturing a launcher or system ANR is an explicit failure.
set -euo pipefail
root="$(pwd)"
mkdir -p "$root/results/android-emulator"
adb wait-for-device
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1
for f in svelte solid; do
    adb install -r "$root/results/android-emulator/$f.apk"
    adb logcat -c
    # AVD/ActivityManager can take longer than am start -W's internal timeout.
    # Record its output, but use actual process+screen evidence as the gate.
    adb shell am start -n dev.gpui.mobile.example/dev.gpui.mobile.GpuiActivity \
        > "$root/results/android-emulator/$f-activity.txt" 2>&1 || true
    pid=""
    for i in $(seq 1 35); do
        pid="$(adb shell pidof dev.gpui.mobile.example | tr -d '\r' || true)"
        if [[ -n "$pid" ]]; then break; fi
        sleep 2
    done
    adb logcat -d -v time > "$root/results/android-emulator/$f-logcat.txt"
    if [[ -z "$pid" ]]; then
        tail -100 "$root/results/android-emulator/$f-logcat.txt"
        echo "GPUI_ANDROID_APP_PROCESS_NOT_RUNNING:$f" >&2
        exit 1
    fi
    sleep 12
    adb exec-out screencap -p > "$root/results/android-emulator/$f.png"
    python3 platforms/mobile/verify-android-image.py "$root/results/android-emulator/$f.png"
    echo "GPUI_ANDROID_EMULATOR_HERMES_SCENE_RENDER_PASS:$f:pid=$pid"
    adb shell am force-stop dev.gpui.mobile.example
done
