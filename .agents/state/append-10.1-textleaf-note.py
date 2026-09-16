# -*- coding: utf-8 -*-
"""回写台账 `aap-feature-status.csv` 序号 10.1 行的 备注 列（追加一段）。
用法: python .agents/state/append-10.1-textleaf-note.py [--dry]
"""
import csv
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-feature-status.csv')
SEQ = '10.1'
NOTE = (
    '队列 8 · 文本叶子维度（2026-09-16 20:15 轮 · cron `aap-tdd-run-20260916-2015`）：'
    '`textleaf-scan.py 10.1`（mock api-10-1-2 · leafs 45 · docH 1414）→ `textleaf-audit.py 10.1` 红基线 '
    '**待判读 class 9**（evidence/red-序号10.1-textleaf-待判读.txt）→ 逐条判读 → 复跑 **待判读 0 · 已核定 8**'
    '（green-序号10.1-textleaf-待判读0.txt）；其中 **2 处真偏差先红后绿**：'
    '①`.intro-box__text`：design 234362e0 **显式 height=40 是块高（2 行）**、行盒按设计渲染实测 fs12×lh1.2 = 14.4 '
    '→ line-height 20→**14.4px** + 块高 40 + 盒内居中（红 2/275 → 绿 0/275）；'
    '②`.gate__text`：闸门提示 87815f1d padding12 的 **#FFFBEB 填充盒两侧同为 60 = 12+36+12 ⇒ 块高 36**（图标行框 27 不承重，'
    '图标墨迹中心两侧同为 211.5）→ line-height 18→**14.4px** + 块高 36 + 盒内居中（红 2/277 → 绿 0/277）。'
    '设计 PNG 墨迹对账（evidence/cmp-序号10.1-文本叶子-逐类带.txt）：简介 917..929/932..943 → 实现 918..930/933..943（±1）、'
    '闸门 202..214/217..228 → 203..214/218..228（±1）；两处盒高两侧不变（简介 899..962=64 · 闸门 186..245=60）· '
    '**docScrollHeight 1414 = 设计帧高** · 两轮独立测量 43/43 字段全等 · requests 两轮集合逐字节相同（24 行 = 1 写 + 11 对只读 GET）。'
    '其余 8 类判为**非偏差**并登记 `.agents/state/textleaf-accept.json`（+9 键，累计 73）= 定高胶囊/定高按钮内单行文本不承重'
    '（胶囊 h24/h22、角标 h20、按钮 h44，墨迹 ±1 或逐值相同）+ 单行 note（墨迹 636..648 两侧逐值相同）。'
    '判法新增「**多行文本模型**」：设计里 fs12 文本的块高 = n × 18（自然 CJK 行框，或显式声明），而字形行按 lh1.2 = 14.4 排布并在块内垂直居中'
    '（n=1 与 n=2 两个实测同解）→ 写进状态文件 §5.25。'
    '质量门：npm test **1185/1185 · 72 files 连跑两轮** · type-check exit 0 · build:mp-weixin DONE（wxss 含 '
    '`line-height:14.4px`×2 / `height:36px` / `height:40px`）· build:h5 DONE · review-artifacts 22/22 · '
    '设计帧重抓（design.json sha256 e7983634… **逐字节相同**，无漂移）。'
    '证据：evidence/{red,green}-序号10.1-textleaf-*.txt · .agents/state/evidence/review-序号10.1-{tlred,tlred2,tlg,tlg2}-run{1,2}.json · '
    'requests-序号10.1-tlg2-run{1,2}.txt · cmp-序号10.1-文本叶子-逐类带.txt · review-序号10.1-textleaf-报告.md · '
    '截图 logs/screenshots/20260916-2035-序10.1-文本叶子维度收口-h5-430宽.png（430×1414）。'
)

raw = io.open(P, encoding='utf-8', newline='').read()
rows = list(csv.reader(io.StringIO(raw)))
head = rows[0]
n = len(head)
hit = 0
for r in rows[1:]:
    if r and r[0].strip() == SEQ:
        while len(r) < n:
            r.append('')
        r[10] = (r[10] + ' ｜ ' + NOTE) if r[10].strip() else NOTE
        hit += 1
if hit != 1:
    raise SystemExit('序号 %s 命中 %d 行（要求恰好 1）→ 不写盘' % (SEQ, hit))
out = io.StringIO()
csv.writer(out, lineterminator='\r\n').writerows(rows)
print('命中 1 行 · 备注列 +%d 字' % len(NOTE))
if '--dry' not in sys.argv:
    io.open(P, 'w', encoding='utf-8', newline='').write(out.getvalue())
    print('已写盘 %s' % P)
