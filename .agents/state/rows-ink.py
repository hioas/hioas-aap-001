# -*- coding: utf-8 -*-
"""在给定横向区间内，逐行判断是否存在「与背景色不同」的像素（墨迹行），并打印连续区间。
用于从设计截图上定死每一行文本/盒子的 y 区间。

用法: python .agents/state/rows-ink.py <png> <x0> <x1> <y0> <y1> [bghex=#ffffff] [tol=24]
"""
import sys
import zlib
import struct


def read_png(path):
    data = open(path, 'rb').read()
    pos = 8
    w = h = ctype = None
    idat = b''
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, _bitd, ctype = struct.unpack('>IIBB', chunk[:10])
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'IEND':
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
x0, x1, y0, y1 = (int(sys.argv[i]) for i in range(2, 6))
bg = (sys.argv[6] if len(sys.argv) > 6 else '#ffffff').lstrip('#')
tol = int(sys.argv[7]) if len(sys.argv) > 7 else 24
br, bgc, bb = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)

w, h, ch, px = read_png(path)
print('PNG %dx%d band x[%d,%d) y[%d,%d) bg=#%s tol=%d' % (w, h, x0, x1, y0, y1, bg, tol))

runs = []
start = None
for y in range(y0, min(y1, h)):
    ink = False
    for x in range(x0, min(x1, w)):
        o = (y * w + x) * ch
        if (abs(px[o] - br) > tol or abs(px[o + 1] - bgc) > tol or abs(px[o + 2] - bb) > tol):
            ink = True
            break
    if ink and start is None:
        start = y
    elif not ink and start is not None:
        runs.append((start, y - 1))
        start = None
if start is not None:
    runs.append((start, h - 1))
for a, b in runs:
    print('  ink %d..%d  h=%d' % (a, b, b - a + 1))
