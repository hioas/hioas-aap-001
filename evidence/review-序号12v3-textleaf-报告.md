# 序号 12-v3（page-29「新增报价单-保存成功」）文本叶子维度收口 — 报告

- 轮次：`aap-tdd-run-20260916-2000`（cron）
- 设计真源（人工指令 C）：**同一画布当前状态**。重抓帧「新增报价单-保存成功」+ `layer_id 49d2fa52-959d-4415-9fda-edf38415d6bd`
  → `design.json` sha256 `cdd34a51d7afcf78fd10976d8987e0aa919e6e50ba5ee7f17d9b8326754dc55b`，与留证**逐字节相同** → 无漂移。
- 测量面：`__measure-textleaf.html?route=%23/pages/quote-form/success`（带参路由，与载体页 iframe src 一致）+ mock `api-12-v3`
  → `evidence/textleaf-12-v3.json`（leafs 29 · docH 1018 = 设计帧高）。

## 1. RED（收口前）— 11 条待判读 class

`evidence/red-序号12v3-textleaf-待判读11.txt`（`python .agents/state/textleaf-audit.py 12-v3`）：

| class | 审计 want（= fs × lh1.2） | 实现 | 设计里该文本所在的容器声明 |
|---|---|---|---|
| `btn__text` | fs14 → 16.8 | 18 | 次按钮 `26d36f5b` / 主按钮 **height=48**（textAlignVertical=middle） |
| `card__title`（结果摘要 fs15） | 15 → 18 | 20 | 摘要标题行 `c0b98aa4`（竖条 h16 + 文本） |
| `card__title--sm`（已带出模型 fs14） | 14 → 16.8 | 18 | 带出模型标题行 `831dc5d9` 内含 remixicon 字形层 `f6b7fbbd` fs16 → 字形行盒 24 |
| `count-chip__text` | fs10 → 12 | 18 | 模型数标 `22acf5bc` **height=18** + padding [0,8,0,8] |
| `env-chip__text` | fs10 → 12 | 18 | 环境小标 `2a6f28d0` **height=18** + padding [0,8,0,8] |
| `no-bar__copy-text` | fs12 → 14.4 | 16 | 复制按钮 `6bb5859a` **height=32** + padding [0,12,0,12] |
| `srow__label` | fs13 → 15.6 | 18 | 摘要行 4 个：padding [10,0,10,0] + alignItems=center |
| `srow__value` | fs13 → 15.6 | 18 | 同上（与标签同行） |
| `status-chip__text` | fs11 → 13.2 | 20 | 状态标 `c9fda041` **height=20** + padding [0,8,0,8] |
| `tag__text`（--on / --off） | fs12 → 14.4 | 16 | 模型标签 `5290721b` / `1f778b64` **height=28** + padding [0,12,0,12] |

## 2. 判据与判读（判据优先级：①设计显式 height ②design PNG 盒/带实测 ③fs × lh1.2；②③冲突以 ② 为准）

逐类 ink 带对账：`evidence/cmp-序号12v3-文本叶子行盒-逐类带.txt`
（窗口 = 该 DOM 叶子 rect 左右 ±1、上下 ±14；打印设计与实现两图在同一窗口里的墨迹带）。

| class | 设计墨迹带 | 实现墨迹带 | 判读 |
|---|---|---|---|
| `btn__text` 继续设置模型报价 | 901..915 | 901..915 | 相同 |
| `btn__text` 返回报价单列表 | 959..972 | 960..973 | +1（H5 回退字体墨迹） |
| `card__title` 结果摘要 | 409..423 | 409..423 | 相同 |
| `card__title--sm` 已带出模型 | 677..690 | 678..691 | +1 |
| `count-chip__text` 已勾选 3 个 | 526 / 530..539 / 543 | 526 / 530..539 / 543 | 胶囊边界与墨迹**逐值相同** |
| `env-chip__text` 生产环境 | 488 / 492..501 / 505 | 488 / 492..501 / 505 | 逐值相同 |
| `no-bar__copy-text` 复制 | 309..320 | 309..320 | 相同 |
| `srow__label` ×4 | 453 / 491 / 529 / 568 | 453 / 491 / 529 / 568 | 逐值相同 |
| `srow__value` ×3 | 453..466 / 491..504 / 569..581 | 453..466 / 491..504 / 569..581 | 逐值相同 |
| `status-chip__text` 草稿 | 604 / 608..618 / 623 | 604 / 609..619 / 623 | 胶囊边界相同，墨迹 +1 |
| `tag__text` ×4 | 708 / 718..729 / 735 · 734..735 / 753..765 / 772 | 708 / 718..729 / 735 · 734..735 / 753..765 / 771..772 | 胶囊边界与墨迹逐值相同（个别 AA 行 ±1） |

