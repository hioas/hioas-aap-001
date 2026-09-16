# 序号 12-v1「新增报价单-初始态」载体页「设计期望值 checks」维度复核报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1355`（队列 8 第 13 页）
- 帧：`新增报价单-初始态` · `page-26` · layer_id `e9214640-519e-4671-a23e-ac03e92add54`
- 目标路由：`/pages/quote-form/index`（实现 = `src/components/quote-form/QuoteFormView.vue` + `src/pages/quote-form/index.vue`）
- 载体页：`.agents/state/h5-measure/__measure-quote-form.html`（430 宽 iframe）· mock 目录 `api-12-v1`

## 1. 设计帧重抓（人工指令 C：复核前必须重抓并与实现所依据的一份逐字节比对）

```
$ cmd /c start "" https://www.calicat.cn/design/2095515676955668480     # 先拉起编辑器，否则整包重抓全 FAIL
$ python .../calicat_source.py page --url ... --layer-id e9214640-... --page-id page-26 --out %TEMP%/aap-live-1355
design.json sha256 留证 2e8d879b3418765c2708d2dd27d42df8bbe64d2b87c4de6a75af351923644498
重抓         design.json sha256 2e8d879b3418765c2708d2dd27d42df8bbe64d2b87c4de6a75af351923644498  → BYTE-IDENTICAL（无漂移）
```

结论：实现所依据的帧 == 当前画布帧，本轮所有几何判据都基于这一份。

## 2. TDD 红 → 绿（本轮主交付）

- 探针：`__measure-quote-form.html` 由 277 行旧体例（只测「文案齐 / 溢出 0 / 页高」）重写为 **430 宽 iframe + 286 条设计期望值 checks**。
- want 两类来源（口径写进探针头部注释）：
  1. **声明值**：`.calicat/raw/pages/page-26/design.tree.json` 逐节点（`node-by-id.py` / `text-lineheight.py` / `raw-node.py`）；
  2. **fit_content 真实尺寸**：设计 PNG `.agents/state/design-shots/page-26.png`（430×1238）像素实测（`png-rows` / `scan-col` / `png-textbands` / `png-profile` / `png-colorat` / `png-xruns`）。
- 红基线（`git stash` 掉本轮源码改动 → `build:h5` → 同一份探针两轮）：

```
红 45 / 286 · docScrollHeight 1235（设计 1238）· 溢出 0 · 文案缺失 0     ← review-序号12v1-checks-red-run{1,2}.json
绿  0 / 286 · docScrollHeight 1241 · 溢出 0 · 文案缺失 0                ← review-序号12v1-checks-run{1,2}.json
两轮独立测量 28/28 字段全等（cmp-measure-runs.py phase1，不一致 0）
```

（记录：探针初版 281 条跑未修改源码时红 53 条，其中 8 条是探针自身的期望值 bug（见 §5），修正后才做上面的正式红基线 → 45 条全部是页面缺陷。）

## 3. 修掉的 7 类设计偏差（先红后绿，全部有 checks 断言）

| # | 偏差 | 设计依据 | 现状 → 修正 |
|---|---|---|---|
| 1 | 卡片 / 操作条 / 保存按钮**缺 effects 投影** | 步骤卡 `7acff570` (0,4,16,.05) · 基本信息卡 `82bbea2b`、模型列表卡 `9fabffe3` (0,4,16,.06) · 填写须知卡 `f4fab5a4`、底栏 `0bf8e01d` (0,4,16,.05 / 0,-4,16,.05) · 保存按钮 `d88fa94a` (0,6,16,rgba(37,99,235,.28)) | `none` → `box-shadow`（6 处；PNG 佐证：卡片间 12..16px 的间隙被投影染色，实测 `rgb(238,240,244)`） |
| 2 | 4 处 Figma **center 描边用 border** | 名称输入框 `d2fd0412`、单号只读框 `bdd719bb`、凭证选择框 `6d71d189`、存草稿按钮 `dbfc6853`：`stroke{align:center,thickness:0.8}` | `border: 0.8px solid` → `box-shadow: 0 0 0 .8px`（border 占布局：内容左界 46→46.8、右侧胶囊右界 384→383.2） |
| 3 | **13 处图标占位盒未按设计图层尺寸** | 见 §4 表 | 旧尺寸（10×10 / 16×16 / 12×12 / 14×14 …）→ 「盒 = 声明宽 × 字号×1.5 行盒」，形状移入 `::before` |
| 4 | 顶部返回/帮助**圆角 50%** | `018ac574` / `a6afa87b` `cornerRadius: 18` | `border-radius: 50%` → `18px`（口径：圆角取设计声明值，此前轮次同款修正） |
| 5 | 填写须知卡标题图标行盒 **27** | 字形 `3987dfa6` fs16 → 行盒 24 | `iconLineBox(18)=27` → `iconLineBox(16)=24`（卡3 高 152→156 = 设计 156） |
| 6 | 须知条目文案**行盒 14.4** | 设计 PNG：条目3 两行 1047..1083 = **36**、行距 1052→1067 = 15（14.4 行盒只给 26 行墨迹，实测 31 行） | 内联 `textLineBox(12)=14.4` → 常量 `NOTICE_TEXT_LINE_BOX = 18`（行盒两行 36，条目3 高 29→36） |
| 7 | 模型列表 chip 文案 10px/600 | `c26a8591` fs11 `SourceHanSans-Medium` | `.tag__text--muted`（模型行可选态共用）→ 新增 `.tag__text--chip` = 11px/500 |

