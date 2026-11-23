# Six-platform benchmark evidence

Generate a strict 12-cell evidence matrix from real GitHub Actions artifacts:

```bash
python3 tools/collect-six-platform.py --out results/six-platform
```

Each platform/framework row records source CI run, render proof and any measured
GPUI timer-driven update->Render callback latency. Missing values stay null.
The current checked-in snapshot is in `benchmarks/results/latest.json` and
`benchmarks/results/README.md`. Refresh from new CI artifacts after successful
runs; do not confuse these callback timings with GPU presentation or full
Hermes/JSI end-to-end latency. Mobile G1 is screenshot readiness, not FPS.

Tests: `python3 -m unittest discover -s tools/tests -p 'test_*.py'`.

## Real Hermes Mutation → Rust apply stage

[CI run 45247776226](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45247776226)
passed seven independent Rust applications of actual Hermes-exported batches.
The verified source data is `benchmarks/results/hermes-rust-apply.json`.
This includes transactional cloning of the entire scene for each batch. It
excludes JS propagation, JSI host invocation, GPU rendering and presentation.
Workloads emit different operation counts and are **not an equal-operations
framework performance comparison**. On this runner, Svelte P50 was 219279 µs
(53095 operations) and Solid P50 was 326665 µs (47017 operations).
