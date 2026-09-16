# -*- coding: utf-8 -*-
"""序号 5（page-5-2「检测进行中」）文本叶子行盒证据：设计 PNG vs 实现截图 同窗口逐项对账。

用法: python .agents/state/tl-5-evidence.py <design.png> <impl.png> [out.txt]

每一行的度量都与某一「待判读 class」或「盒算术链」对应（见输出里的 note 列）。
"""
import io
import sys

from PIL import Image

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
RES = []


def load(p):
    return Image.open(p).convert('RGB')


def close(a, b, tol=8):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) <= tol


def color_rows(im, x, y0, y1, want, tol=8, minlen=3):
    """返回「某列上接近指定颜色」的连续行段 [(a,b,len), ...]"""
    px = im.load()
    W, H = im.size
    y1 = min(y1, H)
    segs = []
    run = None
    for y in range(y0, y1):
        if close(px[x, y], want, tol):
            if run is None:
                run = [y, y]
            else:
                run[1] = y
        else:
            if run and run[1] - run[0] + 1 >= minlen:
                segs.append((run[0], run[1], run[1] - run[0] + 1))
            run = None
    if run and run[1] - run[0] + 1 >= minlen:
        segs.append((run[0], run[1], run[1] - run[0] + 1))
    return segs


def ink_bands(im, x0, y0, x1, y1, minink=3, gap=1, tol=24):
    """按「行内与**该窗口主色**不同的像素数」切墨迹带（不受阴影/底色染色影响）。"""
    px = im.load()
    W, H = im.size
    x1, y1 = min(x1, W), min(y1, H)
    hist = {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            p = px[x, y]
            hist[p] = hist.get(p, 0) + 1
    modal = max(hist.items(), key=lambda kv: kv[1])[0]
    rows = []
    for y in range(y0, y1):
        cnt = 0
        for x in range(x0, x1):
            p = px[x, y]
            if abs(p[0] - modal[0]) + abs(p[1] - modal[1]) + abs(p[2] - modal[2]) > tol:
                cnt += 1
        rows.append((y, cnt))
    bands = []
    for y, c in rows:
        if c >= minink:
            if bands and y - bands[-1][1] <= gap:
                bands[-1][1] = y
                bands[-1][2] = max(bands[-1][2], c)
            else:
                bands.append([y, y, c])
    return modal, [(a, b, b - a + 1, m) for a, b, m in bands]


def IB(im, *a, **k):
    """只取墨迹带（丢掉主色）。"""
    return ink_bands(im, *a, **k)[1]


def add(name, note, d, i):
    RES.append((name, note, str(d), str(i), 'SAME' if str(d) == str(i) else 'diff'))


def measure(p):
    im = load(p)
    out = {}
    # 卡1 上下界（x=25，避开圆角取内列；r18 → 白起比卡顶低约 2.4 行）
    out['card1_white_x25'] = color_rows(im, 25, 90, 320, (254, 254, 254), tol=4, minlen=5)
    # 进度条蓝带（x=60 在填充内）
    out['bar_blue_x60'] = color_rows(im, 60, 150, 200, (37, 99, 235), tol=8, minlen=3)
    # 成本块 #ECFDF5（x=60）
    out['cost_x60'] = color_rows(im, 60, 205, 300, (236, 253, 245), tol=8, minlen=3)
    # 标题行两段文字墨迹
    out['title_ink'] = IB(im, 30, 120, 100, 160)
    out['percent_ink'] = IB(im, 320, 120, 380, 160)
    # 元信息行墨迹
    out['meta_ink'] = IB(im, 36, 186, 300, 216)
    # 提示卡：卡盒（x=25 白带）+ 文案两行墨迹（x 64..400）
    out['tip_white_x25'] = color_rows(im, 25, 750, 848, (255, 255, 255), tol=4, minlen=5)
    out['tip_text_ink'] = IB(im, 64, 770, 400, 825, minink=20)
    # 顶部状态胶囊：盒（x=410 近右圆角）+ 文案墨迹
    out['topchip_x410'] = color_rows(im, 410, 40, 90, (239, 246, 255), tol=8, minlen=3)
    out['topchip_label_ink'] = IB(im, 374, 52, 404, 80, minink=2)
    # D1 行状态胶囊：盒（x=380）+ 文案墨迹
    out['d1chip_x380'] = color_rows(im, 380, 370, 410, (236, 253, 245), tol=8, minlen=2)
    out['d1chip_label_ink'] = IB(im, 366, 378, 392, 404, minink=2)
    # 底部操作条：按钮带（x=140）+ 文案墨迹
    out['bar_btn_x140'] = color_rows(im, 140, 850, 934, (241, 245, 249), tol=8, minlen=5)
    out['bar_label_ink'] = IB(im, 100, 862, 360, 910)
    return out


def main():
    dp, ip = sys.argv[1], sys.argv[2]
    D, I = measure(dp), measure(ip)
    keys = [
        ('card1_white_x25', '卡1 白带（x=25，内含 20+T+16+10+12+M+16+58+20=196）'),
        ('bar_blue_x60', '进度条蓝带（= 卡顶+20+T+16；T=标题行高）'),
        ('cost_x60', '成本块 #ECFDF5（= 卡顶+20+T+16+10+12+M+16；M=元信息行高）'),
        ('title_ink', '“总进度” fs15 墨迹（class card__title）'),
        ('percent_ink', '“58%” fs20 墨迹（class card__percent）'),
        ('meta_ink', '元信息行墨迹 fs12（class meta__done/meta__eta）'),
        ('tip_white_x25', '提示卡白带（16+content+16=72）'),
        ('tip_text_ink', '提示卡文案两行墨迹 fs12（class tip__text，行距=行盒）'),
        ('topchip_x410', '顶部状态胶囊盒（h24，x=410 近右圆角）'),
        ('topchip_label_ink', '“进行中” fs11 墨迹（class chip__text）'),
        ('d1chip_x380', 'D1 行状态胶囊盒（h22，class probe-chip__text 所在行）'),
        ('d1chip_label_ink', '“完成” fs11 墨迹（class probe-chip__text）'),
        ('bar_btn_x140', '底栏按钮带（h48，底栏 12+48+24=84）'),
        ('bar_label_ink', '“查看历史检测报告” fs14 墨迹（class history-bar__text）'),
    ]
    lines = []
    lines.append('序号 5 page-5-2 文本叶子行盒证据 · 设计 PNG vs 实现截图')
    lines.append('design=%s' % dp)
    lines.append('impl  =%s' % ip)
    lines.append('')
    for k, note in keys:
        d, i = D.get(k), I.get(k)
        same = 'SAME' if d == i else 'diff'
        lines.append('[%s] %s' % (same, k))
        lines.append('  note: %s' % note)
        lines.append('  design: %s' % d)
        lines.append('  impl  : %s' % i)
        if k.endswith('_ink') and d and i:
            dc = (d[0][0] + d[-1][1]) / 2.0
            ic = (i[0][0] + i[-1][1]) / 2.0
            lines.append('  ink 中心: design=%.1f impl=%.1f 差=%.1f' % (dc, ic, ic - dc))
        lines.append('')
    txt = '\n'.join(lines)
    print(txt)
    if len(sys.argv) > 3:
        io.open(sys.argv[3], 'w', encoding='utf-8').write(txt + '\n')


if __name__ == '__main__':
    main()
