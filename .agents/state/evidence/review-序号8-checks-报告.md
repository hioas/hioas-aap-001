# 序号 8「【报价管理】报价单列表」载体页「设计期望值 checks」轮 · 报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1141`（队列 8 第 7 页）
- 页面：`page-8-2`「8. 报价端·小程序 ｜ 【报价管理】报价单列表 2」→ 路由 `/pages/quotes/index`
- 帧引用：**帧名 + layer_id** = 「【报价管理】报价单列表 2」`56142177-5e03-487d-ba5d-3a5c3c3b4071`
- 载体页：`.agents/state/h5-measure/__measure-quotes.html`（430 宽 iframe · **138 条 checks**）
- mock：`.agents/state/h5-measure/api`（台账对照：`api` = 3/4/4-v1/5/6/7/8/9）

## 1. 设计帧重抓（复核前必做）

- 先 `cmd /c start ""` 拉起 Calicat 编辑器，再
  `calicat_source.py page --layer-id 56142177-… --page-id page-8-2 --out %TEMP%/aap-live8`。
- 与留证逐字节比对：**唯一差异 = 「新建按钮」（`7ccb56ba`）`width 97 → 100`**（差 1 字节；自动布局按子节点重算：
  `padding 12 + 图标 18 + container padding-left 4 + 文案 54 + padding 12 = 100`，与子节点自洽 —— 与 2026-09-16 08:55 基线记录一致）。
- 处置：按「当前帧为准」实现为 **宽 100**（原实现按旧的 97 做成内容自然宽 88）；其余节点逐字节相同 ⇒ **无其它漂移**。

## 2. 期望值口径（want 两类来源，零目测）

1. **声明值**：`.calicat/raw/pages/page-8-2/design.tree.json`
   - 本轮新增工具 `python .agents/state/text-fields.py page-8-2` → 打印 96 个文本叶子的
     `fontSize / fontFamily→字重 / fontFill / 宽高 / 文案`（字重映射 Bold→700 · SemiBold→600 · Medium→500 · Regular→400）。
   - `python .agents/state/tree-view.py page-8-2` → 盒子的几何/内边距/圆角/stroke/gap/effects。
2. **fit_content 盒的真实几何**：设计 PNG 430×1206 像素实测
   - `png-rowclass.py`（逐行判卡片/间隙，不受投影染色）· `png-textbands.py`（盒内文字行带）· `png-xruns.py`（行内左右边界）。
   - 实测骨架：顶部导航 0..90 · 筛选行 90..144（chip 102..131）· 列表 144..1106 ·
     卡 156..334 / 346..524 / 536..714 / 726..904 / 916..1094（**卡高 178 · 间距 12**）·
     卡内 顶行 172..194(22) · 单号块 210..230(16+20) · 元信息块 242..258(12+16) · 操作行 258..318(60) ·
     容器 padding-top 16 + TabBar 1122..1206(84) ⇒ **整页 1206**。

关键模型（本页复用）：fit_content 文本行框 = `fontSize × 1.5`，**显式 height 优先**（新建报价文案 16 · TabBar 标签 16）；
图标字形行框 = `fontSize × 1.5`（22→33 · 16→24）；Figma `stroke{align:center}` → `box-shadow: 0 0 0 1px`（`border` 占布局，内容宽会从 358 挤成 356）。

## 3. TDD 红 → 绿

| 步骤 | 命令 | 结果 |
|---|---|---|
| 红（源码侧） | `npx vitest run tests/unit/quotes-model.spec.ts` | **1 failed**：`bg '#fffceb' ≠ '#fffbeb'`（待签署胶囊底色，design `c426702b`） |
| 红（探针侧） | 同一份探针两轮：`review-measure.sh 8-checks-red …`（`git stash` 复现修复前源码） | **27 / 138**（两轮完全一致，`evidence/red-序号8-checks-设计期望值偏差.txt`） |
| 绿 | 同上探针两轮：`review-measure.sh 8 …` | **0 / 138**（`green-序号8-checks-设计期望值.txt`） |
| 一致性 | `cmp-measure-runs.py … phase1/phase2` | 两轮独立测量 **30/30 字段全等**，不一致 0 |
| 数据侧 | `npm test` | **1172 / 1172 · 72 files 连跑两轮** |

