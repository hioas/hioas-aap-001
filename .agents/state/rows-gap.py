"""按行找卡片间隙：比较 x=probe（卡内）与 x=ref（页边距，恒为页面底色）的距离，输出接近的行段。

用法: python .agents/state/rows-gap.py <png> <probeX> <refX> [tol] [from] [to]
"""
import sys, zlib, struct

path = sys.argv[1]
probe = int(sys.argv[2])
ref = int(sys.argv[3])
tol = int(sys.argv[4]) if len(sys.argv) > 4 else 8
y0 = int(sys.argv[5]) if len(sys.argv) > 5 else 0
y1 = int(sys.argv[6]) if len(sys.argv) > 6 else 10 ** 9

data = open(path, "rb").read()
pos = 8
w = h = None
idat = b""
while pos < len(data):
    ln = struct.unpack(">I", data[pos:pos + 4])[0]
    typ = data[pos + 4:pos + 8]
    if typ == b"IHDR":
        w, h, bd, ct = struct.unpack(">IIBB", data[pos + 8:pos + 18])
    elif typ == b"IDAT":
        idat += data[pos + 8:pos + 8 + ln]
    elif typ == b"IEND":
        break
    pos += 12 + ln
raw = zlib.decompress(idat)
ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
stride = w * ch
prev = bytearray(stride)
rows = []
p = 0
for y in range(h):
    f = raw[p]
    p += 1
    line = bytearray(raw[p:p + stride])
    p += stride
    bpp = ch
    for i in range(stride):
        a = line[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        if f == 1:
            line[i] = (line[i] + a) & 255
        elif f == 2:
            line[i] = (line[i] + b) & 255
        elif f == 3:
            line[i] = (line[i] + ((a + b) >> 1)) & 255
        elif f == 4:
            pa = abs(b - c)
            pb = abs(a - c)
            pc = abs(a + b - 2 * c)
            pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            line[i] = (line[i] + pr) & 255
    prev = line
    rows.append(bytes(line))

def px(y, x):
    o = x * ch
    return (rows[y][o], rows[y][o + 1], rows[y][o + 2])

runs = []
cur = None
for y in range(max(0, y0), min(h, y1)):
    a = px(y, probe)
    b = px(y, ref)
    d = max(abs(a[i] - b[i]) for i in range(3))
    ok = d <= tol
    if ok:
        cur = [y, y] if cur is None else [cur[0], y]
    else:
        if cur:
            runs.append(cur)
            cur = None
if cur:
    runs.append(cur)

print(f"PNG {w}x{h} probe={probe} ref={ref} tol={tol}  # 近似同色段（≈卡间隙/页面底色）")
for a, b in runs:
    c = px(a, probe)
    print(f"  gap {a}..{b} len={b - a + 1} #{c[0]:02X}{c[1]:02X}{c[2]:02X}")
