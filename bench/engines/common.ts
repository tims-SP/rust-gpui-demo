import { GpuixRenderer } from "@gpuix/native";

type Stats = { batches: number; mutations: number; bytes: number; ops: Record<string, number>; nativeMs: number; probeMs: number };
let active: Stats | null = null;
const originalApply = GpuixRenderer.prototype.applyBatch;

export function installNativeProbe(): void {
  (GpuixRenderer.prototype as any).applyBatch = function (input: string) {
    const target = active;
    if (target) {
      const t0 = performance.now();
      const batch = JSON.parse(input) as any[][];
      target.batches++;
      target.mutations += batch.length;
      target.bytes += Buffer.byteLength(input);
      for (const entry of batch) {
        const name = String(entry[0]);
        target.ops[name] = (target.ops[name] ?? 0) + 1;
      }
      target.probeMs += performance.now() - t0;
    }
    const start = performance.now();
    const result = originalApply.call(this, input);
    if (target) target.nativeMs += performance.now() - start;
    return result;
  };
}

export function pause(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function phase(iterations: number, update: (i: number) => void, flush: () => void) {
  if (active) throw new Error("nested measurement");
  const stats: Stats = { batches: 0, mutations: 0, bytes: 0, ops: {}, nativeMs: 0, probeMs: 0 };
  const durations: number[] = [];
  active = stats;
  const start = performance.now();
  try {
    for (let i = 0; i < iterations; i++) {
      const t = performance.now();
      update(i);
      flush();
      durations.push(performance.now() - t);
    }
  } finally { active = null; }
  const elapsedMs = performance.now() - start;
  durations.sort((a,b)=>a-b);
  return { ...stats, iterations, elapsedMs: +elapsedMs.toFixed(4),
    p95Ms: +durations[Math.ceil(iterations*0.95)-1]!.toFixed(4),
    nativeMs: +stats.nativeMs.toFixed(4), probeMs: +stats.probeMs.toFixed(4) };
}

export function checkTree(native: GpuixRenderer, start: number) {
  const getTree = (native as any).getAutomationTree;
  if (typeof getTree !== "function") throw new Error("Native automation tree API missing");
  const tree = JSON.parse(getTree.call(native, true));
  const names: string[] = [];
  function walk(n: any) {
    if (n && typeof n.text === "string" && /^Song \d+(?: \/ \d+)?$/.test(n.text)) names.push(n.text);
    if (Array.isArray(n?.children)) for (const child of n.children) walk(child);
  }
  walk(tree);
  if (names.length !== 48 || names[0] !== "Song " + start ||
      names[47] !== "Song " + (start + 47)) {
    throw new Error("Wrong native order " + JSON.stringify(names.slice(0,48)));
  }
  return names;
}

export function complete(framework: "solid"|"svelte", native: GpuixRenderer, phases: Record<string, ReturnType<typeof phase>>) {
  if (phases.offscreen.mutations !== 0 || phases.offscreen.batches !== 0)
    throw new Error("Hidden-row edits emitted Native mutations");
  for (const name of ["single","theme","reorder","window"]) {
    if (phases[name].mutations < 1) throw new Error("Missing Native mutations in " + name);
  }
  const names = checkTree(native, 24);
  const runtime = {
    execPath: process.execPath,
    bun: process.versions.bun || null,
    hermes: (process.versions as any).hermes || null,
    node: process.versions.node || null,
    actualCommand: process.argv[0],
  };
  console.log("ENGINE_BENCH=" + JSON.stringify({
    framework, engine: process.env.BENCH_ENGINE, trial: Number(process.env.BENCH_TRIAL || 0),
    runtime, datasetRows: 10000, visibleRows: names.length, nativeBackend: "GPUIX 0.11 Linux real window",
    phases, rssBytes: process.memoryUsage?.().rss ?? null
  }));
}
