# Hermes GPUI six-platform comparison (Svelte 5 versus Solid)

Fresh code tree as of 2026-11-23. The previous complete Git tree is preserved at branch archive/pre-six-platform-hermes-2026-11-23. The Git history was not rewritten.

## Goal

Run actual custom renderer components with the SAME Hermes engine and SAME GPUI host mutations across Windows, Linux, macOS, Android, iOS and Web. Measure engine, bridge and graphics separately. BUILD is not RUN, and RUN is not visible GPUI RENDER.

## Current implemented scope

P0: Svelte 5.59 experimental custom renderer and SolidJS 1.9.15 universal renderer. Both generate a 48-row non-DOM scene graph; run 256 count changes, 40 viewport moves and 50 theme changes. The scene graph contains observable create/insert/remove/text/attribute operations. Node is only the development control runner; the native GitHub Actions job executes precompiled JS using actual Ibex 2 Hermes HBC.

Do not call this a GPUI window or an end-to-end graphics benchmark. Native GPUI windows, mobile apps and Web GPU Canvas still require implementation and separate acceptance.

## Run

    npm install
    npm run ci

See .github/workflows/framework-hermes.yml for real Ibex 2 Rust/Hermes bytecode tests. Strict acceptance: both native Hermes framework runs produce GPUI_SCENE_OK markers and the exact final scene. Framework-only timings are not final GPU frame latency.

## Platforms

Linux: Native Hermes smoke targeted (P0). Windows/macOS/iOS/Android: not yet run. Web: Prior Hermes VM Wasm-only proof in archive branch; the new Svelte/Solid bundles have not yet been verified in Wasm or with GPUI Web rendering. Android GPUI mobile platform requires porting.

## Sources

- https://svelte.dev/docs/svelte/custom-renderers
- https://github.com/solidjs/solid/blob/main/packages/solid/universal/README.md
- https://github.com/expo/ibex
- https://github.com/zed-industries/zed/tree/main/crates/gpui
- https://github.com/itsbalamurali/gpui-mobile
