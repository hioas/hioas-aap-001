# 序号 22「【工作台与我的】我的与用量概览 2」checks 复核报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1605`（2026-09-16 16:0x–16:3x）
- 帧引用（按人类指令 C 的口径）：帧名 `22. 报价端·小程序 ｜ 【工作台与我的】我的与用量概览 2` + `layer_id 8bc59233-3854-4725-b85b-bfaf4518e934`
- 目标路由：`/pages/usage/index` · 载体页 `__measure-usage.html` · mock 目录 `api-22`

## 1. 设计真源重抓（无漂移）

| 项 | 命令 | 结果 |
|---|---|---|
| design.json | `calicat_source.py page --layer-id 8bc59233-… --page-id page-22-2` | sha256 `63d7ce0c2e7b31dd…` **逐字节相同**（`cmp` 无差异） |
| 设计 PNG | 重下载 `2099979326419681280.png` | sha256 `ce50a955bd33e5c0…` **相同**（430×1138） |

> 重抓前已 `cmd /c start "" https://www.calicat.cn/design/2095515676955668480` 拉起编辑器（否则抓取报「请先在浏览器中打开文件」）。

## 2. TDD 红 → 绿（本轮主交付）

载体页 `__measure-usage.html` 由 293 行旧体例（只报「文案齐 / 溢出 0」）**重写为 430 宽 iframe + 267 条设计期望值 checks**
（构建脚本 `build-probe-22.py`，四段骨架切自 `__measure-mine.html`）。

| 阶段 | 命令 | 结果 |
|---|---|---|
| 红（修复前源码 + **同一份最终版探针**两轮） | `review-measure.sh 22 … 5334` | **8 / 267**（两轮逐条相同）· `docH 1138` · 溢出 0 · 文案缺失 0 |
| 绿（修复后 + 同一份探针两轮） | `review-measure.sh 22 … 5354` | **0 / 267** · `docH 1138` = 设计帧高 · 溢出 0 · 文案缺失 0 |
| 两轮独立测量一致性 | `cmp-measure-runs.py … phase1` | **50 字段全等 · 不一致 0** |

证据：`red-序号22-run{1,2}-checks.json` · `red-序号22-checks-设计期望值偏差.txt` · `green-序号22-checks-设计期望值.txt`。

### 2.1 红基线 8 条 → 5 类页面偏差（全部真实缺陷）

| # | check | got → want | 根因 |
|---|---|---|---|
| 1 | `summary.pad` | `20px` → `20px 16px` | 设计 811a53eb padding=[20,16,20,16]，实现误用 `.card` 的 20 → 宫格与标题整体内缩 4px |
| 2 | `summary.title.x` | 36 → 32 | 同上（卡 padding-left 16 → 标题 x 32，PNG 标题墨迹 32..87） |
| 3 | `summary.tileX` / `summary.tileW` | `36,220…` / `175` → `32,220…` / `178` | 同上（宫格 358−9 → 366−9 ⇒ 每条 175 → 178.5） |
| 4 | `summary.shadow` | `none` → `rgba(15, 23, 42, 0.06) 0px 6px 20px 0px` | 设计 effects `drop_shadow(0,6,20,rgba(15,23,42,.06))` 漏实现（本卡**无 stroke**，此前只给了 ring 家族，本卡落空） |
| 5 | `month.cal.h` / `month.chev.h` | 15 / 15 → 22.5 / 24 | 月份胶囊内两个字形盒按设计层宽×字号×1.5（fs15→22.5、fs16→24）；另去掉下箭头形状的 `margin-bottom:3px`（把墨迹从中心上移 1.5px，设计墨迹中心 = 胶囊中心 66） |
| 6 | `month.value.lh` | 18 → 14.4 | 设计 `lineHeight 1.2 × 12` |

（表内 6 行对应 8 条 check：`summary.pad` 引发的 x/宽 3 条 + 字形盒 3 条 + 行盒 1 条 + 投影 1 条。）

### 2.2 探针自身 3 处口径 bug（已修正并重跑红基线，保证红/绿同版探针）

