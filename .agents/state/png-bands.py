# -*- coding: utf-8 -*-
"""从设计/实现截图里量色带：沿一列（v）或一行（h）打印「同色连续段」，用于确定卡片边界、间距、行高。

用法：
    python .agents/state/png-bands.py <png> v <x> [from] [to]
    python .agents/state/png-bands.py <png> h <y> [from] [to]
"""
import sys

sys.path.insert(0, ".agents/state")
from importlib import util as _u  # noqa: E402

spec = _u.spec_from_file_location("pngink", ".agents/state/png-ink.py")

# png-ink.py 顶部为主程序，这里直接复制其 read_png 逻辑，避免执行副作用
import struct  # noqa: E402
import zlib  # noqa: E402


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not png"
    pos = 8
    w = h = bitd = ctype = None
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitd, ctype = struct.unpack(">IIBB", chunk[:10])
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


path = sys.argv[1]
mode = sys.argv[2]
idx = int(sys.argv[3])
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
end = int(sys.argv[5]) if len(sys.argv) > 5 else 10 ** 9

w, h, ch, px = read_png(path)
print("PNG %dx%d" % (w, h))

items = []
if mode == "v":
    end = min(end, h)
    for y in range(start, end):
        o = (y * w + idx) * ch
        items.append((y, hexof(px, o)))
else:
    end = min(end, w)
    for x in range(start, end):
        o = (idx * w + x) * ch
        items.append((x, hexof(px, o)))

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
    if b - a + 1 < 2:
        continue
    print("%s %d..%d  len=%d  %s" % (mode, a, b, b - a + 1, col))
