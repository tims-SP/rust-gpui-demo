#!/usr/bin/env python3
"""Verify the GPUI Web canvas contains actual rows, not just a static HTML badge.

Uniform light themes have low full-image standard deviation, so a global
standard-deviation threshold cannot distinguish blank from valid UI.
The expected Hermes scene contains 48 dark GPUI-rendered track labels on the
left. A screenshot containing only the HTML badge at top-right must fail.
"""
from pathlib import Path
from PIL import Image
import sys

file = Path(sys.argv[1])
im = Image.open(file).convert("RGB")
width, height = im.size
if width < 850 or height < 650:
    raise SystemExit("Browser viewport is unexpectedly small")

# The same fixed light palette is used by the GPUI Rust view on both frameworks.
background = im.getpixel((width // 2, height // 2))
expected = (241, 245, 251)
if max(abs(actual - reference) for actual, reference in zip(background, expected)) > 16:
    raise SystemExit(f"GPUI canvas expected background absent: {background}")

# GPUI draws >= 48 densely spaced row labels near the left edge. Require
# significant dark strokes across many distinct vertical bands below the
# header; a blank canvas or the unrelated top-right DOM badge cannot pass.
bands = []
for y in range(120, min(height - 35, 860), 16):
    count = sum(
        max(im.getpixel((x, yy))) < 135
        for yy in range(y, min(y + 16, height))
        for x in range(20, 175)
    )
    if count >= 20:
        bands.append(y)

if len(bands) < 30:
    raise SystemExit(
        f"Not enough GPUI list text rows in screenshot: {len(bands)} dark bands"
    )

print(
    f"GPUI_WEB_CANVAS_TEXT_ROWS_VERIFIED:{file.name} "
    f"{width}x{height} bands={len(bands)} background={background}"
)
