"use strict";
const fs=require("node:fs"),path=require("node:path");
const base=path.resolve("results/hermes-web/browser");
const glue=path.join(base,"hermes.cjs");
if(!fs.existsSync(glue))fs.copyFileSync(path.join(base,"hermes.js"),glue);
const create=require(glue);
const expected={count:256,start:40,theme:"light",renderedRows:48};
(async()=>{
 fs.mkdirSync("results/hermes-web", {recursive:true});
 for(const f of ["svelte","solid"]){
   const output=[],errors=[];
   const vm=await create({
     locateFile:n=>path.join(base,n),
     print:s=>output.push(String(s)),
     printErr:s=>errors.push(String(s))
   });
   vm.FS.writeFile("/shim.hbc",fs.readFileSync(path.join(base,"shim.hbc")));
   const shimResult=vm.ccall("hermes_run_hbc_file","number",["string"],["/shim.hbc"]);
   if(shimResult===-6)throw Error("Hermes shim failed: "+JSON.stringify(errors));
   vm.FS.writeFile("/demo.hbc",fs.readFileSync(path.join(base,f+".hbc")));
   const code=vm.ccall("hermes_run_hbc_file","number",["string"],["/demo.hbc"]);
   if(code===-6)throw Error("Hermes "+f+" bytecode eval failed: "+JSON.stringify(errors));
   const records=output.filter(x=>x.startsWith("BENCH_RESULT:"));
   if(records.length!==1||!output.includes("GPUI_SCENE_OK:"+f))
     throw Error("Missing actual Hermes "+f+" output; got "+JSON.stringify(output.slice(-4)));
   const result=JSON.parse(records[0].slice("BENCH_RESULT:".length));
   if(result.framework!==f||JSON.stringify(result.final)!==JSON.stringify(expected))
     throw Error("Wrong "+f+" Hermes scene result: "+JSON.stringify(result.final));
   fs.writeFileSync(path.join("results/hermes-web",f+".json"),JSON.stringify(result,null,2));
   console.log("HERMES_WEB_HBC_FRAMEWORK_PASS:"+f+" mutations="+result.mutations);
 }
})().catch(e=>{console.error(e.stack);process.exitCode=1});
