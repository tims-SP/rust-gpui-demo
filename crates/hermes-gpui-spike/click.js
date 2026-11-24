// Repeatedly invoke the framework's own registered event handler in one VM.
globalThis.__gpuiExpectedClicks = (globalThis.__gpuiExpectedClicks || 1000) + 1;
if (typeof globalThis.__gpuiInteractiveClick !== "function") {
  throw Error("framework did not register its persistent interactive callback");
}
globalThis.__gpuiInteractiveClick(globalThis.__gpuiExpectedClicks);
"interactive-click-dispatched";
