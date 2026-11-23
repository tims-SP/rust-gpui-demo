from PIL import Image, ImageStat
from pathlib import Path
import sys
file=Path(sys.argv[1]); image=Image.open(file).convert("RGB")
if image.width<1000 or image.height<800: raise SystemExit("Unexpected screenshot size")
std=ImageStat.Stat(image).stddev
if max(std)<8: raise SystemExit(f"Blank or uniform screen: {std}")
colors=image.resize((144,100)).getcolors(maxcolors=14400)
if colors is None or len(colors)<16:
    raise SystemExit(f"Insufficient visual diversity: {None if colors is None else len(colors)}")
print(f"GPUI_SCREENSHOT_PIXELS_OK:{file.name} {image.width}x{image.height}")
