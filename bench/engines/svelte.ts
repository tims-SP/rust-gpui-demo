import { flushSync } from "svelte";
import { render } from "gpuix-svelte";
import { commit, get_native } from "gpuix-svelte/renderer";
import App from "../SvelteApp.svelte";
import type { GpuixRenderer } from "@gpuix/native";
import { installNativeProbe, phase, pause, complete, checkTree } from "./common.ts";

installNativeProbe();
async function main(){
  const app=render(App,{title:"GPUIX Hermes engine Svelte",width:680,height:900}) as {
    updateTitle(index:number,title:string):void;
    changeTheme(color:string):void;
    rotate():void;
    shiftWindow(index:number):void;
  };
  const native=get_native() as GpuixRenderer;
  if(!native)throw Error("Svelte did not bind the native renderer");
  const flush=()=>{flushSync();commit();};
  await pause(700);
  for(let i=0;i<512;i++){app.changeTheme(i%2?"#8b5cf6":"#ff6699");flush();}
  for(let i=0;i<192;i++){app.rotate();flush();}
  for(let i=0;i<240;i++){app.shiftWindow((i%120)+1);flush();}
  app.shiftWindow(0);flush();
  const phases={
    single:phase(120,i=>app.updateTitle(12,"Song 12 / "+i),flush),
    theme:phase(24,i=>app.changeTheme(i%2?"#8b5cf6":"#ff6699"),flush),
    offscreen:phase(200,i=>app.updateTitle(5000+i,"Offscreen "+i),flush),
    reorder:phase(24,()=>app.rotate(),flush),
    window:phase(120,i=>app.shiftWindow(i+1),flush)
  };
  checkTree(native,120);
  app.shiftWindow(0);flush();
  await pause(400);
  complete("svelte",native,phases);
  await pause(2800);
  process.exit(0);
}
main().catch(e=>{console.error("ENGINE_FAILED svelte",e?.stack||e);process.exit(1);});
