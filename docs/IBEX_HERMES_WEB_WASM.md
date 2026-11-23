# Ibex 2 Rust native + Hermes WebAssembly VM: verified

**Status: Native Ibex 2 PASS; real Chromium Hermes VM Wasm PASS.**

Both hosts executed the exact same original JavaScript source and observed HERMES_SHARED_OK=479820.

## Pinned engines and inputs

- Native Ibex2 Rust host: [expo/ibex](https://github.com/expo/ibex), commit 24cd0ae8cdd20106bed04cd3a4a2378d1dd81995.
- Hermes engine and bytecode compiler: [meta/hermes](https://github.com/meta/hermes), commit d412d3bd851278712c20cca25d094e32641a0465 (Ibex2's pinned vanilla source).
- Emscripten: 4.0.15.
- Shared JS input: [shared.js](../bench/hermes-ibex-wasm/shared.js).
- Observable checksum: HERMES_SHARED_OK=479820.

## Native Rust/Hermes: PASS

[Actions run #45173224108](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45173224108); [native logs and precompiled cache](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45173224108/artifacts/14817478082).

Built the actual Ibex2 Rust runtime, precompiled the module graph with Ibex2 build, verified nonempty cache, and executed using Ibex2 run --precompiled. The runtime printed HERMES_SHARED_OK=479820. The runner-injected warnings-as-errors setting required narrowly disabling an upstream vendored ring lifetime-syntax lint; the Ibex engine source was unchanged.

## Web Hermes VM compiled to Wasm: PASS

[Green Web JSI Actions run #45187557146](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45187557146); [Hermes wasm/glue/HBC, Node and real Chromium evidence](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45187557146/artifacts/14825561658).

This is the actual **Hermes JavaScript engine compiled to WebAssembly**, not the browser's built-in V8 evaluating the shared JS script.

The workflow:
1. Compiles the native Hermes bytecode compiler and the Hermes VM + JSI Wasm static libraries from the exact pinned revision.
2. Builds a minimal **persistent C++ JSI host** ([source](../bench/hermes-ibex-wasm/hermes-web-host.cpp)) into Hermes Wasm, exposing a function that reads a matching HBC file from Emscripten MEMFS, calls Hermes evaluateJavaScript and returns the numeric checksum.
3. Compiles the same JS input to raw HBC using the pinned hermesc, and runs the Hermes VM in Node using the generated Wasm loader.
4. Executes the **same** Wasm and HBC in a real headless Chromium page. The acceptance parser requires the actual HTML result node with data-status=pass and the exact text PASS HERMES_SHARED_OK=479820. A negative test ensures a source-code PASS string cannot satisfy the check.

**Observed real Web CI log markers:**

- HERMES_NODE_WASM_OK=479820
- HERMES_BROWSER_DOM_PROOF=479820
- HERMES_BROWSER_VM_HBC_PASS

The Web job exited success. This is more than compilation: it verifies the runtime execution and DOM result in a real browser.

## Root cause and final repair

The first Web approach compiled Hermes CLI main() to Wasm. That successfully printed the expected checksum, but aborted on CLI teardown in Node and Chromium. The final architecture embeds Hermes through **JSI** instead of running CLI main(). Build repairs also included:

- Replace unsupported Emscripten -sNO_ENTRY=1 with --no-entry.
- Add the upstream public/ include directory, and run a fast C++ syntax preflight before compiling the large VM.
- Enable the C++ exception runtime required by Hermes JSI static libraries.
- Verify the browser's real result DOM node, not plain HTML grepping.

## Limitations and scope

- The shared JS source and **matching Hermes engine revision** are verified on Linux native Rust and real Chromium Web. **Ibex's own module-graph cache artifact is not proven interchangeable** with the raw HBC generated for the Web VM; the two hosts use different module loaders.
- This proof does not yet integrate Svelte/Solid, actual GPUI rendering, JS-to-Rust UI Mutation callbacks, a production browser package or performance profiling.
- Android/iOS/macOS/Windows target binaries are not separately built or validated in this test.
- Passing this smoke test must not be treated as evidence of real-world GPUIX frame throughput, memory ceilings, sandbox security, or browser engine bundle size suitability.

## Reproduction

- Native: run bench/hermes-ibex-wasm/native-smoke.sh with the pinned Ibex source checked out at .ibex-source.
- Web: run bench/hermes-ibex-wasm/web-smoke.sh with the pinned Hermes source checked out at .hermes-source, Emscripten 4.0.15 and headless Chromium.
- Workflow definition: [.github/workflows/ibex-hermes-web-wasm.yml](../.github/workflows/ibex-hermes-web-wasm.yml).
