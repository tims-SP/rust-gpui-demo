import { GpuixRenderer } from "@gpuix/native";
import { mkdirSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

type PhaseStats = { batches: number; mutations: number; bytes: number; byOp: Record<string, number> };
type TimedPhase = PhaseStats & { iterations: number; elapsedMs: number; msPerOperation: number; p50Ms: number; p95Ms: number; p99Ms: number };
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
  const durations: number[] = [];
  const start = performance.now();
  try {
    for (let i = 0; i < iterations; i++) {
      const t0 = performance.now();
      update(i);
      settle();
      durations.push(performance.now() - t0);
    }
    // Time only the measured work. Never include a fixed timer in performance numbers.
    const elapsedMs = performance.now() - start;
    active = undefined;
    await Bun.sleep(60);
    const sorted = durations.sort((a, b) => a - b);
    const percentile = (p: number) => +sorted[Math.min(sorted.length - 1, Math.ceil(p * sorted.length) - 1)]!.toFixed(4);
    return { ...sample, iterations, elapsedMs: +elapsedMs.toFixed(3),
      msPerOperation: +(elapsedMs / iterations).toFixed(4),
      p50Ms: percentile(0.5), p95Ms: percentile(0.95), p99Ms: percentile(0.99) };
  } finally {
    active = undefined;
  }
}

export async function writeResult(framework: string, phases: Record<string, TimedPhase>, native: GpuixRenderer): Promise<void> {
  if (Object.values(phases).some(p => p.batches === 0 || p.mutations === 0)) {
    throw new Error("Native mutation probe recorded zero batches: not a valid comparison");
  }
  const live = native as unknown as {
    getAutomationTree?: (forceRender?: boolean) => string;
    getPaintedText?: () => string[];
  };
  if (typeof live.getAutomationTree !== "function") throw new Error("Linux live renderer has no automation tree API");
  const tree = live.getAutomationTree(true);
  const painted = typeof live.getPaintedText === "function" ? live.getPaintedText() : [];
  if (!String(tree).includes("Song 12 / 119") && !painted.some(t => t.includes("Song 12 / 119"))) {
    throw new Error("Live GPUI tree/paint missing final song title; tree " + String(tree).slice(0, 600) + "; painted " + JSON.stringify(painted.slice(0, 8)));
  }
  const treeLabels: string[] = [];
  const walk = (node: unknown): void => {
    if (!node || typeof node !== "object") return;
    const value = node as { text?: unknown; children?: unknown };
    if (typeof value.text === "string" && /^Song [0-9]+(?: \/ [0-9]+)?$/.test(value.text)) {
      treeLabels.push(value.text);
    }
    if (Array.isArray(value.children)) for (const child of value.children) walk(child);
  };
  walk(JSON.parse(tree));
  const paintedSongs = painted.filter(t => /^Song [0-9]+(?: \/ [0-9]+)?$/.test(t));
  const visibleSongs = paintedSongs.length >= 10 ? paintedSongs : treeLabels;
  if (visibleSongs.length !== 48 || visibleSongs[0] !== "Song 24") {
    throw new Error("Keyed reorder not reflected in live GPUI automation tree. First song labels: " +
      JSON.stringify(visibleSongs.slice(0, 12)) + "; tree preview: " + tree.slice(0, 1200));
  }
  mkdirSync("results", { recursive: true });
  const trial = Number(process.env.BENCH_TRIAL ?? "0");
  if (!Number.isInteger(trial) || trial < 0 || trial > 100) throw new Error("Invalid BENCH_TRIAL");
  const png = "results/" + framework + "-" + trial + ".png";
  const snapshot = spawnSync("import", ["-window", "root", png], { timeout: 15000 });
  if (snapshot.status !== 0) {
    console.error("X11 screenshot failed", snapshot.stderr?.toString());
    throw new Error("Failed to capture real Linux X11 screen");
  }
  const imageStats = spawnSync("identify", ["-format", "%[standard-deviation]", png], { timeout: 15000 });
  const deviation = Number(imageStats.stdout?.toString());
  if (imageStats.status !== 0 || !Number.isFinite(deviation) || deviation <= 0) {
    throw new Error("X11 screenshot is empty/unreadable (stddev=" + deviation + "): " + imageStats.stderr?.toString());
  }
  const data = { framework, runtime: "Bun", platform: process.platform,
    backend: "real GpuixRenderer Linux window (Xvfb + Mesa Vulkan software rasterizer)",
    trial, rows: 48, datasetRows: 10000, phases,
    retainedTreeBytes: Buffer.byteLength(tree), visibleSongs: visibleSongs.length,
    memory: { rssBytes: process.memoryUsage().rss, heapUsedBytes: process.memoryUsage().heapUsed },
    screenshot: png, screenshotDeviation: deviation };
  writeFileSync("results/" + framework + "-" + trial + ".json", JSON.stringify(data, null, 2) + "\n");
  console.log("BENCHMARK_RESULT=" + JSON.stringify(data));
}
