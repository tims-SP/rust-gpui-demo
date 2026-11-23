import {resetScene,makeNode,attach,detach,changeText,setAttr,flush,findById} from "../shared/scene.js";
const root=resetScene(),n=makeNode("element","label"),text=makeNode("text","","A");
setAttr(n,"id","probe");attach(root,n);attach(n,text);changeText(text,"B");
const batch=flush();
if(batch.length!==7||!batch.every(Array.isArray))throw Error("Protocol malformed: "+batch.length);
if(findById(root,"probe")!==n)throw Error("Lookup malformed");
detach(n);
if(findById(root,"probe")!==null)throw Error("Removal malformed");
console.log("GPUI_MUTATION_PROTOCOL_OK");
