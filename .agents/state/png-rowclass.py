"""png-rowclass.py — 逐行判定「卡片行 / 间隙行」，不受卡片投影染色影响。

用法: python .agents/state/png-rowclass.py <png> [--x0 16] [--x1 414] [--white FFFFFF] [--minfrac 0.7]

原理：设计导出图上卡片之间的 12px 间隙会被两张卡的 drop_shadow 染色，
所以「等于页面底色」的判据不可靠（见 prototype-reconstruction 的坑）。
改为按行统计「x0..x1 区间内等于卡片底色（默认 #FFFFFF）的像素占比」：
  >= minfrac → 卡片行（CARD）
  <  minfrac → 间隙行（GAP）
再把连续同类行合成区段打印，得到卡片上下边界（含投影外沿）。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_png = import_module('png-cardmap')
read_png = _png.read_png


def hexc(px):
    return '%02X%02X%02X' % (px[0], px[1], px[2])


def main():
    args = sys.argv[1:]
    png = args[0]
    def opt(name, default):
        return args[args.index(name) + 1] if name in args else default
    x0 = int(opt('--x0', 16))
    x1 = int(opt('--x1', 414))
    want = opt('--white', 'FFFFFF').upper()
    minfrac = float(opt('--minfrac', 0.7))

    w, h, rows = read_png(png)
    ch = 3 if len(rows[0]) == w * 3 else 4
    print('PNG %dx%d x=[%d,%d) white=#%s minfrac=%.2f' % (w, h, x0, x1, want, minfrac))
    flags = []
    fracs = []
    for y in range(h):
        row = rows[y]
        n = 0
        tot = 0
        for x in range(max(0, x0), min(w, x1)):
            px = row[x * ch:x * ch + 3]
            tot += 1
            if hexc(px) == want:
                n += 1
        f = (n / tot) if tot else 0
        fracs.append(f)
        flags.append('CARD' if f >= minfrac else 'GAP')

    start = 0
    for y in range(1, h + 1):
        if y == h or flags[y] != flags[start]:
            seg = flags[start]
            fr = fracs[start:y]
            print('%s %4d..%4d  len=%4d  whiteFrac %.2f..%.2f' % (seg, start, y - 1, y - start, min(fr), max(fr)))
            start = y


if __name__ == '__main__':
    main()
