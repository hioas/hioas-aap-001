# 序号 10.1「【档案与凭证】供应商档案」载体页「设计期望值 checks」轮 · 报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1255`（队列 8 第 10 页）
- 页面：`page-10-1-2`「10.1. 报价端·小程序 ｜ 【档案与凭证】供应商档案 2」→ 路由 **`/pages/profile/index`**（台账「目标路由」列）
- 帧引用：**帧名 + layer_id** = 「10.1. 报价端·小程序 ｜ 【档案与凭证】供应商档案 2」`54ad46b0-1f7c-498a-ac1a-70dff723b35d`
- 载体页：`.agents/state/h5-measure/__measure-profile.html`（由 314 行旧体例重写为 430 宽 iframe · **271 条 checks**）
- mock：`.agents/state/h5-measure/api-10-1-2`
- 设计真源：文件 `2095515676955668480` / 画布 `2095515676976640000`（画布 1）**当前状态**

## 1. 设计帧重抓（复核前必做）

- `calicat_source.py page --url https://www.calicat.cn/design/2095515676955668480 --layer-id 54ad46b0-1f7c-498a-ac1a-70dff723b35d --page-id page-10-1-2 --out .calicat`
- 与实现所依据的一份**逐字节比对**：
  - `design.json` sha256 `e7983634a07f6ff3194f359e238b782717afd12aa791641f3b23b443a5bfce66`
  - `design.tree.json` sha256 `d8048a42ea7ed6b315dc6b66a657a03705593ca4c551d9e95c39d2949ab010ed`
  - 重抓前后 **完全相同** ⇒ 画布当前状态 = 实现所依据版本，**无漂移**。

## 2. 期望值口径（want 两类来源，零目测）

1. **声明值**：`.calicat/raw/pages/page-10-1-2/design.tree.json`
   - `python .agents/state/tree-view.py page-10-1-2` → 盒子几何/内边距/圆角/stroke/effects/gap/布局
   - `python .agents/state/text-fields.py page-10-1-2` → 58 个文本叶子的 `fontSize / fontFamily→字重 / fontFill / 宽高 / 文案`
   - `python .agents/state/node-by-id.py page-10-1-2 <layerId>` → 单节点原始声明（**本轮新增**，按 id 前缀查任意图层）
2. **盒的真实几何**：设计截图 PNG 430×1414 像素实测（`.agents/state/design-shots/page-10-1-2.png`）
   - `png-rowmodal.py --x0 40 --x1 400 --runs` → 卡片/间隙边界；`text-rows.py 36 400 190 3 0 1414` → 全部文本行带
   - **本轮新增** `ink-bbox.py`（区域内墨迹包围盒）/ `ink-runs.py`（y 带内 x 方向墨迹连续段）/ `scan-row.py`（单行颜色分段）/
     `scan-col.py`（单列颜色分段）—— 用来定标「图标墨迹」「胶囊/角标的左右边界」「描边行」

实测骨架（**整页 1414** = 顶栏 96 + 卡 158/413/279/319 + 卡间距 12 + 底栏 84）：

| 区块 | 设计实测 |
|---|---|
| 顶部导航 | 0..95（96）· padding 48/16/12/16 · 返回图层 26 宽（fs=24 → 行框 36）· 完整度胶囊 319..413（**95 宽** · h24 · `#FFF7ED`）· 胶囊图标 ink 328..339 |
| 卡1 完整度进度卡 | 108..265（**158**）· 标题行 128..148（20）· 进度轨道 160..169（10，填充 36..294 = **259**）· 闸门提示 186..245（**60**）· 闸门图标 ink 50..64（盒 20×27） |
| 卡2 主体信息卡 | 278..690（**413**）· 头 298..325（27）· 锁定标签 **266..393（128 宽）** h22 · 字段标签 ink 344..354 / 值 ink 362..374 · 类型 chip 473..496 · 锁定提示 `#F8FAFC` **621..671（51）** |
| 卡3 联系信息卡 | 703..981（**279**）· 头 723..750 · 两行两栏（标签 ink 770..780 / 824..834）· 简介框 `#F8FAFC` **899..962（64）**（文本 ink 918..928 / 933..943） |
| 卡4 资质文件卡 | 995..1312（**319**）· 三行 1058/1122/1186（行高 48 · 间距 16）· 缩略图 48×48（文档 ink 19×21）· 角标 344..393（50 宽）h20 · 第三行 chevron ink 379..385 · 上传按钮 1250..1293（44 · 描边行 1250/1251 与 1292/1293） |
| 底部操作条 | 1330..1413（**84**）· 保存按钮描边列 15/16 与 208/209（193 宽）· 主按钮蓝段 221..413 · 文案 ink 1342..1389 |

**本页复核到的设计模型**（与序号 4/5/9/10 同族）：

- 文本行框：**设计声明 height 优先**（资质名 13px → h18 · 资质副行 11px → h14 · 简介 12px → h40），否则按族内实测（12→16 · 14→20 · 11→15）
- remixicon 图标占位盒 = 设计图层宽 × `fontSize × 1.5`：20×27（fs=18）· 26×36（fs=24）· 22×30（fs=20）· 15×20（fs=13）· 14×18（fs=12）
- Figma `stroke{align:center,thickness:1}` → `box-shadow: 0 0 0 1px`（`border` 占布局）

## 3. TDD 红 → 绿

