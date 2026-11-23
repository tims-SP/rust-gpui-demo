# Verified Linux GPUIX Svelte vs Solid hotpaths

## Evidence

- [Bun/JavaScriptCore CPU sample run — passed](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45089211003); [raw 8 per-phase JSC profiles](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45089211003/artifacts/14781020399). Profiles use `bun:jsc.profile()` on warmed update loops, not compilation or startup.
- [Production-mode, 4-trial scope/cache and array-proxy isolation](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45089494608); [16 real application logs, JSON and X11 screenshots](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45089494608/artifacts/14780900802). All 16 native apps created valid retained trees and nonblank screenshots; the initial **overall Action marked failure** due to a report-only screenshot-path assertion. Its raw results have been independently checked; `bench/cache_proxy_compare.py` was corrected in commit `2fc8c710`, and a follow-up Action was triggered. Do not confuse this reporting defect with a renderer failure.
- [Both runtimes are Bun 1.4.5/JavaScriptCore](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45088146436); different JS engines are ruled out.
- [Earlier unstyled-control results](https://github.com/tims-SP/rust-gpui-demo/blob/main/docs/STYLE_ABLATION.md) showed that deleting author-level CSS alone did not improve list updates.

## Current root causes

### 1. Scoped CSS variables disable the existing rule-style cache

In `gpuix-svelte/src/style.ts`, `build_style()` walks the ancestor chain to detect any scoped `vars`. When it finds one, it passes `scoped=true` to `rule_style()`. **That function only reuses its `rule.generation` / `rule.resolved` cache when `!scoped`.** This protects against different variables in subtrees, but for a single `style:--accent` on a shared parent it means the same `color: var(--accent)` must be substituted and parsed separately for each text node.

CPU self-samples in the Svelte theme profile (1,326 samples) included **892 samples in `gpuix-svelte/lib/style.js`** (67.3%); prominent functions are `expand` (203), `take` (178), `camel` (125), `parse_css_text` (104), `substitute_vars` (80). This is evidence of repeated CSS parsing, not Rust/GPU drawing overhead.

Changing *only the theme scope* to the existing `set_css_vars()` global API lets the same rule cache work for all 48 rows. Four independent **warmed native Linux** processes each give:

| Theme variant | Median theme ×24 update (ms) | Native mutations |
|---|---:|---:|
| Svelte local `style:--accent` (original) | **3.336** | 1,176 |
| Svelte global `set_css_vars({accent})` | **1.4885** | 1,152 |
| Solid direct reactive color | **0.9985** | 1,152 |

**Observed 55.4% time reduction** from switching Svelte to the global cache path. The global and local variable variants are NOT semantically identical in a multiwindow or nested-theme application; a production fix should implement effective per-scope resolution caching rather than force everything global. The difference of 24 Native mutations is small relative to 1,176 and does not plausibly explain the entire 55% reduction.

### 2. Svelte deep reactive array Proxy + list reconciliation overhead

The original Svelte list keeps `order = $state([...])` and slices the deeply proxied 10,000-element `tracks` array on each visible-window change. In the CPU samples for Svelte keyed reorder, its `get`, `has`, `slice`, `getOwnPropertyDescriptor`, `each.js` and Effect scheduler functions dominate. For window shifts, Svelte framework self-samples were 353 of 728 (48.5%), while Svelte host Style + Renderer code contributed another 116 (15.9%). Sampling categories are not a precise per-function wall-time decomposition.

The controlled list variant **combines two changes**: `order = $state.raw([...])` (immutable structural array, still reactive on reassignment) and `Array.from({length:48}, (_,i) => tracks[windowStart+i])` instead of `tracks.slice(...)`. Four independent warmed processes:

| List variant | Reorder ×24 (ms) | Window shift ×120 (ms) | Reorder mutations | Window mutations |
|---|---:|---:|---:|---:|
| Svelte original | **1.877** | **8.8275** | 24 | 1,223 |
| Svelte raw order + indexed window | **1.106** | **7.1965** | 24 | 1,223 |
| Solid | **1.0165** | **4.244** | 264 | 1,223 |

Result: **41.1% faster reorder, 18.5% faster visible-window shifts**, with unchanged Native mutation counts for those scenarios. Consequently the improvement came from JS state/list work, not fewer Rust commands. The two list changes were evaluated together; their individual contributions are not yet isolated.

### 3. Remaining differences

Svelte after these changes is near Solid's keyed-reorder timing (1.106 vs 1.0165 ms), but window shifts remain about 1.7× slower (7.1965 vs 4.244 ms), likely involving Svelte Effect lifecycle, keyed each-block reconciliation and shadow-node management. Source tracing pinpoints candidates, but no single additional function has yet been causally proven as responsible. The two framework adapters are not identical: Solid sends 264 mutations for 24 rotations while Svelte sends 24, although Solid is still faster in JS loop time.

Even in production mode, initial short, lightly warmed CI measurements were slower than results after explicit warmup (512 theme changes / 192 rotations / 240 shifts). **Do not compare the warm-run medians to older cold-run medians as if the program or hardware changed.**

## Product implications

1. **Don't delete Svelte CSS**: the actual cost comes from scoped-variable cache misses, not just having a `<style>` block.
2. For truly global app themes, `set_css_vars()` currently reuses existing GPUIX-Svelte caching more efficiently. For per-panel/per-window themes, retain scoping and consider implementing a cache keyed by effective scope/version after testing invalidation.
3. Use `$state.raw` for structurally replaced arrays and keep fine-grained proxies only where individual fields need local updates; avoid unnecessary full reactive-array slicing on frequent window shifts.
4. Prototype optimizations on the existing custom renderer rather than assuming a different JS engine would fix it.

The presented measurements are JS/reactive-host/native-command timings on **Ubuntu 24.04 Xvfb + llvmpipe software Vulkan**, not actual hardware GPU frame times. One GitHub Actions run does not establish universal Svelte-vs-Solid performance, and the 4-process sample size is not a confidence interval.
