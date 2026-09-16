# 序号 12 复核报告 ·【报价管理】报价预览与提交 2（page-12-2）

- 轮次：cron 轮 `aap-tdd-run-20260916-1330`　页面：`/pages/quote-preview/index?quoteId=q7`
- 设计真源：Calicat 文件 `2095515676955668480` · 画布 `2095515676976640000` ·
  帧「12. 报价端·小程序 ｜ 【报价管理】报价预览与提交 2」· layer_id `55b40659-f198-4a04-b36b-ce699c55c75d`
  - 重抓 2026-09-16 13:30：`design.json` sha256 `20f0f3626f5a4d6bd9fd011a88c5e3b8197fdf8f9b995d23ab8e7d42b6b7b610`
    与实现所依据的一份 **逐字节相同**（`cmp` 报 BYTE-IDENTICAL）→ 无漂移
- 载体页：`.agents/state/h5-measure/__measure-quote-preview.html`（由 `build-probe-12.py` 生成：
  从 `__measure-model-pricing.html` 切出「顶部作用域 / collect helpers / 溢出统计」三段骨架逐字节复用，
  只写本页 checks）· mock 目录 `api-12`

## 1. 设计骨架（PNG 实测 + 声明值）

设计帧 430×1027。PNG 量尺命令（仓库根）：

```bash
python .agents/state/stroke-rows.py   .agents/state/design-shots/page-12-2-design.png eef2f7 6 150
python .agents/state/png-colorat.py   .agents/state/design-shots/page-12-2-design.png v 100 f8fafc 3 2
python .agents/state/png-textbands.py .agents/state/design-shots/page-12-2-design.png 46 217 384 261
python .agents/state/png-xruns.py     .agents/state/design-shots/page-12-2-design.png 236 36 394
python .agents/state/png-profile.py   .agents/state/design-shots/page-12-2-design.png 70 217 394 261
```

| 结构 | 设计值 | 依据 |
|---|---|---|
| 顶部导航 | 0..96（padding 48/16/12/16，返回图标盒 26×36 = fs24×1.5） | PNG 白行 1..95 + 页面底 96..107 |
| 卡1 / 卡2 / 卡3 / 确认卡 | 108..380(273) / 392..612(221) / 624..788(165) / 800..926(127) | `stroke-rows` 描边行 392/612/624/788/800/926 + 卡1 下方投影带 381..391 |
| 卡间距 / 内容区 padding | 12 / `12 16 0 16` | design `5320463d` |
| 卡 padding / 圆角 / 底 | 20 / 16 / #FFFFFF | design `39fed800` 等 |
| 卡1 效果 | `drop_shadow(0,6,20,rgba(15,23,42,.06))`，**无描边** | design `39fed800.effects`；PNG x=16 行内无描边像素 |
| 卡2/卡3/确认卡 | `stroke{align:center,thickness:1,#EEF2F7}`，**无投影** | design `e4ab139b`/`4bd8c232`/`a059de31`；PNG 卡下方为纯页面底色 |
| 头行 | 26（标签胶囊 h20 居中 → 128..154） | 卡高算术 + PNG 胶囊行 |
| 基础价行 | **38 = 标签 16 + 值 22**（设计显式 height） | design `6e2f1cb7`/`2fdab0a8`；PNG 标签墨迹 170..179 中心 174.5 = 盒 167..183 中心 |
| 规则行 | 峰谷/阶梯 **44**（内容 24）、请求规则 **40**（内容 20） | PNG `#F8FAFC` 色带 217..260 / 269..312 / **321..360**·501..544 / **553..592**·**729..768** |
| 确认行 | **19**（= fs12 文本行框 19.2） | PNG 确认行 820..838、提示条顶 851 = 800+20+19+12 |
| 提示条 | **56** = 10 + 2×18 + 10（11px 两行，第二行 1~2 字） | PNG `#FFFBEB` 851..906 + 文字带 866..877 / 880..890 |
| 操作条 | 943..1027(84)，容器 padding-top 16 | PNG 白行 + design `8e160a88`/`d7b75749` |

## 2. TDD 红 → 绿

### 2.1 探针（设计期望值 checks）

