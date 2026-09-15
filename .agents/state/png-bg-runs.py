"""沿某一列扫描「页面底色」色带（= 卡片之间的间距 / 页边距），用于把设计截图反推成盒子边界。

用法: python .agents/state/png-bg-runs.py <png> <x> [hexcolor] [minLen]
默认底色 #F5F7FB（page-9 页面容器色），minLen=2。
"""
import sys
import zlib
import struct

path = sys.argv[1]
x = int(sys.argv[2])
target = (sys.argv[3] if len(sys.argv) > 3 else "#f5f7fb").lstrip("#").lower()
min_len = int(sys.argv[4]) if len(sys.argv) > 4 else 2

data = open(path, "rb").read()
pos = 8
w = h = None
idat = b""
while pos < len(data):
    ln = struct.unpack(">I", data[pos : pos + 4])[0]
    typ = data[pos + 4 : pos + 8]
    body = data[pos + 8 : pos + 8 + ln]
    if typ == b"IHDR":
        w, h, depth, color = struct.unpack(">IIBB", body[:10])
    elif typ == b"IDAT":
        idat += body
    elif typ == b"IEND":
        break
    pos += 12 + ln

raw = zlib.decompress(idat)
ch = 4 if color == 6 else 3
stride = w * ch
rows = []
prev = bytearray(stride)
i = 0
for y in range(h):
    ft = raw[i]
    i += 1
    line = bytearray(raw[i : i + stride])
    i += stride
    if ft == 1:
        for j in range(ch, stride):
            line[j] = (line[j] + line[j - ch]) & 0xFF
    elif ft == 2:
        for j in range(stride):
            line[j] = (line[j] + prev[j]) & 0xFF
    elif ft == 3:
        for j in range(stride):
            a = line[j - ch] if j >= ch else 0
            line[j] = (line[j] + ((a + prev[j]) >> 1)) & 0xFF
    elif ft == 4:
        for j in range(stride):
            a = line[j - ch] if j >= ch else 0
            b = prev[j]
            c = prev[j - ch] if j >= ch else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            line[j] = (line[j] + pr) & 0xFF
    rows.append(line)
    prev = line

print("PNG %dx%d x=%d target=#%s" % (w, h, x, target))
runs = []
start = None
for y in range(h):
    px = rows[y][x * ch : x * ch + 3]
    ok = "#%02x%02x%02x" % (px[0], px[1], px[2]) == "#" + target
    if ok and start is None:
        start = y
    elif not ok and start is not None:
        runs.append((start, y - 1))
        start = None
if start is not None:
    runs.append((start, h - 1))
for a, b in runs:
    if b - a + 1 >= min_len:
        print("  bg %d..%d len=%d" % (a, b, b - a + 1))
