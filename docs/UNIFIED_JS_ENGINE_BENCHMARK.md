# Unified 12-mode Linux JavaScript engine benchmark

Date: 2026-11-23. Environment: Ubuntu 24.04, one GitHub-hosted x86-64 runner.

Evidence: [Actions run 45158280307](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45158280307) on source commit 61f9eb547846298a711a166a636c98c79799c452; [all 60 process JSON files, compiled bytecode and RSS evidence](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45158280307/artifacts/14810531377).

CI caveat: All 60 process executions, checksum assertions and unified report generation passed. The workflow was marked failure only after report generation, because it tried to concatenate the obsolete REPORT.md instead of the generated UNIFIED_REPORT.md. Fixed by commit 62aaa29fa46233a47d43bdbca88200958f935ee8; [full CI rerun](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45160497906).

## Same-runner performance and peak memory

All 12 modes used the same original JS source, the same Linux host and five independent process trials per mode, with alternating execution order. Each kernel includes two unmeasured warm-up calls. Values are medians; lower is better.

| Engine / mode | Numeric ms | Reorder ms | Proxy ms | CSS ms | Whole-process wall s | Peak RSS MiB |
|---|---:|---:|---:|---:|---:|---:|
| Bun / JavaScriptCore | 26 | 23 | **74** | **193** | **0.33** | 55.6 |
| Node / V8 | **6** | **13** | 391 | 235 | 0.68 | 59.2 |
| SpiderMonkey 115 | 22 | 48 | 332 | 420 | 0.85 | 31.3 |
| QuickJS 2021 | 356 | 344 | 470 | 1376 | 2.58 | **6.7** |
| QuickJS-NG source | 323 | 277 | 438 | 1176 | 2.24 | **6.7** |
| QuickJS-NG bytecode | 330 | 282 | 437 | 1168 | 2.25 | **6.7** |
| PrimJS source | 444 | 194 | 523 | 1452 | 2.65 | 9.4 |
| PrimJS bytecode | 444 | 193 | 518 | 1449 | 2.64 | 9.4 |
| Escargot source | 143 | 280 | 386 | 1704 | 2.55 | 13.8 |
| Escargot cached source | 143 | 284 | 381 | 1743 | 2.59 | 13.8 |
| Hermes bytecode | 164 | 149 | 564 | 928 | 1.83 | 14.1 |
| Static Hermes native ELF | 151 | 147 | 576 | 891 | 1.79 | 14.6 |

Runtime correctness: all 60 processes produced identical work-case checksums and iteration counts.

Bytecode verification:
- PrimJS used a minimal benchmark-only CLI adapter to serialize bytecode to a disk file and load it in a fresh process without the compiler input file.
- QuickJS-NG produced raw bytecode and launched an independently executable runtime containing compiled bytecode.
- Hermes loaded optimized HBC using its matching pinned VM.
- Static Hermes generated an x86-64 machine-code ELF; this is native AOT rather than bytecode.
- Escargot produced and subsequently HIT a persistent disk cache in another process, but STILL REQUIRES THE ORIGINAL JS SOURCE for lookup. It does not pass source-free bytecode loading.

Interpretation: In these four untyped, GPUI-inspired pure-JS kernels, Bun/JSC wins proxy-state, CSS and overall wall-time; V8 wins numeric and reorder kernels. QuickJS-NG uses much less process memory but is slower on UI-style JS work; PrimJS and Escargot do not outperform Bun/JSC here. Static Hermes gives limited improvements over Hermes bytecode.

Limitations: This is not real GPUIX window rendering, Svelte/Solid-to-Rust FFI or native UI frame performance. PrimJS ARM64-only template interpreter optimizations are disabled on Linux x86-64. Cold start is not measured separately. Total wall time includes workload and startup; peak RSS measures the whole process, not JS heap. JIT tiering, GC and CPU/scheduler noise still matter even with five same-runner samples.

See [.github/workflows/static-hermes-native.yml](https://github.com/tims-SP/rust-gpui-demo/blob/main/.github/workflows/static-hermes-native.yml) and [unified_report.py](https://github.com/tims-SP/rust-gpui-demo/blob/main/bench/static-hermes/unified_report.py) for exact gates.
