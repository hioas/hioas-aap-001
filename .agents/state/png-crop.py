"""PNG 裁剪（纯标准库）：python png-crop.py <in> <out> x0,y0,x1,y1"""
import sys, zlib, struct


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not png"
    pos, w, h, bitd, ctype, idat = 8, None, None, None, None, b""
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
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    assert bitd == 8
    stride = w * ch
    out = bytearray(w * h * ch)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
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


def write_png(path, w, h, ch, px):
    ctype = {1: 0, 3: 2, 4: 6}[ch]
    raw = bytearray()
    stride = w * ch
    for y in range(h):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    def chunk(typ, payload):
        return struct.pack(">I", len(payload)) + typ + payload + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


src, dst, box = sys.argv[1], sys.argv[2], sys.argv[3]
x0, y0, x1, y1 = (int(v) for v in box.split(","))
w, h, ch, px = read_png(src)
x1 = min(x1, w); y1 = min(y1, h)
nw, nh = x1 - x0, y1 - y0
out = bytearray(nw * nh * ch)
for y in range(nh):
    out[y * nw * ch:(y + 1) * nw * ch] = px[((y0 + y) * w + x0) * ch:((y0 + y) * w + x1) * ch]
write_png(dst, nw, nh, ch, bytes(out))
print("cropped %s [%d,%d,%d,%d] -> %s (%dx%d)" % (src.split("/")[-1], x0, y0, x1, y1, dst.split("/")[-1], nw, nh))
