# Six-platform Hermes + Svelte/Solid — verified execution status

Updated: 2026-11-23 UTC. **Build**, **Hermes HBC execution**, **GPUI rendering**, and **live JSI→Rust→GPUI updates** are independent acceptance gates. A scene snapshot drawn by GPUI does **not** imply Hermes is running on that platform.

## Pinned sources and preservation

The pre-reset tree remains recoverable under [archive/pre-six-platform-hermes-2026-11-23](../../tree/archive/pre-six-platform-hermes-2026-11-23). Native Ibex2 is pinned to `24cd0ae8cdd20106bed04cd3a4a2378d1dd81995`, Hermes to `d412d3bd851278712c20cca25d094e32641a0465`, desktop/Web GPUI to Zed `v1.29.3`. Mobile compatibility uses community gpui-mobile `5fd54f4554263ae06753e90472c7f2e2ff5d7495`, which depends on **gpui-pre 0.3.6**, not the same GPUI API.

## Evidence matrix

| Platform | HBC running on platform | GPUI Build | Actual GPUI Run / Render | Live JSI→Rust Mutation |
|---|---|---|---|---|
| Linux | **PASS**, native Ibex2 for both | **PASS** | **PASS**, two real windows with screenshots | Not implemented |
| Windows | Not yet (Hermes scenes imported) | **PASS** | **PASS**, two real windows / desktop screenshots | Not implemented |
| macOS | Not yet (Hermes scenes imported) | **PASS** | Real-window test pending | Not implemented |
| Web | **PASS**, Hermes Wasm in Chromium | **PASS** | **PASS**, actual GPUI Web Canvas for both | Not implemented; browser→Hermes→host mutations only |
| Android | Not yet (precomputed scene import) | **PASS**, ARM64 dual scene APKs | Android AVD launch/screenshot pending | Not implemented |
| iOS | Not yet (precomputed scene import) | **PASS** upstream GPUI iOS backend check | Two .app bundles and Simulator run pending | Not implemented |

### Independent source runs

- **Native Hermes/Svelte/Solid**: [45199793980](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45199793980), both frameworks with 1000 click roundtrips and keyed reorder.
- **Linux official GPUI real windows**: [45196783362](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45196783362), imported actual Hermes scene JSONs and screenshot pixel checks.
- **Windows official GPUI real windows**: [45203114141](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45203114141), Svelte and Solid; desktop screenshot accepted.
- **Web HBC in real Chromium / interactive host event**: [45201423339](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45201423339); one additional browser-originated event entered the same Hermes VM and returned a text mutation.
- **Official GPUI Web Canvas**: [45204482618](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45204482618), actual 1200×950 screenshots, 47 foreground text bands for each framework.
- **Official macOS + iOS backend compile probes**: [45206809147](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45206809147), compiled successfully, not run/render evidence.
- **Android GPUI Mobile ARM64 APK**: [45207776184](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45207776184), Android **job** passed; workflow's overall conclusion may differ due unrelated macOS/iOS jobs.
- **Android two imported Hermes-scene ARM64 APKs**: [45209285192](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45209285192), Android **job** passed; real JSON parity and distinct Svelte/Solid APKs, not execution of Hermes on the phone.
- **Seven alternating native Hermes HBC performance trials**: [45203456152](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45203456152), real process timings, not GPUI frame times. See artifact `REPORT.md`.
- **Android x86_64 AVD / iOS simulator mobile experiments**: [45211655482](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45211655482), pending real launch evidence on `feature/mobile-scene-parity`.
- **macOS native window/screenshot experiment**: [45212271889](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271889), pending.

## Correctness caveats

1. Svelte/Solid both use official custom/non-DOM renderers and one semantic JS host scene/mutation model. Raw mutation counts alone are **not** a speed ranking. For the expanded synthetic case, native Hermes reported Svelte 52,465 mutations and Solid 46,754.
2. Prior Solid list workload regenerated non-stable object keys and was corrected. Do not compare obsolete results.
3. Mobile GPUI uses a different fork. The mobile adapter shares the **actual final Hermes scene JSON**, not the same compiled GPUI Rust implementation or an embedded Hermes runtime.
4. The Web Canvas and native desktop GPUI programs currently import final Hermes snapshots. The Chromium Hermes JSI event QA and GPUI Canvas QA are **separate processes**; full live UI integration remains unverified.
5. Cross-platform absolute timings are not comparable across runner hardware. Missing measurements are unmeasured, not zero.

## Next acceptance gate

Implement the identical live Mutation batch schema inside a persistent Hermes host, feed it into the Rust GPUI scene adapter on a real window/Canvas, produce two different frame screenshots before/after a click or list move, and measure JS propagation, bridge apply, layout/draw and frame time separately. After that, validate native Hermes execution and real touch rendering on Android/iOS, and macOS real-window proof.
