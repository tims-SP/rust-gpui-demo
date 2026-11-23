import { mount, tick } from "svelte";
import renderer from "../../renderers/svelte/renderer.js";
import App from "./App.svelte";
import { flush, snapshot, dispatch, nodeCount } from "../../renderers/shared/host.js";
const root = renderer.createFragment();
const control = {};
mount(App, {target: root, renderer, props: { control }});
globalThis.__gpuiDemo = {
  control, root, snapshot: () => snapshot(root), dispatch: (id, type) => dispatch(root, id, type),
  flush, settle: () => tick(), nodeCount
};
