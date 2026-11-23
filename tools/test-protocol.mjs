import {resetScene,makeNode,attach,detach,changeText,setAttr,
  setListener,dispatchEvent,flush,findById} from "../shared/scene.js";
const root=resetScene(),n=makeNode("element","label"),text=makeNode("text","","A");
setAttr(n,"id","probe");attach(root,n);attach(n,text);changeText(text,"B");
const a=makeNode("element","row"),b=makeNode("element","row");
attach(root,a);attach(root,b);attach(root,b,b);  // must not detach its own anchor
attach(root,b,a);
if(root.children[0]!==n||root.children[1]!==b||root.children[2]!==a)throw Error("Keyed reorder malformed");
let clicked=0;
setListener(n,"click",()=>clicked++,true);
dispatchEvent("probe");
if(clicked!==1)throw Error("Event roundtrip malformed");
const batch=flush();
if(!batch.every(Array.isArray)||!batch.some(x=>x[0]==="event"))throw Error("Protocol malformed");
if(findById(root,"probe")!==n)throw Error("Lookup malformed");
let cycleFailed=false;
try{attach(n,root);}catch(_){cycleFailed=true;}
if(!cycleFailed)throw Error("Cycle was accepted");
detach(n);
if(findById(root,"probe")!==null)throw Error("Removal malformed");
console.log("GPUI_MUTATION_PROTOCOL_OK");
