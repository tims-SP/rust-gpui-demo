import App from "./App.jsx";
import {render} from "../../renderers/solid.js";
import {resetScene} from "../../shared/scene.js";
import {runBenchmark} from "../../shared/workload.js";
(async()=>{
 const root=resetScene();
 render(()=><App/>,root);
 await runBenchmark("solid",()=>Promise.resolve());
})().catch(e=>{console.error("GPUI_FATAL:"+e.stack);throw e;});
