# -*- coding: utf-8 -*-
"""状态文件回写：序号 12-v3 checks 轮完成（第 1 行在办项 + LEASE free + §4 队列 8 追加 + 本轮小结 + §5.11 工具口径）。

用法: python .agents/state/append-12v3-state.py
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(ROOT, '.agents/state/aap-tdd-state.md')

with io.open(P, encoding='utf-8', newline='') as fh:
    raw = fh.read()

nl = '\r\n' if '\r\n' in raw else '\n'
text = raw.replace('\r\n', '\n')
lines = text.split('\n')

# ---------- 1) 第 1 行：追加 12-v3 完成句 + 把「下一轮开工做」指向 序号 15 ----------
l1 = lines[0]
a = l1.find('→ 下一轮开工做 序号 12-v3')
b = l1.find('两个载体页）', a)
assert a > 0 and b > a, '第 1 行锚点未找到（在办项写法变了？）'
b += len('两个载体页）')

done_12v3 = (
    '✅ **序号 12-v3 已完成 2026-09-16 15:0x（`page-29`「新增报价单-保存成功」→ `/pages/quote-form/success`：'
    '新建载体页 `__measure-quote-success.html`（430 宽 iframe + **259 条 checks**，构建脚本 `build-probe-12v3.py`）；'
    '红基线 30/259（git stash 复现修复前源码 + 同一份最终版探针两轮）→ 绿 **0/259** · 两轮独立测量 31/31 全等 · '
    '`docH 1018` = 设计帧高 · 溢出 0 · 文案缺失 0 · 像素对账 **50 命中 / 0 未命中**（首个零未命中页）· '
    '修 4 类偏差（5 处 effects 投影 / 8 个图标占位盒按设计图层 / 单号行右侧组 gap 8→4 / 提示卡文案单行）· '
    '四出口交互两轮逐字节相同（copy 剪贴板 + toast · primary → model-pricing?quoteId=q9 · secondary/close → quotes/index）· '
    'fixture 缺口先红后绿（补 api-12-v3 两个落地页 fixture，`check-mock-fixtures --mock api-12-v3` 5 PASS / FAIL 0）· '
    '共用组件回归门 12-v1 286/0 · 12-v2 272/0）**'
)
next_ptr = (
    '→ 下一轮开工做 序号 15**（`page-15-2`「【合同与通知】合同签署 2」→ `/pages/contract/index`，'
    '载体页 `__measure-contract.html`，mock 目录 `api-15`）'
)
lines[0] = l1[:a] + done_12v3 + ' ' + next_ptr + l1[b:]

# ---------- 2) LEASE 行 -> free ----------
for i, ln in enumerate(lines[:4]):
    if ln.startswith('LEASE:'):
        lines[i] = 'LEASE: free until -'
        break
else:
    raise SystemExit('LEASE 行未找到')

text = '\n'.join(lines)

# ---------- 3) §4 队列 8：12-v2 条目后追加 12-v3 条目 ----------
anchor = '   - ⚠️ 本轮踩到并写进 §5 的坑：重抓前必须先确认 Calicat 编辑器在浏览器里打开'
assert anchor in text, '§4 队列 8 锚点未找到'
entry = (
    '   - ✅ **序号 12-v3 已完成 2026-09-16 15:0x**（cron 轮 `aap-tdd-run-20260916-1445`）：'
    '**新建**载体页 `__measure-quote-success.html`（430 宽 iframe + **259 条设计期望值 checks**，'
    '构建脚本 `build-probe-12v3.py` 切 12-v2 骨架）。红基线（`git stash push -- aap-client/src/pages/quote-form/success.vue` '
    '复现修复前源码 + **同一份最终版探针**两轮）**30/259** · `docH 1018` → 绿 **0/259** · `docH 1018`（= 设计帧高）；'
    '两轮独立测量 **31/31 字段全等**（`cmp-measure-runs … phase1` 不一致 0）。\n'
    '     修 **4 类偏差**（清单见台账序号 12-v3 行 用例(证据) 列 / `evidence/red-序号12v3-checks-设计期望值偏差.txt`）：\n'
    '     ①**5 处 effects 投影**（三张卡 `drop_shadow(0,4,16,rgba(15,23,42,.06))` · 底栏 `(0,-4,16,.05)` · 主按钮 `(0,6,16,rgba(37,99,235,.28))`）；\n'
    '     ②**8 个图标占位盒按设计图层**（盒 = 声明宽 × 字号×1.5 → 20×27 / 20×27 / 41×57 / 16×21 / 15×19.5 / 18×24 / 18×24 / 20×27，形状入 `::before`，颜色改由伪元素声明）；\n'
    '     ③**单号行右侧组 gap 8→4**（设计「单号值行」55b312e3 gap=4，与密钥行「密钥信息」gap=8 不同）；\n'
    '     ④提示卡文案按单行渲染（行盒 13.2；卡高 48 由图标行盒 24 决定 —— 旧注释「文案两行 26.4」作废）。\n'
    '     **像素对账 `cmp-bands-6`（±3）：内容列 35/35 + 条列 15/15 = 50 命中 / 0 未命中**（`evidence/cmp-序号12v3-设计PNGvs实现截图-结构带.txt`）。\n'
    '     **交互相有牙齿（四出口，各两轮逐字节相同）**：`?scenario=copy` 剪贴板写 `QT-20240615-0007` + toast「报价单号已复制」· hash 不变 · 零写请求；\n'
    '     `?scenario=primary` → `#/pages/model-pricing/index?quoteId=q9`（渲染「模型定价」）；`?scenario=secondary` / `?scenario=close` → `#/pages/quotes/index`（5 张卡片）；\n'
    '     每轮 serve 实收 2~3 行 **全为只读 GET**。**fixture 缺口先红后绿**：两个落地页 fixture 缺失（404 + 错误 toast）→ 补 `api-12-v3/v1/quotes/q9/items/index`（同 12-v1）与 `api-12-v3/v1/quotes/index`（同 12）→ 200 且 toast 空，`check-mock-fixtures --mock api-12-v3` **5 PASS / FAIL 0**。\n'
    '     质量门：`npm test` **1178/1178 ×2** · `type-check` exit 0 · `build:mp-weixin` DONE · `build:h5` DONE · `review-artifacts` 22/22 ·\n'
    '     **共用组件回归门**（本页无共用组件，仍复跑兄弟载体页）：12-v1 **286 条 0 失败** · 12-v2 **272 条 0 失败** ·\n'
    '     截图 `evidence/20260916-序12v3-新增报价单保存成功-checks轮-h5-430宽.png`（430×1018 = 设计尺寸）。\n'
    '     **下轮开工第一件事**：队列 8 的 **序号 15**（`page-15-2`「【合同与通知】合同签署 2」→ `/pages/contract/index`，载体页 `__measure-contract.html`，mock 目录 `api-15`）。\n'
)
text = text.replace(anchor, entry + anchor, 1)

# ---------- 4) 本轮小结 ----------
summary = (
    '\n- 2026-09-16 15:0x（cron 轮 `aap-tdd-run-20260916-1445`）· **队列 8 第 15 页：序号 12-v3「新增报价单-保存成功」'
    '载体页补「设计期望值 checks」维度（259 条 · 偏差 30→0）+ 4 类设计偏差修复 + 像素对账首个零未命中（50/50）**：\n'
    '  ①**设计帧重抓（人工指令 C）**：帧「新增报价单-保存成功」+ layer_id `49d2fa52-959d-4415-9fda-edf38415d6bd` 重抓 →\n'
    '     `design.json` sha256 `cdd34a51…` **逐字节相同**（无漂移）。\n'
    '  ②**TDD 红→绿（本轮主交付）**：**新建**载体页 `__measure-quote-success.html`（430 宽 iframe + **259 条 checks**；`build-probe-12v3.py` 切 12-v2 骨架，新增 `dump-layout.py` 全字段 dump 出 want）；\n'
    '     红基线（`git stash push -- aap-client/src/pages/quote-form/success.vue` 复现修复前源码 + **同一份最终版探针**两轮）**30/259** → 绿 **0/259**；\n'
    '     两轮独立测量 **31/31 字段全等**；`docScrollHeight 1018` = 设计帧高 · 溢出 0 · 文案缺失 0。\n'
    '  ③**修 4 类偏差**：5 处 effects 投影（三卡/底栏/主按钮）· 8 个图标占位盒按设计图层（盒 = 声明宽 × 字号×1.5，形状入 `::before`，颜色改判伪元素）·\n'
    '     单号行右侧组 gap 8→4 · 提示卡文案单行（旧注释「两行 26.4」作废）。\n'
    '  ④**像素对账 50 命中 / 0 未命中**（`evidence/cmp-序号12v3-设计PNGvs实现截图-结构带.txt`）—— 本循环首个零未命中页：\n'
    '     本页几何（1018）本来已对齐，本轮修的都是盒内效果/图标盒，且该页无 CJK 换行残差。\n'
    '  ⑤**交互四出口两轮逐字节相同**（copy / primary / secondary / close）+ **fixture 缺口先红后绿**（补 api-12-v3 两个落地页 fixture，5 PASS / FAIL 0）。\n'
    '  ⑥**质量门**：`npm test` **1178/1178 ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · `review-artifacts` 22/22 ·\n'
    '     共用组件回归门（12-v1 286/0 · 12-v2 272/0）· 截图 `evidence/20260916-序12v3-新增报价单保存成功-checks轮-h5-430宽.png`。\n'
    '  ⑦**下轮开工第一件事**：队列 8 的 **序号 15**（`page-15-2`「合同签署 2」→ `/pages/contract/index`，载体页 `__measure-contract.html`，mock 目录 `api-15`）。\n'
)
marker = '\n## 5. 关键命令（照抄可用）'
assert marker in text
text = text.replace(marker, summary + marker, 1)

# ---------- 5) §5.11 工具与口径 ----------
sec = (
    '### 5.11 本轮（14:45 轮 · 序号 12-v3）新增的工具与口径\n\n'
    '- **设计节点全字段 dump**：`python .agents/state/dump-layout.py <page-id> [--match 子串] [--depth N]`\n'
    '  —— 打印全树每节点的 layout/`gap`/padding/宽高/圆角/fills/stroke/**effects**/fontSize/fontFamily/**lineHeight**/文案；\n'
    '  `tree-view.py` **不打印 `gap` 与 `lineHeight`**（本页要断「顶部左侧 gap12」「密钥行 gap8 vs 单号行 gap4」「11px 行盒」就靠它）。\n'
    '- **按页组装 checks 探针（第四例）**：`python .agents/state/build-probe-12v3.py`（从 `__measure-quote-apikey.html` 切四段骨架：\n'
    '  顶部作用域 / `collect()` helpers / 溢出统计 / `sink+phase+点击工具`）。\n'
    '  ⚠️ 溢出统计的切片终点必须是 `find("/* ===================== 整页", i_over)` —— 用 `function sink(` 当终点会把上一页的 checks + return 一并切进来。\n'
    '  ⚠️ 本页 NEED_TEXT/CARDS 必须写在**溢出统计之前**（切片顺序：top + preamble + 本页 PRELUDE + overflow + 本页 CHECKS + return + tail + main）。\n'
    '- ⚠️ **载体页里不要放可见的说明元素**（本轮首版加了一个 `#note` div，整页截图被它整体下移 ~20px，像素对账 40 条假未命中）；\n'
    '  说明一律写进 HTML 注释。判据：实现截图的带起点列表比设计整体偏一个常量 → 先查 iframe 之前有没有渲染元素。\n'
    '- ⚠️ **`show-checks.py` 只认扁平单段文件**；多相（phase1..N）载体页要用 `show-phases.py <run.json> [out.txt]`（本轮踩到：show-checks 报 `checkCount=None`）。\n'
    '- ⚠️ **`review-measure.sh` 的 requests 证据偶发 0 行**（serve 日志在 kill 前未刷新完）→ 该轮重跑一次；两轮必须 `diff` 逐字节相同才算证据。\n'
    '- **本页定标（供同族「成功/结果页」复用）**：图标字形行盒 = 字号 × 1.5（三条交叉验证：单号行 fs13→19.5 使卡2 恰 249.5 ·\n'
    '  卡3 标题行 fs16→24 使卡3 恰 132 · 提示卡 fs16→24 使提示卡恰 48）；13px 文本行盒 18（卡2 五行算术自洽）；\n'
    '  15px 标题行盒 20（卡2 高 249.5 反推）；11px 走显式 height（单号标签 15）或 13.2（提示卡文案，单行）；\n'
    '  三张卡 effects 同值且**无 stroke** → 只能 `box-shadow`；**同一页里两处相邻元素间距可以不同**（密钥信息 gap8 / 单号值行 gap4）—— 探针要分别断言。\n'
    '- **本轮新增脚本**：`dump-layout.py` · `build-probe-12v3.py` · `shot-12v3.sh`（430×1018 整页截图）· `gen-12v3-checks-evidence.py`（红/绿/四出口/请求行合成）·\n'
    '  `append-12v3-checks-note.py`（台账回写）· `append-12v3-state.py`（本文件回写）。\n'
)
text = text.rstrip('\n') + '\n\n' + sec

with io.open(P, 'w', encoding='utf-8', newline='') as fh:
    fh.write(text.replace('\n', nl))
print('state file updated; lines:', len(text.split('\n')))
