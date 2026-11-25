// Minimal deterministic host globals for the framework HBC benchmark.
globalThis.console = { log: function () {}, warn: function () {}, error: function () {} };
globalThis.queueMicrotask = function (callback) { Promise.resolve().then(callback); };
globalThis.setTimeout = function (callback) { callback(); return 0; };
globalThis.clearTimeout = function () {};
globalThis.requestAnimationFrame = function (callback) { callback(Date.now()); return 0; };
globalThis.cancelAnimationFrame = function () {};
