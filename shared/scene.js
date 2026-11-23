// Shared non-DOM scene graph. Each framework uses the same host protocol.
// The mutations can be emitted to JSI without serializing JS callback closures.
let nextId=1, ops=[], root=null;
const scalar=v=>typeof v==="function"?"[function]":v===undefined?null:v;
function record(op){ops.push(op);}
export function makeNode(type,name="",data=""){
  const n={id:nextId++,type,name,data:String(data),attrs:{},children:[],parent:null,listeners:{}};
  record(["create",n.id,type,name,String(data)]);return n;
}
export function resetScene(){nextId=1;ops=[];root=makeNode("fragment");return root;}
export function getRoot(){return root;}
export function flush(){const batch=ops;ops=[];if(typeof globalThis.gpuiEmit==="function")globalThis.gpuiEmit(JSON.stringify(batch));return batch;}
export function attach(parent,node,before=null){
  if(node.type==="fragment"){for(const child of [...node.children])attach(parent,child,before);return;}
  // Solid's keyed reconciliation may insert an existing node before itself.
  if(node===before && node.parent===parent)return;
  if(before!==null && before.parent!==parent)throw Error("Anchor not in target parent");
  if(node===parent)throw Error("Self-parenting");
  for(let p=parent;p;p=p.parent)if(p===node)throw Error("Cycle");
  if(node.parent)detach(node);
  const i=before?parent.children.indexOf(before):parent.children.length;
  if(i<0)throw Error("Missing anchor");
  parent.children.splice(i,0,node);node.parent=parent;
  record(["insert",parent.id,node.id,before?.id??null]);
}
export function detach(node){
  if(!node.parent)return;
  const p=node.parent,i=p.children.indexOf(node);
  if(i<0)throw Error("Detached node missing");p.children.splice(i,1);node.parent=null;
  record(["remove",p.id,node.id]);
}
export function changeText(node,value){const text=String(value);if(text!==node.data){node.data=text;record(["text",node.id,text]);}}
export function setAttr(node,key,value){node.attrs[key]=value;record(["attr",node.id,key,scalar(value)]);}
export function removeAttr(node,key){delete node.attrs[key];record(["attr",node.id,key,null]);}
export function setListener(node,type,handler,enabled=true){
  if(!node.listeners[type])node.listeners[type]=new Set();
  if(enabled)node.listeners[type].add(handler);else node.listeners[type].delete(handler);
  record(["event",node.id,type,node.listeners[type].size>0]);
}
export function findById(node,id){
  if(node.attrs?.id===id)return node;
  for(const child of node.children){const x=findById(child,id);if(x)return x;}return null;
}
export function dispatchEvent(id,type="click"){
  const node=findById(root,id);
  if(!node)throw Error("Event target not found: "+id);
  const handlers=node.listeners[type];
  if(!handlers||handlers.size===0)throw Error("No event listener for "+type);
  for(const callback of [...handlers])callback({type,target:node});
}
export function getText(node){return node.type==="text"?node.data:node.children.map(getText).join("");}
export function snapshot(node=root){
  if(!node)throw Error("No root");
  const result={type:node.type};
  if(node.type==="element"){result.name=node.name;result.attrs=Object.fromEntries(Object.entries(node.attrs).filter(([key])=>!/^on/i.test(key)));}
  if(node.type==="text")result.text=node.data;
  if(node.children.length)result.children=node.children.map(snapshot);
  return result;
}
export function assertScene(count,start,theme){
  const panel=findById(root,"app"),counter=findById(root,"counter"),list=findById(root,"tracks");
  if(!panel||!counter||!list)throw Error("Required nodes missing");
  if(getText(counter).trim()!=="Count: "+count)throw Error("Counter mismatch: "+getText(counter));
  if(panel.attrs.theme!==theme)throw Error("Theme mismatch: "+panel.attrs.theme);
  const rows=list.children.filter(x=>x.type==="element"&&x.name==="row");
  if(rows.length!==48)throw Error("Rendered rows: "+rows.length);
  if(rows[0].attrs.id!=="track-"+start)throw Error("First row mismatch: "+rows[0].attrs.id);
  if(rows[47].attrs.id!=="track-"+(start+47))throw Error("Last row mismatch");
  return {count,start,theme,renderedRows:rows.length};
}
export function assertEventClicks(count){
  const eventButton=findById(root,"event-button");
  if(!eventButton||getText(eventButton).trim()!=="Clicks: "+count)
    throw Error("Event clicks mismatch: "+(eventButton&&getText(eventButton)));
}
export function assertReorder(){
  const list=findById(root,"reorder");
  if(!list)throw Error("Reorder list missing");
  const rows=list.children.filter(x=>x.type==="element"&&x.name==="row");
  if(rows.length!==1000)throw Error("Keyed list size "+rows.length);
  if(rows[0].attrs.id!=="order-0" || rows[999].attrs.id!=="order-999")
    throw Error("Incorrect keyed reorder endpoints");
}