1. `summary.tiles1.top/h`：把「容器（含 padding-top）」当「宫格行」写 want（164/72）→ 改为容器 `148/88`，另补 `summary.tileTops [164,164,244,244]`。
2. `models.trackW`：want 写成 4 行同值 192；设计轨道 = `fill_container`，末行「6%」百分比盒窄 7 → PNG 实测行 1 轨道 `167..358.5`(=192)、行 4 `167..365.5`(=199) → want 改 `[192,192,192,199]`（±1）。
3. `summary.shadow`：Chrome 序列化会补尾随 spread `0px` → want 与序号 12/15 同口径写成 `… 20px 0px`。
   另 `trend.img.src` 误读元素 `src`（uni-image 在 H5 把 src 放进内部 img/背景图）→ 改为从 innerHTML 取 data-URI 并 `atob` 解码回 SVG，新增 5 条硬断言：`viewBox="0 0 358 150"` · 4 条网格线 · 7 个数据点 · 折线 `#2563EB` · 面积 `rgba(191,219,254,0.35)`。

## 3. 覆盖度（267 条 checks 抽样）

- 整页：`innerWidth 430` · `docScrollWidth 430` · `docHeight 1138`(=设计帧高) · 溢出 0 · 文案缺失 0 · 卡 5 · input 0 · **无 TabBar**。
- 导航：96 高 / padding `48px 16px 12px` · 返回字形盒 `26×36 @x16` · 标题 x54 fs17/700/lh25.5/`#0F172A` · 月份胶囊 `299..414 h30 r10 #F1F5F9 padding 0/12` · 日历盒 `17×22.5` · 文字 fs12/500/lh14.4/`#475569` · 下箭头盒 `18×24`。
- 汇总卡：`108..336(228)` · r18 · **仅投影**（`chkD` 反向断言未声明 border）· 标题 h20 @128 · 宫格行 `164..236 / 244..316`（各 178 宽 gap 9）· 四值 `1.24M/3.86B/¥12,860/¥2,140` fs17/700/h26 + 逐值色 `#1D4ED8/#15803D/#B45309/#7C3AED` · 标签 fs10/400/h16/`#64748B`。
- 趋势卡：`348..570(222)` · ring `#EEF2F7` · 标题行 20 · 图例点 `9×8 r4 #2563EB` + 图例文字右边界 394 · 图 `358×150 @400` · 横轴 7 标签 `20.12` 宽 @`122.95`（x `56/107/159/210/261/313/364`）。
- 模型卡：`582..766(184)` · 行内容 `638/668/698/728` · 名称列 131 · 轨道 `x167 w192/199 h10 r5 #F1F5F9` · 填充 `81/60/41/12px` + 逐行色 · 百分比 `42/31/21/6%` 右 394。
- 成本卡：`778..985(207)` · 3 行 + 合计行 `924..965`（padding 10 r10 `#F8FAFC`）· 合计值 fs14/800/lh21/`#1D4ED8` 右 384。
- 明细卡：`997..1057(60)` · 图标盒 `20×27 @x36` · 文字 fs13/500 @x64 · chevron 盒 `22×28` 右 394。
- 底部说明：`1057..1138` · 两行 11px h16（墨迹实测 1084..1095 / 1100..1110 = 实现同带）。

## 4. 交互相（三出口 · 各两轮 · serve 实收请求行逐字节比对）

| 出口 | 两轮一致 | 结论 |
|---|---|---|
| `?scenario=back` | ✅ 逐字节相同（2 行） | hash 不变 · 无 toast · 零写请求 · `cardCount 5`；`windowMark=null` 证明 **uni H5 无栈时降级为整页重载**（第二次 GET 同 URL），非重复取数 |
| `?scenario=month` | ✅ 逐字节相同（2 行） | 点开真 `uni-picker` 覆盖层（`uni-picker-container uni-date-select` + `uni-picker-action-confirm`）→ 确认 → **第二次真取数 `GET /usage/summary?month=2024-06`**（首屏 `?month=2026-09`） |
| `?scenario=detail` | ✅ 逐字节相同（1 行） | 无落点（画布 30 页无明细页）→ **no-op**：hash 不变 / 无 toast / 无新请求（台账待拍板） |

