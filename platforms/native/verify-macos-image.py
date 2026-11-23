#!/usr/bin/env python3
"""Verify an actual macOS screenshot contains GPUI's imported light scene.

This is a pixel and real-window acceptance gate, not proof of live JS mutation.
"""
from pathlib import Path
from PIL import Image, ImageStat
import sys

p=Path(sys.argv[1])
im=Image.open(p).convert("RGB")
w,h=im.size
if w<800 or h<600:
    raise SystemExit(f"macOS display unexpectedly small: {w}x{h}")
std=ImageStat.Stat(im).stddev
if max(std)<8:
    raise SystemExit(f"Mac desktop appears blank: {std}")
# Sample the imported GPUI scene's known light-blue background, which should
# occupy a substantial fraction of the app window (not simply a mac wallpaper).
target=(241,245,251)
hits=0
for y in range(25,h-25,8):
    for x in range(25,w-25,8):
        color=im.getpixel((x,y))
        if max(abs(a-b) for a,b in zip(color,target)) <= 4:
            hits+=1
if hits<800:
    raise SystemExit(f"No large GPUI-colored content area: matching grid cells={hits}")
print(f"GPUI_MACOS_REAL_WINDOW_PIXELS_PASS:{p.name}:{w}x{h}:background_hits={hits}")
