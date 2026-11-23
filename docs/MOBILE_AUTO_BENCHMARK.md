# Hermes + Svelte/Solid six-platform automatic execution — implementation contract

Status: **G1 real mobile render evidence exists for Android Svelte/Solid (fresh emulator CI #45283713120) and iOS Svelte/Solid (fresh simulator CI #45283316517); G2/G3 are specified but NOT implemented.** An earlier Android G1 replay CI #45282165716 reused unchanged APKs to isolate the screenshot verifier fix; clean CI #45283713120 subsequently rebuilt both APKs and verified two fresh real screenshots. This document is not evidence of complete six-platform performance benchmarking.

## Objective and non-objectives

The same application functionality, the same Hermes HBC workload, and the same semantic Rust Mutation/GPUI renderer must run on Linux, Windows, macOS, Web, Android and iOS for BOTH Svelte and Solid. A GitHub Actions job must autonomously start each app, prove that it drew the correct scene, execute identical workloads when the embedded VM exists, and publish reproducible results.

- A successful `cargo check`, APK/.app build, PID, VM initialization, log line or a screenshot of an unrelated page **never** implies a GPUI render pass.
- A precomputed final Hermes scene rendered by GPUI **never** implies HBC ran on the target or live JS-to-GPUI mutation delivery.
- Fixed `sleep 8/25` must not be an acceptance gate; elapsed time only sets a retry timeout.
- Do not add a new agent, orchestrator or E2E framework. Shell + Python, GPUI and the existing Hermes/Rust code are sufficient.

## G1 — automatically boot and prove actual rendered scene (first)

**Acceptance:** On the SAME emulator/simulator, Svelte and Solid each install, start, actually draw `Router::Home` and pass scene-specific pixel checks, with a machine-readable result. A crash, wrong initial screen, emulator launcher, blank output or timeout must yield a failing CI job and preserve diagnostic artifacts.

### Files / contracts

| File | Responsibility |
|---|---|
| `platforms/mobile/prepare-upstream.sh` | Verify canonical JSON and patch pinned GPUI Mobile home + iOS root; enable `bench-auto` feature |
| `platforms/mobile/home.rs` | Validate JSON count=256/start=40/theme=light/48 tracks; optional `BENCH_G1_SCENE_BUILT` emitted exactly once by the Rust app |
| `platforms/mobile/g1_probe.py` | Poll actual ADB / simctl screenshots, validate them, atomically write `<framework>-g1.json`, fail closed |
| `platforms/mobile/verify-{android,ios}-image.py` | Verify Hermes Home screenshot pixels; reject an arbitrary app/splash/system screenshot |
| `platforms/mobile/test-android-emulator.sh` | Install/start both APKs; invoke shared G1 probe; save logcat, crash buffer and activity/window diagnostics |
| `platforms/mobile/build-ios.sh` | Build both static-linked simulator apps, install, launch, invoke shared G1 probe, save evidence |
| `.github/workflows/gpui-platform-probes.yml` | Scoped G1 CI, KVM & Simulator, artifact upload on both success and failure |

Feature `bench-auto` means **do the scene self-check automatically**, NOT “run Hermes performance benchmarks.” It is intentionally separate from `solid-demo` and should never silently turn a snapshot into a live HBC.

The application log `BENCH_G1_SCENE_BUILT:<framework>:count=256:rows=48` means only that the GPUI *element tree was constructed*. The HOST may output `BENCH_G1_RENDER_PASS:<platform>:<framework>:<attempts>` **only after** an actual device screenshot passes the scene verifier. No `BENCH_READY` generic marker until G2 is implemented; don't conflate these meanings.

Example G1 JSON (actual values supplied by CI, example is structural):

```json
{
  "schema": "gpui-mobile-g1/v1",
  "platform": "android",
  "framework": "svelte",
  "phase": "G1",
  "status": "PASS",
  "stage": "RENDER_PASS",
  "mode": "precomputed-hermes-scene",
  "actual_hermes_vm_on_device": false,
  "live_jsi_to_gpui": false,
  "elapsed_ms": 12430,
  "attempts": 4,
  "screenshot": "svelte.png",
  "evidence": "GPUI_ANDROID_HERMES_SCENE_PIXELS_PASS:..."
}
```

A failure JSON uses `status=FAIL`, `stage=RENDER_TIMEOUT`, and `error`. G1 numbers are startup/screenshot probe timings, **not native Hermes VM or FPS measurements**. Final CI acceptance additionally requires *both* variants' JSON `status=PASS` and existence of both screenshots. Run `python3 -m unittest discover -s platforms/mobile/tests -p 'test_*.py' -v` before pushing.

**Android renderer status (2026-11-24):** Community `gpui-mobile` remains pinned at `5fd54f4554263ae06753e90472c7f2e2ff5d7495` / `gpui-pre 0.3.6`. The isolated compatibility branch vendors the Apache-2.0 `gpui-pre-wgpu 0.3.6` crate, backports Zed PR #67323's GLES low-capability texture instance fallback, and enables a GLES-only wgpu Instance strictly in the Android emulator build. This resolved the verified compute Limits rejection and EGL Surface failure. Android AVD CI [#45283713120](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45283713120) freshly rebuilt both APKs and passed G1 for **both** Svelte and Solid with 1080×2340 screenshots (92.87%/92.90% matching scene pixels, 59 text bands each), scene markers, and live PIDs. Both `g1.json` artifacts record `actual_hermes_vm_on_device=false` and `live_jsi_to_gpui=false`. Vulkan backend crash analysis, real Android hardware and the G2/G3 live Hermes/JSI chain remain separate, unverified. Do not interpret renderer startup as HBC execution.

## G2 — actual embedded Hermes HBC → Rust → live GPUI frame

**Entrance requirement:** G1 mobile boot proof is stable, or run the live bridge prototype first on Linux while addressing mobile renderer problems independently.

1. **One persistent Hermes host:** Own Hermes VM + HBC module on a dedicated controlled runtime thread. Build HBC ahead of time; keep the same framework bundles (`Svelte` / `Solid`) and `shared/scene.js`. No DOM shim. Avoid creating or destroying VM for each update.
2. **Host callback `gpuiEmit(batch)`:** Keep the existing mutation array protocol `create/insert/remove/text/attr/event`. Hermes invokes native callback with an immutable batch; return to JS quickly. Use a bounded message queue and explicit failure/backpressure rules; no independent `console.log` file transport in final app. Record JS timestamp and receive timestamp from one monotonic clock domain.
3. **Rust atomic apply:** Reuse `crates/ui-mutation` (already verified with true HBC traces) as the canonical scene semantics. Reject unknown IDs, cycles, invalid anchors or partial batches. Ensure event handler identity remains owned by Hermes; Rust stores event subscription metadata only.
4. **GPUI adapter:** On GPUI UI thread, apply accepted batches to the view-model and request redraw. One dirty scene update should lead to the expected visible text/list/theme change; do not remount the full view on every event if incremental rendering is possible. Emit a *frame completion* acknowledgement only after actual rendering/present instrumentation, not after `render()` invocation.
5. **Event roundtrip:** Native input → stable target node/event ID → Hermes handler → new Mutation batch → Rust apply → GPUI invalidation → screenshot proves changed pixels. Run count changes `Count: 0→1→2`; keyed reorder; theme; 48 virtualized rows.
6. **Lifecycle:** Foreground/background, activity/surface recreation, VM shutdown, host callback failure and queue overflow must not strand the UI; record a specific FAIL state and release all native resources.

**G2 acceptance:** At least one real Linux GPUI window and one Chromium GPUI Canvas show a changed *post-event* frame from their own live Hermes VM; the exact same native host mechanism then builds for Windows/macOS and is ported to Android/iOS. The merged PR must attach evidence from a live process, not offline replay. Current real-HBC-to-Rust **offline** replay is proven by [run 45216113064](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45216113064), but this is not G2.

## G3 — deterministic cross-platform performance runs

**Entrance requirement:** G2 must provide actual event-to-present frame acknowledgements and stable, comparable workload semantics on each tested platform. Until then, existing seven-trial HBC data remain engine/scene benchmarks, not GPUI end-to-end results.

One shared workload manifest, compiled once for both frameworks:

| Workload ID | Identical operations | Required result |
|---|---|---|
| `counter-10000` | 10,000 logical updates | JS compute, mutation count, bridge delivery, UI invalidation |
| `virtual-list-500` | Scroll 500 items with identical 48-row viewport | update/GC/layout/frame percentiles |
| `keyed-reorder-1000x20` | 1,000 stable-key items reordered 20 times | correctness plus update & draw |
| `theme-50` | 50 light/dark changes | style/layout/draw |
| `event-1000` | 1,000 native input-to-present events | input→Hermes→Rust→frame latency |
| `cold-start` | Independent, fresh process launches | first verified frame & memory |

Use a **versioned result schema**. Record framework, target, exact HBC hash/build, GPUI commit, hardware/runner characteristics, workload SHA, warm-up, repetitions, time source, JS/bridge/apply/layout/draw/present timings, P50/P95/P99, CPU, peak RSS, and per-frame histogram. Keep `null` for missing measures, never `0`. Report independent process timings and GPU frame latency separately. Re-run A/B in alternating order, with 7+ samples and raw artifacts; do **not** compare absolute runner timings without hardware controls.

## Milestone stop criteria

- **G1 completed:** Android + iOS Svelte/Solid *correct-screen* screenshots and two PASS JSONs per platform, CI green. Failed screenshots preserved.
- **G2 completed:** Persistent embedded Hermes VM on each required platform genuinely changes a GPUI frame after an event; Rust update, timings, and screen evidence agree.
- **G3 completed:** All 12 platform×framework cases execute same workloads and export verified, correctly labeled raw measurements (missing/unsupported cases remain explicit failures).

Do not merge a draft feature and claim G1 solely because ARM64 APKs or iOS simulator builds succeed. The actual [mobile CI](https://github.com/tims-SP/rust-gpui-demo/actions/workflows/gpui-platform-probes.yml) is authoritative for individual run status.
