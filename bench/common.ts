import { GpuixRenderer } from "@gpuix/native";
import { mkdirSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

type PhaseStats = { batches: number; mutations: number; bytes: number; byOp: Record<string, number> };
type TimedPhase = PhaseStats & { iterations: number; elapsedMs: number; msPerOperation: number };
let active: PhaseStats | undefined;
let installed = false;

export function instrumentNative(): void {
  if (installed) return;
  installed = true;
  const proto = GpuixRenderer.prototype as unknown as { applyBatch(json: string): number[] };
  const original = proto.applyBatch;
  if (typeof original !== "function") throw new Error("Cannot intercept native applyBatch; cannot benchmark FFI");
  proto.applyBatch = function (json: string): number[] {
    if (active) {
      const entries = JSON.parse(json) as unknown[][];
      active.batches++;
      active.mutations += entries.length;
      active.bytes += Buffer.byteLength(json);
      for (const entry of entries) {
        const key = String(entry[0]);
        active.byOp[key] = (active.byOp[key] ?? 0) + 1;
      }
    }
    return original.call(this, json);
  };
}

export async function measurePhase(
  iterations: number,
  update: (index: number) => void,
  settle: () => void
): Promise<TimedPhase> {
  if (active) throw new Error("Nested benchmark phases are forbidden");
  const sample: PhaseStats = { batches: 0, mutations: 0, bytes: 0, byOp: {} };
  active = sample;
  const start = performance.now();
  try {
    for (let i = 0; i < iterations; i++) {
      update(i);
      settle();
    }
    // Give the GPUI event loop a chance to process committed batches.
    await Bun.sleep(60);
    const elapsedMs = performance.now() - start;
    return { ...sample, iterations, elapsedMs: +elapsedMs.toFixed(3),
      msPerOperation: +(elapsedMs / iterations).toFixed(4) };
  } finally {
    active = undefined;
  }
}

export async function writeResult(framework: string, phases: Record<string, TimedPhase>, native: GpuixRenderer): Promise<void> {
  if (Object.values(phases).some(p => p.batches === 0 || p.mutations === 0)) {
    throw new Error("Native mutation probe recorded zero batches: not a valid comparison");
  }
  const getTree = (native as unknown as { getTreeJson?: () => string }).getTreeJson;
  if (typeof getTree !== "function") throw new Error("GpuixRenderer.getTreeJson unavailable");
  const tree = getTree.call(native);
  if (typeof tree !== "string" || !tree.includes("Song 12 / 119")) {
    throw new Error("Native retained tree is missing the expected updated song title; received " + String(tree).slice(0, 700));
  }
  mkdirSync("results", { recursive: true });
  const snapshot = spawnSync("import", ["-window", "root", "results/" + framework + ".png"], { timeout: 15000 });
  if (snapshot.status !== 0) {
    console.error("X11 screenshot failed", snapshot.stderr?.toString());
    throw new Error("Failed to capture real Linux X11 screen");
  }
  const data = { framework, runtime: "Bun", platform: process.platform,
    backend: "real GpuixRenderer Linux window (Xvfb + Mesa Vulkan software rasterizer)",
    rows: 48, phases, retainedTreeBytes: Buffer.byteLength(tree),
    screenshot: "results/" + framework + ".png" };
  writeFileSync("results/" + framework + ".json", JSON.stringify(data, null, 2) + "\n");
  console.log("BENCHMARK_RESULT=" + JSON.stringify(data));
}
