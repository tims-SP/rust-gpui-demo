import {createRenderer} from "solid-js/universal";
import {makeNode,attach,detach,changeText,setAttr,removeAttr} from "../shared/scene.js";
export const {render,effect,memo,createComponent,createElement,createTextNode,
  insertNode,insert,spread,setProp,mergeProps,use}=createRenderer({
  createElement(name){return makeNode("element",name);},
  createTextNode(t){return makeNode("text","",t);},
  replaceText(n,t){changeText(n,t);},
  setProperty(n,k,v){if(v===undefined||v===null)removeAttr(n,k);else setAttr(n,k,v);},
  insertNode(parent,node,anchor){attach(parent,node,anchor);},
  removeNode(parent,node){if(node.parent!==parent)throw Error("Remove parent mismatch");detach(node);},
  isTextNode(n){return n.type==="text";},
  getParentNode(n){return n.parent;},
  getFirstChild(n){return n.children[0]??null;},
  getNextSibling(n){return n.parent?.children[n.parent.children.indexOf(n)+1]??null;}
});
export {For,Show,Index} from "solid-js";
