# -*- coding: utf-8 -*-
"""序号 12-v2 checks 轮的状态文件回写：STATUS 行 / 租约 / §4 队列 8 完成行 / §5.10 工具口径 / 本轮小结。"""
import io

P = r"E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-tdd-state.md"
with io.open(P, encoding="utf-8", newline="") as fh:
    text = fh.read()

# ---------- 1) STATUS 行：12-v2 完成 + 下一轮 12-v3 ----------
old_tail = ("→ 下一轮开工做 序号 12-v2**（`page-apikey`「新增报价单-APIKey下拉展开」→ `/pages/quote-form/apikey`，"
            "载体页 `__measure-quote-form.html` 扩 iframe src 或另立 `__measure-quote-apikey.html`，mock 目录 `api-12-v2`；"
            "⚠️ `src/components/quote-form/QuoteFormView.vue` 是 12-v1/12-v2 **共用组件**，本轮样式改动连带该帧，需按 page-apikey 自己的 PNG 重锚）")
new_tail = ("· **序号 12-v2 已完成 2026-09-16 14:5x（`page-apikey`「新增报价单-APIKey下拉展开」→ `/pages/quote-form/apikey`："
            "新建载体页 `__measure-quote-apikey.html`（430 宽 iframe + **272 条 checks**，由 `build-probe-12v2.py` 切 12-v1 骨架）；"
            "红 6/272 → 绿 **0/272** · 两轮独立测量 35/35 全等 · `docH 1127`（设计帧 1128）· 修 6 类偏差"
            "（展开态文案色 / 面板 border→ring+投影 / 选项行宽 354 / 图标盒 17×22.5 / 选项行高 55（新增 `CRED_SUB_LINE_BOX`）/ 标签行盒 17）· "
            "共用组件回归门 12-v1 复跑 **286 条 0 失败**（docH 1241→1240）· 像素对账 54 命中 / 4 未命中（≤1px 小数坐标链 + 设计帧首行选中矛盾）· "
            "报告 `evidence/review-序号12v2-checks-报告.md`）→ 下一轮开工做 序号 12-v3**（`page-29`「新增报价单-保存成功」→ `/pages/quote-form/success`，"
            "载体页 `__measure-quote-success.html`，mock 目录 `api-12-v3`；⚠️ 与 12-v1/12-v2 共用 `src/components/quote-form/QuoteFormView.vue` 的保存流程，"
            "改动后必须同时复跑 `__measure-quote-apikey.html` 与 `__measure-quote-form.html` 两个载体页）")
assert old_tail in text, "STATUS tail not found"
text = text.replace(old_tail, new_tail, 1)

# ---------- 2) 租约释放 ----------
import re
text2 = re.sub(r"LEASE: aap-tdd-run-\S+ until \S+", "LEASE: free until -", text)
assert text2 != text, "LEASE line not found"
text = text2

# ---------- 3) §4 队列 8：插入 12-v2 完成行 ----------
anchor9 = "9. **决策台账 `aap-decisions.md` 的待执行项优先于本队列**"
assert anchor9 in text, "§4 anchor 9 not found"
entry = """   - ✅ **序号 12-v2 已完成 2026-09-16 14:5x**（cron 轮 `aap-tdd-run-20260916-1420`）：**新建**载体页 `__measure-quote-apikey.html`
     （430 宽 iframe + **272 条设计期望值 checks**；由 `build-probe-12v2.py` 从 12-v1 载体页切「顶部作用域 / `collect()` helpers / 溢出统计」三段骨架复用）。
     红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**6/272** → 绿 **0/272**；两轮独立测量 **35/35 字段全等**；
     `docScrollHeight 1127`（设计帧 1128）· 溢出 0 · 文案缺失 0 · 共用组件回归门 12-v1 复跑 **286 条 0 失败**。
     修 6 类偏差：展开态占位色 #CBD5E1→**#94A3B8**（逐帧不同，加 `.select--open` 作用域）· 面板 `border`→**ring + 设计投影**
     `0 0 0 .8px #2563EB, 0 12px 24px rgba(15,23,42,.1)` · 选项行宽 **354**（x 38）· 图标盒 13×13→**17×22.5**（形状入 `::before/::after`）·
     选项行高 **55**（新增 `CRED_SUB_LINE_BOX = 16`：设计三个副行节点都显式 h16，不是 13.2）· 标签行盒 17.5→**17**（两帧共用）。
     像素对账 `evidence/cmp-序号12v2-设计PNGvs实现截图-结构带.txt` 命中 **54 / 未命中 4**（y=485 设计帧首行选中矛盾 + y=737/766/1008 的 ≤1px 小数坐标链，非页面缺陷）。
     交互相三场景两轮逐字节相同：`?scenario=actions`（7 行：选 c2 → 重开验选中态 → 收起 → 保存 → 模型定价落地）·
     `?scenario=settings`（2 行：**/pages/settings/index 已实现并渲染**，改正旧台账「未实现 → hash 不变」口径）· 纯测量轮 1 行。
     质量门：`npm test` 1178/1178 ×2 · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · `review-artifacts` 22/22 ·
     `check-mock-fixtures --mock api-12-v2` **7/7 PASS**（本轮新增 6 条 + `v1/auth/me` fixture）。
     **下一轮开工第一件事**：队列 8 的 **序号 12-v3**（`page-29`「新增报价单-保存成功」→ `/pages/quote-form/success`，
     载体页 `__measure-quote-success.html`，mock 目录 `api-12-v3`），做完再依次收尾 **15 / 20 / 21 / 22 / 23** 五页（队列 8 剩余）。
"""
text = text.replace(anchor9, entry + anchor9, 1)

