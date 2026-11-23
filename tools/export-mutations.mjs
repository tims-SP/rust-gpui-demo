import {spawnSync} from "node:child_process";
import {mkdirSync,writeFileSync} from "node:fs";
mkdirSync("results/mutations",{recursive:true});
for(const f of ["svelte","solid"]){
  const proc=spawnSync(process.execPath,["tools/emit-mutations.mjs",f],{
    encoding:"utf8",maxBuffer:50*1024*1024,timeout:180000
  });
  if(proc.status!==0)throw Error(f+" trace execution failed: "+proc.stderr);
  const lines=proc.stdout.split(/\r?\n/);
  const batches=lines.filter(x=>x.startsWith("UI_MUTATION_BATCH:"))
    .map(x=>JSON.parse(x.slice("UI_MUTATION_BATCH:".length)));
  const results=lines.filter(x=>x.startsWith("BENCH_RESULT:"))
    .map(x=>JSON.parse(x.slice("BENCH_RESULT:".length)));
  if(results.length!==1 || batches.length<5 || !lines.includes("GPUI_SCENE_OK:"+f))
    throw Error("missing genuine framework traces "+f);
  const r=results[0];
  const operations=batches.reduce((n,x)=>n+x.length,0);
  if(operations!==r.initMutations+r.mutations)
    throw Error("trace operations mismatch "+f+" "+operations);
  writeFileSync("results/mutations/"+f+".json",JSON.stringify({
    framework:f, operations, scene:r.scene, batches
  }));
  console.log("FRAMEWORK_MUTATION_TRACE_EXPORTED:"+f+":"+operations+":"+batches.length);
}