> 说明：第一版探针跑出的红基线是 23 条，其中 2 条是**探针自身的坑**（`grpTexts` 只取每组第一个匹配 → 操作文案只比出 5 条；
> `actionRight` 把 x 与 right 混用）——已修；另有 1 条 `card.metaText.w`（元信息整串宽 216）被替换为 6 条**结构断言**
> （见 §4 第 11 项）。最终红基线 27 条 = 23 − 2（探针坑）+ 6（新结构断言）。

## 4. 修掉的 11 类设计偏差

| # | 位置 | 修前 | 修后（设计依据） |
|---|---|---|---|
| 1 | 顶部标题 | 字重 600 · 行框 24 | **700**（`91be2734` Bold）· 行框 **30**（20×1.5） |
| 2 | 「新建报价」按钮 | 宽 88（内容自然宽） | **宽 100**（当前画布 `7ccb56ba` 声明值） |
| 3 | 按钮内图标盒 | 12×12 | **18×24**（`47594508` 16px remixicon 行框），加号形状入 `::before/::after` |
| 4 | 按钮文案 | 字重 400 · 行框 14 | **500**（`8b0d35de` Medium）· 行框 **16**（显式 height） |
| 5 | 报价卡描边 | `border: 1px`（占布局） | **`box-shadow: 0 0 0 1px`** → 内容宽 356→**358**，操作链接左界 37→**36** |
| 6 | 卡高 / 卡顶 | 177 · 156/345/534/724/913 | **178** · **156/346/536/726/916**（PNG 实测） |
| 7 | 卡片标题 | 行框 18 | **22.5**（15×1.5） |
| 8 | 状态胶囊文字 | 行框 13.2 | **16**（11×1.5） |
| 9 | 单号标签 | 行框 16 | **19.5**（13×1.5） |
| 10 | 元信息行框 | 13 | **16**（11×1.5；这 3px×5 卡正是整页高度差的来源之一） |
| 11 | 元信息行结构 | **单文本节点** `2 个模型 · CNY · 更新于 06-14 15:20`（整串撑满卡片宽 356，分隔点用 #94A3B8） | 设计里的 **5 个节点**（`559e490e`：3 段 + 2 个分隔点，节点之间 **8px**），分隔点用设计另一套浅灰 **#CBD5E1**（`fd63dfdb/9cafcec1`）；新增 `metaParts()` + 单测断言 5 节点顺序 |
| 12 | 操作图标盒 | 16×16（形状画在盒子上） | **16×24**（16px remixicon 行框；形状移入 `::before`，与序号 3/4/5/6/7 同族） |
| 13 | TabBar 图标盒 | 18×18 | **22×33**（22px remixicon 行框；18×18 形状居中于 `::before`） |
| 14 | 列表底留白 | 108 | **112** → 整页 `docScrollHeight` **1198 → 1206 = 设计帧高**（90+54+962+16+84） |
| 15 | 待签署胶囊底色 | `#FFFBEB` | **`#FFFCEB`**（design `c426702b fills rgba(255,252,235,1)`；先红后绿 1 条单测 + 1 条页面断言） |

（表内 15 行按「类」归并为 11 类：1–4 顶部栏 · 5–6 卡片盒 · 7 标题 · 8 胶囊文字 · 9 单号 · 10–11 元信息 · 12 操作图标 · 13 TabBar · 14 整页高度 · 15 色值。）

## 5. 交互相有牙齿（`?scenario=actions`，两轮）

