#!/usr/bin/env python3
"""G1 protocol tests; no emulator required."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("g1_probe", BASE/"g1_probe.py")
g1=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g1)
PNG=b"\x89PNG\r\n\x1a\n"+b"x"*6000

class G1ProbeTest(unittest.TestCase):
    def test_android_pass_requires_pixel_verifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap=subprocess.CompletedProcess(["adb"],0,stdout=PNG,stderr=b"")
            passed=subprocess.CompletedProcess(["python"],0,stdout="GPUI_ANDROID_HERMES_SCENE_PIXELS_PASS",stderr="")
            with patch.object(g1.subprocess,"run",side_effect=[cap,passed]) as run:
                result=g1.run_probe("android","svelte",Path(tmp),None,0,1)
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["stage"],"RENDER_PASS")
            self.assertFalse(result["actual_hermes_vm_on_device"])
            self.assertFalse(result["live_jsi_to_gpui"])
            self.assertEqual(run.call_count,2)
            self.assertEqual(json.loads((Path(tmp)/"svelte-g1.json").read_text())["phase"],"G1")
            self.assertTrue((Path(tmp)/"svelte.png").exists())

    def test_wrong_screen_is_failure_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap=subprocess.CompletedProcess(["adb"],0,stdout=PNG,stderr=b"")
            wrong=subprocess.CompletedProcess(["python"],1,stdout="",stderr="Wrong root screen")
            with patch.object(g1.subprocess,"run",side_effect=[cap,wrong]):
                result=g1.run_probe("android","solid",Path(tmp),None,0,1)
            self.assertEqual(result["status"],"FAIL")
            self.assertEqual(result["stage"],"RENDER_TIMEOUT")
            self.assertIn("Wrong root screen",result["error"])
            self.assertTrue((Path(tmp)/"solid.png").exists())
            self.assertEqual(json.loads((Path(tmp)/"solid-g1.json").read_text())["status"],"FAIL")

    def test_capture_failure_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap=subprocess.CompletedProcess(["adb"],1,stdout=b"",stderr=b"device offline")
            with patch.object(g1.subprocess,"run",return_value=cap) as run:
                result=g1.run_probe("android","solid",Path(tmp),None,0,1)
            self.assertEqual(result["status"],"FAIL")
            self.assertIn("device offline",result["error"])
            run.assert_called_once()

    def test_ios_targets_specific_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            image=Path(tmp)/"solid.png"
            self.assertEqual(g1.capture_command("ios",image,"fake-device"),
                             ["xcrun","simctl","io","fake-device","screenshot",str(image)])
            with self.assertRaises(ValueError):
                g1.capture_command("ios",image,None)

    def test_png_signature_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            cap=subprocess.CompletedProcess(["adb"],0,stdout=b"invalid"*2000,stderr=b"")
            with patch.object(g1.subprocess,"run",return_value=cap) as run:
                result=g1.run_probe("android","svelte",Path(tmp),None,0,1)
            self.assertEqual(result["status"],"FAIL")
            self.assertIn("invalid PNG",result["error"])
            run.assert_called_once()

if __name__=="__main__":
    unittest.main()
