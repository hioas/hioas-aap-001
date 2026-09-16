STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。四条在办：①**目录命名对齐 hioas-aap-client**（用户 dev server 持句柄 → 每轮重试，锁一放就搬）②**按序号逐页复核**：序号 1/2 本轮补上 430 宽载体页（**22/22 页全覆盖**），并给载体页加了「设计期望值 checks」维度；已复核页里 3~23 行的 checks 维度**尚未补**（队列 8）③**序号 9 测量面 fixture 缺口已补并复跑**（历史）④**登录注册页 auth fixture 缺口本轮已补**（`api/v1/auth/sms/{send,login}/post`，同探针 before/after 见队列 6）。历史流水归档在 aap-notes-archive-2026-09-16.md，**不要每轮读**。
LEASE: aap-tdd-run-20260916-0835 until 2026-09-16 09:35

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

0. **目录命名对齐**（§1 A，每轮先试一次 `git mv`，被占用就记一行顺延）。
1. **按台账序号 1→23 逐页复核**（不重写页面，只做客观复核 + 修偏差）：每页跑
   `npm test` **连跑两轮**全绿 · `npm run type-check` exit 0 · `build:mp-weixin` 产物存在（`pages/<route>/index.{js,json,wxml,wxss}`，
   `credential-submit/form`、`quote-form/{index,apikey,success}` 等同理）· 有 `__measure-*.html` 载体页的页面复跑 430 宽 DOM 实测并用
   `.agents/state/cmp-measure-runs.py` 证明**两次独立测量一致**；有偏差按 §2 的第 4~6 步（先红后绿）修；台账行写「复核通过 <时间> + 命令」。
2. **已拍板口径的落地核对**：用户已拍板一条 —— 报价单列表「新建报价」与检测报告「填写报价」落点 = `/pages/quote-models/index`
   （画布序号 9；已落 `e1522f7`）。复核时确认 22 页里**没有别处**仍把 `/pages/quote-form/index` 当「新建/填写」入口，
   有则按同口径改（**先红后绿**，别只改注释）。
3. **15 条待人类拍板缺口**：只做**可自主**的部分；未拍板的**保持原样**，每轮简报只列 1 条最该拍的，不擅自改设计稿口径。
4. 画布余下 **8 个管理端 PC 页（`aap-admn`）** —— **本轮范围外**，除非人类放行，不要开工。
5. ✅ **补 序号 9 的测量面 fixture（已完成 2026-09-16 08:28）**：`api/v1/quotes/q9/items/index`（GET 明细行；页面按 `src/api/quote.ts:90` 的回落入口取数）。
   已补 fixture + 同探针 before/after（`__measure-model-pricing-q9.html`，red=404 无明细 / green=gpt-4o·2.50·10.00 且 PUT 成功）+ 解析器体检 `check-mock-fixtures.py` 红→绿；
   **用 `api` 目录的 8 页（3、4、4-v1、5、6、7、8、9）已两轮复跑**：两轮一致，且与上轮 review 留证逐字节相同（仅序号 9 的 phase4 由「404 文案」变回「保存成功 + 跳 model-pricing」，正是本缺口）。
6. ✅ **给 序号 1（登录注册）、2（工作台）补 430 宽载体页（已完成 2026-09-16 08:58）**：新增 `__measure-login.html`（93 条设计期望值 checks + 6 相交互：空表单 / 缺短信码 / 未勾协议×2 / 获取验证码 / 登录成功；`?scenario=guard` 只跑校验门）与 `__measure-workbench.html`（92 条 checks + 交互回放 2-actions）；两页均**两轮独立测量全等**且 `checkFails` 49→0 / 7→0；配套补 `api/v1/auth/sms/{send,login}/post` fixture（红 FAIL 2 → 绿 FAIL 0）；新增证据维度 `evidence/requests-序号<tag>-run{1,2}.txt`（serve 实收请求行，写请求带 body）——「校验门有没有偷偷发请求」由 **guard 场景 requests 0 行**直接证明，不再靠页面自报。（脚本升级：`review-measure.sh` 支持第 5 个参数 url 查询串 + 落 requests 证据；`check-mock-fixtures.py` 新增两条 POST 检查并把变体目录名（`api-tmp-noauth`）归到基础 mock；新增 `cmp-flat-phase.py`（扁平老留证 vs 新 phase 跨代对比）、`text-list.py`、`append-login-structure-tests.py`）
   两轮 dump-dom + 与建页留证对比；这两页此前只有截图/产物证据，是逐页复核里唯一没有客观 DOM 数字的两行。**← 下轮开工第一件事**
7. （工具卫生）把「uni-app 内部测量元素不计入溢出统计」的口径补到序号 22 的载体页（`uni-picker`），与序号 6 已修的 `uni-resize-sensor` 同族；
8. **给其余 20 个载体页补「设计期望值 checks」维度**（本轮新立，从序号 3 开始，一页一轮）：现有 3~23 的载体页只测「文案齐、溢出 0、两轮一致」，本轮登录页的经验说明**还能量出与设计树的逐项偏差**（序号 1 就量出 49 条）。做法照 `__measure-login.html` 的 `chk(k, got, want)`：want 一律取 `.calicat/raw/pages/<page>/design.tree.json` + `node-probe.py` 的声明值，不许凭截图目测。
9. **队列 2「已拍板口径核对」仍未做**：确认 22 页里没有别处把 `/pages/quote-form/index` 当「新建/填写」入口（已拍板落点 = `/pages/quote-models/index`，page-9）。
   如果还有别的页面出现「两轮 overflowing 波动但 docScrollWidth 恒等」，先跑 `__diag-report-overflow.html` 那类祖先链探针定位，再决定是探针噪音还是真溢出。

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
- 设计截图像素量尺：`python .agents/state/png-bands.py <png> v|h <idx> [from] [to]`（同色色带 = 盒子边界；定卡高/间距/栏高最硬的依据）
- 像素对账：`python .agents/state/text-rows.py`（同一脚本跑设计与实现，逐行文本带对比）
- 台账取件：`python .agents/state/list-pending.py`（按序号列出未完成页面）
- 两次独立测量一致性：`python .agents/state/cmp-measure-runs.py <runA.json> <runB.json> [phase]`（扁平单段文件自动兼容）
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
- Calicat CLI：`calicat status` / `calicat tools-call --name get_screenshots --args '{...}'`；
  技能脚本目录 `C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/`
- gh：`E:\tools\bin\gh.exe`（已登录 geeker-lait）
- 平台坑：中文 Windows `netstat` 是 GBK；`taskkill` 要写 `/PID`（`//PID` 报「无效参数」）；
  bash 把中文塞 JSON body 会变 GBK（要发中文请求体用 Node/Python 的 utf-8）；
  `npm run build:h5` 会清空 `dist/build/h5` → `__measure*.html` 载体页每次 build 后要重新拷贝。