- **phase3**（点「已驳回」chip = `api`）：chip 高亮 `已驳回`（bg `rgb(37, 99, 235)`）· 行数 5 · hash 不变；
  serve 实收 **`GET /api/v1/quotes?page=1&pageSize=10&status=REJECTED` 200**。
- **phase4**（点卡1「删除」= `api`）：真实 `uni-modal`（标题「删除报价单」/ 按钮 `[取消, 删除]`/ 文案占位已记台账）
  → 确认 → serve 实收 **`DELETE /api/v1/quotes/q1` 200** → toast「已删除」→ 重新 `GET` 列表。
- 两轮 `requests-序号8-actions-run{1,2}.txt` **逐字节相同**（各 6 行，含写请求 body 行）；
  phase3/phase4 的 6 + 9 个字段两轮全等（`cmp-measure-runs.py`）。
- 纯测量轮（无场景）两轮各只 **1 行**请求（`GET /quotes?page=1&pageSize=10`）—— 无多余请求。

## 6. 像素对账（实现 430 宽整页截图 vs 设计 PNG）

- 取图：`bash .agents/state/shot-8.sh`（窗口 430×1206；载体页 `?shot=1` 时 iframe 高度 = **1206 = 设计帧高**，
  这样固定底栏才落在设计位置 1122..1206）。
- `cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> <out.txt> 10`：
  - 内容列 x36..394：**24 / 24 命中**；条列 x194..356：**18 / 18 命中**；**未命中合计 0**。
  - 命中处位移：中位 0/1，**min −1 / max +1**（Figma 小数坐标链取整差）。
- 结论：本页实现与设计帧在**结构带级别逐带对齐**（本页是 checks 轮以来首个「0 未命中」的页面）。

## 7. 质量门

- `npm test` **1172 / 1172 · 72 files 连跑两轮**（`green-序号8-checks-全量轮{1,2}.txt`）
- `npm run type-check` exit 0（`typecheck-序号8-checks.txt`）
- `npm run build:mp-weixin` DONE → `dist/build/mp-weixin/pages/quotes/index.{js,json,wxml,wxss}`；
  wxss 实测含 `box-shadow:0 0 0 1px #eef2f7` · `width:100px` · `font-weight:700` · `line-height:16px`
- `npm run build:h5` DONE（430 宽 DOM 实测 + 截图均基于该产物）
- `check-mock-fixtures.py --mock api` **FAIL 0**（`mock-fixtures-序号8.txt`）· `review-artifacts.py` **22/22 三件套齐备并注册**
- 截图：`logs/screenshots/20260916-序08-报价单列表-checks轮-h5-430宽.png`（同件入库 `evidence/`）

## 8. 本轮新增工具 / 口径

- `text-fields.py`（新增）：打印设计树**全部文本叶子**的字号/字重/字色/尺寸/文案 —— 判「声明值」的第一入口。
- `shot-8.sh`：430×1206 整页截图模板（含「shot 模式 iframe 高度 = 设计帧高」约定，固定底栏页必须这样取图）。
- `gen-8-checks-evidence.py`：红/绿转录 + 两轮一致性 + serve 实收请求行的证据合成。
- 口径补充（写进状态文件 §5.5）：**底部固定栏页面的截图载体必须把 iframe 高度设为设计帧高**，否则像素对账会在底栏带整体偏移（本轮首图偏移 35px，非页面缺陷）。
- 口径补充：**设计里用 `padding-left: 8` 分隔的文本节点组，不能实现成一个带空格的字符串**（innerText 无空格、字距与分隔点色值都会偏）。

## 9. 结论

序号 8 载体页「设计期望值」维度补齐：**138 条 checks · 红 27 → 绿 0**，两轮独立测量全等，
整页高度、卡片边界、操作行与底栏均与设计帧对齐（像素对账 0 未命中），交互相有实收请求行与 toast 证据。
队列 8 下一轮开工：**序号 9**（`page-9`「模型报价设置-列表」→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`，mock 目录 `api`）。
