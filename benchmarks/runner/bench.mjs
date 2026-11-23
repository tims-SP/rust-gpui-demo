// Baseline only: JavaScript + in-memory mutation collection. NO GPUI or GPU here.
import { readFile, mkdir, writeFile } from "node:fs/promises";
import vm from "node:vm";
import { performance } from "node:perf_hooks";
const samples = [];
const durations = {};
for (const framework of ["svelte", "solid"]) {
  const bundle = await readFile("dist/" + framework + ".js", "utf8");
  for (let run = 0; run < 5; run++) {
    let mutations = 0, batchCount = 0;
    const context = {console, setTimeout, clearTimeout, queueMicrotask,
      __gpuiMutationBatch: batch => {mutations += batch.length; batchCount++;}};
    context.globalThis = context;
    vm.createContext(context);
    const start = performance.now();
    vm.runInContext(bundle, context, {timeout: 15000});
    const demo = context.__gpuiDemo;
    await demo.settle(); demo.flush();
    const startupMs = performance.now() - start;
    const actions = [
      ["counter", 10000, () => demo.control.increment()],
      ["visible_window", 500, () => demo.control.move()],
      ["style_toggle", 500, () => demo.control.theme()],
      ["event_roundtrip", 1000, () => demo.dispatch("counter", "click")],
      ["keyed_reorder", 20, () => demo.control.reorder()]
    ];
    for (const [name, iterations, action] of actions) {
      let t0 = performance.now();
      for (let i = 0; i < iterations; i++) {
        action();
        // Both frameworks commit at the same measured batch boundary.
        if (i % 50 === 49 || i === iterations - 1) {
          await demo.settle();
          demo.flush();
        }
      }
      const ms = performance.now() - t0;
      samples.push({runtime: "node-vm-not-hermes", framework, run, phase: name,
        iterations, elapsed_ms: ms, mutations, batches: batchCount});
    }
    samples.push({runtime: "node-vm-not-hermes", framework, run,
      phase: "startup_to_host_tree", iterations: 1, elapsed_ms: startupMs,
      mutations, batches: batchCount});
  }
}
for (const framework of ["svelte", "solid"]) {
  durations[framework] = {};
  for (const phase of new Set(samples.map(s => s.phase))) {
    const values = samples.filter(s => s.framework === framework && s.phase === phase)
      .map(s => s.elapsed_ms).sort((a,b) => a-b);
    durations[framework][phase] = {
      p50_ms: values[2], min_ms: values[0], max_ms: values[4],
      n: values.length
    };
  }
}
await mkdir("benchmarks/results", {recursive: true});
await writeFile("benchmarks/results/node-baseline.json", JSON.stringify({
  label: "HOST_JS_ONLY_NOT_HERMES_NOT_GPUI", engine: process.version,
  runs: samples, summary: durations
}, null, 2));
console.log(JSON.stringify(durations, null, 2));
console.log("NODE_BASELINE_COMPLETE_NOT_GPU");
