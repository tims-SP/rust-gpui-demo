# Hermes engine comparison

Use the Linux [Hermes vs Bun workflow](../.github/workflows/hermes-compare.yml). It tests *both* Svelte 5 and Solid 1.9 with **identical compiled CommonJS bundles across engines**, rather than comparing different frontend compilation modes. Native renderer: `@gpuix/native` 0.11.0, real Linux GPU window under Xvfb/Mesa llvmpipe.

Runtime: pinned hermes-node v0.0.2 linux-x64, verified with upstream release SHA256. The project uses the existing N-API addon, per [GPUIX official Hermes guide](https://gpuix.dev/guides/hermes). No GPUIX fork is needed to attempt this.

Each framework must create a real GPUI window, update 10k backing entries with 48 visible, pass native automation-tree ordering after window movement and keyed rotation, emit zero mutations on offscreen edits, create nonblank X11 screenshots, and provide a 3-process median by engine. Report `results/HERMES.md` and full raw data in Actions artifacts.

**Scope**: Hermes is a JS engine, not Svelte/Solid replacement. This CI does not measure hardware GPU frame times, React Native Android/iOS, or production AOT bytecode startup. It measures JS + N-API update loops for identical source-built CommonJS with 512/192/240 prewarm operations.


## Optimized Hermes comparison

The workflow now includes four engine modes for each identical compiled GPUIX application: Bun/JavaScriptCore, Hermes source without compilation cache, Hermes source with optimization enabled, and Hermes ahead-of-time bytecode bundle. Each has 3 real Linux native runs. Hermes bundle compilation happens *before* timed loops, ensuring we do not conflate startup with steady-state host update costs. Results in HERMES.md, not inferred from a pure JS benchmark.


## Final Linux native benchmark — PASS

[GitHub Actions #45094761850](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45094761850) completed **24 / 24 independent native GPUI window runs** successfully.
[Download raw JSON, logs, per-run screenshots, and identical compiled CJS sources](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45094761850/artifacts/14782079120).

Setup: Ubuntu 24.04 / Xvfb + Mesa llvmpipe, Bun 1.4.5/JavaScriptCore, hermes-node **v0.0.2** (Hermes engine reports 0.1.0), `@gpuix/native` 0.11.0, Solid 1.9.15, Svelte 5 custom renderer. All engines execute the **same Bun-built CommonJS file for each framework** with one unmodified GPUIX Native Node-API binary. Each process warms 512 themes, 192 rotations and 240 shifts before time measurement. Each result is the median of 3 independent processes. Rust retained-tree/order, no offscreen mutations, exact Native Mutation counts and nonblank Linux X11 screenshot were required for every run.

### Steady-state JS + native mutation costs (milliseconds)

| Framework and workload | Bun JSC | Hermes no-cache | Hermes optimized | Hermes AOT bytecode | AOT/Bun |
|---|---:|---:|---:|---:|---:|
| Solid single ×120 | 2.8983 | 2.0681 | 1.4273 | 1.1703 | 0.40x |
| Solid theme ×24 | 1.2416 | 4.5367 | 2.5100 | 2.1671 | **1.75x** |
| Solid reorder ×24 | 0.8526 | 2.9474 | 2.2167 | 2.2079 | **2.59x** |
| Solid window ×120 | 4.0155 | 19.2348 | 14.3932 | 14.2805 | **3.56x** |
| Svelte single ×120 | 1.5684 | 5.1835 | 3.1267 | 4.0405 | 2.58x |
| Svelte theme ×24 | 4.0006 | 32.0325 | 21.8531 | 20.4713 | **5.12x** |
| Svelte reorder ×24 | 1.9759 | 8.6407 | 6.8470 | 6.5894 | **3.33x** |
| Svelte window ×120 | 9.1797 | 42.0241 | 29.0089 | 28.7138 | **3.13x** |

Full results (including 200 offscreen edits and mutation counts) live in the artifact's `results/HERMES.md` and `results/HERMES.json`.

**Mechanism**: Hermes optimized/AOT versions are distinctly faster than Hermes no-cache, but not enough to match JSC for representative high-churn list and style updates. The single Solid text-edit timing goes the other way in this small sample; it should not override the multi-workload conclusion. Both optimized source and prebuilt bytecode perform similarly in long-running loops; AOT's primary purpose is **avoiding compilation at startup** (startup not measured).

### Resource snapshots, not leak measurements

End-of-workload process RSS snapshots were approximately 191–204 MiB for Bun, 175 MiB for optimized Hermes, and 155–166 MiB for Hermes AOT. These snapshots are not steady-state memory leak tests, and the numbers include Native/GPUI and process loading differences. Hermes may merit further evaluation for low-memory/startup goals, but **no measured app startup latency** or real-device memory use is claimed here.

### Practical integration repairs

1. Use [tmikov/hermes-node](https://github.com/tmikov/hermes-node) pinned at v0.0.2, Linux tarball SHA256 `56403274e5c5f24a58e84e15624bce473af1ab00d3bf60efc3f64a574614a4f7`.
2. Bundle with explicit `Bun.build({plugins:[...]})`: runtime `--preload` registrations do not run in `Bun.build`. Solid uses its `createSolidPlugin()`; Svelte uses the custom renderer compiler plugin and `custom-renderer,production` conditions.
3. **Only** externalize `@gpuix/native` (actual CJS/native extension). Bundle `@gpuix/native/host` and other ESM JS subpaths into CommonJS, otherwise hermes-node cannot `require()` them.
4. `hermes-node --build-bundle` v0.0.2 ignores the `package.json` `exports.require` selection and reads `main` instead. The workflow **temporarily edits only the installed dependency manifest** to set `main=./index.cjs`, matching the package's already published `exports.require` path. It does not alter the Git-managed source, native addon or compiled JS. This is not a Hermes core fork.
5. Rewrite remaining `import()` expressions to `require()` in the generated CJS and polyfill missing `performance.now` and `queueMicrotask` as in GPUIX's [Hermes guide](https://gpuix.dev/guides/hermes).
6. All 4 runtime modes successfully load the **same unmodified Rust GPUIX Node-API addon** and display an actual GPUI window.

### Recommendation and boundaries

Keep **Bun/JSC as the performance baseline** for this Linux music-list UI. Hermes is technically viable and consumes less memory in this small snapshot, but should not replace the default runtime for steady-state update performance on the evidence above. Hermes AOT's startup and distribution-size benefits remain an independent possible product reason to use it, and must be measured before adoption.

The test does **not** establish comparative Linux physical GPU frame time, production memory leaks, Android/iOS runtime support, or fair real-world launch latency. No upstream fork is required for these Linux results. 

## Verified meaning of AOT (audit)

**AOT means ahead-of-time optimized Hermes BYTECODE, not machine-code compilation.**
The actual workflow invokes `hermes-node --build-bundle=... app.cjs` and then
executes `hermes-node --bundle=...`. Upstream v0.0.2
[`lib/bundle/bundle_build.cpp`](https://github.com/tmikov/hermes-node/blob/v0.0.2/lib/bundle/bundle_build.cpp)
uses `hermes_compile_to_bytecode` with `cflags.optimize = true`;
[`lib/bundle/bundle_run.cpp`](https://github.com/tmikov/hermes-node/blob/v0.0.2/lib/bundle/bundle_run.cpp)
executes it with `hermes_run_bytecode`. No `shermes` or Static Hermes native
code generation was invoked. The current CI adds a strict `--dump`,
`--extract-module`, `--dump-bytecode` check for both bundles and archives
actual entry-module bytecode, disassembly header and SHA256 evidence.

**Important:** `hermes-opt` compiles optimized bytecode when running the source;
`hermes-aot` compiles it during the preceding build step and loads it at runtime.
The AOT performance table compares Hermes bytecode interpretation against JSC,
*not* native machine code from Static Hermes.
