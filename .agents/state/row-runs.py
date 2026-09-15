# -*- coding: utf-8 -*-
"""按行输出紧凑的颜色游程（RLE），用于横向定位元素/查越界。
用法: row-runs.py <png> <y> [x0] [x1] [minLen]
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
        pos += 12 + ln
    raw = zlib.decompress(idat)
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * ch
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    for _y in range(h):
        ft = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        if ft == 1:
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 255
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif ft == 4:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out += line
        prev = line
    return w, h, ch, bytes(out)


def rgb_at(px, w, ch, x, y):
    o = (y * w + x) * ch
    return px[o], px[o + 1], px[o + 2]


png = sys.argv[1]
y = int(sys.argv[2])
x0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
x1 = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
minlen = int(sys.argv[5]) if len(sys.argv) > 5 else 3
w, h, ch, px = read_png(png)
name = png.replace('\\', '/').split('/')[-1]
print('PNG %s %dx%d  row y=%d  x=%d..%d  minLen=%d' % (name, w, h, y, x0, min(x1, w), minlen))
runs = []
for x in range(x0, min(x1, w)):
    c = rgb_at(px, w, ch, x, y)
    if runs and runs[-1][2] == c:
        runs[-1][1] = x
    else:
        runs.append([x, x, c])
for a, b, c in runs:
    if b - a + 1 >= minlen:
        print('  x %3d..%3d  len=%3d  rgb%s' % (a, b, b - a + 1, c))
