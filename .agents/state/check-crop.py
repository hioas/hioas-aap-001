#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""客观检查截图是否真的"右侧被裁切"：看最右若干列有没有内容像素。

用法：python .agents/state/check-crop.py <png> [右边界列数]
判据：若最右侧 N 列的内容像素数 ≈ 0，说明右侧没有被裁切（内容没顶到边缘）。
"""
import sys

try:
    from PIL import Image
except ImportError:
    print("PIL 不可用：pip install pillow")
    raise SystemExit(2)


def main():
    path = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    # 背景色取左上角像素
    bg = px[0, 0]

    def is_bg(c):
        return all(abs(c[i] - bg[i]) <= 6 for i in range(3))

    print(f"图片尺寸: {w}x{h}  背景色: {bg}  检测最右 {n} 列")
    for x in range(w - n, w):
        cnt = sum(0 if is_bg(px[x, y]) else 1 for y in range(h))
        print(f"  x={x}: 非背景像素 {cnt}")

    right_ct = sum(0 if is_bg(px[x, y]) else 1 for x in range(w - n, w) for y in range(h))
    total = sum(0 if is_bg(px[x, y]) else 1 for x in range(w) for y in range(h))
    print(f"最右 {n} 列内容像素合计 {right_ct} / 全图内容像素 {total}")
    print("结论:", "未顶到右边缘（无裁切迹象）" if right_ct < total * 0.002 else "右边缘有内容（可能被裁切或满宽元素）")


if __name__ == "__main__":
    main()
