#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本轮（aap-tdd-run-20260916-0910, 决策 D3）对状态文件做定点回写。

原因：aap-tdd-state.md 行尾混合 CRLF/LF，patch 工具的模糊匹配会失配 →
统一用脚本做「行内片段替换 + 末尾追加」，并保留原行的行尾风格。
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-tdd-state.md")

REPLACEMENTS = [
    # 队列 2：口径核对已完成
    (
        "2. **已拍板口径的落地核对**：用户已拍板一条",
        "2. ✅ **已拍板口径的落地核对（已完成 2026-09-16 09:38）**：用户已拍板一条",
    ),
    (
        "   有则按同口径改（**先红后绿**，别只改注释）。",
        "   有则按同口径改（**先红后绿**，别只改注释）。→ **核对结果：无遗漏** —— "
        "`src/pages/quotes/index.vue:158`（新建报价）与 `src/utils/report-model.ts:112 QUOTE_ROUTE`（填写报价）及断言 "
        "`tests/pages/quotes.spec.ts:156` / `tests/pages/report.spec.ts:190` 均为 `/pages/quote-models/index`；"
        "卡片内「报价」= `quote-form/index?quoteId=`（按设计稿打开当前报价单，带参，非「新建」入口，保留）；"
        "唯一残留是 `tests/pages/report.spec.ts` 头部旧注释（已改）；台账序号 6 行已追记。",
    ),
    # 队列 9：D3 已完成，下一件事变成队列 8
    (
        "- **D3 · 图例百分比统一且最优**（`待执行`）——最大余数法 + 环形图与图例同分母，是工作台（序号 2）的实质改造，**下轮第一件事**。",
        "- ✅ **D3 · 图例百分比统一且最优** —— **已完成 2026-09-16 09:35**（口径落在 `src/utils/percentage.ts`，执行证据见 `aap-decisions.md` D3）。"
        "**下轮第一件事 = 队列 8**（给序号 3 的载体页补「设计期望值 checks」维度，照 `__measure-login.html` 的 `chk(k,got,want)` 做法）。",
    ),
    (
        "- D2 已由本轮执行完（见 `aap-decisions.md` D2 证据）；D4/D5 的「循环要做的」小改（tokens 顶部注释、`docs/aap-client-page-plan.md` §4 结论）尚未做。",
        "- D2 已完成（2026-09-16 09:15）；**D4/D5 的循环侧小改已完成 2026-09-16 09:38**（`src/styles/tokens.scss` 顶部注释改为"
        "「主色=设计稿蓝（D4）+ 图标维持 CSS 占位（D5）」；`docs/aap-client-page-plan.md` §4 表格三行冲突结论更新）。D1~D6 至此全部有结论。",
    ),
]

APPEND_AFTER_COMMAND = [
    "- **D3 测量面（本轮新增）**：缺字段变体的载体页场景 `?scenario=nomedia` + mock 变体重建/清理 "
    "`python .agents/state/make-nomedia-mock.py [--clean]`（= api 目录去掉 summary 的 audio/video 字段）；"
    "看某轮实测的 checkFails `python .agents/state/show-measure-fails.py <json> [phase] [字段...]`。",
    "- ⚠️ `python .agents/state/cmp-measure-runs.py <runA> <runB> <phase>` —— **第 3 个参数（phase）必填**，"
    "省略会 IndexError: list index out of range（本轮踩到）。",
    "- ⚠️ 载体页解析 `conic-gradient` 时注意：Chrome 会把每段序列化成「color p%, color p%」两两配对、颜色写成 `rgb()`，"
    "`color from% to%` 式正则解析不到任何段（本轮踩到，已修 `__measure-workbench.html` 的 ringStops）。",
]

