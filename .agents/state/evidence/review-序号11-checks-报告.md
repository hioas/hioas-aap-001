# 序号 11 载体页「设计期望值 checks」复核报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1315`（队列 8 第 11 页 · `page-11`）
- 页面：**11. 报价端·小程序 ｜ 【报价管理】模型定价-详情**（`layer_id 46c3747b-3aca-419f-a302-22cf9de8cff8`）
- 路由：`/pages/model-pricing/index`（台账「目标路由」列为准；带参 `?itemId=qi1`）
- 载体页：`.agents/state/h5-measure/__measure-model-pricing.html`（430 宽 iframe，**271 条 checks**）
  · 另有 `?quoteId=` 回落载体页 `__measure-model-pricing-q9.html`（本页同源，本轮一并复跑，mock `api`）
- mock：`.agents/state/h5-measure/api-11`（`GET /api/v1/quotes/items/qi1` + `PUT /api/v1/quotes/items/qi1`）

## 1. 设计帧重抓（人工指令 C：复核前必须重抓）

```
cmd /c start "" https://www.calicat.cn/design/2095515676955668480      # 先让编辑器开在浏览器里
python C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/calicat_source.py page \
  --url https://www.calicat.cn/design/2095515676955668480 \
  --layer-id 46c3747b-3aca-419f-a302-22cf9de8cff8 --page-id page-11 --out "$LOCALAPPDATA/Temp/aap-live"
sha256sum "$LOCALAPPDATA/Temp/aap-live/raw/pages/page-11/design.json"
```

`design.json` sha256 **`fcec83536a0a9c6d981f920721b93d13c1f50a37703da7c6402834ba6d1d955b`**，
与实现所依据的 `.calicat/raw/pages/page-11/design.json` **逐字节相同**（`cmp` 报 BYTE-IDENTICAL）→
**画布当前状态 = 实现所依据的版本，无漂移**（不用旧结论，本轮重抓重比）。

## 2. 红 → 绿（主交付）

| 轮 | checkCount | checkFailCount | docH | 两轮独立测量 |
|---|---|---|---|---|
| 红（修复前源码 + 同一份探针，两轮） | 256 | **21** | 1540 | 一致（是） |
| 绿（修复后 + 同一份探针，两轮） | **271** | **0** | 1540 | **15/15 字段全等，不一致 0** |

- 红基线命令：`git` 未改动源码前直接跑 `bash .agents/state/review-measure.sh 11-checks-red __measure-model-pricing.html .agents/state/h5-measure/api-11 5331`
  → `.agents/state/evidence/review-序号11-checks-red-run{1,2}.json`（转录 `red-序号11-checks-设计期望值偏差.txt`）
- 绿命令：`bash .agents/state/review-measure.sh 11-checks __measure-model-pricing.html .agents/state/h5-measure/api-11 5332`
  → `review-序号11-checks-run{1,2}.json`（转录 `green-序号11-checks-设计期望值.txt`）
- 两轮一致性：`python .agents/state/cmp-measure-runs.py .../review-序号11-checks-run1.json .../review-序号11-checks-run2.json phase1`
  → `phase=phase1 · 全等字段 15 个 · 不一致 0 个`
- 21 条红的分诊见 `red-序号11-checks-设计期望值偏差.txt` 末尾：**15 条真页面偏差 + 6 条探针自身期望值 bug**
  （`normShadow` 把 alpha=1 的颜色归一成 `rgb(...)`；`card3.tokenBoxTops` 取了 `slice(0,3)` 而 DOM 顺序是行内成对）。
  探针自身 bug 先修探针再复跑（脚本 `build-probe-11.py`），不记到页面账上。

## 3. 修掉的 5 类真偏差（`src/pages/model-pricing/index.vue`）

1. **四张卡缺设计声明的投影**：design `effects` 四张卡均有 `drop_shadow(0,4,16,rgba(15,23,42,0.06))` →
   `.card` 补 `box-shadow: 0 4px 16px rgba(15,23,42,.06)`（box-shadow 不占布局，卡高/卡位不变）。
