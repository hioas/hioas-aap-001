# 序号 7「检测未通过报告」载体页「设计期望值 checks」轮 · 报告

- 页面：`.` — 帧 **`7. 报价端·小程序 ｜【检测验真】检测未通过报告 2`** = `page-7-2`
  · `layer_id 47815a05-f501-4617-8265-7c8eec0df360`（画布 1，文件 `2095515676955668480`）
- 目标路由：`/pages/report-failed/index?reportId=DR-7`
- 载体页：`.agents/state/h5-measure/__measure-report-failed.html`（由 273 行旧体例重写为 430 宽 iframe + 196 条 checks）
- mock：`.agents/state/h5-measure/api`（`GET /api/v1/reports/DR-7`、`GET /api/v1/reports/DR-7/export`、`POST /api/v1/detection-jobs`）

## 1. 设计帧重抓（复核前必做）

```
calicat_source.py page --layer-id 47815a05-f501-4617-8265-7c8eec0df360 --page-id page-7-2-live
sha256 实测：278041694733a310ede929b6b4386d7b1ea0cd7cb0fc50b9c3c5721b2199f54（live）
             f278041694733a310ede929b6b4386d7b1ea0cd7cb0fc50b9c3c5721b2199f54（留证）
→ 逐字节相同（无漂移）：画布当前状态 = 实现所依据的版本
```

## 2. 期望值口径（want 两类来源，零目测）

1. **声明值**：`.calicat/raw/pages/page-7-2/design.tree.json` + `node-probe.py`（`.agents/state/page-7-2-nodes.txt`）
   + `dump-node-fields.py`（逐节点全字段：lineHeight / height / fontFamily / stroke / effects / padding / gap）。
2. **fit_content 盒真实高度**：设计截图 PNG（430×1110）像素实测
   `.agents/state/design-shots/page-7-2.png`（下载自 ledger 里的 design 截图 URL）。
   本轮新增工具 **`png-rowclass.py`**：逐行统计 `x∈[16,414)` 里等于卡片底色的像素占比 → 判「卡片行 / 间隙行」，
   **不受两卡之间被双份 drop_shadow 染色**的影响（旧口径「等于页面底色」会把卡+间隙+卡连成一段）。
   命令：`python .agents/state/png-rowclass.py .agents/state/design-shots/page-7-2.png`

实测骨架（设计帧高 **1110**）：

| 区块 | 设计 y 区间 | 高 |
|---|---|---|
| 顶部栏 | 0..96 | 96 |
| 未通过封面卡 | 108..362 | 254 |
| 分项评分总览卡 | 374..756 | 382 |
| D2 详情卡 | 768..934 | 166 |
| 免责声明卡 | 946..1014 | 68 |
| 底部操作 | 1030..1110 | 80 |

关键模型（本页定标，后续同族长页复用）：
- **文本行框 = fontSize × 1.5**（12→18 · 17→25.5 · 38→57）；显式声明 height 的节点以声明为准
  （「综合评分」18 /「满分 100」16 /「分项总览」22 / 权重说明 36 / D2 四行 20）。
- 图标字形行框 = fontSize × 1.5（24→**26×36** · 20→22×30 · 18→20×27 · 16→18×24）。
- Figma `stroke{align:center,thickness:1}` → `box-shadow: 0 0 0 1px`（`border` 占布局，内容宽 356→**358**）。
- `effects.drop_shadow(0,6,20,rgba(15,23,42,.06))` → `box-shadow: 0 6px 20px rgba(15,23,42,.06)`。
- 分项行：行高 18 + 间距 12 = **行距 30**（首行前 16）；总览卡尾部权重说明盒 12+36+12=**60**。

## 3. TDD 红 → 绿

