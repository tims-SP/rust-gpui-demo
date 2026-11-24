# Six-platform Hermes + Svelte/Solid — verified execution status

Updated: 2026-11-24 UTC. Treat **G1 render proof**, **replay callback timing**, **Hermes HBC/JSI → Rust mutation**, **Hermes/JSI → live GPUI**, and **GPU Present/E2E** as separate acceptance gates. A successful gate must never be reused as evidence for a later gate.

## Current acceptance matrix

The checked-in `benchmarks/results/latest.json` describes the 12 platform/framework cells using precomputed Hermes scene JSON for the GPUI scene-replay measurements:

| Gate | Current result | Meaning |
|---|---:|---|
| Real GPUI scene rendered / screenshot verified | **12/12** | All six platform targets have both Svelte and Solid G1 render evidence |
| GPUI update → Render callback replay metrics | **8/12** | Linux, Windows, Web and macOS; iOS/Android timing cells remain unmeasured |
| In-process Hermes HBC → JSI → Rust Scene | **2/2 frameworks** | Real Svelte and Solid bundles executed through Hermes and delivered mutations to Rust Scene |
| Live Hermes/JSI → GPUI window | **6/6 desktop cells across Linux + macOS + Windows** | Real Svelte and Solid HBC ran inside native GPUI apps on all three desktop OSes; each cell delivered 120 interactive mutation batches and at least 20 measured Render callbacks |
| GPU Present timing | **0/12** | Not instrumented / measured |
| Full platform E2E timing | **0/12** | Not yet accepted |

The replay matrix is intentionally not rewritten to claim live Hermes execution. Its `scene_source` remains `precomputed-Hermes-JSON`. Live integration metrics are stored separately in `benchmarks/results/live-hermes.json`. GPU Present and full E2E remain unmeasured.

## Verified evidence

- **Linux real GPUI windows and replay callbacks**: [Run 45248284872](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248284872), both frameworks; Svelte P50/P95/P99 1027/16127/32520 µs, Solid 1319/16227/16277 µs.
- **Windows real GPUI windows and replay callbacks**: [Run 45248296457](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248296457), both frameworks; Svelte 2258/16047/18496 µs, Solid 2533/16891/18220 µs.
- **Web GPUI Canvas and replay callbacks**: [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392), both frameworks. This is the actual GPUI Web Canvas; its replay input is still precomputed Hermes scene data.
- **macOS real windows and replay callbacks**: [Run 45293663677](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45293663677), commit `615f4c1`, artifact `gpui-macos-svelte-solid-real-window-evidence`. The fix updates the real root `WindowHandle` and calls `window.refresh()` in the same update transaction, while requesting display-link frames on macOS. Svelte and Solid each applied 120/120 updates and produced 120/120 Render callbacks. Svelte P50/P95/P99 10612/14406/14531 µs; Solid 10486/14671/25503 µs. This run is precomputed-scene replay, not live Hermes.
- **iOS simulator G1**: [Run 45286884084](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45286884084), head `59cd286`, both .app bundles and screenshots passed. Svelte readiness 21075 ms (2 attempts); Solid 1906 ms (1 attempt). These values include build/launch/polling and are not frame latency; Hermes does not run on-device in this test.
- **Android x86_64 AVD G1**: [Run 45291575255](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45291575255), PR #5 head `e40eebf`, both APKs built and both screenshots passed. Svelte readiness 6515 ms (2 attempts); Solid 6130 ms (2 attempts). These are G1 readiness values, not frame latency; Hermes does not run on-device in this test.
- **In-process Hermes HBC → JSI → Rust Scene**: [Run 45295492997](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45295492997), artifact `live-svelte-solid-hermes-jsi-rust-scene`. The real Svelte and Solid bundles were compiled to HBC and executed in persistent in-process Hermes VMs. Each framework sent eight JSI mutation batches into the Rust `Scene`; Svelte applied 53096 operations and Solid 47018. The same VM then dispatched an actual registered framework event. HBC version 99; engine digest `sha256-ee46fde82bc5bea2cfa32b2418618efb20f50c4f95c731032b01a9654bc92647`. This is Rust Scene proof outside a GPUI window.

## Live Hermes → GPUI integration

The current PR #9 branch contains `crates/hermes-gpui-spike`, a thread-affine native Hermes/JSI bridge and a `SceneRuntime` that owns the Rust scene. `platforms/native/bench_view.rs` renders that live scene in a real GPUI window and drives 120 real framework-HBC click events. The measured interval begins at the Rust JSI callback entry and ends at the GPUI `Render` callback; it explicitly does **not** claim GPU Present.