**盒算术（判据 ② 的可执行化，本轮对唯一不受定高盒约束的一类做推导）**：
`srow__label / srow__value`（fs13）所在摘要行 `fba2ebb8 / 11050f12 / bb193b6b / dd3a795d` 均为
`padding [10,0,10,0] + alignItems=center`，行高由内容决定 → 行高 = 10 + 行盒 + 10。
设计 PNG 实测相邻行同字号标签的墨迹起点差 = **38**（453→491）：
`pitch = 行高 = 10 + L + 10 → L = 18`（若按声明模型 15.6，则行距 ≈ 37，与实测不符）⇒ **行盒 18**，与实现一致。

其余 8 条均落在设计**显式声明 height** 的定高盒内（胶囊 18/20/28 · 复制按钮 32 · 按钮 48）→ 文本行盒不承重
（状态文件 §5.18 口径：固定高盒内行盒变动只移动墨迹 ≤1px，不在此 churn）。

整页分区并排对账：`evidence/cmp-序号12v3-分区并排对账.txt` → **24/25 命中**
（卡1 6/6 · 卡2 8/8 · 卡3 5/5 · 底栏 5/6；唯一未命中 = 设计底栏 954..955 的 2 行带（次按钮 ring AA），
实现该带并入邻带 —— 与既有「Figma center 描边 vs ring 可见行外移 1px」同族，非页面缺陷）。

## 3. GREEN（收口后）

- `python .agents/state/accept-12v3-textleaf.py` → `textleaf-accept.json` +9 键（覆盖 11 条 class），条目内写明容器声明与 PNG 佐证。
- 审计复跑：`evidence/green-序号12v3-textleaf-待判读0.txt` → **待判读 class 0 · 已核定 11**（设计文本叶子 29 · 匹配 25 · 未渲染 0）。
- **本轮无源码改动**（11 条全部为非偏差）→ 未改 `src/**`。

## 4. 回归门（无源码改动也要证明页面仍绿）

- 载体页 `__measure-quote-success.html` 两轮 430 宽实测：`evidence/review-序号12v3-tl-run{1,2}.json`
  → `checkCount 259 · checkFailCount 0 · overflowing 0 · docH 1018 · docW 430 · missingTexts []`；
  两轮独立测量 **31/31 字段全等、不一致 0**；`requests-序号12v3-tl-run{1,2}.txt` 各 2 行且**逐字节相同**（`GET /quotes/q9` + `GET /credentials/c1`，只读）。
- 430 宽整页截图 `evidence/20260916-2012-序12v3-新增报价单保存成功-文本叶子维度收口-h5-430宽.png`
  与 15:0x 轮截图 `cmp` **逐字节相同**（本轮未改样式，无视觉漂移）。
- `npm test` **1185/1185 · 72 files 连跑两轮**（20:05:47 / 20:06:19，另存转录 `evidence/green-序号12v3-全量轮.txt` 20:07:24 同值）· `npm run type-check` exit 0。
- 未重跑 `build:mp-weixin` / `build:h5`（无 `src/**` 改动，沿用上一轮产物；`review-artifacts` 22/22 未受影响）。

## 5. 工具

- `tl-page-bands.py` 新增 `--regions "区名:y0:y1,..."`（换页时按设计 PNG 的卡片色带显式给窗口，
  不再只能跑内置的 page-26 分区）；本轮用它在 page-29 上跑出 24/25。
