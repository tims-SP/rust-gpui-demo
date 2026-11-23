import { readFile } from "node:fs/promises";
import vm from "node:vm";
import assert from "node:assert/strict";
function walk(node, out = []) {
  if (node && typeof node === "object") {
    if (node.attrs?.id) out.push({tag: node.tag, id: node.attrs.id, theme: node.attrs.theme,
      style: node.attrs.style, content: text(node)});
    for (const child of node.children || []) walk(child, out);
  }
  return out;
}
function text(node) {
  if (typeof node === "string") return node;
  if (node === null || node === undefined) return "";
  return (node.children || []).map(text).join("");
}
const states = {};
for (const framework of ["svelte", "solid"]) {
  const batches = [];
  const context = {console, setTimeout, clearTimeout, queueMicrotask,
    __gpuiMutationBatch: batch => batches.push(batch)};
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(await readFile("dist/" + framework + ".js", "utf8"), context, {
    timeout: 15000, filename: framework + ".js"
  });
  const demo = context.__gpuiDemo;
  assert.ok(demo?.control?.increment, framework + " did not mount");
  await demo.settle();
  demo.flush();
  const initial = walk(demo.snapshot());
  assert.equal(initial.find(x => x.id === "counter")?.content.trim(), "Counter 0");
  assert.equal(initial.filter(x => x.id?.startsWith("track-")).length, 48);
  demo.dispatch("counter", "click");
  for (let i = 0; i < 100; i++) demo.control.increment();
  await demo.settle(); demo.flush();
  assert.equal(walk(demo.snapshot()).find(x => x.id === "counter")?.content.trim(), "Counter 101");
  for (let i = 0; i < 30; i++) demo.control.move();
  demo.control.theme();
  await demo.settle(); demo.flush();
  const moved = walk(demo.snapshot());
  assert.equal(moved.find(x => x.id === "app").theme, "dark");
  assert.equal(moved.find(x => x.id === "tracks").tag, "list");
  assert.equal(moved.filter(x => x.id?.startsWith("track-"))[0].id, "track-00030");
  demo.control.reorder();
  await demo.settle(); demo.flush();
  const reordered = walk(demo.snapshot());
  assert.equal(reordered.filter(x => x.id?.startsWith("reorder-")).length, 1000);
  assert.equal(reordered.find(x => x.id === "reorder-999").content, "Entry 999");
  states[framework] = {
    count: moved.find(x => x.id === "counter").content,
    windowFirst: moved.filter(x => x.id?.startsWith("track-"))[0].id,
    theme: moved.find(x => x.id === "app").theme,
    reorderFirst: reordered.filter(x => x.id?.startsWith("reorder-"))[0].id,
    nodeCount: demo.nodeCount(), mutations: batches.reduce((n, b) => n + b.length, 0)
  };
  console.log("CUSTOM_RENDERER_SMOKE_PASS=" + framework + " " + JSON.stringify(states[framework]));
}
for (const key of ["count", "windowFirst", "theme", "reorderFirst"]) {
  assert.equal(states.svelte[key], states.solid[key], "mismatch " + key);
}
console.log("CUSTOM_RENDERER_PARITY_PASS");
