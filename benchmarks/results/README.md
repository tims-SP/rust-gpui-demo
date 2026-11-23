# Six-platform Hermes + Svelte/Solid evidence matrix

This report separates real GPUI render proof from measured GPUI timer-driven
rebuild latency. It **does not** claim complete live Hermes→JSI→GPU performance.
The source for every GPUI view is a precomputed Hermes scene JSON.

| Platform | Framework | Actual GPUI scene | Update→Render P50 | P95 | Mobile G1 readiness | CI evidence |
|---|---|---|---:|---:|---:|---|
| linux | svelte | PASS | — | — | — | [Run 45212271704](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271704) |
| linux | solid | PASS | — | — | — | [Run 45212271704](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271704) |
| windows | svelte | PASS | — | — | — | [Run 45203114141](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45203114141) |
| windows | solid | PASS | — | — | — | [Run 45203114141](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45203114141) |
| macos | svelte | PASS | — | — | — | [Run 45212271889](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271889) |
| macos | solid | PASS | — | — | — | [Run 45212271889](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45212271889) |
| web | svelte | PASS | — | — | — | [Run 45204482618](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45204482618) |
| web | solid | PASS | — | — | — | [Run 45204482618](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45204482618) |
| ios | svelte | PASS | — | — | 15556 ms | [Run 45242919984](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45242919984) |
| ios | solid | PASS | — | — | 3321 ms | [Run 45242919984](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45242919984) |
| android | svelte | UNVERIFIED | — | — | — | Unverified |
| android | solid | UNVERIFIED | — | — | — | Unverified |

**Metric definitions:** P50/P95 = elapsed microseconds between scheduled
GPUI state mutation and the next `Render` callback. This excludes real
GPU submission/presentation and any Hermes runtime/JSI propagation.
Each platform uses different runner hardware: compare Svelte/Solid only
within the same run and don't treat mobile G1 polling time as FPS or
framework latency. iOS/Android G1 includes screenshot polling and cold
boot effects, and is not a clean Svelte-vs-Solid speed comparison.

**Measured cells:** 0/12.
**Rendered cells:** 10/12.
**Full six-platform end-to-end benchmark:** NOT COMPLETE.
