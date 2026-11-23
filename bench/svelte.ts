import { flushSync } from "svelte";
import { render, renderer } from "gpuix-svelte";
import { commit, get_native } from "gpuix-svelte/renderer";
import { assertWindowState, instrumentNative, measurePhase, writeResult } from "./common.ts";
import { collectHotpathProfiles } from "./hotpath.ts";
import App from "./SvelteApp.svelte";
import InlineApp from "./SvelteInline.svelte";
import StaticApp from "./SvelteStatic.svelte";
import GlobalThemeApp from "./SvelteGlobalTheme.svelte";
import RawListApp from "./SvelteRawList.svelte";
import RawOrderApp from "./SvelteRawOrder.svelte";
import IndexedWindowApp from "./SvelteIndexedWindow.svelte";
const staticStyle = process.env.SVELTE_STYLE_MODE === "static";
const SelectedApp = staticStyle ? StaticApp :
  process.env.SVELTE_STYLE_MODE === "inline" ? InlineApp :
  process.env.SVELTE_STYLE_MODE === "global" ? GlobalThemeApp :
  process.env.SVELTE_STYLE_MODE === "raw" ? RawListApp :
  process.env.SVELTE_STYLE_MODE === "raw-order" ? RawOrderApp :
  process.env.SVELTE_STYLE_MODE === "indexed-window" ? IndexedWindowApp : App;
import type { GpuixRenderer } from "@gpuix/native";

instrumentNative();
try {
  const app = render(SelectedApp, { title: "Svelte / GPUI Linux comparison", width: 680, height: 900 }) as {
    updateTitle: (index: number, title: string) => void;
    changeTheme: (color: string) => void;
    rotate: () => void;
    shiftWindow: (index: number) => void;
  };
  const native = get_native() as GpuixRenderer;
  if (!native) throw new Error("Svelte root did not bind a real native renderer");
  const tracing = process.env.SVELTE_HOST_TRACE === "1";
  type MethodTime = { calls: number; ms: number };
  type Trace = { flushMs: number; commitMs: number; host: Record<string, MethodTime> };
  let activeTrace: Trace | null = null;
  if (tracing) {
    const target = renderer as unknown as Record<string, (...args: unknown[]) => unknown>;
    for (const name of ["createElement", "createTextNode", "setAttribute", "insert", "remove", "setText"]) {
      const original = target[name];
      if (typeof original !== "function") throw new Error("Svelte host is missing " + name);
      target[name] = (...args) => {
        const t0 = performance.now();
        try { return original.apply(renderer, args); }
        finally {
          if (activeTrace) {
            const item = activeTrace.host[name] ??= { calls: 0, ms: 0 };
            item.calls++;
            item.ms += performance.now() - t0;
          }
        }
      };
    }
  }
  const settle = () => {
    const t0 = performance.now();
    flushSync();
    const t1 = performance.now();
    commit();
    const t2 = performance.now();
    if (activeTrace) {
      activeTrace.flushMs += t1 - t0;
      activeTrace.commitMs += t2 - t1;
    }
  };
  const measure = async (iterations: number, action: (i: number) => void) => {
    activeTrace = tracing ? { flushMs: 0, commitMs: 0, host: {} } : null;
    const trace = activeTrace;
    try {
      const result = await measurePhase(iterations, action, settle);
      if (!trace) return result;
      return {
        ...result,
        svelteTrace: {
          flushMs: +trace.flushMs.toFixed(4),
          commitMs: +trace.commitMs.toFixed(4),
          host: Object.fromEntries(Object.entries(trace.host).map(([key, value]) => [key, {
            calls: value.calls, ms: +value.ms.toFixed(4)
          }]))
        }
      };
    } finally { activeTrace = null; }
  };
  await Bun.sleep(700);
  if (process.env.THEME_ISOLATION === "1") {
    for (let i = 0; i < 512; i++) { app.changeTheme(i % 2 ? "#8b5cf6" : "#ff6699"); settle(); }
    for (let i = 0; i < 192; i++) { app.rotate(); settle(); }
    for (let i = 0; i < 240; i++) { app.shiftWindow((i % 120) + 1); settle(); }
    app.shiftWindow(0); settle();
  }
  collectHotpathProfiles("svelte", [
    { name: "single", iterations: 4800,
      run: i => { app.updateTitle(12, "Song 12 / " + i); settle(); } },
    { name: "theme", iterations: 1920,
      run: i => { app.changeTheme(i % 2 ? "#8b5cf6" : "#ff6699"); settle(); } },
    { name: "reorder", iterations: 1536,
      run: () => { app.rotate(); settle(); } },
    { name: "window", iterations: 2400,
      run: i => { app.shiftWindow((i % 120) + 1); settle(); } },
  ]);
  app.shiftWindow(0);
  settle();
  const phases = {
    single: await measure(120, i => app.updateTitle(12, "Song 12 / " + i)),
    ...(!staticStyle ? { theme: await measure(24, i => app.changeTheme(i % 2 ? "#8b5cf6" : "#ff6699")) } : {}),
    offscreen: await measure(200, i => app.updateTitle(5000 + i, "Offscreen " + i)),
    reorder: await measure(24, () => app.rotate()),
    window: await measure(120, i => app.shiftWindow(i + 1)),
  };
  assertWindowState(native, 120);
  app.shiftWindow(0);
  settle();
  await Bun.sleep(400);
  await writeResult("svelte", phases, native);
  process.exit(0);
} catch (error) {
  console.error("SVELTE_BENCH_FAILED", error);
  process.exit(1);
}
