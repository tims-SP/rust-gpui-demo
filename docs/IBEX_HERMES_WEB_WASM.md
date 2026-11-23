# Ibex 2 Rust native + Hermes VM WebAssembly

## Goal

Use the same pinned Hermes engine version for native Ibex 2 Rust hosting and a browser-based Hermes WebAssembly VM. Execute one shared JavaScript program and validate identical output, not simply successful compilation.

Source of truth:

- Ibex 2: `expo/ibex` commit `24cd0ae8cdd20106bed04cd3a4a2378d1dd81995`.
- Ibex 2's upstream vanilla Hermes: `meta/hermes` commit `d412d3bd851278712c20cca25d094e32641a0465`.
- Emscripten: 4.0.15, pinned in GitHub Actions.
- Shared script: [shared.js](../bench/hermes-ibex-wasm/shared.js).
- Expected observable marker: `HERMES_SHARED_OK=479820`.

## Native: verified

[Successful GitHub Actions 45173224108](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45173224108) and [original native logs](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45173224108/artifacts/14817478082).

The CI built the real Ibex 2 Rust `ibex2-runtime` CLI, ran `ibex2 build` on the shared script, required nonempty precompiled cache files, then ran `ibex2 run --precompiled`. Actual output: `HERMES_SHARED_OK=479820`. The upstream vendored ring source required a targeted `-A mismatched-lifetime-syntaxes` to avoid a runner-injected warning-as-error policy; no upstream source changes were necessary.

## Web: VM build successful, browser bytecode execution not yet verified

[First browser/Web build 45172679896](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45172679896) compiled the entire Hermes VM to `hermes.js` and `hermes.wasm` and built `shared.hbc` from the same upstream Hermes commit. [First Wasm artifact](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45172679896/artifacts/14819715994): `hermes.wasm` 4,183,514 bytes and `shared.hbc` 658 bytes.

The original Node adapter failed because the repository has ESM module scope but Emscripten generated CommonJS glue. Copying `hermes.js` to `hermes.cjs` corrects this loading mismatch. After loading, the Wasm VM printed the expected marker but **aborted during exit**. A separate real Chromium diagnostic [run 45177161396](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45177161396) reproduced the abort; its workflow deliberately permits diagnostics even when the page shows FAIL, so a green diagnostic job is *not* a browser acceptance.

The corrected [Web build workflow 45177066771](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45177066771) uses the CommonJS adapter and Emscripten `-sEXIT_RUNTIME=1`; its true outcome must be verified from both the Node marker and a Chromium page displaying `PASS HERMES_SHARED_OK=479820` before Web can be marked successful.

The browser harness [index.html](../bench/hermes-ibex-wasm/index.html) instantiates `CreateHermesVM`, fetches the matching HBC file, writes it into Emscripten MEMFS, invokes the Hermes VM, and checks its standard output. This runs the JS *inside Hermes Wasm*, not directly in browser JavaScript.

## Important boundaries

- The native Ibex2 engine runs its own module-graph/manifest-wrapped precompiled modules; its serialized cache is **not proven interchangeable with the browser-hosted Hermes CLI's raw HBC** even though the upstream VM versions match.
- This proof of concept does not implement Svelte/Solid runtime reconciliation, native GPUI mutation/JSI, bidirectional JS-Rust callbacks, production browser VM embedding or performance.
- The minimum acceptance is real native Rust/Hermes and real Chromium Hermes-Wasm on the *same JS source*, with matching output. Both execution paths must independently pass.
- Do not extrapolate the previous JavaScript-only kernel results to the performance of Ibex2 or Hermes running inside Wasm.

## Reproduction

Native: `bash bench/hermes-ibex-wasm/native-smoke.sh` with the pinned Ibex repo checked out at `.ibex-source`. Web: `bash bench/hermes-ibex-wasm/web-smoke.sh` with the pinned Hermes repo at `.hermes-source` and Emscripten installed.

Workflows: [actual full build](../.github/workflows/ibex-hermes-web-wasm.yml) and [cached artifact diagnosis](../.github/workflows/hermes-wasm-artifact-check.yml).
