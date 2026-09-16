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
