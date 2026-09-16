# hioas-aap-001 · 报价端小程序页面计划（序号 = 执行顺序）

> 真源：Calicat 文件 `2095515676955668480` 画布 `2095515676976640000` →
> 台账 `.agents/state/aap-feature-status.csv`（本文件只做人类可读的说明）。
> 顺序按设计稿页面名前面的**序号**升序，逐个执行；每个页面走严格 TDD（见 `.agents/skills/dev/SKILL.md`）。

## 1. 范围划分

画布共 **30 个页面层**：22 个「报价端·小程序」+ 8 个「管理端」（PC / 应用）。
本轮目标 = `aap-client`（uni-app）里的 **22 个报价端·小程序页面**；管理端 8 页不在本轮范围（后续 `aap-admn` 另起循环）。

## 2. 执行顺序（22 页 + 4 个同页变体合并进主页面）

| 序号 | 页面 | 模块 | 目标路由 | inventory id |
|---|---|---|---|---|
| 1 | 登录注册 | 账号接入 | `/pages/login/index` | page-1-2 |
| 2 | 工作台 · 方案B 数据台（浅色版） | 工作台与我的 | `/pages/workbench/index` | page-2-b |
| 3 | 凭证列表（有数据） | 工作台与我的 | `/pages/credentials/index` | page-3 |
| 4 | 提交接入凭证（+ 准入表单变体） | 检测验真 | `/pages/credential-submit/index` | page-4-2 / page-24 |
| 5 | 检测进行中 | 检测验真 | `/pages/detecting/index` | page-5-2 |
| 6 | 大模型检测报告 · 多维度专业版 | 检测验真 | `/pages/report/index` | page-6 |
| 7 | 检测未通过报告 | 检测验真 | `/pages/report-failed/index` | page-7-2 |
| 8 | 报价单列表 | 报价管理 | `/pages/quotes/index` | page-8-2 |
| 9 | 模型报价设置-列表 | 报价管理 | `/pages/quote-models/index` | page-9 |
| 10 | 供应商档案编辑 | 档案与凭证 | `/pages/profile-edit/index` | page-10-2 |
| 10.1 | 供应商档案 | 档案与凭证 | `/pages/profile/index` | page-10-1-2 |
| 11 | 模型定价-详情 | 报价管理 | `/pages/model-pricing/index` | page-11 |
| 12 | 报价预览与提交（+ 新增报价单 初始态/下拉/保存成功 三个变体） | 报价管理 | `/pages/quote-preview/index` | page-12-2 / page-26 / page-apikey / page-29 |
| 15 | 合同签署 | 合同与通知 | `/pages/contract/index` | page-15-2 |
| 20 | 站内信列表 | 合同与通知 | `/pages/messages/index` | page-20-2 |
| 21 | 我的 | 工作台与我的 | `/pages/mine/index` | page-21-2 |
| 22 | 我的与用量概览 | 工作台与我的 | `/pages/usage/index` | page-22-2 |
| 23 | 我的设置 | 工作台与我的 | `/pages/settings/index` | page-23-2 |

> ⚠️ 序号 10 与 10.1 的名称有歧义（10 = 供应商档案**编辑**、10.1 = 供应商**档案**查看）；
> 按数字升序先做 10（编辑），若人工希望先做档案查看页，改台账 CSV 的序号码即可。

## 3. 每页 DoD（完成定义）

1. 设计与交互已抓取（`.calicat/raw/pages/<page-id>/{design,interaction,screenshot}.json`）。
2. 页面所有可见元素与交互逐条进台账；接口指向 `18-API设计OpenAPI.md` 的真实路径，缺依据标 `阻塞`。
3. 先红后绿：`npm test` 至少连跑两轮全绿，红基线输出留证据。
4. `npm run build:mp-weixin` 通过（`dist/build/mp-weixin` 产物存在）。
5. `npm run build:h5` + 浏览器截图存 `logs/screenshots/`。
6. 台账与 `.agents/state/aap-tdd-state.md` 回写，单独一次提交。

## 4. 已知冲突（不静默解决）

| 冲突 | 设计稿 | PRD | 处理 |
|---|---|---|---|
| 主色 | 蓝 `#1D4ED8` / `#2563EB` | 08-前端原型说明「深青 oklch(0.52 0.085 197)」 | **已确认：按设计稿蓝**（用户 2026-09-16 拍板，决策 D4 → `.agents/state/aap-decisions.md`）；`src/styles/tokens.scss` 顶部注释已同步，08-PRD 该描述作废 |
| 图例百分比 | 设计稿 page-2-b 图例 45+30+15+4+6+6 = **106%**（逐项取整的产物） | 设计稿自身不自洽 | **已按用户拍板统一口径**（决策 D3）：百分比一律由真实数值算（分母 `max(total_tokens, Σ六类)` + 最大余数法），环形图与图例共用同一份整数、合计恒 ≤ 100；设计百分比只作视觉参考 |
| 图标 | 设计为 remixicon 矢量图标 | 08-PRD 禁 emoji | **已确认：维持 CSS 绘制占位**（用户 2026-09-16 答复「可以」，决策 D5）；不引入图标字体库，未来拿到 iconfont/SVG 资产再整批替换 |
