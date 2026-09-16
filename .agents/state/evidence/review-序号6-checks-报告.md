# 序号 6「大模型检测报告 · 多维度专业版」载体页补「设计期望值 checks」维度 — 复核报告

- 轮次 id：`aap-tdd-run-20260916-1050`（cron 轮，2026-09-16 10:50 → 12:20）
- 页面：`/pages/report/index`（Calicat 帧「6. 报价端·小程序 ｜ 【检测验真】大模型检测报告 · 多维度专业版」= layer_id `0f0755e4-b7c6-41c1-bebf-0969c536b163`，`page-6`）
- 载体页：`.agents/state/h5-measure/__measure-report.html`（由 191 行旧体例重写为 **430 宽 iframe + 221 条设计期望值 checks**）
- mock 目录：`api`（起在 5333–5338 端口，用完即关）
- 设计真源：画布 `2095515676976640000`（文件 `2095515676955668480`）**当前状态**；帧重抓 2026-09-16 10:52
  `python E:/agent/aap-tools/recapture-all.py` → **22 帧全 SAME（无漂移）**，其中 `page-6` `design.json` 633742 → 633742 **逐字节相同**。

## 1. 期望值（want）的两类来源

| 来源 | 说明 | 工具 |
|---|---|---|
| 声明值 | `.calicat/raw/pages/page-6/design.tree.json` 的 width/height/padding/cornerRadius/fills/stroke/effects/fontSize/fontFamily | `tree-view.py`（本轮新增）、`dump-node-fields.py`、`node-probe.py` |
| fit_content 真实高度 | 设计截图 PNG（430×5342）色带实测 | `png-cardmap.py` / `png-textbands.py` / `png-bands.py` / `png-rows.py`（本轮新增前两个） |

设计截图 PNG：
`https://prototype-prod-1254106194.cos.ap-beijing.myqcloud.com/calicat/file/2099910139278049280/canvas/image/2099910139278049280.png`

PNG 实测骨架（设计帧高 **5342**）：

```
顶部栏 0..93(93) · 结论封面卡 105..521(416) · 关键指标卡 533..884(351) · 维度总览卡 896..1413(518)
明细卡 1425..4388(2963) · 风险发现卡 4400..4810(410) · 原始证据卡 4822..5108(287)
免责声明卡 5120..5229(109) · 底部操作块 5245..5317 + 24 底边距
明细条目行距 43（行高 29 + 间隔 14）· 组标题行 18 + 组内间隔 14 · 分组之间间隔 16
指标子卡 174×85（行距 95）· 均分行行距 28 · 雷达区 258 · 明细卡 7 组 55 项
```

## 2. TDD 红 → 绿

| 阶段 | checkCount | checkFailCount | docH | 证据 |
|---|---|---|---|---|
| 红（`git stash push -- aap-client/src/pages/report/index.vue` 复现修复前代码，同一份探针） | 219 | **45** | 4886 | `red-序号6-checks-设计期望值偏差.txt` · `review-序号6-red-run{1,2}.json` |
| 绿 | 221 | **0** | **5343** | `green-序号6-checks-设计期望值.txt` · `review-序号6-run{1,2}.json` |

两轮独立测量全等：`cmp-measure-runs.py review-序号6-run1.json …-run2.json phase1` → **全等字段 24 / 不一致 0**
（红基线两轮同样全等）。`overflowingCount 0` · `missingTexts None` · `docScrollWidth 430 = innerWidth`。

## 3. 修掉的 11 类设计偏差（`src/pages/report/index.vue`）

| # | 偏差 | 修前 | 修后（= 设计） |
|---|---|---|---|
| 1 | 顶部栏高（返回图标盒 = remixicon 22px 行框 33） | 84 | **93** |
| 2 | 顶部栏标题字重/间距（fontFamily=SourceHanSans-Bold） | 600 / 8px | **700 / 12px** |
| 3 | 结论封面卡缺设计 `drop_shadow(0,6,20,rgba(15,23,42,0.06))` | 无投影 | **box-shadow 0 6px 20px rgba(15,23,42,.06)** |
| 4 | 卡片描边：Figma `stroke{align:center,thickness:0.8,#EEF2F7}` 被写成 border / 缺失 | 无（或 border 占布局） | **`box-shadow: 0 0 0 .8px #eef2f7`**（5 张卡 + 底部操作条） |
| 5 | 结论封面卡标题（design 625f2248 = 12px Medium #64748B，与其余卡片 15px Bold 不同） | 15px/600/#0F172A | **12px/500/#64748B**（新增 `.card__title--cover`） |
| 6 | 综合分（fontFamily=SourceHanSans-Black）+ 行框 44 | 600 / 1.2 | **900 / 44px** |
| 7 | 「通过」标签底 + 字重（design #F0FDF4） | #ECFDF5 / 400 | **#F0FDF4 / 700**（新增 token `$color-success-weak-2`） |
| 8 | 状态四格值 字重、结论措辞盒图标盒（remixicon 18px → 20×27） | 600 / 14×14 | **700 / 20×27**（形状入 `::before`） |
| 9 | 结论封面卡缺 1px 分隔线 + 两处 16 间隔；信息清单上间距 | 无 / 12px | **`card__divider`（margin-top 16）+ 信息清单 margin-top 16** |
| 10 | 关键指标卡：标题行缺 5×14 色条、值行字重 ExtraBold / 行框、末行多余 10 间距 | 无色条 / 600 / 84 高 / 351 | **色条 + 800 + 值行高 28 → 子卡 85、行距 95、卡高 351** |
| 11 | 维度总览卡「分」列宽 32 右对齐、均分行高 16；明细卡：条目间隔 8→14、组标题行 18、分组间隔 16、指纹提示/权重说明盒行框 16、5 处字重（Bold 700 / Medium 500） | 分列 13 宽右 375、行距 37、卡高 2552 | **分列 32/右 394、行距 43、卡高 2962、整页 5343** |

