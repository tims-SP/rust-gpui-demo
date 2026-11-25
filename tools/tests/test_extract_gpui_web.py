import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "webbench", Path(__file__).resolve().parents[1] / "extract-gpui-web.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

DATA = dict(schema="gpui-render-replay/v1", platform="web",framework="svelte",
            scheduled_updates=120,applied_updates=120,
            render_callbacks_with_pending_update=70,live_jsi_to_gpui=False,
            live_hermes_vm=False,p50_us=200,p95_us=1000,p99_us=1500)

def doc(payload=DATA, status="pass"):
    return f'<html><pre id="gpui-bench-result" data-status="{status}">{json.dumps(payload)}</pre></html>'

class Tests(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(module.extract(doc(),"svelte")["p50_us"], 200)
    def test_missing(self):
        with self.assertRaises(ValueError): module.extract("<html></html>","svelte")
    def test_not_ready(self):
        with self.assertRaises(ValueError): module.extract(doc(status="pending"),"svelte")
    def test_mislabel(self):
        with self.assertRaises(ValueError): module.extract(doc(),"solid")
    def test_partial(self):
        with self.assertRaises(ValueError): module.extract(doc({**DATA,"applied_updates":5}),"svelte")
    def test_no_frames(self):
        with self.assertRaises(ValueError): module.extract(doc({**DATA,"render_callbacks_with_pending_update":0}),"svelte")
    def test_fake_script(self):
        with self.assertRaises(ValueError):
            module.extract("<script>"+doc()+"</script>","svelte")

    def test_live_wasm_bridge_ok(self):
        live_payload = {
            **DATA,
            "source": "live-Hermes-WASM-in-browser",
            "live_hermes_vm": True,
            "live_jsi_to_gpui": True,
        }
        self.assertEqual(module.extract(doc(live_payload), "svelte")["live_hermes_vm"], True)
    def test_live_wasm_claim_without_live_source_rejected(self):
        bad_payload = {
            **DATA,
            "source": "precomputed-Hermes-scene",
            "live_hermes_vm": True,
            "live_jsi_to_gpui": True,
        }
        with self.assertRaises(ValueError):
            module.extract(doc(bad_payload), "svelte")

if __name__ == "__main__":
    unittest.main()
