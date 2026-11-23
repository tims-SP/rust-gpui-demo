import {build} from "esbuild";
import {compile} from "svelte/compiler";
import babel from "@babel/core";
import fs from "node:fs/promises";
import path from "node:path";
const sveltePlugin={
  name:"svelte-custom-renderer",
  setup(build){
    build.onLoad({filter:/\.svelte$/},async({path:file})=>{
      const source=await fs.readFile(file,"utf8");
      const result=compile(source,{
        filename:file,generate:"client",dev:false,css:"external",
        experimental:{customRenderer:true}
      });
      return {contents:result.js.code,loader:"js",resolveDir:path.dirname(file)};
    });
  }
};
const solidPlugin={
  name:"solid-universal-jsx",
  setup(build){
    build.onLoad({filter:/\.jsx$/},async({path:file})=>{
      const source=await fs.readFile(file,"utf8");
      const compiled=await babel.transformAsync(source,{
        filename:file,babelrc:false,configFile:false,
        presets:[["babel-preset-solid",{generate:"universal",moduleName:"./solid-renderer.js"}]]
      });
      return {contents:compiled.code,loader:"js",resolveDir:path.dirname(file)};
    });
  }
};
await fs.mkdir("dist",{recursive:true});
for(const [name,entry,plugins] of [
 ["svelte","apps/svelte/main.js",[sveltePlugin]],
 ["solid","apps/solid/main.jsx",[solidPlugin]]
]){
 await build({absWorkingDir:process.cwd(),entryPoints:[entry],outfile:"dist/"+name+".js",
   bundle:true,format:"iife",platform:"neutral",target:"es2020",minify:true,
   conditions:["svelte-custom-renderer","browser","module"],
   plugins,logLevel:"info"});
}