SUMMARY = """- 2026-09-16 09:38（cron 轮 `aap-tdd-run-20260916-0910`）· **执行决策 D3（图例百分比统一且最优）+ 队列 2 口径核对 + D4/D5 循环侧小改**：
  ①**D3 落地（本轮主交付，严格 TDD）**：新增 `src/utils/percentage.ts`（唯一口径：分母 = max(total_tokens, Σ六类) + 最大余数法 + `percentTotalOf`），
  `workbench-model.ts` 出 `ring{hasData,denominator,segments,percentSum,remainderPercent}` 与 `categories[i].percent`，
  页面 `donutBackground` 只读 `model.ring`（不再自算比例）；三个红基线（`red-D3-01/02/03*.txt`，含 `'45% · 1.74B' ≠ '42% · 1.74B'` 与 conic 42.54% ≠ 图例整数 42）→ 三处绿。
  实测：分母 4.09B → 图例 **42/28/14/4/6/6（合计 100，修前照抄设计稿=106%）**，环形图分段宽与图例逐项相等；缺字段场景两行 `—`（不显示 0%）、4 段 + 6% 余量 = 100。
  ②**证据有牙齿**：载体页 `__measure-workbench.html` 新增 11 条 D3 checks（`d3.legend.*` / `d3.ring.stopWidths` / `d3.ring.stopColors` / `d3.ring.remainder` / `d3.ring.totalPct` / 设计字面量必须缺席）
  + `overriddenByDecision` 决策留痕；`api` mock 与 `api-tmp-d3-nomedia` 两种场景各跑**两轮独立测量全等**（`review-序号2-d3-run{1,2}.json` / `review-序号2-d3nomedia-run{1,2}.json`，`checkCount 103 · checkFailCount 0 · 溢出 0`）；
  变体用新增的 `make-nomedia-mock.py` 复现（用完已 clean）。与 D2 轮留证差异仅 D3 相关 7 项。
  ③**质量门**：`npm test` **1168/1168 · 72 files 连跑两轮**（`green-D3-全量轮1/2.txt`）· `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE（`pages/workbench` 四件套齐备）·
  截图 `logs/screenshots/20260916-0932-序号2-工作台-图例统一口径D3-h5-430宽.png`。
  ④**队列 2**：全仓库核对「新建/填写报价」落点确为 `/pages/quote-models/index`，无遗漏；顺手修掉 `tests/pages/report.spec.ts` 头部旧注释。⑤**D4/D5 循环侧小改**：tokens.scss 顶部注释 + 页面计划 §4 冲突表更新。
  ⑥**下轮第一件事**：队列 8 —— 给序号 3 的载体页补「设计期望值 checks」维度（照 `__measure-login.html` 的 chk 做法，每页一轮）。
"""


def main():
    with io.open(P, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()

    misses = []
    for old, new in REPLACEMENTS:
        if old not in text:
            misses.append(old[:40])
            continue
        text = text.replace(old, new, 1)

    tail_anchor = "- Calicat CLI：`calicat status`"
    added = "\n".join(APPEND_AFTER_COMMAND)
    if tail_anchor in text and APPEND_AFTER_COMMAND[0][:18] not in text:
        idx = text.rindex("\n", 0, text.index(tail_anchor))
        text = text[:idx] + "\n" + added + text[idx:]
    elif not APPEND_AFTER_COMMAND[0][:18] in text:
        misses.append("anchor for §5 commands")

    summary_anchor = "## 5. 关键命令（照抄可用）"
    if SUMMARY.strip().splitlines()[0] not in text and summary_anchor in text:
        idx = text.rindex(summary_anchor)
        text = text[:idx] + SUMMARY + "\n" + text[idx:]
    elif SUMMARY.strip().splitlines()[0] in text:
        misses.append("summary already present")

    with io.open(P, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)

    if misses:
        print("MISSED:")
        for m in misses:
            print("  - %s" % m)
        return 1
    print("state file updated: %d in-line replacements + %d command lines + summary" % (len(REPLACEMENTS), len(APPEND_AFTER_COMMAND)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
