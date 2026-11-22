# CSS ablation: Svelte and Solid on Linux GPUIX

Validated by [successful GitHub Actions run #45084751046](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45084751046) on commit `f03b9944`.
[Raw results and screenshots](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45084751046/artifacts/14778647285), particularly `UNSTYLED.json` and `UNSTYLED.md`.

## Experiment

Both implementations use the same GPUIX 0.11 Linux native renderer, Ubuntu 24.04, Bun 1.4.5, Xvfb and Mesa llvmpipe. They have 10,000 backing records and 48 visible songs.

An initial **truly style-free** Svelte variant (no style attributes, no CSS rules) produced a completely blank X11 frame, even though the retained tree still contained the expected labels. This was correctly rejected by the nonblank screenshot gate, so **its performance is not a valid app benchmark**.

A valid control kept only **immutable visible layout and text-color inline styles** while removing Svelte `<style>`, class rules, CSS variables and runtime style updates. Solid got a corresponding fixed-style control. Theme changes were excluded because an unconsumed theme variable is a no-op.

A styled baseline includes 5 process trials per framework; each fixed-style variant includes 3 independent process trials. Numbers are milliseconds, median total JS+FFI duration; negative change = faster.

| Framework | Workload | Original styles | Fixed-only styles | Change | Mutation original/fixed |
|---|---|---:|---:|---:|---:|
| Solid | single 120 | 4.899 | 5.655 | +15.4% | 120 / 120 |
| Solid | offscreen 200 | 1.111 | 1.182 | +6.4% | 0 / 0 |
| Solid | keyed reorder 24 | 4.409 | 4.632 | +5.1% | 264 / 264 |
| Solid | window shift 120 | 15.879 | 17.386 | +9.5% | 1223 / 1223 |
| Svelte | single 120 | 7.778 | 7.760 | -0.2% | 120 / 120 |
| Svelte | offscreen 200 | 3.600 | 3.548 | -1.4% | 0 / 0 |
| Svelte | keyed reorder 24 | 10.003 | 10.302 | +3.0% | 24 / 24 |
| Svelte | window shift 120 | 37.665 | 43.487 | +15.5% | 1223 / 1223 |

All 6 fixed-style runs passed: native window created, 48 expected nodes visible in Rust automation tree, proper window order and nonblank screenshot.

## Interpretation

- Removing **CSS authoring features and reactive style bindings** alone does not materially improve Svelte's single-item updates or keyed reorder in this GPUIX adapter.
- The more expensive visible-window operation is **not eliminated** by removing the CSS style sheet. The fixed-style Svelte variant still emits the same 1,223 Native mutations during 120 window shifts.
- The constant-style variant retains the native renderer's normal style parsing and propagation on mount/rebuild; it is not a test of removing style handling **from the adapter itself**.
- No theme benchmark is claimed for the fixed-only variant, because deleting the actual visible theme feature turns that workload into a no-op.
- Current data point toward Svelte JS rendering/host adapter reconciliation as the major remaining performance cost. Further internals tracing is needed to attribute it precisely to a function; the experiments do **not** prove Svelte is inherently slower in every application.
- The dedicated hardware GPU frame-time comparison is **not** performed here. Host/runner noise and unequal number of baseline vs control trials limit small-percentage comparisons.

## Implementation

- `bench/SvelteStatic.svelte`: constant inline geometry/color, no `<style>` or reactive style.
- `bench/solid.tsx`: `BENCH_STYLE_MODE=static` branch.
- `bench/unstyled_compare.py`: compares original baseline against three fixed-style runs.
- `.github/workflows/linux-compare.yml`: stores JSON and X11 captures on real CI.

**Decision**: Keep the existing styled UI; deleting CSS is not a justified performance optimization. Focus on the real update/reconciliation hot paths and native operation reuse instead.
