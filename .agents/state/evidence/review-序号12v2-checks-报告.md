# 序号 12-v2「新增报价单-APIKey 下拉展开」载体页「设计期望值 checks」维度复核报告

- 帧引用：**帧名「新增报价单-APIKey下拉展开」+ `layer_id c861ae72-865c-42b6-b314-bef4da1b2277`**（page-apikey；不使用任何位置 id / 自编号）
- 目标路由：`/pages/quote-form/apikey`（台账「目标路由」列为准）
- 页面实现：`src/components/quote-form/QuoteFormView.vue`（与 12-v1/page-26 **共用组件**，帧级差异由 `variantFlags('expanded')` 开关）
- 本轮载体页：`.agents/state/h5-measure/__measure-quote-apikey.html`（**新建**；由 `.agents/state/build-probe-12v2.py`
  从 12-v1 载体页切「顶部作用域 / `collect()` helpers / 溢出统计」三段骨架逐字节复用，只写本帧的 checks / return / phases）
- 本轮时间：2026-09-16 14:2x~14:5x（cron 轮 `aap-tdd-run-20260916-1420`）

---

## 1. 设计帧重抓（人工指令 C：复核前必须重抓并与实现所依据的一份逐字节比对）

| 项 | 值 |
|---|---|
| 重抓命令 | `calicat_source.py page --url https://www.calicat.cn/design/2095515676955668480 --layer-id c861ae72-865c-42b6-b314-bef4da1b2277 --page-id page-apikey` |
| 重抓时间 | 2026-09-16 14:20 |
| `design.json` sha256 | `29a2c80fa606c1453f83a07566f0da1858adf3f636a19edd1caa92c85c604288` |
| 与 `.calicat/raw/pages/page-apikey/design.json` | `cmp` 报 **BYTE-IDENTICAL**（95899 字节） |

→ 画布**当前状态** = 实现所依据的版本，**无漂移**。设计 PNG 实测尺寸 **430×1129**。

---

## 2. TDD 红 → 绿（本轮主交付）

| 阶段 | 命令 | 结果 |
|---|---|---|
| 红基线 | `git stash push -- aap-client/src/components/quote-form/QuoteFormView.vue aap-client/src/utils/quote-form-model.ts` → `npm run build:h5` → `bash .agents/state/review-measure.sh 12-v2-checks-red __measure-quote-apikey.html .agents/state/h5-measure/api-12-v2 5333` | **272 条 · 红 6 条** · docH 1126 · 溢出 0 · 文案缺失 0 |
| 红基线两轮一致性 | `cmp-measure-runs.py … red-run1.json … red-run2.json phase1` | **35/35 字段全等，不一致 0** |
| 绿基线 | `git stash pop` → `npm run build:h5` → `review-measure.sh 12-v2-checks … 5334` | **272 条 · 红 0 条** · docH **1127**（设计帧 1128）· 溢出 0 · 文案缺失 0 |
| 绿基线两轮一致性 | `cmp-measure-runs.py … checks-run1.json … checks-run2.json phase1` | **35/35 字段全等，不一致 0** |

- 红基线口径：**红 = 「最终版探针 + 未修改源码」**（本轮先建探针、后修页面，故无需 `git stash` 的探针时序问题在结尾统一处理：
  为满足「红/绿用同一版探针」，红基线是在源码 stash 后、用**与绿完全相同的探针文件**跑的两轮）。
- `?shot=1` 时 iframe 高 = 设计帧高 1129（截图用，不跳页）。
- 证据：`evidence/review-序号12-v2-checks-run{1,2}.json` · `evidence/review-序号12-v2-checks-red-run{1,2}.json` ·
  `evidence/red-序号12v2-checks-设计期望值偏差.txt` · `evidence/green-序号12v2-checks-设计期望值.txt`

### 红基线 6 条（全部为页面缺陷）

| # | key | got | want | 归因 |
|---|---|---|---|---|
| 1 | `cred.value.color` | `rgb(203,213,225)` | `rgb(148,163,184)` | 展开态占位文案色（设计 324d1612） |
| 2 | `panel.h` | 223 | 226（设计 225.5） | 选项行 54（设计 55）+ 面板用 border 占布局 |
| 3 | `panel.ring` | `none` | `0 0 0 .8px #2563EB, 0 12px 24px rgba(15,23,42,.1)` | 设计 stroke + effects 都没表达 |
| 4 | `row.w` | 352 | 354 | 面板内容宽 = 366 − 2×6（border 挤掉 1.6px） |
| 5 | `panel.actionIcon.w` | 13 | 17 | 设计图层 w17 |
| 6 | `panel.actionIcon.h` | 13 | 22.5 | 图标字形行盒 = 字号 15 × 1.5 |

---

## 3. 修掉的 6 类设计偏差（先红后绿）

