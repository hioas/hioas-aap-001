import sys, zlib, struct


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
    assert bitd == 8, "bit depth %s unsupported" % bitd
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


def ink_runs(w, h, ch, px, x0, x1, y0, y1, thresh=200):
    """返回 [x0..x1) x [y0..y1) 区域内「有墨迹」的列区间（列上存在非白像素则记为墨迹）"""
    cols = []
    for x in range(x0, min(x1, w)):
        ink = False
        for y in range(y0, min(y1, h)):
            o = (y * w + x) * ch
            r, g, b = px[o], px[o + 1], px[o + 2]
            if r < thresh or g < thresh or b < thresh:
                ink = True
                break
        cols.append(ink)
    runs = []
    start = None
    for i, v in enumerate(cols):
        if v and start is None:
            start = x0 + i
        elif not v and start is not None:
            runs.append((start, x0 + i - 1))
            start = None
    if start is not None:
        runs.append((start, x1 - 1))
    return runs


path = sys.argv[1]
w, h, ch, px = read_png(path)
print("PNG %s -> %dx%d ch=%d" % (path.split("/")[-1], w, h, ch))


def ink_rows(x0, x1, y0, y1, thresh=245):
    rows = []
    for y in range(y0, min(y1, h)):
        ink = False
        for x in range(x0, min(x1, w)):
            o = (y * w + x) * ch
            if px[o] < thresh or px[o + 1] < thresh or px[o + 2] < thresh:
                ink = True
                break
        rows.append((y, ink))
    runs = []
    start = None
    for y, v in rows:
        if v and start is None:
            start = y
        elif not v and start is not None:
            runs.append((start, y - 1))
            start = None
    if start is not None:
        runs.append((start, y))
    return runs


for spec in sys.argv[2:]:
    if spec.startswith("v:"):
        name, box = spec[2:].split("=")
        x0, y0, x1, y1 = (int(v) for v in box.split(","))
        print("%-16s 纵向墨迹 y 区间 x=[%d,%d) -> %s" % (name, x0, x1, ink_rows(x0, x1, y0, y1, 245)))
        continue
    name, box = spec.split("=")
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    runs = ink_runs(w, h, ch, px, x0, x1, y0, y1)
    # 右侧最远的墨迹像素
    maxx = max((r[1] for r in runs), default=None)
    print("%-16s y=[%d,%d) x=[%d,%d) -> runs=%s  maxInkX=%s  右留白=%s" % (
        name, y0, y1, x0, x1, runs, maxx, (w - 1 - maxx) if maxx else None))
