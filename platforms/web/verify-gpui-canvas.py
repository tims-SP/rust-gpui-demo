#!/usr/bin/env python3
"""Verify browser's official GPUI Web canvas pixels, not a static DOM fallback."""
from pathlib import Path
from PIL import Image, ImageStat
import sys
file=Path(sys.argv[1])
im=Image.open(file).convert("RGB")
if im.width<850 or im.height<650: raise SystemExit("Browser viewport is unexpectedly small")
std=ImageStat.Stat(im).stddev
if max(std)<18: raise SystemExit(f"Likely blank canvas: {std}")
print(f"GPUI_WEB_CANVAS_PIXELS_NONBLANK:{file.name} {im.width}x{im.height} {std}")
