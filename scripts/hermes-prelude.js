// Hermes CLI lacks browser scheduling globals. This only fills Web-platform primitives.
if (typeof globalThis.queueMicrotask !== "function") {
  globalThis.queueMicrotask = function(fn) { Promise.resolve().then(fn); };
}
globalThis.__gpuiMutationBatch = function(batch) {
  if (!Array.isArray(batch)) throw Error("mutation batch not array");
  globalThis.__receivedMutations = (globalThis.__receivedMutations || 0) + batch.length;
};
