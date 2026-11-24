# Six-platform Hermes + Svelte/Solid evidence matrix

This report separates the 12-cell precomputed-scene replay matrix from the newer
real in-process Hermes HBC → JSI → Rust mutation proof. The replay matrix does
**not** claim live Hermes→JSI→GPUI or GPU presentation performance.

| Platform | Framework | Actual GPUI scene | Update→Render P50 | P95 | P99 | Mobile G1 readiness | CI evidence |
|---|---|---|---:|---:|---:|---|---|
| linux | svelte | PASS | 1027 µs | 16127 µs | 32520 µs | — | [Run 45248284872](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248284872) |
| linux | solid | PASS | 1319 µs | 16227 µs | 16277 µs | — | [Run 45248284872](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248284872) |
| windows | svelte | PASS | 2258 µs | 16047 µs | 18496 µs | — | [Run 45248296457](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248296457) |
| windows | solid | PASS | 2533 µs | 16891 µs | 18220 µs | — | [Run 45248296457](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248296457) |
| macos | svelte | PASS | 10612 µs | 14406 µs | 14531 µs | — | [Run 45293663677](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45293663677) |
| macos | solid | PASS | 10486 µs | 14671 µs | 25503 µs | — | [Run 45293663677](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45293663677) |
| web | svelte | PASS |  10580 µs | 24795 µs | 25150 µs | — | [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392) |
| web | solid | PASS |  10815 µs | 25945 µs | 88085 µs | — | [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392) |
| ios | svelte | PASS | — | — | — | 21075 ms (2 attempts) | [Run 45286884084](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45286884084) |
| ios | solid | PASS | — | — | — | 1906 ms (1 attempt) | [Run 45286884084](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45286884084) |
| android | svelte | PASS | — | — | — | 6515 ms (2 attempts) | [Run 45291575255](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45291575255) |
| android | solid | PASS | — | — | — | 6130 ms (2 attempts) | [Run 45291575255](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45291575255) |

**Metric definitions:** P50/P95/P99 = elapsed microseconds between scheduled
GPUI state mutation and the next `Render` callback. This excludes real
GPU submission/presentation and any Hermes runtime/JSI propagation.
Each platform uses different runner hardware: compare Svelte/Solid only
within the same run and don't treat mobile G1 polling time as FPS or
framework latency. iOS/Android G1 includes screenshot polling and cold
boot effects, and is not a clean Svelte-vs-Solid speed comparison.

**Measured replay cells:** 8/12.
**Rendered cells:** 12/12.
**Live JSI→Rust Scene integration:** PASS for both frameworks in [Run 45295492997](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45295492997).
**Live JSI→GPUI window integration:** PASS on macOS and Windows for both frameworks (4/4 desktop cells); Linux and iOS/Android mobile runs are being revalidated separately.
**GPU Present / full six-platform end-to-end benchmark:** NOT COMPLETE.

**Web evidence update (2026-11-23 UTC):** [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392), commit `ab466b89`, artifact `gpui-web-official-canvas-svelte-solid`: both Svelte and Solid JSON files report `status=PASS`, `scheduled_updates=120`, `applied_updates=120`, with 34/35 render callbacks and screenshot PNGs. These are GPUI timer-driven replay callback timings, **not** live Hermes HBC/JSI or GPU Present timings. Chromium console reports a wgpu resize poll timeout warning, but the replay completion markers and metrics were emitted.

**Android GLES render evidence (2026-11-23 UTC):** [Run 45283713120](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45283713120), branch `fix/android-gles-render-fallback`, commit `7d416c782`, artifact `android-emulator-hermes-svelte-solid-evidence`. Downloaded and inspected `svelte-g1.json`, `solid-g1.json`, screenshots `svelte.png` and `solid.png` (1080×2340), emulator logcat and APKs. Both JSON files state `RENDER_PASS` with pixel coverage 92.87%/92.90%, 59 bands. These are **precomputed Hermes scenes**, with `actual_hermes_vm_on_device=false` and `live_jsi_to_gpui=false`; screenshot readiness includes polling and cannot be used as P50/P95/P99. The GLES fix remains on a separate branch, not merged to `main` or PR #9.


