// Browser-side orchestrator for live Hermes WASM HBC -> gpui_web Canvas.
// Active only when URL search params contain mode=live.
(function () {
  const params = new URLSearchParams(window.location.search);
  if (params.get("mode") !== "live") {
    return;
  }
  const framework = params.get("f") === "solid" ? "solid" : "svelte";

  function failBench(message) {
    console.error("GPUI_WEB_LIVE_DRIVER_FAIL:" + message);
    const el = document.getElementById("gpui-bench-result");
    if (el) {
      el.textContent = JSON.stringify({ error: String(message), framework });
      el.setAttribute("data-status", "fail");
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function waitForBindings(timeoutMs) {
    const start = performance.now();
    while (performance.now() - start < timeoutMs) {
      const b = window.wasmBindings;
      if (
        b &&
        typeof b.gpui_web_push_hermes_batch === "function" &&
        typeof b.gpui_web_get_state === "function"
      ) {
        const state = JSON.parse(b.gpui_web_get_state());
        if (state.ready) {
          return b;
        }
      }
      await sleep(25);
    }
    throw new Error("Timed out waiting for gpui_web wasmBindings to become ready");
  }

  async function waitForState(bindings, predicate, timeoutMs, label) {
    const start = performance.now();
    while (performance.now() - start < timeoutMs) {
      const state = JSON.parse(bindings.gpui_web_get_state());
      if (state.error) {
        throw new Error("Rust GPUI Web error: " + state.error);
      }
      if (predicate(state)) {
        return state;
      }
      await sleep(4);
    }
    throw new Error("Timed out waiting for state: " + label);
  }

  async function runLive() {
    const bindings = await waitForBindings(30000);
    if (typeof window.CreateHermesVM !== "function") {
      throw new Error("CreateHermesVM is not available on window");
    }

    const chunkStore = new Map();
    const errs = [];
    let forwardedBatches = 0;

    function handleStdoutLine(raw) {
      const line = String(raw);
      if (line.startsWith("HERMES_MUTATION_BATCH:")) {
        const payload = line.slice("HERMES_MUTATION_BATCH:".length);
        forwardedBatches += 1;
        bindings.gpui_web_push_hermes_batch(payload);
        return;
      }
      if (line.startsWith("HERMES_MUTATION_CHUNK:")) {
        const rest = line.slice("HERMES_MUTATION_CHUNK:".length);
        const c1 = rest.indexOf(":");
        const c2 = rest.indexOf(":", c1 + 1);
        const c3 = rest.indexOf(":", c2 + 1);
        if (c1 < 0 || c2 < 0 || c3 < 0) {
          throw new Error("Malformed HERMES_MUTATION_CHUNK header");
        }
        const id = rest.slice(0, c1);
        const idx = Number(rest.slice(c1 + 1, c2));
        const total = Number(rest.slice(c2 + 1, c3));
        const slice = rest.slice(c3 + 1);
        let entry = chunkStore.get(id);
        if (!entry) {
          entry = { parts: new Array(total), received: 0, total };
          chunkStore.set(id, entry);
        }
        entry.parts[idx] = slice;
        entry.received += 1;
        if (entry.received === entry.total) {
          const fullPayload = entry.parts.join("");
          chunkStore.delete(id);
          forwardedBatches += 1;
          bindings.gpui_web_push_hermes_batch(fullPayload);
        }
        return;
      }
      if (line.startsWith("GPUI_SCENE_OK:")) {
        console.log("GPUI_WEB_LIVE_HERMES:" + line);
      }
    }

    const vm = await window.CreateHermesVM({
      locateFile: (name) => "./" + name,
      print: (line) => {
        try {
          handleStdoutLine(line);
        } catch (err) {
          errs.push(String(err));
        }
      },
      printErr: (line) => errs.push(String(line)),
    });

    const files = [
      ["bootstrap.hbc", "/bootstrap.hbc"],
      [framework + ".hbc", "/app.hbc"],
      ["click.hbc", "/click.hbc"],
    ];
    for (const [url, target] of files) {
      const resp = await fetch("./" + url);
      if (!resp.ok) {
        throw new Error("Failed to fetch " + url + ": HTTP " + resp.status);
      }
      vm.FS.writeFile(target, new Uint8Array(await resp.arrayBuffer()));
    }

    const rcBoot = vm.ccall("hermes_run_hbc_file", "number", ["string"], ["/bootstrap.hbc"]);
    if (rcBoot === -6) {
      throw new Error("bootstrap.hbc failed: " + errs.join("\n"));
    }
    const rcApp = vm.ccall("hermes_run_hbc_file", "number", ["string"], ["/app.hbc"]);
    if (rcApp === -6) {
      throw new Error(framework + ".hbc failed: " + errs.join("\n"));
    }
    if (errs.length > 0) {
      throw new Error("Hermes init stderr: " + errs.join("\n"));
    }
    if (chunkStore.size > 0) {
      throw new Error("Incomplete chunked batches after init: " + chunkStore.size);
    }
    console.log(
      "GPUI_WEB_LIVE_INIT_SENT:" + framework + ":batches=" + forwardedBatches
    );

    await waitForState(
      bindings,
      (st) => st.phase === "interactive",
      15000,
      "initial scene applied and verified"
    );

    for (let i = 0; i < 120; i++) {
      const before = JSON.parse(bindings.gpui_web_get_state());
      const expectedSamples = before.render_samples + 1;
      const rcClick = vm.ccall("hermes_run_hbc_file", "number", ["string"], ["/click.hbc"]);
      if (rcClick === -6) {
        throw new Error("click.hbc failed at step " + (i + 1) + ": " + errs.join("\n"));
      }
      if (errs.length > 0) {
        throw new Error("Hermes click stderr at step " + (i + 1) + ": " + errs.join("\n"));
      }
      await waitForState(
        bindings,
        (st) => st.applied_updates >= i + 1 && st.render_samples >= expectedSamples,
        5000,
        "render sample for click " + (i + 1)
      );
      await sleep(16);
    }
    console.log("GPUI_WEB_LIVE_CLICKS_DONE:" + framework + ":total_batches=" + forwardedBatches);
  }

  runLive().catch((err) => failBench(err && err.stack ? err.stack : String(err)));
})();
