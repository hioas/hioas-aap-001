# -*- coding: utf-8 -*-
"""把序号 11 的本轮小结 + §5.7 工具/口径追加进 .agents/state/aap-tdd-state.md（保持原行尾风格）。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, '.agents', 'state', 'aap-tdd-state.md')

with io.open(P, encoding='utf-8', newline='') as f:
    txt = f.read()

eol = '\r\n' if txt.endswith('\r\n') else '\n'

NOTE = """- 2026-09-16 13:2x（cron 轮 `aap-tdd-run-20260916-1315`）· **队列 8 第 11 页：序号 11「【报价管理】模型定价-详情」载体页补「设计期望值 checks」维度（271 条 · 偏差 21→0）+ 5 类设计偏差修复（含卡片投影与图标盒）**：
  ①**改名**：未执行 —— 队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-11`（layer_id `46c3747b-3aca-419f-a302-22cf9de8cff8`）→ `design.json` sha256 `fcec8353…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ③**TDD 红→绿（本轮主交付）**：`__measure-model-pricing.html` 由 285 行旧体例重写为 **430 宽 iframe + 271 条 checks**（构建脚本 `build-probe-11.py`，helpers 与 `__measure-profile.html` 同源）；
     红基线（**修复前源码 + 同一份探针两轮**）**256 条 · 21 失败**（`red-序号11-checks-设计期望值偏差.txt`）→ 绿 **0/271**（`green-序号11-checks-设计期望值.txt`）；
     两轮独立测量 **15/15 字段全等**（`cmp-measure-runs … phase1` 不一致 0）；docH **1540**（设计框高算术 98.4+1365+76 = 1539.4，PNG 1541 含底投影 AA）。
  ④**红基线 21 条的分诊**（写进 red 转录末尾，避免把探针 bug 记到页面账上）：**15 条真页面偏差 + 6 条探针自身期望值 bug**
     （`normShadow()` 会把 alpha=1 的 box-shadow 颜色归一成 `rgb(...)`，而我 want 写了 `rgba(…, 1)`）+ 1 条索引写错（`card3.tokenBoxTops` 用 `slice(0,3)`，而 `.card--box--input` 的 DOM 顺序是行内成对）。
  ⑤**修掉 5 类偏差**（清单见 `evidence/review-序号11-checks-报告.md` §3）：①四张卡补设计 effects `drop_shadow(0,4,16,rgba(15,23,42,.06))` ②保存按钮补 `drop_shadow(0,6,16,rgba(37,99,235,.28))` ③**图标盒改为「盒子 = 设计图层盒、形状入 `::before`」**（卡1 折叠箭头 20×20 · 计费 caret 18×18 · 加分支 + 18×18 · 保存按钮 ✓ 22×22 · 媒体/规则箭头 18×18 · 规则组删除 18×18 · 条件行 + 15×15）④连带布局回到设计值（添加计费分支按钮 **111→119** = 12+18+4+73+12 · 计费方式选择框 **245→237** · 按钮 x **287→279**）⑤媒体列勾选框描边 0.8→**1px**（设计 thickness=1，`:not(.check--on)` 保证勾选态仍无描边）。
  ⑥**本页定标（与其它页不同，必须记住）**：本页 remixicon/字形行框 ≈ **fontSize × 1.1**，不是 ×1.5 —— 三条独立实测自洽（媒体定价头 17.6≈18 · 条件操作行 15.4≈16 · 返回图标盒 26.4≈26）；用 ×1.5 会把卡1 顶成 83（设计 82）、卡3 顶成 603（设计 597）。
  ⑦**像素对账**：`cmp-bands-6-design-vs-impl.py`（±3）内容列 **59/62** + 条列 **19/19** = 78 命中 / 3 未命中；未命中 3 条用 `scan-col` 逐条判读 = 卡2/卡3 顶边 **−2px**（Figma 小数坐标链 211.4→210 / 378.4→377）与底栏内 AA 行的带起点边界效应 → **非页面缺陷**（本轮不在 1–2px 上 churn，避免把下游越改越偏）。
  ⑧**交互相有牙齿**：`requests-序号11-checks-run{1,2}.txt` 各 6 行且两轮逐字节相同 —— 首屏 `GET /quotes/items/qi1`；点顶栏「保存」→ 真实 `PUT /quotes/items/qi1`（body 含 input/output/tier/billing_mode/request_rules）→ toast「保存成功」；勾选「缓存读取价格」→ `.check--on` 2→3 → 底部「保存价格」→ `PUT` body 多出 `cache_read_price`；折叠规则 → 组消失且出现设计里 `visible=false` 的「点击展开，配置计费请求规则」；新增规则组 → 标题 `[规则组 #1, 规则组 #2]`；返回 = navigateBack。
  ⑨**回落载体页一并复跑**：`__measure-model-pricing-q9.html`（`?quoteId=q9`，mock `api`）两轮 20/20 字段全等，docH 1540，未受本轮改动影响。
  ⑩**质量门**：`npm test` **1173/1173 · 72 files 连跑两轮**（13:25:19 / 13:25:48）· `type-check` exit 0 · `build:mp-weixin` DONE（wxss 内含 `box-shadow:0 0 0 1px #cbd5e1` / `0 6px 16px rgba(37,99,235,.28)` / `width:18px;height:18px`）· `build:h5` DONE · `review-artifacts` 22/22 · 截图 `logs/screenshots/20260916-序11-模型定价详情-checks轮-h5-430宽.png`。
  ⑪**下轮开工第一件事**：队列 8 的 **序号 12**（`page-12-2`「报价预览与提交 2」→ `/pages/quote-preview/index`，载体页 `__measure-quote-preview.html`，mock 目录 `api-12`）。

