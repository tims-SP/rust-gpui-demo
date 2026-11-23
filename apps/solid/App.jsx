import {createSignal,createMemo,For} from "solid-js";
export default function App(){
 const [count,setCount]=createSignal(0);
 const [start,setStart]=createSignal(0);
 const [theme,setTheme]=createSignal("light");
 const rows=createMemo(()=>Array.from({length:48},(_,i)=>({id:start()+i,title:"Track "+(start()+i)})));
 globalThis.__gpuiDrive=(op,value)=>{
   if(op==="counter")setCount(value);
   else if(op==="window")setStart(value);
   else if(op==="theme")setTheme(value);
   else throw Error("Unknown operation "+op);
 };
 return <panel id="app" theme={theme()}>
   <label id="counter">Count: {count()}</label>
   <list id="tracks"><For each={rows()}>{item=><row id={"track-"+item.id}>{item.title}</row>}</For></list>
 </panel>;
}
