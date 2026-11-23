// Run the actual built framework bundle and capture the same JSON mutation
// batches that a live JSI bridge would receive. No simulated DOM.
const framework = process.argv[2];
if (!["svelte", "solid"].includes(framework)) throw Error("unknown framework");
globalThis.gpuiEmit = (json) => console.log("UI_MUTATION_BATCH:" + json);
await import("../dist/" + framework + ".js");
