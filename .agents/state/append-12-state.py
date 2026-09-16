# -*- coding: utf-8 -*-
"""把序号 12 checks 轮的小结 + §5.8 工具口径追加到状态文件，并在 §4 队列 8 里插入完成行。"""
import io

P = r"E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-tdd-state.md"
with io.open(P, encoding="utf-8", newline="") as fh:
    text = fh.read()

# ---------- 1) §4 队列 8：插到「下一轮：序号 11」那段之后 ----------
anchor = "**下一轮：序号 11**（`page-11`「【报价管理】模型定价-详情」→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`（另有 `?quoteId=` 回落载体页 `__measure-model-pricing-q9.html`），mock 目录 `api-11`）。"
assert anchor in text, "§4 anchor not found"
entry = anchor + """
   - ✅ **序号 12 已完成 2026-09-16 13:5x**（cron 轮 `aap-tdd-run-20260916-1330`）：`__measure-quote-preview.html` 由 241 行旧体例重写为 430 宽 iframe + **126 条 checks**
     （want = `page-12-2` design.tree.json 声明值 + `text-lineheight.py` 全字段 + 设计 PNG 430×1027 色带/描边/墨迹实测）。
     红基线（`git stash` 复现修复前源码 + 同一份探针两轮）**10/126** → 绿 **0/126**；两轮独立测量 **24/24 字段全等**；`docScrollHeight 1027` = 设计帧高；溢出 0 · 文案缺失 0。
     修掉 7 类偏差：①卡片效果**按设计逐卡不同**（卡1 `drop_shadow(0,6,20,.06)` 无描边 / 卡2·卡3·确认卡 `stroke 1px #EEF2F7` 无投影；修前四卡统一 ring）
     ②基础价行 **34→38**（标签盒 12→16、line-height 16 = 设计显式 height 16/22）③规则行**按类型分行高**：请求规则行 **40**（内容 20）、峰谷/阶梯行 **44**（内容 24）
     —— 模型新增 `RuleKind` + 页面 `.rule--compact` ④请求规则行文字行框 **13.2**（设计墨迹位于行顶 +11）、峰谷/阶梯 **18**（+13）
     ⑤`.rule__wrap` 去掉 `min-height:24px` + `align-items:center`（它把 11px 行框在 24 高盒里居中 → 整行墨迹下沉 3.5px，**像素对账抓出**；设计该容器是 `alignItems=start` 的行）
     ⑥确认行 **22→19**（= fs12 行框 19.2；提示条顶回到 851 = 800+20+19+12）⑦提示条 **53→56**（文本行框 16.5→18 = 10+2×18+10）。
     交互相 `?scenario=actions` 两轮逐字节相同：取消勾选 → 提交被门禁拦住（toast「请先确认报价条款」· hash 不变 · **零写请求**）→ 重新勾选 → 真实 `POST /quotes/q7/submit`（body 为空）→ toast「已提交审核」→ `#/pages/quotes/index`。
     **fixture 缺口先红后绿**：落地页会取 `GET /api/v1/quotes?page=1&pageSize=10`（api-12 缺 → 404 且错误 toast 盖掉提交成功 toast）→ 补 `api-12/v1/quotes/index` 后 200。
     像素对账（±3）**命中 55 / 未命中 3**：未命中 = 卡1→卡2 投影带的逐行主色归一化差（`scan-col x=20 388..396` 两侧同为 `rgb(245,247,249)`）+ 提交按钮文案底缘 AA 的 1 行带阈值效应 → 非页面缺陷。
     质量门：`npm test` **1178/1178 · 72 files ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE（wxss 含 `.card--lead` 投影、`.rule--compact{height:40px}`、`height:38px`、`line-height:13.2px`、`min-height:56px`）· `review-artifacts` 22/22 ·
     报告 `evidence/review-序号12-checks-报告.md` · 截图 `logs/screenshots/20260916-序12-报价预览与提交-checks轮-h5-430宽.png`。
     **下一轮开工第一件事**：队列 8 的 **序号 12-v1**（`page-26`「新增报价单-初始态」→ `/pages/quote-form/index`，载体页 `__measure-quote-form.html`，mock 目录 `api-12-v1`）。"""
text = text.replace(anchor, entry, 1)

