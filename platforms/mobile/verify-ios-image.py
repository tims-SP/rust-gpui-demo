#!/usr/bin/env python3
"""Verify screenshot is the *Hermes Home scene*, not the upstream GPUI Kit demo.

Pixel inspection is intentionally scene-specific. A screenshot of a launched
app, splash screen, or unrelated GPUI Kit TextView MUST fail acceptance.
"""
import sys
from pathlib import Path
from PIL import Image, ImageStat

path=Path(sys.argv[1])
im=Image.open(path).convert("RGB")
w,h=im.size
if w<650 or h<750: raise SystemExit(f"iOS screenshot too small: {w}x{h}")
# This same light-blue GPUI background is hardcoded into our Hermes Home
# scene on Linux/Web/Android/iOS: 0xf1f5fb.
color=(241,245,251)
num=0
samples=0
for y in range(int(h*.10),int(h*.84),7):
    for x in range(int(w*.06),int(w*.94),7):
        p=im.getpixel((x,y))
        samples+=1
        if max(abs(a-b) for a,b in zip(p,color))<=5:
            num+=1
coverage=num/samples
if coverage<0.15:
    raise SystemExit(f"Wrong root screen / not Hermes Home: light-blue coverage={coverage:.3%}")
# Require multiple dark text rows inside the GPUI Home body (not top status).
bands=0
for y in range(int(h*.12),int(h*.82),16):
    x1=int(w*.02);x2=int(w*.32)
    patch=im.crop((x1,y,x2,min(y+16,h)))
    dark=sum(1 for p in patch.getdata() if max(p)<160)
    if dark>30:
        bands+=1
if bands<9:
    raise SystemExit(f"Target scene content missing: foreground bands={bands}")
print(f"GPUI_IOS_HERMES_SCENE_PIXELS_PASS:{path.name}:{w}x{h}:coverage={coverage:.3%}:bands={bands}")
