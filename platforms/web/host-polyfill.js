// Runs in Hermes JSI (not V8). The same matching shim HBC is deliberately
// evaluated again after mounting to simulate a browser-originated event.
// No recompilation or browser-JS evaluation of the Svelte/Solid bundles.
if (!globalThis.__gpuiShimInitialized) {
  globalThis.__gpuiShimInitialized = true;
  globalThis.setImmediate = function(callback) { callback(); return 0; };
  globalThis.queueMicrotask = function(callback) { Promise.resolve().then(callback); };
  globalThis.__forwardMutations = false;
  globalThis.gpuiEmit = function(payload) {
    if (globalThis.__forwardMutations) {
      const text = String(payload);
      console.log("HERMES_MUTATION_BATCH:" + text);
      const bridge = globalThis.__gpuiWebBridge;
      if (bridge && typeof bridge.pushBatch === "function") {
        bridge.pushBatch(text);
      }
    }
  };
} else {
  if (typeof globalThis.__gpuiInteractiveClick !== "function") {
    throw Error("Hermes interactive host callback unavailable");
  }
  globalThis.__forwardMutations = true;
  globalThis.__gpuiInteractiveClick();
}
