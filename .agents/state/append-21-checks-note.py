#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""台账序号 21 行回写（本轮 checks 复核）。走文件避免 shell 引号/中文转义问题。

用法: python .agents/state/append-21-checks-note.py
"""
import subprocess
import sys

CASE = (
    "复核通过 2026-09-16 16:0x（cron aap-tdd-run-20260916-1545）· 430 宽 iframe 载体页 `__measure-mine.html`（由 248 行旧体例、无 checks 重写）+ "
    "**230 条设计期望值 checks**：红基线（修复前源码 + 同一份最终版探针两轮）**17/230** → 绿 **0/230** · "
    "两轮独立测量 43/43 字段全等（不一致 0）· docH 990 = 设计帧高 · 溢出 0 · 文案缺失 0 · "
    "像素对账（设计 PNG 430×990 vs 实现截图 430×990）**内容列 16/16 + 条列 13/13 = 29 命中 / 0 未命中**（位移中位 0 · max 1）· "
    "六个交互相出口各两轮（withdraw / rows-quotes / usage / settings / tab-workbench / tab-mine，requests 集合相等；"
    "withdraw 7 行全只读零写请求 + hash 不变 + toast「提现功能暂未开放」）· "
    "共用组件回归门 序号 20 载体页复跑 **148 条 0 失败**（两轮全等；先跑 `refresh-notification-mock.py` 修测量面相对时间过期）· "
    "`check-mock-fixtures --mock api-21` **9 PASS + 反向体检 PASS / FAIL 0**（本轮新补 9 条）· "
    "`review-artifacts` 22/22 · 报告 `evidence/review-序号21-checks-报告.md`"
)

NOTE = (
    "复核轮修 10 类偏差（先红后绿，清单见 `evidence/red-序号21-checks-设计期望值偏差.txt`）："
    "①头像字形盒 16×16 → **33×45**（设计 85003c7e fs30 声明 w33 × 行盒 30×1.5；形状 26×25 按设计字形墨迹画在盒内）"
    "②4 处文本行盒未按设计 `lineHeight 1.2`：类型标签/已认证 16→**13.2** · 钱包标题 21→**16.8** · 提现文案 20→**15.6**"
    "③行图标字形盒 16×16 → **20×27**（设计字形层声明 w20 · fs18 行盒 27；x 44→42、top 逐行 +6，形状 17×16 移入 `::before`）"
    "④行标签行盒 19.5→**15.6** ⑤行值行盒 18→**14.4** ⑥胶囊文字行盒 14→**12**"
    "⑦字形颜色改由伪元素承载（原 `background: currentColor` 在元素自身 → 探针读 `::before` 拿不到颜色）"
    "· **口径改正**：备注⑧「用量与对账 / 账号与设置 落点页未实现 → 跳转由 uni 侧降级」**作废** —— "
    "序号 22 `/pages/usage/index` 与序号 23 `/pages/settings/index` 均已实现并注册在 pages.json，"
    "本轮 `?scenario=usage` / `?scenario=settings` 实测落点渲染（「用量概览」/「账号与设置」），"
    "`src/utils/routes.ts` 对应注释同步改为「已实现」"
    "· **探针自身 2 类期望值 bug 已修正并重跑红基线**（红/绿同版探针）：head.tags.top 误把「带 padding 的容器」当「子行」（改断容器 74 + 新增 `.head__type.top` 82）；"
    "entries.values 漏了第 5 行「我的消息」的「待阅读 3」（设计 row5 确有值节点，且字色是字面量 `rgba(0,0,0,1)` 与同卡其它值不同 → 逐值断言）"
    "· 遗留（未擅自改）：设计帧第 5 行「待阅读 3」与 chevron 被推出卡片右界（导出图墨迹 372..429 > 卡右界 414）→ 实现按零溢出右对齐，已登记 `designLiteralDiff`"
)

cmd = [sys.executable, ".agents/state/append-ledger-note.py", "21", "--case", CASE, "--note", NOTE]
print(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout)
print(subprocess.run([sys.executable, ".agents/state/normalize-ledger-eol.py"], capture_output=True, text=True, encoding="utf-8").stdout)
