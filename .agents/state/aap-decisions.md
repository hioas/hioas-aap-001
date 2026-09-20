# AAP 决策台账（用户拍板 → 循环执行）

> **每轮开工先读本文件**；`待执行` 的条目**优先于**状态文件 §4 里的其他在办项。
> 执行完把该条改成 `已完成 <YYYY-MM-DD HH:MM>` 并写明证据（用例名 / 提交）。

## D1 · 补接口字段级 schema —— `已完成 2026-09-16 09:0x`（本轮由前台会话执行）

- 产物：仓库 `docs/api/接口字段级schema.md`（覆盖 `GET /usage/summary`、`GET /usage/hourly`、`GET /provider/profile`，
  每字段带类型/单位/来源依据；错误码；前端落地约定）。
- 同步回设计侧：Calicat 文件 `2095515676955668480` 已建卡《18-补充·接口字段级schema》（`get_prd_list` 回读：23 张卡，含本卡）。
  Calicat 建卡接口对 6k+ 字 body 会 524 → 卡片放摘要，完整版在仓库。
- **统一约定（对所有后续页面生效）**：JSON 字段一律 **snake_case**，与 `15-数据模型ER与数据字典.md` 1:1 同名。
- 循环要做的：把台账中记 `missing-prd` 的接口备注改为「依据 `docs/api/接口字段级schema.md` §x」，
  并检查已实现页面的字段名是否与该 schema 一致（不一致以 schema 为准改代码，别改 schema）。

## D2 · 删除「钱包」入口 —— `已完成 2026-09-16 09:15`（cron 轮 aap-tdd-run-20260916-0835）

- 位置：`aap-client/src/pages/workbench/index.vue` 快捷入口列表里的 `{ label: '钱包', iconBg: '#eff6ff', iconColor: '#2563eb', url: '' }`
  （设计画布无对应页面，之前做成 client-only toast）。
- 要求：**整项删除**（不是改成 toast、不是隐藏），同时删掉测试里针对「钱包」的断言；
  视图模型/常量里若有 wallet 相关项一并清掉。
- 验收：`src/` 内 `grep -i 钱包` 为 0 命中（台账/状态文件/本文件里的文字除外）；
  工作台页面 DOM 实测 `overflowingCount 0`；`npm test` 连跑两轮全绿。

**执行证据（cron 轮 aap-tdd-run-20260916-0835）**

- 代码：`src/pages/workbench/index.vue` 的 `quickEntries` 删掉 `{ label: '钱包', iconBg: '#eff6ff', iconColor: '#2563eb', url: '' }`（只剩 评测/报价/合同/明细），
  并删掉 `onQuick` 里专为它写的 `if (!q.url) { showToast('钱包功能开发中') }` 分支 —— 已无空 `url` 项，分支成了死代码。
  工作台目录内 `grep -n 钱包 src/pages/workbench/index.vue` 只剩 **1 行注释**（写明「按决策 D2 整项删除」，属设计↔决策偏差留痕，见状态文件 §2 第 6 条）。
- 单测（先红后绿）：`tests/pages/workbench.spec.ts` 结构用例「快捷入口 5 个」→「4 个」；「快捷入口跳转」用例改为先断言
  `[data-testid^="quick-"]` 恰为 4 项且 `wrapper.text()` 不含「钱包」；新增「『钱包』入口被删干净（节点不存在 / 文案无钱包 / 无 toast）」。
  红基线：3 failed（2 个新断言 + 结构用例）→ 绿 **16/16**。
- 测量面（430 宽 DOM 实测，两轮独立测量全等）：`__measure-workbench.html` 的 phase2 由「钱包 client-only toast」换成
  「评测 → `/pages/credentials/index`」，并把「钱包」从设计文案清单移入 `removedByDecision`（D2 留痕）。
  复跑结果：`checkFailCount 0/92` · `quickIds=["quick-评测","quick-报价","quick-合同","quick-明细"]` · `walletEntryAbsent=true` ·
  `pageTextHasWallet=false` · `overflowingCount=0` · `navigatedToCredentials=true`；证据 `evidence/review-序号2-{run,actions-run}{1,2}.json`。
