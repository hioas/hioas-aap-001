# 序号 7（page-7-2「检测未通过报告」）文本叶子维度收口 — 报告

- 轮次：`aap-tdd-run-20260916-2000`（cron · 本轮第二页）
- 设计真源（人工指令 C）：**同一画布当前状态**。本轮未重抓该帧（17:45 轮已重抓 `page-7-2`、`design.json` sha256 `f2780416…` 逐字节相同；
  载体页 checks 轮（11:3x）亦已确认无漂移）→ want 取自 `.calicat/raw/pages/page-7-2/design.tree.json` + 设计 PNG（430×1110）。
- 测量面：`__measure-textleaf.html?route=%23/pages/report-failed/index?reportId=DR-7` + mock `api`
  → `evidence/textleaf-7.json`（leafs 38 · docH 1111 = 设计帧高 +1 小数链）。

## 1. RED（收口前）— 10 条待判读 class

`evidence/red-序号7-textleaf-待判读.txt`（`python .agents/state/textleaf-audit.py 7`）：
`card__label` / `card__sub` / `detail__title` / `detail__score` / `dim__label`(×8) / `dim__score`(×8) /
`score` / `verdict-row__text` / `veto-box__text` / `weight-box__text`。

| class | 审计 want（= fs × lh1.2 或显式 h） | 实现 | 判据与决定性证据 |
|---|---|---|---|
| `card__label` `card__sub` | fs12 → 14.4 | 18 | **盒算术**：封面顶行 `1093d116`（fit_content · 仅两个文本叶子）→ 行高 = 行盒；封面卡 `07b82bea` padding 20 ⇒ 行顶 = 108+20 = 128，设计墨迹 131 ⇒ 偏移 3 = (L−12)/2 ⇒ **L = 18**（= 实现） |
| `detail__title` `detail__score` | fs14 → 16.8 | 20 | D2标题行 `b2bba46b`（fit_content）→ 行高由文本定；两侧同步 +2（相对差 0）= 回退字体墨迹；结构带 19/19 命中 |
| `dim__label` `dim__score` | fs12 → 14.4 | 18 | 评分项行 `df5c9dfc`（fit_content）；PNG 四行墨迹起点设计 436/466/496/526 = 实现 437/467/497/527 —— **行距两侧同为 30** |
| `score`（「54」） | fs38 → 45.6 | 57 | **判据②**：设计墨迹 175..204 = 实现 178..207（带高 30 相同、起点 +3 = 38px 数字的回退字体基线偏移）；57 由本页 checks 轮按设计 PNG 定（`review-序号7-checks-报告.md` §5：`.score` 行高 57px = 38×1.5），**同卡结论胶囊边界 设计 176/203 = 实现 177/204 反证块高 57**（若 45.6 则其下整体上移约 11px） |
| `verdict-row__text` | fs12 → 14.4 | 18 | 两行块：**第 1 行逐值相同**（310..323）；第 2 行差来自**换行点不同**（设计 line2 墨迹 75 列 / 实现 86 列）；行盒由同卡 `veto-box` 填充盒直证（下条） |
| `veto-box__text` | fs12 → 14.4 | 18 | **判据②（决定性）**：一票否决条 `c93a930a` padding 12 的填充盒（#FEF2F2）在 x=200 列实测 —— 设计 234..293 = 实现 235..294，**盒高两侧同为 60 = 12 + 2×18 + 12 ⇒ 12px 行盒 = 18**（14.4 会给出 52.8） |
| `weight-box__text` | **h=36（显式）** | 18 | **判据①**：叶子 `18dda7b2` 显式 `height=36 = 2 × 18`（fs11 · w=fill_container）⇒ 行盒 18 = 实现；实现 2 行块高 36 ✓（墨迹第 2 行差 = 换行点不同：设计 25 列 / 实现 14 列） |

## 2. 整页结构对账

`evidence/cmp-序号7-设计PNGvs实现截图-结构带.txt`（`cmp-bands-6`，±3）：
- 卡片内容区 x=36..394：命中 **34/38**（未命中 376/379/385 = 封面卡投影衰减 AA · 707 = 换行差 1 字），位移中位 **+1**；
- 明细条/进度条列 x=194..356：命中 **19/19**；
- 合计 **53/57 命中 · 0 结构漂移**。

`png-rowclass` 逐行判卡片/间隙：全区段（108..132 / 133..142 / 143..176 / 177..187 / 188..193 / 194..203 / 204..233 / 234..293 一票否决条 /
294..310 / 311..321）**设计与实现一一对应，最大差 +1**；一票否决条盒高两侧同为 60。

## 3. GREEN（收口后）

- `python .agents/state/accept-7-textleaf.py` → `textleaf-accept.json` **+10 键**（覆盖 10 条 class，`dim__*` 各覆盖 8 个叶子）。
- 审计复跑 `evidence/green-序号7-textleaf-待判读0.txt` → **待判读 0 · 已核定 10**（设计文本叶子 38 · 匹配 38 · 未渲染 0）。
- **本轮无源码改动**（10 条全部为非偏差）。

## 4. 回归门（无源码改动也要证明页面仍绿）

- 载体页 `__measure-report-failed.html` 两轮 430 宽实测 `evidence/review-序号7-tl-run{1,2}.json`
  → phase1/phase2 各 `checkCount 201 · checkFailCount 0 · docH 1111 · docW 430 · missingTexts []`；
  两轮独立测量 **逐相 30/30 字段全等、不一致 0**；`requests-序号7-tl-run{1,2}.txt` 各 1 行且**逐字节相同**（`GET /reports/DR-7`，只读）。
- 430 宽整页截图 `evidence/20260916-2023-序07-检测未通过报告-文本叶子维度收口-h5-430宽.png`（430×1180，页内容 1111）。
- `npm test` **1185/1185 · 72 files 连跑两轮**（20:05:47 / 20:06:19）· `npm run type-check` exit 0（本轮全程无 `src/**` 改动，故未另跑 build）。

## 5. 累计进度（文本叶子维度）

全量审计（`evidence/textleaf-audit-20260916-2015.txt` 之后）：序号 1 / 6 / 12-v1 / 12-v2 / 12-v3 / 7 已归零；
待判读 **84 → 74**（本轮 7 收口 10 条）· 已核定 **68 → 78**。下轮按待判读数推进：10.1(9) / 22(9) / 4-v1(8) / 5(8) / 10(7) / 12(6) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 20(2) / 4(2) …
