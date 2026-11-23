#!/usr/bin/env bash
# Called inside an actual AVD session created by android-emulator-runner.
set -euo pipefail
root="$(pwd)"
mkdir -p "$root/results/android-emulator"
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1
for f in svelte solid; do
    adb install -r "$root/results/android-emulator/$f.apk"
    adb logcat -c
    adb shell am start -W -n dev.gpui.mobile.example/dev.gpui.mobile.GpuiActivity |
        tee "$root/results/android-emulator/$f-activity.txt"
    sleep 12
    pid="$(adb shell pidof dev.gpui.mobile.example | tr -d '\r')"
    test -n "$pid" || { echo "Android GPUI app crashed for $f"; adb logcat -d | tail -100; exit 1; }
    adb logcat -d -v time > "$root/results/android-emulator/$f-logcat.txt"
    adb exec-out screencap -p > "$root/results/android-emulator/$f.png"
    python3 platforms/mobile/verify-android-image.py "$root/results/android-emulator/$f.png"
    echo "GPUI_ANDROID_EMULATOR_LAUNCH_SCREENSHOT_PASS:$f:pid=$pid"
    adb shell am force-stop dev.gpui.mobile.example
done
