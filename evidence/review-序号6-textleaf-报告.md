# 序号 6「大模型检测报告 · 多维度专业版」文本叶子维度收口报告

- 日期：2026-09-16 19:1x（cron 轮 `aap-tdd-run-20260916-1915`）
- 设计真源：Calicat 文件 `2095515676955668480` · 画布 `2095515676976640000` · 帧 `page-6`（layer_id `0f0755e4-…`，帧名「大模型检测报告 · 多维度专业版」）
  → `.calicat/raw/pages/page-6/design.tree.json` + 设计 PNG `.agents/state/design-shots/page-6.png`（430×5342，sha256 `a505a58c…`，17:45 轮已重抓比对无漂移）
- 实现：`aap-client/src/pages/report/index.vue` · `src/utils/report-model.ts` · 路由 `/pages/report/index`
- 载体页：`.agents/state/h5-measure/__measure-report.html`（430 宽 iframe，本轮 228 → **243 条 checks**）

## 1. 本轮入口（上一轮留下的 27 条待判读 class）

`python .agents/state/textleaf-scan.py 6 && python .agents/state/textleaf-audit.py 6`（先重扫，保证 DOM dump 与当前构建一致）：

```
== 序号 6  page-6  文本叶子 294 · 匹配 273 · 未渲染 7 · 待判读 class 27 · 已核定 0
```

27 条按「设计声明值 vs 实现」分诊为三类：

| 类别 | 条数 | 处理 |
|---|---|---|
| 声明值真偏差（字重/字号/行盒） | 7 组 | 改代码（先红后绿） |
| 结构真偏差（本轮 PNG 对账新发现） | 2 处 | 改代码（先红后绿） |
| 审计模型口径差（多行块高 vs 单行行盒 / 设计自身矛盾 / 设计渲染行盒） | 18 组 | 逐类 PNG 实测后登记 `textleaf-accept.json`（非偏差） |

## 2. 红基线（探针版本 = 最终版 / 源码未改）

`git stash push -- aap-client/src/pages/report/index.vue aap-client/src/utils/report-model.ts` → `npm run build:h5`
→ `bash .agents/state/review-measure.sh 6-tl-red __measure-report.html .agents/state/h5-measure/api 5342` 两轮：

```
phase1/phase2: checkCount=243 checkFailCount=16 docH=5343
  FAIL card4.summary.h: got 24 want 16
  FAIL card5.finding.title.fw: got "700" want 600
  FAIL tl.ghostExport.fw: got "400" want 500
  FAIL tl.findingTitle.fw: got "700" want 600
  FAIL tl.dimText.fw: got "400" want 500
  FAIL tl.dimScore.fw: got "400" want 700
  FAIL tl.pillStatus.fw: got "400" want 600
  FAIL tl.pillValue.fs: got null want 11
  FAIL tl.pillValue.fw: got null want 400
  FAIL tl.summary.lh: got 24 want 16
  FAIL tl.summary.outer.h: got 32 want 24
  FAIL tl.groupSep.count: got 0 want 6
  FAIL tl.groupSep.h: got null want 1
  FAIL tl.groupSep.bg: got null want "rgb(238, 242, 247)"
  FAIL tl.groupTitle.top: got 1513 want 1504
  FAIL tl.cardTops: got "105,533,896,1425,4402,4824,5122" want "105,533,896,1425,4400,4822,5120"
```
两轮 JSON **逐字节相同**、`cmp-measure-runs … phase1` 25/25 字段全等（转录 `evidence/red-序号6-tl-checks-设计期望值偏差.txt`）。
单测红基线：`evidence/red-序号6-textleaf-单测基线.txt`（3 failed / 53：两条新结构用例 + 一条模型用例）。

## 3. 修掉的 7 组声明值偏差（设计声明 → 实现）

| 类 | 设计叶子 | 声明 | 修前 | 修后 |
|---|---|---|---|---|
| `.action__ghost-text` 导出 PDF | `a3023014` | SourceHanSans-**Medium** | 400 | **500** |
| `.finding__title` 发现标题 | `2ba0333a` | SourceHanSans-**SemiBold** | 700 | **600** |
| `.dim__text` 维度名 | `177b7f5f` | SourceHanSans-**Medium** | 400 | **500** |
| `.dim__score` 维度分 | `0947f700` | SourceHanSans-**Bold** | 400 | **700** |
| 状态标签 pill 未申报/仅证据/不可测 | `e247efe0` / `1b3c9a9f` / `66800e15` | fs10 + **SemiBold** | 400 | **600** |
| G 组「值 pill」 | `ef69fd0e` | **fs11** / Regular（w142 vs 实现 127） | fs10 | **fs11 / 400** |
| 明细说明行盒 | `068c8976`（frame `8485b93b` h=24 = pad-top 8 + 行盒 16） | 行盒 **16** | 24 | **16** |

> 「值 pill」与「状态标签 pill」在设计里是两套规格，实现原本共用一个类 ⇒ 模型新增 `statusIsValue`
> （`!meta && !status && !scored && value !== ''`），模板加 `item__pill--value` 修饰。

## 4. 修掉的 2 处结构偏差（设计 PNG 实测抓出）

### 4.1 明细说明行盒把 frame 的 24 当成了行盒（整卡 +8px 偏移）

设计 `明细说明` frame `8485b93b` **h=24 = padding-top 8 + 行盒 16**；实现写成 `line-height: 24px`
→ 盒高 8+24 = 32（多 8）且单行墨迹在 24 行盒里居中（低 4px）。

