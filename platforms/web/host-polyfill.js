// Evaluated INSIDE Hermes (not in Node/V8). The earlier minimal JSI host
// intentionally omitted Ibex's event-loop globals. In the benchmark we need
// deterministic same-turn scheduling for the custom renderer commit barrier.
globalThis.setImmediate=function(callback){callback();return 0;};
globalThis.queueMicrotask=function(callback){Promise.resolve().then(callback);};
