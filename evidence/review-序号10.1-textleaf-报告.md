# 序号 10.1（page-10-1-2 · 供应商档案 / `/pages/profile/index`）· 文本叶子维度收口报告

- 轮次：cron `aap-tdd-run-20260916-2015`（2026-09-16 20:15 起）
- 设计真源：Calicat 文件 `2095514676955668480`（画布 `2095515676976640000`）帧「供应商档案 2」= `page-10-1-2`
  · `layer_id 54ad46b0-1f7c-498a-ac1a-70dff723b35d`
- 重抓核对（人工指令 C）：`python .agents/state/recapture-10.1.py` →
  `design.json` sha256 新 `e7983634a07f…` = 旧 `e7983634a07f…` **逐字节相同（无漂移）**
  （`screenshot.json` 仅签名 URL 变化；设计 PNG 本地 `e44f8963…` 430×1414）

## 1. 红 → 绿（两段，同一份最终版探针两轮）

| 段 | 命令 | 红基线 | 绿 | docH |
|---|---|---|---|---|
| ① 简介块行盒 | `bash .agents/state/review-measure.sh 10.1-tlred __measure-profile.html .agents/state/h5-measure/api-10-1-2 5351` | **2/275**（`c3.introText.lh` got 20 want 14.4px · `c3.introText.align` got normal want center） | `10.1-tlg` **0/275** | 1414 |
| ② 闸门块行盒 | 同上 `10.1-tlred2`（端口 5353） | **2/277**（`c1.gateText.lh` got 18 want 14.4px · `c1.gateText.align`） | `10.1-tlg2` **0/277** | 1414 |

- 两轮独立测量 **43/43 字段全等**（`cmp-measure-runs.py … tlg2-run1 tlg2-run2 phase1`）；
  requests 两轮**集合**逐字节相同（24 行 = 1 写 + 11 对只读 GET；仅两条并发 GET 的行序互换）。
- 证据：`.agents/state/evidence/review-序号10.1-{tlred,tlred2,tlg,tlg2}-run{1,2}.json` ·
  `evidence/requests-序号10.1-{tlred2,tlg2}-run{1,2}.txt` · `evidence/red-序号10.1-textleaf-简介行盒.txt`。

## 2. 两处真偏差（设计 PNG 实测驱动，非样式猜测）

### ① `.intro-box__text`（design `234362e0`）

- 声明：`fs12 · lineHeight 1.2 · textAlignVertical=middle · width=fill_container · **height=40**`
  → 40 是**块高（两行）**，不是行盒。
- 判据②：设计 PNG 墨迹 **917..929 / 932..943（行距 15）**；修前实现 915..927 / 936..946（行距 21）。
- 修复：`line-height: 20px → **14.4px**` + `height: 40px` + `display:flex; align-items:center`
- 结果：实现墨迹 **918..930 / 933..943（±1）**；简介盒 899..962 = 64 两侧不变；docH 1414 不变。

### ② `.gate__text`（design `d183dcc0` + 容器 `87815f1d`）

- 声明：文本 `fs12 lh1.2`；容器 `padding 12`、`height fit_content`。
- 判据②盒算术：`#FFFBEB` 填充盒在 **x=215**（盒中心列，避开 r=12 圆角）实测 ——
  **设计 186..245 = 实现 186..245，两侧同为 60 = 12 + 36 + 12 ⇒ 块高 36**。
  圆角校正：同一盒在 x=40 列量得 54 = 60 − 2×(12 − √(12²−8²))，两列互证。
- 「图标行框 27 不承重」的反证：闸门图标墨迹**中心两侧同为 211.5**（设计 204..219 / 实现 203..220）
  ⇒ 设计的图标盒也是 27（若是 36，中心会落在 216）⇒ 36 由**文本块**贡献。
- 修复：`line-height: 18px → **14.4px**` + `height: 36px` + `display:flex; align-items:center`
- 结果：实现墨迹 **203..214 / 218..228（±1）**，修前 220..230（第 2 行低 3px）；盒高与整页几何不变。

## 3. 8 类「非偏差」登记（`textleaf-accept.json` +9 键，累计 73）

`btn-upload__text`（按钮 h44）· `completeness__text`（胶囊 h24）· `lock-badge__text`（h22）·
`qual-row__badge-text`（角标 h20，覆盖 2 个变体）· `type-chip__text`（h24）—— 均在**定高居中盒**内（不承重），墨迹 ±1 或逐值相同；
`note__text`—— 单行，设计与实现墨迹 **636..648 两侧逐值相同**（两模型对 n=1 同解，差 <1px）；
`head-line__percent`—— 标题行 fit_content，卡1 高 158 = 设计 158，墨迹 +1；
`intro-box__text` —— 已修复，audit 的 want=40 属「显式 height 当行盒」的模型口径差。

审计复跑：**待判读 class 0 · 已核定 8**（`evidence/green-序号10.1-textleaf-待判读0.txt`），
红基线 `evidence/red-序号10.1-textleaf-待判读.txt`（9 条）。

## 4. 逐类墨迹带对账（设计与实现同窗口）

`evidence/cmp-序号10.1-文本叶子-逐类带.txt`（`tl-bands.py --pad 16`）：

```
btn-upload__text   design 1266..1278      = impl 1266..1278        SAME
note__text         design 636..648        = impl 636..648          SAME
intro-box__text    design 917..929/932..943  impl 918..930/933..943  ±1
gate__text         design 202..214/217..228  impl 203..214/218..228  ±1
completeness__text design 60..70          impl 61..71              +1
lock-badge__text   design 306..316        impl 307..317            +1
qual-row__badge-text design 1076..1086/1140..1150  impl 1077..1087/1141..1151  +1
type-chip__text    design 479..489        impl 480..490            +1
head-line__percent design 132..143        impl 133..144            +1
```

## 5. 质量门

- `npm test` **1185/1185 · 72 files 连跑两轮**（20:24:18 / 20:25:01）
- `npm run type-check` **exit 0**
- `npm run build:mp-weixin` DONE —— `dist/build/mp-weixin/pages/profile/index.{js,json,wxml,wxss}`；
  wxss 含 `line-height:14.4px` ×2 · `height:36px` · `height:40px` · `align-items:center`
- `npm run build:h5` DONE；`review-artifacts.py` → 台账全部路由的 mp-weixin 三件套齐备（22/22）
- 台账体检 `validate-ledger-csv.py` 22 行 × 11 字段 `bad 0`
- 截图：`logs/screenshots/20260916-2035-序10.1-文本叶子维度收口-h5-430宽.png`（430×1414 = 设计帧尺寸）

## 6. 未做 / 留给人类

- mp-weixin 只做**编译证明**（本机无微信开发者工具），真机/预览验收仍留给人类。
- 本页原列 11 条待拍板缺口沿用，本轮不新增、不擅自改设计稿口径。
