# Six-platform Hermes + Svelte/Solid evidence matrix

This report separates real GPUI render proof from measured GPUI timer-driven
rebuild latency. It **does not** claim complete live Hermes→JSI→GPU performance.
The source for every GPUI view is a precomputed Hermes scene JSON.

| Platform | Framework | Actual GPUI scene | Update→Render P50 | P95 | P99 | Mobile G1 readiness | CI evidence |
|---|---|---|---:|---:|---:|---|
| linux | svelte | PASS | 1027 µs | 16127 µs | 32520 µs | — | [Run 45248284872](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248284872) |
| linux | solid | PASS | 1319 µs | 16227 µs | 16277 µs | — | [Run 45248284872](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248284872) |
| windows | svelte | PASS | 2258 µs | 16047 µs | 18496 µs | — | [Run 45248296457](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248296457) |
| windows | solid | PASS | 2533 µs | 16891 µs | 18220 µs | — | [Run 45248296457](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45248296457) |
| macos | svelte | PASS | — | — | — | — | [Run 45212271889](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271889) |
| macos | solid | PASS | — | — | — | — | [Run 45212271889](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271889) |
| web | svelte | PASS |  10580 µs | 24795 µs | 25150 µs | — | — | [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392) 
| web | solid | PASS |  10815 µs | 25945 µs | 88085 µs | — | — | [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392) 
| ios | svelte | PASS | — | — | — | 15556 ms | [Run 45242919984](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45242919984) |
| ios | solid | PASS | — | — | — | 3321 ms | [Run 45242919984](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45242919984) |
| android | svelte | UNVERIFIED | — | — | — | — | Unverified |
| android | solid | UNVERIFIED | — | — | — | — | Unverified |

**Metric definitions:** P50/P95 = elapsed microseconds between scheduled
GPUI state mutation and the next `Render` callback. This excludes real
GPU submission/presentation and any Hermes runtime/JSI propagation.
Each platform uses different runner hardware: compare Svelte/Solid only
within the same run and don't treat mobile G1 polling time as FPS or
framework latency. iOS/Android G1 includes screenshot polling and cold
boot effects, and is not a clean Svelte-vs-Solid speed comparison.

**Measured cells:** 6/12.
**Rendered cells:** 10/12.
**Full six-platform end-to-end benchmark:** NOT COMPLETE.

**Web evidence update (2026-11-23 UTC):** [Run 45266653392](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45266653392), commit `ab466b89`, artifact `gpui-web-official-canvas-svelte-solid`: both Svelte and Solid JSON files report `status=PASS`, `scheduled_updates=120`, `applied_updates=120`, with 34/35 render callbacks and screenshot PNGs. These are GPUI timer-driven replay callback timings, **not** live Hermes HBC/JSI or GPU Present timings. Chromium console reports a wgpu resize poll timeout warning, but the replay completion markers and metrics were emitted.