# ---------- 4) 末尾：§5.10 + 本轮小结 ----------
text = text.rstrip() + """

### 5.10 本轮（14:20 轮 · 序号 12-v2）新增的工具与口径

- **按页组装 checks 探针（第三例）**：`python .agents/state/build-probe-12v2.py`
  —— 从 `__measure-quote-form.html`（**同一页/同一共用组件**的 12-v1 载体页）切三段骨架
  （`var f = …` 顶部作用域 / `function collect(doc, win, withChecks) {` … `/* ============ 溢出` helpers / 溢出统计），逐字节复用；
  ⚠️ 三段切片的边界：`i_checks` 必须用 `/* ===================== 整页` 这类**不带半角括号的锚**（原文件的注释是全角括号 `（设计帧 …）`）。
- ⚠️ **D5 下「字形颜色」不在元素的 `color` 上**：图标一律是 CSS 占位形状，颜色落在 `::before` 的 `border-color` / `background`。
  探针直接 `getComputedStyle(el).color` 会得到 `rgb(0, 0, 0)` → 误判成页面缺陷（本轮踩到 2 条）。
  正解：`getComputedStyle(el, '::before')[prop]`，本页封装成 `pseudoStyle()` / `chkP()`。
- ⚠️ **断「容器 gap」前先确认那个容器真的是横排组**：组件里 `.nav__titles` 是**竖排**的标题块（组件把返回按钮与标题块并排，
  没有单独的「左侧组」节点）→ 断 `columnGap` 永远得 `normal`。横排间距改为断「后者的 x − 前者的 right」。
- ⚠️ **同一页里同字号文本可以有两套行盒，且「设计显式 height」优先于任何倍数**：page-apikey 的三个选项副行节点都显式 h16
  （同页 11px 另有走 1.2 的 13.2）；用 13.2 时选项信息 32.2 < 图标盒 34 → 行高被图标盒接管 → 每行 54（设计 55）、面板短 3px。
  **做法**：给这类「显式 height」建常量（本页 `CRED_SUB_LINE_BOX = 16`）并把它绑到模板的内联 `lineHeight` 上
  —— 只改 CSS 类会被内联样式覆盖（本轮先踩到）。判据链：PNG 逐行取色定出「盒边界」→ 反推行盒 → 再写进常量注释。
- ⚠️ **面板/卡片这类「整块由若干行拼成」的盒子，容差要能抓住 1 行高差**：`panel.h` 的 want 226（设计 225.5）配 tol 2，
  才能在「选项行 54」时红；tol 3 会静默放过（本轮把 tol 从 3 收到 2 后才成为有效断言）。
- **落地页在别轮被实现后，旧备注会变成假口径**：本页原备注写「/pages/settings/index（序号 23）未实现 → hash 不变」，
  本轮实测该页**已实现且注册在 pages.json**。复核任何「落点 hash 不变」的旧结论前，先查 `src/pages.json` 与产物；
  载体页的相序也要随之拆开（一个相里既跳走又想继续点原页元素 = 后续相全 `NOT_FOUND`）。
  本轮拆成 `?scenario=actions`（线性到底）与 `?scenario=settings`（落点核对）两个场景，各自两轮取证。
- **本轮新增脚本**：`shot-12v2.sh`（430×1129 整页截图）· `gen-12v2-checks-evidence.py`（红/绿/交互/落点四段转录合成）·
  `append-12v2-note.py`（台账第 12-v2 行回写）· `append-12v2-state.py`（本文件回写）· `show-ledger-cols.py`（写回前核列位）·
  `list-not-verified.py`（按状态列列未完成行）· `show-ledger-cols.py`。

- 2026-09-16 14:5x（cron 轮 `aap-tdd-run-20260916-1420`）· **队列 8 第 14 页：序号 12-v2「新增报价单-APIKey 下拉展开」载体页补「设计期望值 checks」维度（272 条 · 偏差 6→0）+ 6 类设计偏差修复（展开态文案色 / 面板 ring+投影 / 选项行宽 354 / 图标盒 17×22.5 / 选项行高 55 / 标签行盒 17）**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-apikey`（layer_id `c861ae72-865c-42b6-b314-bef4da1b2277`）→ `design.json` sha256 `29a2c80f…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ②**TDD 红→绿（本轮主交付）**：**新建** `__measure-quote-apikey.html`（430 宽 iframe + 272 条 checks，构建脚本 `build-probe-12v2.py` 切 12-v1 骨架）；
  红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**6/272** · `docH 1126` → 绿 **0/272** · `docH 1127`（设计 1128）；两轮独立测量 **35/35 字段全等**；`git stash pop` 后重建复跑同值。
  ③**修 6 类偏差**（清单见台账序号 12-v2 行 / `evidence/review-序号12v2-checks-报告.md` §3）：展开态占位文案色 #CBD5E1→#94A3B8（加 `.select--open` 作用域，不动 12-v1）·
  面板描边 `border`→ring 并补设计 effects `0 0 0 .8px #2563EB, 0 12px 24px rgba(15,23,42,.1)` · 选项行宽 352→354（x 38）·
  图标盒 13×13→17×22.5（形状入 ::before/::after，加号两笔用两层渐变）· 选项行高 54→55（新增 `CRED_SUB_LINE_BOX = 16` + `.panel__title` line-height 19）· 标签行盒 17.5→17（两帧共用）。
  ④**本页定标**：面板 = 6 + 3×选项行 55 + (4+1 分隔线) + (4 + 8+22.5+8 底部操作) + 6 ≈ 225.5；选项行 = 10 + max(图标盒 34, 名称行 19 + 副行 16) + 10；
  卡1 = 118..748（630）· 卡2 = 764..990.4（226.4 = 16+20+16+158.4+16）· 底栏 1010.4..1128（117.5）· 页高 1128（PNG 1129 行）。
  ⑤**共用组件回归门**：12-v1 同帧（`__measure-quote-form.html`）复跑 **286 条 0 失败**，`docH 1241→1240`（标签行 17.5→17 的预期结果；与设计 1238 的差仍是提示卡 CJK 换行的既有残差）。
  ⑥**交互相有牙齿（三场景）**：`?scenario=actions` 两轮 7 行请求逐字节相同（选 c2 → 重开验选中行 #EFF6FF + 对勾 `cred-check-c2` → 收起 → 名称 12/30 → 真实 `POST /quotes{name,credential_id}` + `POST /quotes/q9/items` → toast「保存成功」→ `#/pages/model-pricing/index?quoteId=q9` 落地页渲染）；
  `?scenario=settings` 两轮 2 行 → **`#/pages/settings/index` 已实现并渲染**（标题「账号与设置」）；纯测量轮 1 行（仅首屏 `GET /credentials`）。
  **旧台账口径改正**：原备注③⑦的「序号 23 未实现 → hash 不变」作废；并给 `api-12-v2` 补 `v1/auth/me` fixture（否则落地页弹「数据加载失败」盖住落点证据）。
  ⑦**质量门**：`npm test` **1178/1178 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（组件 wxss 含本轮设计值）· `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api-12-v2` **7/7 PASS**；
  像素对账 **54 命中 / 4 未命中**（判读见表）· 截图 `logs/screenshots/20260916-序12v2-新增报价单APIKey下拉展开-checks轮-h5-430宽.png`（430×1129）。
  ⑧**探针自身 3 处口径 bug** 已修（见 §5.10）：nav.left.gap 断错容器 · 字形颜色读元素 `color`（D5 占位形状）· 面板首行选中态属设计帧矛盾。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 12-v3**（`page-29`「新增报价单-保存成功」→ `/pages/quote-form/success`，载体页 `__measure-quote-success.html`，mock `api-12-v3`）；其后 15 / 20 / 21 / 22 / 23。
"""

with io.open(P, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)
print("state file updated:", len(text), "chars")