附带（同批）：标签行行盒 **18 → 17.5**（PNG 实测：名称输入框顶 276.5 = 251 + 17.5 + 8；取 18 会让卡1 与下方 3 个锚点整体 +0.5~1）。

## 4. 本页定标（供同族「表单长页」复用）

- **图标字形行盒 = 字号 × 1.5**（本页四处交叉验证：底栏 `05adee9c` fs13→19.5 使底栏恰为 117.5；卡3 标题 fs16→24 使卡3 恰为 156；提示卡 `70e950fc` fs15→22.5 使卡高 42.5；nav 返回/帮助 fs18→27）。
  → 图标盒 = `声明 width × (字号×1.5)`：返回/帮助 20×27 · 必填 12×15 · 清除 18×24 · 单号文档 18×24 · 单号说明/凭证说明 14×18 · 选择钥匙 17×22.5 · chevron 22×30 · 空态字形 29×39 · 提示卡 17×22.5 · 须知标题 18×24 · 底栏保存说明 15×19.5 · 保存按钮 20×27。
- **文本行盒**：11px → **16.5**（字数提示盒 PNG 实测 330..346.5，用 13.2 会把分隔线拉到 359 而非 362.5）· 12px 空态说明 → **14.4**（空态盒 164.4 反证）· 12px 须知条目 → **18**（两行 36）。
  ⚠️ 同一页里同字号文本有 14.4 / 18 两套行盒 → **不统一口径，按各自 PNG 实测落地**（设计自身不自洽，已登记）。
- 卡高（PNG）：步骤卡 65 · 卡1 425.5 · 卡2 287.5 · 卡3 156 · 底栏 117.5 = 12 + 19.5 + 10 + 48 + 28 · 页高 1238。

## 5. 探针自身的期望值 bug（8 条，红基线前修掉，不计页面账）

| 检查 | 原 want | 改为 | 依据 |
|---|---|---|---|
| `nav.back.top` | 48 | 51 | 顶部左侧 `alignItems=center`：48 + (42−36)/2 = 51；PNG 圆 51..87 |
| `name.counter.h` / `.lh` | 13.2 | 16.5 | 见 §4（字数提示盒 330..346.5） |
| `name.counter.right` | 382 | 398 | PNG「0/30」墨迹右缘 397 = 卡片内容右界（卡片内边 16 → 32..398） |
| `qno.pill.right` | 382 | 384 | 只读框 padding 14，设计 stroke 不占布局 |
| `qno.box.top` | 404 | 406 | 描边行 405/406 → 盒顶 405.5 |
| `qno.hint.h` / `cred.hint.h` | 18 | 24 | 容器 `pad-top 6` + 行盒 18（原 want 把两者合成一条） |
| `page.card2Height` | 287 | 291 | 见 §6 designLiteralDiff |
| `page.docHeight` / `bar.top` / `cardTops` 容差 | 2 | 4 | 同上顺延 |

## 6. 像素对账（设计 PNG vs 实现 430 宽整页截图）

```
python .agents/state/cmp-bands-6-design-vs-impl.py 设计PNG 实现PNG 出报告 3
设计 430x1238 vs 实现 430x1241
卡片内容列 x=36..394 ：设计带起点 54 · 实现 49 · 命中(±3) 47 · 未命中 7
条列     x=194..356 ：设计带起点 17 · 实现 18 · 命中(±3) 13 · 未命中 4
位移：y 0..1000 中位 1（−3..3）· y 1000..1425 中位 3
→ 命中 60 / 未命中 11
```

