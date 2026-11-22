# GPUI on Linux: Svelte 5 vs SolidJS 1.9

This repository is a clean, Linux-only native GPUIX comparison. The previous
lyrics casting, MP4 and WebRTC sources are removed from the current tree;
their Git history remains available.

## What is tested

Two independent implementations of the same 48-row music library:

- **Solid**: Solid 1.9 Signals + Store, `@gpuix/solid` 0.11.
- **Svelte**: Svelte 5 Runes, `gpuix-svelte` 0.6, scoped CSS and `var(--accent)`.
- Both use **`@gpuix/native` 0.11** and run a real GPUI window on Linux.
- GitHub Actions runs them under Xvfb with Mesa **software Vulkan**, collects
  actual `applyBatch` mutations, measures elapsed JS/FFI time, checks a
  final value in the Rust retained tree and captures an X11 screenshot.

Same scenarios: 120 single-row edits, 24 theme switches, 24 keyed list rotations.
The scripts fail if the native addon, mutation probe, retained-tree assertion,
or screenshot fails. No screenshots or numbers are synthesized.

## CI and results

[Linux comparison workflow](https://github.com/tims-SP/rust-gpui-demo/actions/workflows/linux-compare.yml)
runs on each `main` push and through `workflow_dispatch`. Download the
`linux-svelte-solid-gpui-results` artifact for JSON, logs, summary and PNGs.

### Scope and limitations

- GPUIX Linux upstream has no `TestGpuixRenderer`. These are **real-window**
  tests, not headless `TestGpuixRenderer` tests.
- Software Vulkan is not representative of a discrete/integrated hardware GPU.
- Svelte uses cascading CSS variables, while Solid uses direct reactive
  styles; mutations and style propagation are the **actual integration cost**
  of those designs, not an isolated framework microbenchmark.
- The first iteration **does not test a custom Rust ArtworkFlow component**,
  real GPU frame-time distributions, memory leak cycles or mobile hosts.
  These are explicitly not claimed as passed.
- A single CI run must not be treated as a statistically significant winner.

## Reproduce on Linux

Install Bun, Node 24, Xvfb, ImageMagick, Mesa Vulkan and the X11 libraries
listed in the workflow. Then:

```sh
bun install
mkdir -p results
xvfb-run -a -s "-screen 0 1280x950x24" bun run bench:solid
xvfb-run -a -s "-screen 0 1280x950x24" bun run bench:svelte
bun run compare
```

Only pass/fail and measurements produced by real Actions runs are evidence.
