import { profile } from "bun:jsc";
import { mkdirSync, writeFileSync } from "node:fs";

type Scenario = { name: string; iterations: number; run: (i: number) => void };

/** Scope CPU sampling to the warm update/host flush phase, never the compiler/startup. */
export function collectHotpathProfiles(framework: "solid" | "svelte", cases: Scenario[]): void {
  if (process.env.HOTPATH_PROFILE !== "1") return;
  mkdirSync("results", { recursive: true });
  const token = process.env.BENCH_TRIAL ?? "0";
  for (const item of cases) {
    // First warm the exact loop; JIT tiering should not be conflated with initial code loading.
    for (let i = 0; i < Math.min(200, item.iterations); i++) item.run(i);
    const start = performance.now();
    const result = profile(() => {
      for (let i = 0; i < item.iterations; i++) item.run(i);
    }, 100);
    const elapsedMs = performance.now() - start;
    const payload = {
      framework,
      scenario: item.name,
      iterations: item.iterations,
      sampleIntervalUs: 100,
      elapsedMs: +elapsedMs.toFixed(3),
      runtime: { bun: process.versions.bun ?? null, execPath: process.execPath },
      cpu: result,
    };
    const file = "results/hotpath-" + framework + "-" + item.name + "-" + token + ".json";
    writeFileSync(file, JSON.stringify(payload, null, 2) + "\n");
    const data = result as unknown as { functions?: unknown[] };
    console.log("PROFILE_SCOPE=" + JSON.stringify({
      framework, scenario: item.name, elapsedMs: payload.elapsedMs,
      profileKeys: Object.keys(result), functions: data.functions?.length,
      firstFunction: data.functions?.[0],
      file,
    }));
  }
}
