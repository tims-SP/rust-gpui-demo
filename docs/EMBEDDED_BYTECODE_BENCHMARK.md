# Embedded JS bytecode & persistent-cache Linux benchmark (2026-11-23)

## Goal and observed acceptance

Evaluate bytecode deployment and JavaScript execution performance on Linux x86-64
for PrimJS, Escargot, QuickJS-NG, Bun/JavaScriptCore and Hermes
(optimized bytecode and Static Hermes native ELF). Require real process execution,
matching deterministic checksums, repeated samples, and per-process peak RSS.

**Results are kernel-only, not actual GPUIX native windows or Rust FFI.**

| Engine / mode | Offline compilation | New process runs compiled artifact without original JS? | Result |
|---|---|---|---|
| QuickJS-NG qjsc / standalone qjs | Verified | Verified | PASS |
| PrimJS LEPUS_WriteObject / ReadObject | Verified disk output (4,547 bytes) | Verified; fresh-process bytecode path; source input renamed | PASS |
| Hermes optimized HBC | Verified | Verified | PASS |
| Static Hermes shermes native ELF | Verified native machine code | Verified | PASS |
| Escargot native code cache | Verified cache stored on disk and HIT on a later process | **No** — still takes source for cache lookup | CACHE PASS; OFFLINE BYTECODE UNMET |
| Bun/JSC | Not a standalone bytecode mode in this test | N/A | PERFORMANCE REFERENCE |

### Evidence

- [8-mode QuickJS-NG, Hermes, Bun and other JS references: Actions #45106160801](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45106160801) — [original source, compiled bytecode/ELF, process JSON and RSS](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45106160801/artifacts/14787509297). 24/24 processes passed exact checksums.
- [PrimJS successful build, independent serialized bytecode loading and 9 process trials: Actions #45107271806](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45107271806) — [PrimJS artifact](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45107271806/artifacts/14788216541). Compiler/test shell is patched only for the benchmarking CLI; engine source is pinned.
- [Escargot successful fresh-process cache store/HIT and 9 process trials: Actions #45107271806](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45107271806) — [Escargot artifact](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45107271806/artifacts/14787932984). Both jobs in this workflow passed; earlier PrimJS failed on GCC-only build but recovered by explicitly selecting Clang.
- [Verified green two-job CI run after selecting Clang and restricting Escargot submodule checkout](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45107271806).

Pinned compiler source:
- PrimJS: lynx-family/primjs at c6d670ca2250bf3ee967c7b9f28310b4a4b75e5f (Linux x86-64 ARM64 template interpreter disabled).
- Escargot: Samsung/escargot at fb66b79dcb45bea038a18c69b5e6e9b13bc2922e, build with ESCARGOT_CODE_CACHE=ON.
- QuickJS-NG: quickjs-ng/quickjs at 133cafb95a969fcb09dc2e020e9ec72d3c7a3140.
- Hermes: meta/hermes at d864d3f09d10e8aebe429715eeed5a4d7edf114d.
- Bun/JSC 1.4.5.

### Execution performance (median pre-warmed in-JS time, ms, lower is better)

The three blocks below are **not one shared runner**: only compare *within*
each Actions job, never infer precise cross-job percentage differences.

| 8-mode job | Numeric | Reorder | Proxy window | CSS |
|---|---:|---:|---:|---:|
| Bun/JSC | 30 | 25 | 65 | 185 |
| QuickJS-NG bytecode | 254 | 227 | 390 | 1023 |
| Hermes bytecode | 137 | 134 | 518 | 836 |
| Static Hermes native | 125 | 133 | 502 | 836 |

| PrimJS job | Numeric | Reorder | Proxy window | CSS |
|---|---:|---:|---:|---:|
| Bun/JSC | 23 | 24 | 61 | 180 |
| PrimJS source | 353 | 185 | 516 | 1287 |
| PrimJS serialized bytecode | 351 | 186 | 511 | 1291 |

| Escargot job | Numeric | Reorder | Proxy window | CSS |
|---|---:|---:|---:|---:|
| Bun/JSC | 29 | 24 | 65 | 186 |
| Escargot source | 142 | 256 | 310 | 1481 |
| Escargot cached-source | 141 | 255 | 309 | 1462 |

### Peak process RSS and process wall time

Recorded by /usr/bin/time for each independent trial. Each value is a
three-process median, **not JavaScript heap size** and not a memory-leak result.

| Mode | Wall seconds | Peak RSS MiB |
|---|---:|---:|
| 8-mode: Bun/JSC | 0.32 | 55.5 |
| Node/V8 | 0.61 | 59.4 |
| SpiderMonkey 115 | 0.76 | 31.6 |
| QuickJS-NG bytecode | 1.92 | 6.6 |
| Hermes bytecode | 1.65 | 14.1 |
| Static Hermes native ELF | 1.62 | 14.6 |
| PrimJS job: Bun/JSC | 0.30 | 55.9 |
| PrimJS serialized bytecode | 2.37 | 9.4 |
| Escargot job: Bun/JSC | 0.32 | 55.7 |
| Escargot cached-source | 2.19 | 13.8 |

### Recommendation and boundaries

For the tested untyped music-list/state/style JS kernels, **Bun/JSC is the
fastest practical baseline overall**. The interpreters have much smaller
process RSS; QuickJS-NG and PrimJS offer genuine source-free bytecode
execution; Escargot can cache compiled code across processes but does not
satisfy the strict offline bytecode requirement. Keeping Escargot as a
standalone bytecode contender would require additional runtime API work,
and its current pure-JS timings do not justify prioritizing that work.

PrimJS's mobile ARM64 template interpreter has not been tested; its Linux
x86-64 result must not be treated as the best available ARM64 speed. Neither
JIT warmup equality, application startup, nor GPUIX JS-to-Rust calls,
retained-tree mutations, real rendering, or mobile hardware performance
are measured by this kernel suite. For those claims a separate host-level
benchmark is mandatory.
