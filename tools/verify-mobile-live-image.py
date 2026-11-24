#!/usr/bin/env python3
"""Verify a real iOS Simulator / Android ARM64 emulator GPUI screenshot."""
from pathlib import Path
from PIL import Image, ImageStat
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("image", type=Path)
parser.add_argument("--minimum-hits", type=int, default=600)
args = parser.parse_args()
image = Image.open(args.image).convert("RGB")
width, height = image.size
if width < 800 or height < 600:
    raise SystemExit(f"mobile GPUI screenshot unexpectedly small: {width}x{height}")
if max(ImageStat.Stat(image).stddev) < 8:
    raise SystemExit("mobile GPUI screenshot appears blank")
target = (241, 245, 251)
hits = 0
for y in range(25, height - 25, 8):
    for x in range(25, width - 25, 8):
        pixel = image.getpixel((x, y))
        if max(abs(a - b) for a, b in zip(pixel, target)) <= 8:
            hits += 1
if hits < args.minimum_hits:
    raise SystemExit(f"no large GPUI content area: background sample hits={hits}")
print(f"GPUI_MOBILE_LIVE_HERMES_PIXELS_PASS:{args.image.name}:{width}x{height}:background_hits={hits}")
