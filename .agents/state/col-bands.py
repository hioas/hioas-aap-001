#!/usr/bin/env python
"""按列把设计截图逐像素分类成色带：W=白卡 B=页面底色 S=卡片描边 X=其他(文字/元素)。
用法: col-bands.py <png> <x> [from] [to]"""
import sys
from PIL import Image

png, x = sys.argv[1], int(sys.argv[2])
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else None
im = Image.open(png).convert("RGB")
w, h = im.size
y1 = y1 if y1 is not None else h
print(f"PNG {w}x{h} col x={x} range {y0}..{y1}")


def cls(p):
    r, g, b = p
    if r >= 250 and g >= 250 and b >= 250:
        return "W"
    if abs(r - 248) <= 3 and abs(g - 250) <= 3 and abs(b - 252) <= 3:
        return "B"
    if abs(r - 238) <= 6 and abs(g - 242) <= 6 and abs(b - 247) <= 6:
        return "S"
    return "X"


runs = []
for y in range(y0, y1):
    c = cls(im.getpixel((x, y)))
    if runs and runs[-1][0] == c:
        runs[-1][2] = y
    else:
        runs.append([c, y, y])
for c, a, b in runs:
    print(f"  {c} {a}..{b} len={b - a + 1}")
