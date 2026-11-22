import { createMemo, createSignal, For } from "solid-js";
import { createStore } from "solid-js/store";
import { render, useGpuixRequired, resetRender } from "@gpuix/solid";
import type { GpuixRenderer } from "@gpuix/native";
import { instrumentNative, measurePhase, writeResult } from "./common.ts";

instrumentNative();
const base = Array.from({ length: 10000 }, (_, id) => ({ id, title: "Song " + id }));
const [tracks, setTracks] = createStore(base);
const [order, setOrder] = createSignal(base.slice(0, 48).map(row => row.id));
const [windowStart, setWindowStart] = createSignal(0);
const visibleRows = createMemo(() => windowStart() === 0
  ? order().map(id => tracks[id]!)
  : Array.from({ length: 48 }, (_, index) => tracks[windowStart() + index]!));
const [accent, setAccent] = createSignal("#8b5cf6");
let native: GpuixRenderer | undefined;

function App() {
  native = useGpuixRequired() as GpuixRenderer;
  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", padding: 20, gap: 2, backgroundColor: "#101620" }}>
      <For each={visibleRows()}>{track => (
        <div style={{ display: "flex", flexDirection: "row", height: 12, padding: 3 }}>
          <text style={{ color: accent(), fontSize: 12 }}>{track.title}</text>
        </div>
      )}</For>
    </div>
  );
}

try {
  const root = render(() => <App />, { title: "Solid / GPUI Linux comparison", width: 680, height: 900 });
  if (!native) throw new Error("Solid root did not bind a real native renderer");
  await Bun.sleep(700);
  const phases = {
    single: await measurePhase(120, i => setTracks(12, "title", "Song 12 / " + i), () => root.flushSync(() => {})),
    theme: await measurePhase(24, i => setAccent(i % 2 ? "#8b5cf6" : "#ff6699"), () => root.flushSync(() => {})),
    reorder: await measurePhase(24, () => setOrder(rows => [...rows.slice(1), rows[0]!]), () => root.flushSync(() => {})),
    window: await measurePhase(120, i => setWindowStart(i + 1), () => root.flushSync(() => {})),
  };
  setWindowStart(0);
  root.flushSync(() => {});
  await Bun.sleep(400);
  await writeResult("solid", phases, native);
  resetRender();
  process.exit(0);
} catch (error) {
  console.error("SOLID_BENCH_FAILED", error);
  process.exit(1);
}
