# Static Hermes native machine-code benchmark

This is separate from [Hermes **bytecode** AOT](HERMES_ENGINE.md).
Source compiler: [meta/hermes static_h](https://github.com/meta/hermes/tree/static_h)
pinned to commit `d864d3f09d10e8aebe429715eeed5a4d7edf114d`.

The [GitHub Actions native workflow](../.github/workflows/static-hermes-native.yml)
builds shermes and hermes from the same pinned source; uses
`shermes -O -o kernels-native kernels.js` to emit a **machine-code ELF executable**
and `hermes -O -emit-binary` for **optimized bytecode**; compares these with
Bun/JavaScriptCore running *exactly the same* source.

Native machine code is checked via `file`, `readelf -h`, `readelf -S`,
nonempty `.text` section, SHA256 and real execution.
Each standalone JS program runs the same deterministic numeric, keyed reorder,
10,000-track/48-row proxied window, and scoped CSS substitution kernels.
Three process trials per mode with pre-warm inside JS. Checksums must match exactly.

## Critical comparability limitation

**This is a JS-only hot-path benchmark, NOT a native GPUIX window benchmark.**
Static Hermes's `shermes` creates standalone binaries with the Hermes VM,
but does *not* provide the `hermes-node` Node-API host that loads
`@gpuix/native`. GPUIX's actual Solid/Svelte app also imports Node-compatible
CommonJS modules, timers, and application-level APIs. Without a JSI / N-API
host that preserves identical native frame and FFI operations, it would be
incorrect to call this a GPUIX end-to-end comparison.

This initial study uses **untyped** JavaScript native compilation;
the sound typed Flow compilation route is separate.
The result establishes only how these sampled state/list/style JS kernels
perform under Static Hermes native AOT, Hermes bytecode, and JSC, not
actual native-GPUI performance or the typed Static Hermes speed ceiling.
