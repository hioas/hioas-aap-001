# -*- coding: utf-8 -*-
"""序号 23 设计 PNG 量尺：卡片投影（账号信息卡 effects）· 文本墨迹色 · 结构带。

用法: python .agents/state/probe-23-png.py
"""
from collections import Counter

from PIL import Image

png = '.agents/state/design-shots/page-23-2.png'
im = Image.open(png).convert('RGB')
px = im.load()
W, H = im.size
print('image', W, 'x', H)

print('\n--- 竖直色扫描 x=215（卡1 底 331 → 卡2 顶 343；卡2 底 519 → 卡3 顶 531）---')
for y in list(range(325, 350)) + list(range(512, 536)):
    print('  y=%3d  %s' % (y, px[215, y]))

print('\n--- 卡1 下方 12px 间隙最暗值 vs 卡2 下方间隙 ---')
g1 = [px[x, y] for y in range(332, 343) for x in range(60, 380)]
g2 = [px[x, y] for y in range(520, 531) for x in range(60, 380)]
print('  卡1 下方间隙 min 亮度', min(sum(c) for c in g1) // 3, ' 最常见', Counter(g1).most_common(2))
print('  卡2 下方间隙 min 亮度', min(sum(c) for c in g2) // 3, ' 最常见', Counter(g2).most_common(2))

print('\n--- 文本墨迹主色（取该行内最暗的前 3 个颜色）---')


def ink_color(y0, y1, x0=20, x1=410):
    cnt = Counter()
    for y in range(y0, y1 + 1):
        for x in range(x0, x1):
            c = px[x, y]
            if sum(c) < 3 * 200:
                cnt[c] += 1
    return cnt.most_common(4)


for name, y0, y1 in [
    ('nav 标题', 58, 73),
    ('卡1 标题 账号信息', 134, 148),
    ('手机号行 标签+值', 180, 191),
    ('微信行', 235, 246),
    ('登录安全行', 290, 301),
    ('卡2 标题 通知设置', 369, 384),
    ('短信通知行', 409, 436),
    ('订阅消息行', 468, 495),
    ('入口1 实名与主体信息', 559, 574),
    ('入口2 服务协议与隐私政策', 617, 631),
    ('入口3 退出登录', 674, 688),
    ('底部说明 v1.4.2', 744, 753),
]:
    print('  %-22s' % name, ink_color(y0, y1))

print('\n--- 胶囊（已绑定 / 已授权）水平墨迹与底色 ---')
cnt = Counter()
for y in range(232, 250):
    for x in range(100, 220):
        cnt[px[x, y]] += 1
print('  微信已绑标区域最常见色', cnt.most_common(3))


def runs(y, x0, x1, test, name):
    out = []
    start = None
    for x in range(x0, x1):
        c = px[x, y]
        if test(c):
            if start is None:
                start = x
        else:
            if start is not None:
                out.append((start, x - 1))
                start = None
    if start is not None:
        out.append((start, x1 - 1))
    print('  %-28s y=%d runs=%s' % (name, y, out))


print('\n--- 水平墨迹 runs（非白/非卡底）---')
# 行墨迹：与行内众数色不同的像素
for y in (240, 295, 185):
    row = [px[x, y] for x in range(20, 410)]
    modal = Counter(row).most_common(1)[0][0]
    runs(y, 20, 410, lambda c, m=modal: max(abs(c[i] - m[i]) for i in range(3)) > 12, 'account y=%d' % y)
for y in (560, 618, 675):
    row = [px[x, y] for x in range(20, 410)]
    modal = Counter(row).most_common(1)[0][0]
    runs(y, 20, 410, lambda c, m=modal: max(abs(c[i] - m[i]) for i in range(3)) > 12, 'entry y=%d' % y)
for y in (420, 479):
    row = [px[x, y] for x in range(20, 410)]
    modal = Counter(row).most_common(1)[0][0]
    runs(y, 20, 410, lambda c, m=modal: max(abs(c[i] - m[i]) for i in range(3)) > 12, 'notify y=%d' % y)
