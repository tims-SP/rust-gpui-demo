# Root cause: Svelte 5 vs SolidJS 1.9 on Linux GPUIX

Verified: [Action #45083887947](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45083887947), commit `aa4797ab`. See artifact `DIAGNOSIS.json`, `DIAGNOSIS.md`, and per-trial JSONs. Same GPUIX Native 0.11, Bun 1.4.5, Ubuntu 24.04 Xvfb + llvmpipe. Baseline medians are from five independent processes.

| Scenario | Solid total ms | Svelte total ms | Svelte state-update ms | Svelte flush + commit ms | Svelte native call ms |
|---|---:|---:|---:|---:|---:|
| Single edits ×120 | 2.680 | 4.257 | 1.598 | 2.504 | 0.353 |
| Theme ×24 | 2.305 | 10.606 | 0.418 | 10.158 | 0.605 |
| Keyed reorder ×24 | 2.961 | 6.969 | 1.256 | 5.741 | 0.243 |
| Window shifts ×120 | 8.737 | 25.249 | 0.763 | 24.346 | 1.535 |

**Result:** More time is spent in Svelte's JS scheduling/reconciliation/host-adapter path than in Rust Native FFI. Phase labels do not compare exactly across frameworks: Solid reacts during a setter, Svelte defers much work until `flushSync`. Compare total update-and-settle times.

### Isolation results

1. Svelte `style:color` rather than `var(--accent)` does **not** eliminate theme overhead. Three-process median direct-style theme ~11.117ms versus original baseline ~10.606ms; Native mutations 1152 instead of 1176. The CSS variable cascade **alone is not the main cause**.
2. Instrumented Svelte direct-style theme: about 1152 `setAttribute` calls, ~10.5ms inclusive inside host setters, mostly during `flushSync`. Instrumented CSS-variable theme: only 24 `setAttribute` calls, but roughly 12ms in `commit()` due to deferred restyling. These tracing runs add substantial instrumentation overhead; do **not** compare traced totals to untraced baselines.
3. During 120 window shifts, an instrumented Svelte run called host `insert()` **1104 times**, taking about 4.7–5ms inclusive. Most of the larger ~31–35ms instrumented `flushSync` time remains in other JS framework/adapter work, not Native calls. The exact contributions of compiler-generated effects vs internal shadow-tree operations remain unisolated.
4. Changing Solid `<For>` from track-object references to stable numeric IDs did not reduce its 264 Native mutations in 24 rotations (including 24 `destroyElement` and 72 `createElement`). Svelte emits 24 `appendChild` for those same rotations. The precise Solid runtime/adapter decision causing rebuild is **still to be traced**; it is not just an unstable object-key issue.
5. Editing 200 offscreen tracks emits **zero Native mutations** in both adapters. Final Linux GPUI Automation Tree and X11 non-blank screenshots passed.

### Source code hotspots

- [Svelte renderer](https://github.com/khromov/gpuix-svelte/blob/main/src/renderer.ts): `setAttribute`, `apply_style`, `restyle_readers`, `insert`, `commit`.
- [Svelte style system](https://github.com/khromov/gpuix-svelte/blob/main/src/style.ts): `declare_vars`, `parse_css_text`, `build_style`.
- [Solid host](https://github.com/remorses/gpuix/blob/main/packages/solid/src/host.ts): `setHostProperty`, `insertHostNode`, `removeHostNode`.
- [Solid Universal Renderer](https://github.com/remorses/gpuix/blob/main/packages/solid/src/universal.ts): `createRenderer` callbacks.
- This repository: `bench/common.ts`, `bench/solid.tsx`, `bench/SvelteApp.svelte`, `bench/SvelteInline.svelte`.

### Conclusion and limits

The tests establish a **current-adapter performance gap in these Linux JS/FFI workloads**, not a universal Svelte-vs-Solid runtime benchmark or a hardware GPU gap. Svelte's CSS parsing, style restyling, keyed diff and shadow-tree overhead are promising optimization targets, but the exact per-function savings require more focused instrumentation before making a change. Solid also needs a keyed-rotation investigation because it emits unnecessary native node churn.


## Follow-up: Are different JavaScript engines responsible?

**No.** The native-process experiment [Action #45088146436](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45088146436) demonstrates that the original Svelte CLI, Svelte explicit development mode, Svelte without the development condition, and Solid all run under `/home/runner/.bun/bin/bun` **Bun 1.4.5** on this Linux CI runner. The native GPUIX backend is unchanged. Bun uses **JavaScriptCore**, even though its `process.versions.v8` and `process.versions.node` can carry compatibility-version values; these are not evidence that V8 executed the app.

The Svelte launcher script `gpuix-svelte --bun` itself uses a Node-compatible CLI to spawn a **Bun child** with flags `--conditions custom-renderer --conditions development --preload ...`. The Node executable that starts the launcher does not execute the timed application update loops.

### Same-engine, different conditions (4 independent native processes each)

| Runtime path | Single ×120 (ms) | Theme ×24 | Reorder ×24 | Window ×120 |
|---|---:|---:|---:|---:|
| Svelte via original CLI, dev condition | 4.3915 | 10.465 | 6.9285 | 23.2705 |
| Svelte direct Bun, dev condition | 4.291 | 10.385 | 6.7175 | 24.9975 |
| Svelte direct Bun, **without dev condition** | **3.9955** | 10.645 | **5.8435** | **18.6235** |
| Solid direct Bun | **2.6335** | **2.3895** | **2.9835** | **8.4415** |

These numbers are independent-process median JS+instrumented FFI update durations, *not* GPU frame-time or startup measurements. All variants passed native mutation counts, automation-tree checks and nonblank screenshots. The pre-existing full benchmark also passed [Action #45088146376](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45088146376) after adding runtime diagnostics.

**Conclusion:** Using `development` conditions explains **part** of the Svelte overhead (especially visible-window shifts), but cannot explain the remaining approximately 2.2× window and 4.5× theme total-time gaps. The engines were identical. Remaining differences come from framework scheduling, compiler output and host/adapter operations, rather than two different JS engines. The evidence does not yet uniquely separate those components by CPU hotspot.

### Reproduction

```bash
# Existing CLI path: Bun child + development condition
bunx gpuix-svelte --bun bench/svelte.ts

# Same custom renderer / Bun, directly with development condition
bun --conditions custom-renderer --conditions development --preload gpuix-svelte/plugin bench/svelte.ts

# Same custom renderer / Bun, without development condition
bun --conditions custom-renderer --preload gpuix-svelte/plugin bench/svelte.ts

# Solid control, also Bun
bun --preload @gpuix/solid/preload bench/solid.tsx
```

The [engine isolation workflow](https://github.com/tims-SP/rust-gpui-demo/blob/main/.github/workflows/engine-isolation.yml) records actual runtime metadata and raw tests in [the artifact](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45088146436/artifacts/14779239750).
