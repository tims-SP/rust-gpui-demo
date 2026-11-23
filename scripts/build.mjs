import esbuild from "esbuild";
import { compile } from "svelte/compiler";
import { transformAsync } from "@babel/core";
import solidPreset from "babel-preset-solid";
import { readFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
const sveltePlugin = {
  name: "svelte-custom-renderer",
  setup(build) {
    build.onLoad({filter: /\.svelte$/}, async ({path}) => {
      const source = await readFile(path, "utf8");
      const result = compile(source, {
        filename: path, generate: "client",
        experimental: {customRenderer: true}, css: "external"
      });
      return {contents: result.js.code, loader: "js", resolveDir: dirname(path)};
    });
  }
};
const solidPlugin = {
  name: "solid-universal",
  setup(build) {
    build.onLoad({filter: /\.jsx$/}, async ({path}) => {
      const source = await readFile(path, "utf8");
      const output = await transformAsync(source, {
        filename: path, babelrc: false, configFile: false,
        presets: [[solidPreset, {
          generate: "universal",
          moduleName: "../../renderers/solid/renderer.js"
        }]]
      });
      return {contents: output.code, loader: "js", resolveDir: dirname(path)};
    });
  }
};
await mkdir("dist", {recursive: true});
for (const [name, entry, plugin] of [
  ["svelte", "apps/demo-svelte/main.js", sveltePlugin],
  ["solid", "apps/demo-solid/main.jsx", solidPlugin]
]) {
  await esbuild.build({
    entryPoints: [entry], outfile: "dist/" + name + ".js",
    bundle: true, format: "iife", platform: "browser",
    conditions: ["svelte-custom-renderer", "browser"],
    target: "es2020", plugins: [plugin], logLevel: "warning",
    legalComments: "none"
  });
  console.log("BUILD_OK=" + name);
}
