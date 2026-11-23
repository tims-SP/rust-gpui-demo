import { render } from "../../renderers/solid/renderer.js";
import App from "./App.jsx";
import { makeNode, flush, snapshot, dispatch, nodeCount } from "../../renderers/shared/host.js";
const root = makeNode("fragment");
const control = {};
render(() => App({control}), root);
globalThis.__gpuiDemo = {
  control, root, snapshot: () => snapshot(root), dispatch: (id, type) => dispatch(root, id, type),
  flush, settle: () => Promise.resolve(), nodeCount
};