2. **保存按钮缺投影**：design `drop_shadow(0,6,16,rgba(37,99,235,0.28))` → `.pricing__save` 补 `box-shadow`。
3. **图标盒不是设计图层盒**（只有形状大小）：`.ic` 改为「盒子 = 设计图层盒，形状入 `::before`」，
   按声明尺寸落地 6 类：卡1 折叠箭头 **20×20**（design e47dc806 w20 fs18；原 17×17 且右界溢出到 400）、
   计费方式 caret **18×18**（00bedca8 w18 fs16）· 添加计费分支 + **18×18**（84b1c4b0 w18 fs16）·
   保存按钮 ✓ **22×22**（e1e80bd3 w22 fs20）· 媒体/规则折叠箭头 **18×18**（fs16）·
   规则组删除 **18×18**（fs16）· 条件行 + **15×15**（fs14）。
4. **由 3) 连带的布局效果=设计值**：添加计费分支按钮宽 **111→119**（= 12+18+4+73+12，design fit_content 实宽）、
   计费方式选择框 **245→237**、按钮 x **287→279**（三者互相自洽）。
5. **媒体列勾选框描边**：设计里媒体列 stroke `thickness=1`（token 列 0.8）→
   `.media__col .check:not(.check--on) { box-shadow: 0 0 0 1px }`（`:not(--on)` 保证勾选态仍无描边）。

## 4. 期望值口径（want 的两类来源，全部可复现）

(a) **声明值**：`.calicat/raw/pages/page-11/design.json`
```
python .agents/state/tree-view.py page-11          # 几何/内边距/圆角/stroke/effects/gap
python .agents/state/text-fields.py page-11        # 文本叶子 fontSize/字重/fontFill/宽高
python .agents/state/node-probe.py page-11         # 逐节点 padding/gap/字号/文案（page-11-nodes.txt）
```
(b) **盒的真实边界**：设计 PNG 430×1541 实测（`.agents/state/design-shots/page-11.png`）
```
python .agents/state/png-rowmodal.py .agents/state/design-shots/page-11.png --x0 30 --x1 400 --runs
python .agents/state/text-rows.py   .agents/state/design-shots/page-11.png 20 410 190 3 0 1541
python .agents/state/scan-col.py    .agents/state/design-shots/page-11.png 35 995 1445
python .agents/state/scan-col.py    .agents/state/design-shots/page-11.png 25 960 1541
python .agents/state/ink-bbox.py    .agents/state/design-shots/page-11.png 10,48,45,90
```

**本页定标（重要，与其它页不同）**：本页的 remixicon/字形行框 ≈ **fontSize × 1.1**，不是 ×1.5 ——
三条独立实测同时自洽：媒体定价头 17.6 ≈ 18（`媒体定价标题` h15.6 + 箭头 fs16）· 条件操作行 15.4 ≈ 16（fs14）·
返回图标盒 26.4 ≈ 26（fs24）。用 ×1.5 会把卡1 顶成 83（设计 82）、卡3 顶成 603（设计 597）。

## 5. 像素对账（设计 PNG vs 实现 430 宽整页截图）

截图：`logs/screenshots/20260916-序11-模型定价详情-checks轮-h5-430宽.png`
（同件入库 `.agents/state/evidence/`；`bash .agents/state/shot-11.sh`，窗口 430×1541 = 设计帧高）

```
python .agents/state/cmp-bands-6-design-vs-impl.py \
  .agents/state/design-shots/page-11.png \
  ".agents/state/evidence/20260916-序11-模型定价详情-checks轮-h5-430宽.png" \
  .agents/state/evidence/cmp-序号11-设计PNGvs实现截图-结构带.txt 3
```

- 卡片内容列（x36..394）：设计带 62 个 / 实现带 70 个，**命中(±3) 59 · 未命中 3**；
  位移中位 **0**（min −3 max +2，0 位移 21 个）
