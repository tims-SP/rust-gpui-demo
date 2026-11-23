# Six-platform Hermes + Svelte/Solid actual execution status

Updated: 2026-11-23. Source of truth is linked GitHub Actions run logs/artifacts, not a claim inferred from a successful build.

## Clean reset and preservation

- The pre-test full repo is preserved on branch [archive/pre-six-platform-hermes-2026-11-23](../../tree/archive/pre-six-platform-hermes-2026-11-23).
- The current branch was rebuilt from an empty Git tree with no history rewriting.
- Both Svelte 5 Custom Renderer and Solid Universal Renderer use the exact same JS scene graph and Mutation API.

## Confirmed execution

| Stage | Result | Evidence |
|---|---|---|
| Hermes / Ibex2 Linux HBC with BOTH Svelte+Solid | **PASS** | [45197307921](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45197307921) |
| Same JS source/HBC engine revision in true Chromium Hermes Wasm | **PASS** | [45198355349](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45198355349) |
| Linux official GPUI REAL WINDOW from BOTH actual Hermes scene JSONs | **PASS** | [45196783362](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45196783362), [two pixel-checked screenshots](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45196783362/artifacts/14830745261) |
| Windows official GPUI same Rust scene source compiled on windows-2025 | **BUILD PASS** (RUN/RENDER pending) | [45199068505](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45199068505) |
| Android GPUI Mobile upstream ARM64 example cross-compiled | **BACKEND BUILD PASS** (Hermes app/run pending) | [45199068505](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45199068505) |
| macOS GPUI compiled and run | Not yet verified: macOS CI job not scheduled / retried | [45199068505](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45199068505) |
| iOS GPUI simulator compiled and run | Not yet verified: CI job cancelled before execution | [45199068505](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45199068505) |
| Web official GPUI Web CANVAS rendering | CI started; independent from earlier successful Hermes-Wasm HBC proof | [45200902301](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45200902301) |

## Benchmark correctness and limitations

- Original Solid generated new row objects on every virtual-window shift, invalidating a fair comparison. Corrected Solid to stable primitive key IDs; actual native Hermes output dropped from 11,826 to 546 update operations on that initial workload. Svelte had 909. Do not use the original Solid result.
- A later change added 1,000 event round-trips and 20 keyed reorder cycles. Both frameworks passed [the updated HBC scene correctness gate 45199793980](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45199793980). For this synthetic workload, a single run contained 46,754 total Solid and 52,465 total Svelte mutations; this is **not a stable speed ranking**.
- Native same-runner 7-trial process measurements with wall/RSS and integrity assertions are tracked by [45201785545](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45201785545). The run URL is 45201785545; do not publish performance numbers until it completes.
- Engine-level scene updates and GPUI final-scene rendering are separate proven components. **A live bidirectional JSI → Rust GPUI Mutation bridge has not been built or measured.**
- Actual Android/iOS apps, macOS/Windows GUI runs, Web GPUI canvas and true frame-to-frame GPU measurements require their own evidence.
- Platform result classification: BUILD, RUN (Hermes), and RENDER (GPUI) are separate checkboxes; do not conflate them.

## Code and authoritative reference implementations

- [Svelte Custom Renderer](https://svelte.dev/docs/svelte/custom-renderers)
- [Solid Universal Renderer](https://github.com/solidjs/solid/blob/main/packages/solid/universal/README.md)
- [Ibex2 Rust + Hermes](https://github.com/expo/ibex)
- [Zed official GPUI](https://github.com/zed-industries/zed/tree/main/crates/gpui)
- [GPUI Mobile Android/iOS community backend](https://github.com/itsbalamurali/gpui-mobile)

## Highest-priority remaining gaps

1. Live Hermes HBC JSI → Rust GPUI update after app launch, including clicks, list changes and frame timestamps.
2. Actual Chromium GPUI Canvas render with the same Hermes-generated two scene JSONs (independent CI currently in progress).
3. Real Windows/macOS GUI launch; iOS Simulator/Android APK runtime with input, screenshots and replayable device/session logs.
4. Once full-frame tests run, compare 7+ alternated trials **within each platform**, not by mixing runner hardware.
