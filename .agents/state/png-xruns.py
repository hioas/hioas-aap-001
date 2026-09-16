# -*- coding: utf-8 -*-
"""某一行里「非主色」像素的 x 区间（判断文字行覆盖宽度 / 行数）。

用法: python .agents/state/png-xruns.py <png> <y> <x0> <x1> [gap]
"""
import struct
import sys
import zlib
from collections import Counter


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
y = int(sys.argv[2])
x0, x1 = int(sys.argv[3]), int(sys.argv[4])
gap = int(sys.argv[5]) if len(sys.argv) > 5 else 12
w, h, ch, px = read_png(path)
row = []
for x in range(x0, min(x1, w)):
    o = (y * w + x) * ch
    row.append((x, (px[o], px[o + 1], px[o + 2])))
modal = Counter(c for _x, c in row).most_common(1)[0][0]
ink = [x for x, c in row if c != modal]
print("y=%d  modal=#%02X%02X%02X  ink px=%d" % (y, modal[0], modal[1], modal[2], len(ink)))
if not ink:
    raise SystemExit
runs = []
a = b = ink[0]
for x in ink[1:]:
    if x - b <= gap:
        b = x
    else:
        runs.append((a, b))
        a = b = x
runs.append((a, b))
for a, b in runs:
    print("   x %d..%d  w=%d" % (a, b, b - a + 1))
