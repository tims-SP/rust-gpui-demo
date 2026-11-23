"use strict";
const fs = require("node:fs");
const path = require("node:path");
const base = path.resolve("results/ibex-hermes-wasm/browser");
const glue = path.join(base, "hermes.js");
const commonjs = path.join(base, "hermes.cjs");
// This repo uses ESM .js scope; Emscripten's default glue is CommonJS.
fs.copyFileSync(glue, commonjs);
const createVM = require(commonjs);
if (typeof createVM !== "function") throw Error("JSI Hermes Wasm factory not exported");
(async function () {
  const stdout = [], stderr = [];
  const vm = await createVM({
    locateFile: name => path.join(base, name),
    print: line => stdout.push(String(line)),
    printErr: line => stderr.push(String(line))
  });
  const bytes = fs.readFileSync(path.join(base, "shared.hbc"));
  if (bytes.byteLength < 32) throw Error("Invalid HBC file");
  vm.FS.writeFile("/shared.hbc", bytes);
  const code = vm.ccall("hermes_run_hbc_file", "number", ["string"], ["/shared.hbc"]);
  if (code !== 479820 || !stdout.some(x => x.includes("HERMES_SHARED_OK=479820"))) {
    throw Error("JSI Hermes VM returned " + code + "; stdout=" +
      JSON.stringify(stdout) + "; stderr=" + JSON.stringify(stderr));
  }
  console.log("HERMES_NODE_WASM_OK=479820");
})().catch(error => { console.error(error); process.exitCode = 1; });
