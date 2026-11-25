import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "webbench", Path(__file__).resolve().parents[1] / "extract-gpui-web.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

DATA = dict(schema="gpui-render-replay/v1", platform="web", framework="svelte",
            scheduled_updates=120, applied_updates=120,
            render_callbacks_with_pending_update=70, live_jsi_to_gpui=False,
            live_hermes_vm=False, p50_us=200, p95_us=1000, p99_us=1500)

LIVE_SVELTE = dict(
    **{k: v for k, v in DATA.items() if k not in ("live_jsi_to_gpui", "live_hermes_vm")},
    source="live-Hermes-WASM-in-browser",
    live_hermes_vm=True,
    live_jsi_to_gpui=True,
    initial_hermes_mutation_batches=7,
    interactive_hermes_mutation_batches=120,
    scene_operations=53215,
    gpu_present_latency_ms=None,
    end_to_end_latency_ms=None,
)

def doc(payload=DATA, status="pass"):
    return f'<html><pre id="gpui-bench-result" data-status="{status}">{json.dumps(payload)}</pre></html>'

class Tests(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(module.extract(doc(), "svelte")["p50_us"], 200)
    def test_missing(self):
        with self.assertRaises(ValueError): module.extract("<html></html>", "svelte")
    def test_not_ready(self):
        with self.assertRaises(ValueError): module.extract(doc(status="pending"), "svelte")
    def test_mislabel(self):
        with self.assertRaises(ValueError): module.extract(doc(), "solid")
    def test_partial(self):
        with self.assertRaises(ValueError): module.extract(doc({**DATA, "applied_updates": 5}), "svelte")
    def test_no_frames(self):
        with self.assertRaises(ValueError): module.extract(doc({**DATA, "render_callbacks_with_pending_update": 0}), "svelte")
    def test_fake_script(self):
        with self.assertRaises(ValueError):
            module.extract("<script>" + doc() + "</script>", "svelte")

    def test_live_wasm_bridge_ok(self):
        res = module.extract(doc(LIVE_SVELTE), "svelte")
        self.assertTrue(res["live_hermes_vm"])
        self.assertEqual(res["scene_operations"], 53215)

    def test_live_wasm_claim_without_live_source_rejected(self):
        bad_payload = {**LIVE_SVELTE, "source": "precomputed-Hermes-scene"}
        with self.assertRaises(ValueError):
            module.extract(doc(bad_payload), "svelte")

    def test_live_wasm_wrong_ops_rejected(self):
        bad_payload = {**LIVE_SVELTE, "scene_operations": 123}
        with self.assertRaises(ValueError):
            module.extract(doc(bad_payload), "svelte")

    def test_live_wasm_non_null_gpu_present_rejected(self):
        bad_payload = {**LIVE_SVELTE, "gpu_present_latency_ms": 1.2}
        with self.assertRaises(ValueError):
            module.extract(doc(bad_payload), "svelte")

if __name__ == "__main__":
    unittest.main()
