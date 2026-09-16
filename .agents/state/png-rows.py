# -*- coding: utf-8 -*-
"""同 png-bands.py，但可打印长度 1 的色带（默认全打印）——用于确定 1px 描边/子像素边界。

用法: python .agents/state/png-rows.py <png> v|h <idx> <from> <to> [minLen]
"""
import struct
import sys
import zlib


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not png"
    pos = 8
    w = h = ctype = None
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, _bitd, ctype = struct.unpack(">IIBB", chunk[:10])
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


def hexof(px, o):
    return "#%02X%02X%02X" % (px[o], px[o + 1], px[o + 2])


path, mode, idx = sys.argv[1], sys.argv[2], int(sys.argv[3])
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
end = int(sys.argv[5]) if len(sys.argv) > 5 else 10 ** 9
minlen = int(sys.argv[6]) if len(sys.argv) > 6 else 1

w, h, ch, px = read_png(path)
print("PNG %dx%d" % (w, h))
items = []
if mode == "v":
    for y in range(start, min(end, h)):
        items.append((y, hexof(px, (y * w + idx) * ch)))
else:
    for x in range(start, min(end, w)):
        items.append((x, hexof(px, (idx * w + x) * ch)))

runs = []
cur = None
for pos, col in items:
    if cur and cur[2] == col:
        cur[1] = pos
    else:
        if cur:
            runs.append(cur)
        cur = [pos, pos, col]
if cur:
    runs.append(cur)

for a, b, col in runs:
    if b - a + 1 >= minlen:
        print("%s %d..%d  len=%d  %s" % (mode, a, b, b - a + 1, col))
