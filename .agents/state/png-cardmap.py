#!/usr/bin/env python
"""Structural map of a design PNG: where the page background (default #F8FAFC) stops and starts.

Usage:
  python .agents/state/png-cardmap.py <png> [--x 20] [--from 0] [--to 99999] [--bg F8FAFC] [--minrun 3]

Prints one line per run: `<y0>..<y1> len=N [BG|CARD|color]`. BG = the page background colour
(so a BG run between two CARD runs is the inter-card gap = block padding 12). Everything that is
not BG is reported with its first row's colour, which is enough to locate card tops/bottoms and
sub-boxes (sub-cards #F8FAFC inside a white card read as "other" -> labelled SUB).
"""

import argparse
import zlib
import struct


def read_png(path):
    data = open(path, 'rb').read()
    pos = 8
    width = height = None
    idat = b''
    channels = 4
    while pos < len(data):
        (ln,) = struct.unpack('>I', data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if ctype == b'IHDR':
            width, height, depth, color = struct.unpack('>IIBB', chunk[:10])
            if depth != 8 or color not in (2, 6):
                raise SystemExit('only 8-bit RGB/RGBA supported (got depth=%s color=%s)' % (depth, color))
            channels = 3 if color == 2 else 4
        elif ctype == b'IDAT':
            idat += chunk
        elif ctype == b'IEND':
            break
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = width * channels
    rows = []
    prev = bytearray(stride)
    p = 0
    for _ in range(height):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        if channels == 3:
            # 统一成 RGBA（alpha=255），调用方一律按 4 字节/像素取址；
            # prev 必须保留「未转换的 RGB 行」，否则下一行的 Up/Paeth 反滤波会用错参考行
            raw_line = line
            rgba = bytearray(width * 4)
            for x in range(width):
                rgba[x * 4:x * 4 + 3] = line[x * 3:x * 3 + 3]
                rgba[x * 4 + 3] = 255
            line = rgba
            rows.append(line)
            prev = raw_line
            continue
        rows.append(line)
        prev = line
    return width, height, rows


def hexof(px):
    return '#%02X%02X%02X' % (px[0], px[1], px[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('png')
    ap.add_argument('--x', type=int, default=20)
    ap.add_argument('--from', dest='frm', type=int, default=0)
    ap.add_argument('--to', type=int, default=10 ** 9)
    ap.add_argument('--bg', default='F8FAFC')
    ap.add_argument('--minrun', type=int, default=2)
    args = ap.parse_args()
    bg = tuple(int(args.bg[i:i + 2], 16) for i in (0, 2, 4))
    w, h, rows = read_png(args.png)
    print('PNG %dx%d x=%d bg=#%s' % (w, h, args.x, args.bg))
    y = args.frm
    end = min(args.to, h)
    while y < end:
        px = rows[y][args.x * 4:args.x * 4 + 3]
        isbg = tuple(px) == bg
        y2 = y
        while y2 + 1 < end:
            nxt = rows[y2 + 1][args.x * 4:args.x * 4 + 3]
            if (tuple(nxt) == bg) != isbg:
                break
            y2 += 1
        if y2 - y + 1 >= args.minrun:
            tag = 'BG' if isbg else hexof(px)
            print('%5d..%-5d len=%-5d %s' % (y, y2, y2 - y + 1, tag))
        y = y2 + 1


if __name__ == '__main__':
    main()