- 全量：`npm test` **1145/1145 连跑两轮** · `npm run type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE。
- ⚠️ **验收口径需修正（请拍板）**：D2 原文写的「`src/` 内 `grep -i 钱包` 为 0 命中」按字面**做不到**——
  `src/pages/mine/index.vue`（序号 21「我的页」）、`src/utils/mine-model.ts`、`src/api/payment.ts` 里的「我的钱包」卡
  是**设计稿 page-21-2 的图层**（设计上就有「我的钱包 / 可提现余额 / 提现 / 待结算 / 累计结算」），删掉它才是违背「设计稿优先」。
  建议把该验收改成 **「`src/pages/workbench/**` 内 0 命中」**（当前已满足，仅 1 行偏差留痕注释）；本轮未擅自扩大删除范围。

## D3 · 图例百分比「统一且最优」—— `已完成 2026-09-16 09:26`（cron 轮 `aap-tdd-run-20260916-0910`）

背景：page-2-b 设计稿图例「音频 6% + 视频 6%」等数字与总量口径矛盾（合计 106%）。用户要求**改统一且最优方式**。

**唯一口径（不许每页各写一套）**：
1. 百分比**一律由真实数值计算**，禁止硬编码设计稿里的百分比文字；设计稿百分比只作视觉参考。
2. 分母统一：`denominator = max(total_tokens, Σ(六类分类值))`；每段 `pct = value / denominator`，
   显示时按**最大余数法**取整，保证「环形图分段之和 == 图例整数百分比之和」，且**总和 ≤ 100%**。
3. 环形图与图例必须**同一个分母、同一份计算结果**（视觉与数字永远一致）。
4. 字段缺失 → 占位符（`—`），不显示 0%。

**验收**：单测断言（a）图例与环形图分母同源；（b）六个分类整数百分比之和 ≤ 100（容差 0）；
（c）无数据时全部占位；（d）`音频/视频` 不再出现 6%/6% 的硬编码值。`npm test` 连跑两轮全绿。

**执行证据（cron 轮 `aap-tdd-run-20260916-0910`）**

- 口径落点：新增 `src/utils/percentage.ts`（`resolvePercentDenominator` = max(total, Σ分类值) / `largestRemainderPercentages` 最大余数法 /
  `percentTotalOf`），**全站唯一实现**；`src/utils/workbench-model.ts` 出 `ring{hasData,denominator,segments,percentSum,remainderPercent}`
  与 `categories[i].percent`（同一份整数）；`src/pages/workbench/index.vue` 的 `donutBackground` 只读 `model.ring` 拼 conic-gradient（不再自算比例）。
- 实测数字（同一 mock，真源 `GET /api/v1/usage/summary`：总 3.86B、六类合计 4.09B）：
  分母 **4.09B** → 图例 `42% · 1.74B / 28% · 1.16B / 14% · 0.58B / 4% · 0.15B / 6% · 0.23B / 6% · 0.23B`（合计 **100**；修前照抄设计稿 = 45/30/15/4/6/6 = 106%），
  环形图 conic-gradient 分段宽 **42/28/14/4/6/6**、余量 0、合计 100（与图例逐项相等，色值与设计图例点色一一对应）。
- 验收对应：**(a)** `workbench-percent.spec.ts`「分段与图例逐项同 key/同色/同整数百分比」+ 载体页 `d3.ring.stopWidths == 图例整数`；
  **(b)** `percentage.spec.ts` 7 组输入逐条 `≤ 100`（容差 0）+ 载体页 `d3.ring.totalPct = 100`；
  **(c)** 空 summary → 六行 `—`、`ring.hasData=false`（页面退轨道色 rgb(241,245,249)）+ 缺字段场景（去 audio/video）实测 4 段 + 两行 `—`；
  **(d)** 音频/视频随数值变化（100M/50M → 10%/5%）且有断言禁止出现 `45% · ` 设计字面量。
- TDD：红基线 `evidence/red-D3-01-percentage-helper.txt`（import 解析失败）· `red-D3-02-model.txt`（8 failed，含 `'45% · 1.74B' ≠ '42% · 1.74B'`）
  · `red-D3-03-page.txt`（conic 分段 42.54% ≠ 图例整数 42）；绿 `evidence/green-D3-01/02/03*.txt`；
  全量 `npm test` **1168/1168 · 72 files 连跑两轮**、`type-check` exit 0、`build:mp-weixin`/`build:h5` DONE。
- 430 宽 DOM 实测：`evidence/review-序号2-d3-run{1,2}.json`（api mock，`checkCount 103 · checkFailCount 0`，两次独立测量全等）
  与 `evidence/review-序号2-d3nomedia-run{1,2}.json`（缺字段场景，全等）；变体可用 `python .agents/state/make-nomedia-mock.py` 复现。
- 截图：`logs/screenshots/20260916-0921-序号2-工作台-图例统一口径D3-h5-430宽.png`。
- 顺带（同一口径的连带影响，已按 D3 改）：`tests/unit/usage-api.spec.ts` 与 `tests/pages/workbench.spec.ts` 里照抄设计稿 45/30/15 的断言改为算出的 42/28/14（断言强度不变、并加「不得出现 45%」）。
- 备注（未擅自扩大范围）：序号 22「用量概览」的模型分布占比用的是**服务端下发的 `share/percent/ratio` 字段**（`usage-model.ts` `sharePercent`），不是从 token 值算的 —— 与 D3 的六类图例不是同一场景；若要它也改成同口径，需你确认（本轮不动）。

## D4 · 主色：蓝 —— `已完成 2026-09-16`（用户拍板）

- **生效结论**：主色以**设计稿**为准 —— 品牌 `#1d4ed8`、主按钮/链接 `#2563eb`、浅蓝底 `#eff6ff` / `#eef2ff`；
  `08-前端原型说明.md` 里的「深青 oklch(0.52 0.085 197)」**作废**（该卡为早期原型描述，与画布不一致）。
- 循环要做的：`src/styles/tokens.scss` 顶部注释里删掉「与 PRD 冲突待确认」字样，改成「主色=设计稿蓝（用户 2026-09-16 确认）」；
  `docs/aap-client-page-plan.md` §4 冲突表该行结论改为「已确认：按设计稿蓝」。
- ✅ **已落地 2026-09-16 09:26（cron 轮 `aap-tdd-run-20260916-0910`）**：`src/styles/tokens.scss` 顶部注释改为
  「主色 = 设计稿蓝（用户 2026-09-16 确认，决策 D4）… 08-PRD 的深青 oklch 已作废」；`docs/aap-client-page-plan.md` §4 表格该行结论改为
  「**已确认：按设计稿蓝**」，并补记 D3/D5 两行冲突结论（图例百分比口径 / 图标维持 CSS 占位）。churn 仅注释与文档，无行为改动。

## D5 · 图标：维持 CSS 占位 —— `已完成 2026-09-16`（用户答复「可以」）

- **结论**：不引入图标字体库；继续用 CSS 绘制的中性色块占位（PRD 08 禁令 emoji 依旧有效）。
- 理由：微信小程序对本地字体文件支持差（需 base64 内嵌，包体+维护成本高），
  而当前占位已通过视觉验收；将来拿到正式图标资产（iconfont base64 / SVG data-uri）再整批替换。
- 循环要做的：新页面图标一律沿用 `tokens.scss` 的 `field__mark` 同族做法；
  不要再就"图标方案"重复提问。
- ✅ **已落库 2026-09-16 09:26**：`src/styles/tokens.scss` 顶部注释写明「图标：维持 CSS 绘制的中性色块占位（决策 D5，不引入图标字体库，PRD08 禁 emoji）」，
  `docs/aap-client-page-plan.md` §4 增一行「图标 | 设计为 remixicon 矢量 | 08-PRD 禁 emoji | 已确认：维持 CSS 绘制占位」。

## D6 · 目录重命名 `aap-client → hioas-aap-client` —— `挂起，勿再重试`（前台会话决定）

- 现状：状态文件 §4 里把它当成在办项，每轮因文件句柄占用重试失败。
- 决定：**不重命名**。仓库内模块目录沿用 `aap-*`（与 `aap-server`、`aap-admn` 对齐），
  `hioas-*` 是**仓库名**约定（hioas-aim / hioas-portal），不是模块目录约定。
- 循环要做的：从在办队列移除该项；用户若确实想改名再单独要求。

## D7 · 合同电子签入口：**保留** —— `用户拍板 2026-09-16`（原话「保留a 电子签入口」）

**生效结论**：序号 15 `/pages/contract/index` 的**电子签入口保留**，按设计帧实现 —— 电子签章文案
（「本合同采用电子签章，签署后即时生效并具备法律效力。」）+「签署方式：短信验证码签署」+ 底部「去签署」
（二次确认 → `POST /api/v1/contracts/{id}/sign` → toast「签署申请已提交」）。**不改为只读合同详情、不下架该入口。**

- 口径：一期**设计稿优先**（与序号 1/11 一致）；10-PRD §4.2 / 17-spec R-41 / 数据字典
  `Contract(sign_channel)` 的「合同线下签署、线上电子签一期不做」按**偏差留痕**处理（台账备注保留原文），不改实现；
  线下签署作为并行渠道存在，`sign_channel` 枚举 `ONLINE/OFFLINE` 保留、默认值不动，签署流程由服务端按 `sign_channel` 决定。
- 理由：设计帧是视觉真源（画布里逐字写着电子签章 + 短信验证码签署）；保留入口只调服务端接口，不产生客户端数据副作用。

**循环要做的（不必再就此事提问）**

1. 任何页面（后续合同列表 / 详情 / 通知模板）出现「去签署 / 签署」入口一律**保留**，不得改成只读或下架。
2. 把三处「等人类拍板 / 记台账」措辞改成「已拍板（决策 D7：保留电子签入口）」：
   `aap-client/src/utils/contract-model.ts` 顶部注释 · `aap-client/src/pages/contract/index.vue` 顶部注释与 `onSign` 注释 ·
   `aap-client/tests/pages/contract-flow.spec.ts` 文件头注释。
3. `docs/aap-client-page-plan.md` §4 冲突表补一行：设计帧电子签章/短信验证码签署 vs 10-PRD §4.2 / R-41 线下签署 → 「已确认：保留电子签入口（决策 D7）」。
4. 台账 `aap-feature-status.csv` 序号 15 行备注里「电子签 vs 线下（待人类拍板）」一条改为「**已确认（D7）：保留电子签入口**」，其余 `missing-prd` 不动。
5. 回归锁定：「去签署」4 例（入口存在 / 二次确认文案 / `POST /contracts/c1/sign` / 签署被拒 E-1601 状态保持）保持全绿；
   载体页 `__measure-contract.html` 的 `?scenario=sign` 出口继续纳入每轮复跑（请求逐字节比对）。

**循环侧执行证据（cron 轮 `aap-tdd-run-20260916-1525`，2026-09-16 15:4x）**

- ①**收纳用户在做中的 4 处改动**（用户 15:41 自行改的注释/文档口径）为独立提交 `9637730`
  （`docs(aap-client): 采纳用户在做中的决策 D7…`）：`contract/index.vue` 顶部与 `onSign` 注释 · `utils/contract-model.ts` 顶部冲突段 · `tests/pages/contract-flow.spec.ts` 文件头 ·
  `docs/aap-client-page-plan.md` §4 冲突表新行 —— 均为注释/文档，无行为改动（diff 已逐行核对）。
- ②**第 3 条（page-plan §4 补行）已由用户本人在同批改动里完成**（表格最后一行「已确认：保留电子签入口（决策 D7）」），循环侧无需重复。
- ③**第 4 条已完成**：台账 `aap-feature-status.csv` 序号 15 行备注①由「是否下架『去签署·电子签』入口待拍板」改为
  **「已确认（D7）：保留电子签入口」（用户 2026-09-16「保留a 电子签入口」；PRD 口径作偏差留痕）**，其余 `missing-prd` 条目一字未动。
- ④**第 5 条已完成（回归锁定，两轮独立测量）**：`bash .agents/state/review-measure.sh 15-d7regress __measure-contract.html .agents/state/h5-measure/api-15 5330 "?scenario=sign"`
  → 载体页 239 条 checks **0 失败**、`docH 1231` = 设计帧高；`?scenario=sign` 出口两轮：uni-modal 文案「确认签署 / 确认对当前合同发起签署？」→
  **真实 `POST /api/v1/contracts/c1/sign`（body 空）** → toast「签署申请已提交」→ 重载后状态胶囊「待签署」；
  两轮 serve 实收请求行 **逐字节相同**（`evidence/requests-序号15-d7regress-run{1,2}.txt`：GET c1 → POST sign → GET c1）。
  证据 JSON：`evidence/review-序号15-d7regress-run{1,2}.json`。
- ⑤**「去签署」4 例回归**：`npm test` **1181/1181 · 72 files 连跑两轮**（15:42 轮1 / 轮2）+ `type-check` exit 0 —— 含
  `tests/pages/contract-flow.spec.ts` 的 4 例（入口存在 / 二次确认 / POST sign / 被拒 E-1601 保持状态）全绿。

## 2026-09-19 · H5 有头浏览器链路联调发现（缺陷 7）

**缺陷 7（H5 专有）· `profile-edit` 的「所在地区」选择器在 H5 上不可用**

- 现象：H5 打开 `/pages/profile-edit/index` 时控制台稳定报
  `[Vue warn]: Invalid prop: custom validator check failed for prop "mode"` at `<Picker>`（4 条/次）。
- 根因（读 uni-app 源码实证，非推断）：`@dcloudio/uni-h5` 的 Picker 只允许
  `selector | multiSelector | time | date`，**`region` 被显式注释掉**：
  ```js
  const mode = { SELECTOR:"selector", MULTISELECTOR:"multiSelector", TIME:"time", DATE:"date"
    // 暂不支持城市选择
    // REGION: 'region'          ← 注释掉
  };
  mode: { validator(val) { return Object.values(mode).includes(val) } }
  ```
  本页用的是 `mode="region"` → validator 失败 → **H5 上不渲染地区选择器**。
- **这修正了台账序号 10 备注⑫的原判断**：原文写「无头环境无法驱动原生控件 → 该交互仅单测覆盖」，
  实际不是「驱动不了」，而是 **H5 端该控件不存在**。微信小程序端支持 region，**故这是一个真实双端差异**。
- 影响面：H5 用户无法选择所在地区（`province`/`city` 无法填写）→ 档案完整度相关链路受影响。
- 证据：`aap-client/evidence/h5-smoke/h5-smoke-result.json`（`rows[].consoleErrors`）·
  `.agents/state/evidence/h5-both-runs.txt` · 截图 `evidence/h5-smoke/*pages_profile-edit_index.png`。
- 处置建议（未擅自改，等拍板）：①H5 降级为 `mode="selector"` 自绘省市级联；
  ②或 H5 用 `<input>` 文本录入 + 校验；③或明确「地区仅小程序端可编辑」并在 H5 隐藏该项。

**同时确认（非缺陷，避免重复排查）**：

- H5 全量 21 页在登录态下**渲染正常 21/21**，0 空白页、0 路由不符、**0 异常接口**（14 次真实业务 HTTP 全 `code=0`）。
- `GET /detection-jobs/{id}/results` 恒返回 `{total:0, items:[]}` 且任务恒 `QUEUED` —— 这是**缺陷 1（检测执行器缺失）**的**假绿**表现：
  HTTP 200 + `code=0`，只看状态码会判成通过。已在 `h5-chain.mjs` 第⑪步固化为**故意红**的业务结果断言。
- 联调账号别混：`13800138000`=SUPPLIER（供应商侧链路）· `13900000001`=SUPER_ADMIN（管理端）。
  混用会得到一批 `403 E-1901`，**是账号错不是权限缺陷**。

## 2026-09-19 · 项目级口径：H5 与 mp-weixin 必须共用同一套实现

**用户拍板原文**：「同一套源码构建出的 h5、mp-weixin 页面应该保持一样！」

→ **禁止**用 `#ifdef` / `#ifndef` 或运行时平台判断去分平台给不同 UI；
遇到「某平台不支持某组件属性」时，正确做法是**换一个两端都支持的写法**，
而不是为其中一端做降级分支。

**同期全量审计结果**（`grep -rn "#ifdef|#ifndef" src/` 与运行时平台判断）：

- 条件编译：**零命中**，源码结构本来就是平台中立的。
- 唯一的运行时平台分支：`src/api/base-url.ts`（接口基址）。
  小程序**必须**绝对 URL，H5 走 vite 代理避免 CORS —— **不影响页面渲染**，属必要差异，保留。
- `mode="region"` 是当时**唯一**一处把两端做岔的地方（→ 缺陷 7，见下）。

### 缺陷 7 已修复（按上述口径）

原实现 `<picker mode="region">`：uni-h5 不支持 region（`REGION` 在源码里被注释掉，
`mode` 的 validator 直接拒绝）→ H5 不渲染控件，微信支持 → 两端不一致。

改为 `<picker mode="multiSelector">` + 共享数据 `src/utils/region-data.ts`
（34 省级 + 下辖地级，**形态对齐微信 region picker：直辖市省===市**，否则历史数据回填错位）。

质量门（真实运行产物）：

| 项 | 结果 |
|---|---|
| 红基线（源码回退 `mode="region"`，新测试不动） | **6 失败 / 37 通过**，首条 `expected 'region' to be 'multiSelector'` |
| 绿 | **43/43** |
| 全量回归 | **1225/1225（76 files）** |
| type-check | exit 0 |
| build:h5 / build:mp-weixin | 均 DONE；mp-weixin 产物 `region` 残留 **0**，h5 产物 `multiSelector` 2 文件 / `mode:"region"` **0** |
| **真实浏览器 H5 全页冒烟** | **21/21 渲染正常，控制台报错 0**（修复前 profile-edit 稳定 4 条 Vue 告警） |

证据：`.agents/state/evidence/{red,green}-fe-7*.txt` · `aap-client/evidence/h5-smoke/h5-smoke-result.json`。
方案与取舍全文：`docs/backend/10-三项缺口方案与取舍.md`。

⚠️ 数据源 PRD 未定义（台账序号 10 备注⑫仍记 `missing-prd`）：当前用民政部行政区划口径的内置数据；
**如需与上游行政区划库对齐，只替换 `region-data.ts`**，页面无需改动。
台账备注⑫原写「无头环境无法驱动原生控件」**判断有误**，已更正为「H5 端该控件不存在」。


## 管理端 · 设计/PRD 冲突（待裁定）

### D-ADM-1「批量通过」按钮：设计稿有，PRD 明确禁止
- **设计源**：Calicat 文件 `2100748148891054080` / 画布 `2100748148912025600` / 页 `page-6-pc`（报价审核台）
  图层树里存在文案「批量通过」（fs=13）。
- **业务源**：`.calicat/prd/13-管理端PRD.md` §5 ——
  「批量操作：批量领取、批量驳回（同一原因）、批量导出；**不提供批量通过**
  （通过触发合同+编译链式副作用，必须逐单确认）」。
- **处置**：按 **PRD 为准**，审核台**不渲染**「批量通过」，并在页面顶部显式提示该冲突待裁定。
  未静默二选一（calicat skill 铁律 #7）。
- **待用户裁定**：a) 维持 PRD（去掉设计稿该按钮）；b) 改设计稿；c) 折中为「批量预检+逐单确认」。

## 管理端 · 设计不一致与能力缺口（待裁定）

### D-ADM-2 管理端外壳存在两套设计口径（page-3 是孤例）
实测 11 页的品牌/副标题/用户（脚本逐页提取 design.json 的 content）：

| 页 | 品牌 | 副标题 | 用户 | 导航分组 |
|---|---|---|---|---|
| page-1-pc | 云算接入 | 运营管理端 | 运营 · 王倩 / 管理员 | 概览 / 进件管理 / 下发与同步 |
| page-2 | 云算接入 | 运营管理端 | 运营 · 王倩 | 同上 |
| page-4-pc | 云算接入 | 运营管理端 | 运营 · 王倩 | 同上 |
| page-5-pc | 云算接入 | 运营管理端 | 运营 · 王倩 | 同上 |
| page-6-pc | 云算接入 | 运营管理端 | 运营 · 王倩 | 同上 |
| page-7-pc | 云算接入 | 运营管理端 | 运营 · 王倩 | 同上 |
| page-8-pc-new-api | 云算接入 | 运营管理端 | 运营 · 王倩 | 同上 |
| **page-3** | **智检云** | **AI 检测中台 · 管理端** | **陈志远 / 超级管理员** | **工作台 / 业务管理 / 系统配置** |

- **9/11 页一致**（云算接入），仅 **page-3 模型管理** 是另一套（智检云，含「网关运行状态」顶栏、
  业务管理/系统配置分组、超级管理员用户）。
- **处置**：外壳以**多数口径（云算接入）为准**（AdminLayout 已按 page-1-pc 实现），
  page-3 的**内容**（厂商分组 / 模型表 / 两个抽屉）仍按其设计实现，但**放进统一外壳**。
- **待裁定**：page-3 是否为早期版本应废弃？还是管理端要改名「智检云」、导航改「业务管理/系统配置」？

### D-ADM-3 模型管理（page-3）**后端无任何能力**
- 后端**没有** `ModelController`；全仓 model 相关路由只有 `GET /admin/sync/models/upstream`。
- 主代码**没有** `model_catalog`；**没有** `aap_vendor` / `aap_model` 表。
- 唯一只读来源 `GET /admin/sync/models/upstream` 实测返回
  `E-1501 未配置可用的 new-api 端点（aap_newapi_endpoint 无 ACTIVE 记录）` → **当前也不可用**。
- 设计稿要求的「新增厂商 / 新增模型 / 编辑 / 测试 / 启用停用 / 批量管理 / 导出清单」
  **后端一个端点都没有** → 与缺陷1（检测执行器）、缺陷2（文件上传）同类，属**整页能力缺口**。
- **处置**：页面按设计稿实现 UI 与状态，但所有写操作与数据源**显式标注「后端未提供」**，
  不伪造数据、不假装成功。**待用户拍板**：补后端能力 / 页面降级为只读占位 / 暂缓此页。

---

## 管理端 · 逐页实现进度（2026-09-19 夜）

设计源 11 页 → 管理端 9 个路由（设计稿只画了 9 个菜单项，PRD 13 §2 更多，差异记 missing-design）。

| 设计页 | 路由 | 状态 |
|---|---|---|
| page-1-pc 状态看板 | `/dashboard` | ✅ |
| page-2 用量统计 | `/usage` | ✅ |
| page-3 模型管理 | `/models` | ⚠️ UI 完整、后端无能力（D-ADM-3） |
| **page-4-pc 供应商管理（+4.1 抽屉）** | `/providers` | ✅ **本轮实现** |
| **page-5-pc 检测中心任务监控** | `/detection` | ✅ **本轮实现**（任务监控部分为显式缺口 D-ADM-5） |
| page-6-pc 报价审核台 | `/reviews` | ✅ |
| page-7-pc 合同与结算 | `/contracts` | ✅ |
| **page-8-pc-new-api 同步** | `/sync` | ✅ **本轮实现** |
| （设计稿未单独出页） | `/compilation` | 骨架（PRD 13 §7 M10；等设计补齐或按 PRD 实现） |

报告与证据：`.agents/state/evidence/adm-pages-4-5-8-REPORT.md` · `redgreen-defect8-pageSize.txt` ·
`redgreen-defect8-vitest.txt` · `aap-admin/evidence/admin/{admin-acceptance.json,page-*.png}`。

## 缺陷 8 · 管理端分页参数名不匹配（`page_size`）→ 后端静默降级默认 20 条/页 —— `已修复 2026-09-19`

- **现象**：`aap-admin` 各 api 模块发 `page_size`，后端 `@RequestParam(required = false) Integer pageSize` 绑不上 →
  **静默**用默认 20。请求 100 / 200 / 500 条也只回 20 条，**没有任何报错**。
- **影响**：仪表盘 KPI（请求 100 条）、用量页（请求 500 条）等**统计口径被截断**；接口 code=0、页面照常渲染，
  数字却是错的 —— 典型「假绿」（与缺陷1「HTTP 200 + code=0 但业务是假的」同一类）。
- **实证**（`redgreen-defect8-pageSize.txt`）：`/admin/audit-logs?page=1&page_size=2` → 服务端 `pageSize=20`、`items=20`；
  同请求用 `pageSize=2` → `items=2`。`total` 一直是 157，所以只看 total 也发现不了。
- **修复**：`providers.ts` / `reviews.ts` / `contracts.ts`(×3) / `usage.ts` / `dashboard/model.ts`(×5) 全改 `pageSize`；
  `PageResult` 补响应侧真实字段 `pageSize?`；`reviews` 页对 `/quotes/{id}/items`（该端点**无分页参数**）去掉无效分页参数。
- **回归判据（先红后绿）**：`tests/unit/providers.spec.ts`「分页参数名是 pageSize（不是 page_size）」，
  用 `tools/redgreen-defect8.sh` 实测 RED exit=1（`expected '…page_s…' to contain 'pageSize=50'`）→ GREEN exit=0；
  证据 `redgreen-defect8-vitest.txt`（真实 vitest 输出，LF、CR=0）。
- **验收侧连带**：`index.html` 补内联空 favicon（否则浏览器默认请求 `/favicon.ico` 得 404，
  控制台留一条 `Failed to load resource: 404`，污染「控制台 0 报错」判据）。

## 缺陷 11 · 证据文件把**真实令牌**写进 git（本轮自查发现）—— `已修复 2026-09-19`

- **现象**：两个验收脚本都把后端响应体**原样**写进证据 JSON，其中 `/auth/sms/login` 的响应含
  **真实 access token（303/307 字符 JWT）与 refresh token（43 字符）**：
  - `aap-client/evidence/h5-chain/h5-chain-result.json` —— **已经进了 git**（历史里仍有）；
  - `aap-admin/evidence/admin/admin-acceptance.json`（本轮新产出，尚未入库）。
- **为什么自检没拦住**：项目硬规则要求「提交前敏感值自检」，但**工具输出层会把 JWT 打码显示**
  （`eyJhbG...xxxx`）—— 看日志/看 diff 都会以为「已经脱敏了」。这是**判据不能靠人眼**的又一例
  （同族：坑「一个从没见过它失败的判据不是判据」）。
- **修复**：
  1. 两个脚本**在写文件这一步**做机器脱敏（`redact`/`redactSecrets`）：白名单键名（token/refresh_token/
     api_key/secret/password/authorization/credential…）且值 ≥16 字符、或任何**真 JWT 形状**的字符串
     → `<redacted len=N>`（**保留长度**，证据价值不丢）。
  2. 新增共享守卫 `tools/evidence-secrets.py`：扫描（命中即 exit 1，可作门禁）/ `--redact` 就地脱敏。
     两个脚本的注释都指向它做独立复核。
  3. 已入库的 `h5-chain-result.json` 就地脱敏（**纯文本替换，3 行改动**，其余字节不动）。
- **验证**：`python tools/evidence-secrets.py` 全仓复扫 **0 命中**；重跑一次有头验收后新写的 JSON
  复扫仍 0 命中（证明是**写时**脱敏，不是事后擦）；脱敏后 JSON 仍合法、行数与证据内容不变
  （`git diff` 仅 3 行：token/refresh_token/refreshToken）。
- **踩坑（已回退）**：第一版实现用 `json.load` + `json.dumps` 重写整个文件 → 把他方会话的 6 个证据文件
  **整份重新格式化**（行尾/缩进全变，1124 行 diff），会打乱他们「产物零写副作用（size+md5）」的回归守卫；
  第一版键名还用**子串**匹配 `token` → 误伤 `tokenPage` 这类字段。已 `git checkout` 回退那 6 个文件，
  改成**纯文本替换 + 键名白名单精确匹配**。
- **残留风险（需知晓）**：`h5-chain-result.json` 的旧令牌**已在 git 历史里**（本次只改了工作区/新提交）。
  这些是 **dev 环境**令牌（TTL 2h，本地 dev 密钥签发），实际可利用窗口已过；若在意，需按
  「历史重写 + dev 密钥轮换」处理 —— 属需要你拍板的事，本轮未动历史。

## 管理端 · 新登记能力缺口（2026-09-19 夜，待拍板）

### D-ADM-4 无「创建供应商」接口 —— 设计 `page-4-1` 抽屉无法真正提交
- 全仓**没有** `POST /admin/providers`；`AdminProviderController` 只有 list / suspend / resume。
- **处置**：抽屉按设计实现完整 UI 与校验错误态（逐字用设计稿文案：「供应商名称不能为空」
  「地址格式不正确，需以 http:// 或 https:// 开头」「请填写 API Key，或点击「测试连通」完成校验」
  「有 N 项内容需要修正，修正后才能保存供应商」），但**保存 / 保存草稿 / 测试连通**三个动作都明确提示
  「后端未提供接口 → 本次未发出任何请求」，不伪造成功。
- **待拍板**：补后端创建接口（含校验规则与重复校验）/ 抽屉降级为只读示例 / 暂缓。

### D-ADM-5 无「管理端检测任务列表」接口 —— page-5-pc 任务监控无数据来源
- 全仓 admin 侧与检测任务相关的端点只有 `POST /detection-jobs/{id}/release`；
  `DET-01…05` 全部限供应商本人（管理端调用得 403 `E-1901`）。
- 因此设计稿的「运行中任务 / 排队等待 / 今日已完成 / 失败率」与任务表格**无法**用真实数据渲染。
- **处置**：页面顶部可见告警 + 可执行空态；KPI 渲染 `—`（**不用 0 冒充未知**）；
  筛选控件显式禁用；把**真实可用**的能力做成两张卡 —— 人工放行（DET-06，理由必填、1:1 产报告 AC-18）
  与检测项配置（ADM-CFG01…05，含 D1–D8 字典、权重/超时、DRAFT→PUBLISHED 发布）。
- **待拍板**：补管理端任务列表 + 聚合计数（注意与缺陷1 联动：执行器缺失时任务恒 `QUEUED`，列表价值有限）。

### D-ADM-6 无「立即同步 / 同步计划配置」接口 —— page-8-pc 的四个控件无后端
- 后端只有：读任务（ADM-S01/02）、按任务重试（ADM-S03）、读渠道绑定（ADM-S04）、启停（ADM-S05）、读上游清单（ADM-S06）。
  **没有**「立即触发渠道同步」，**没有**同步计划（下次同步/间隔）配置端点。
- **处置**：「立即同步」点击后明确提示「未发出任何请求」；「自动同步」开关禁用并标注原因；
  「下次同步 / 同步间隔」渲染 `—`；KPI 用真实列表统计（渠道总数 / 已同步 / 待同步 / 同步失败），
  并在页面上写明每个 KPI 的取数口径。
- **待拍板**：补触发同步端点与计划配置 / 维持只读 + 按任务重试。

### 设计源内部不一致（登记，不静默二选一）
- **供应商类型两套措辞**：`page-4-pc` 列表列「渠道商 / 原厂 / 中转商」 vs `page-4-1` 抽屉
  「官方直连 / 第三方代理 / 自建网关」。取值统一为后端枚举 `ORIGINAL | RESELLER | AGGREGATOR`，
  两套文案都在代码留痕，页面可见地说明该偏差。
- `page-8-pc` 的「同步价格」列在 `ChannelBinding` 无对应字段（价格在报价单/编译产物上）→ 渲染 `—`。

## 与他方会话的交汇（同一仓库并发提交，未改写他方提交）

1. **缺陷2（文件服务）已由另一会话修复**：提交 `9cf495f feat(server): 补缺陷2 文件服务 —— 合同链从此可签发、可下载（211/211 全绿）`。
   新增 `POST /api/v1/files`（multipart，字段 `file`，可选 `biz_type`）与 `GET /api/v1/files/{id}`。
   - 管理端两处文案已按事实更新（供应商资质文件 / 合同文本）：**代码已就绪**，
     但 ⚠️ **当前 dev 实例尚未重启到含该版本的构建** —— 实测 `POST /files` 仍返回 404 `E-1406`（2026-09-19 夜）。
     重启后再验上传/下载与合同签发链路。
   - 另一条管理端仍存在的限制：把文件挂到某供应商资质上的 `POST /provider/qualifications` 仅**供应商本人**可用
     （管理端 403 `E-1901`）→ 管理端无法代上传，只能只读展示。
2. **`aap-admin/index.html` 的内联空 favicon 由他方会话代为提交**（`e362ac6`，内容与本轮改动一致）。
   本轮的其余改动均在 `e362ac6` 之上，未 rebase / 未 reset / 未改写他方提交。

## 安全发现（静态确证，运行未复现）—— S-1 · `GET /files/{id}` 无归属校验

- **代码层确证**：`FileController` 类上无 `@PreAuthorize`；`SecurityConfig` 只把
  `/api/v1/**` 一律要求 `authenticated()`（`PUBLIC_PATHS` 不含 `/files`）→
  **任意已登录角色**（含普通供应商）只要拿到 `file_id` 就能 `GET /files/{id}` 下载**他人**文件
  （供应商资质、合同盖章件…）。`FileController` 的类注释写明「归属校验由各业务域自己做」，
  但该端点自身**没有任何归属判断**。
- **风险**：水平越权（IDOR）。雪花 ID 不易猜，但 `file_id` 会随业务响应下发
  （如合同详情的 `file_id`、资质文件的 `file_id`），跨账号拿到即可读。
- **运行层未复现**：本轮实测 `POST /files` 返回 404 `E-1406`（dev 实例未重启到含该版本的构建），
  因此**无法**在本实例上做「供应商账号读管理员上传文件」的实证 —— 只报代码层结论，不声称已实测。
- **建议（待拍板，不擅自改他方新代码）**：①`/files/{id}` 增加归属/用途校验（按 `biz_type` + 业务域回调），
  或 ②改为「一次性签名 URL / 短时效 token」，或 ③管理端专用下载端点（`GET /admin/files/{id}`）单独授权。
  另建议补一条负向集成测试：**用 B 账号取 A 账号的文件必须 403**。

## 产品可见限制 —— 报价单「表头字段」当前不可编辑（已留硬证据）

- **背景**：用户口径（2026-09-19）「卡片『报价』与『新建报价』应为同一页面，点『报价』= 对该报价单做编辑」。
  已统一为同一页面（提交 `5187745`），编辑态会回填名称 / 凭证 / 已选模型。
- **限制**：编辑态**只能真正改动明细行**，表头字段（名称 / 报价主体 / 凭证）**改不动**。
- **硬证据**（不再是「我记得」）：`QuoteController` 共 **12** 个映射，`@PutMapping` **只有 1 处**，
  且路径是 `/items/{itemId}`（明细行），**没有** `PUT /quotes/{quoteId}`（表头）。
  证据文件：`.agents/state/evidence/full-20260919/quote-routes.md` + `quote-routes.txt`。
- **当前做法（不假装）**：`loadExistingQuote()` 如实回填并让用户看到现状，
  保存时只提交明细；代码注释写明「表头字段在当前接口能力下无法修改」。
  UI 未把名称/主体/凭证渲染成可编辑控件，避免给用户「改了会生效」的错觉。
- **待拍板三选一**：
  1. 补 `PUT /quotes/{quoteId}`（后端加表头更新端点 + 状态机守卫：仅 `DRAFT` 可改）
  2. 维持现状，UI 把表头三项显示为**只读**并加说明文案（改动最小、零后端风险）
  3. 编辑态只允许改明细，表头要改就删单重建（当前实际效果，但需 UI 明示）
- **若选 1 需一并确定**：改表头是否触发版本快照（`aap_quote_version` 已有）、
  以及「已提交（SUBMITTED）的单子能否再改表头」的状态机规则。

## 严重发现 —— 雪花 ID 按 JSON number 下发，JS 客户端必然精度丢失（契约违背）

- **契约原文**（`docs/backend/json-schema/models/audit-log.schema.json`）：
  ```json
  "id": { "type": ["string","null"],
          "description": "雪花 ID（对外 string，避免 JS 精度丢失；可空）" }
  ```
  契约明确要求**对外 string**。实测却被下成**裸 JSON number**。
- **实测证据**：`GET /admin/catalog/vendors` 原始响应 `"id":459074703791419392`（18 位）。
  JS `Number` 安全整数上限 2^53 ≈ 9.0e15（16 位）→ 解析后**必然被舍入**，
  回传即打到**错的 ID**（404 / E-1406 / 误更新他行）。
- **发现路径（重要）**：**编译通过、单测全绿、既有 211 用例全绿**都发现不了 ——
  Java 侧 `Long` 没有精度问题。是**运行态验收**里「建完厂商紧接着用它的 id 建模型」
  这一步报 `E-1406 所属厂商不存在` 才暴露。
  → 教训：新增 HTTP 接口只过编译/单测是不够的，**必须真打一次往返**（建→用其 id 再操作）。
- **已修范围**：本轮新增的 `catalog` 模块（`CatalogViews` 的 `id` / `vendorId`
  加 `@JsonFormat(shape = JsonFormat.Shape.STRING)`）。修后验收 **24/24 全绿**，
  原始响应对账 `"id":"459075797691068416"` 精确无舍入。
- **⚠️ 未修范围（需你拍板，涉及面广）**：此问题**很可能不止 catalog**——项目里没有全局
  Long→String 的 Jackson 配置，也没有任何视图用过 `@JsonFormat`/`ToStringSerializer`
  （全仓 grep 为空）。既有视图若同样按 number 下发 ID，则**管理端与 H5 端所有
  「拿到 id 再回传」的操作都可能已经在打错行**，只是多数流程恰好没走这条路径而未暴露。
  建议：①全局注册 Long→String 的 Jackson 模块（一处修全，但要回归所有前端），
  或 ②逐视图补注解（安全但易漏）。**这与 D-ADM-4 一样属于需要你定的口径，我不擅自扩大改动面。**

## D-ADM-3 已解除 —— 模型管理页后端能力补齐并接线（2026-09-20）

- **用户报障**：「点击新增模型，功能好像还是没有实现啊，还是有缓存？」
- **定性**：**不是缓存，是前端从未接线**。实证：
  `grep -rn "admin/catalog" aap-admin/src/` → 零处调用；
  `views/models/index.vue` 仍写着
  「「${what}」后端未提供接口（D-ADM-3），本次未发出任何请求」。
- **后端**（上一轮已交付，提交 `b03f3c5`）：V9 迁移（`aap_vendor`+`aap_model`）
  + `/api/v1/admin/catalog/*` 6 个端点 + `/api/v1/catalog/models`（H5 只读），
  运行态验收 **24/24**。
- **前端**（本轮）：`src/api/admin/catalog.ts` + 重写 `views/models/index.vue`，
  按 Calicat **page-3 / page-3-1 / page-3-2** 逐字段还原。
- **验收**：管理端有头验收 **15/15**（新增**抽屉校验**：点开抽屉并确认设计稿必填字段
  真的渲染出来 —— 只查「按钮存在」会漏掉一整类假完成）；type-check 0；单测 52/52。
  真实 HTTP 33 次，含 `/admin/catalog/vendors`、`/admin/catalog/models/grouped`。

### 按原型还原时**刻意不编数据**的四处（设计稿有、后端无）

| 设计稿元素 | 处理 | 原因 |
|---|---|---|
| KPI 环比涨跌（↑8.3% 等） | 标「环比未采集」 | 后端无对比期数据 |
| KPI「平均可用率 99.36%」 | 标「未采集」 | 无可用率采集口径 |
| 表格「可用率」列 | 显示「未采集」 | 同上（不在 `aap_usage_hourly`） |
| 厂商次行「接入时间」 | **该段不渲染** | 出参未含 `createdAt`，不编造日期 |

**能取真值的都取了真值**：本月调用量走 `/admin/usage/hourly` 的 **model 维度**聚合
（`aap_usage_hourly.model_name` + `Bucket.total_tokens`，按「万」显示），
厂商维度的本月调用由该厂商下模型的用量汇总而来 —— 不是示意值。

### 仍然存在的两个边界（未变）

- 「测试连通 / 测试连接」按钮：后端无连通性测试端点 → **置灰并在 tooltip 注明**。
- 「批量管理」按钮：后端无批量端点 → **置灰**。
- `page-3` 的**外壳**仍是「智检云 / AI 检测中台 / 陈志远」孤例（D-ADM-2 待裁定）；
  本轮只还原**页面内容**，未改全局外壳（改一处会让它与其余 9 页不一致）。
