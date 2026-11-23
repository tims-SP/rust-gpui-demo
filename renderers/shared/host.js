// Identical mutation vocabulary and node semantics for Svelte and Solid.
// JS callbacks stay in the runtime. The transport crosses only JSON-like mutations.
let nextId = 1;
let queue = [];
const nodes = new Map();

export function makeNode(type, name = "", data = "") {
  const node = { id: nextId++, type, name, data: String(data), attrs: {},
    children: [], parent: null, listeners: Object.create(null) };
  nodes.set(node.id, node);
  queue.push({ op: "create", id: node.id, kind: type, name, text: node.data });
  return node;
}
export function insert(parent, node, anchor = null) {
  if (node.type === "fragment") {
    for (const child of [...node.children]) insert(parent, child, anchor);
    return;
  }
  if (node === anchor && node.parent === parent) return;
  if (anchor !== null && anchor.parent !== parent) throw Error("anchor parent mismatch");
  if (node === parent) throw Error("cannot insert parent into itself");
  if (node.parent !== null) {
    const previous = node.parent.children;
    const index = previous.indexOf(node);
    if (index < 0) throw Error("lost child");
    previous.splice(index, 1);
  }
  let at = anchor === null ? parent.children.length : parent.children.indexOf(anchor);
  if (at < 0) throw Error("missing anchor: parent=" + parent.id + " node=" + node.id + " anchor=" + anchor?.id);
  parent.children.splice(at, 0, node);
  node.parent = parent;
  queue.push({ op: "insert", parent: parent.id, id: node.id,
    before: anchor === null ? null : anchor.id });
}
export function remove(node) {
  if (!node.parent) return;
  const siblings = node.parent.children;
  const idx = siblings.indexOf(node);
  if (idx < 0) throw Error("lost child");
  siblings.splice(idx, 1);
  node.parent = null;
  queue.push({ op: "remove", id: node.id });
}
export function setText(node, value) {
  node.data = String(value);
  queue.push({ op: "text", id: node.id, value: node.data });
}
export function setAttr(node, key, value) {
  if (value == null) {
    delete node.attrs[key];
    queue.push({ op: "attribute", id: node.id, key, value: null });
  } else if (typeof value !== "function") {
    const normalized = typeof value === "object" ? JSON.stringify(value) : String(value);
    node.attrs[key] = normalized;
    queue.push({ op: "attribute", id: node.id, key, value: normalized });
  }
}
export function listen(node, type, callback, enabled) {
  if (!node.listeners[type]) node.listeners[type] = new Set();
  if (enabled) node.listeners[type].add(callback);
  else node.listeners[type].delete(callback);
  queue.push({ op: "event", id: node.id, event: type, enabled: node.listeners[type].size > 0 });
}
export function dispatch(root, target, type = "click") {
  const node = find(root, (n) => n.attrs.id === target);
  if (!node) throw Error("missing event target " + target);
  const handlers = node.listeners[type];
  if (!handlers || handlers.size === 0) throw Error("missing event handler " + target + ":" + type);
  for (const handler of [...handlers]) handler({ type, target: node });
}
export function find(node, predicate) {
  if (predicate(node)) return node;
  for (const child of node.children) {
    const found = find(child, predicate);
    if (found) return found;
  }
  return null;
}
export function snapshot(node) {
  if (node.type === "comment") return null;
  if (node.type === "text") return node.data;
  const children = node.children.map(snapshot).filter((x) => x !== null && x !== "");
  return { tag: node.name || node.type, attrs: {...node.attrs}, children };
}
export function flush() {
  const batch = queue;
  queue = [];
  if (typeof globalThis.__gpuiMutationBatch === "function") {
    globalThis.__gpuiMutationBatch(batch);
  }
  return batch;
}
export function nodeCount() { return nodes.size; }
