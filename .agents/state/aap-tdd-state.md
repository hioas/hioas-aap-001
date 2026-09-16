STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。**每轮先读 `aap-decisions.md`**（待执行决策优先于本文件在办项）。**D1~D6 已全部执行完**（D6 挂起=不重命名）。当前在办：①**队列 8（给载体页补「设计期望值 checks」维度，一页一轮）：序号 3 已完成 09:38（160 条 · 15→0）· 序号 4 已完成 09:55（212 条 · 45→0）· 序号 4-v1 已完成 10:20（249 条 · 78→0）· 序号 5 已完成 10:42（237 条 · 95→0）· 序号 6 已完成 2026-09-16 11:5x（221 条 · 45→0，docH 4886→5343 = 设计帧高 5342，报告 `evidence/review-序号6-checks-报告.md`）· 序号 7 已完成 2026-09-16 11:3x（196 条 · 51→0，docH 1063→1111 = 设计帧高 1110，报告 `evidence/review-序号7-checks-报告.md`）· 序号 8 已完成 2026-09-16 11:5x（138 条 · 27→0，docH 1198→1206 = 设计帧高 1206，像素对账 42/42 命中，报告 `evidence/review-序号8-checks-报告.md`）→ 下一轮开工做 序号 9**（`page-9`「模型报价设置-列表」→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`，mock 目录 `api`；对照表 `python .agents/state/survey-harness-routes.py`） ②队列 1 逐页复核（7~23 行的 checks 维度待补） ③队列 7（uni-picker 溢出口径） ④D1 循环侧收尾余项（台账 `missing-prd` 接口备注改成「依据 `docs/api/接口字段级schema.md` §x」+ 字段名一致性核对；D1 本体的 schema 文档已由前台会话建好）。历史流水归档在 `aap-notes-archive-2026-09-16.md`，**不要每轮读**。
LEASE: free until -

# AAP TDD 推进 · 状态与目标（自驱动循环的单一事实来源）

> 每轮：读**决策台账 `aap-decisions.md`** → 读本文件 → 看 STATUS/LEASE → 取件（待执行决策优先）→ 做透（严格 TDD）→ 提交 → 回写台账与本文件 → 飞书简报。
> 本文件只留**当前状态 + 硬约束 + 关键命令**；历史流水追加到 `aap-notes-archive-*.md`，**不要每轮读**。
> ⚠️ 用户拍板的决定一律记在 `aap-decisions.md`，**不要凭状态文件 §4 的在办项自行发明目标**（例：目录改名已挂起）。

## 0. 状态与租约（每轮第一件事）

- 时间一律用 `date "+%Y-%m-%d %H:%M:%S"` 读，**禁止手写/推测时间**。
- 第 1 行 `STATUS: RUNNING | PAUSED: <原因> | DONE: <说明>`
  - `RUNNING` → 继续干活。
  - `PAUSED` → **本轮不动任何文件**，只回「仍在暂停：<原因>」，并且**必须**用
    `hermes send -t feishu:oc_7bb40d75cd345875ba9345a4fc599be2 "⛔ 需要你拍板：<一句话>"` 单独通知人类。
  - `DONE` → 回「目标已完成」，并 `cronjob_manage action='list'` 找 name=`aap-tdd` → `action='pause'`（**按名字找，不要硬编码 id**）。
- 第 2 行 `LEASE: <holder> until <YYYY-MM-DD HH:MM>`，本轮 id 用 `aap-tdd-run-<YYYYMMDD-HHMM>`
  - holder 以 `aap-tdd` 开头但**不是本轮 id**且未过期：看 `git log -1 --format=%cd` 与 `git status --porcelain` ——
    最近提交 **>45 分钟**前且工作区**干净** → 判定上一轮已死，**直接接管**（写成本轮 id + 现在+45 分钟），简报写「接管了死租约」；
    否则本轮跳过，只回「租约被 <holder> 持有至 <until>」，不碰文件。
  - holder 不以 `aap-tdd` 开头（人类/前台会话在改同一仓库）→ 本轮跳过。
  - `free` 或已过期 → 开工前写成本轮 id + 现在+45 分钟；提交后改回 `free`；预计超时中途续租。
  - **干净度判定请忽略这 3 个未跟踪项**：`.playwright-mcp/`、`aap-client/pnpm-lock.yaml`、`aap-client/pnpm-workspace.yaml`
    （后两个是一次 pnpm 尝试的残留，仓库实际用 npm —— 见 §3.9，不要擅自删/提交）。

> ⚠️ **cron 会话里不要再调 `hermes send -t feishu:oc_7bb40d75cd345875ba9345a4fc599be2`**：实测会被跳过（本 job 的最终回复自动投递到同一目标）。**简报与「⛔ 需要你拍板」都直接写进最终回复**即可，否则白丢一次工具调用（2026-09-16 08:35 轮实测）。

## 1. 目标

在 `E:\workspaces\hioas\hioas-aap-001` 用 **uni-app（Vue3 + Vite + TS）** 实现 Calicat 画布上
**报价端 · 小程序**全部页面与交互，**按页面序号逐个执行**，每页走严格 TDD（台账序号 1~23 已全部实现并留证）。

当前两条在办事项：

**(A) 目录命名对齐（用户 2026-09-16 明确要求）**：用户指定开发目录名为 **`hioas-aap-client`**
（与 Calicat 原型同名，用户已手工建出这个空目录）；现有代码在 **`aap-client/`**。
- 每轮开工**第一件事**：在仓库根 `git mv aap-client hioas-aap-client`。
- `fatal: renaming 'aap-client' failed: Permission denied` = **用户本机进程持有句柄**
  （实测元凶：用户自己的 `npm run dev:h5`（uni/vite dev server，cwd=aap-client）+ esbuild 子进程 + IntelliJ JS 语言服务）。
  → **绝不 kill 用户进程**（§3.10）。记一行「本机进程持有句柄，改名顺延」后**照做其余工作**，下轮再试；
  锁一放（用户关 dev server / 关 IDE）就会一次成功。
- 改名成功后**必须同批完成**：
  `aap-client` → `hioas-aap-client` 的全部**操作性**引用改写（`.agents/state/*.py|*.sh` 里的路径、
  本文件、`docs/aap-client-page-plan.md`、根 `README.md`、`.claude/skills/dev/SKILL.md`），
  并复跑 `npm test` 两轮全绿 + `npm run type-check` exit 0 + `build:mp-weixin` + `build:h5` 证明没搬坏；
  未改名之前**不做**改名后的路径改写。
  `evidence/`、`logs/` 下的历史日志是审计件，**一律不回改**。

**(B) 按序号逐页复核**（见 §4 队列）。

- 设计真源：Calicat 文件 `2095515676955668480`，画布 `2095515676976640000`（见 `.calicat/`）。
- 页面序号/顺序/目标路由：`.agents/state/aap-feature-status.csv`（台账，序号列即执行顺序）。
- 需求真源：`.calicat/prd/*.md`（22 份 PRD 卡；关键 = `01-PRD总览`、`09-检测验证引擎PRD`、
  `10-报价与合同结算PRD`、`11-同步与用量统计PRD`、`13-管理端PRD`、`17-零歧义执行规格spec`、`18-API设计OpenAPI`、`21-验收标准`）。
- 页面计划说明：`docs/aap-client-page-plan.md`。

## 2. 每页的标准动作（固定顺序，不得跳步）

1. **抓设计**：`python C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/calicat_source.py page --url https://www.calicat.cn/design/2095515676955668480 --layer-id <sourceLayerId> --page-id <页面ID> --out .calicat`
   → 产出 `raw/pages/<页面ID>/{design,interaction,screenshot}.json`（截图 URL 用 vision_analyze 看图，别猜样式）。
   报「请先在浏览器中打开文件」时用 `cmd /c start "" <design-url>` 拉起编辑器再重试。
2. **列功能清单**：从 design.json + interaction.json + 相关 PRD 抽出该页的每个可见元素与交互，
   逐条落到台账行（一条交互一行，`用例(证据)` 先写**计划中的用例名**）。
3. **梳理接口**：该页每个 `api` 类交互必须指向 `18-API设计OpenAPI.md` 的路径与方法；
   无接口依据的写 `missing-prd` 并标 `阻塞`，**不得臆造**。
4. **先写红测试**：`aap-client/tests/**` 下写断言 → 跑 `npm test` 看**真红**（贴报错行）。
   交互切片「写完页面才能看到红」时用 `.agents/state/strip-page-handlers.py strip|restore <页面路径>` 临时摘掉 `@tap` 绑定取证。
5. **实现到绿**：写 `src/**` 代码 → 复跑 → **连跑两轮全绿**才算过；`npm run type-check` 也要 exit 0。
6. **构建证明**：`npm run build:mp-weixin` 产出 `dist/build/mp-weixin`（能编译过 = 小程序可导入）；
   `npm run build:h5` + 430 宽 iframe 载体页 DOM 实测 + 截图（`logs/screenshots/`）作为可视化证据。
   **本机未装微信开发者工具**，故 mp-weixin 只做编译证明，真机/开发者工具验收留给人类。
7. **回写**：台账该行状态改 `已验证`/`部分`，`用例(证据)` 写真实用例名与命令；本文件 §4 追加一行本轮小结。
8. **提交**：只提交自己改动的文件，提交信息 `feat(aap-client): <序号>-<页面> <做了什么>`。

## 3. 硬约束

1. **严格 TDD**：先写会红的断言 → 看红基线 → 实现 → 复跑绿 → **连跑两轮**一致才算过。
2. **不得臆造**：接口、字段、错误码、页面元素一律来自 `.calicat/` 证据或 PRD；缺依据就标 `阻塞` 并写进简报。
3. **一页一提交**：不跨页面混装；台账、状态文件与该页代码同批提交。
4. **证据要有牙齿**：vitest 真跑输出（不是"应该能过"）+ H5 截图 + mp-weixin 编译产物存在。
   `npm run dev` 能起 ≠ 页面能用。视觉结论一律以 430 宽 iframe DOM 实测数字为准（`vision_analyze` 对窄截图会误报「右侧被裁切」）。
5. **中文页面文案**必须与设计稿一致（design.json 里的文字为准），不得自己改写。
6. **设计系统先抽取**：`src/styles/tokens.scss` + 基础组件为单一来源，新页面复用，不许每页各写一套。
7. 凭证/密钥不落盘、不打印；不把 `.calicat/raw` 大文件提交进仓库（`.gitignore` 已挡）。
8. cron 会话里 `python -c` / `node -e` / `execute_code` 可能被安全策略拦 → 脚本一律先 `write_file` 落成 `.py`/`.mjs` 再执行。
9. **仓库里有两套 lock/工作区文件**（`package-lock.json` 用 npm、`pnpm-lock.yaml` + `pnpm-workspace.yaml` 是一次 pnpm 尝试的残留）：
   统一用 **npm** 跑命令；这两个 pnpm 文件**不是本循环的产物，不要删也不要提交**，等人类定夺。
10. **绝不 kill 用户的本机进程**（IntelliJ / `npm run dev:h5` / Playwright-MCP / claude.exe ACP）。
    目录被占用只顺延，不动刀；`taskkill` 只对**本循环自己起的**后台进程（如 `serve.py` 静态服务器）使用。
11. **用户在做中的改动优先**：开工前若发现工作区有用户自己的改动（非本循环产出），不 commit、不 revert、不覆盖，
    在简报里说明并让路；本循环只提交自己改动的文件。

## 4. 工作队列（严格按序；一行一轮，别跳）

0. ~~**目录命名对齐（`git mv aap-client hioas-aap-client`）**~~ —— **挂起，勿再重试**（决策 D6，2026-09-16 前台会话决定：仓库内模块目录沿用 `aap-*` 与 `aap-server`/`aap-admn` 对齐，`hioas-*` 是仓库名约定，不是模块目录约定）。本轮（08:35 轮）仍在重试前已按旧在办项试过一次，得到 `Permission denied`（用户 dev server 持句柄）→ 自 D6 起**不再重试**。
  - ⚠️ **cron 任务 prompt 里仍写着「每轮先试一次 `git mv`」——该条已被决策 D6 取代，勿再执行**：人类 2026-09-16 在 `aap-decisions.md` D6 明确「不重命名（`hioas-*` 是仓库名约定，不是模块目录约定），勿再重试」，凡 prompt 与本文件/决策台账冲突，一律以人类决策为准（本文件即此记录）。
1. **按台账序号 1→23 逐页复核**（不重写页面，只做客观复核 + 修偏差）：每页跑
   `npm test` **连跑两轮**全绿 · `npm run type-check` exit 0 · `build:mp-weixin` 产物存在（`pages/<route>/index.{js,json,wxml,wxss}`，
   `credential-submit/form`、`quote-form/{index,apikey,success}` 等同理）· 有 `__measure-*.html` 载体页的页面复跑 430 宽 DOM 实测并用
   `.agents/state/cmp-measure-runs.py` 证明**两次独立测量一致**；有偏差按 §2 的第 4~6 步（先红后绿）修；台账行写「复核通过 <时间> + 命令」。
2. ✅ **已拍板口径的落地核对（已完成 2026-09-16 09:26）**：用户已拍板一条 —— 报价单列表「新建报价」与检测报告「填写报价」落点 = `/pages/quote-models/index`
   （画布序号 9；已落 `e1522f7`）。复核时确认 22 页里**没有别处**仍把 `/pages/quote-form/index` 当「新建/填写」入口，
   有则按同口径改（**先红后绿**，别只改注释）。→ **核对结果：无遗漏** —— `src/pages/quotes/index.vue:158`（新建报价）与 `src/utils/report-model.ts:112 QUOTE_ROUTE`（填写报价）及断言 `tests/pages/quotes.spec.ts:156` / `tests/pages/report.spec.ts:190` 均为 `/pages/quote-models/index`；卡片内「报价」= `quote-form/index?quoteId=`（按设计稿打开当前报价单，带参，非「新建」入口，保留）；唯一残留是 `tests/pages/report.spec.ts` 头部旧注释（已改）；台账序号 6 行已追记。
3. **15 条待人类拍板缺口**：只做**可自主**的部分；未拍板的**保持原样**，每轮简报只列 1 条最该拍的，不擅自改设计稿口径。
4. 画布余下 **8 个管理端 PC 页（`aap-admn`）** —— **本轮范围外**，除非人类放行，不要开工。
5. ✅ **补 序号 9 的测量面 fixture（已完成 2026-09-16 08:28）**：`api/v1/quotes/q9/items/index`（GET 明细行；页面按 `src/api/quote.ts:90` 的回落入口取数）。
   已补 fixture + 同探针 before/after（`__measure-model-pricing-q9.html`，red=404 无明细 / green=gpt-4o·2.50·10.00 且 PUT 成功）+ 解析器体检 `check-mock-fixtures.py` 红→绿；
   **用 `api` 目录的 8 页（3、4、4-v1、5、6、7、8、9）已两轮复跑**：两轮一致，且与上轮 review 留证逐字节相同（仅序号 9 的 phase4 由「404 文案」变回「保存成功 + 跳 model-pricing」，正是本缺口）。
6. ✅ **给 序号 1（登录注册）、2（工作台）补 430 宽载体页（已完成 2026-09-16 08:58）**：新增 `__measure-login.html`（93 条设计期望值 checks + 6 相交互：空表单 / 缺短信码 / 未勾协议×2 / 获取验证码 / 登录成功；`?scenario=guard` 只跑校验门）与 `__measure-workbench.html`（92 条 checks + 交互回放 2-actions）；两页均**两轮独立测量全等**且 `checkFails` 49→0 / 7→0；配套补 `api/v1/auth/sms/{send,login}/post` fixture（红 FAIL 2 → 绿 FAIL 0）；新增证据维度 `evidence/requests-序号<tag>-run{1,2}.txt`（serve 实收请求行，写请求带 body）——「校验门有没有偷偷发请求」由 **guard 场景 requests 0 行**直接证明，不再靠页面自报。（脚本升级：`review-measure.sh` 支持第 5 个参数 url 查询串 + 落 requests 证据；`check-mock-fixtures.py` 新增两条 POST 检查并把变体目录名（`api-tmp-noauth`）归到基础 mock；新增 `cmp-flat-phase.py`（扁平老留证 vs 新 phase 跨代对比）、`text-list.py`、`append-login-structure-tests.py`）
   两轮 dump-dom + 与建页留证对比；这两页此前只有截图/产物证据，是逐页复核里唯一没有客观 DOM 数字的两行。**← 下轮开工第一件事**
7. （工具卫生）把「uni-app 内部测量元素不计入溢出统计」的口径补到序号 22 的载体页（`uni-picker`），与序号 6 已修的 `uni-resize-sensor` 同族；
8. **给其余 20 个载体页补「设计期望值 checks」维度**（本轮新立，从序号 3 开始，一页一轮）：现有载体页只测「文案齐、溢出 0、两轮一致」，
   本轮登录页的经验说明**还能量出与设计树的逐项偏差**（序号 1 就量出 49 条）。做法照 `__measure-login.html` 的 `chk(k, got, want)`：
   want 一律取 `.calicat/raw/pages/<page>/design.tree.json` + `node-probe.py` 的声明值，不许凭截图目测。
   - ✅ **序号 3 已完成 2026-09-16 09:38**：`__measure.html` 内置 **160 条 checks**（含 effects 声明：`probe-effects.py` 读 design.json 的 drop_shadow），
     红基线 **15/160**（`evidence/red-序号3-checks-设计期望值偏差.txt`）→ 绿 **0/160**（`evidence/green-序号3-checks-设计期望值.txt`），两轮独立测量全等 47/47。
     修掉 4 类偏差：顶部栏 1px 分隔由 border 改为设计声明的 `drop_shadow(0,1,0,#F1F5F9)`（border 把栏高撑成 69，设计 68 → 整页 docScrollHeight 944→943）、
     顶部栏按设计 `3ad1d267` 加「顶部左侧」组（返回按钮 + 标题块 gap 12；修前被 space-between 撑到 99）、8 处字重按设计 fontFamily 对齐（Bold→700 ×3 / SemiBold→600 ×3 / Medium→500 ×2）、
     底部 TabBar 四项按设计各 76 宽 + space_between（修前 flex:1 = 100）。**下一轮：序号 4**。
   - ✅ **序号 4 已完成 2026-09-16 09:55**：`__measure-submit.html` 重写为 430 宽 iframe + **212 条 checks**（红基线 **45/206** → 绿 **0/212**，两轮独立测量 33/33 全等）。
     设计期望值口径升级为**两类来源**：①声明值（design.tree.json + node-probe/dump-node-fields）；
     ②fit_content 行的**真实高度**取设计 PNG 色带实测（新增 `png-rows.py`/`png-profile.py`/`png-xruns.py`）。
     据此修掉 7 类偏差，其中**卡边界做到像素级一致**：顶部栏 84→96（返回图标盒 24×24→26×36 = remixicon 24px 行框）、
     卡高 126/169/132/343→**133/172/137/354**（= 设计 PNG 108/241·253/425·437/574·586/940）、
     卡片描边 border→box-shadow（Figma center 描边不占布局，内容宽 356→358）、图标占位盒按设计声明尺寸（26/20/16/14/22 宽，字号×1.5 行框）、
     提示文本左移 6→4、已配置字重 600→500、编辑图标盒 24×24→20×27。**关键模型**：设计里 fit_content 行高 = 图标字形行框（fontSize×1.5）。
     证据：`evidence/review-序号4-checks-run{1,2}.json` · `red/green-序号4-checks-设计期望值*.txt` · `cmp-序号4-上一轮vs本轮.txt` ·
     报告 `evidence/review-序号4-checks-报告.md` · 430 宽截图 `evidence/20260916-0955-序号4-提交接入凭证-checks轮-h5-430宽.png`。
     设计帧重抓（09:59）sha256 逐字节相同（`29757a6f…`，无漂移）。**下一轮：序号 4-v1**（`__measure-form.html`，先补成 430 宽 iframe 体例）。
   - ✅ **序号 4-v1 已完成 2026-09-16 10:20**：`__measure-form.html` 由旧体例重写为 430 宽 iframe + **249 条 checks**（phase1 空态 6 条、phase2 已上传态 249 条），
     红基线（`git stash` 复现修复前代码、同一份探针两轮）**phase1 5/6 · phase2 78/249** → 绿 **0 / 0**，两轮独立测量 **33/33 字段全等**；
     整页 `docScrollHeight` **1079 → 1137**（= 设计帧高；空态 1071），关键几何与设计 PNG 色带 **x=30/x=100 两列逐带相同**
     （`cmp-序号4v1-设计PNGvs实现截图-色带.txt`）。修掉 9 类偏差：顶部栏 68→74、7 个图标盒按设计图层（20×27 / 24×33 / 22×30 / 16×21，形状入 `::before`）、
     13 处字重（Bold→700 / SemiBold→600）、文本行高（11→16 / 12→18 / 13→20 / 14→20 / 18→24）、中心描边 0.8 由 border 改 box-shadow、
     上传区 dashed→**实线**、备注框 52→56、文件行 48→54、删除盒 20×20→20×27。
     交互相：guard 场景两轮 **0 行 /api 请求**；补必填后真实 POST `/provider/qualifications` → 跳 `/pages/detecting/index?jobId=j1`（mock fixture 本轮补齐，先红后绿）。
     证据 `evidence/review-序号4v1-checks-报告.md` · `red/green-序号4v1-*` · `cmp-序号4v1-*` · 截图 `evidence/20260916-1022-序号4v1-…-h5-430宽.png`。
     设计帧重抓 sha256 `bd249858…` **逐字节相同**（无漂移）。
   - ✅ **序号 5 已完成 2026-09-16 10:42**：`__measure-detecting.html` 由 129 行旧体例重写为 430 宽 iframe + **237 条 checks**
     （want = page-5-2 `design.json` 声明值 + 设计 PNG 色带/墨迹实测：顶部栏 96 · 卡高 196/434/72 · 行高 34/行距 46 · 成本块 58 · 提示卡 72 · 底栏 84；
     进度填充 PNG 实测 **208**，设计树写 209 是陈旧值）。
     红基线（`git stash push -- src/pages/detecting/index.vue` 复现修复前代码、同一份探针两轮）**phase1/phase2 各 95/237**（`red-序号5-checks-设计期望值偏差.txt`）→ 绿 **0/237**
     （`green-序号5-checks-设计期望值.txt`），两轮独立测量 **32/32 字段全等**，`docH 934`（= 设计帧高，修前 900）。
     修掉 9 类偏差：顶部栏 84→96（返回图标盒 26×36）· 卡1 184→196（标题行 26）· 卡2 416→434（行高 34/行距 46）· 提示卡 68→72（文案行高 16 + `align-self:center`）·
     成本块 52→58 · 元信息行 14→18 · 描边 `border`→`box-shadow 0 0 0 1px`（内容宽 356→358、行左 37→36）· 卡1 补设计 `drop_shadow(0,6,20,rgba(15,23,42,0.06))` ·
     7 个图标盒按设计图层（26×36 / 22×30 / 20×27 / 22×30 / 22×30，形状移入 `::before`）。
     像素对账 `cmp-序号5-设计PNGvs实现截图-色带.txt`（±1 容差）：x=62 列 41 个粗边界 36 命中，全部关键结构行命中；未命中 22 行全为「卡1 投影渐变台阶（Figma vs Chrome 衰减差异）」
     与「H5 回退字体墨迹边界（块级几何与居中位置逐项相同）」两类 → 非页面缺陷。交互相：历史报告按钮 client-only → toast + hash 不变 + serve 实收 10 行全为成对轮询 GET、零写请求。
     **下一轮：序号 6**（`page-6`「大模型检测报告 · 多维度专业版」→ `/pages/report/index`，载体页 `__measure-report.html`，mock 目录 `api`）。
   - ⚠️ 本轮踩到并写进 §5 的坑：重抓前必须先确认 Calicat 编辑器在浏览器里打开（否则 22 帧全 FAIL `请先在浏览器中打开文件`）；
     `cmp-measure-runs.py` 对扁平文件也要传 phase 名（传 `flat`）；Chrome `--screenshot` 的中文路径会被 MSYS 弄坏 → 先写 ASCII 临时名再 `cp`；
     探针自身 4 处口径错误（`.card__hint` 只有 2 处不是 3 处、`.card__title-row` 首个是 APIKey 卡、`.card__field` 的 8px 是 padding 不是间距、`declared()` 不认 `[data-testid=...]`）。
   - ⚠️ 本轮踩到并写进探针的 3 条口径（**探针自身**的坑，不是页面缺陷）：①设计里 chip 的「待检测 3」是 dot+label+count 三个节点用 flex `gap` 隔开，`textContent` **没有空格** → 分开断言 `chip__label`/`chip__count`；
     ②在 `padding` 容器内的卡片，左右边要按容器内边算（序号 3 的卡是 20/410，不是 16/414）；③`0.8px` 描边的 computed 是 **used value**（Chrome 取整成 1px）→ 判「样式表声明值」（探针新增 `declared(sel, prop)` 读 CSSOM），used 值另记一条；
     ④box-shadow 颜色 alpha=1 时 Chrome 序列化成 `rgb()`（`norm()` 已改成 alpha 感知，否则误报）。
   - 探针工具：`python .agents/state/show-checks.py <run.json> [out.txt]` 打印 checks 概览 + 失败清单（红/绿基线转录）；拍 430 宽截图 `bash .agents/state/shot-430.sh <输出.png>`（自带静态服务器，用完即关）。
9. **决策台账 `aap-decisions.md` 的待执行项优先于本队列**（前台会话 2026-09-16 建立该文件，状态文件顶部已加提醒）：
   - ✅ **D3 · 图例百分比统一且最优** —— **已完成 2026-09-16 09:26**（口径落在 `src/utils/percentage.ts`，执行证据见 `aap-decisions.md` D3）。**下轮第一件事 = 队列 8**（给序号 3 的载体页补「设计期望值 checks」维度，照 `__measure-login.html` 的 `chk(k,got,want)` 做法）。
   - **D1 的循环侧收尾**：把台账里 `missing-prd` 的接口备注改成「依据 `docs/api/接口字段级schema.md` §x」，并核对已实现页面字段名与该 schema 是否一致（不一致以 schema 为准改代码）。
   - D2 已完成（2026-09-16 09:15）；**D4/D5 的循环侧小改已完成 2026-09-16 09:26**（`src/styles/tokens.scss` 顶部注释改为「主色=设计稿蓝（D4）+ 图标维持 CSS 占位（D5）」；`docs/aap-client-page-plan.md` §4 表格三行冲突结论更新）。D1~D6 至此全部有结论。
   - ⚠️ 已向人类提一条拍板：D2 的验收「`src/` 内 grep 钱包 = 0」与设计稿冲突（mine 页的「我的钱包」卡是 page-21-2 图层），建议改为按 `src/pages/workbench/**` 计。

### 本轮小结（追加式，一行一轮）

- 2026-09-16 08:0x（前台会话，非 cron 轮）· **收纳用户在做中的改动 + 循环复位**：
  ①发现 `hioas-aap-client/`（用户 07:45 建）是空目录、代码在 `aap-client/` → 判定为**目录命名问题而非重建**，
  改用 `git mv` 对齐；实测被用户自己的 `npm run dev:h5`（PID 30432，cwd=aap-client，07:04 起）+ esbuild 子进程 +
  IntelliJ JS 语言服务持句柄 → `Permission denied`，**未杀用户进程**，改为每轮重试（§1 A）。
  ②收纳用户在做中的 3 处改动为独立提交：`e1522f7` 落点对齐 page-9（代码+2 用例断言）、
  `0b1ac10` H5 联调假后端（dev-only `/api/v1/auth`，短信码 123456）、`4e584ea` dev SOP 扩写 v1.2。
  ③基线留证：改前后 `npm test` **1141/1141 · 69 files** exit 0、`npm run type-check` exit 0。
  ④本文件历史流水（146,736 字节）归档为 `aap-notes-archive-2026-09-16.md`，本文件瘦身为「当前状态 + 队列」。
  ⑤清理本循环自己的遗留：两个 01:25/01:43 起的 `serve.py` 静态服务器已 kill，并按原参数在 5199 端口重启，
  用户浏览器原 URL 不受影响。

- 2026-09-16 08:11（cron 轮 `aap-tdd-run-20260916-0805`）· **目录改名顺延 + 逐页复核（430 宽 DOM）覆盖 20/22 页**：
  ①**改名**：`git mv aap-client hioas-aap-client` 仍 `Permission denied`（用户 `npm run dev:h5` 持句柄）→ 记一行顺延，**未杀用户进程**（§3.10）。
  ②**仓库基线**：`npm test` **1141/1141 · 69 files** 连跑两轮 exit 0；`npm run type-check` exit 0；
  `npm run build:mp-weixin` exit 0。新增 `.agents/state/review-artifacts.py` 按台账「目标路由」核 22 行 →
  **22/22 路由 mp-weixin 三件套（js/json/wxml）齐备且注册在 app.json**（wxss 仅在页面有样式时产出，不算缺失）。
  ③**逐页 DOM 复核**：新增 `review-measure.sh`（一页两轮 dump-dom）/`review-compare.py`（两次独立测量 + 与建页留证对比）/
  `show-measure-fields.py` / `gen-review-report.sh`，报告 `.agents/state/evidence/review-measure-20260916-0805.md`。
  覆盖 3、4、4-v1、5、6、7、8、9、10、10.1、11、12、12-v1、12-v2、12-v3、15、20、21、22、23 共 20 页：
  **两次独立测量在每个分组上都全等（不一致 0）**。
  ④**三处差异全部定位为非页面缺陷**（报告里逐条留证）：序号 6 / 10 / 9 的差异都是「留证文件早于同轮/本页提交」的过期快照
  （6 早于载体页 01:28 更新；10 早于 a5916ac 02:46:57 的「双角标补红」；9 早于 cc98e23 02:24:51），
  序号 22 的 `overflowing` 两轮波动系 uni-app 内置 `uni-picker` 空 div（父级 overflow:hidden，`docScrollWidth` 两轮均 430）。
  ⑤**修掉本循环自己的两个取证工具缺陷**：`cmp-measure-runs.py` 不支持扁平单段文件；`review-compare.py` 曾漏比「顶层标量字段」
  （被 rect 分组掩盖）——都补齐后**全量重跑**，结论不变。
  ⑥**台账回写**：22 行里 20 行追加「复核通过 2026-09-16 08:11 + 命令 + 证据文件」，4 处差异补 `备注`。
  ⑦**下轮开工第一件事**：补 `api/v1/quotes/q9/items/index` fixture（页面按 `src/api/quote.ts:90` 回落取明细行）并回跑用 `api` 目录的页面；
  再给 序号 1/2 补 430 宽载体页。

- 2026-09-16 08:30（cron 轮 `aap-tdd-run-20260916-0820`）· **补 序号 9 测量面 fixture + 复跑 `api` 目录 8 页 + 修探测噪音**：
  ①**改名**：`git mv aap-client hioas-aap-client` 仍 `Permission denied`（用户 `npm run dev:h5` 持句柄）→ 记一行顺延，**未杀用户进程**（§3.10）。
  ②**fixture 红→绿**：新增 `.agents/state/check-mock-fixtures.py`（自起 serve.py + http.client 直连校验，另做「mock 目录所有 fixture 均可按路径取到」的反向体检）——
  红基线 1 FAIL（`GET /api/v1/quotes/q9/items` 404，证据 `evidence/red-mock-fixture-q9items.txt`）→ 补 `api/v1/quotes/q9/items/index`
  （3 行明细：字段来自 15-数据字典/`QuoteItemRaw`，模型名与单价来自设计 page-9 的行值与上轮实测请求体 `{"items":[{"model_name":"gpt-4o"}]}`，不臆造）→ 全 PASS（`evidence/green-mock-fixture-q9items.txt`）；
  新增 `.agents/state/make-mock-variant.py` 造「同目录去掉该 fixture」的变体，供**同探针 before/after** 用。
  ③**同探针 before/after**：新载体页 `__measure-model-pricing-q9.html`（序号 9「保存并继续」落点 `model-pricing?quoteId=q9`）——
  before（`review-序号11-fallback-red-run{1,2}.json`）toast「mock 未定义该接口: /api/v1/quotes/q9/items」· modelName 空 · 点保存「未找到模型明细，请返回重试」；
  after（`review-序号11-fallback-run{1,2}.json`）toast 空 · `gpt-4o` · `2.50/10.00` · 档位 base · 规则组 #1，点保存 → serve 日志实测 `GET /quotes/q9/items 200` + `PUT /quotes/items/qi1` body 带 2.5/10 → 「保存成功」。
  ④**回跑 8 页两轮**：3/4/4-v1/5/6/7/8 的 review JSON 与上轮留证**逐字节相同**（git 判定无改动＝最强一致性证明）；序号 9 仅 phase4 由 404 文案变回「保存成功 + 跳 model-pricing」，正是本缺口。
  ⑤**修探测工具缺陷**：序号 6 phase1 的 `overflowing` 两轮波动（0/2）由新探针 `__diag-report-overflow.html`（三时刻采样 + 祖先链）定位为
  `<image mode="widthFix">`（雷达图）挂的 **`uni-resize-sensor`** 内部两个空 div（宽 100000/352，负偏移量测；docScrollWidth 恒 430 = innerWidth）
  → 在该载体页溢出统计里过滤后 phase1/phase2 全等 65/65 且与留证全等 65/65（`review-序号diag-report-run{1,2}.json`）。
  另：序号 4 与建页留证的 3 处差异已定位为 shared mock 凭证 `api_key_mask` 在 cc98e23 变更（page-4 的 16 点 → page-9 的 `sk-prod-••••••••2f9a`，同一 mock 无法同时满足两帧设计值）→ 非页面缺陷。
  ⑥**基线**：`npm test` **1141/1141 · 69 files** 连跑两轮一致 exit 0、`npm run type-check` exit 0（本轮未改 `src/`）。
  ⑦**产物**：报告 `.agents/state/evidence/review-measure-20260916-0830.md`；台账 4/6/9 行已回写（含命令与证据文件名）。
  ⑧**下轮开工第一件事**：给 序号 1（登录注册）/ 2（工作台）补 430 宽载体页（队列 6）。

- 2026-09-16 08:58（cron 轮 `aap-tdd-run-20260916-0835`）· **补 序号 1/2 载体页（队列 6 收官，22/22 页全覆盖）+ 两页按设计树修掉 56 条偏差 + 补 auth fixture（红→绿）**：
  ①**改名**：`git mv aap-client hioas-aap-client` 仍 `Permission denied`（用户 `npm run dev:h5` 持句柄）→ 记一行顺延，**未杀用户进程**（§3.10）。
  ②**新增载体页**（本轮主交付）：`__measure-login.html`（序号 1）与 `__measure-workbench.html`（序号 2），两页都把设计期望值写进探针：`checkCount` 93 / 92，`checkFailCount` 即「与设计稿的偏差条数」。
  ③**先红后绿**：修前 `checkFailCount` 登录页 **49** / 工作台 **7**（两轮完全一致，逐条清单转录在 `evidence/red-序号12-修前偏差-转录.txt`）→ 修后 **0 / 0**。登录页按设计重排品牌区为 `Logo行`（Logo 54x54 r16 + 12 + 品牌名块）、去掉表单卡片 -32px 负边距、输入框 h48/r12/底 rgb(248,250,252)、验证码块与「获取验证码」按钮 112x48 r12 带描边、勾选框 18x18 r6、免责说明改为 container 内白卡、主/微信按钮 h50 r14；工作台修 7 处色值并让模型序号四行文字逐行给色。
  ④**单测（真红→绿）**：新增 `tests/unit/workbench-model.spec.ts`（序号逐行配色）与 `tests/pages/login.spec.ts` 两个结构用例，红基线 `evidence/red-序号12-结构用例.txt`（3 failed / 15）→ 绿 15/15；全量 `npm test` **1145/1145 · 70 files 连跑两轮**（evidence/green-序号12-全量轮{1,2}.txt）。
  ⑤**fixture 缺口（同族于序号 9 那次）**：登录页真发的两个 POST 在 mock 里没有 → `check-mock-fixtures.py --mock api-tmp-noauth` FAIL 2 → 补 `api/v1/auth/sms/{send,login}/post` 后 FAIL 0；**同探针 before/after**：`aap_token` 由 `{"type":"undefined"}`（等于没写进真 token）变为 `tk-mock-001` 且跳 `/pages/workbench/index`。
  ⑥**证据有牙齿**：`?scenario=guard`（空表单/缺短信码/未勾协议×2）两轮 serve 实收 **0 行 /api 请求**（requests-序号1-guard-run{1,2}.txt 皆 0 行），`?scenario=` 全量则实测 `POST /auth/sms/send`（body phone+captcha）→ `POST /auth/sms/login`（body phone+smsCode）→ `GET /provider/profile` + `GET /usage/summary`；工作台 2-actions 的钱包=client-only（toast「钱包功能开发中」且 hash 不变）、Tab 我的 → `/pages/mine/index`。
  ⑦**跨代对比**：工作台与建页老留证（扁平结构）用新增的 `cmp-flat-phase.py` 对比，公共键 16 → 相同 12，4 处差异全部 = 老留证那轮 iframe 有可见滚动条（innerWidth 同为 430 而 `docScrollWidth` 415）：docScrollWidth/avatarRight/todoChevronRight 各 +15、条填 95→102（42% × 轨道宽）→ **非页面漂移**（evidence/cmp-序号2-老留证vs本轮.txt）。
  ⑧**产物与报告**：`build:mp-weixin` exit 0（`dist/build/mp-weixin/pages/{login,workbench}/index.{js,json,wxml,wxss}` 齐备）、`build:h5` + 430 宽实测、`type-check` exit 0；报告 `evidence/review-measure-20260916-0900.md`（含差异判读 6~9）。
  ⑨**下轮开工第一件事**：改名重试 → 队列 9（已拍板口径核对）→ 队列 8（给序号 3 的载体页补 checks 维度）。

- 2026-09-16 09:15（**同一 cron 轮 `aap-tdd-run-20260916-0835` 的后半段**）· **发现了并发的人类/前台会话决策台账，并执行 D2（删「钱包」入口）**：
  ①**发现**：提交前 `git log` 里出现非本轮的 `cb926a8 docs(api): 补接口字段级 schema + 决策台账 D1-D6（用户拍板）`（08:56:44），新增 `aap-decisions.md`、`docs/api/接口字段级schema.md`、`push-calicat-doc.py`，并改状态文件顶部加「每轮先读决策台账、待执行决策优先」。已核对：其状态文件改动仍在（未被本轮覆盖），本轮三个提交**未包含**其任何文件。
  ②**D6**：目录改名**挂起、勿再重试**（`hioas-*` 是仓库名约定）→ 已从队列移除并标注。
  ③**D2 执行（先红后绿）**：工作台快捷入口「钱包」整项删除（连同 `onQuick` 里的 toast 死分支）+ 单测改 4 项断言与「删干净」新用例（红 3 failed → 绿 16/16）；载体页 phase2 由「钱包 client-only」换成「评测 → 凭证列表」，「钱包」移入 `removedByDecision`；两轮实测 `checkFailCount 0/92`、`walletEntryAbsent=true`、`pageTextHasWallet=false`、`navigating→/pages/credentials/index`、溢出 0；全量 `npm test` **1145/1145 ×2**、type-check exit 0、两个 build DONE（证据 `evidence/green-D2-全量轮{1,2}.txt`）。
  ④**向人类提拍板一条**：D2 写的「`src/` 内 grep 钱包 = 0 命中」按字面做不到 —— mine 页的「我的钱包」卡是设计稿 page-21-2 的图层，删它违背「设计稿优先」；已建议改成按 `src/pages/workbench/**` 计（当前已满足）。本轮未擅自扩大删除范围。
  ⑤**下轮第一件事**：执行 **D3**（图例百分比统一且最优：最大余数法 + 环形图与图例同分母），再回头做队列 8（给序号 3 的载体页补 checks 维度）。

- 2026-09-16 09:26（cron 轮 `aap-tdd-run-20260916-0910`）· **执行决策 D3（图例百分比统一且最优）+ 队列 2 口径核对 + D4/D5 循环侧小改**：
  ①**D3 落地（本轮主交付，严格 TDD）**：新增 `src/utils/percentage.ts`（唯一口径：分母 = max(total_tokens, Σ六类) + 最大余数法 + `percentTotalOf`），
  `workbench-model.ts` 出 `ring{hasData,denominator,segments,percentSum,remainderPercent}` 与 `categories[i].percent`，
  页面 `donutBackground` 只读 `model.ring`（不再自算比例）；三个红基线（`red-D3-01/02/03*.txt`，含 `'45% · 1.74B' ≠ '42% · 1.74B'` 与 conic 42.54% ≠ 图例整数 42）→ 三处绿。
  实测：分母 4.09B → 图例 **42/28/14/4/6/6（合计 100，修前照抄设计稿=106%）**，环形图分段宽与图例逐项相等；缺字段场景两行 `—`（不显示 0%）、4 段 + 6% 余量 = 100。
  ②**证据有牙齿**：载体页 `__measure-workbench.html` 新增 11 条 D3 checks（`d3.legend.*` / `d3.ring.stopWidths` / `d3.ring.stopColors` / `d3.ring.remainder` / `d3.ring.totalPct` / 设计字面量必须缺席）
  + `overriddenByDecision` 决策留痕；`api` mock 与 `api-tmp-d3-nomedia` 两种场景各跑**两轮独立测量全等**（`review-序号2-d3-run{1,2}.json` / `review-序号2-d3nomedia-run{1,2}.json`，`checkCount 103 · checkFailCount 0 · 溢出 0`）；
  变体用新增的 `make-nomedia-mock.py` 复现（用完已 clean）。与 D2 轮留证差异仅 D3 相关 7 项。
  ③**质量门**：`npm test` **1168/1168 · 72 files 连跑两轮**（`green-D3-全量轮1/2.txt`）· `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE（`pages/workbench` 四件套齐备）·
  截图 `logs/screenshots/20260916-0921-序号2-工作台-图例统一口径D3-h5-430宽.png`。
  ④**队列 2**：全仓库核对「新建/填写报价」落点确为 `/pages/quote-models/index`，无遗漏；顺手修掉 `tests/pages/report.spec.ts` 头部旧注释。⑤**D4/D5 循环侧小改**：tokens.scss 顶部注释 + 页面计划 §4 冲突表更新。
- 2026-09-16 09:38（cron 轮 `aap-tdd-run-20260916-0930`）· **队列 8 第 1 页：序号 3 载体页补「设计期望值 checks」维度（160 条 · 偏差 15→0）+ 修 4 类设计偏差**：
  ①**改名**：本轮**未执行**——队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**TDD 红→绿**（本轮主交付）：`__measure.html` 从「只在快照里报文案/溢出」升级为 **160 条设计期望值 checks**（want 全部取 `page-3 design.tree.json` + `node-probe.py` + 新增 `probe-effects.py` 读到的 effects 声明）。
     红基线 **checkFailCount 15/160**（`evidence/red-序号3-checks-设计期望值偏差.txt`，两轮一致）→ 修后 **0/160**（`green-序号3-checks-设计期望值.txt`），两轮独立测量全等 `47/47`（`review-compare --tag 3-checks`）。
  ③**修掉的 4 类偏差**（`src/pages/credentials/index.vue`）：顶部栏 1px 分隔由 `border-bottom` 改为设计声明的 `drop_shadow(0,1,0,#F1F5F9)`（border 把栏高撑成 **69**，设计 **68**；连带整页 docScrollHeight 944→943、卡片 top 227→226）；
     顶部栏按设计 `3ad1d267` 加 `cred__topbar-left` 组（返回按钮 + 标题块 横排 gap 12；修前标题块被 `space-between` 撑到距返回按钮 **99px**）；
     8 处字重按设计 fontFamily 对齐（Bold→700 ×3 · SemiBold→600 ×3 · Medium→500 ×2）；底部 TabBar 四项按设计「各 76 宽 + space_between」（修前 `flex:1` = **100** 宽）。
  ④**同轮修正 3 条探针口径**（经核对属探针自身错误、非页面缺陷，已在探针里写明）：chip 文案设计用 flex `gap` 无空格 → 分开断言 label/count；卡在 `padding` 容器内 → 左右边 20/410；
     `0.8px` 描边的 computed 是 used value（Chrome 取整 1px）→ 新增 `declared(sel, prop)` 判样式表声明值；另修 `norm()` 的 alpha 感知（alpha=1 的 shadow 颜色 Chrome 序列化成 `rgb()`）。
  ⑤**质量门**（修后）：`npm test` **1168/1168 ×2**（`green-序号3-checks-全量轮{1,2}.txt`）· `type-check` exit 0 · `build:mp-weixin` DONE（产物 `pages/credentials/index.{js,json,wxml,wxss}`，
     wxml 含 `cred__topbar-left`、wxss 含 `font-weight 500/600/700` 与 `.tabbar__item{width:76px}`）· `build:h5` DONE · 台账路由核对 `review-artifacts.py`：22/22 三件套齐备且注册。
  ⑥**证据**：430 宽截图 `logs/screenshots/20260916-0938-序号3-凭证列表-checks轮-h5-430宽.png`（另存一份到 `.agents/state/evidence/` 随本提交入库，因 `logs/` 被 ignore）；
     与旧留证（`measure-序号3-无滚动条430.json`）差异**全部**为「垂直 1px 平移 + 新增探针维度」，`overflowingCount 0` · `docScrollWidth 430` 不变。
  ⑦**下轮开工第一件事**：队列 8 的 **序号 4**（= page-4-2「提交接入凭证」→ `/pages/credential-submit/index`，载体页 = `__measure-submit.html`（旧的、无 iframe 版式，需先补成 430 宽 iframe 体例）、mock 目录 = `api`）；其后 **4-v1**（page-24「接入凭证-表单」→ `/pages/credential-submit/form`，载体页 = `__measure-form.html`）。对照表见 `python .agents/state/survey-harness-routes.py`。

- 2026-09-16 09:55（cron 轮 `aap-tdd-run-20260916-0945`）· **队列 8 第 2 页：序号 4 载体页补「设计期望值 checks」维度（212 条 · 偏差 45→0）+ 卡片边界做到与设计 PNG 像素级一致**：
  ①**改名**：未执行 —— 队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**设计帧重抓（人工指令 C）**：整包 22 帧先全 FAIL（`请先在浏览器中打开文件`）→ `cmd /c start ""` 拉起编辑器后重抓 page-4-2，
     `design.json` **sha256 逐字节相同** `29757a6f…` → 画布当前状态 = 实现所依据的版本，无漂移。
  ③**TDD 红→绿（本轮主交付）**：`__measure-submit.html` 从 175 行的旧体例重写为 430 宽 iframe + **212 条 checks**；
     红基线 **checkFailCount 45/206**（两轮完全一致，转录 `evidence/red-序号4-checks-设计期望值偏差.txt`）→ 修后 **0/212**（`green-序号4-checks-设计期望值.txt`），
     两轮独立测量 **33/33 字段全等**。
  ④**期望值口径升级**：声明值（design.tree.json + `node-probe.py` + 新增 `dump-node-fields.py` 全字段 dump）+ fit_content 行的**真实高度**（设计 PNG 色带实测：
     新增 `png-rows.py`（可打印 1 行长带）/`png-profile.py`（行剖面判文字行数）/`png-xruns.py`（行内 x 区间判换行））。**关键设计模型**：fit_content 行高 = 图标字形行框 = fontSize×1.5。
  ⑤**修掉 7 类偏差**（`src/pages/credential-submit/index.vue`）：顶部栏高 84→**96**（返回图标盒 24×24→26×36 = 24px 行框 36）；
     卡高 126/169/132/343→**133/172/137/354**（= 设计 PNG 卡边界 108/241·253/425·437/574·586/940，逐项相同；行框 18/16/21、安全提示盒 56）；
     卡片描边 `border`→`box-shadow: 0 0 0 1px`（设计 stroke 为 Figma center 不占布局 → 内容宽 356→**358**，设计 358；
     连带 inputBox/vendor/已配置 chip 右边 393→394）；图标占位盒按设计声明（26/20/16/14/22 宽 + 字号×1.5 行框，形状移入 `::before`，D5 仍为 CSS 占位）；
     提示文本左移 6→**4**；「已配置」字重 600→**500**（设计 Medium）；编辑图标盒 24×24→20×27。
  ⑥**像素对账（实现截图 vs 设计 PNG，同列 x=30 逐带）**：0..95/96..106/109..239/242..251/254..423/426..435/438..572/575..584/587..938 **逐带相同**；
     唯一有意偏离 = 操作条 fixed（设计在文档流末尾 956..1040），栏高 84 与 `barPinned` 一致、`atBottom.lastCardFullyAboveBar true`。
  ⑦**质量门**：`npm test` **1168/1168 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（产物含 `box-shadow:0 0 0 1px`/`line-height:18px`/`26x36`/`16x21`）· `build:h5` DONE · `review-artifacts.py` 22/22 路由三件套齐备。
  ⑧**与上一轮留证对比**：公共字段 14 全等、53 处差异全部可解释（本轮的 7 类修复 + 探针字段集升级 + 脱敏值口径）→ `evidence/cmp-序号4-上一轮vs本轮.txt`；报告 `evidence/review-序号4-checks-报告.md`。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 4-v1**（page-24「接入凭证-表单」→ `/pages/credential-submit/form`，载体页 `__measure-form.html` 需先补成 430 宽 iframe 体例）。

- 2026-09-16 10:20（cron 轮 `aap-tdd-run-20260916-1005`）· **队列 8 第 3 页：序号 4-v1 载体页补「设计期望值 checks」维度（249 条 · 偏差 78→0）+ 整页高度对齐设计帧 1137**：
  ①**改名**：未执行 —— 队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 page-24 → `design.json` sha256 **逐字节相同**（`bd249858…`）→ 画布当前状态 = 实现所依据的版本，无漂移。
  ③**TDD 红→绿（本轮主交付）**：`__measure-form.html` 从 169 行旧体例重写为 430 宽 iframe + **249 条 checks**；
     红基线用 `git stash` 复现修复前代码、同一份探针跑：**phase1 5/6 · phase2 78/249**（`evidence/red-序号4v1-checks-设计期望值偏差.txt`）→ 修后 **0 / 0**，
     两轮独立测量 33/33 字段全等、不一致 0；`git stash pop` + 重建后再跑一轮（`…-final-run{1,2}`）仍 0 且与首轮逐字段相同 → 复位干净。
  ④**期望值口径**：声明值（`design.tree.json` + `dump-node-fields.py` 全字段）+ fit_content 行真实行框（设计 PNG 色带）。
     本轮定标：**文本行框 ≈ 字号度量行框**（18→24 · 14→20 · 13→20 · 12→18 · 11→16）、**图标字形行框 = 字号×1.5**；PNG 命令写进载体页头注释可复现。
  ⑤**修掉 9 类偏差**（列表见台账序号 4-v1 行 / 报告 §4）：顶部栏 68→**74**、7 个图标盒按设计图层（形状入 `::before`）、13 处字重、文本行高、
     中心描边 0.8 由 border 改 box-shadow（内容宽 356→358）、上传区 dashed→**实线**、备注框 52→**56**、文件行 48→**54**、删除盒 20×20→**20×27**。
     连带卡高 370/93/259/111 → **388/98/274/118**、卡 top 84/470/580/855 → **90/494/608/898**、整页 1079 → **1137**。
  ⑥**像素对账**：实现截图 vs 设计 PNG 在 x=30 / x=100 两列**逐带相同**（`cmp-序号4v1-设计PNGvs实现截图-色带.txt`）。
  ⑦**交互相有牙齿**：guard 场景（chip 切换 + 空表单提交）两轮 serve 实收 **0 行** /api 请求；补必填后真实 `POST /provider/qualifications`（body 落 `requests-序号4v1-run1.txt`）→ 跳 `detecting?jobId=j1`。
     mock 缺口先红后绿：`api/v1/provider/qualifications/post` 缺失时 serve.py 对未定义 POST 会回 **200 `{"id":"c1"}`（静默假成功）** → 补 fixture + `check-mock-fixtures.py` 新增该条（FAIL 1→0）。
  ⑧**质量门**：`npm test` **1168/1168 ×2** · `type-check` exit 0 · `build:mp-weixin` exit 0（wxss 含本轮设计值）· `build:h5` DONE · `review-artifacts.py` 22/22。
  ⑨**探针自纠 3 处**（写进 §5）：`declared()` 不认 `[data-testid]`、Chrome 对 box-shadow 声明值的序列化形如 `rgb(..) 0px 0px 0px .8px`、
     **uni-app H5 的 placeholder 是 `.uni-input-placeholder` 文本节点而非 attribute**；另 chip 文字宽度改 ±3 容差断言。
  ⑩**下轮开工第一件事**：队列 8 的 **序号 5**（page-5-2「检测进行中」→ `/pages/detecting/index`，载体页 `__measure-detecting.html`，mock 目录 `api`）。

- 2026-09-16 10:42（cron 轮 `aap-tdd-run-20260916-1025`）· **队列 8 第 4 页：序号 5 载体页补「设计期望值 checks」维度（237 条 · 偏差 95→0）+ 9 类设计偏差修复 + 整页对齐设计帧 934**：
  ①**改名**：本轮开工按 prompt 试了一次 `git mv aap-client hioas-aap-client` → 仍 `Permission denied`（用户 `npm run dev:h5` 持句柄）→ 记一行顺延，**未杀用户进程**；决策 D6 仍为「勿再重试」，下轮按人类决策处理。
  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器（否则整包 `请先在浏览器中打开文件`），重抓 page-5-2 → `design.json` sha256 `4ed8ad58…` **逐字节相同**（`cmp` 报 BYTE-IDENTICAL）→ 画布当前状态 = 实现所依据版本，**无漂移**。
  ③**期望值口径**：声明值（`design.json` / `node-probe.py` / `dump-node-fields.py`）+ 设计 PNG 色带与墨迹实测（`png-rows.py` / `png-xruns.py` / `png-profile.py`，命令写进载体页头注释可复现）。
     本页新定标：**fit_content 文本行框 = 设计显式 height**（13→18 · 12→18 · 11→16 · 15→22）· 顶部栏内容高 = 图标字形行框 36（24×1.5）· 提示卡文案在卡内垂直居中（ink 784..810）。
  ④**TDD 红→绿（本轮主交付）**：`__measure-detecting.html` 由 129 行旧体例重写为 430 宽 iframe + **237 条 checks**；
     红基线（`git stash push -- aap-client/src/pages/detecting/index.vue` 复现修复前代码、同一份探针两轮）**phase1/phase2 各 95/237** · docH 900 → 绿 **0/237** · docH **934**（= 设计帧高）；
     两轮独立测量 **32/32 字段全等**（`cmp-measure-runs.py`，phase1 + phase2 各一次，红基线两轮同样全等）。
  ⑤**修掉 9 类偏差**（详见台账序号 5 行 / `review-序号5-checks-报告.md` §4）：顶部栏 84→96 · 卡1 184→196 · 卡2 416→434 · 提示卡 68→72 · 成本块 52→58 · 元信息行 14→18 ·
     描边 `border`→`box-shadow 0 0 0 1px` · 卡1 补设计 `effects` 投影 · 7 个图标盒按设计图层尺寸（形状移入 `::before`）。
  ⑥**像素对账**：新增 `cmp-bands-5-design-vs-impl.py`（±1 容差 + 自动判命中 + 文案 ink 行对比）→ x=62 列 41 个粗边界 **36 命中**，全部关键结构行命中；
     未命中 22 行逐条判读 = 「卡1 投影渐变台阶（Figma vs Chrome 衰减步长）」+「H5 回退字体字形墨迹边界」，**非页面缺陷**；提示卡文案 ink 修后与设计逐行相同（第二行 +1）。
  ⑦**交互相有牙齿**：`?scenario=interaction` 点「查看历史检测报告」→ client-only toast「历史检测报告可在凭证列表中查看」· `hashUnchanged true` · 行数仍 8 ·
     serve 实收 **10 行全为成对 `GET /api/v1/detection-jobs/j1` + `/results`**（5s 轮询 5 次）、**零写请求**。
  ⑧**质量门**：`npm test` **1168/1168 ×2** · `type-check` exit 0 · `build:mp-weixin` DONE（`pages/detecting/index.{js,json,wxml,wxss}` 齐备）· `build:h5` DONE ·
     截图 `logs/screenshots/20260916-1042-序号5-检测进行中-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）。
  ⑨**探针自纠 2 处口径**（写进 §5.2）：`norm()` 增加「数值直通」（number 与 `'32px'` 不可比 → 出现过 got 32 / want "32" 的假失败）；`tip.textLines` 改读 computed `height`。
  ⑩**下轮开工第一件事**：队列 8 的 **序号 6**（`page-6`「大模型检测报告 · 多维度专业版」→ `/pages/report/index`，载体页 `__measure-report.html`，mock 目录 `api`）。
  ⑪**流程自纠**：本轮开工时 §0 租约是 `free`，但**没有即时写成本轮 id 再开工**（缺了一步），收尾时它仍是 `free` —— 本 job 每 5 分钟触发而本轮做了约 20 分钟，理论上存在并发窗口；
     下轮起恢复「开工先写租约、提交后改回 free」的动作（若人类把周期调长可忽略）。

- 2026-09-16 11:16（cron 轮 `aap-tdd-run-20260916-1050`）· **队列 8 第 5 页：序号 6「大模型检测报告 · 多维度专业版」载体页补「设计期望值 checks」维度（221 条 · 偏差 45→0）+ 11 类设计偏差修复 + 整页对齐设计帧 5342**：
  ①**改名**：未执行 —— 队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**设计帧重抓（人工指令 C）**：`python E:/agent/aap-tools/recapture-all.py` → **22 帧全 SAME**，其中 `page-6` design.json 633742→633742 **逐字节相同** → 画布当前状态 = 实现所依据版本，**无漂移**。
  ③**TDD 红→绿（本轮主交付）**：`__measure-report.html` 由 191 行旧体例重写为 430 宽 iframe + **221 条 checks**；
     红基线（`git stash push -- aap-client/src/pages/report/index.vue` 复现修复前代码、同一份探针两轮）**45/219**（`evidence/red-序号6-checks-设计期望值偏差.txt`）→ 绿 **0/221**（`green-序号6-checks-设计期望值.txt`），
     两轮独立测量 **24/24 字段全等**（`cmp-measure-runs.py`），`overflowingCount 0` · `missingTexts None` · `docScrollWidth 430`。
     `docScrollHeight` **4886 → 5343**（设计帧高 5342）；`cardTops [105,533,896,1425,4402,4824,5122]` vs 设计 `[105,533,896,1425,4400,4822,5120]`（前 4 张完全对齐）。
  ④**期望值口径**：声明值（`.calicat/raw/pages/page-6/design.tree.json` + 新增 `tree-view.py`）+ 设计 PNG（430×5342）色带/行带实测（新增 `png-cardmap.py`/`png-textbands.py`）。
     本页定标：**图标字形行框 = 字号×1.5**（22→33 顶部栏 · 16→24 封面图标 · 18→27 措辞盒图标）；**标题行框**：15px Bold→20 · 40px Black→44 · 19px ExtraBold 值行→24 · 13px Bold 组标题→18 · 10.5px 说明→16；
     **明细卡结构模型**：组高 = 16 + 18(标题行) + 14(标题→列表) + n×29 + (n−1)×14，分组之间 16，权重说明盒前 16，指纹提示在 D 组标题行之后（两侧各 14）。
  ⑤**修掉 11 类偏差**（清单见台账序号 6 行 / `review-序号6-checks-报告.md` §3）：顶部栏 84→93 · 封面卡补 `drop_shadow(0,6,20,rgba(15,23,42,.06))` · 5 张卡+底栏描边 `border`→`box-shadow: 0 0 0 .8px #eef2f7` ·
     封面卡标题 15px/600 → **12px/500/#64748B**（design 625f2248）· 综合分 600/1.2 → **900/44px** · 通过标签 #ECFDF5/400 → **#F0FDF4/700**（新增 token `$color-success-weak-2`）·
     措辞盒图标盒 14×14 → **20×27** · 补 1px 分隔线 + 信息清单 margin 16 · 关键指标卡补 5×14 色条 + 值行高 28（**子卡 85 / 行距 95 / 卡高 351**）·
     维度「分」列 13→**32 宽右对齐**、均分行高 16 · 明细条目间隔 8→**14**、组标题行 18、分组间隔 16、指纹提示/权重说明盒行框 16、5 处字重（Bold 700 / Medium 500）。
  ⑥**像素对账**：新增 `cmp-bands-6-design-vs-impl.py`（±容差结构带逐条匹配 + 分区间位移概况）→ ±10：内容列 **142/142 命中**、条形列 **115/121**（6 条未命中经判读为设计 PNG 自身 AA/阴影带）；
     位移分区：y0..1000 中位 0 · y1425..4400（明细卡内）中位 +5（min −8 max +9）· y4400.. 中位 +2。**残留已定位**：明细卡内部条目整体 +8、到 G 组收敛 +2，系 H5 回退字体在明细说明(11px)/指纹提示(10.5px)两处换行与墨迹差异（同族于其它页记录），非页面缺陷。
  ⑦**交互相有牙齿**：`?scenario=actions` 两轮 → 点「导出 PDF」serve 实收 `GET /reports/DR-1/export 200` 且 `hashUnchangedAfterExport true`（toast「导出链接已生成，请在浏览器中打开」）、点「填写报价」→ `#/pages/quote-models/index`（用户拍板口径）；
     无场景轮实收 **1 行**（仅 `GET /reports/DR-1`）—— 无多余请求。
  ⑧**质量门**：`npm test` **1168/1168 · 72 files 连跑两轮**（11:11 / 11:15）· `type-check` exit 0 · `build:mp-weixin` DONE（`pages/report/index.{js,json,wxml,wxss}` 四件套，wxss 含 `font-weight:800/900`、`line-height:16px/24px`、`box-shadow:0 0 0 .8px`）· `build:h5` DONE ·
     整页 430 宽截图 `logs/screenshots/20260916-序06-检测报告-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）。
  ⑨**本轮新增工具**（写进 §5.3）：`tree-view.py` / `png-cardmap.py` / `png-textbands.py` / `png-sample.py` / `cmp-bands-6-design-vs-impl.py` / `shot-6.sh`；
     并修掉探针自身 3 处口径（`chk()` 数值直通、`sel@@N` 取第 N 个匹配、`rectField` 由 key 末段决定字段）。
  ⑩**下轮开工第一件事**：队列 8 的 **序号 7**（`page-7-2`「检测未通过报告」→ `/pages/report-failed/index`，载体页 `__measure-report-failed.html`，mock 目录 `api`）。

   - ✅ **序号 7 已完成 2026-09-16 11:3x**：`__measure-report-failed.html` 由 273 行旧体例重写为 430 宽 iframe + **196 条 checks**
     （want = page-7-2 `design.tree.json` 声明值 + `dump-node-fields.py` 全字段 + 设计 PNG 430×1110 像素实测）。
     红基线（`git stash push` 复现修复前代码、同一份探针两轮）**51/196**（`evidence/red-序号7-checks-设计期望值偏差.txt`）→ 绿 **0/196**
     （`green-序号7-checks-设计期望值.txt`），两轮独立测量 **30/30 字段全等**；`git stash pop` 复位后复跑仍 0 且与复位前逐字段相同。
     整页 `docScrollHeight` **1063 → 1111**（设计帧 1110 = Figma 小数坐标链取整后 +1）。
     修掉 13 类偏差：顶部栏 89→**96**（图标盒 26×36）· 封面卡补 `drop_shadow(0,6,20,…)` · 三张卡 + 次按钮描边 `border`→`box-shadow 0 0 0 1px`
     （内容宽 356→**358**）· 封面标题行 14.4→**18** · 综合分 46→**57** · 「综合评分/满分 100」两行 **18+16** · 分项行高 14→**18**、行距 26→**30** ·
     分值文字色改用设计**第二套色板**（新增 `scoreTextColor()` + `FailedDimRow.textColor`：#334155/#D97706/#B91C1C）· 结论胶囊 76→**83** ·
     否决条/结论措辞/免责图标盒 → **20×27 / 20×27 / 22×30**（形状入 `::before`）· 「导出 PDF」删掉设计里没有的图标 · D2 详情卡标题行 20、卡高 166。
     交互相：`?scenario=actions` 两轮 → 导出 PDF 实收 `GET /reports/DR-7/export 200` + hash 不变；重新提交检测 → `POST /detection-jobs body={credential_id:c1}`
     → 跳 `detecting?jobId=j7`；纯测量轮两轮各只 **1 行**请求（`GET /reports/DR-7`）。
     像素对账 `cmp-bands-6`：内容列命中 34/38 · 条填列 19/19 · 位移中位 +1；4 条未命中 = 投影 AA 带（y376/379/385）+ H5 回退字体换行差 1 字（y707）。
     质量门：`npm test` **1170/1170 ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · `check-mock-fixtures` FAIL 0 · `review-artifacts` 22/22。

- 2026-09-16 11:20（cron 轮 `aap-tdd-run-20260916-1120`）· **队列 8 第 6 页：序号 7「检测未通过报告」载体页补「设计期望值 checks」维度（196 条 · 偏差 51→0）+ 13 类设计偏差修复 + 整页对齐设计帧 1110**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-7-2` → `design.json` sha256 `f2780416…` **逐字节相同**（无漂移）。
  ②**TDD 红→绿（本轮主交付）**：载体页重写为 430 宽 iframe + 196 条 checks；红基线（`git stash` 复现修复前代码、同一份探针两轮）**51/196**、`docH 1063` → 绿 **0/196**、`docH 1111`；
     两轮独立测量 30/30 全等；复位后复跑同值（stash 循环干净）。
  ③**修掉 13 类偏差**（清单见台账序号 7 行 / `review-序号7-checks-报告.md` §4）：顶部栏 89→96 · 封面卡补投影 · 描边 `border`→`box-shadow`（内容宽 356→358）·
     封面标题行 18 · 综合分 57 · 评分说明 18+16 · 分项行高 18 行距 30 · **分值文字色改设计第二套色板**（新增 `scoreTextColor`，先红后绿 2 条新用例）·
     结论胶囊 83 · 图标盒按设计图层 20×27/20×27/22×30 · 「导出 PDF」删掉设计里没有的图标 · D2 详情卡 166。
  ④**本页定标**：文本行框 = fontSize×1.5（显式 height 优先）；图标字形行框 = fontSize×1.5；Figma center 描边 → `box-shadow: 0 0 0 1px`；分项行 18+12=30。
  ⑤**新增工具** `png-rowclass.py`（逐行判卡片/间隙，不受双份投影染色影响，本页靠它定出卡1 108..362 / 卡2 374..756 等）。
  ⑥**探针自纠 3 处**（写进 §5.4）：boxShadow 不能用 normColor（会把整串压成只剩颜色）· `rectField` 不认 `left` · 数组比对要 `chkList` 容差。
  ⑦**质量门**：`npm test` **1170/1170 · 72 files ×2** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 `box-shadow:0 0 0 1px #eef2f7`、`line-height:57px`）· `build:h5` DONE ·
     `check-mock-fixtures --mock api` FAIL 0 · `review-artifacts` 22/22 · 截图 `logs/screenshots/20260916-序07-检测未通过报告-checks轮-h5-430宽.png`。
  ⑧**下轮开工第一件事**：队列 8 的 **序号 8**（`page-8-2`「报价单列表」→ `/pages/quotes/index`，载体页 `__measure-quotes.html`，mock 目录 `api`）。

- 2026-09-16 11:56（cron 轮 `aap-tdd-run-20260916-1141`）· **队列 8 第 7 页：序号 8「报价单列表」载体页补「设计期望值 checks」维度（138 条 · 偏差 27→0）+ 11 类设计偏差修复 + 整页对齐设计帧 1206（像素对账 42/42 命中）**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-8-2`（layer_id `56142177-…`）→ **唯一差异 = 「新建按钮」`width 97→100`**
     （自动布局按子节点重算 12+18+4+54+12 = 100，与子节点自洽；与 08:55 基线一致）→ 按当前帧实现为 100 宽；其余节点逐字节相同。
  ②**TDD 红→绿（本轮主交付）**：`__measure-quotes.html` 由 249 行旧体例重写为 430 宽 iframe + **138 条 checks**
     （want = `design.tree.json` 声明值 + 新增 `text-fields.py` 全字段 + 设计 PNG 430×1206 色带/墨迹实测）；
     红基线（`git stash` 复现修复前源码、同一份探针两轮）**27/138**、`docH 1198` → 绿 **0/138**、`docH 1206`；
     两轮独立测量 **30/30 字段全等**；`git stash pop` 后重建复跑同值。
  ③**修掉 11 类偏差**（清单见台账序号 8 行 / `review-序号8-checks-报告.md` §4）：顶部标题 600→**700** + 行框 30 ·
     「新建报价」宽 88→**100** + 图标盒 12×12→**18×24** + 文案 500/行框 16 · 卡片描边 `border`→`box-shadow 0 0 0 1px`
     （内容宽 356→358、操作链接左界 37→36、卡高 177→**178**）· 标题行框 22.5 · 胶囊文字 16 · 单号标签 19.5 · 元信息行框 16 ·
     **元信息行由单文本节点改为设计里的 5 节点（3 段 + 2 个分隔点、节点间 8px，分隔点用设计另一套浅灰 #CBD5E1）** ·
     操作图标盒 16×24 · TabBar 图标盒 22×33 · 列表底留白 112 · 待签署胶囊底色 `#FFFBEB`→**`#FFFCEB`**（先红后绿 1 条单测）。
  ④**像素对账**：`cmp-序号8-设计PNGvs实现截图-色带.txt` → 内容列 **24/24** + 条列 **18/18 全命中**，**未命中合计 0**（首个 0 未命中页），位移中位 0/1（min −1 max +1）。
  ⑤**交互相有牙齿**：`?scenario=actions` 两轮 → 点「已驳回」chip 实收 `GET /quotes?page=1&pageSize=10&status=REJECTED`；
     点卡1「删除」→ 真实 `uni-modal` → 确认 → 实收 `DELETE /quotes/q1 200` → toast「已删除」→ 重拉列表；两轮请求行逐字节相同。
  ⑥**质量门**：`npm test` **1172/1172 · 72 files ×2** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 `box-shadow:0 0 0 1px #eef2f7`/`width:100px`/`font-weight:700`）·
     `build:h5` DONE · `check-mock-fixtures --mock api` FAIL 0 · `review-artifacts` 22/22 · 截图 `logs/screenshots/20260916-序08-报价单列表-checks轮-h5-430宽.png`。
  ⑦**下轮开工第一件事**：队列 8 的 **序号 9**（`page-9`「模型报价设置-列表」→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`，mock 目录 `api`）。

## 5. 关键命令（照抄可用）

- 项目根：`E:\workspaces\hioas\hioas-aap-001`（远端 https://github.com/hioas/hioas-aap-001）
- 客户端：`cd aap-client`（改名后为 `hioas-aap-client`）；`npm test`（vitest run）；`npm run build:mp-weixin`；`npm run build:h5`；`npm run dev:h5`；`npm run type-check`
- **目录对齐**：仓库根 `git mv aap-client hioas-aap-client`（`Permission denied` = 用户进程持有句柄 → 顺延，别 kill）
- 台账统计：`python .agents/state/gen-ledger.py`
- **mock fixture 体检**：`python .agents/state/check-mock-fixtures.py [--mock api]`（自起 serve.py + 直连校验 + 反向体检；红=有路径取不到数）
- **造 before/after mock 变体**：`python .agents/state/make-mock-variant.py <src> <dst> [relpath ...]` / `--clean <dst>`（当轮用完即 clean，别提交）
- **本轮新增探针**：`__measure-model-pricing-q9.html`（q9 回落：序号 9 保存并继续的落点）· `__diag-report-overflow.html`（溢出元素祖先链定位）
- **生成复核报告**：`bash .agents/state/gen-review-report.sh <轮次id> <输出文件名>`
- 设计树探针：`python .agents/state/node-probe.py <page-id>`（产出 `.agents/state/<page-id>-nodes.txt`，含几何/填充/内边距/文字）
- **节点字段全量 dump**：`python .agents/state/dump-node-fields.py <page-id> <名字或文案片段>`（打印该节点在 design.json 里的**全部字段**：lineHeight / content / stroke / padding / gap / textAlignVertical …，判「声明值」的硬依据）
- 设计截图像素量尺：`python .agents/state/png-bands.py <png> v|h <idx> [from] [to]`（同色色带 = 盒子边界；定卡高/间距/栏高最硬的依据）
  - `python .agents/state/png-rows.py <png> v <x> <from> <to> [minLen]` —— 同族但**可打印长度 1 的色带**（1px 描边/子像素边界就藏在这些 1 行带里）
  - `python .agents/state/png-profile.py <png> <x0> <y0> <x1> <y1> [minInk]` —— 区块**行剖面**（每行与主色不同的像素数 → 判文字行数/图标墨迹范围）
  - `python .agents/state/png-xruns.py <png> <y> <x0> <x1>` —— 某一行「非主色」像素的 x 区间（判换行/文本覆盖宽度）
- **设计帧重抓（复核前必做）**：先确认 Calicat 编辑器开在浏览器里（`cmd /c start "" https://www.calicat.cn/design/2095515676955668480`，否则整包重抓 22 帧全 FAIL「请先在浏览器中打开文件」），再
  `python C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/calicat_source.py page --url https://www.calicat.cn/design/2095515676955668480 --layer-id <layer_id> --page-id <id> --out "$LOCALAPPDATA/Temp/aap-live"` + `sha256sum` 与留证逐字节比对；整包用 `python E:/agent/aap-tools/recapture-all.py`（仓库外）。
- 一次实测的关键字段速览：`python .agents/state/show-snapshot.py <run.json>`；页面元信息：`python .agents/state/show-page-meta.py <page-id>`（layer_id/name/截图 URL/抓取文件）
- 430 宽截图：`bash .agents/state/shot-430.sh <输出.png> [载体页=__measure.html] [查询串=?shot=1]`
  —— ⚠️ **输出路径用 ASCII**（Chrome 的 `--screenshot` 收到含中文的 MSYS 相对路径会写不出来，静默失败）：先写到 `$LOCALAPPDATA/Temp/x.png` 再 `cp` 成中文名。
- 像素对账：`python .agents/state/text-rows.py`（同一脚本跑设计与实现，逐行文本带对比）
- 台账取件：`python .agents/state/list-pending.py`（按序号列出未完成页面）
- 两次独立测量一致性：`python .agents/state/cmp-measure-runs.py <runA.json> <runB.json> <phase>`（扁平单段文件自动兼容，**但仍必须传第 3 个参数，传 `flat`**）
- **逐页复核一条龙**（本轮新增）：
  - 一页跑两轮 430 宽实测：`bash .agents/state/review-measure.sh <序号> <__measure-*.html> <mock目录> <端口>`
    → 证据 `.agents/state/evidence/review-序号<序号>-run{1,2}.json`
  - 两次独立测量 + 与建页留证对比（紧凑输出）：`python .agents/state/review-compare.py --tag <序号> [--old .agents/state/evidence/measure-序号<序号>-*.json]`
  - 定位字段差异：`python .agents/state/show-measure-fields.py <a.json> <b.json> <phase> <字段...>`
  - 台账产物核对：`python .agents/state/review-artifacts.py`（按台账路由核 mp-weixin 三件套 + app.json 注册）
  - 生成报告：`bash .agents/state/gen-review-report.sh` → `.agents/state/evidence/review-measure-<日期>.md`
  - 台账追加笔记：`python .agents/state/append-ledger-note.py <序号> --case <文本> --note <文本>`（**写完跑 `normalize-ledger-eol.py` 把行尾改回 LF**，否则整文件在 git 里显示改动）
  - mock 目录与载体页对照：`api`=3/4/4-v1/5/6/7/8/9 · `api-10-2`=10 · `api-10-1-2`=10.1 · `api-11`=11 · `api-12`=12 ·
    `api-12-v1/v2/v3`=12-v1/v2/v3 · `api-15`=15 · `api-20`=20 · `api-21`=21 · `api-22`=22 · `api-23`=23
- 静态取证服务器（本循环自用，用完即关）：`python .agents/state/h5-measure/serve.py <h5 产物目录> .agents/state/h5-measure/api <端口>`
- **D3 测量面（本轮新增）**：缺字段变体的载体页场景 `?scenario=nomedia` + mock 变体重建/清理 `python .agents/state/make-nomedia-mock.py [--clean]`（= api 目录去掉 summary 的 audio/video 字段）；看某轮实测的 checkFails `python .agents/state/show-measure-fails.py <json> [phase] [字段...]`。
- ⚠️ `python .agents/state/cmp-measure-runs.py <runA> <runB> <phase>` —— **第 3 个参数（phase）必填**，省略会 IndexError: list index out of range（本轮踩到）。
- ⚠️ 载体页解析 `conic-gradient` 时注意：Chrome 会把每段序列化成「color p%, color p%」两两配对、颜色写成 `rgb()`，`color from% to%` 式正则解析不到任何段（本轮踩到，已修 `__measure-workbench.html` 的 ringStops）。
- Calicat CLI：`calicat status` / `calicat tools-call --name get_screenshots --args '{...}'`；
  技能脚本目录 `C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/`
- gh：`E:\tools\bin\gh.exe`（已登录 geeker-lait）
- 平台坑：中文 Windows `netstat` 是 GBK；`taskkill` 要写 `/PID`（`//PID` 报「无效参数」）；
  bash 把中文塞 JSON body 会变 GBK（要发中文请求体用 Node/Python 的 utf-8）；
  `npm run build:h5` 会清空 `dist/build/h5` → `__measure*.html` 载体页每次 build 后要重新拷贝。

### 5.1 本轮（10:20 轮）新增的工具与口径

- **多相载体页看板**：`python .agents/state/show-phases.py <run.json> [out.txt] [--fails-only]`
  —— 打印 acc（phase1..N）每相的 checkCount / checkFailCount / docH / 失败清单（`show-checks.py` 只认扁平单段文件）。
- **红基线复现（不用手抄）**：`git stash push -- aap-client/src/pages/credential-submit/form.vue` → `npm run build:h5` → 跑 `review-measure.sh <tag>-red` → `show-phases.py … red-…txt` → `git stash pop` → 再 build:h5 复位（复位后补跑一轮 `-final` 证清白）。
- **单发排查载体页**：`bash .agents/state/dbg-measure.sh <载体页> <mock目录> <端口>`（带 `--enable-logging=stderr` 抓 console 报错 + 打印 pre 内容；本轮靠它定位 `dim is not defined`）。
- **内联脚本语法体检**：`python .agents/state/extract-inline-js.py <html> <out.js>` + `node --check <out.js>`。
- **拍整页截图**：`bash .agents/state/shot-4v1.sh [文件名]`（模板：ASCII 临时名 → `cp` 到中文名；`--window-size=440,1240` 才能装下 1200 高 iframe 载体页；载体页需 `?shot=1` 且**截图模式停在设计帧状态**不跳页）。
- **台账/清单查看**：`python .agents/state/show-inv-page.py <page-id>`（inventory.json 里某页的 layer_id/抓取文件）。
- ⚠️ **iframe 取数高度要小于内容高**：页面 `min-height:100vh` → iframe 1200 高时 `docScrollHeight` 恒 = 1200，量不到整页高；取数用 900、截图用 1200（载体页里按 `SHOT_ONLY` 切换）。
- ⚠️ **uni-app H5 的 placeholder 不是 attribute**：`<uni-input>` 内部渲染 `.uni-input-placeholder` 文本节点 → 断言渲染文案（`texts('.input-box .input-box__placeholder')`），别读 `getAttribute('placeholder')`。
- ⚠️ **serve.py 对未定义的 POST/PUT/DELETE 会返回 200 `{"id":"c1"}`**（静默假成功，不是 404）→ 页面「提交成功」可能只是 mock 兜底；新增写接口的页面必须往 `check-mock-fixtures.py` 加一条并补 fixture。
- ⚠️ **Chrome 对 box-shadow 声明值的序列化**：`rule.style.boxShadow` 读出来是 `rgb(238, 242, 247) 0px 0px 0px 0.8px`（颜色在前、逗号后带空格）→ 用 `declaredNorm()` 归一化空白再比；`declared()` 只认**类名选择器**，传 `[data-testid=...]` 永远取不到。
- 口径（本轮定标，后续页面复用）：**fit_content 文本行框 ≈ 字号度量行框**（18→24 · 14→20 · 13→20 · 12→18 · 11→16）；
  **图标字形行框 = 字号×1.5**（24→36 · 22→33 · 20→30 · 18→27 · 14→21）；形状画 `::before`、盒子按设计图层尺寸。

### 5.2 本轮（10:25 轮）新增的工具与口径

- **像素对账（±1 容差、自动判命中）**：`python .agents/state/cmp-bands-5-design-vs-impl.py <设计PNG> <实现PNG> [out.txt]`
  —— 逐列取「粗色带边界」（长度 ≥2 的色带起点，滤掉 AA/渐变 1 行带），设计的每个边界在实现里 ±1 行内命中即算过；另打印文案 ink 行对比（提示卡 / 底栏）。
  设计 PNG 下载：`curl -o design5.png https://prototype-prod-1254106194.cos.ap-beijing.myqcloud.com/calicat/file/2099906439898591232/canvas/image/2099906439898591232.png`
- **红基线复现（第二例，模式固定）**：`git stash push -- aap-client/src/pages/detecting/index.vue` → `npm run build:h5` → `review-measure.sh <tag>-red …` → `show-phases.py` 存转录 → `git stash pop` → 再 `build:h5` 复位 → 跑正式两轮。
  （比 `git stash` 全量安全：只 stash 该页文件，探针/证据不被牵连。）
- **证据转录合成**：`python .agents/state/gen-5-checks-evidence.py`（红/绿两轮的 phase 概览 + 失败清单 + serve 实收请求行 → `red-序号5-checks-*.txt` / `green-序号5-checks-*.txt`；后续页面照抄改 tag）。
- ⚠️ **探针 `norm()` 必须让数值直通**：`dim()`/`rect` 给 number、computed style 给 `'32px'` 字符串 → 不直通时 `32 !== '32'` 报假失败（本轮踩到，已加 `if (typeof v === 'number') return v`）。
- ⚠️ **设计树里的固定宽高可能是陈旧值**：page-5-2 进度填充设计树写 `width 209`，设计 PNG 实际渲染 **208**（= 58% × 358）→ 固定尺寸也要用 PNG 复核一次再写进 checks。
- ⚠️ **行框优先取设计显式 `height`**（13→18 · 12→18 · 11→16 · 15→22），**没有**显式 height 才用 PNG 反推（元信息行 18 · 标题行 26 · 提示卡文案 16）。
- ⚠️ **Figma 的 center 描边与投影**：`stroke{align:center}` → `box-shadow: 0 0 0 1px`（`border` 会占布局）；`effects drop_shadow` → `box-shadow`。
  Chrome 与 Figma 的阴影衰减步长不同（±3px 内），像素对账会把渐变台阶行列为差异 —— 判读时看**关键结构行**是否命中，不要逐行追究阴影。
- ⚠️ **H5 回退字体的墨迹与设计字体不同**：同为 12px，设计字体在行框内的 ink 偏低约 4px（本页提示卡文案）→ 用 `align-self:center` 把 ink 对齐到设计位置。
  这类差异 checks 探针量不到（它只测盒子），**只能靠像素对账发现**。

### 5.3 本轮（10:50 轮 · 序号 6）新增的工具与口径

- **设计树紧凑视图**：`python .agents/state/tree-view.py <page-id> [--types frame|all] [--min-depth N] [--max-depth N] [--match 子串] [--text-max N]`
  —— 每行带 `id=<前 8 位>`、几何/内边距/圆角/fills/stroke/**effects**/layout/fontSize/fontFamily/文案；判「声明值」的第一入口
  （比 `node-probe.py` 多打印 stroke/effects/圆角与 id，`--match` 定位单个节点）。
