# -*- coding: utf-8 -*-
"""序号 5 文本叶子维度收口：回写台账「用例(证据)」与「备注」两列。

规则（§5.16）：台账 CSV 里该行两列都是**带引号**字段 → 追加文本中不得出现 ASCII 双引号。
写法：csv.DictReader 读入 → 改字段 → csv.DictWriter 重写；先在内存生成完整文本并复解析体检，通过后才落盘。

用法: python .agents/state/append-5-textleaf-note.py [--dry]
"""
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')

CASE = (' ｜ 文本叶子维度（2026-09-16 21:2x）：textleaf-scan 5（mock api · 带参路由 '
        '/pages/detecting/index?jobId=j1 · leafs 35 · docH 934）→ 红基线 待判读 class 8（'
        'evidence/red-序号5-textleaf-待判读.txt）→ 逐条判读后**全部非偏差**并登记 textleaf-accept.json'
        '（page-5-2 +8 键）→ 复跑 **待判读 0 · 已核定 8**（green-序号5-textleaf-待判读0.txt）；'
        '载体页 __measure-detecting.html 新增 3 条行盒断言（chip.textLineHeight · rowChip.lineHeight · '
        'history.textLineHeight）237 → **240 条**并以**源码变异**证明有牙齿（三条同时改成声明模型值 → '
        '3 条红 → git checkout 还原 → 0/240 ×2，red-序号5-tlchecks-变异测试.txt）；'
        '回归门：两轮独立测量 phase1/phase2 **32/32 字段全等**（review-序号5-tlfinal-run{1,2}.json）· '
        'serve 实收 10 行/轮（5 对轮询 GET · **零写请求**）排序集合逐字节相同 · docH 934 = 设计帧高 · '
        '溢出 0 · 430 宽整页截图与 10:42 轮 checks 轮**逐字节相同**（sha256 0eecb24e…）· '
        'npm test 1185/1185 ×2 · type-check exit 0 · review-artifacts 22/22 · 无源码改动')

NOTE = (' ｜ 文本叶子维度判读（2026-09-16 21:2x · 全部非偏差 · 无源码改动）：本帧给出了**同帧同字号的显式 '
        'height**（判据①）—— fs15 ea3a0a0d h=22 · fs13 D1..D8 标题 ×8 h=18 · fs12 ff72fdea h=18 · '
        'fs11 副行 ×9 h=16 —— 据此 card__title(22) · meta__done/meta__eta(18) · chip__text(16) · '
        'probe-chip__text(16) 直接定为实现取值；card__percent(26) 由**盒算术**定（卡1 = '
        '20 + 标题行 26 + 16 + 进度条 10 + 12 + 元信息行 18 + 16 + 成本块 58 + 20 = 196，'
        '设计 PNG 与实现截图在 x=60 的进度条蓝带同为 170..179、x=60 的成本块起点同为 226、'
        'x=25 的卡1 白带同为 110..301）；tip__text(16) 由设计 PNG 的两行墨迹**行距 16**'
        '（设计 785..795/800..810 = 实现 785..795/801..811）定，并按声明模型 14.4 会得行距 14.4 而冲突；'
        'history-bar__text(20) 为定高 48 按钮内**不承重**项，两侧墨迹中心同为 886.5。'
        '逐类盒/带明细见 evidence/cmp-序号5-文本叶子行盒-逐类带.txt（脚本 .agents/state/tl-5-evidence.py，'
        '设计 PNG = design-shots/page-5-2.png 430×934 sha256 b64ef9e8…，与重抓帧新导出图逐字节相同）。')


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding='utf-8')))
    fields = list(rows[0].keys())
    hit = 0
    for r in rows:
        if r.get('序号') == '5':
            r['用例(证据)'] = (r.get('用例(证据)') or '') + CASE
            r['备注'] = (r.get('备注') or '') + NOTE
            hit += 1
    print('命中行数 %d' % hit)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    text = buf.getvalue()
    back = list(csv.DictReader(io.StringIO(text)))
    assert len(back) == len(rows), '复解析行数不一致 %d != %d' % (len(back), len(rows))
    for b in back:
        assert len(b) == len(fields)
    print('复解析体检通过：%d 行 × %d 字段' % (len(back), len(fields)))
    if '--dry' not in sys.argv:
        io.open(CSV, 'w', encoding='utf-8', newline='').write(text)
        print('已写盘 %s' % CSV)


main()
