#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""往台账 序号 8/10/10.1/12/22 行追加本轮「导航标题行盒」口径修正的证据与备注。

规则（状态文件 §5.16）：追加文本里不得出现 ASCII 双引号与 ASCII 逗号（用「」与全角 、）。
用法: python .agents/state/append-navtitle-note.py
"""
import csv
from pathlib import Path

path = Path(".agents/state/aap-feature-status.csv")

CASE = ("跨页「导航标题行盒」口径修正（2026-09-16 18:1x）：探针 want 改按各帧 design.tree.json 的标题文本叶子声明值"
        "（显式 height 优先、否则 fontSize×lineHeight 1.2）——序号 8 由 30→24 · 10 由 22→20.4 · 10.1 由 22→20.4 · "
        "12 由 21→20.4 · 22 由 25.5→20.4；红基线各 1 失败 → 绿 0、两轮独立测量差异字段 0、docH 不变"
        "（1206/1409/1414/1027/1138）、序号 22 标题盒中心 66 与设计 PNG 墨迹 57..73 一致（实现 58..74 = +1 行 H5 回退字体）；"
        "命令 bash .agents/state/review-measure.sh <序号>-navtitle __measure-*.html <mock> 55xx；"
        "证据 evidence/review-序号<n>-navtitle-run{1,2}.json · redgreen-导航标题行盒-20260916-1800.txt · "
        "nav-title-audit-20260916-1800.txt（跨页 21 页扫描）")

NOTES = {
    "8": ("导航标题行盒 30→24 属声明保真修正（旧注释「20px 行框 = 20×1.5」与代码值自相矛盾）：该行行高由「新建报价」按钮 30 决定 "
          "→ 栏高与整页几何不变（docH 1206）"
          " ｜ 同批登记：序号 2/21 的标题类名不在本核对器的选择器覆盖内（.workbench__title / 用户头部姓名）→ 判读为未覆盖、非偏差"),
    "10": "导航标题行盒 22→20.4 属声明保真 + 跨页一致性修正：该行行高由返回图标盒 26×36 决定 → 栏高 96 与整页几何不变（docH 1409）",
    "10.1": "导航标题行盒 22→20.4 属声明保真 + 跨页一致性修正：该行行高由返回图标盒 26×36 决定 → 栏高 96 与整页几何不变（docH 1414）",
    "12": ("导航标题行盒 21→20.4 属声明保真 + 跨页一致性修正（同一设计声明 fs17 × 1.2 此前在 5 个页面被写成 4 个值）："
           "该行行高由返回图标盒 26×36 决定 → 栏高 96 与整页几何不变（docH 1027）"),
    "22": ("导航标题行盒 25.5→20.4 属声明保真 + 跨页一致性修正（同声明的序号 23 已是 20.4）：该行行高由返回图标盒 26×36 决定 "
           "→ 栏高 96 与整页几何不变（docH 1138）；标题墨迹中心 66 未变（改前后同为盒中心 66）"),
}

raw = path.open(encoding="utf-8", newline="").read()
rows = list(csv.DictReader(raw.splitlines()))
fields = list(rows[0].keys())

hit = []
for r in rows:
    if r["序号"] in NOTES:
        r["用例(证据)"] = (r["用例(证据)"] or "") + " ｜ " + CASE
        r["备注"] = (r["备注"] or "") + " ｜ " + NOTES[r["序号"]]
        hit.append(r["序号"])

with path.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)

print("追加 %d 行 · 序号 %s" % (len(hit), hit))