- 条列（x194..356）：**命中 19 / 未命中 0**，位移中位 0
- 未命中 3 条（设计 y=211/378/1468）逐条判读（`scan-col` 取两侧真实色阶）：
  - y=211 = 卡2 顶边：设计白起 **212**、实现白起 **210**（−2）
  - y=378 = 卡3 顶边：设计白起 **379**、实现白起 **377**（−2）
  - y=1468 = 底栏内白区 AA 行（设计 1465..1469 `253,253,254`，实现 1465..1469 `255,255,255`）：同一行带内的 AA 值差 →
    **探针带起点检测的边界效应**，不是结构位移（两侧底栏顶 1465、蓝色保存按钮 1477..1499 完全相同）
  - 结论：整页存在 **≤2px 的整体上移**（Figma 小数坐标链取整：nav 98.4→98、卡顶 114.4/211.4/378.4→114/210/377），
    与台账里已登记的残差同族，**非页面缺陷**（本轮不在 ±1..2px 上做 churn，避免把下游越改越偏）。

## 6. 交互相（serve 实收请求为证）

`?noaction` 不带 → 默认跑 phase1~4，`requests-序号11-checks-run{1,2}.txt` 各 **6 行**，两轮逐字节相同：

| phase | 动作 | serve 实收 |
|---|---|---|
| 2 | 点顶栏「保存」 | `PUT /api/v1/quotes/items/qi1 body={input_price:2.5,output_price:10,tier:"base",billing_mode:"按 token",request_rules:[…]}` → toast「保存成功」 |
| 3 | 勾选「缓存读取价格」→ 点底部「保存价格」 | 勾选后 `.check--on` 计数 **2→3**；`PUT … body` 多出 `cache_read_price:0` → toast「保存成功」 |
| 4 | 折叠请求规则 → 展开 → 新增规则组 → 返回 | 折叠后 `.rule-group` 0 个且渲染设计里 `visible=false` 的「点击展开，配置计费请求规则」；展开后新增 → 标题 `["规则组 #1","规则组 #2"]`；返回 = navigateBack（hash 不变，H5 顶层无返回栈） |
| 首屏 | — | `GET /api/v1/quotes/items/qi1`（唯一读请求，无轮询） |

纯静态轮无多余请求（无场景/无动作时 serve 只收到首屏那一条 GET）。
回落载体页 `?quoteId=q9` 两轮实测：`docH 1540`、`tierValue base`、`priceInput 2.50`、`priceOutput 10.00`、
`ruleGroupTitles ["规则组 #1"]`、20/20 字段全等（`review-序号11-q9-checks-run{1,2}.json`），未受本轮改动影响。

## 7. 质量门

```
cd aap-client
npm test            → 1173/1173 · 72 files（连跑两轮，13:25:19 / 13:25:48）
npm run type-check  → exit 0
npm run build:mp-weixin → DONE；dist/build/mp-weixin/pages/model-pricing/{index.js,index.json,index.wxml,index.wxss} 齐备
   wxss 内含本轮设计值：`box-shadow:0 0 0 1px #cbd5e1`（媒体勾选框）· `0 6px 16px rgba(37,99,235,.28)`（保存按钮）·
   `width:18px;height:18px`（图标盒）
npm run build:h5    → DONE（430 宽实测与截图同源）
python .agents/state/review-artifacts.py → 台账全部路由 mp-weixin 三件套齐备且已注册（22 页）
```

## 8. 未解决 / 留给人类

- **mini program 真机/开发者工具验收**：本机未装微信开发者工具，`build:mp-weixin` 只做**编译证明**；
  真机验收需人类导入 `aap-client/dist/build/mp-weixin`。
- 台账序号 11 行的 14 条 `missing-prd` / 待拍板缺口（计价方式选项集合、请求规则条件枚举、媒体字段键名等）
  本轮**未改口径**，仍按原样留证。
- 图标仍为 CSS 形状占位（决策 D5）；设计 PNG 里返回箭头字形 ink 为 17×16，占位形状为 10×10（居中于 26×26 盒）——
  属已登记的占位口径，不是尺寸偏差。
