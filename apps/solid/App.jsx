import {createSignal,createMemo,For,Show} from "solid-js";
export default function App(){
 const [count,setCount]=createSignal(0);
 const [clicks,setClicks]=createSignal(0);
 const [start,setStart]=createSignal(0);
 const [theme,setTheme]=createSignal("light");
 const [expanded,setExpanded]=createSignal(false);
 const [order,setOrder]=createSignal(Array.from({length:1000},(_,i)=>i));
 const rows=createMemo(()=>Array.from({length:48},(_,i)=>start()+i));
 globalThis.__gpuiDrive=(op,value)=>{
   if(op==="counter")setCount(value);
   else if(op==="window")setStart(value);
   else if(op==="theme")setTheme(value);
   else if(op==="reorder"){setExpanded(true);setOrder((v)=>[...v].reverse());}
   else if(op==="collapse")setExpanded(false);
   else throw Error("Unknown operation "+op);
 };
 return <panel id="app" theme={theme()}>
   <label id="counter">Count: {count()}</label>
   <button id="event-button" onClick={()=>setClicks(v=>v+1)}>Clicks: {clicks()}</button>
   <Show when={expanded()} fallback={<list id="tracks"><For each={rows()}>{id=>
     <row id={"track-"+id}>{"Track "+id}</row>
   }</For></list>}>
     <list id="reorder"><For each={order()}>{id=><row id={"order-"+id}>{"Row "+id}</row>}</For></list>
   </Show>
 </panel>;
}
