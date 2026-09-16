"""序号 5 像素对账（±1 容差版）：设计 PNG vs 实现 430 宽截图。

用法: python .agents/state/cmp-bands-5-design-vs-impl.py <设计PNG> <实现PNG> [out.txt]
规则:
  · 只比「粗色带边界」= 长度 ≥ 2 的色带起点（1 行带是 AA/渐变噪声）
  · 设计边界在实现里 ±1 行内找到同值 → 计为命中；否则列为差异，人工判读
"""
import sys
import zlib
import struct
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def read_png(path):
    data = Path(path).read_bytes()
    assert data[:8] == PNG_SIG, "not a png: " + path
    pos, idat, w, h, bitdepth, colortype = 8, b"", 0, 0, 0, 0
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, bitdepth, colortype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colortype]
    raw = zlib.decompress(idat)
    stride = w * channels
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, channels, out


def coarse_bounds(img, x):
    w, h, ch, buf = img
    stride = w * ch
    bands = []
    for y in range(h):
        o = y * stride + x * ch
        px = tuple(buf[o:o + 3])
        if not bands or bands[-1][2] != px:
            bands.append([y, y, px])
        else:
            bands[-1][1] = y
    return [b[0] for b in bands if (b[1] - b[0]) >= 2 or b[0] == 0]


def ink_rows(img, x0, x1, y0, y1):
    w, h, ch, buf = img
    stride = w * ch
    rows = []
    for y in range(y0, min(y1, h)):
        # 行主色
        counts = {}
        for x in range(x0, min(x1, w)):
            o = y * stride + x * ch
            px = tuple(buf[o:o + 3])
            counts[px] = counts.get(px, 0) + 1
        modal = max(counts.items(), key=lambda kv: kv[1])[0]
        ink = sum(v for k, v in counts.items() if k != modal)
        rows.append((y, ink))
    return rows


def rows_with_ink(rows, min_ink=1):
    return [y for y, n in rows if n >= min_ink]


def main():
    design = read_png(sys.argv[1])
    impl = read_png(sys.argv[2])
    out = []
    out.append("序号 5 像素对账：设计 PNG %dx%d vs 实现 430 宽截图 %dx%d" % (design[0], design[1], impl[0], impl[1]))
    out.append("（实现截图由 bash .agents/state/shot-430.sh <out.png> __measure-detecting.html \"?shot=1\" 拍到，iframe 960 高、页面 934 = 设计帧高）")
    out.append("")
    total_miss = 0
    for x in (8, 25, 62, 215, 404):
        db = coarse_bounds(design, x)
        ib = coarse_bounds(impl, x)
        hits, miss = [], []
        for v in db:
            (hits if any(abs(v - u) <= 1 for u in ib) else miss).append(v)
        total_miss += len(miss)
        out.append("--- x=%d ---" % x)
        out.append("  设计粗边界 %d 个: %s" % (len(db), db))
        out.append("  实现粗边界 %d 个: %s" % (len(ib), ib))
        out.append("  命中(±1) %d / 缺失 %d → %s" % (len(hits), len(miss), miss))
    out.append("")
    out.append("=== 提示卡文案两行 ink（x 60..400） ===")
    d_rows = rows_with_ink(ink_rows(design, 60, 400, 770, 830), 5)
    i_rows = rows_with_ink(ink_rows(impl, 60, 400, 770, 830), 5)
    out.append("  设计 ink 行: %s" % d_rows)
    out.append("  实现 ink 行: %s" % i_rows)
    out.append("")
    out.append("=== 底部按钮文案 ink（x 150..300） ===")
    d_rows2 = rows_with_ink(ink_rows(design, 150, 300, 860, 912), 5)
    i_rows2 = rows_with_ink(ink_rows(impl, 150, 300, 860, 912), 5)
    out.append("  设计 ink 行: %s" % d_rows2)
    out.append("  实现 ink 行: %s" % i_rows2)
    out.append("")
    out.append("结构边界缺失合计（±1 容差外）: %d" % total_miss)
    text = "\n".join(out) + "\n"
    print(text)
    if len(sys.argv) > 3:
        Path(sys.argv[3]).write_text(text, encoding="utf-8")
        print("-> " + sys.argv[3])


if __name__ == "__main__":
    main()
