import json
import unittest
from pathlib import Path
import importlib.util

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("metrics", root / "extract-gpui-replay.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def log(**updates):
    d = {"schema": "gpui-render-replay/v1", "framework": "svelte",
         "live_jsi_to_gpui": False, "live_hermes_vm": False,
         "scheduled_updates": 120, "applied_updates": 120,
         "render_callbacks_with_pending_update": 115,
         "p50_us": 350, "p95_us": 800, "p99_us": 1200}
    d.update(updates)
    return "GPUI_WINDOW_CREATED\nGPUI_REPLAY_BENCH_RESULT:" + json.dumps(d) + "\nGPUI_REPLAY_BENCH_PASS:svelte\n"

class TestExtract(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(mod.extract(log(), "svelte")["p50_us"], 350)
    def test_missing_marker(self):
        with self.assertRaises(ValueError): mod.extract("GPUI_WINDOW_CREATED", "svelte")
    def test_wrong_framework(self):
        with self.assertRaises(ValueError): mod.extract(log(), "solid")
    def test_incomplete(self):
        with self.assertRaises(ValueError): mod.extract(log(applied_updates=119), "svelte")
    def test_claim_falsification(self):
        with self.assertRaises(ValueError): mod.extract(log(live_jsi_to_gpui=True), "svelte")
    def test_no_render(self):
        with self.assertRaises(ValueError): mod.extract(log(render_callbacks_with_pending_update=0), "svelte")
    def test_repeated_results(self):
        with self.assertRaises(ValueError): mod.extract(log()+log(), "svelte")

if __name__ == "__main__": unittest.main()
