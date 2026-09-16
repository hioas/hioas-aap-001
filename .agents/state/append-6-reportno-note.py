#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""台账回写：序号 6「报告编号」前缀口径核定 + 行框偏差修复；序号 7 跨页断言⑩ 更正。

用法: python .agents/state/append-6-reportno-note.py
      然后 python .agents/state/validate-ledger-csv.py .agents/state/aap-feature-status.csv
      再   python .agents/state/normalize-ledger-eol.py

⚠️ 写 CSV 的两条硬规则（2026-09-16 踩到，曾把 22 行写成 6 行）：
   ①追加进**带引号**字段（本文件的「用例(证据)」列）的文本里**不能出现 ASCII 双引号** ——
     它会提前闭合字段，把后续内容拆成新列/并掉后续行；用 `·` `=` 或全角引号代替。
   ②追加进**不带引号**字段（序号 7 的「备注」列历史写入未加引号）的文本里**不能出现 ASCII 逗号**。
"""
import csv
import io
from pathlib import Path

P = Path('.agents/state/aap-feature-status.csv')
text = io.open(P, encoding='utf-8', newline='').read()

CASE6 = (
    '｜ 报告编号前缀口径核定 + 顶部栏行框偏差修复（2026-09-16 17:5x · cron 轮 aap-tdd-run-20260916-1745）：'
    '__measure-report.html 新增 7 条顶部栏 checks（228 条：topbar.no.text / prefixAbsent / h / top / right / lineHeight / fw）· '
    '红基线（修复前源码 + 同一份最终版探针两轮）**1/228**（`topbar.no.lineHeight: got normal want 16`，'
    '`evidence/red-序号6-reportno-checks.txt`）→ 绿 **0/228**（`evidence/green-序号6-reportno-checks.txt`）；'
    '两轮独立测量 25/25 字段全等（不一致 0）· docH 5343 = 设计帧高 · 溢出 0 · 文案缺失 0 · '
    '实现 DOM 实测 topbarNo = {text=DR-20240613-0758 · x319 w95 right414 h16 top57 lineHeight 16 fw400}。'
    '修复：`.report-page__no` 补 `line-height:16px`（design 5d860a4b「报告编号」frame 显式 h=16 · 叶子 height=fill_container '
    '→ 行框取显式 height 16，不是 lineHeight 1.2×11=13.2；设计 PNG 墨迹 y60..69 中心 64.5 = 内容行 48..81 的中心，'
    '正是「16 高盒在 33 高行里居中」的必然结果）。'
    '像素对账（`evidence/cmp-序号6-reportno-设计PNGvs实现截图-顶部栏.txt`）：右区设计 x318..412 w95 y60..69 vs 实现 x320..413 w94 y61..70 '
    '（±2 横向 / +1 纵向 = 设计小数坐标 56.5 取整 + H5 回退字体墨迹，非页面缺陷）。'
    '口径锁（新增 1 条单测，1182/1182 ×2）：`报告编号不带「报告编号」前缀（按设计稿原文直出）` —— '
    '变异测试（临时把前缀写回模板）**2 failed** 证明该锁有牙齿（`evidence/red-序号6-前缀口径锁-变异测试.txt`）。'
    '质量门：npm test 1182/1182 · 72 files 连跑两轮 · type-check exit 0 · build:mp-weixin DONE'
    '（wxss 含 line-height:16px）· build:h5 DONE · review-artifacts 22/22 · '
    '设计帧重抓 sha256 08ad8ea5… 逐字节相同（无漂移）。'
)

NOTE6 = (
    '⑫**报告编号前缀核定（2026-09-16 17:5x）**：序号 7 台账备注⑩ 曾跨页断言「序号 6 顶部同样缺『报告编号』前缀（设计原文含前缀）'
    '→ 序号 6 待回炉时一并修」→ 经**两条独立证据**核定为**误判**，本页**保持无前缀**（不改实现口径）：'
    '①设计树「顶部导航 → 报告编号(5d860a4b) → 图层(202cd360)」content = `DR-20240613-0758`（w=97 · fs11）；'
    '②设计 PNG 顶部栏右侧墨迹 x318..412 **w=95** = 15 字符；对照序号 7-2 同位置墨迹 **w=142** = 21 字符（含前缀）。'
    '两帧同 fs11 同字体 → 单字符推进宽相同，95 与 142 之差恰是「有无前缀」之差。'
    '误判来源：page-6 design.json 里确实出现过「报告编号」字样 —— 那是**图层名**（frame 5d860a4b），不是文本内容。'
    '现已加口径锁（单测 + 载体页 `topbar.no.prefixAbsent` 断言），禁止后续再把前缀补到本页。'
    '证据：`evidence/序号6-报告编号前缀核定.txt`。'
)

NOTE7 = (
    '⑩**更正（2026-09-16 17:5x · cron 轮 aap-tdd-run-20260916-1745）**：本条原写「序号 6 顶部同样只渲染了号码、缺『报告编号』前缀'
    '（设计原文含前缀）→ 序号 6 待回炉时一并修」——经核定**序号 6 设计稿本就无前缀**（设计树叶子 202cd360 content = '
    '`DR-20240613-0758` + 设计 PNG 墨迹宽 95=15 字符），**该跨页结论作废**，序号 6 不得改（已在序号 6 行备注⑫ 与本条留痕）。'
    '本页（序号 7）设计原文 57f828cc = 单个文本图层 `报告编号 DR-20240614-0312`（含前缀 · w=143）→ 实现保留前缀，'
    '并补 `line-height:13.2px`（h=fit_content · lineHeight 1.2 → 行框 13.2；本帧**没有** 16 高盒子 · 与序号 6 的 frame h=16 不同）：'
    '载体页 __measure-report-failed.html 红基线 **2/201**（lineHeight normal→13.2 · h 16→13.2）→ 绿 **0/201** · '
    '两轮独立测量 31/31 全等 · 新增 5 条 topbar.no checks（text/prefixPresent/lineHeight/h/right）· '
    '实测 .rf-page__no = {text=报告编号 DR-20240614-0312 · x272 w142 right414 h13 lineHeight 13.2}。'
)


def append(row_id: str, col: str, extra: str):
    global text
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        if ln.startswith(row_id + ','):
            idx = i
            break
    else:
        raise SystemExit('row not found: %s' % row_id)
    ln = lines[idx]
    if col == 'case':
        # 用例(证据) 列本身带引号：边界形如 `..."<case>",部分,"<note>"` → 插入必须在收尾引号**之内**
        for marker in ['",部分,', '",已验证,', '",阻塞,']:
            if marker in ln:
                lines[idx] = ln.replace(marker, extra + marker, 1)
                break
        else:
            raise SystemExit('case column boundary not found in row %s' % row_id)
    else:
        # 备注列：多数行以 `"` 收尾；序号 7 历史写入未带收尾引号 → 两种都兼容
        if ln.endswith('"'):
            lines[idx] = ln[:-1] + extra + '"'
        else:
            lines[idx] = ln + extra
    text = '\n'.join(lines)


append('6', 'case', CASE6)
append('6', 'note', NOTE6)
append('7', 'note', NOTE7)

# 落盘前自检：复解析必须仍是 22 行 / 11 字段
rows = list(csv.DictReader(io.StringIO(text)))
bad = [i for i, r in enumerate(rows, start=2) if None in r or len(r) != 11]
if bad:
    raise SystemExit('复解析异常行：%s → 拒绝写入' % bad)
if len(rows) != 22:
    raise SystemExit('行数 %d != 22 → 拒绝写入' % len(rows))

io.open(P, 'w', encoding='utf-8', newline='').write(text)
print('rows 6/7 updated（复解析 22 行 / 11 字段通过）')