- **Current PR #9**: [Draft PR #9](https://github.com/tims-SP/rust-gpui-demo/pull/9), latest head `919be5d` at this update. PR #9 remains Draft and unmerged.
- **macOS live-window acceptance**: [Run 45297305246](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45297305246), head `8388c75`, artifact `gpui-macos-live-hermes-svelte-solid-evidence`. Both real HBC framework bundles executed inside the official GPUI app's persistent Hermes VM. Each delivered exactly 120 interactive mutation batches, applied 120/120 updates, and produced 120/120 Render callbacks. Svelte P50/P95/P99 10387/13733/14021 µs; Solid 10139/13805/15484 µs. Both 1024×768 real macOS screenshots passed pixel verification. These metrics measure JSI callback entry → Render callback, not GPU Present.
- **Windows live-window acceptance**: [Run 45301213456](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301213456), head `b927b19`, artifact `windows-live-hermes-svelte-solid-evidence`. The MSVC build explicitly used C++17 and completed. Both HBC framework bundles ran in persistent Hermes VMs; each delivered 120/120 interactive JSI mutation batches, 120/120 Render callbacks, and passed 1024×768 screenshot pixel checks. Svelte P50/P95/P99 4500/17151/17850 µs; Solid 3645/17475/17964 µs. These are JSI callback entry → Render callback metrics, not GPU Present.
- **Linux live-window acceptance**: [Run 45301209053](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301209053), head `b927b19`, artifact `gpui-linux-live-hermes-svelte-solid-evidence`. Both real HBC bundles ran in the official GPUI app. Each applied 120/120 interactive updates and passed screenshot pixel verification (1440×1000). Svelte: 49/120 valid Render callbacks, P50/P95/P99 11224/13264/13544 µs; Solid: 51/120, 3934/15859/21466 µs. The sample threshold remains 20; these are live JSI-entry→Render measurements, not GPU Present.
- **Windows live-window first attempt**: [Run 45298135997](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45298135997) failed because the MSVC command emitted by cc-rs did not contain `/std:c++17`; Hermes public headers then failed on `std::string_view`, `std::optional` and `std::variant`. The build script now passes `/std:c++17` explicitly for `target_env=msvc`; corrected live run [45301213456](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301213456) passed at head `b927b19`.
- **macOS live-window frame-scheduling retry**: [Run 45301205161](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301205161), head `b927b19`, compiled but delivered only 5 Render callbacks paired with no interactive updates. It still applied all 120 HBC/JSI updates. Retry [Run 45302554758](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302554758), head `dfd898b`, explicitly requests a display-link frame on every root-window update and calls `AsyncApp::refresh()`; build was still running at the latest poll.
- **iOS live-Hermes simulator retry**: first run [45301289892](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45301289892) compiled the bridge but failed at `open_window`; gpui-pre 0.3.6 requires an `Entity` return. The harness now uses `cx.new`; corrected iOS-only run [45302935498](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302935498), head `7a089e7`, remains at the Simulator build/run step.
- **Android live-Hermes ARM64**: first run [45302086301](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302086301) reached the emulator path check and exposed a bad PATH-resolved QEMU location. The next run [45302939129](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45302939129) failed earlier because `yes | sdkmanager --licenses` returned expected SIGPIPE under `pipefail`. Both defects are fixed: SDK-root emulator invocation and a license pipeline that preserves `sdkmanager`'s status but ignores producer SIGPIPE. Corrected Android-only run [45303432502](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45303432502), head `919be5d`, is now installing Android SDK/NDK/emulator packages. No live Android Hermes result is accepted yet. Android cleanup is device-aware and bounds logcat to 12 seconds.
- **First macOS live-window attempt**: [Run 45295907751](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45295907751), head `8277139`, is diagnostic only: Svelte reached 120/120 callbacks, but the job failed later in the metrics-extraction shell command because of a double-escaped continuation. The subsequent corrected workflow and strict callback-batch accounting are now covered by [Run 45297305246](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45297305246).

## Pinned components and constraints

- Native Hermes/Ibex2 source: `expo/ibex` commit `24cd0ae8cdd20106bed04cd3a4a2378d1dd81995`; Hermes upstream source pin `d412d3bd851278712c20cca25d094e32641a0465`.
- Desktop/Web GPUI source: Zed `v1.29.3`.
- Mobile GPUI is a separate community fork/API line (`gpui-mobile` commit `5fd54f4554263ae06753e90472c7f2e2ff5d7495`, based on `gpui-pre 0.3.6`). Do not imply it is the same Rust GPUI implementation as desktop.
- PR #9 and PR #5 are both open Draft PRs; neither is merged.
- Do not use CPU-only HBC timing, precomputed JSON replay, screenshot readiness, or Render-callback timing as GPU Present or end-to-end latency.

## Next acceptance gate

Complete the corrected Linux, Windows and macOS desktop live-Hermes runs, plus the separate iOS Simulator and Android ARM64 GPUI Mobile runs. The mobile fork uses the separate `gpui-mobile` / `gpui-pre 0.3.6` API line, so its live evidence remains a distinct platform acceptance path. GPU Present and full E2E remain separate future gates.