1. **展开态占位文案色**：新增 `.select--open .select__value { color: $color-text-placeholder }`（#94A3B8）。
   收起态（page-26）仍是 #CBD5E1 —— **逐帧不同，不统一**，改动加在 `.select--open` 作用域内，不影响 12-v1。
2. **面板描边 `border` → ring + 补设计投影**：`box-shadow: 0 0 0 .8px $color-primary, 0 12px 24px rgba(15,23,42,.1)`
   （设计 `stroke{align:center,thickness:0.8,#2563EB}` + `effects drop_shadow(0,12,24,rgba(15,23,42,0.1))`）。
   与选择框下沿的描边在边界处重合 → 视觉仍是 1 条连续蓝线。
3. **选项行宽 352 → 354、x 39 → 38**（= 366 − 2×6）：Figma 中心描边不占布局，`border` 会占 —— 这是「面板内容宽」的直接证据。
4. **面板底部操作图标盒 13×13 → 17×22.5**（设计图层 w17 fs15）：形状（13px 圆形加号）移入 `::before` / `::after`，
   加号两笔用两层 `linear-gradient` 画，**不新增 DOM 节点**（盒子按设计图层、形状不撑盒子）。
5. **选项行高 54 → 55**：
   - 新增常量 `CRED_SUB_LINE_BOX = 16`（真源：设计三个副行节点 `7a442214` / `40b8ef3a` / `2958b233` **都显式 h16**，
     不是 11px × 1.2 = 13.2）→ 模板里 `panel__sub` 的内联 `lineHeight` 改用它；
   - `.panel__title` line-height 16.8 → **19**（page-apikey 后两行名称节点显式 h19，首行 fit_content 同为 19~20）；
   - 用 13.2 时选项信息 32.2 < 图标盒 34 → 行高被下拉到 54，面板整体短 3px 并把卡1/卡2/底栏一起顶偏。
6. **标签行行盒 17.5 → 17**（两帧共用，`.label__text` / `.label__star`）：PNG 反证 —— page-26 名称框顶 276、page-apikey 195。

**整体效果**：面板 223 → **225**（设计 225.5）· 卡1 628 → **629**（设计 630）· docH 1126 → **1127**（设计 1128）。

---

## 4. 共用组件回归门（同一份 `QuoteFormView.vue` 也服务 12-v1）

| 页面 | 载体页 | 结果 |
|---|---|---|
| 12-v1（page-26 初始态） | `__measure-quote-form.html`（mock `api-12-v1`） | **286 条 · 红 0** · docH **1240**（修前 1241） |
| 12-v2（page-apikey 展开态） | `__measure-quote-apikey.html`（mock `api-12-v2`） | **272 条 · 红 0** · docH 1127 |

12-v1 的 docH 1241 → 1240 是标签行 17.5→17 的**预期结果**（两帧各 −0.5~1，page-26 名称框顶因此精确落回设计值 276）；
1240 与设计帧 1238 的差 = 提示卡文案在设计稿里一行、浏览器 CJK 必然两行的既有残差（+2~2.5，非本轮引入）。

证据：`evidence/review-序号12-v1-recheck-run{1,2}.json`（两轮不一致 0）。

---

## 5. 探针自身的口径 bug（3 条，红基线前已修，不计页面账）

1. `nav.left.gap` 断在 `.nav__titles` 的 `columnGap` —— 组件里**标题块本身就是竖排容器**，
   横排间距在返回按钮与标题块之间 → 改断 `rect('.nav__title').x − rect('.nav__back').right` = 12。
2. `cred.chevron.color` / `empty.glyph.color` 读**元素自身**的 `color` —— 决策 D5 下图标是 CSS 绘制的占位形状，
   设计声明的字形颜色落在 `::before` 的 `border-color` / `background` 上 → 新增 `chkP` / `pseudoStyle` 读伪元素声明值。
3. `row.h` / `panel.h` 的容差：设计帧自身把首行画成选中态（选择框却显示占位「请选择凭证」）→ 不照抄，
   改断「三行都不高亮」，选中态由真实选择驱动（`?scenario=actions` phase3 实测）。

---

## 6. 像素对账（设计 PNG 430×1129 vs 实现 430 宽整页截图）

- 命令：`python .agents/state/cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> evidence/cmp-序号12v2-设计PNGvs实现截图-结构带.txt 3`
- 结果：**命中 54 / 未命中 4**（内容列 x=36..394 → 40/44；条列 x=194..356 → 14/14）；命中处位移中位 0（min −3 max 2）
- 未命中 4 条的分诊（`png-rows.py v 200` 逐行取色，两侧并列比对）：

| 未命中 y | 判读 | 结论 |
|---|---|---|
| 485 | 设计有 #EFF6FF 带 → 首行选中底；实现无（未选凭证） | **设计帧自身矛盾**（已登记 `designLiteralDiff`），非缺陷 |
| 737 | 设计白带 741..747 + 748 起投影；实现 736..746 + 747 起投影 | 卡1 底 748 vs 747 的 **≤1px 小数坐标链**，非缺陷 |
| 766 | 卡2 顶（设计 764 / 实现 763） | 同上，由卡1 −1px 顺延 |
| 1008 | 底栏顶投影起点（设计 1010.4 / 实现 1009） | 同上 |