- **PNG 区块图**：`python .agents/state/png-cardmap.py <png> --x 30 [--bg F8FAFC] [--minrun 2]`
  —— 按指定列输出「等于页面底色 / 不等于」的区段（判卡片上下边界）。⚠️ 卡片带 `drop_shadow` 时**卡片之间的 12px 间隙会被两张卡的阴影染色**，
  在 `--x` 选在卡片外缘时会与卡片连通成一段 → 判边界要挑「卡片内、避开文字」的列，或改用 `png-textbands.py`。
- **行墨迹带**：`python .agents/state/png-textbands.py <png> <x0> <y0> <x1> <y1> [--minink 3] [--gap 1]`
  —— 逐行统计「与**该行主色**不同的像素数」，≥minink 的连续行带 = 一条文案/一个条目（行距、行高、条目数的硬依据）。
  ⚠️ 整行同色（卡片间隙/页面底色）不会被记为 ink —— 这正是不受阴影干扰的原因；`png-bands.py` 判「同色带」、`png-textbands.py` 判「文字带」，两者互补。
- **逐点取样**：`python .agents/state/png-sample.py <png> --x 8 --step 250`（带 alpha；用于判断「颜色异常是页面还是导出图」）。
- ⚠️ **Chrome `--screenshot` 产出的是 RGB（colorType 2）PNG，设计导出是 RGBA** → PNG 读取器必须同时支持 3/4 通道；转换时必须保留「未转换的 RGB 行」给下一行做 Up/Paeth 反滤波（`png-cardmap.read_png` 已修）。
- **像素结构带对账**：`python .agents/state/cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> <out.txt> [容差=3]`
  —— 逐列取「ink 带起点」，设计每个起点在实现里 ±容差 内找同起点；另打分区间（y 0..1000 / 1000..1425 / 1425..4400 / 4400..）的位移 min/max/中位 → **一眼区分「整体平移」与「局部漂移」**。
