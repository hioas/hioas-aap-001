# 序号 5 · 检测进行中 2（page-5-2）· 队列 8「设计期望值 checks」复核报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1025`（2026-09-16 10:25 起）
- 帧：**「5. 报价端·小程序 ｜ 【检测验真】检测进行中 2」** · `layer_id b2d065a3-34a0-45e3-8e2e-b9bd9a810126` · 抓取 id `page-5-2`
- 路由：`/pages/detecting/index?jobId=j1` · 载体页 `.agents/state/h5-measure/__measure-detecting.html` · mock 目录 `api`
- 设计真源：`.calicat/raw/pages/page-5-2/design.json`（+ `design.tree.json` / `.agents/state/page-5-2-nodes.txt`）+ 设计 PNG 色带实测

## 1. 设计帧重抓（人工指令 C：复核前必须重抓并逐字节比对）

- 编辑器未打开时整包重抓失败（`请先在浏览器中打开文件`）→ `cmd /c start "" https://www.calicat.cn/design/2095515676955668480` 拉起后重抓成功。
- `design.json` sha256 = `4ed8ad581e7b836037e3f4c07fe43c1e4411c60eabc1199f9b9ff678e7a1a792`，
  与实现所依据的留证 **逐字节相同**（`cmp` 报 BYTE-IDENTICAL）→ 画布当前状态 = 实现版本，**无漂移**。

## 2. 期望值口径（两类来源，逐条可复现）

**A. 声明值**（design.json）：`padding [48,16,12,16]` · chip `h24 r12 padding 0 8` · 卡 `r18 padding 20` ·
描边 `stroke{center,thickness 1}` · `effects drop_shadow(0,6,20,rgba(15,23,42,0.06))` · 各行 `fontSize/fontFamily`
显式 `height`（13→18 / 12→18 / 11→16 / 15→22）· 全部中文文案。

**B. 盒子高度 = 设计 PNG 色带/墨迹实测**（命令写在载体页头注释，可复现）：

| 量 | 值 |
|---|---|
| 设计 PNG | 430×934 |
| 顶部栏 | 0..95 → **96**（= padding 48 + 图标行框 36 + 12） |
| 卡1 总进度 | 108..303 → **196**（20 + 标题行 26 + 16 + 条 10 + 12 + 元信息 18 + 16 + 成本块 58 + 20） |
| 卡2 分项 | 316..749 → **434**（20 + 标题 22 + 16 + 8×34 + 7×12 + 20） |
| 提示卡 | 762..833 → **72**（16 + 内容 40 + 16；文案两行 ink 784..795 / 800..810 = 垂直居中，行距 16） |
| 底栏 | 850..933 → **84**（12 + 48 + 24） |
| 8 行图标块 | 375/421/467/513/559/605/651/697 → 行顶 374…，**行高 34、行距 46** |
| 进度填充 | 36..243 → **208**（= 58% × 358；设计树写 209 是陈旧值，PNG 为准） |
| 状态 chip 右缘 | 394（行）/ 414（顶部栏 chip 351..413 宽 63） |

**图标盒子口径**（沿用序号 4 定标）：盒子 = 设计图层 width × 字号×1.5 行框（24→36 / 20→30 / 18→27），形状画进 `::before`。

## 3. TDD 红 → 绿（同一份 237 条 checks 探针）

- **红基线**（`git stash push -- aap-client/src/pages/detecting/index.vue` 复现修复前代码 → `build:h5` → 同一份探针两轮）：
  **phase1/phase2 各 95/237**，两轮完全一致 · `docH 900`（设计 934）。
  转录：`.agents/state/evidence/red-序号5-checks-设计期望值偏差.txt`（394 行）
- **绿**：**0/237**，phase1/phase2 都 0 · `docH 934`（= 设计帧高）· `overflowingCount 0` · `docScrollWidth 430 = innerWidth` · `missingTexts 0`。
  转录：`.agents/state/evidence/green-序号5-checks-设计期望值.txt`
- **两轮独立测量**：`review-序号5-checks-run{1,2}.json` → `cmp-measure-runs.py` 报 **32/32 字段全等、不一致 0**（phase1 与 phase2 各一次）；
  红基线的两轮同样全等。

## 4. 修掉的 9 类偏差（每类都能对到设计证据）

