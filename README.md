# GPUIX Linux: Svelte 5 vs SolidJS 1.9

Linux-only **native GPUIX** comparison. The original lyrics/WebRTC test files
were removed from the current worktree; the Git history is preserved.

## Current benchmark

- `@gpuix/native` 0.11.0 is shared by `@gpuix/solid` 0.11.0 and `gpuix-svelte` 0.6.0.
- Same 10,000-track backing dataset; 48 rendered rows.
- 120 single-row edits, 24 theme updates, 200 offscreen edits, 24 list rotations and 120 window movements.
- Native must show exactly songs 120..167 after moving the visible window; 200 edits to non-visible songs must produce **zero** Native Mutation.
- **5 independent runs per framework**, alternating execution order.
- Measures end-to-end JS update + instrumented Native Mutation submission, including per-operation P95, batch and byte counts.
- Checks the real Linux GPUI Automation Tree, final list order and nonblank screenshot.
- Measures process RSS and heap at the end. A one-time RSS number **is not a memory-leak test**.
- GitHub Actions runs Ubuntu 24.04 under Xvfb / Mesa software Vulkan (llvmpipe), not physical GPU.

[CI workflow](https://github.com/tims-SP/rust-gpui-demo/actions/workflows/linux-compare.yml)

Download the result artifact: `comparison.json`, `SUMMARY.md`, `solid-*.json`,
`svelte-*.json`, process logs and actual X11 `.png` captures.

## Interpretation

The "window" workload updates an **app-side** 48-row window over a 10k collection;
it does *not* test GPUI native `virtual-list`. Svelte's CSS variable propagation
and Solid's inline reactive style are intentionally different implementation
strategies; their performance numbers test the entire strategy, not just the
framework kernel.

No claim is made about GPU frame times, Android/iOS performance, a custom Rust
ArtworkFlow node, long-running memory leaks or AI Agent iteration cost.
The native addon and compositor are real, but software Vulkan is not a GPU
hardware benchmark. Five process trials provide repeatability evidence, not
controlled confidence intervals.

## Linux manual reproduction

Install Bun 1.4.5, Node 24, Xvfb, ImageMagick, Mesa Vulkan and the system
libraries in the workflow:

```bash
bun install
mkdir -p results
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
for trial in 0 1 2 3 4; do
  export BENCH_TRIAL="$trial"
  xvfb-run -a -s "-screen 0 1280x950x24" bun run bench:solid
  xvfb-run -a -s "-screen 0 1280x950x24" bun run bench:svelte
done
bun run compare
```

Only CI logs, actual run JSON and screenshots are evidence of success.

## Performance root-cause isolation

The workflow adds three native process trials for two targeted variants after the five baseline trials: Solid `<For>` keyed by numeric IDs instead of reactive store objects, and Svelte direct `style:color` instead of inherited `var(--accent)`. The same dataset, Native 0.11 backend and window assertions are required. The emitted `DIAGNOSIS.md` separates state update, framework flush, benchmark probe overhead and native addon call time, along with per-operation mutation counts.

An additional instrumented Svelte run records `flushSync()`, `commit()`, and individual renderer host method timings (setAttribute/insert/remove/setText). The traces deliberately add call overhead and therefore must not be treated as uninstrumented framework throughput; they are intended to locate hot paths.

## Root-cause analysis

[Experiment-based Svelte vs Solid bottleneck report](docs/ROOT_CAUSE.md) summarizes five-trial timing, the two controlled variants, Svelte host tracing, the remaining uncertainty, and the upstream source hotspots.

## Static-style control

Removing **all** styles left a blank native X11 frame for Svelte; that result was rejected as a non-rendering app. The revised valid control keeps immutable geometry and text-color style attributes so GPUI displays real UI. It removes **all <style> blocks, class selectors, CSS variables, and runtime style binding**. Both frameworks run three independent static-style trials, while the five styled baseline trials still run. The theme phase is omitted in static style because no visible theme mutation exists. See `results/UNSTYLED.md` and `results/UNSTYLED.json` for actual performance deltas.

## CSS ablation results

[See the real Linux comparison of full CSS versus fixed-only styles](docs/STYLE_ABLATION.md). Removing Svelte CSS sheets, variables and dynamic styles did not produce a significant update-speed improvement. An entirely style-free version rendered a blank window and was rejected.

## JavaScript engine and runtime-mode isolation

The `engine-isolation.yml` workflow launches **the same native Linux GPUIX app**
under Svelte CLI, Svelte direct Bun with `development` condition, Svelte direct Bun
without that condition, and Solid direct Bun. Each uses Bun 1.4.5. It records
`process.execPath`, `process.versions`, `execArgv`, mutation counts and
four repeated native window timings, with screenshots and live tree assertions.
Results are in `results/ENGINE.md` and `results/ENGINE.json`.

## Confirmed engine/runtime diagnosis

[Runtime verification and development-condition performance isolation](docs/ROOT_CAUSE.md#follow-up-are-different-javascript-engines-responsible) confirms that both applications run Bun 1.4.5/JavaScriptCore; Svelte's CLI adds a `development` export condition, which explains some but not all of the performance gap. Actual data: [Action #45088146436](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45088146436).