- 载体页重写为 430 宽 iframe 体例，**126 条 checks**（want = 声明值 + PNG 实测）。
- 红基线（同一份探针跑**修复前源码**，`git stash push -- src/pages/quote-preview/index.vue src/utils/quote-preview-model.ts`
  复现，两轮逐字节相同）：`review-序号12-checks-red-run{1,2}.json` → 转录
  `red-序号12-checks-设计期望值偏差.txt`，**checkFailCount 10/126**：

  | 偏差 | 修复前 | 设计 |
  |---|---|---|
  | `page.card1.shadow` | `rgb(238,242,247) 0 0 0 1px`（四卡统一 ring） | 卡1 `rgba(15,23,42,.06) 0 6px 20px`（无描边） |
  | `price.row.h` / `price.label.h` / `price.label.lh` | 34 / 12 / 12 | 38 / 16 / 16 |
  | `rule.h` / `rule.icon.h` | 六行全 44 / 图标全 24 | 44,44,**40**,44,**40**,**40** / 24,24,**20**,24,**20**,**20** |
  | `rule.text.lh`（紧凑行） | 13.2（外层 24 高居中 → 墨迹 +6.5） | 请求规则行文字带位于行顶 +11 |
  | `confirm.row.h` | 22 | 19 |
  | `hint.h` / `hint.text.lh` | 53 / 16.5 | 56 / 18 |
- 绿基线：`review-序号12-checks-run{1,2}.json` → `green-序号12-checks-设计期望值.txt`：
  **126 条 · 失败 0 · 溢出 0 · 文案缺失 0 · docScrollWidth 430 · docScrollHeight 1027（= 设计帧高）**。
- 两轮独立测量**全等 24/24 字段**（`cmp-measure-runs.py … phase1`，不一致 0）；`git stash pop` + 重建后复跑仍 0
  （`review-序号12-checks-final-run{1,2}.json`）。

### 2.2 单测（先红后绿）

- 新增 `tests/unit/quote-preview-model.spec.ts` 的「规则行 kind」组（3 例）+
  `tests/pages/quote-preview.spec.ts` 的「设计骨架类」组（2 例）。
- 红基线 `red-序号12-checks-结构用例.txt`：**4 failed | 47 passed**（`kind` 未定义 / `.card--lead` 缺失）。
- 实现后全量 `npm test` **1178/1178 · 72 files 连跑两轮**（`green-序号12-checks-全量轮{1,2}.txt`）。

## 3. 本页修掉的 7 类设计偏差（先红后绿）

1. **卡片效果按设计逐卡不同**（原来是四卡统一 ring）：卡1 `box-shadow: 0 6px 20px rgba(15,23,42,.06)`、
   卡2/卡3/确认卡 `0 0 0 1px #EEF2F7`（Figma center 描边不占布局 → ring，`border` 会挤掉内容宽 2px）。
2. **基础价行 34 → 38**：标签盒 12 → **16**（设计显式 height 16）、`line-height` 12 → 16 → 标签墨迹回到设计位置（170..179）。
3. **规则行按类型分行高**：请求规则行 40（内容 20），峰谷/阶梯行 44（内容 24）——模型侧新增 `RuleKind`，
   页面加 `.rule--compact`。
4. **规则行文字行框**：峰谷/阶梯 18（设计墨迹位于行顶 +13）、请求规则 13.2（+11，= 设计声明 lineHeight 1.2）。
5. **`.rule__wrap` 去掉 `min-height:24px` + `align-items:center`**：它把 11px 文字的行框在 24 高盒里居中，
   整行墨迹下沉 3.5px（像素对账抓出；设计该容器是 alignItems=start 的行）。
6. **确认行 22 → 19**（= fs12 文本行框 19.2）：提示条顶回到 851（= 800+20+19+12）。
7. **提示条 53 → 56**：文本行框 16.5 → **18**（设计 11px 行框 18 → 10 + 2×18 + 10 = 56，与 PNG 851..906 一致）。

## 4. 交互（有牙齿）

`?scenario=actions` 两轮逐字节相同（`review-序号12-checks-actions-run{1,2}.json`，
`requests-序号12-checks-actions-run{1,2}.txt` 逐字节相同）：

| 步骤 | 实测 |
|---|---|
| 「返回编辑」 | `CLICKED` · hash 不变（navigateBack 无栈） |
| 取消勾选 | `data-checked` `true` → **false** |
| 未勾选点「提交报价」 | toast **「请先确认报价条款」** · hash 不变 · **无写请求**（请求日志里 POST 只出现 1 次，且在其后） |
| 重新勾选 → 提交 | 真实 **`POST /api/v1/quotes/q7/submit`（body 为空）→ 200** · toast **「已提交审核」** · hash → `#/pages/quotes/index` · 列表渲染 |

纯测量轮两轮各只 **1 行**请求（`GET /api/v1/quotes/q7`）——无多余请求。

