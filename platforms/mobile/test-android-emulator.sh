#!/usr/bin/env bash
# G1 acceptance: actual GPUI Scene pixels + in-app scene marker.
# All ADB calls MUST be bounded: if emulator-5554 vanishes, an unbounded
# "adb logcat -d" can wait forever and consume the whole 90-minute CI job.
set -euo pipefail
root="$(pwd)"
out="$root/results/android-emulator"
mkdir -p "$out"
timeout -k 3s 120s adb wait-for-device
test "$(timeout -k 3s 12s adb shell getprop sys.boot_completed | tr -d '\r')" = 1

for f in svelte solid; do
    timeout -k 3s 60s adb install -r "$out/$f.apk"
    timeout -k 3s 12s adb logcat -c

    # Begin collecting BEFORE activity launch. Post-mortem adb logcat is
    # unavailable if the guest/emulator crashes and ADB disconnects.
    timeout -k 3s 145s adb logcat -v time > "$out/$f-logcat-stream.txt" 2>&1 &
    stream_pid=$!
    timeout -k 3s 15s adb shell am start \
        -n dev.gpui.mobile.example/dev.gpui.mobile.GpuiActivity \
        > "$out/$f-activity.txt" 2>&1 || true

    accepted=false
    if python3 platforms/mobile/g1_probe.py android \
        --framework "$f" --output-dir "$out" \
        --timeout-sec 90 --interval-sec 3; then
        accepted=true
    fi

    # Every diagnostic is best effort, but never blocks successful artifact
    # upload when the device disappears. Max total diagnostic overhead ~60s.
    timeout -k 2s 12s adb shell dumpsys activity activities \
        > "$out/$f-activity-state.txt" 2>&1 || true
    timeout -k 2s 12s adb shell dumpsys window windows \
        > "$out/$f-window-state.txt" 2>&1 || true
    timeout -k 2s 12s adb logcat -d -v time \
        > "$out/$f-logcat-tail.txt" 2>&1 || true
    timeout -k 2s 12s adb logcat -d -b crash -v time \
        > "$out/$f-crash.txt" 2>&1 || true
    kill "$stream_pid" 2>/dev/null || true
    wait "$stream_pid" 2>/dev/null || true
    cat "$out/$f-logcat-stream.txt" "$out/$f-logcat-tail.txt" > "$out/$f-logcat.txt"
    live="$(timeout -k 2s 12s adb shell pidof dev.gpui.mobile.example 2>/dev/null | tr -d '\r' || true)"
    echo "ANDROID_GPUI_PROCESS_DIAGNOSTIC:$f:after_probe=$live"

    # The GL backport must really run on Android; ordinary screen pixels alone
    # are insufficient if a different renderer implementation was selected.
    gpu_profile_logged=false
    if grep -Fq 'GPUI_ANDROID_GPU_PROFILE: backend=Gl texture_instances=true' "$out/$f-logcat.txt"; then
        gpu_profile_logged=true
    fi
    echo "ANDROID_GPUI_GLES_BACKPORT_DIAGNOSTIC:$f:$gpu_profile_logged"
    scene_logged=false
    if grep -Fq "BENCH_G1_SCENE_BUILT:$f:" "$out/$f-logcat.txt"; then
        scene_logged=true
    fi
    echo "ANDROID_GPUI_SCENE_LOG_DIAGNOSTIC:$f:$scene_logged"
    if [[ "$accepted" != true || -z "$live" || "$scene_logged" != true || "$gpu_profile_logged" != true ]]; then
        grep -iE 'ResumedActivity|mCurrentFocus|topResumedActivity' \
            "$out/$f-activity-state.txt" "$out/$f-window-state.txt" | tail -12 || true
        grep -iE 'gpui-mobile-example|FATAL|AndroidRuntime|Fatal signal|signal 11|emulator' \
            "$out/$f-logcat.txt" | tail -95 || true
        echo "GPUI_ANDROID_G1_NOT_VERIFIED:$f" >&2
        exit 1
    fi
    echo "GPUI_ANDROID_EMULATOR_HERMES_SCENE_RENDER_PASS:$f:pid=$live"
    timeout -k 2s 12s adb shell am force-stop dev.gpui.mobile.example || true
done