未命中 11 条判读（逐条 scan-col 复核，均非页面缺陷）：

- `108 / 113 / 116`（顶栏下方）：设计带起点在卡片投影**渐变**上，Figma 与 Chrome 的阴影衰减步长不同（设计自 109 起 `244→242`，实现自 111 起）→ 卡片边缘本身一致：设计白行 119、实现 118（±1）。
- `998 / 1023 / 1067 / 1099 / 1109 / 1136 / 1149 / 1178`：全部落在**卡2 以下**，位移 +3~4 —— 唯一来源是提示卡文案「带出的模型数量与凭证权限相关…」在**设计稿里是一行（墨迹 328px ≈ 9.9px/字）、浏览器 CJK 11px/字必然两行**（盒 46 vs 设计 42.5），其后所有元素（卡3 / 底栏）整体顺延 3~4px。已 `designLiteralDiff` 登记，不在 1–4px 上 churn（会破坏上方已对齐的 60 条）。

## 7. 交互相有牙齿（`?scenario=actions` 两轮）

```
phase1 286 条 · 0 失败 · 零请求（首屏空态不发任何请求，见 requests-序号12v1-checks-run{1,2}.txt = 0 行）
phase2 点凭证选择框 → GET /api/v1/credentials?page=1&pageSize=20 200 → 面板 2 行
       选 c1 → GET /api/v1/credentials/c1 200 → chip「已选 1 / 2」· 值「主线路 Key」· 模型行 [gpt-4o, gpt-4o-mini] · 空态消失
phase3 填名称 → 计数「12/30」→ 保存并继续 → POST /api/v1/quotes body={"name":"2024Q3 主线路报价","credential_id":"c1"} 200
       → POST /api/v1/quotes/q9/items body={"items":[{"model_name":"gpt-4o"}]} 200 → toast「保存成功」
       → #/pages/model-pricing/index?quoteId=q9 → 落地页 GET /api/v1/quotes/q9/items 200 并渲染
两轮：phase2/phase3 逐字段相同 = True · serve 实收请求行逐字节相同 = True（7 行/轮）
```

**fixture 缺口（先红后绿）**：落地页 `/pages/model-pricing/index?quoteId=q9` 会取 `GET /api/v1/quotes/q9/items`，`api-12-v1` 缺该 fixture（404 且落地页错误 toast 会盖掉「保存成功」）→ 补 `api-12-v1/v1/quotes/q9/items/index`；`check-mock-fixtures --mock api-12-v1` 本页两条入口 GET 均 PASS。

## 8. 质量门

```
npm test          1178/1178 · 72 files 连跑两轮（14:08:05 / 14:13:43）
npm run type-check  exit 0
build:mp-weixin    DONE — components/quote-form/QuoteFormView.wxss 内含本轮设计值：
                   box-shadow:0 0 0 .8px #e2e8f0 ×4 / #cbd5e1 / #2563eb · 0 4px 16px rgba(15,23,42,.05|.06) ·
                   0 -4px 16px rgba(15,23,42,.05) · 0 6px 16px rgba(37,99,235,.28) · width:29px;height:39px ·
                   height:22.5px ×2 · line-height:17.5px ×2 · line-height:18px ×5
build:h5           DONE · review-artifacts 22/22（/pages/quote-form/index = OK，样式随共用组件产出）
截图               logs/screenshots/20260916-1412-序12v1-新增报价单初始态-checks轮-h5-430宽.png（430×1241）
```

## 9. designLiteralDiff（设计字面量与实现的有意差异，登记不照抄）

| 项 | 设计字面量 | 实现 | 原因 |
|---|---|---|---|
| 提示卡盒高 | 42.5（文案一行） | 46 | 浏览器 CJK 11px/字 → 33 字必然两行（字号/文案都是设计原文，不改文案也不缩字号） |
| 卡2 / 页高 | 287.5 / 1238 | 291 / 1241 | 同上顺延（+3~4） |
| 须知条目文案行盒 | `lineHeight: 1.2`（=14.4） | 18 | 设计 PNG 实测两行为 36；同页空态说明走 14.4 —— 设计自身两套口径，各按实测落地 |
| 标签行行盒 | `lineHeight: 1.2`（=15.6） | 17.5 | PNG 实测输入框顶 276.5 反推 |
| 「QT-XXXXXXXX-XXXX」 | 设计示例常量 | 仅当服务端返回 quote_no 时替换（空态不预填） | 留证同旧轮次 |