| 步骤 | 命令 | 结果 |
|---|---|---|
| 红基线（探针自纠后、修复前源码） | `bash .agents/state/review-measure.sh 10.1-checks __measure-profile.html .agents/state/h5-measure/api-10-1-2 5334` | **22 / 271** 不符 · 两轮一致 · docH 1414 |
| 修复 | `aap-client/src/pages/profile/index.vue`（纯样式） | 见 §4 |
| 绿基线（修复后） | `bash .agents/state/review-measure.sh 10.1-checks __measure-profile.html .agents/state/h5-measure/api-10-1-2 5335` | **0 / 271** · 两轮独立测量 **43/43 字段全等** |

红基线 22 条（`evidence/red-序号10.1-checks-设计期望值偏差.txt`）：图标占位盒 18 条（pill.icon / c2·c3·c4 headIcon / lockIcon / docIcon / uploadIcon / chevron）·
Figma center 描边用 `border` 而声明值不是 ring 2 条（save.stroke / upload.stroke）· 胶囊被图标盒宽带偏 2 条（pill.x / pill.w）。

## 4. 修掉的 3 类偏差（全部先红后绿，纯样式，无行为改动）

1. **8 处图标占位盒按设计图层尺寸**，形状移入 `::before`（与序号 10 同族做法）：
   `.glyph--completeness` 13×13 → **15×20** · `.glyph--basic/contact/files` 18×18 → **20×27** · `.glyph--lock` 12×12 → **14×18** ·
   `.glyph--doc` 24×24 → **26×36** · `.glyph--plus` 18×18 → **22×30** · `.glyph--chevron` 7×7 → **22×30**（旋转形状入 `::before`）。
   连带修正：卡2 标题左界 60 → **62**（= 36 + 20 + gap 6）、资质缩略图内文档图标居中盒、胶囊宽 91 → **95** 且 x 323 → **321**（= 414 − 95）。
2. **两处 Figma center 描边由 `border` 改为 ring**：`.btn-upload`（#93C5FD）· `.btn--ghost`（#CBD5E1）→ `box-shadow: 0 0 0 1px`。
   border 会把按钮内容宽压成 191（设计声明 193 不占布局）。
3. **探针自身 4 处口径错误**（不是页面缺陷）：`A@@N B` 型选择器被 list 助手当成「全部 A 的文本」（新增 `resolveAll()`）·
   `padLeft` 误用 rect 检查（改用 `chkC`）· 资质角标 top 目测值错（PNG 实测 1072/1136）· `.qual-row__info` 的盒 x 是 padding 外层（84 而非 96）。

## 5. 交互回放（两轮逐字节相同 · `green-序号10.1-checks-交互回放.txt`）

| 场景 | 实测 |
|---|---|
| phase2 点「保存」 | serve 实收 **PUT /api/v1/provider/profile**（body 含 company_name/unified_social_credit_code/industry_category/province/city/address/website）→ toast「保存成功」· 完整度 72% → **78%**（pill/percent/bar `width:78%` 三处一致）· hash 不变 |
| phase3 四个入口 | 「编辑」「管理」「上传新资质」「去补全资质」→ 均跳 `#/pages/profile-edit/index`（画布唯一的档案编辑页 page-10-2） |
| phase4 返回 | `navigateBack` 触发、hash 不变（直进无栈） |
| 请求面 | 每轮 serve 实收 24 行 = **1 条写请求（PUT）** + 11 对只读 GET（profile + qualifications），**零意料外写** |

## 6. 像素对账（实现截图 vs 设计 PNG，同一把尺子）

`evidence/cmp-序号10.1-设计PNGvs实现截图-文本带.txt`（x[36,400) 阈值<190 最少 3 像素；按最近 y0 一对一匹配，**不按 index**）：
**命中 31 / 未命中 1（97%）**，两图均为 430×1414。唯一未命中 = 官网值行被设计切成 h11 + h1(602) 两条带、实现并成一条（口径差非布局差）；
实现侧多出的 1252/1254 h1 = 上传按钮 1px ring 的抗锯齿行（Figma center 描边半像素在盒内 → 整体 −1px，两轮同值）。

## 7. 残差登记（已在台账备注，未擅自改设计）

- 卡2 高 414 vs 设计 413（1px）：设计 PNG 卡2 底padding 19 行、其余 20 → 与「padding:20 auto-layout」不自洽；实现按 20 落地，整页仍为 1414（设计帧高）。
- 简介两行 ink 行距：设计 15（918..928 / 933..943）vs 实现 20（916..926 / 936..946）——设计自身声明 `height=40`（2×20）与墨迹行距不自洽；实现按声明盒高落地（盒 899..962 = 64 与设计逐值相同）。
- 占位图形墨迹：head 图标实现 18×18 vs 设计 remixicon ink 17×16；文档 20×22 vs ink 19×21（决策 D5：暂不引入图标字体）。

## 8. 质量门

- `npm test` **1173/1173 · 72 files 连跑两轮**（`green-序号10.1-checks-全量轮{1,2}.txt`）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE → `dist/build/mp-weixin/pages/profile/{index.js,index.json,index.wxml,index.wxss}` 齐备
- `npm run build:h5` DONE
- 430 宽截图 `logs/screenshots/20260916-1309-序号10.1-供应商档案-checks轮-h5-430宽.png`（430×1414 = 设计尺寸，另存 `evidence/` 同 commit）
- 设计帧重抓 sha256 逐字节相同（无漂移）