| 阶段 | 命令 | 结果 |
|---|---|---|
| 红基线（**用最终探针**，`git stash push` 复现修复前代码） | `bash .agents/state/review-measure.sh 7-checks-red __measure-report-failed.html .agents/state/h5-measure/api 5354` | **51/196 失败**（两轮一致）· `docH 1063` |
| 绿（修复后，两轮独立测量） | `… review-measure.sh 7-checks __measure-report-failed.html … 5353` | **0/196** · 两轮 30/30 字段全等 · `docH 1111` |
| 复位后复跑（`git stash pop` + 重建） | `… review-measure.sh 7-checks-final … 5355` | **0/196** · 与复位前逐字段相同（证明 stash 循环干净） |

- 红基线转录：`evidence/red-序号7-checks-设计期望值偏差.txt`（两轮各 51 条）
- 绿转录：`evidence/green-序号7-checks-设计期望值.txt`
- 一致性：`cmp-measure-runs.py … phase1` → 「全等字段 30 个 · 不一致 0」

## 4. 修掉的 13 类设计偏差（`src/pages/report-failed/index.vue` + `src/utils/report-failed-model.ts`）

1. **顶部栏 89 → 96**：返回图标盒 26×29 → **26×36**（remixicon 24px 行框 = 24×1.5；原按 `lineHeight 1.2` 取 28.8 → 栏高少 7px，整页随之短）。
2. **封面卡补投影**：设计 `effects.drop_shadow(0,6,20,rgba(15,23,42,.06))` → 新增 `.card--cover { box-shadow: 0 6px 20px … }`（修前 `none`）。
3. **三张卡 + 底部次按钮的描边由 `border` 改 `box-shadow: 0 0 0 1px`**（Figma center 描边不占布局）：修前内容宽被挤成 356、卡内元素整体左移 1px（`card3.title.left 37→36`、`card4.text.left 69→70`、`card2.weight.w 356→358`）。
4. **封面卡标题行 14.4 → 18**：`.card__label` / `.card__sub` 行高改 `18px`（12×1.5）。
5. **综合分块 46 → 57**：`.score` 行高 `57px`（38×1.5）；结论胶囊 top 160→**176**。
6. **「综合评分 / 满分 100」两行 14.4+14.4 → 18+16**（设计两行显式 height 不同，`：last-child` 单独给 16）。
7. **分项 8 行 行高 14 → 18、行距 26 → 30**（`.dim__label` / `.dim__score` 行高 18）。
8. **分值文字色改用设计第二套色板**（新增 `scoreTextColor()` + `FailedDimRow.textColor`）：
   高分 `#334155`（D1 89 / D4 82）· 中 `#D97706`（D3/D5/D6/D7）· 低 `#B91C1C`（D2 12 / D8 0）——
   修前用条填色（绿/琥珀/红）当文字色，**与设计 fontFill 逐行不符**；阈值仍取通过线 70 / 否决线 40。
9. **结论胶囊 76 → 83**：图标盒 12×12 → **18×24**（形状移入 `::before`）。
10. **否决条图标 18×18 → 20×27**、文案左边 74→**76**（36+12+20+8）。
11. **结论措辞图标 14×14 → 20×27**、文案左边 58→**64**（36+20+8）。
12. **免责卡图标 20×20 → 22×30**、文案左边 69→**70**；卡高 70→**68**（border 去掉后内容高 36 + 16×2）。
13. **底部「导出 PDF」按钮去掉设计里没有的图标**（设计 `adc9d8c6` 唯一子节点是文本；PNG y=1064 实测按钮内只有居中文本 ink x83..140），
    文字左边 94→**83**；按钮描边改 `box-shadow`。
    另：D2 详情卡标题行 16.8 → **20**、首行解释 top 766→**816**，卡高 165→**166**。

整页 `docScrollHeight` **1063 → 1111**（设计帧 1110；设计为 Figma 小数坐标链，卡1 真值 254.5 → 落地取整整体 +1，
卡顶 108/375/769/947、卡高 255/382/166/68，逐项 ±1 属取整，checks 用 ±2 容差）。

## 5. 交互相有牙齿（`?scenario=actions`，两轮）