**Android PR #5 revalidation (2026-11-23 UTC):** [Run 45291575255](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45291575255), head `e40eebf`, artifact `android-emulator-hermes-svelte-solid-evidence`. Both x86_64 AVD APKs built and both real Android GPUI scenes passed screenshot pixel verification (1080×2340; coverage 92.87%/92.90%; 59 bands). The 6515/6130 ms values are G1 probe elapsed times, not frame latency.

**iOS PR #5 simulator revalidation (2026-11-23 UTC):** [Run 45286884084](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45286884084), head `59cd286`, artifact `gpui-mobile-hermes-svelte-solid-ios-simulator`. Both .app bundles built and passed real simulator screenshot pixel verification (1206×2622). The Svelte/Solid G1 readiness values are 21075/1906 ms, respectively; these include launch/polling effects, not frame latency. Hermes was not running on-device and live JSI remained false.

**macOS Render callback revalidation (2026-11-24 UTC):** [Run 45293663677](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45293663677), commit `615f4c1`, artifact `gpui-macos-svelte-solid-real-window-evidence`. Both real GPUI windows received all 120 scheduled updates; 120/120 were observed by Render callbacks. Metrics are precomputed Hermes scene replay only, not live JSI or GPU Present.

**Live Hermes HBC → JSI → Rust proof (2026-11-24 UTC):** [Run 45295492997](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45295492997), artifact `live-svelte-solid-hermes-jsi-rust-scene`. The actual Svelte and Solid bundles were compiled to HBC and executed in persistent in-process Hermes VMs. Each framework sent eight JSI mutation batches to the Rust Scene; Svelte applied 53,096 operations and Solid 47,018, including a real registered interactive event. HBC version 99; engine digest `sha256-ee46fde82bc5bea2cfa32b2418618efb20f50c4f95c731032b01a9654bc92647`. This validates Hermes→JSI→Rust Scene, not GPUI window rendering, GPU Present or end-to-end latency.

**Live Hermes HBC → JSI → macOS GPUI window (2026-11-24 UTC):** [Run 45297305246](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45297305246), head `8388c75`, artifact `gpui-macos-live-hermes-svelte-solid-evidence`. Both framework bundles ran in persistent in-process Hermes VMs. Svelte and Solid each delivered 120/120 interactive JSI mutation batches and 120/120 Render callbacks, with screenshot pixel checks passing. Svelte JSI-entry→Render P50/P95/P99: 10387/13733/14021 µs; Solid: 10139/13805/15484 µs. This is live GPUI Render timing, not GPU Present or E2E. Full measurements are in `benchmarks/results/live-hermes.json`.


**Live Hermes HBC → JSI → Windows GPUI window (2026-11-24 UTC):** [Run 45301213456](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301213456), head `b927b19`, artifact `windows-live-hermes-svelte-solid-evidence`. Both Svelte and Solid HBC bundles ran in persistent in-process Hermes VMs inside real official GPUI windows. Both delivered 120/120 interactive mutation batches, 120/120 Render callbacks and passed 1024×768 screenshot pixel checks. Svelte JSI-entry→Render P50/P95/P99: 4500/17151/17850 µs; Solid: 3645/17475/17964 µs. This is not GPU Present or E2E.


## Stage-by-stage acceptance