`png-textbands` 同窗口对账（x=33..385）：

```
                设计            实现（修前）      实现（修后）
说明行 ink      1476..1486      1480..1490       1476..1486   ✅
组标题 A ink    1508..1520      1516..1528       1508..1520   ✅
```

### 4.2 分组之间缺 1px 分隔线（每组差 1px，累计 -6px）

设计在每组之后有 `spacer 16` + `分隔线X`（h=1，rgba(238,242,247,1)，共 A–F 六条）；实现只有 `margin-top:16`
→ 组标题 ink 间距 437（实现自洽算术）而设计是 **438**。

`stroke-rows.py eef2f7`（x 40..390）：

```
设计 1926..1927 / 2321..2322 / 2716..2717 / 3197..3198 / 3592..3593 / 3987..3988   （六条）
修后 1926..1926 / 2321..2321 / 2716..2716 / 3197..3197 / 3592..3592 / 3987..3987   （六条，同起点）
修前 （该区间 0 条）
```

修后整卡逐条对账（`evidence/cmp-序号6-明细卡纵向对账-修后.txt`）：

```
组标题 A/B/C/D/E/F/G   设计 1508/1946/2341/2735/3217/3611/4006
                       实现 1508/1946/2341/2736/3217/3612/4006      （±1 内）
权重说明盒             设计 4296..4368 = 实现 4296..4367
明细卡下缘→风险卡标题   设计 4423..4437 = 实现 4423..4437              ✅
cardTops               设计 [105,533,896,1425,4400,4822,5120] = 实现同值
整页 docH              5342（设计）vs 5341（实现，−1）
```

## 5. 登记为「非偏差」的 18 组（19 条 accept 记录，覆盖 23 个聚合项）

判据优先级：①设计显式 height ②design PNG 盒/带实测 ③fs × lineHeight（②③冲突以 ② 为准）。

- **多行块高 vs 单行行盒**（审计模型口径差）：`disclaimer__body` h=51 = 3×17 · `evidence-row__value` h=32 = 2×16 ·
  `finding__body` h=34 = 2×17 · `note-box` h=48 = 3×16 · `verdict-box__text` h=38 = 2×19
- **设计渲染行盒 ≠ fs×1.2**（PNG 逐条相同）：`card__title`（封面 18 / 其余 20）· `metric__label` 15 ·
  `metric__sub` 14 · `metric__value` 24 · `group__title` 18 · `score__meta-text` 17 · `dim__text`/`dim__score` 16
- **设计自身矛盾**：`radar__label` 叶子声明 `lineHeight 1.31`（→14.41）却又给 `h=12.43`，实现按 1.31 落地，
  PNG 墨迹 962..972 两侧相同
- **判据①显式 height 优先**：`report-page__no` 行盒 16（frame `5d860a4b` h=16，17:45 轮已核定并加口径锁）

证据：`evidence/cmp-序号6-设计PNGvs实现截图-行盒判读-修后.txt` · `evidence/cmp-序号6-维度行距对账.txt` ·
`evidence/cmp-序号6-明细卡纵向对账-修后.txt` · 复核后审计 `待判读 class 0 · 已核定 23`（`evidence/textleaf-audit-20260916-1935-6.txt`）。

## 6. 绿基线（同一份最终版探针 · 两轮）

```
phase1/phase2: checkCount=243 checkFailCount=0 docH=5341 · 溢出 0 · 文案缺失 0
```
两轮 JSON 逐字节相同、`cmp-measure-runs` 25/25 全等（`evidence/review-序号6-tl-run{1,2}.json` ·
`evidence/green-序号6-tl-checks-设计期望值.txt`）。

交互相 `?scenario=actions` 两轮 requests **逐字节相同**（各 4 行 200）：
`GET /reports/DR-1` → 点「导出 PDF」`GET /reports/DR-1/export 200` + toast「导出链接已生成，请在浏览器中打开」+ hash 不变
→ 点「填写报价」→ `#/pages/quote-models/index`（用户拍板口径）。

## 7. 质量门

- `npm test` **1185/1185 · 72 files 连跑两轮**（19:30:41 / 19:31:09；+3 新用例）
- `npm run type-check` exit 0 · `build:mp-weixin` DONE（`pages/report/index.{js,json,wxml,wxss}`；wxml 含 `group__sep`，
  js 含 `item__pill--value` / `statusIsValue`，wxss 含 `font-size:11px` / `font-weight:600` / `line-height:16px`）
- `build:h5` DONE · `review-artifacts.py` **22/22** · `check-mock-fixtures.py --mock api` FAIL 0
- 430 宽整页截图：`logs/screenshots/20260916-1935-序06-检测报告-文本叶子维度收口-h5-430宽.png`（430×5400，同件入 `.agents/state/evidence/`）

## 8. 探针自身 2 处口径 bug（未记到页面账上）

- `chkR` 的第 3 参数由 **key 末段**决定字段名：`tl.summary.boxH` 的末段不是 `h/height/w/top/right/bottom/xN`
  → 返回**整个 rect 对象**与数字比较，永久失败 ⇒ 键名改为 `tl.summary.outer.h`（同 §5.6 记录）。
- `cardTops` 是 sink 里的**对象属性**而不是变量 ⇒ 在 checks 区直接引用抛 `cardTops is not defined`（本页第一次跑得到
  `phases=['error']`）。正解：`rects('.card').map(r => r.top)` 就地算。
