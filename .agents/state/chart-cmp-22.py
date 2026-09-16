# -*- coding: utf-8 -*-
"""序号 22 趋势图区（设计内联 SVG ↔ 实现 data-URI）像素等价对账。

设计侧 = 13 个内联 SVG 图形叶子（4 网格线 + 1 折线 + 1 面积 + 6 点 r4 + 1 末点 r5）
实现侧 = uni-image 的 SVG data-URI（同族画法）

本脚本对同一 y 区间逐行统计：
  · 网格线行（横跨 x 30..400 的 #F1F5F9 / #E2E8F0 行）
  · 蓝墨迹行（折线/数据点）与每行的 x 区间
两图并排打印，供逐行判「是否等价」。

用法: python .agents/state/chart-cmp-22.py <design.png> <impl.png> [y0 y1]
"""
import os
import sys
from importlib import import_module

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
png = import_module('png-cardmap')


def near(px, rgb, tol=6):
    return all(abs(a - b) <= tol for a, b in zip(px, rgb))


def blue(px):
    r, g, b = px
    return b > 150 and b - r > 60 and b - g > 40


def colprofile(path, y0, y1, x0=20, x1=410):
    """逐列蓝像素数 → 数据点（核 ≥7 行）与折线（细）区分；返回点和网格线的 x 范围。"""
    w, h, rows = png.read_png(path)
    cols = []
    for x in range(x0, min(x1, w)):
        n = sum(1 for y in range(y0, min(y1, h)) if blue((rows[y][x * 4], rows[y][x * 4 + 1], rows[y][x * 4 + 2])))
        cols.append((x, n))
    runs = []
    cur = None
    for x, n in cols:
        if n >= 7:
            if cur is None:
                cur = [x, x]
            else:
                cur[1] = x
        else:
            if cur is not None:
                runs.append(tuple(cur))
                cur = None
    if cur:
        runs.append(tuple(cur))
    dots = [((a + b) / 2.0, b - a + 1) for a, b in runs]
    grid = []
    for y in range(y0, min(y1, h)):
        xs = [x for x in range(x0, min(x1, w))
              if near((rows[y][x * 4], rows[y][x * 4 + 1], rows[y][x * 4 + 2]), (241, 245, 249), 4)
              or near((rows[y][x * 4], rows[y][x * 4 + 1], rows[y][x * 4 + 2]), (226, 232, 240), 4)]
        if len(xs) > 150:
            grid.append((y, xs[0], xs[-1], len(xs)))
    return dots, grid


def main():
    design, impl = sys.argv[1], sys.argv[2]
    y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 395
    y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 560
    for label, path in (('DESIGN', design), ('IMPL', impl)):
        dots, grid = colprofile(path, y0, y1)
        print('=== %s %s' % (label, os.path.basename(path)))
        print('  数据点列（中心 x, 核宽）: %s' % ', '.join('%.1f/%d' % d for d in dots))
        print('  网格线行（y, x 起, x 止, 命中列数）: %s' % ', '.join('%d(%d..%d,%d)' % g for g in grid))


main()
