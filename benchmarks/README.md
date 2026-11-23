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
