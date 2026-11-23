# Hermes + GPUI | Svelte vs Solid | six-platform experiment

**Implementation in progress.** This repository was rebuilt from the archived history at
[`archive/pre-hermes-six-platform-20261123`](https://github.com/tims-SP/rust-gpui-demo/tree/archive/pre-hermes-six-platform-20261123).

## Scope and evidence levels

Every framework/platform pair must reach **Build**, **Run**, and **Render** separately.
A passing JS-only smoke, successful HBC build, or APK build is **not** a GPUI render proof.

| Level | Meaning | Current evidence |
| --- | --- | --- |
| JS / Node | Real Svelte 5 custom renderer and Solid universal renderer produce mutations | Run `npm test` |
| Hermes HBC | Hermes compiles and executes each UI app from bytecode | `P0 Hermes HBC` CI, pending run |
| Rust mutation | Rust parses and applies a batch to a scene transactionally | `cargo test -p ui-mutation` |
| GPUI Linux | Real window and pixels + UI input | Not yet integrated |
| Web GPUI | Canvas screenshot + Hermes Wasm JSI UI | Not yet integrated |
| Windows/macOS/iOS/Android | Actual platform run + render evidence | Not yet integrated |

## Pinned versions

Svelte **5.59.1** with `experimental.customRenderer`; Solid **1.9.20**
and `babel-preset-solid` **1.9.19** with `generate: "universal"`.
Hermes commit **d412d3bd851278712c20cca25d094e32641a0465**
(same version as the previously verified Ibex 2/Web Hermes experiment).
The prior verified native Ibex 2 commit is **24cd0ae8cdd20106bed04cd3a4a2378d1dd81995**.
All JS packages are pinned in `package-lock.json`.

## Run

```bash
npm ci
npm test
npm run bench  # Node baseline ONLY; never report as Hermes/GPUI fps
cargo test -p ui-mutation
```

`npm test` builds real Svelte/Solid components through **official** custom renderers
(no browser DOM shim), tests 48/10,000 virtual tracks, 100 counter calls +
one actual event, 30 window moves, 1 theme change, and a 1000-key reversal.
It compares semantic output between frameworks and validates mutation operations.
Raw mutation ID counts are not an apples-to-apples speed comparison.

To validate genuine Hermes bytecode locally: build a matching `.hermes-host/bin/hermes`
and `hermesc`, then run `bash scripts/check-hbc.sh`.
The CI workflow performs these steps from the pinned Hermes source.

## Architecture

```text
Svelte 5 customRenderer ---+
                           +--> renderers/shared/host.js --> JSON-like mutation batches
Solid universal renderer --+                                |
                                                   crates/ui-mutation (Rust)
                                                             |
                                             [next: GPUI scene + frame adapter]
Hermes: pinned native Ibex 2 / Wasm JSI are historical verified hosts,
but the newly rebuilt UI program is NOT yet integrated with either.
```

Mutation vocabulary: `create`, `insert`, `remove`, `text`,
`attribute`, `event`. Move uses insert with an optional before-anchor;
events stay registered in JS and are delivered by target ID.
Only serializable data crosses the boundary. Host code owns event closures.

## Source-of-truth upstream references

- [Svelte official custom renderer](https://svelte.dev/docs/svelte/custom-renderers)
- [Solid universal renderer](https://github.com/solidjs/solid)
- [GPUI source](https://github.com/zed-industries/zed/tree/main/crates/gpui)
- [Hermes](https://github.com/facebook/hermes)
- [Ibex 2](https://github.com/expo/ibex)

The archived previous workflow passed Ibex native HBC and Chromium Wasm HBC,
but never tested the UI bridge. See the archive for its distinct proof.

## Remaining gates

P0: Hermes HBC UI run and Rust scene batch integration. P1: Linux GPUI window,
input, screenshots, four-layer profiling. P2: Web GPUI and Hermes Wasm.
P3: Windows, macOS, iOS. P4: Android adaptation. P5: comparative report.
No unavailable result will be recorded as passing.
