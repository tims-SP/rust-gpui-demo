import {assertScene,flush,snapshot} from "./scene.js";
export async function runBenchmark(framework,settle){
  if(typeof globalThis.__gpuiDrive!=="function")throw Error("Component not mounted");
  await settle();
  assertScene(0,0,"light");
  const initMutations=flush().length;
  const measurements={};
  let mutations=0;
  async function measure(name,rounds,change){
    const start=Date.now();
    for(let i=1;i<=rounds;i++){change(i);await settle();}
    const ms=Date.now()-start;
    const batch=flush();
    measurements[name]={iterations:rounds,ms,mutations:batch.length};
    mutations+=batch.length;
  }
  await measure("counter",256,i=>globalThis.__gpuiDrive("counter",i));
  await measure("window",40,i=>globalThis.__gpuiDrive("window",i));
  await measure("theme",50,i=>globalThis.__gpuiDrive("theme",i%2?"dark":"light"));
  const final=assertScene(256,40,"light");
  const result={framework,initMutations,mutations,measurements,final,scene:snapshot()};
  console.log("BENCH_RESULT:"+JSON.stringify(result));
  console.log("GPUI_SCENE_OK:"+framework);
}