- **整页 430 宽截图**：`bash .agents/state/shot-6.sh`（`--window-size=430,5400`；ASCII 临时名 → cp 成中文名，见 §5 的 Chrome 中文路径坑）。
- **载体页探针语法与陷阱**（本页踩到并修）：
  - 选择器取「第 N 个匹配」用 `sel@@N`（`.card@@1 .card__title-row` = 第 2 张卡的标题行）；**CSS 里 `.card#1` 非法**，探针的 `splitSel()` 会把非法的 `#N` 归一化成 `@@N`。
  - `chkR()` 比较哪个字段由 **key 末段**决定（`.h/.w/.x/.right/.top/.bottom`），否则 `got` 会变成整个 rect 对象而永远失败。
  - `chk()` 必须**数值直通**：computed 的 `fontWeight` 是字符串 `"700"`，want 写数字 `700` → 不归一化就报假失败。
  - `declared()`（读 CSSOM 声明值）只按**类名**匹配；`.card--cover` 这类覆盖规则会让同一元素有两条 `.card*` 规则 → **带覆盖的元素要判 computed 值**，只对 `0.8px` 这种「used 值被取整」的描边判声明值。
- **本页记录的设计模型（可直接复用于同族长页）**：
  - 图标字形行框 = `fontSize × 1.5`（22→33 · 16→24 · 18→27）。
  - 文本行框：40px Black→44 · 19px ExtraBold 值行→24 · 15px Bold 标题→20 · 13px Bold 组标题→18 · 12px→18 · 11px→16 · 10.5px→16。
  - `stroke{align:center,thickness:0.8}` → `box-shadow: 0 0 0 .8px <color>`；`effects.drop_shadow(0,6,20,c)` → `box-shadow: 0 6px 20px c`（`border` 会占布局、把内容宽挤掉 2px）。
  - 明细类长列表：行高 29（12px 标签 16 + 10px 副标 13）+ 行间隔 14；组标题行 18 + 组内 14；**分组之间 16**；组前提示盒/文末说明盒行框 16。
  - **同一页里同名类可以有不同字号/字重**（结论封面卡标题 12px/500 vs 其余卡 15px/700）→ 探针必须按「卡 + 类」分别断言，不能只断言第一个 `.card__title`。

