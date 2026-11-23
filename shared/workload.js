import {assertScene,assertEventClicks,assertReorder,dispatchEvent,flush,snapshot} from "./scene.js";
export async function runBenchmark(framework,settle){
  if(typeof globalThis.__gpuiDrive!=="function")throw Error("Component not mounted");
  await settle();
  assertScene(0,0,"light");
  assertEventClicks(0);
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
  await measure("event_roundtrip",1000,()=>dispatchEvent("event-button"));
  assertEventClicks(1000);
  await measure("keyed_reorder",20,()=>globalThis.__gpuiDrive("reorder"));
  assertReorder();
  globalThis.__gpuiDrive("collapse");
  await settle();
  mutations+=flush().length;
  const final=assertScene(256,40,"light");
  assertEventClicks(1000);
  const result={framework,initMutations,mutations,measurements,final,scene:snapshot()};
  console.log("BENCH_RESULT:"+JSON.stringify(result));
  console.log("GPUI_SCENE_OK:"+framework);
  // A second HBC invocation in the SAME persistent Hermes runtime performs
  // a real registered framework event and emits actual update mutations.
  globalThis.__gpuiInteractiveClick=async function(){
    dispatchEvent("event-button");
    await settle();
    assertEventClicks(1001);
    const batch=flush();
    if(!batch.some(op=>op[0]==="text")) throw Error("click produced no text mutation");
    console.log("HERMES_INTERACTIVE_RESULT:"+framework+":1001:"+batch.length);
  };
}