- 点「导出 PDF」→ serve 实收 `GET /api/v1/reports/DR-7/export 200` · toast「导出链接已生成，请在浏览器中打开」· `hashUnchanged true`。
- 点「重新提交检测」→ serve 实收 `POST /api/v1/detection-jobs body={"credential_id":"c1"}` → iframe hash
  `#/pages/detecting/index?jobId=j7`，检测进行中页渲染出「检测进行中 / 总进度 50%」，随后连续成对
  `GET /api/v1/detection-jobs/j7` + `/results`（轮询）。
- **无多余请求**：纯测量轮（无 scenario）两轮各只 **1 行** —— `GET /api/v1/reports/DR-7`。
- 证据：`evidence/review-序号7-checks-actions-run{1,2}.json` · `evidence/requests-序号7-checks-actions-run{1,2}.txt`

## 6. 像素对账（实现 430 宽整页截图 vs 设计 PNG）

- 截图：`logs/screenshots/20260916-序07-检测未通过报告-checks轮-h5-430宽.png`（同件入 `evidence/`）
  · 拍图脚本 `bash .agents/state/shot-7.sh`（`--window-size=430,1180`）
- `cmp-bands-6-design-vs-impl.py`（±3 容差、逐列结构带起点）：
  内容列 x=36..394 **命中 34 / 未命中 4**；条填列 x=194..356 **命中 19 / 未命中 0**。
  命中处位移中位 **1**（min −2 max 3）→ 无整体漂移。
- 4 条未命中逐条判读（**非页面缺陷**）：
  - `y 376 / 379 / 385`：卡1 底部投影落区 + 卡2 顶边描边的 **单行 AA 带**（设计 ink 8/13/22 px）
    → Figma 阴影衰减 vs Chrome 的差异（同序号 5/6 记录）。
  - `y 707`：权重说明盒第二行的**墨迹分布**——设计行2 ink 4..25 px/行（约 2 字余量），实现 9..14 px/行（约 1 字）
    → H5 回退字体宽度差异导致**换行点差 1 字**；盒高 36、盒高 60、文案左 48 三项均与设计一致。
- 输出：`evidence/cmp-序号7-设计PNGvs实现截图-色带.txt`

## 7. 质量门

- `npm test` **1170/1170 · 72 files 连跑两轮**（修前 1168 → 新增 2 条模型用例）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE：`dist/build/mp-weixin/pages/report-failed/index.{js,json,wxml,wxss}`
  （wxss 含 `box-shadow:0 0 0 1px #eef2f7` / `#fecaca` / `#cbd5e1`、`line-height:57px`、`line-height:18px` ×10）
- `npm run build:h5` DONE（载体页测量面）
- `check-mock-fixtures.py --mock api`：**FAIL 0**（含反向体检）
- `review-artifacts.py`：台账全部路由 mp-weixin 三件套齐备且已注册（22 页）

## 8. 本轮探针自纠 3 处（探针自身的坑，非页面缺陷）

1. `css(sel,'boxShadow')` 早先走 `normColor()`，把整串压成**只剩颜色**
   （`rgba(15,23,42,.06) 0px 6px 20px 0px` → `rgba(15,23,42,.06)`），使**每条 box-shadow 检查假失败** → 新增 `normShadow()`（只归一颜色片段，保留偏移）。
2. `rectField()` 不认 `left`（只有 `x`）→ 传 `.left` 的检查拿到**整个 rect 对象**，永远失败 → 补 `f === 'left'`。
3. 卡顶/卡高用 `join(',')` 精确比字符串，把设计小数坐标链的 ±1 取整差报成缺陷 → 新增 `chkList()`（逐项容差）。

## 9. 结论

序号 7 的载体页已从「文案齐 / 溢出 0 / 两轮一致」升级为**196 条设计期望值 checks**，红 51 → 绿 0，
两轮独立测量全等，设计帧重抓无漂移；13 类偏差按「先红后绿」修完，整页高度对齐设计帧（1111 vs 1110）。
仍未解决（**留给人类拍板，本轮未擅自动**）：台账序号 7 行原有 10 条待确认项（设计 D1–D8 口径与 09-PRD 不一致、
一票否决维度冲突、配色阈值、报告详情字段级 schema 等），本轮未改其中任何一条的业务口径。
