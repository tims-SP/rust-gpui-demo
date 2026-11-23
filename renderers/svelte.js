import {createRenderer} from "svelte/renderer";
import {makeNode,attach,detach,changeText,setAttr,removeAttr,setListener} from "../shared/scene.js";
export default createRenderer({
  createFragment(){return makeNode("fragment");},
  createElement(name){return makeNode("element",name);},
  createText(data){return makeNode("text","",data);},
  createComment(data){return makeNode("comment","",data);},
  getNodeType(n){return n.type;},
  getText(n){return n.data;},
  setText(n,t){changeText(n,t);},
  getAttribute(n,k){return n.attrs[k]??null;},
  setAttribute(n,k,v){setAttr(n,k,v);},
  removeAttribute(n,k){removeAttr(n,k);},
  hasAttribute(n,k){return Object.prototype.hasOwnProperty.call(n.attrs,k);},
  getFirstChild(n){return n.children[0]??null;},
  getLastChild(n){return n.children[n.children.length-1]??null;},
  getNextSibling(n){return n.parent?.children[n.parent.children.indexOf(n)+1]??null;},
  getParent(n){return n.parent;},
  insert(parent,node,anchor){attach(parent,node,anchor);},
  remove(n){detach(n);},
  addEventListener(n,k,handler){setListener(n,k,handler,true);},
  removeEventListener(n,k,handler){setListener(n,k,handler,false);}
});