### 5.4 本轮（11:20 轮 · 序号 7）新增的工具与口径

- **逐行判「卡片行 / 间隙行」**：`python .agents/state/png-rowclass.py <png> [--x0 16] [--x1 414] [--white FFFFFF] [--minfrac 0.7]`
  —— 按行统计区间内「等于卡片底色」的像素占比，≥minfrac 判卡片行。**这是判卡片上下边界的第一工具**：
  设计导出图上两张卡之间的间隙会被**两张卡各自的 drop_shadow 同时染色**，所以「等于页面底色」的旧判据会把卡+间隙+卡连成一段
  （本页 `png-cardmap --x 30` 就把卡1/卡2 连成 98..756 一整段）；`png-textbands.py` 则用于盒内文字带。三者互补：
  rowclass 判卡片边界 · textbands 判盒内文字/条目行 · png-rows 判单列色带。
- ⚠️ **探针 `css(sel,'boxShadow')` 不能走 `normColor()`**：normColor 只回 `rgba(...)` 片段，会把
  `rgba(15, 23, 42, 0.06) 0px 6px 20px 0px` 压成 `rgba(15, 23, 42, 0.06)` → **每条 box-shadow 检查都假失败**（本页踩到 5 条）。
  正解：`normShadow()` 只替换颜色片段、保留偏移/模糊/扩散。