证据：`review-序号22-{back,month,detail}-run{1,2}.json` · `requests-序号22-*-run{1,2}.txt` · `interactions-序号22-三出口.txt`。

## 5. 像素对账（实现 430×1138 截图 vs 设计 PNG 430×1138）

`cmp-bands-6-design-vs-impl.py`：**命中 39 / 未命中 8**，命中处位移中位 0（内容列 0 位移 14 个，min −3 / max +3）。

未命中判读（详见 `cmp-序号22-设计PNGvs实现截图-结构带.txt` 末尾）：

1. 内容列 `[107, 350, 353, 359]` = 汇总卡投影的**衰减尾**（设计 349..359 仍有 252..254 淡染、实现 348+ 纯白；起点/峰值两侧同值 238,240,243）→ Figma/Chrome 模糊衰减步长差（1~3/255），非页面缺陷。
2. 明细/进度列 `[839, 843, 869, 873]` = 成本行右对齐值的 **H5 回退字体字距/右留白**（设计墨迹 353..391、实现 355..393，同为右对齐 394、墨迹同宽 39）→ 非页面缺陷。

文本行对账 `cmp-textrows.py`：21 行 ↔ 21 行，8 行完全相同，其余 ±1（H5 回退字体墨迹上下沿），无 2px 级位移。

## 6. 质量门

| 门 | 结果 |
|---|---|
| `npm test` | **1181/1181 · 72 files 连跑两轮**（16:18:51 / 16:19:28） |
| `npm run type-check` | exit 0 |
| `npm run build:mp-weixin` | DONE；`pages/usage/{index.js,index.json,index.wxml,index.wxss}` 齐备 + `app.json` 注册；wxss 含本轮设计值 `padding:20px 16px` · `box-shadow:0 6px 20px rgba(15,23,42,.06)` · `height:22.5px` · `height:24px` · `line-height:14.4px` |
| `npm run build:h5` | DONE（像素对账与截图所用产物） |
| `review-artifacts.py` | 22/22 台账路由的 mp-weixin 三件套齐备且已注册 |
| `check-mock-fixtures.py --mock api-22` | **5 PASS + 反向体检 PASS / FAIL 0**（本轮新补 5 条：四宫格/月份切换/7 逐日点/4 模型占比/成本构成） |
| 共用消费方回归门 | 序号 2 工作台（同用 `usage-model.ts` 的 D3 环形/图例口径）`__measure-workbench.html` 复跑 **103 条 0 失败**（两轮 `docH 1146` 全等） |

截图：`logs/screenshots/20260916-序22-用量概览-checks轮-h5-430宽.png`（430×1138 = 设计帧尺寸，同件入 `.agents/state/evidence/`）。

## 7. 口径与遗留

- 本页定标（写入状态文件 §5.15）：图标字形盒 = 设计声明宽 × 字号×1.5；文本行盒**显式 height 优先**（标题 20 · 值 26 · 标签 16 · 合计值 21 · 底部 16）、无显式 height 走 `lineHeight 1.2`（12 → 14.4）；设计里「容器 padding-top N + 行」的容器盒 = N + 行盒（探针要分两层写）；`stroke{align:center,thickness:1}` → ring，`effects.drop_shadow` → box-shadow，**逐卡断言不统一**（汇总卡只有投影、其余四卡只有描边）。
- 登记不照抄项：占比条填充 = 百分比 × **轨道宽**（设计声明 × 卡外层宽 398，设计自身不自洽）· 横轴末位标签设计自行左移 8px（实现按数据点 x 居中）· 趋势图为 data-URI `<image>` + DOM 横轴标签（mp-weixin 不能内联 svg）· 图标 CSS 占位（D5）· 明细入口无落点（待拍板）· 卡片 ring 比设计中心描边外移 0.5px · 页面数据全部来自 `GET /usage/summary`（字段级 schema 为推断）。
- 工具侧发现：`review-measure.sh` 的 mock 参数必须是**仓库相对路径**（`.agents/state/h5-measure/api-22`）；传裸 `api` 会变成 `<root>/api` → 整页 404、checkFails 假红（本轮回归门首跑 19 条假失败即此，SKILL §5 已记该陷阱）。
