// Deterministic host globals for live Hermes WASM -> GPUI Web Canvas.
// Runs inside the pinned Hermes WASM VM (not browser V8).
globalThis.setImmediate = function (callback) { callback(); return 0; };
globalThis.queueMicrotask = function (callback) { Promise.resolve().then(callback); };
globalThis.setTimeout = function (callback) { callback(); return 0; };
globalThis.clearTimeout = function () {};
globalThis.requestAnimationFrame = function (callback) { callback(Date.now()); return 0; };
globalThis.cancelAnimationFrame = function () {};

(function () {
  var nextBatchId = 1;
  var CHUNK_SIZE = 32768;
  globalThis.gpuiEmit = function (payload) {
    var text = String(payload);
    if (text.length <= CHUNK_SIZE) {
      console.log("HERMES_MUTATION_BATCH:" + text);
      return;
    }
    var id = nextBatchId++;
    var total = Math.ceil(text.length / CHUNK_SIZE);
    for (var i = 0; i < total; i++) {
      var slice = text.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
      console.log("HERMES_MUTATION_CHUNK:" + id + ":" + i + ":" + total + ":" + slice);
    }
  };
})();
