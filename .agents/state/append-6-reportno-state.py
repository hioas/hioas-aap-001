#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""状态文件回写：本轮（17:45 轮 · 序号 6/7 报告编号口径核定 + 行框偏差修复）。

用法: python .agents/state/append-6-reportno-state.py
"""
import io
from pathlib import Path

P = Path('.agents/state/aap-tdd-state.md')
text = io.open(P, encoding='utf-8', newline='').read()

NEW_STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
    '①队列 8 ✅（20 个载体页 checks 全覆盖）②队列 1 ✅ ③队列 7 ✅ ④D1 ✅ '
    '⑤**序号 6/7 顶部栏「报告编号」口径核定 ✅（本轮）**——序号 7 台账备注⑩ 的跨页断言经两条独立证据核定为**误判**并更正，'
    '两页行框偏差已修（序号 6 行框 16 · 序号 7-2 行框 13.2）⑥队列 3 余 15 条待人类拍板缺口 — 自主部分已执行完毕。'
    '队列 0（目录改名）= 决策 D6 挂起。管理端 8 页范围外。'
)

lines = text.split('\n')
if lines[0].startswith('STATUS:'):
    lines[0] = NEW_STATUS
else:
    raise SystemExit('first line is not STATUS: %r' % lines[0][:60])
text = '\n'.join(lines)

SECTION = '''
### 5.16 本轮（17:45 轮 · 序号 6/7 报告编号口径）新增的工具与口径

- **跨页断言核定脚本**：`python .agents/state/verify-report-no-prefix.py` —— 按**内容特征**（`DR-########-####`）
  在两帧设计树里找「报告编号」文本叶子，并对设计 PNG 量「顶部栏右侧墨迹包围盒」；输出转录
  `evidence/序号6-报告编号前缀核定.txt`。§7 的「一切以当前画布为准」要求这类跨页结论必须可复现，别靠 grep。
- **台账 CSV 体检**：`python .agents/state/validate-ledger-csv.py <file>`（逐行打印字段数，标出 ≠11 的行）。
  `normalize-ledger-eol.py` 已改为**先在内存生成完整文本 + csv 复解析校验，通过后才落盘**
  （旧版直接以 `"w"` 打开目标文件逐行写 → 中途解析报错会把已写部分留在盘上，实测把 22 行截成 6 行；本轮踩到并已修）。
- ⚠️ **往台账 CSV 追加文本的两条硬规则**：①追加进**带引号**字段（「用例(证据)」列）的文本里**不能出现 ASCII 双引号**
  —— 会提前闭合字段、把后续内容拆成新列；②追加进**不带引号**字段（序号 7 的「备注」列历史写入未加引号）的文本里
  **不能出现 ASCII 逗号**。写前先 `diag-ledger-boundary.py <序号>` 看边界形态，写完必须两条体检都过。
- ⚠️ **「设计里出现过该串」≠「设计文本含该串」**：page-6 `design.json` 里确实有 `报告编号` 字样，但那是
  **图层名**（frame `5d860a4b`），文本叶子 `202cd360` 的 content 只是 `DR-20240613-0758`。
  跨页断言前必须读**文本叶子的 content**（`text-fields.py` / `raw-node.py` / `node-by-id.py`），不要 grep 整个 design.json。
- ⚠️ **同族页的同一位置可以有两套行框口径，逐帧判**：序号 6 顶部「报告编号」是 frame **h=16**（叶子 height=fill_container）
  → 行框 16；序号 7-2 是单叶子 h=fit_content + lineHeight 1.2 → 行框 **13.2**。把一页的结论复制到另一页必错。
- **字符宽度可作独立证据**：同 fs 同字体的两串，墨迹宽之比 ≈ 字符数之比
  （page-6 95px / 15 字符 vs page-7-2 142px / 21 字符）→ 可反证「某串到底有没有前缀」，比只看设计树更硬。
- **口径锁要有牙齿的证明方式（变异测试）**：新增的「禁止型」断言（本轮的 `报告编号不带「报告编号」前缀`）
  天生是绿的 → 必须用**变异**证明：临时把被测行为改回错误形态 → 跑该用例看红 → 还原
  （`evidence/red-序号6-前缀口径锁-变异测试.txt`）。没做变异的「禁止型断言」等于没断言。
- **本轮新增脚本**：`verify-report-no-prefix.py` · `validate-ledger-csv.py` · `diag-ledger-row.py` · `diag-ledger-boundary.py` ·
  `append-6-reportno-note.py` · `append-6-reportno-state.py`；`shot-6.sh` 复用（430×5400）；设计 PNG 存
  `.agents/state/design-shots/page-6.png`（430×5342 · sha256 a505a58c…）。

- 2026-09-16 17:5x（cron 轮 `aap-tdd-run-20260916-1745`）· **序号 6/7 顶部栏「报告编号」口径核定 + 行框偏差修复（红 1+2 → 绿 0）**：
  ①**设计帧重抓（人工指令 C）**：序号 6（layer_id `0f0755e4-…`）`design.json` sha256 `08ad8ea5…` **逐字节相同**；
     序号 7-2（layer_id `47815a05-…`，首抓误用了序号 15 的 layer_id → 已纠正）sha256 `f2780416…` **逐字节相同**；
     两帧设计 PNG 重下载 sha256（`a505a58c…` / `6891e547…`）与留证一致 → **无漂移**。
  ②**核定结论（本轮主交付）**：序号 7 台账备注⑩ 的跨页断言「序号 6 也缺『报告编号』前缀、待回炉修」= **误判**。
     证据 ①设计树：page-6 叶子 `202cd360` content = `DR-20240613-0758`（w=97 · fs11）；page-7-2 叶子 `57f828cc`
     content = `报告编号 DR-20240614-0312`（w=143）。证据 ②设计 PNG 顶部栏右侧墨迹：page-6 **x318..412 w=95**（15 字符）
     vs page-7-2 **x271..412 w=142**（21 字符）。同 fs 同字体 → 差值恰是「有无前缀」之差。误判来源 =
     把 page-6 design.json 里的**图层名**「报告编号」当成文本内容。**序号 6 保持无前缀**，并加口径锁防回炉误改。
  ③**TDD 红→绿**：两页载体页各加 7 / 5 条设计声明值 checks（text / prefixAbsent·prefixPresent / h / top / right / lineHeight / fw）
     + `topbarNo` 实测留证字段。红基线（修复前源码 + 同一份最终版探针两轮）**序号 6 = 1/228**
     （`topbar.no.lineHeight: got normal want 16`）· **序号 7 = 2/201**（lineHeight normal→13.2 · h 16→13.2）→
     绿 **0/228 · 0/201**；两轮独立测量 25/25 · 31/31 字段全等（不一致 0）；docH 5343 / 1111 = 设计帧高。
  ④**修 2 处页面偏差**：`src/pages/report/index.vue` 的 `.report-page__no` 补 `line-height:16px`（design 5d860a4b frame 显式 h=16）；
     `src/pages/report-failed/index.vue` 的 `.rf-page__no` 补 `line-height:13.2px`（design 57f828cc h=fit_content · lineHeight 1.2）。
     两处都写明「逐帧不同」的理由与证据路径。
  ⑤**口径锁（变异测试证明有牙齿）**：`tests/pages/report.spec.ts` 新增「报告编号不带『报告编号』前缀」；
     临时把前缀写回模板 → 该文件 **2 failed**（新断言 + 原有精文断言）→ 还原后 17/17。
     证据 `evidence/red-序号6-前缀口径锁-变异测试.txt`。
  ⑥**像素对账**：`evidence/cmp-序号6-reportno-设计PNGvs实现截图-顶部栏.txt` —— 右区设计 x318..412 w95 y60..69 vs 实现
     x320..413 w94 y61..70（±2 横向 / +1 纵向 = 设计小数坐标 56.5 取整 + H5 回退字体墨迹，非页面缺陷）。
  ⑦**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮**（+1 新用例）· `type-check` exit 0 ·
     `build:mp-weixin` DONE（report wxss 含 `line-height:16px` · report-failed wxss 含 `line-height:13.2px`）·
     `build:h5` DONE · `review-artifacts` **22/22** · 截图 `evidence/20260916-1755-序06-检测报告-报告编号前缀核定-h5-430宽.png`（430×5400）。
  ⑧**台账回写**：序号 6 追加用例证据 + 备注⑫（核定结论与误判来源）；序号 7 备注⑩ 改写为**更正**（跨页结论作废）。
     顺带修好两个取证工具缺陷：`normalize-ledger-eol.py` 改为「内存生成 + 复解析校验后落盘」（旧版中途报错会截断台账，
     本轮实测把 22 行写成 6 行并已 `git checkout` 复原）、新增 `validate-ledger-csv.py` 逐行字段数体检。
  ⑨**下轮开工第一件事**：队列 3 余下 15 条待人类拍板缺口（自主部分已尽）——若无可自主项，则按队列 1 口径
     把「逐页复核」扩到**每页的顶部栏/导航区**这类跨页同族位置的一致性核对（本轮已示范序号 6↔7-2 的做法）。
'''

if '### 5.16' in text:
    raise SystemExit('§5.16 已存在，避免重复追加')
text = text.rstrip('\n') + '\n' + SECTION
io.open(P, 'w', encoding='utf-8', newline='').write(text)
print('state file updated（STATUS 行 + §5.16）')
