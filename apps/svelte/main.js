import {mount,tick} from "svelte";
import renderer from "../../renderers/svelte.js";
import App from "./App.svelte";
import {resetScene} from "../../shared/scene.js";
import {runBenchmark} from "../../shared/workload.js";
(async()=>{
  const root=resetScene();
  mount(App,{target:root,renderer});
  await tick();
  await runBenchmark("svelte",()=>tick());
})().catch(e=>{console.error("GPUI_FATAL:"+e.stack);throw e;});
