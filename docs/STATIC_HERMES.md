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


## Verified Linux x86-64 result — PASS (2026-11-23)

- **Successful run:** [GitHub Actions #45101141779](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45101141779), commit `58b9c8c5b7811afce2cfb0eb4998241fc3daf827`.
- **Evidence archive:** [static-hermes-native-linux artifact #14785377841](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45101141779/artifacts/14785377841), containing the original JS kernel, compiler output, native ELF proof, all individual JSON/process logs, and reports.
- **Linker fix:** the first run failed with `ld: cannot find -lshermes_console`. The workflow now builds `shermes-dep` (which builds executable-link libraries) instead of only `shermes`; the second run passed.
- **Executable proof:** generated `kernels-native` is an ELF 64-bit x86-64 executable with a `.text` section, while `kernels.hbc` is Hermes JavaScript bytecode version 100.
- **Correctness:** all nine processes (3 engines × 3 independent trials) exited successfully. The exact checksums match in all four workloads.

Median pre-warmed JS-only timings (milliseconds; lower is better):

| JS workload | Bun / JSC | Hermes optimized bytecode | Static Hermes native AOT | Native / Bun | Native / bytecode |
|---|---:|---:|---:|---:|---:|
| Numeric (5M rounds) | 32 | 140 | 126 | 3.94× | 0.90× |
| Keyed reorder (120k) | 23 | 135 | 134 | 5.83× | 0.99× |
| Proxied 48-row window (45k) | 65 | 523 | 505 | 7.77× | 0.97× |
| Scoped CSS substitution (13k) | 188 | 839 | 839 | 4.46× | 1.00× |

**Interpretation:** for these **untyped**, GPUI-inspired JS kernels, Static Hermes native machine code is far slower than Bun/JSC and has little improvement over Hermes bytecode. Native output is verified, but native code generation is *not* evidence of better JS throughput.

**Do not extrapolate to actual GPUIX/Svelte/Solid native UI**, since no GPUIX Node-API addon, Rust mutation calls, or X11 window runs in this workflow. Neither typed Flow specialization, app startup, binary distribution size, nor actual app memory usage is measured. Three process trials and `Date.now()` millisecond resolution are suitable for identifying large differences here, not tight confidence intervals or tiny timing advantages.


## Six-engine Linux comparison — PASS (2026-11-23)

**Provenance:** [GitHub Actions #45104180668](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45104180668) · [full raw artifact #14787495421](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45104180668/artifacts/14787495421) · source commit `acef0c4c63fcf01dc023fe84751145f733eca8bf`.

The CI runs the identical `bench/static-hermes/kernels.js` file in **six modes** and verifies all 18 independent process results against exactly matching `(name, rounds, checksum)` tuples. Each engine has three separate process trials, with two per-kernel warmup invocations that are excluded from the `Date.now()` measurements.

- Bun **1.4.5**: JavaScriptCore (JSC)
- Node **24.22.2**: V8
- Ubuntu `libmozjs-115-dev` **115.10.0-1**: SpiderMonkey JS shell
- Ubuntu `quickjs` **2021.03.27-1**: QuickJS interpreter (**historical version**, not current QuickJS performance)
- Pinned upstream Hermes: optimized Hermes bytecode VM
- Same pinned upstream Hermes: Static Hermes `shermes -O` native ELF executable

**Measured median in-program times (milliseconds, lower is better):**

| Workload | Bun/JSC | Node/V8 | SpiderMonkey 115 | QuickJS 2021 | Hermes bytecode | Static Hermes native |
|---|---:|---:|---:|---:|---:|---:|
| numeric, 5M rounds | 10 | 5 | 22 | 279 | 136 | 125 |
| keyed reorder, 120k | 26 | 15 | 47 | 280 | 136 | 134 |
| Proxy visible window, 45k | 63 | 321 | 251 | 469 | 519 | 505 |
| CSS substitution, 13k × 48 | 188 | 235 | 411 | 1215 | 834 | 835 |

Native Hermes / Node-V8 timing ratios: **25.00×, 8.93×, 1.57×, 3.55×**. Native Hermes / Bun-JSC timing ratios: **12.50×, 5.15×, 8.02×, 4.44×**. All four kernels ran slower under Static Hermes than both JIT-enabled runtimes; Native AOT was only marginally faster than Hermes optimized bytecode.

**Interpretation safeguards:** Each engine has a different runtime, version, interpreter/JIT design and warmup/tiering behavior. The Bun numeric result was 32 ms in the preceding three-engine run but 10 ms in this run, illustrating sensitivity to warmup or JIT behavior; ratios are *observed in this run*, not general engine constants. These are JS-only GPUI-inspired kernels, **not** GPUIX native window, Node-API or actual Rust UI frame timings. The benchmark does **not** exercise soundly typed Static Hermes/Flow. A newer SpiderMonkey or QuickJS version may perform differently; the shipped Ubuntu packages are pinned and their versions preserved in the artifact.

For this sampled untyped music-list/state/style JS workload, retaining Bun/JSC is better supported than migrating to Static Hermes on steady-state execution-speed grounds. Typed Static Hermes, startup/memory, and actual GPUIX embedding remain unmeasured by this suite.
