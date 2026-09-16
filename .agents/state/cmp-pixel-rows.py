"""临时：对两张 PNG 的若干行，打印同一列区间的颜色（判「未命中」是页面缺陷还是阴影/AA 类）。"""
import sys

from PIL import Image

a = Image.open(sys.argv[1]).convert('RGB').load()
b = Image.open(sys.argv[2]).convert('RGB').load()
rows = [int(v) for v in sys.argv[3].split(',')]
x = int(sys.argv[4]) if len(sys.argv) > 4 else 200
for y in rows:
    print('y=%d  design=%s  impl=%s' % (y, a[x, y], b[x, y]))
