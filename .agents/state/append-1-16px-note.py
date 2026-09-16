#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""台账序号 1 行回写（本轮 16px 残差收口）。走文件避免 shell 引号/中文转义问题。

用法: python .agents/state/append-1-16px-note.py
"""
import subprocess
import sys

CASE = (
    "16px 残差收口 2026-09-16 18:5x（cron aap-tdd-run-20260916-1845）：载体页 `__measure-login.html` 再扩 "
    "**19 条设计期望值 checks（合计 133 条）** —— 红基线（同版探针两轮）**19/133** · docH 1098 "
    "（转录 `evidence/redgreen-序号1-16px残差-20260916.txt`）→ 绿 **0/133** · **docH 1114 = 设计帧高**（修前 1098）；"
    "两轮独立测量 phase1 **全字段逐字节相同** · 溢出 0 · 文案缺失 0 · "
    "像素对账（设计 PNG 430×1114 vs 实现截图 `evidence/20260916-1945-序01-登录注册-16px残差对齐-h5-430宽.png` 430×1114）"
    "**命中 42 / 未命中 6**（未命中逐条判读 = 投影衰减起点 656/891 · 设计导出图软染色 914/920 · 带分割阈值效应 819/415，均非页面缺陷）；"
    "文本行逐行对账：两行免责正文墨迹 设计 965..975 / 980..990 = 实现 966..976 / 980..990（行距 15），其余全行 ±1 · "
    "npm test **1182/1182 ×2**（72 files）· type-check exit 0 · build:mp-weixin DONE（wxss 含 `width:16px;height:21px` / `height:40px` / "
    "`line-height:14.4px` ×2 / `0 0 0 1px #eef2f7` / `min-height:18px`）· build:h5 DONE · `review-artifacts` 22/22 · "
    "共用消费方回归门 序号 2 工作台两轮 **103 条 0 失败** · "
    "命令 `bash .agents/state/review-measure.sh 1-red|1-green __measure-login.html .agents/state/h5-measure/api 5393|5394`"
)

NOTE = (
    "16px 残差已收口（先红后绿 6 类）①首字段前间距 16→**20**（设计 spacer 9113d86d h20；其余字段之间仍 16）"
    "②验证码提示行 14.4→**21** 且图标占位盒 12×12→**16×21**（设计图标层 c7f5db13 声明 w16 fs14 · 字形行框 = fs×1.5；"
    "形状 13×13 按设计字形墨迹 PNG 实测 x37..49 / y630..642 画在盒内），颜色由 `$color-primary` 改 **rgba(148,163,184,1)**（= 设计字形填充 · 灰）并改由 `::before` 承载 "
    "③免责卡标题行 20→**27**（图标盒 14×14→**20×27**，设计 477e4b3f w20 fs18；形状 15×17 · 填充 rgba(37,99,235,1)）"
    "④免责正文 38→**40**（设计 e5e24331 **显式 height 40** = 两行；`line-height` 1.6→**14.4px** 且垂直居中 → 墨迹行距 15 与设计逐行相同）"
    "⑤免责卡描边 `border`→**box-shadow 0 0 0 1px**（设计 stroke align=center；border 会把卡高撑成 109、内容宽挤掉 2px）"
    "⑥分隔行 17→**18**（设计 spacer 669abf96 h18）· 协议行 20→**18**（设计 row alignItems=center → 去掉勾选框 `margin-top:2px`）。"
    "**下轮待办（本轮发现并留证、未擅自改）**：(a) 本页仍有 5 处 center 描边用 `border` 实现（`.field__box` ×3 · `.captcha` · `.sms-btn` · `.wechat` · `.agree__box`）"
    "→ 按同族页口径应改 `box-shadow: 0 0 0 1px`（border 占布局：输入框内容左界 设计 48 vs 实现 49、右界 382 vs 381）；"
    "(b) 3 个输入框图标占位盒 16×16 → 应 **20×27**（设计 df37d41e 等声明 w20 fs18）且填充改灰 rgba(148,163,184,1) —— "
    "实测设计占位文本左界 **76** vs 实现 **73**（ink-runs y407..421）。"
    "另：设计帧协议行勾选框为**选中态**（蓝底 + tick）而实现默认未选中 —— 按 PRD 校验门（未勾选不得提交）保留，"
    "像素对账该行差异属状态差非几何差。"
)

cmd = [sys.executable, ".agents/state/append-ledger-note.py", "1", "--case", CASE, "--note", NOTE]
print(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout)
print(subprocess.run([sys.executable, ".agents/state/normalize-ledger-eol.py"], capture_output=True, text=True, encoding="utf-8").stdout)
print(subprocess.run([sys.executable, ".agents/state/validate-ledger-csv.py", ".agents/state/aap-feature-status.csv"], capture_output=True, text=True, encoding="utf-8").stdout)
