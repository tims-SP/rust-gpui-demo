// Invoke the framework's own registered event handler in the same persistent VM.
if (typeof globalThis.__gpuiInteractiveClick !== "function") {
  throw Error("framework did not register its persistent interactive callback");
}
globalThis.__gpuiInteractiveClick();
"interactive-click-dispatched";
