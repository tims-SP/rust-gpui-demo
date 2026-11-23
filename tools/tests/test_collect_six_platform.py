import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "collector", Path(__file__).resolve().parents[1] / "collect-six-platform.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def test_missing_does_not_create_fake_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            c = m.cell(Path(directory),"linux","svelte",{"run_id":None})
            self.assertEqual(c["metric_status"],"NOT_MEASURED")
            self.assertIsNone(c["gpui_replay_p95_us"])
            self.assertFalse(c["gpui_render_verified"])
    def test_valid_real_gpui_replay(self):
        data = {
            "schema":"gpui-render-replay/v1","platform":"linux","framework":"svelte",
            "scheduled_updates":120,"applied_updates":120,
            "render_callbacks_with_pending_update":111,"live_hermes_vm":False,
            "live_jsi_to_gpui":False,"p50_us":10,"p95_us":40,"p99_us":70
        }
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)/"gpui-linux"
            base.mkdir()
            (base/"svelte-metrics.json").write_text(json.dumps(data))
            (base/"svelte.png").write_bytes(b"PNG_FIXTURE")
            c=m.cell(Path(directory),"linux","svelte",{"run_id":123,"sha":"abc"})
            self.assertEqual(c["metric_status"],"MEASURED")
            self.assertEqual(c["gpui_replay_p95_us"],40)
            self.assertTrue(c["gpui_render_verified"])
            data["live_jsi_to_gpui"]=True
            (base/"svelte-metrics.json").write_text(json.dumps(data))
            self.assertEqual(m.cell(Path(directory),"linux","svelte",{"run_id":123})["metric_status"],"NOT_MEASURED")
    def test_ios_g1_is_not_gpui_latency(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)/"ios"
            base.mkdir()
            record={"schema":"gpui-mobile-g1/v1","platform":"ios","framework":"solid",
                    "stage":"RENDER_PASS","status":"PASS","elapsed_ms":3321}
            (base/"solid-g1.json").write_text(json.dumps(record))
            c=m.cell(Path(directory),"ios","solid",{"run_id":321,"sha":"xyz"})
            self.assertEqual(c["g1_screenshot_readiness_ms"],3321)
            self.assertIsNone(c["gpui_replay_p50_us"])
            self.assertFalse(c["live_jsi_to_gpui"])

if __name__=="__main__":
    unittest.main()
