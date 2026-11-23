#!/usr/bin/env python3
"""G1 only: wait for an actually rendered Hermes-scene screenshot.

This script is a screenshot acceptance harness, NOT a JS/Hermes benchmark.
An Android/iOS activity, PID, compiled library, or screenshot file alone is
insufficient. Only a scene-specific pixel verifier can assert G1_RENDER_PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def capture_command(platform: str, screenshot: Path, device: str | None) -> list[str]:
    if platform == "android":
        return ["adb", "exec-out", "screencap", "-p"]
    if platform == "ios" and device:
        return ["xcrun", "simctl", "io", device, "screenshot", str(screenshot)]
    raise ValueError("iOS requires --device; supported platforms: android, ios")


def verify_command(platform: str, screenshot: Path) -> list[str]:
    validator = Path(__file__).with_name("verify-android-image.py" if platform == "android"
                                         else "verify-ios-image.py")
    return [sys.executable, str(validator), str(screenshot)]


def run_probe(platform: str, framework: str, output_dir: Path, device: str | None,
              timeout_sec: float, interval_sec: float) -> dict:
    screenshot = output_dir / f"{framework}.png"
    result_path = output_dir / f"{framework}-g1.json"
    started = time.monotonic()
    attempt = 0
    last_error = "no screenshot attempted"
    while True:
        attempt += 1
        try:
            # On iOS take a fresh path each attempt. Never accept a leftover
            # screenshot from an earlier install if simctl failed to overwrite it.
            capture_path = screenshot
            if platform == "ios":
                capture_path = output_dir / f"{framework}-capture.png"
                capture_path.unlink(missing_ok=True)
            cmd = capture_command(platform, capture_path, device)
            capture = subprocess.run(cmd, capture_output=True, timeout=15, check=False)
            if capture.returncode != 0:
                raise RuntimeError(f"screenshot failed rc={capture.returncode}: "
                                   f"{capture.stderr.decode(errors='replace')[:320]}")
            if platform == "android":
                if not capture.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise RuntimeError("adb screencap returned invalid PNG")
                screenshot.write_bytes(capture.stdout)
            else:
                if not capture_path.is_file():
                    raise RuntimeError("simctl returned success without writing screenshot")
                os.replace(capture_path, screenshot)
            if not screenshot.is_file() or screenshot.stat().st_size < 5000:
                raise RuntimeError("screenshot missing or implausibly small")
            verification = subprocess.run(verify_command(platform, screenshot),
                                          capture_output=True, text=True, timeout=15)
            if verification.returncode != 0:
                raise RuntimeError(verification.stderr.strip() or verification.stdout.strip()
                                   or "scene-specific pixel check failed")
            elapsed_ms = round((time.monotonic() - started) * 1000)
            result = {
                "schema": "gpui-mobile-g1/v1",
                "platform": platform, "framework": framework,
                "phase": "G1", "status": "PASS", "stage": "RENDER_PASS",
                "mode": "precomputed-hermes-scene",
                "actual_hermes_vm_on_device": False,
                "live_jsi_to_gpui": False,
                "elapsed_ms": elapsed_ms, "attempts": attempt,
                "screenshot": screenshot.name,
                "evidence": verification.stdout.strip(),
            }
            atomic_json(result_path, result)
            print(f"BENCH_G1_RENDER_PASS:{platform}:{framework}:{attempt}", flush=True)
            return result
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            last_error = str(exc)
            print(f"BENCH_G1_RETRY:{platform}:{framework}:{attempt}:{last_error[:120]}",
                  flush=True)
        if time.monotonic() - started >= timeout_sec:
            break
        time.sleep(min(interval_sec, max(0, timeout_sec - (time.monotonic() - started))))
    result = {
        "schema": "gpui-mobile-g1/v1",
        "platform": platform, "framework": framework,
        "phase": "G1", "status": "FAIL", "stage": "RENDER_TIMEOUT",
        "mode": "precomputed-hermes-scene",
        "actual_hermes_vm_on_device": False,
        "live_jsi_to_gpui": False,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "attempts": attempt, "screenshot": screenshot.name if screenshot.exists() else None,
        "error": last_error,
    }
    atomic_json(result_path, result)
    print(f"BENCH_G1_RENDER_TIMEOUT:{platform}:{framework}:{attempt}:{last_error[:240]}",
          file=sys.stderr, flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("android", "ios"))
    parser.add_argument("--framework", choices=("svelte", "solid"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", help="iOS simctl UDID; unused on Android")
    parser.add_argument("--timeout-sec", type=float, default=90)
    parser.add_argument("--interval-sec", type=float, default=3)
    args = parser.parse_args()
    if args.timeout_sec <= 0 or args.interval_sec <= 0:
        parser.error("timeouts and polling intervals must be positive")
    if args.platform == "ios" and not args.device:
        parser.error("iOS requires --device")
    result = run_probe(args.platform, args.framework, args.output_dir, args.device,
                       args.timeout_sec, args.interval_sec)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
