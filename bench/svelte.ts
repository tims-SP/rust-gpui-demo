import { flushSync } from "svelte";
import { render } from "gpuix-svelte";
import { commit, get_native } from "gpuix-svelte/renderer";
import { assertWindowState, instrumentNative, measurePhase, writeResult } from "./common.ts";
import App from "./SvelteApp.svelte";
import InlineApp from "./SvelteInline.svelte";
const SelectedApp = process.env.SVELTE_STYLE_MODE === "inline" ? InlineApp : App;
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
  const settle = () => { flushSync(); commit(); };
  await Bun.sleep(700);
  const phases = {
    single: await measurePhase(120, i => app.updateTitle(12, "Song 12 / " + i), settle),
    theme: await measurePhase(24, i => app.changeTheme(i % 2 ? "#8b5cf6" : "#ff6699"), settle),
    offscreen: await measurePhase(200, i => app.updateTitle(5000 + i, "Offscreen " + i), settle),
    reorder: await measurePhase(24, () => app.rotate(), settle),
    window: await measurePhase(120, i => app.shiftWindow(i + 1), settle),
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
