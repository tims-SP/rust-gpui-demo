"use strict";
const fs = require("node:fs");
const path = require("node:path");
// Emscripten emits CommonJS, while this repository declares .js as ESM.
const glue = path.resolve("results/ibex-hermes-wasm/browser/hermes.js");
const commonjs = path.resolve("results/ibex-hermes-wasm/browser/hermes.cjs");
fs.copyFileSync(glue, commonjs);
const createVM = require(commonjs);
if (typeof createVM !== "function") throw Error("Hermes Wasm factory unavailable");
(async () => {
  const output = [];
  const vm = await createVM({
    noInitialRun: true,
    locateFile: name => path.resolve("results/ibex-hermes-wasm/browser", name),
    print: line => output.push(String(line)),
    printErr: line => process.stderr.write(String(line) + "\n")
  });
  vm.FS.writeFile("/shared.hbc",
    fs.readFileSync("results/ibex-hermes-wasm/browser/shared.hbc"));
  try {
    const status = vm.callMain(["/shared.hbc"]);
    if (status !== 0 && status !== undefined) throw Error("Hermes exit: " + status);
  } catch (e) {
    if (!e || e.status !== 0) throw e;
  }
  if (!output.some(line => line.includes("HERMES_SHARED_OK=479820"))) {
    throw Error("Hermes Wasm failed: " + JSON.stringify(output));
  }
  console.log("HERMES_NODE_WASM_OK=479820");
})().catch(error => { console.error(error); process.exitCode = 1; });