### 5.7 本轮（13:15 轮 · 序号 11）新增的工具与口径

- **按页组装 checks 探针**：`python .agents/state/build-probe-11.py`（读 `__measure-profile.html` 的**顶部作用域**（var f/acc/SCENARIO/SHOT_ONLY/NO_ACTION + splitSel）再拼本页 collect/checks/phases）。
  ⚠️ 切片边界必须落在 `function collect(doc, win, withChecks) {` **之前**：若按 `var CARDS = '.card'` 切，会把上一页的 `collect()` 打开却不闭合（build-probe-10.py 之所以能那样切，是因为它的 BODY 接着写 collect 内部）。
  没切干净时 `node --check` 只报 `Unexpected end of input`，用 `js-depth.py` 看大括号净值更直接。
- **红基线不需要 `git stash`**：本轮的红 = 「新探针 + 未修改的源码」（本轮的修复在前，探针在后），直接跑 `review-measure.sh <tag>-red …` 两轮即可；只有「探针先于修复存在」的页面才需要 stash 复现修复前代码。
- ⚠️ **`normShadow()` 的 want 必须写 `rgb(...)`**：Chrome 对 alpha=1 的 box-shadow 颜色序列化成 `rgb(r, g, b)`，探针的 `normColor()` 也按 alpha 感知归一 → 6 条 `*.ring` 检查全假失败（本轮踩到）。
- ⚠️ **list 类 rect 顺序是 DOM 序，不是「视觉行序」**：`.card--price .box--input` 的前三项是「行1 的输入/输出 + 行2 的输入」，按行取要显式用下标 `[0,2,4]`（本轮踩到，误报 1 条）。
- **图标盒口径的判据**：先看设计图层是否给了**声明 width**（给了就按它定盒宽），行框高再由该页实测字形行框（本页 ×1.1）定；`fit_content` 的图标（折叠箭头/删除/加号）则取「所在行的行盒高」上限，**不要**一律套 fontSize×1.5 —— 套错会把卡高/行位整体顶偏（本页可差 5–6px）。
- **本轮新增脚本**：`shot-11.sh`（430×1541 整页截图）· `gen-11-checks-evidence.py`（红/绿转录合成）· `annotate-11-evidence.py`（给红转录补「探针 bug vs 页面缺陷」分诊段）。
"""

with io.open(P, 'w', encoding='utf-8', newline='') as f:
    f.write(txt.rstrip('\r\n') + eol + eol + NOTE.replace('\n', eol))
print('appended, eol=%r' % eol)
