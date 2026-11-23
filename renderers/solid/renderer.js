import { createRenderer } from "solid-js/universal";
import { makeNode, insert, remove, setText, setAttr, listen } from "../shared/host.js";
const renderer = createRenderer({
  createElement: (name) => makeNode("element", name),
  createTextNode: (text) => makeNode("text", "", text),
  replaceText: (node, text) => setText(node, text),
  insertNode: (parent, node, anchor) => insert(parent, node, anchor),
  removeNode: (_parent, node) => remove(node),
  setProperty: (node, name, value, previous) => {
    if (/^on[A-Z]/.test(name)) {
      const event = name.slice(2).toLowerCase();
      if (typeof previous === "function") listen(node, event, previous, false);
      if (typeof value === "function") listen(node, event, value, true);
    } else setAttr(node, name, value);
  },
  isTextNode: (node) => node.type === "text",
  getParentNode: (node) => node.parent,
  getFirstChild: (node) => node.children[0] ?? null,
  getNextSibling: (node) => node.parent
    ? node.parent.children[node.parent.children.indexOf(node) + 1] ?? null : null
});
export const { render, effect, memo, createComponent, createElement, createTextNode,
  insert: solidInsert, insertNode, spread, setProp, mergeProps, use } = renderer;
// Babel's universal output imports a binding named 'insert', not 'solidInsert'.
export { solidInsert as insert };
