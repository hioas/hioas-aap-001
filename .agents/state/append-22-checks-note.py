#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""台账序号 22 行回写（本轮 checks 复核）。走文件避免 shell 引号/中文转义问题。

用法: python .agents/state/append-22-checks-note.py
"""
import subprocess
import sys

CASE = (
    "复核通过 2026-09-16 16:3x（cron aap-tdd-run-20260916-1605）· 430 宽 iframe 载体页 `__measure-usage.html`（由 293 行旧体例、无 checks 重写）+ "
    "**267 条设计期望值 checks**：红基线（修复前源码 + 同一份最终版探针两轮）**8/267** → 绿 **0/267** · "
    "两轮独立测量 50/50 字段全等（不一致 0）· docH 1138 = 设计帧高 · 溢出 0 · 文案缺失 0 · "
    "像素对账（设计 PNG 430×1138 vs 实现截图 430×1138）**命中 39 / 未命中 8**（未命中 = 汇总卡投影衰减尾 4 + 成本值 H5 回退字体字距 4，均非页面缺陷；位移中位 0）· "
    "文本行对账 21↔21 行（8 行完全相同，其余 ±1）· 三交互相出口各两轮 requests 逐字节相同"
    "（back：uni H5 无栈 → 整页重载，`windowMark=null` 证明；month：点开真 uni-picker → 确认 → 第二次真取数 `GET /usage/summary?month=2024-06`；"
    "detail：无落点 → no-op，hash 不变 / 无 toast / 无新请求）· "
    "共用消费方回归门 序号 2 工作台（同用 `usage-model.ts` 的 D3 口径）复跑 **103 条 0 失败**（两轮 docH 1146 全等）· "
    "`check-mock-fixtures --mock api-22` **5 PASS + 反向体检 PASS / FAIL 0**（本轮新补 5 条）· `review-artifacts` 22/22 · "
    "报告 `evidence/review-序号22-checks-报告.md`"
)

NOTE = (
    "复核轮修 5 类偏差（先红后绿，清单见 `evidence/red-序号22-checks-设计期望值偏差.txt`）："
    "①**汇总卡 padding 20 → 20/16**（设计 811a53eb padding=[20,16,20,16]；宫格 175 → 178.5 宽、x 36 → 32、标题 x 36 → 32 —— 一条改动解掉 3 条 check）"
    "②**补设计 effects `drop_shadow(0,6,20,rgba(15,23,42,.06))`** —— 该卡**无 stroke**，此前只给「趋势/模型/成本/明细」四卡写了 ring，汇总卡的投影整体漏实现（探针 `chkD` 反向断言本卡仍无 border）"
    "③月份日历字形盒 17×15 → **17×22.5**、下箭头字形盒 18×15 → **18×24**（= 设计层声明宽 × 字号×1.5），并去掉下箭头形状的 `margin-bottom:3px`（把墨迹上移 1.5px；设计墨迹中心 = 胶囊中心 66）"
    "④月份文字行盒 18 → **14.4**（设计 lineHeight 1.2 × 12）"
    "· **探针自身 3 处口径 bug 已修正并重跑红基线**（红/绿同版探针）：`summary.tiles1.top/h` 误把「容器（含 padding-top）」当「宫格行」（改断容器 148/88 + 新增 tileTops [164,164,244,244]）；"
    "`models.trackW` 误以为 4 行同宽（轨道是 `fill_container`，末行「6%」百分比盒窄 7 → PNG 实测行 1 为 192、行 4 为 199 → want 改 `[192,192,192,199]`）；"
    "`summary.shadow` 的 want 缺 Chrome 序列化的尾随 spread `0px`"
    "· 另把 `trend.img.src` 从「读元素 src」改为「从 uni-image innerHTML 取 data-URI → atob 解码回 SVG」，新增 5 条硬断言（viewBox `0 0 358 150` · 4 条网格线 · 7 个数据点 · 折线 #2563EB · 面积 rgba(191,219,254,0.35)）"
    "· **本页定标**（写入状态文件 §5.15）：图标字形盒 = 声明宽 × 字号×1.5（返回 fs24→26×36 · 日历 fs15→17×22.5 · 下箭头 fs16→18×24 · 明细列表 fs18→20×27；chevron-right fs20 实测 22×28）；"
    "文本行盒**显式 height 优先**（标题 20 · 值 26 · 标签 16 · 合计值 21 · 底部 16）、无显式 height 走 `lineHeight 1.2`（12→14.4）；"
    "设计里「容器 padding-top N + 行」的容器盒 = N + 行盒（探针必须分两层写，否则自造假偏差）"
    "· **逐卡断言不统一**：汇总卡只有 effects（无 stroke）、其余四卡只有 stroke #EEF2F7（无 effects）→ 必须逐卡写 want"
    "· 保留登记项（不照抄设计）：占比条填充 = 百分比 × **轨道宽**（设计声明 = 百分比 × 卡外层宽 398，设计自身不自洽，台账备注①）· 横轴末位标签设计自行左移 8px（实现按数据点 x 居中）· 趋势图 = data-URI `<image>` + DOM 横轴标签（mp-weixin 不能内联 svg，同序号 6 雷达图）"
    "· 工具侧发现：`review-measure.sh` 的 mock 参数必须是**仓库相对路径**（`.agents/state/h5-measure/api-22`）—— 传裸 `api` 会变成 `<root>/api` → 整页 404、checkFails 假红（本轮共用回归门首跑就吃了一次 19 条假失败，SKILL §5 已记该陷阱）"
)

cmd = [sys.executable, ".agents/state/append-ledger-note.py", "22", "--case", CASE, "--note", NOTE]
print(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout)
print(subprocess.run([sys.executable, ".agents/state/normalize-ledger-eol.py"], capture_output=True, text=True, encoding="utf-8").stdout)
