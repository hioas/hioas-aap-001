#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""台账序号 15 行回写（本轮 checks 复核）。走文件避免 shell 引号/中文转义问题。

用法: python .agents/state/append-15-checks-note.py
"""
import subprocess
import sys

CASE = (
    "复核通过 2026-09-16 15:2x（cron aap-tdd-run-20260916-1505）· 430 宽 iframe 载体页 `__measure-contract.html` + "
    "**239 条设计期望值 checks**：红基线 5/239（另有探针自身 4 条期望值 bug 同步修正）→ 绿 **0/239** · "
    "两轮独立测量 37/37 字段全等（不一致 0）· docH 1231 = 设计帧高 · 溢出 0 · 文案缺失 0 · "
    "像素对账 内容列 35/38 + 条列 17/17 = 52 命中 / 3 未命中（3 条全在设计导出图提示卡顶部 207..217 的 1~3/255 雾带内，非页面缺陷）· "
    "三出口交互各两轮 requests 逐字节相同（pdf：GET /contracts/c1/file + GET /files/CT-2024-0613-008.pdf 200；"
    "sign：modal「确认签署」+ POST /contracts/c1/sign → toast「签署申请已提交」；back：hash 不变 + 零额外请求）· "
    "`check-mock-fixtures --mock api-15` FAIL 0（新补 3 条）· 报告 `evidence/review-序号15-checks-报告.md`"
)

NOTE = (
    "复核轮修 5 类偏差：①合同状态卡投影改回设计 effects `drop_shadow(0,6,20,rgba(15,23,42,.06))`"
    "（旧备注⑩「设计树读不到投影参数」**作废** —— dump-layout 实测 a05669ed 就带该 effects）"
    "②状态图标字形补 26×36 行盒（fs24×1.5，与同帧其余 4 个字形同口径）③待签署标文字 line-height 22→13.2（设计 1.2）"
    "④下载PDF按钮描边 ring 0.8→**1px**（设计 `stroke{thickness:1}`）"
    "⑤提示卡文案行盒 13.2→**16**（**像素对账抓出**：设计墨迹 221..232，修前实现 219..230 整行高 2px；修后 221..232 与设计相同）"
    "· 工具侧：`check-mock-fixtures.py` 的「变体前缀回退」原会把 api-15 误匹配成 api 的检查（一次 8 条无关 FAIL）→ 收窄为只对 `*-tmp-*` 生效并加零匹配 WARN"
)

cmd = [sys.executable, ".agents/state/append-ledger-note.py", "15", "--case", CASE, "--note", NOTE]
print(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout)
print(subprocess.run([sys.executable, ".agents/state/normalize-ledger-eol.py"], capture_output=True, text=True, encoding="utf-8").stdout)
