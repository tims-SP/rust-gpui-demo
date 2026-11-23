"""Replay real CI screenshots to reject false greens and false negatives.

Positive: rendered GPUI scene, CI 45280068480 (was incorrectly rejected by
strict source-only palette). Negative: dead GLES Surface, CI 45272317446.
"""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


class AndroidGlesScreenshotVerifierTest(unittest.TestCase):
    def verify(self, filename):
        return subprocess.run(
            [sys.executable, str(ROOT / "verify-android-image.py"),
             str(FIXTURES / filename)],
            capture_output=True, text=True, check=False, timeout=20,
        )

    def test_real_hermes_svelte_scene_is_accepted(self):
        result = self.verify("android-svelte-gles-rendered.png")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GPUI_ANDROID_HERMES_SCENE_PIXELS_PASS", result.stdout)
        self.assertIn("bands=", result.stdout)

    def test_real_failed_surface_screen_is_rejected(self):
        result = self.verify("android-gles-no-surface.png")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("background coverage", result.stderr)


if __name__ == "__main__":
    unittest.main()
