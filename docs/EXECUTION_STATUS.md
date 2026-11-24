# Six-platform Hermes + Svelte/Solid — verified execution status

Updated: 2026-11-24 UTC. Treat **G1 render proof**, **replay callback timing**, **Hermes HBC/JSI → Rust mutation**, **Hermes/JSI → live GPUI**, and **GPU Present/E2E** as separate acceptance gates. A successful gate must never be reused as evidence for a later gate.

## Current acceptance matrix

The checked-in `benchmarks/results/latest.json` describes the 12 platform/framework cells using precomputed Hermes scene JSON for the GPUI scene-replay measurements:

| Gate | Current result | Meaning |
|---|---:|---|
| Real GPUI scene rendered / screenshot verified | **12/12** | All six platform targets have both Svelte and Solid G1 render evidence |
| GPUI update → Render callback replay metrics | **8/12** | Linux, Windows, Web and macOS; iOS/Android timing cells remain unmeasured |
| In-process Hermes HBC → JSI → Rust Scene | **2/2 frameworks** | Real Svelte and Solid bundles executed through Hermes and delivered mutations to Rust Scene |
| Live Hermes/JSI → GPUI window | **Pending** | macOS integration workflow is compiling the embedded Hermes GPUI app |
| GPU Present timing | **0/12** | Not instrumented / measured |
| Full platform E2E timing | **0/12** | Not yet accepted |

The replay matrix is intentionally not rewritten to claim live Hermes execution. Its `scene_source` remains `precomputed-Hermes-JSON`, and the Hermes-in-GPUI, live-JSI, GPU and E2E fields remain false/null until their own evidence exists.

## Verified evidence

- **Linux real GPUI windows and replay callbacks**: [Run 45248284872](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248284872), both frameworks; Svelte P50/P95/P99 1027/16127/32520 µs, Solid 1319/16227/16277 µs.
- **Windows real GPUI windows and replay callbacks**: [Run 45248296457](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248296457), both frameworks; Svelte 2258/16047/18496 µs, Solid 2533/16891/18220 µs.
- **Web GPUI Canvas and replay callbacks**: [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392), both frameworks. This is the actual GPUI Web Canvas; its replay input is still precomputed Hermes scene data.
- **macOS real windows and replay callbacks**: [Run 45293663677](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45293663677), commit `615f4c1`, artifact `gpui-macos-svelte-solid-real-window-evidence`. The fix updates the real root `WindowHandle` and calls `window.refresh()` in the same update transaction, while requesting display-link frames on macOS. Svelte and Solid each applied 120/120 updates and produced 120/120 Render callbacks. Svelte P50/P95/P99 10612/14406/14531 µs; Solid 10486/14671/25503 µs. This run is precomputed-scene replay, not live Hermes.
- **iOS simulator G1**: [Run 45286884084](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45286884084), head `59cd286`, both .app bundles and screenshots passed. Svelte readiness 21075 ms (2 attempts); Solid 1906 ms (1 attempt). These values include build/launch/polling and are not frame latency; Hermes does not run on-device in this test.
- **Android x86_64 AVD G1**: [Run 45291575255](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45291575255), PR #5 head `e40eebf`, both APKs built and both screenshots passed. Svelte readiness 6515 ms (2 attempts); Solid 6130 ms (2 attempts). These are G1 readiness values, not frame latency; Hermes does not run on-device in this test.
- **In-process Hermes HBC → JSI → Rust Scene**: [Run 45295492997](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45295492997), artifact `live-svelte-solid-hermes-jsi-rust-scene`. The real Svelte and Solid bundles were compiled to HBC and executed in persistent in-process Hermes VMs. Each framework sent eight JSI mutation batches into the Rust `Scene`; Svelte applied 53096 operations and Solid 47018. The same VM then dispatched an actual registered framework event. HBC version 99; engine digest `sha256-ee46fde82bc5bea2cfa32b2418618efb20f50c4f95c731032b01a9654bc92647`. This is Rust Scene proof outside a GPUI window.

## Live Hermes → GPUI integration under test

The current PR #9 branch contains `crates/hermes-gpui-spike`, a thread-affine native Hermes/JSI bridge and a `SceneRuntime` that owns the Rust scene. `platforms/native/bench_view.rs` now renders that live scene in a real GPUI window and drives 120 real framework-HBC click events. The measured interval begins at the Rust JSI callback entry and ends at the GPUI `Render` callback; it explicitly does **not** claim GPU Present.

- **Current PR #9**: [Draft PR #9](https://github.com/tims-SP/rust-gpui-demo/pull/9), latest branch head recorded during this update: `cff1c49`.
- **First macOS live-window attempt**: [Run 45295907751](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45295907751), head `8277139`. The official GPUI app compiled and linked with the embedded Hermes bridge. The Svelte HBC ran inside that app and delivered 120/120 real GPUI Render callbacks (initial log: P50/P95/P99 8620/12262/24387 µs). The job then failed in the metrics-extraction shell command because a YAML-escaped double backslash broke argument continuation; the Solid window had not yet run. This first attempt is diagnostic evidence only, not the final two-framework acceptance.
- The shell invocation is now a single line. The latest branch also separates initial and interactive HBC batch counts and starts latency at Rust JSI callback entry (`b4e40d8`), with source/metric checks covered by unit tests. Rerun at the latest PR #9 head is required before accepting either framework's final live metric.

## Pinned components and constraints

- Native Hermes/Ibex2 source: `expo/ibex` commit `24cd0ae8cdd20106bed04cd3a4a2378d1dd81995`; Hermes upstream source pin `d412d3bd851278712c20cca25d094e32641a0465`.
- Desktop/Web GPUI source: Zed `v1.29.3`.
- Mobile GPUI is a separate community fork/API line (`gpui-mobile` commit `5fd54f4554263ae06753e90472c7f2e2ff5d7495`, based on `gpui-pre 0.3.6`). Do not imply it is the same Rust GPUI implementation as desktop.
- PR #9 and PR #5 are both open Draft PRs; neither is merged.
- Do not use CPU-only HBC timing, precomputed JSON replay, screenshot readiness, or Render-callback timing as GPU Present or end-to-end latency.

## Next acceptance gate

Finish the current macOS live-Hermes build and window run. If it passes, rerun it at the latest PR #9 head so the callback-entry timing change is included, inspect both screenshots and both JSON records, then record live metrics separately from the 12-cell replay matrix. If it fails, fix the first concrete build/runtime failure and rerun the same gate. Do not advance the live-JSI or E2E matrix cells based on the already-passing Rust Scene-only test.