- ⚠️ **`rectField()` 要认 `left`**：只认 `x` 时，key 写成 `xxx.left` 会返回**整个 rect 对象**并与数字比较 → 永久失败（本页踩到 6 条）。
- ⚠️ **数组类断言用 `chkList(key, got, want, tol)`**：设计帧是 Figma 小数坐标链（本页卡1 真值 254.5、整页 1110.5），
  落地取整后卡顶/卡高整体 +1；把数组 `join(',')` 精确比字符串会把取整差报成页面缺陷。
- **本页记录的设计模型**：`stroke{align:center,thickness:1}` → `box-shadow: 0 0 0 1px <color>`（`border` 会占布局，内容宽 356→358）·
  `effects.drop_shadow(0,6,20,rgba(15,23,42,.06))` → `box-shadow`（本页只有封面卡有投影，其余卡是描边 —— 探针要按卡分别断言）·
  文本行框 = `fontSize × 1.5`，但**显式 height 优先**（同一页里「综合评分」18 与「满分 100」16 不同，不能一刀切）·
  分项行：行高 18 + 间距 12 = 行距 30（首行前 16）；总览卡尾部说明盒 = 12 + 2×18 + 12 = 60。
- **一个页面的同一组数据可以有两套色板**：本页分项**条填色**（绿/琥珀/红）与**分值文字色**（#334155 / #D97706 / #B91C1C）
  在设计稿里是两组不同图层填充 → 探针必须分别断言，实现侧用 `dim.color` / `dim.textColor` 两个字段（阈值同一套 70/40）。