| Stage | Current result | Evidence / interpretation |
|---|---|---|
| Svelte/Solid HBC build | PASS, 2/2 | Actual `svelte.hbc` and `solid.hbc` artifacts; HBC bytecode v99 |
| Hermes VM execution | PASS | Persistent in-process Hermes VM executed both HBC bundles |
| JSI → Rust Scene | PASS, 2/2 | 8 mutation batches per framework; 53,096 Svelte / 47,018 Solid scene operations |
| JSI → GPUI | PASS, 4/12 | Real in-process bridge on macOS and Windows, both frameworks |
| GPUI Render callbacks | PASS, 4/4 live cells | 120/120 interactive updates observed by Render per cell; screenshots verified |
| JSI-entry → GPUI Render latency | MEASURED, 4/12 | P50/P95/P99 recorded below; this is not GPU Present |
| GPU submission / Present | NOT MEASURED, 0/12 | No trustworthy present/fence timestamp in the current artifacts |
| Full six-platform end-to-end | NOT MEASURED, 0/12 | No cell currently covers the complete production path through presentation |

## Live Hermes HBC → JSI → GPUI Render measurements

These results are separate from the precomputed-scene matrix above. They execute the actual Svelte/Solid HBC in a persistent in-process Hermes VM, send real JSI mutations into the same app's GPUI view, and measure from JSI mutation entry to the next GPUI `Render` callback. They are **not** GPU submission/presentation timings.

| Platform | Framework | HBC VM | Interactive JSI batches | Render callbacks for updates | P50 | P95 | P99 | Screenshot | CI run |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| macOS | Svelte | PASS | 120/120 | 120/120 | 10387 µs | 13733 µs | 14021 µs | 1024×768 verified | [45297305246](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45297305246) |
| macOS | Solid | PASS | 120/120 | 120/120 | 10139 µs | 13805 µs | 15484 µs | 1024×768 verified | [45297305246](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45297305246) |
| Windows | Svelte | PASS | 120/120 | 120/120 | 4500 µs | 17151 µs | 17850 µs | 1024×768 verified | [45301213456](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301213456) |
| Windows | Solid | PASS | 120/120 | 120/120 | 3645 µs | 17475 µs | 17964 µs | 1024×768 verified | [45301213456](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301213456) |

Windows evidence was downloaded and checked from artifact `windows-live-hermes-svelte-solid-evidence`: both runtime logs contain `GPUI_LIVE_HERMES_VM_READY`, `GPUI_WINDOW_CREATED`, the complete `GPUI_REPLAY_BENCH_RESULT` JSON and `GPUI_REPLAY_BENCH_PASS`; both PNGs are 1024×768 and nonblank. macOS evidence was downloaded and checked from artifact `gpui-macos-live-hermes-svelte-solid-evidence`; both metrics JSONs report 120/120 interactive JSI batches and Render callbacks, and both 1024×768 screenshots contain rendered pixels.

**Live Hermes HBC → JSI → Rust Scene (before GPUI):** [Run 45301192353](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301192353) passed for both frameworks. Actual HBC files were present in the downloaded artifact (Svelte 190,719 bytes; Solid 44,302 bytes; HBC bytecode v99). Runtime logs report 8 JSI mutation batches each, with 53,096 Svelte and 47,018 Solid Rust Scene operations. This proves HBC execution and JSI→Rust Scene application, but by itself does not prove GPUI Render.

**Current live integration coverage:** 4/12 cells (macOS + Windows). The separate precomputed-scene matrix remains 12/12 rendered and 8/12 with replay callback P50/P95/P99. `gpu_present_latency_ms` and `end_to_end_latency_ms` remain null for every live cell; GPU Present and full end-to-end performance are **not measured**.

**In-flight platform revalidation (2026-11-24 UTC):** Linux live GPUI/Hermes [Run 45301209053](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301209053), macOS rerun [Run 45302554758](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302554758), and iOS Simulator [Run 45302935498](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302935498) were still running at the latest check. Android run [45302086301](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302086301) failed at a PATH-resolved emulator invocation that searched for missing `qemu-system-i386`. The first explicit-SDK-path fix in commit `7a089e7` exposed a second, earlier failure in [Run 45302939129](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302939129): `yes | sdkmanager --licenses` returned a broken-pipe error because `pipefail` was enabled. The workflow now isolates that pipeline from `pipefail` and removes the remaining PATH-resolved emulator invocation. Android is not counted as live-Hermes pass until a new run reaches real emulator execution and produces metrics plus screenshots.