# ---------- 2) 文件末尾：小结 + §5.8 ----------
tail = text.rstrip() + """

### 5.8 本轮（13:30 轮 · 序号 12）新增的工具与口径

- **文本叶子行高全字段 dump**：`python .agents/state/text-lineheight.py <page-id> [--geom]`
  —— 打印设计树里**每个文本叶子**的 `fontSize / lineHeight / 显式宽高 / 字色 / 文案`（比 `text-fields.py` 多打 lineHeight，判「声明行框」的第一入口）；
  `--geom` 打印每个节点的 x/y/宽高/内边距（实测本页除根帧外 x/y 全为 None → **fit_content 尺寸只能靠 PNG 实测**）。
- **描边行定位（判卡片上下边界的第一工具）**：`python .agents/state/stroke-rows.py <png> <rrggbb> [tol] [mincount] [x0] [x1] [y0] [y1]`
  —— 找出「接近指定色」的横向量 ≥mincount 的行（本页 `eef2f7 6 150` → 卡2 上下 392/612、卡3 624/788、确认卡 800/926，**一次把四张卡的边定死**）。
  比 `png-colorat v 16` 更硬：1px 中心描边在小数坐标下只在圆角附近整行匹配，直线段反而被 AA 摊薄。
- **看文件结构**：`python .agents/state/show-structure.py <relpath>`（`design.tree.json` 是**单个节点 dict** 而不是 `[{id,layer_data}]` —— 直接按 layer_data 遍历会得到 nodes:0）。
- **按页组装 checks 探针**：`python .agents/state/build-probe-12.py`（从 `__measure-model-pricing.html` 切**三段**骨架：顶部作用域 / `collect()` helpers / 溢出统计；
  ⚠️ 溢出统计里引用了 `NEED_TEXT`，必须切在它**之后**并在本页 BODY 里先定义 `var CARDS/NEED_TEXT` 再拼，否则 `NEED_TEXT is not defined`）。
  切片自带 helper 不含 `textColors`（字色版）→ 本页 BODY 里补一个同实现版本（`resolveAll` + `normColor(getComputedStyle(e).color)`）。
- **本页定标（供同族「逐模型价格卡」长页复用）**：顶部导航 96（48 + 图标字形行框 fs24×1.5=36 + 12）· 卡 padding 20 r16 · **头行 26**（标签胶囊 h20 居中）·
  **基础价行 = 标签 16 + 值 22 = 38**（设计显式 height，别用 fontSize 反推）· **规则行 = padding 10 + max(图标盒, 文本行框) + 10**，
  峰谷/阶梯行内容 24（图标盒 fs16×1.5）→ 44、**请求规则行内容 20 → 40**（该行设计图标图层 `width=fit_content`）·
  确认行 = fs12 行框 19.2 · 提示条 = padding 10 + n×18 + 10（11px 文本行框 18）· 操作条 84 = 12 + 48 + 24。
- ⚠️ **卡片效果要逐卡断言**：同一页里卡1 只有 `effects drop_shadow`（无 stroke）、卡2/卡3/确认卡只有 `stroke`（无 effects）→
  探针必须按卡写 want（`chkC('.card@@0','boxShadow',…)`），不能一句「统一 ring」。PNG 佐证法：卡下方若有投影染色（本页 381..391 带 `rgb(240,242,245)`）= 有 effects；
  卡左边缘 x=16 行内若无描边像素 = 无 stroke。
- ⚠️ **`align-items:center` + `min-height` 的组合会静默把文字墨迹整体推低**：本页 `.rule__wrap{min-height:24px;align-items:center}` 让 11px 文字的行框在 24 高盒里居中，
  墨迹下沉 3.5px；**改 line-height 几乎没用**（盒子居中 + 行框内居中的两项互相抵消），必须让容器 `align-items:flex-start` 且高度由内容决定。
  探针只测盒子、量不到这种墨迹偏移，**只能靠像素对账发现**（本页 `cmp-序号12…` 未命中从 6 → 3 就是这一处）。
- ⚠️ **Figma `stroke{align:center}` 落地成 `box-shadow: 0 0 0 1px`（ring）会把可见描边行外移 1px**：设计描边跨边（392/393 两行各半），ring 只占 392 上侧一行；
  像素对账里表现为「设计带起点 392/398 未命中」而 `scan-col` 逐列颜色两侧一致 → 判为投影/AA 类，**不在 1px 上 churn**。
- **提交类交互的 toast 采样点必须在跳转前**（本页 phase3 于点击后 900ms 采样，1.5s 后 uni 会收起 toast；落地页自己的取数 toast 也会覆盖它）。
- **落地页的 fixture 也算本页的测量面**：提交成功 → `/pages/quotes/index` 会取 `GET /api/v1/quotes`，缺 fixture 时落地页弹错误 toast 并让「提交成功」证据失真 → 一并补进该页 mock 目录。
- **本轮新增脚本**：`shot-12.sh`（430×1027 整页截图）· `append-12-note.py`（台账第 12 行回写，走文件避免引号转义问题）。

- 2026-09-16 13:5x（cron 轮 `aap-tdd-run-20260916-1330`）· **队列 8 第 12 页：序号 12「报价预览与提交 2」载体页补「设计期望值 checks」维度（126 条 · 偏差 10→0）+ 7 类设计偏差修复 + 整页对齐设计帧 1027（像素对账 55 命中 / 3 未命中）**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-12-2`（layer_id `55b40659-f198-4a04-b36b-ce699c55c75d`）→ `design.json` sha256 `20f0f362…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-quote-preview.html` 由 241 行旧体例重写为 **430 宽 iframe + 126 条 checks**（构建脚本 `build-probe-12.py`，三段骨架取自 `__measure-model-pricing.html`）；
     红基线（修复前源码 + 同一份探针两轮）**10/126**（`red-序号12-checks-设计期望值偏差.txt`）→ 绿 **0/126**（`green-序号12-checks-设计期望值.txt`）；
     两轮独立测量 **24/24 字段全等**；`docScrollHeight 1027` = 设计帧高；单测红 4 failed → 全量 **1178/1178 ×2**。
  ③**7 类偏差清单**见台账序号 12 行 / 报告 §3：逐卡卡片效果 · 基础价行 34→38（标签 12→16）· 规则行 40/44 分行高（新增 `RuleKind`）·
     请求规则行文字行框 13.2 · `.rule__wrap` 去 `min-height+center`（墨迹 −3.5px）· 确认行 22→19 · 提示条 53→56。
  ④**本页定标**（PNG 实测）：导航 96 · 卡 108/392/624/800（高 273/221/165/127）· 头行 26 · 基础价行 38（声明 16+22）· 规则行 = 10 + max(图标盒, 文本行框) + 10 ·
     **请求规则行内容 20 → 40**（设计该行图标 `width=fit_content`）· 确认行 19.2 · 提示条 10 + n×18 + 10 · 操作条 84。
  ⑤**像素对账**：`cmp-bands-6`（±3）**命中 55 / 未命中 3**（修前 52/6）；未命中 3 条逐条判读 = 卡1→卡2 投影带的逐行主色归一化差（`scan-col x=20 388..396` 两侧同为 `rgb(245,247,249)`）+ 提交按钮文案底缘 AA 的 1 行带阈值效应 → 非页面缺陷。
  ⑥**交互相有牙齿**：`?scenario=actions` 两轮逐字节相同 —— 取消勾选后提交 → toast「请先确认报价条款」· hash 不变 · **零写请求**；重新勾选 → 真实 `POST /api/v1/quotes/q7/submit`（body 为空）→ toast「已提交审核」→ `#/pages/quotes/index`（列表渲染）；
     纯测量轮两轮各只 1 行请求。**fixture 缺口先红后绿**：补 `api-12/v1/quotes/index`（落地页取数，缺则 404 且错误 toast 盖掉提交成功 toast）。
  ⑦**质量门**：`npm test` 1178/1178 ×2 · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含本轮设计值）· `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api-12` 本页三条 PASS。
  ⑧**下轮开工第一件事**：队列 8 的 **序号 12-v1**（`page-26`「新增报价单-初始态」→ `/pages/quote-form/index`，载体页 `__measure-quote-form.html`，mock 目录 `api-12-v1`）。
"""
# 统一行尾为 CRLF（该文件历来是 CRLF；混行尾会让 git 显示整文件改动）
tail = tail.replace("\r\n", "\n").replace("\n", "\r\n")
with io.open(P, "w", encoding="utf-8", newline="") as fh:
    fh.write(tail)
print("state file updated; bytes:", len(tail))
