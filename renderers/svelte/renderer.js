import { createRenderer } from "svelte/renderer";
import { makeNode, insert, remove, setText, setAttr, listen } from "../shared/host.js";
const renderer = createRenderer({
  createFragment: () => makeNode("fragment"),
  createElement: (name) => makeNode("element", name),
  createText: (data) => makeNode("text", "", data),
  createComment: (data) => makeNode("comment", "", data),
  getNodeType: (node) => node.type,
  getText: (node) => node.data,
  setText,
  getAttribute: (node, key) => node.attrs[key] ?? null,
  setAttribute: setAttr,
  removeAttribute: (node, key) => setAttr(node, key, null),
  hasAttribute: (node, key) => Object.hasOwn(node.attrs, key),
  getFirstChild: (node) => node.children[0] ?? null,
  getLastChild: (node) => node.children[node.children.length - 1] ?? null,
  getNextSibling: (node) => {
    if (!node.parent) return null;
    const siblings = node.parent.children;
    return siblings[siblings.indexOf(node) + 1] ?? null;
  },
  getParent: (node) => node.parent,
  insert, remove,
  addEventListener: (node, type, callback) => listen(node, type, callback, true),
  removeEventListener: (node, type, callback) => listen(node, type, callback, false)
});
export default renderer;
