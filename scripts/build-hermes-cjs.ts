import { mkdirSync, writeFileSync } from "node:fs";
import { createSolidPlugin } from "@gpuix/solid/bun-plugin";
import { load_svelte, load_module, resolve_svelte } from "gpuix-svelte/plugin";
import type { BunPlugin } from "bun";

const sveltePlugin: BunPlugin = {
  name: "gpui-svelte-custom-bundle",
  setup(build) {
    build.onResolve({ filter: /^svelte(\/|$)/ }, resolve_svelte(["custom-renderer","production"]));
    build.onLoad({ filter: /\.svelte\.[jt]s$/ }, load_module);
    build.onLoad({ filter: /\.svelte$/ }, load_svelte);
  }
};
const banner = `
if(typeof globalThis.queueMicrotask!=="function"){globalThis.queueMicrotask=function(fn){process.nextTick(fn);};}
if(typeof globalThis.performance==="undefined"){globalThis.performance={now:function(){var t=process.hrtime();return t[0]*1e3+t[1]/1e6;}};}
`;
mkdirSync("dist/engines",{recursive:true});
for(const [framework,entry,plugin,conditions] of [
  ["solid","bench/engines/solid.tsx",createSolidPlugin(),["production"]],
  ["svelte","bench/engines/svelte.ts",sveltePlugin,["custom-renderer","production"]]
] as const) {
  let loaded=0;
  const result=await Bun.build({
    entrypoints:[entry],
    target:"node",
    format:"cjs",
    external:["@gpuix/native"],
    conditions:[...conditions],
    define:{"process.env.NODE_ENV":'"production"'},
    minify:false,
    plugins:[plugin],
    throw:false
  });
  if(!result.success || !result.outputs.length) {
    for(const log of result.logs)console.error(log);
    throw Error("Cannot produce "+framework+" CJS bundle");
  }
  const text=banner+(await result.outputs[0]!.text()).replace(/\bimport\(/g,"require(");
  if(/\bimport\(/.test(text))throw Error("Unconverted dynamic import");
  if(!text.includes("ENGINE_BENCH"))throw Error("Missing runtime benchmark marker in bundle");
  const outfile="dist/engines/"+framework+".cjs";
  writeFileSync(outfile,text);
  console.log("BUILD_CJS",{framework,outfile,size:text.length});
}
