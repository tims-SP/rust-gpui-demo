import {spawnSync} from "node:child_process";
import {mkdirSync,writeFileSync} from "node:fs";
mkdirSync("results",{recursive:true});
for(const f of ["svelte","solid"]){
 const r=spawnSync(process.execPath,["dist/"+f+".js"],{encoding:"utf8",timeout:120000});
 if(r.status!==0)throw Error(f+" execution failed\n"+r.stderr+"\n"+r.stdout);
 const lines=r.stdout.split("\n").filter(x=>x.startsWith("BENCH_RESULT:"));
 if(lines.length!==1||!r.stdout.includes("GPUI_SCENE_OK:"+f))throw Error(f+" missing markers");
 const data=JSON.parse(lines[0].slice(13));
 if(data.final.count!==256||data.final.renderedRows!==48||data.final.start!==40)throw Error(f+" wrong UI state");
 writeFileSync("results/node-"+f+".json",JSON.stringify(data,null,2));
 console.log("NODE_FRAMEWORK_OK:"+f+" mutations="+data.mutations);
}