| # | 偏差（修前 → 修后） | 设计依据 |
|---|---|---|
| 1 | 顶部栏高 **84 → 96**（返回图标盒 24×24 → 26×36） | 设计 594997da 图层宽 26 / fontSize 24 → 行框 36；PNG 顶部栏 0..95、chip 顶 54 = 48+(36-24)/2 |
| 2 | 卡1 **184 → 196**（标题行 24 → 26：`58%` line 24 → 26） | PNG：卡顶 108 + 20 + 行 + 16 = 进度条 170 → 行 26 |
| 3 | 卡2 **416 → 434**（行高 32 → 34、行距 44 → 46） | 设计 `height=18 / 16`（13px 名 + 11px 详情 = 34）；PNG 图标块行距 46 |
| 4 | 提示卡 **68 → 72**（文案行高 16.8 → 16 + `align-self:center`） | PNG 762..833 = 72；文案 ink 784..810 居中 |
| 5 | 成本块 **52 → 58**（标题/副文案行高 14.4/13.2 → 18/16） | 设计 ff72fdea `height=18`、f44b1675 `height=16`；PNG 成本块 226..283 = 58 |
| 6 | 元信息行 **14 → 18** | 设计 PNG：条底 179 + 12 = 192，+18 + 16 = 成本块 226 |
| 7 | 卡2/提示卡描边 `border:1px` → `box-shadow: 0 0 0 1px` | 设计 `stroke{align:center}` 不占布局 → 用 border 会把内容宽 358 压成 356、行左 36→37、chip 右 394→393 |
| 8 | 卡1 缺设计 `effects` 投影 | 设计 88f1ee17 `drop_shadow(0,6,blur 20,rgba(15,23,42,0.06))` |
| 9 | 7 个图标盒 ≠ 设计图层（返回 9×9 / 盾牌 14×14 / 分项 8×8·13×13 / 提示 0×0 / 历史 13×13 → 26×36 / 22×30 / 20×27 / 22×30 / 22×30），形状改画进 `::before` | 设计各图层 width + fontSize×1.5 行框（D5：形状仍为 CSS 占位） |

## 5. 像素对账（设计 PNG vs 实现 430 宽截图）

证据：`.agents/state/evidence/cmp-序号5-设计PNGvs实现截图-色带.txt`（脚本 `.agents/state/cmp-bands-5-design-vs-impl.py`，±1 行容差）

- x=62 一列 41 个粗边界 **36 命中**；x=25 · 14 中 11；x=404 · 17 中 14；x=215 · 23 中 17。
- **关键结构行全部命中**：顶部栏 96 · 卡1 108..303 · 进度条 170/180 · 成本块 226/284 · 卡2 749 · 提示卡 765/833 · 底栏 850/862/910 ·
  8 个图标块 377/423/469/515/561/607/653/699。
- 未命中的 22 行**全部**是两类，已逐条判读、非页面缺陷：
  1. **卡1 投影的渐变台阶行**（设计 99/106/111/121/132 与 294/304/314/319/322/325/328；实现 102/106/111、290/301/309/312/319）
     —— 同一枚 `drop_shadow(0,6,20)` 在 Figma 渲染器与 Chrome 的衰减步长不同，两端渐变范围一致；
  2. **字形墨迹边界**（chip 内文字 63/68 vs 69、底栏文案 882/887 vs 893）：H5 回退字体的墨迹比设计字体小 4 行，
     但**块级几何与居中位置逐项相同**（底栏文案 ink 中心 设计 886.5 / 实现 886.5）。
- 提示卡文案 ink：设计 784..795 / 800..810 ↔ 实现 784..795 / 801..811（第一行逐行相同，第二行 +1）。

## 6. 交互相（有牙齿）

- `?scenario=interaction`：点「查看历史检测报告」→ toast「历史检测报告可在凭证列表中查看」· `hashUnchanged true` · 行数仍 8 ·
  serve.py 实收 **10 行全部是成对 `GET /api/v1/detection-jobs/j1` + `/results`**（5s 轮询 5 次），**零写请求**
  （证据 `requests-序号5-int-run{1,2}.txt`），也证明轮询真实发生。
- 交互分类沿用台账：返回 = navigation(navigateBack)；「查看历史检测报告」= client-only（画布 30 页无该页，不臆造路由）。

## 7. 质量门（修后）

- `npm test` **1168/1168 · 72 files 连跑两轮**（`green-序号5-全量轮与门槛.txt`）
- `npm run type-check` **exit 0**
- `npm run build:mp-weixin` DONE → `dist/build/mp-weixin/pages/detecting/index.{js,json,wxml,wxss}` 四件套齐备
- `npm run build:h5` DONE · 430 宽截图 `evidence/20260916-1042-序号5-检测进行中-checks轮-h5-430宽.png`（`logs/screenshots/` 同件）
- 未装微信开发者工具 → mp-weixin 只到「编译产物存在」，真机验收留人类。

## 8. 遗留（不逃避，均为既有 missing-prd，非本轮引入）

设计 8 行示例名在 22 份 PRD 零命中（行名以服务端 `probe_name` 为准）· 设计「已完成 7 / 12」与 8 行不自洽（进度取服务端 `progress`）·
`ProbeStatus` 无 RUNNING/QUEUED（三态为映射字典）· `DetectionJob.status` 三份 PRD 三套枚举（徽章只映射 QUEUED/RUNNING）·
设计无完成/失败态（不自动跳报告页）· 详情行度量摘要依赖服务端 `detail`（字段级 missing-prd）· 轮询 5s 为前端取值。
