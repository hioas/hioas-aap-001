# -*- coding: utf-8 -*-
"""台账序号 6 回写（文本叶子维度收口）。走文件避免 shell 引号转义。

规则（§5.16）：追加进带引号字段的文本里不能出现 ASCII 双引号。
"""
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')
SEP = ' ｜ '

CASE = (
    '文本叶子维度收口 2026-09-16 19:3x（cron 轮 aap-tdd-run-20260916-1915）：载体页 228→243 条设计期望值 checks；'
    '红基线 16/243（源码 stash 复现 + 同版探针两轮 JSON 逐字节相同）→ 绿 0/243 · docH 5341（设计 5342）· 两轮 25/25 字段全等；'
    '修 7 组声明值偏差（导出 PDF 字重 500 · 发现标题 600 · 维度名 500 · 维度分 700 · 状态标签 pill 600 · G 组值 pill fs11/400 · '
    '明细说明行盒 24→16）+ 2 处结构偏差（分组之间补 1px 分隔线×6 = design 分隔线A–F · 明细说明 frame 的 24 被当成行盒 → 整卡 +8px）；'
    '设计 PNG 逐类对账：14 类文本叶子 ink 带与实现逐条相同 → textleaf-accept.json 登记 19 条；'
    '新增单测 3 条（红 3 failed/53 → 绿 1185/1185·72 files 连跑两轮）· type-check exit 0 · build:mp-weixin 产物含 group__sep/item__pill--value'
    '（wxss 含 font-size:11px / font-weight:600 / line-height:16px）· 交互相 ?scenario=actions 两轮 requests 各 4 行逐字节相同'
    '（GET /reports/DR-1/export 200 + toast + hash 不变；填写报价 → #/pages/quote-models/index）；'
    '证据 evidence/review-序号6-textleaf-报告.md · red-序号6-tl-checks-设计期望值偏差.txt · green-序号6-tl-checks-设计期望值.txt · '
    'cmp-序号6-设计PNGvs实现截图-行盒判读-修后.txt · cmp-序号6-明细卡纵向对账-修后.txt · textleaf-audit-20260916-1935-6.txt；'
    '截图 logs/screenshots/20260916-1935-序06-检测报告-文本叶子维度收口-h5-430宽.png'
)

NOTE = (
    '文本叶子审计 2026-09-16 19:3x：27 条待判读 class 全部收口（7 组声明值偏差 + 2 处结构偏差已改代码；18 组经设计 PNG 实测登记为非偏差）；'
    '审计复跑 待判读 class 0 · 已核定 23。口径留痕：设计 明细说明 frame 8485b93b 的 h=24 是 padding-top 8 + 行盒 16，'
    '不可把 frame 高度当行盒（同类错误会让整卡下移 8px）；分组之间除 spacer 16 还有 1px 分隔线（实现原先只有 margin 16，每组少 1px）。'
)

rows = list(csv.reader(io.open(P, encoding='utf-8', newline='')))
hit = 0
for r in rows:
    if len(r) >= 11 and r[0] == '6':
        r[8] = r[8] + SEP + CASE
        r[10] = r[10] + SEP + NOTE
        hit += 1
if hit != 1:
    print('序号 6 行命中 %d 次（必须 1 次）—— 未写盘' % hit)
    sys.exit(2)
if '"' in CASE or '"' in NOTE:
    print('追加文本含 ASCII 双引号 —— 未写盘')
    sys.exit(3)

buf = io.StringIO()
w = csv.writer(buf, lineterminator='\n')
w.writerows(rows)
text = buf.getvalue()
# 复解析校验后才落盘（normalize-ledger-eol.py 的教训：中途报错会留半截文件）
back = list(csv.reader(io.StringIO(text)))
assert len(back) == len(rows) and all(len(a) == len(b) for a, b in zip(back, rows)), '复解析不一致'
io.open(P, 'w', encoding='utf-8', newline='').write(text)
print('已写盘（%d 行 · 复解析校验通过）' % len(rows))