### 5.5 本轮（11:41 轮 · 序号 8）新增的工具与口径

- **文本叶子全字段 dump**：`python .agents/state/text-fields.py <page-id> [--grep <子串>]`
  —— 打印设计树里**所有文本叶子**的 `fontSize / fontFamily→字重 / fontFill（字色）/ 宽高 / 文案`；
  判「声明值」的第一入口（比 `tree-view.py` 更聚焦文本：字色取 `fontFill`，不是 `fills`）。
- **430 宽整页截图（固定底栏页）**：`bash .agents/state/shot-8.sh [文件名]`（窗口 430×**1206**，载体页 `?shot=1`）。
  ⚠️ **底部固定栏页面的取图口径**：载体页在 shot 模式必须把 iframe 高度设为**设计帧高**（本页 1206），
  否则固定底栏贴到更高的 iframe 底部 → 像素对账在 TabBar 带整体偏移（本轮首图偏移 35px，**不是页面缺陷**）。
- **红基线复现（第三例）**：`git stash push -- aap-client/src/pages/quotes/index.vue aap-client/src/utils/quotes-model.ts aap-client/tests/`
  → `npm run build:h5` → `review-measure.sh 8-checks-red …` → `show-phases.py` 转录 → `git stash pop` → 再 `build:h5` 跑正式两轮。
