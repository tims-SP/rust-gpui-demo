# Acceptance and metrics

1. Both frameworks compile with a real custom renderer and no DOM globals.
2. Both generate and update a genuine host scene tree, identical final state and 48 physical rows.
3. Node is a diagnostic only: precompiled HBC MUST execute in real Ibex2 native Hermes.
4. Each of the six platforms must separately report BUILD, RUN, and GPUI RENDER with screenshot/pixel proof. Build-only is not render.
5. Within-platform paired measurements only; never compare absolute times from different hardware as framework rankings.
6. Collect raw JSON, mutations, startup, memory, draw latency and frame percentiles if and when available. Missing values = not measured.
7. Web must use Hermes VM Wasm, not substitute the browser V8 as the JS runtime.
8. Android needs a real backend and compatible runner. No fake Android pass.
9. Archived Hermes-only baseline: Native https://github.com/tims-SP/rust-gpui-demo/actions/runs/45173224108 ; Web https://github.com/tims-SP/rust-gpui-demo/actions/runs/45187557146
