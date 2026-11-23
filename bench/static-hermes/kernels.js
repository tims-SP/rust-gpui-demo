// Same self-contained JS workload runs unchanged on Bun/JSC,
// Hermes bytecode VM, and shermes-compiled native Linux executable.
// This is NOT a GPUIX application or an FFI test. Do not call it one.
"use strict";

const tracks = Array.from({ length: 10000 }, (_, id) => ({ id, title: "Song " + id }));
const delegatedGet = { get(target, key) { return Reflect.get(target, key); } };
const proxied = new Proxy(tracks.map(row => new Proxy(row, delegatedGet)), delegatedGet);

function numeric(rounds) {
  let value = 123456789;
  for (let i = 0; i < rounds; i++) {
    value = (Math.imul(value, 1664525) + 1013904223) >>> 0;
  }
  return value;
}

function reorder(rounds) {
  let order = Array.from({ length: 48 }, (_, id) => id);
  let checksum = 0;
  for (let i = 0; i < rounds; i++) {
    order = [...order.slice(1), order[0]];
    checksum = (checksum + order[0] + order[24]) | 0;
  }
  return checksum;
}

function proxiedWindow(rounds) {
  let checksum = 0;
  for (let i = 0; i < rounds; i++) {
    const offset = i % 9952;
    const visible = Array.from({ length: 48 }, (_, j) => proxied[offset + j]);
    checksum = (checksum + visible[0].id + visible[47].id + visible[12].title.length) | 0;
  }
  return checksum;
}

function scopedStyle(rounds) {
  const css = "color: var(--accent); font-size: 12px; padding: 3px; background-color: #101620;";
  const colors = ["#8b5cf6", "#ff6699"];
  let checksum = 0;
  for (let i = 0; i < rounds; i++) {
    const vars = colors[i % 2];
    for (let j = 0; j < 48; j++) {
      const declarations = css.replace("var(--accent)", vars).split(";");
      let pieces = 0;
      for (let k = 0; k < declarations.length; k++) {
        const colon = declarations[k].indexOf(":");
        if (colon < 0) continue;
        const name = declarations[k].slice(0, colon).trim();
        const value = declarations[k].slice(colon + 1).trim();
        pieces += name.length + value.length;
      }
      checksum = (checksum + pieces) | 0;
    }
  }
  return checksum;
}

const cases = [
  ["numeric", numeric, 5000000, 30000],
  ["keyed_reorder", reorder, 120000, 1000],
  ["proxied_visible_window", proxiedWindow, 45000, 350],
  ["scoped_css_substitution", scopedStyle, 13000, 50],
];
const observed = [];
for (const item of cases) {
  const name = item[0], fn = item[1], rounds = item[2], warmup = item[3];
  // Repeat warm-up; it is never included in timing.
  fn(warmup);
  fn(warmup);
  const start = Date.now();
  const checksum = fn(rounds);
  const elapsedMs = Date.now() - start;
  if (!(elapsedMs >= 0) || !Number.isFinite(checksum)) throw Error("Invalid result: " + name);
  observed.push({ name, rounds, checksum, elapsedMs });
}
const message = "STATIC_HERMES_KERNEL=" + JSON.stringify({ workload: "gpui-inspired-pure-js-not-native-ui", cases: observed });
if (typeof print === "function") print(message);
else if (typeof console !== "undefined") console.log(message);
else throw Error("No output function");
