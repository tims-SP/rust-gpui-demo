#!/usr/bin/env python3
"""Android acceptance: require actual Hermes/GPUI Home palette + text.

Screenshots of the emulator launcher, system-ANR dialog, splash screen or
unrelated GPUI Kit demo must FAIL even if Android screenshot is nonblank.
"""
from pathlib import Path
from PIL import Image
import sys

p=Path(sys.argv[1])
im=Image.open(p).convert("RGB")
w,h=im.size
if w<500 or h<800:
    raise SystemExit(f"Android screenshot size is invalid: {w}x{h}")
expected=(241,245,251)
hits=total=0
for y in range(int(h*.10),int(h*.85),7):
    for x in range(int(w*.06),int(w*.94),7):
        color=im.getpixel((x,y))
        total+=1
        if max(abs(a-b) for a,b in zip(expected,color))<=5:
            hits+=1
ratio=hits/total
if ratio<0.15:
    raise SystemExit(f"Android is showing non-Hermes GPUI scene: background coverage={ratio:.2%}")
bands=0
for y in range(int(h*.12),int(h*.82),16):
    patch=im.crop((int(w*.02),y,int(w*.32),min(h,y+16)))
    dark=sum(1 for color in patch.getdata() if max(color)<160)
    if dark>30:
        bands+=1
if bands<9:
    raise SystemExit(f"Android Hermes scene rows not visible: {bands} text bands")
print(f"GPUI_ANDROID_HERMES_SCENE_PIXELS_PASS:{p.name}:{w}x{h}:coverage={ratio:.2%}:bands={bands}")