- **证据合成**：`python .agents/state/gen-8-checks-evidence.py`（红/绿转录 + 两轮一致性 + serve 实收请求行；后续页面照抄改 tag）。
- ⚠️ **设计里用「后续节点 `padding-left: 8`」分隔的文本组，不能实现成一个带空格的字符串**：
  空格在 H5 回退字体里宽 ~3.4px（设计 5 节点应 216 宽 → 单串实测 188），且**分隔点在设计里是另一套更浅的色板**
  （本页 `fd63dfdb/9cafcec1` = #CBD5E1，其余文本 #94A3B8）→ 必须按节点渲染（本页 `metaParts()` + 5 个 `<text>`）。
  同理 `innerText` 里节点之间没有空格（读作「2 个模型·CNY·更新于 …」）→ 文案断言要**逐节点**做，别拼整串。
- ⚠️ **`display:inline-block` 子节点会给父块加出基线空隙**（本页元信息盒 13→16 后卡高变 186，多 8px）：
  设计里这类「一行文字」的父级是 `layout: horizontal, alignItems: center` 的 flex 行 → 落地也用 flex 行（`align-items:center`），
  不要用 `inline-block` 收窄宽度。
- ⚠️ **`lease-set.py` 第二个参数**：纯数字会被当**分钟数**（旧版直接写进去 → 租约行成 `until 45` 非法时间戳）；
  现改为 `lease-set.py <holder> --minutes 45` 自动算子时间戳，`lease-set.py free` 直接释放。
