# -*- coding: utf-8 -*-
"""区块行剖面：在给定矩形内，逐行统计「与整块主色不同的像素数」，用于判定文字行数/图标墨迹范围。

用法: python .agents/state/png-profile.py <png> <x0> <y0> <x1> <y1> [minInk]
输出: 每行 ink 数（>0 才打印），末尾给出「连续 ink 行段」= 文字行/图标的分带。
"""
import struct
import sys
import zlib


def read_png(path):
    data = open(path, "rb").read()
    pos = 8
    w = h = ctype = None
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, _b, ctype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * ch
    out = bytearray(w * h * ch)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if f == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, ch, bytes(out)


path = sys.argv[1]
x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6])
min_ink = int(sys.argv[6]) if len(sys.argv) > 6 else 1
w, h, ch, px = read_png(path)
print("PNG %dx%d  box x %d..%d y %d..%d" % (w, h, x0, x1, y0, y1))

from collections import Counter

for y in range(y0, min(y1, h)):
    row = Counter()
    for x in range(x0, min(x1, w)):
        o = (y * w + x) * ch
        row[(px[o], px[o + 1], px[o + 2])] += 1
    modal, mcount = row.most_common(1)[0]
    ink = sum(c for col, c in row.items() if col != modal)
    if ink >= min_ink:
        print("  y=%4d ink=%3d  modal=#%02X%02X%02X  width=%d" % (y, ink, modal[0], modal[1], modal[2], x1 - x0))
