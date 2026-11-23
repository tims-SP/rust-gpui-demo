#!/usr/bin/env python3
"""Conservative screenshot smoke: reject blank/launchers and record real pixels."""
from pathlib import Path
from PIL import Image, ImageStat
import sys
path=Path(sys.argv[1])
im=Image.open(path).convert("RGB")
if im.width<500 or im.height<900: raise SystemExit("Android screenshot dimensions invalid")
std=ImageStat.Stat(im).stddev
if max(std)<10: raise SystemExit(f"Android screenshot blank: {std}")
# Header + many rows should create independent nonuniform horizontal bands.
# Avoid accepting a monochrome splash screen or launcher as the GPUI scene.
sample_width=min(420,im.width-40)
bands=[]
for y in range(100,min(im.height-120,950),18):
    crop=im.crop((20,y,20+sample_width,y+18))
    var=max(ImageStat.Stat(crop).stddev)
    if var>12: bands.append(y)
if len(bands)<12:
    raise SystemExit(f"Android scene has too few foreground bands: {len(bands)}")
print(f"ANDROID_GPUI_SCENE_SCREENSHOT_PIXEL_CHECK:{path.name}:{im.width}x{im.height}:bands={len(bands)}")
