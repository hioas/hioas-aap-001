#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""回写状态文件：STATUS/LEASE + 本轮小结 + §5 工具与口径。用法: python .agents/state/append-1800-state.py"""
import io
import re

P = '.agents/state/aap-tdd-state.md'
text = io.open(P, encoding='utf-8', newline='').read()

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：①队列 1 当前修订版全量复核 ✅（22 载体页 28 相 × 2 轮全绿 · 两轮差异 0）'
          '②画布「全新版本」覆盖核对 ✅（台账 22 行 layer_id/帧名全部命中 · 未覆盖 8 帧均为管理端·PC）'
          '③跨页「导航标题行盒」一致性核对与修正 ✅（5 页 want 改按设计声明 · 红 1→绿 0 · 几何与墨迹不变）'
          '④设计真源重抓 ✅（21 SAME + 1 已知 DIFF）⑤队列 3 余 15 条待人类拍板缺口 — 自主部分已执行完毕。队列 0（目录改名）= 决策 D6 挂起。管理端 8 页范围外。')

text = re.sub(r'^STATUS: .*$', STATUS.replace('\\', '\\\\'), text, count=1, flags=re.M)
text = re.sub(r'^LEASE: .*$', 'LEASE: free until -', text, count=1, flags=re.M)

SUMMARY = """
- 2026-09-16 18:1x（cron 轮 `aap-tdd-run-20260916-1800`）· **队列 1 当前修订版全量复核（22 载体页 × 2 轮）+ 画布「全新版本」覆盖核对 + 跨页「导航标题行盒」一致性核对与修正（5 页红 1→绿 0 · 声明保真）**：
  ①**设计真源重抓（人工指令 C）**：`python E:/agent/aap-tools/recapture-all.py` → 22 帧 = **21 SAME + 1 DIFF**；唯一 DIFF = 序号 8「新建按钮」`width 97→100`
  （08:55 基线的同一差异：自动布局算得、与子节点 18+4+54+padding 自洽，实现早已按 100、台账已记）→ **无漂移**。另重抓 inventory：30 帧列表与留证**逐字节相同**（仅 `capturedAt` 变化）。
  ②**画布覆盖核对（新增 `canvas-coverage-check.py`，本轮主交付之一）**：台账 22 行的 `layer_id` + 帧名**全部仍在当前画布上**（失配 0）；当前画布 30 帧中未被台账覆盖的
  = 根容器 + **8 个管理端·PC 帧**（范围外）→ **画布上不存在未实现的报价端帧**。证据 `evidence/canvas-coverage-20260916-1800.txt`。
  ③**队列 1 全量复核（新增 `coverage-rerun.sh` + `coverage-report.py`）**：22 个载体页 × 2 轮 = **28 个相全部 `checkFailCount 0`、两轮独立测量差异字段 0**、溢出 0；
  3 个相被工具标注后逐条判读为**非回归**：序号 20 相对时间「10 分钟前」漂成 12 分钟（测量面时间偏移 → 已把 `refresh-notification-mock.py` 挪到该页测量**紧前**，并修好 `coverage-report.py` 不认扁平单段文件导致 序号 3/4 漏报的缺陷）、
  序号 4-v1 phase1 空态 2 条文案缺失（该相定义）、序号 9 phase1 首屏取数前快照（0 checks/19 缺文案，与各页 checks 轮留证逐字段相同）。证据 `evidence/coverage-20260916-1800.{json,txt}`。
  ④**跨页同族位置核对（人工指令 B 的扩展）**：新增 `topbar-matrix.py`（设计侧顶部栏声明矩阵）/`nav-title-decl.py`（顶部栏文本叶子声明）/`nav-title-audit.py`（21 页 want vs 实现）/`nav-cross-matrix.py`（实现侧矩阵）
  → 查出**同一设计声明（标题 fs17 或 fs20 · lineHeight 1.2）在 5 个页面被写成 4 个不同行盒**，其中序号 22 的载体页更把实现值 25.5 写成 want（自证绿）。逐页**先红后绿**（want 先按设计声明改 → 看红 → 改源码 → 两轮绿）：
  序号 8 **30→24** · 10 **22→20.4** · 10.1 **22→20.4** · 12 **21→20.4** · 22 **25.5→20.4**（15/23 两页原本已是 20.4）。
  ⑤**性质与证据（不夸大）**：5 页均为**声明保真 + 跨页一致性**修正，**几何与墨迹不变** —— `docH` 1206/1409/1414/1027/1138 全不变、序号 22 标题盒中心恒 66（改前 53..79 / 改后 56..76）、
  实现截图标题墨迹 58..74 vs 设计 PNG 57..73（+1 行 = H5 回退字体，同族既有记录）；红基线各 1 失败 → 绿 0、两轮差异字段 0
  （`evidence/redgreen-导航标题行盒-20260916-1800.txt` · `review-序号*-navtitle-run{1,2}.json` · 截图 `evidence/20260916-1800-序22-用量概览-导航标题行盒口径-h5-430宽.png`）。**未改**：序号 20（26 由设计 PNG 导航高 86 反推、有依据）、序号 2/21（核对器选择器未覆盖 → 登记为未判读）。
  台账 序号 8/10/10.1/12/22 行已逐行回写（`append-navtitle-note.py` + `normalize-ledger-eol.py` + `validate-ledger-csv.py` 22 行 × 11 字段体检通过）。
  ⑥**下轮开工第一件事**：把序号 3（`.cred__title` 声明 h24 vs 实现 21.6）与 序号 2/21 的标题选择器补进核对器后重跑；若仍有跨页同族位置未覆盖，按同族清单继续（底部操作条 / 卡片标题已在本轮核对器范围内）。

### 5.17 本轮（18:00 轮）新增的工具与口径

- **全量复核一条龙**：`bash .agents/state/coverage-rerun.sh [起点序号]`（build:h5 → 逐页 `review-measure.sh cov-<序号>` 两轮，序号 20 测量前**紧前**重置相对时间 mock）
  + `python .agents/state/coverage-report.py [--json out.json]`（逐页逐相 checks/失败/**两轮差异字段**/docH/溢出/缺文案，**兼容扁平单段文件**）。
- **画布覆盖核对**：`python .agents/state/canvas-coverage-check.py [--out …]`（台账每行 ↔ 当前画布 layer_id/帧名；未覆盖帧按「报价端 / 范围外」分类 → 回答「当前画布上有没有没实现的报价端帧」）。
- **跨页同族位置核对四件套**：`topbar-matrix.py`（设计侧：逐帧顶部栏节点 + 子树声明值）· `nav-title-decl.py`（逐帧顶部栏文本叶子 fs/fam/lineHeight/height）·
  `nav-title-audit.py`（21 页 want vs 实现；want = 显式 height 优先，否则 fs×lineHeight；实现侧支持 `$font-*` token 与无单位 line-height 换算）· `nav-cross-matrix.py`（实现侧 nav/topbar 字段矩阵）。
- ⚠️ **「文本行盒 = 字号×1.5」只适用于图标字形层**：本轮查出 5 个页面把该倍数用到了**文本**标题上（20→30 / 17→25.5 等），而设计对文本一律 `lineHeight 1.2`
  （或显式 height）。跨页核对时先读**该帧**该文本叶子的声明值，再判实现；探针 want 更不许照抄实现（序号 22 曾把 25.5 写成 want → 自证绿）。
- ⚠️ **居中单行文本的 line-height 不改变墨迹位置**：这类偏差在像素对账里**量不到**（盒中心不变），只在「换行/对齐方式变化」时才外显 ——
  本轮仍按「want = 声明值」修正并留证，判读结论写「几何与墨迹不变、属声明保真」，不夸大成视觉缺陷。
- **CSS 里同位置多值 = 排查线索**：同一 `.nav__title`/`.topbar__title` 在 5 个页面出现 4 个不同 line-height，靠 `nav-title-audit.py` 的跨页表一眼可见。
"""

anchor = '\n## 5. 关键命令（照抄可用）'
if '### 5.17 本轮（18:00 轮）新增的工具与口径' not in text:
    text = text.rstrip('\n') + '\n' + SUMMARY
io.open(P, 'w', encoding='utf-8', newline='').write(text)
print('状态文件已回写（STATUS/LEASE + 本轮小结 + §5.17）；字节 %d' % len(text.encode('utf-8')))