---

## 7. 交互相有牙齿（两轮，serve 实收请求行逐字节相同）

### `?scenario=actions`（每轮 7 行请求）

| 相 | 实测 |
|---|---|
| phase1 | 首屏仅 `GET /api/v1/credentials?page=1&pageSize=20`（三候选项渲染，零写请求） |
| phase2 | 点 c2 → `GET /api/v1/credentials/c2` → 面板收起 · 值「测试环境密钥」· chip **「已选 1 / 2」** · 2 行模型（gpt-4o / gpt-4o-mini）· 空态消失 · 选择框描边回到 #E2E8F0 |
| phase3 | 重开面板 → 选中行底 `#EFF6FF` + 图标底 `#2563EB` + 对勾 `cred-check-c2`；其余行仍显环境标（`专用`）/ 推荐标（`常用`）；面板 479..704（h 225） |
| phase3b | 再点收起 → 面板 0 · 描边回 #E2E8F0 |
| phase4 | 填名称 → 字数 **12/30**（按真实长度）→ `POST /api/v1/quotes` body `{"name":"2024Q3 主线路报价","credential_id":"c2"}` → `POST /api/v1/quotes/q9/items` body `{"items":[{"model_name":"gpt-4o"}]}` → toast **「保存成功」** → `#/pages/model-pricing/index?quoteId=q9`（落地页渲染） |

### `?scenario=settings`（每轮 2 行请求）

点「前往「我的设置」新建凭证」→ `#/pages/settings/index` **落地并渲染**（标题「账号与设置」，落地页 toast 为空）。

> ⚠️ **台账旧口径改正**：原备注 ③⑦ 写「/pages/settings/index（序号 23）未实现 → H5 实测 hash 不变」——
> 本轮实测该页**已实现且注册在 `pages.json`**。载体页为此拆成 `actions` / `settings` 两个场景
> （原 phase4 落在此帧后会让保存流程 `NOT_FOUND`）；并给 `api-12-v2` 补 `v1/auth/me` fixture
> （落地页 `authApi.me`；缺则落地页弹「数据加载失败」，盖住落点证据）→ `check-mock-fixtures` 新增该条。

---

## 8. 质量门

| 门 | 结果 |
|---|---|
| `npm test` | **1178/1178 · 72 files**，连跑两轮（14:35 / 14:36） |
| `npm run type-check` | exit 0 |
| `npm run build:mp-weixin` | DONE；产物 `pages/quote-form/{index,apikey}.{js,json,wxml}` + `components/quote-form/QuoteFormView.wxss`（含 `box-shadow:0 0 0 .8px #2563eb,0 12px 24px rgba(15,23,42,.1)` · `line-height:19px/17px/16px` · `width:17px;height:22.5px` · `.select--open .select__value{color:#94a3b8}`） |
| `npm run build:h5` | DONE |
| `review-artifacts.py` | **22/22** 台账路由 mp-weixin 三件套齐备且注册（app.json 22 页） |
| `check-mock-fixtures.py --mock api-12-v2` | **7/7 PASS**（+ 反向体检：该 mock 目录所有 fixture 均可按路径取到） |
| 430 宽截图 | `logs/screenshots/20260916-序12v2-新增报价单APIKey下拉展开-checks轮-h5-430宽.png`（430×1129，同件入 `evidence/`） |

---

## 9. designLiteralDiff（设计字面量与实现的有意差异，登记不照抄）

1. 名称框：设计帧为示例填写态「2024Q3 主线路报价」+ 字数「13/30」（实际 12 字，设计自身不自洽）→ 不预填，字数按真实长度 `0/30`。
2. 下拉首行：设计帧把首选项画成选中态（底 #EFF6FF + 对勾），选择框却显示占位「请选择凭证」→ 按真实选择驱动高亮/对勾。
3. 「沙箱」「专用」（环境标）与「常用」（推荐标）在 22 份 PRD 零命中 → 消费服务端 `env_tag` / `is_primary`，缺字段不渲染。
4. 候选项字形占位形状 16×16（设计图层 19×25.5，位于 34×34 盒内）—— D5 维持 CSS 占位，盒子尺寸不影响任何行高（34 盒主导）。

## 10. 残留与阻塞

- 台账序号 12-v2 仍标 `部分`：唯一未决项是**人类拍板「本帧路由是否与 12-v1 合并为同一路由（`?panel=open`）」**（原备注①，本轮不动）。
- 本机未装微信开发者工具：mp-weixin 只做**编译证明**，真机 / 开发者工具验收留给人类（导入 `dist/build/mp-weixin`）。
