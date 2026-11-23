import { createMemo, createSignal, For } from "solid-js";
import { createStore } from "solid-js/store";
import { render, useGpuixRequired } from "@gpuix/solid";
import type { GpuixRenderer } from "@gpuix/native";
import { installNativeProbe, phase, pause, complete, checkTree } from "./common.ts";

installNativeProbe();
const initial = Array.from({length:10000},(_,id)=>({id,title:"Song "+id}));
const [tracks,setTracks] = createStore(initial);
const [order,setOrder] = createSignal(initial.slice(0,48).map(t=>t.id));
const [windowStart,setWindowStart] = createSignal(0);
const visible = createMemo(()=>windowStart()===0
  ? order().map(id=>tracks[id]!)
  : Array.from({length:48},(_,i)=>tracks[windowStart()+i]!));
const [accent,setAccent] = createSignal("#8b5cf6");
let native: GpuixRenderer | undefined;
function App(){
  native=useGpuixRequired() as GpuixRenderer;
  return <div style={{ display:"flex", flexDirection:"column", width:"100%", height:"100%", padding:20, gap:2, backgroundColor:"#101620" }}>
    <For each={visible()}>{track => (
      <div style={{display:"flex",flexDirection:"row",height:12,padding:3}}>
        <text style={{color:accent(),fontSize:12}}>{track.title}</text>
      </div>
    )}</For>
  </div>;
}
async function main(){
  const root=render(()=> <App/>,{title:"GPUIX Hermes engine Solid",width:680,height:900});
  if(!native) throw Error("native renderer was not bound");
  const flush=()=>root.flushSync(()=>{});
  await pause(700);
  for(let i=0;i<512;i++){setAccent(i%2?"#8b5cf6":"#ff6699");flush();}
  for(let i=0;i<192;i++){setOrder(list=>[...list.slice(1),list[0]!]);flush();}
  for(let i=0;i<240;i++){setWindowStart((i%120)+1);flush();}
  setWindowStart(0);flush();
  const phases={
    single:phase(120,i=>setTracks(12,"title","Song 12 / "+i),flush),
    theme:phase(24,i=>setAccent(i%2?"#8b5cf6":"#ff6699"),flush),
    offscreen:phase(200,i=>setTracks(5000+i,"title","Offscreen "+i),flush),
    reorder:phase(24,()=>setOrder(list=>[...list.slice(1),list[0]!]),flush),
    window:phase(120,i=>setWindowStart(i+1),flush)
  };
  checkTree(native,120);
  setWindowStart(0);flush();
  await pause(400);
  complete("solid",native,phases);
  await pause(2800);
  process.exit(0);
}
main().catch(e=>{console.error("ENGINE_FAILED solid",e?.stack||e);process.exit(1);});