**fixture 缺口（先红后绿）**：提交成功后落地 `/pages/quotes/index` 会取 `GET /api/v1/quotes?page=1&pageSize=10`，
`api-12` 里缺该 fixture → 首轮实测 **404** 且落地页弹「数据加载失败，请稍后重试」，把提交成功 toast 盖掉
（证据 `requests-序号12-checks-actions-run1.txt` 旧版第 5 行 404）。补 `api-12/v1/quotes/index`（从 `api` 同款拷贝）后
→ 200、toast 采样点移到跳转前 → 「已提交审核」；`check-mock-fixtures.py --mock api-12` 该条 FAIL → PASS。

## 5. 像素对账（设计 PNG vs 实现 430×1027 截图）

`python .agents/state/cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> <out> [容差 3]`
→ `cmp-序号12-设计PNGvs实现截图-结构带.txt`：**命中 55 / 未命中 3**（修前 52/6）。

- 未命中 `[392, 398]`（内容列）：卡1→卡2 之间的投影带。逐列复核 `scan-col x=20 388..396` **两侧同为
  `rgb(245,247,249)`** → 差异来自「逐行主色」归一化（设计导出图该区主色 254、实现 255）与 Figma/Chrome
  投影衰减步长，**非页面缺陷**（同族于序号 5/6/7 已记录的两类）。
- 未命中 `[1002]`（条列）：提交按钮文案底缘 AA 的 1 行带，设计 maxink 3 / 实现 2（探针 minInk=3 的阈值效应），
  两侧同在第 1002 行出现 → **非页面缺陷**。
- 命中处位移中位 −1（min −2 / max +2），与 Figma 小数坐标链取整 + ring 外置 1px 同族。

## 6. 质量门

| 门 | 结果 |
|---|---|
| `npm test` | **1178/1178 · 72 files 连跑两轮**（13:49 / 13:50） |
| `npm run type-check` | exit 0（`typecheck-序号12-checks.txt`） |
| `npm run build:mp-weixin` | DONE，`pages/quote-preview/{index.js,index.json,index.wxml,index.wxss}`；wxss 含 `.card--lead{box-shadow:0 6px 20px rgba(15,23,42,.06)}` · `.rule--compact{height:40px}` · `height:38px` · `line-height:13.2px` · `min-height:56px` |
| `npm run build:h5` | DONE |
| `review-artifacts.py` | 22/22 路由三件套齐备且注册 |
| `check-mock-fixtures.py --mock api-12` | 本页两条（`GET /quotes/q7`、`POST /quotes/q7/submit`）+ 新增 `GET /quotes` 全 PASS |
| 430 宽截图 | `logs/screenshots/20260916-序12-报价预览与提交-checks轮-h5-430宽.png`（430×1027，同件入本目录） |

## 7. 留证清单

```
.agents/state/evidence/red-序号12-checks-设计期望值偏差.txt        # 探针红基线（两轮相同）
.agents/state/evidence/red-序号12-checks-结构用例.txt              # 单测红基线 4 failed
.agents/state/evidence/green-序号12-checks-设计期望值.txt          # 探针绿基线（126 条 0 失败）
.agents/state/evidence/green-序号12-checks-全量轮{1,2}.txt         # 全量 1178/1178 ×2
.agents/state/evidence/review-序号12-checks{,-red,-final}-run{1,2}.json
.agents/state/evidence/review-序号12-checks-actions-run{1,2}.json  # 交互回放
.agents/state/evidence/requests-序号12-checks{,-actions}-run{1,2}.txt
.agents/state/evidence/cmp-序号12-设计PNGvs实现截图-结构带.txt
.agents/state/evidence/typecheck-序号12-checks.txt
.agents/state/evidence/20260916-序12-报价预览与提交-checks轮-h5-430宽.png
```

## 8. 未决 / 需人类拍板（沿用，不阻塞本轮）

- 台账序号 12 备注 ①②③④⑤⑦⑧⑨⑩⑪⑫⑬⑮ 的推断项不变：接口方法/请求体 schema 为 REST 语义推断、
  标签文案与底色为派生、`/submit` 无请求体 schema（实测 body 为空）、规则行文案为派生、
  提交后跳 `/pages/quotes/index` 为推断、设计自身不自洽处（价行 38 与卡高、卡1 无 stroke）已按**当前帧**落地。
- `?quoteId=` 入参：本页支持 query 优先 + storage `aap_quote_id` 兜底（沿用序号 12 既有口径）。
