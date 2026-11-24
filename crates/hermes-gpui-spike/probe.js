// Real HBC calls a JSI host function with a dynamic mutation batch.
globalThis.gpuiEmit(JSON.stringify([
  ["create", 1, "fragment", "", ""],
  ["create", 2, "element", "panel", ""],
  ["attr", 2, "id", "app"],
  ["create", 3, "text", "", "Live JSI mutation"],
  ["insert", 1, 2, null],
  ["insert", 2, 3, null]
]));
"mutation-sent";
