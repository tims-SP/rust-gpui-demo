# Hermes engine comparison

Use the Linux [Hermes vs Bun workflow](../.github/workflows/hermes-compare.yml). It tests *both* Svelte 5 and Solid 1.9 with **identical compiled CommonJS bundles across engines**, rather than comparing different frontend compilation modes. Native renderer: `@gpuix/native` 0.11.0, real Linux GPU window under Xvfb/Mesa llvmpipe.

Runtime: pinned hermes-node v0.0.2 linux-x64, verified with upstream release SHA256. The project uses the existing N-API addon, per [GPUIX official Hermes guide](https://gpuix.dev/guides/hermes). No GPUIX fork is needed to attempt this.

Each framework must create a real GPUI window, update 10k backing entries with 48 visible, pass native automation-tree ordering after window movement and keyed rotation, emit zero mutations on offscreen edits, create nonblank X11 screenshots, and provide a 3-process median by engine. Report `results/HERMES.md` and full raw data in Actions artifacts.

**Scope**: Hermes is a JS engine, not Svelte/Solid replacement. This CI does not measure hardware GPU frame times, React Native Android/iOS, or production AOT bytecode startup. It measures JS + N-API update loops for identical source-built CommonJS with 512/192/240 prewarm operations.


## Optimized Hermes comparison

The workflow now includes four engine modes for each identical compiled GPUIX application: Bun/JavaScriptCore, Hermes source without compilation cache, Hermes source with optimization enabled, and Hermes ahead-of-time bytecode bundle. Each has 3 real Linux native runs. Hermes bundle compilation happens *before* timed loops, ensuring we do not conflate startup with steady-state host update costs. Results in HERMES.md, not inferred from a pure JS benchmark.