其余：风险发现卡「标题行 → 首条」16 间距、发现标题 Bold、底部「填写报价」Bold —— 同批修掉。

## 4. 像素对账（设计 PNG vs 实现 430 宽整页截图）

`cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> <out> 10`（结构带起点 ±10 匹配）：

| 列 | 设计带 | 实现带 | 命中 | 未命中 |
|---|---|---|---|---|
| x=36..394（卡片内容区） | 142 | 145 | **142** | 0 |
| x=194..356（明细条/进度条列） | 121 | 116 | **115** | 6（`93` 卡片阴影边、`1453/1456/1460` 明细说明同一行被拆成 3 段、`2815` 指纹提示内文墨迹、`5144` 免责声明墨迹 —— 经逐条判读为设计 PNG 自身的 AA/阴影带，非页面缺陷） |

位移分区概况（命中处）：y 0..1000 中位 0（min -10 max 4）· y 1000..1425 中位 1 · **y 1425..4400（明细卡内部）中位 5（min -8 max 9）** · y 4400..5342 中位 2。
卡片边界实测（DOM）：`cardTops = [105, 533, 896, 1425, 4402, 4824, 5122]` vs 设计 `[105, 533, 896, 1425, 4400, 4822, 5120]` → **前 4 张完全对齐，后 3 张 +2**；
整页 `docScrollHeight` **5343** vs 设计帧高 **5342**（+1）。

**残留（已定位、非页面缺陷）**：明细卡内部条目整体较设计 **+8**（例：A1 条形 设计 1549 / 实现 1557），到 G 组收敛为 **+2**
（G1 设计 4039 / 实现 4041），即明细卡中段存在 ±8 的**内部重分配**而卡边界不变。
原因是 H5 回退字体在中段两处文本块（明细说明 11px、指纹提示 10.5px）的换行/墨迹与设计字体不同（说明行 ink 设计 1476 / 实现 1480），
与本轮其它页记录过的「H5 回退字体差异」同族；**卡片高度、分组高度、行距、条位置均在设计值 ±3 内**。

## 5. 交互相（有牙齿）

`?scenario=actions`（点「导出 PDF」→ 点「填写报价」），两轮 serve 实收请求行 4 行（`requests-序号6-actions-run{1,2}.txt`）：

```
GET /api/v1/reports/DR-1            200   ← 页面取数
GET /api/v1/reports/DR-1/export     200   ← 「导出 PDF」点击（18-API Report Tag）
GET /api/v1/provider/profile        200   ← 跳转后目标页取数
GET /api/v1/credentials?page=1&pageSize=20 200
```

DOM 断言（`review-序号6-actions-run{1,2}.json` 的 `actions`）：`exportClicked true` · `hashUnchangedAfterExport true`（导出为 api 类，不跳页）·
toast「导出链接已生成，请在浏览器中打开」· `quoteClicked true` · `hashAfterQuote = #/pages/quote-models/index`（用户拍板口径）。
无校验门场景（`?scenario=`）两轮实收 **1 行**（仅报表 GET），无多余请求。

## 6. 质量门

- `npm test` **1168/1168 · 72 files 连跑两轮全绿**（11:11 与 11:15 两轮）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE → `dist/build/mp-weixin/pages/report/index.{js,json,wxml,wxss}` 四件套齐备（wxss 含 `font-weight:800/900`、`line-height:16px/24px`、`box-shadow:0 0 0 .8px`）
- `npm run build:h5` DONE + 430 宽 iframe DOM 实测（上表）+ 整页截图 `logs/screenshots/20260916-序06-检测报告-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）
- 本机未装微信开发者工具：mp-weixin 只做**编译证明**，真机/开发者工具验收留给人类（导入 `dist/build/mp-weixin`）

## 7. 本轮新增/升级的工具（仓库外一次性脚本之外）

- `tree-view.py`：设计树紧凑视图（含 id/几何/内边距/圆角/填充/描边/effects/字体/文案），`--match` 可定位节点
- `png-cardmap.py`：按指定列做「页面底色 vs 非底色」区段图（判卡片/区块边界；支持 RGB 与 RGBA PNG）
- `png-textbands.py`：区块行墨迹带（每行与行内主色不同的像素数 ≥ 阈值 → 连续行带），判行高/行距最直接
- `png-rows.py` / `png-sample.py`：单列色带（含 1 行带）与逐点取样（含 alpha）
- `cmp-bands-6-design-vs-impl.py`：设计 PNG vs 实现截图的结构带逐条对账（±容差 + 分区间位移概况）
- `shot-6.sh`：整页 430 宽截图（ASCII 临时名 → cp 成中文名，避免 Chrome 中文路径静默失败）
