STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：①新维度「设计文本叶子 ↔ 实现 DOM」全量审计 ✅（22/22 页 · 1131 设计叶子 · 匹配 970 · 待判读 class 172 · 序号 8 四类经 PNG 判定非偏差已登记 textleaf-accept.json）②序号 1 登录页「字重 10 处 + 行盒 10 处」修正 ✅③序号 1「16px 残差」收口 ✅（18:45 轮：载体页再扩 19 条 checks → 红 19/133 · docH 1098 → 绿 0/133 · docH 1114 = 设计帧高；像素对账 42 命中 / 6 未命中全部判读为非缺陷）④**下轮第一件事 = 序号 1 的两个新待办**（5 处 center 描边 `border`→ring · 3 个输入框图标盒 16×16→20×27 且填充改灰 rgba(148,163,184,1)），其后按 172 条待判读清单逐页推进。队列 0 挂起（D6）；管理端 8 页范围外。
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
   - **序号 1 的两个新待办（18:45 轮发现并留证，下轮先红后绿做）**：(a) 5 处 center 描边仍用 `border` 实现（`.field__box`×3 · `.captcha` · `.sms-btn` · `.wechat` · `.agree__box`）→ 按同族页口径改 `box-shadow: 0 0 0 1px`（border 占布局：输入框内容左界 设计 48 vs 实现 49、右界 382 vs 381）；(b) 3 个输入框图标占位盒 16×16 → **20×27**（设计 `df37d41e` 等声明 w20 fs18）+ 填充改灰 rgba(148,163,184,1) —— 实测设计占位文本左界 **76** vs 实现 **73**（`ink-runs y407..421`）。证据见台账序号 1 行 备注 与 `evidence/review-序号1-16px-checks-报告.md` §7。
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
   - ✅ **序号 9 已完成 2026-09-16 12:21**（cron 轮 `aap-tdd-run-20260916-1205`）：`__measure-quote-setup.html` 由 284 行旧体例重写为 430 宽 iframe + **272 条 checks**
     （want = `page-9` design.tree.json 声明值 + `text-fields.py` 全字段 + 设计 PNG 430×1211 像素实测）。
     红基线（`git stash push` 复现修复前源码、同一份探针两轮）**53/272**、`docH 1202` → 绿 **0/272**、`docH 1212`（设计帧 1211）；
     两轮独立测量 **33/33 字段全等**；`git stash pop` 复位后重建复跑同值。
     修掉 12 类偏差：卡片/底栏/保存按钮投影（设计 effects）· 三处 0.8 描边 `border`→`box-shadow`（内容左界回到 46）· 字数提示行框 16→15 ·
     凭证说明图标盒 20×20→14×18 · 模型工具栏 40→44（全选图标行框 24）· 模型行高 58→59（型号名行框 19）· 底部说明 `padding-top` 12→16 且图标盒 13→15×20 ·
     提示卡文案行距 16→14（卡高 56→52）· 12 处图标盒按设计图层且形状（含旋转）移入 `::before` · 返回/帮助圆角 50%→18px。
     交互相 `?scenario=actions` 两轮逐字节相同：勾选第 4 行/全选/全不选 计数 3→4→5→0 · 保存 → 真实 `POST /quotes` + `POST /quotes/q9/items` →
     toast「保存成功」→ `/pages/model-pricing/index?quoteId=q9` · 纯测量轮 serve 实收仅 3 行。
     像素对账（实现截图 vs 设计 PNG，±3）内容列 **49/49** + 条列 **19/19** = **68/68 命中、未命中 0**。
     质量门：`npm test` **1172/1172 ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · 截图 `evidence/20260916-1221-序号9-模型报价设置-checks轮-h5-430宽.png`。
     **下一轮：序号 10**（`page-10-2`「供应商档案编辑 2」→ `/pages/profile-edit/index`，载体页 `__measure-profile-edit.html`，mock 目录 `api-10-2`）。
   - ✅ **序号 10 已完成 2026-09-16 12:5x**（cron 轮 `aap-tdd-run-20260916-1231`）：`__measure-profile-edit.html` 由 355 行旧体例重写为 430 宽 iframe + **229 条 checks**，
     红基线 36 → 绿 0、`docH 1409` = 设计帧高，像素对账 56/56 命中、未命中 0（明细见台账序号 10 行与 `evidence/review-序号10-checks-报告.md`）。
   - ✅ **序号 10.1 已完成 2026-09-16 13:0x**（cron 轮 `aap-tdd-run-20260916-1255`）：`__measure-profile.html` 由 314 行旧体例重写为 430 宽 iframe + **271 条 checks**
     （want = `page-10-1-2` design.tree.json 声明值 + 58 个文本叶子 + 设计 PNG 430×1414 像素实测）。
     红基线（修复前源码 + 同一份探针两轮）**22/271** → 绿 **0/271**；两轮独立测量 **43/43 字段全等**；`docH 1414` = 设计帧高。
     修掉 3 类偏差：8 处图标占位盒按设计图层（15×20 · 20×27 ×3 · 14×18 · 26×36 · 22×30 · 22×30，形状入 `::before`）·
     2 处 Figma center 描边 `border`→`box-shadow 0 0 0 1px`（上传新资质按钮 / 保存按钮）· 胶囊宽 91→95 且 x 323→321。
     交互相两轮逐字节相同：保存 → 真实 `PUT /provider/profile`（toast「保存成功」· 完整度 72%→**78%**，pill/percent/bar 三处一致）·
     四个入口（编辑/管理/上传新资质/去补全资质）均跳 `/pages/profile-edit/index` · 返回 = navigateBack · 每轮 serve 实收 24 行 = 1 写 + 11 对只读 GET。
     像素对账（设计 PNG vs 实现截图，按最近 y0 一对一匹配）**31/33 = 97%**（唯一未命中 = 官网值行被设计切成 h11 + h1 两条带）。
     质量门：`npm test` **1173/1173 ×2** · `type-check` exit 0 · `build:mp-weixin` 产物 `pages/profile/index.{js,json,wxml,wxss}` · `build:h5` DONE ·
     截图 `logs/screenshots/20260916-1309-序号10.1-供应商档案-checks轮-h5-430宽.png` · 设计帧重抓 sha256 逐字节相同（无漂移）。
     **下一轮：序号 11**（`page-11`「【报价管理】模型定价-详情」→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`（另有 `?quoteId=` 回落载体页 `__measure-model-pricing-q9.html`），mock 目录 `api-11`）。
   - ✅ **序号 12 已完成 2026-09-16 13:5x**（cron 轮 `aap-tdd-run-20260916-1330`）：`__measure-quote-preview.html` 由 241 行旧体例重写为 430 宽 iframe + **126 条 checks**
     （want = `page-12-2` design.tree.json 声明值 + `text-lineheight.py` 全字段 + 设计 PNG 430×1027 色带/描边/墨迹实测）。
     红基线（`git stash` 复现修复前源码 + 同一份探针两轮）**10/126** → 绿 **0/126**；两轮独立测量 **24/24 字段全等**；`docScrollHeight 1027` = 设计帧高；溢出 0 · 文案缺失 0。
     修掉 7 类偏差：①卡片效果**按设计逐卡不同**（卡1 `drop_shadow(0,6,20,.06)` 无描边 / 卡2·卡3·确认卡 `stroke 1px #EEF2F7` 无投影；修前四卡统一 ring）
     ②基础价行 **34→38**（标签盒 12→16、line-height 16 = 设计显式 height 16/22）③规则行**按类型分行高**：请求规则行 **40**（内容 20）、峰谷/阶梯行 **44**（内容 24）
     —— 模型新增 `RuleKind` + 页面 `.rule--compact` ④请求规则行文字行框 **13.2**（设计墨迹位于行顶 +11）、峰谷/阶梯 **18**（+13）
     ⑤`.rule__wrap` 去掉 `min-height:24px` + `align-items:center`（它把 11px 行框在 24 高盒里居中 → 整行墨迹下沉 3.5px，**像素对账抓出**；设计该容器是 `alignItems=start` 的行）
     ⑥确认行 **22→19**（= fs12 行框 19.2；提示条顶回到 851 = 800+20+19+12）⑦提示条 **53→56**（文本行框 16.5→18 = 10+2×18+10）。
     交互相 `?scenario=actions` 两轮逐字节相同：取消勾选 → 提交被门禁拦住（toast「请先确认报价条款」· hash 不变 · **零写请求**）→ 重新勾选 → 真实 `POST /quotes/q7/submit`（body 为空）→ toast「已提交审核」→ `#/pages/quotes/index`。
     **fixture 缺口先红后绿**：落地页会取 `GET /api/v1/quotes?page=1&pageSize=10`（api-12 缺 → 404 且错误 toast 盖掉提交成功 toast）→ 补 `api-12/v1/quotes/index` 后 200。
     像素对账（±3）**命中 55 / 未命中 3**：未命中 = 卡1→卡2 投影带的逐行主色归一化差（`scan-col x=20 388..396` 两侧同为 `rgb(245,247,249)`）+ 提交按钮文案底缘 AA 的 1 行带阈值效应 → 非页面缺陷。
     质量门：`npm test` **1178/1178 · 72 files ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE（wxss 含 `.card--lead` 投影、`.rule--compact{height:40px}`、`height:38px`、`line-height:13.2px`、`min-height:56px`）· `review-artifacts` 22/22 ·
     报告 `evidence/review-序号12-checks-报告.md` · 截图 `logs/screenshots/20260916-序12-报价预览与提交-checks轮-h5-430宽.png`。
     **下一轮开工第一件事**：队列 8 的 **序号 12-v1**（`page-26`「新增报价单-初始态」→ `/pages/quote-form/index`，载体页 `__measure-quote-form.html`，mock 目录 `api-12-v1`）。
   - 本轮新增探针尺子（已写进 §5）：`node-by-id.py`（按 layer_id 查声明值）· `ink-bbox.py` / `ink-runs.py` / `scan-row.py` / `scan-col.py`（墨迹与边界定位）；
     坑：list 助手对 `A@@N B` 型选择器必须走新增的 `resolveAll()`（否则拿到「全部 A 的文本」）· `collect()` 内的 `textOf` 在外层作用域不可见 ·
     `check-mock-fixtures.py` 默认模式会把 api-11 的路径打到 api 目录上假 FAIL（已改为「按每条 check 自带的 mock 目录分组、各起一次 serve」，2 组 FAIL 0）。

   - ✅ **序号 12-v1 已完成 2026-09-16 14:1x**（cron 轮 `aap-tdd-run-20260916-1355`）：`__measure-quote-form.html` 由 277 行旧体例重写为 430 宽 iframe + **286 条 checks**
     （want = `page-26` design.tree.json 声明值 + 设计 PNG 430×1238 像素实测）。红基线（`git stash` 复现修复前源码 + 同一份最终版探针两轮）**45/286** → 绿 **0/286**；
     两轮独立测量 **28/28 字段全等**；`docScrollHeight 1241`（= 设计 1238 + 提示卡 CJK 换行 3）· 溢出 0 · 文案缺失 0。
     修掉 **7 类偏差**：6 处 effects 投影（4 卡/条 + 保存按钮）· 4 处 center 描边 `border`→ring · 13 处图标盒（盒 = 声明宽 × 字号1.5，形状入 `::before`）+
     返回/帮助圆角 50%→18px · 须知卡标题图标行盒 27→24 · 须知条目文案行盒 14.4→18 · 模型 chip 文案 10px/600→11px/500 · 标签行行盒 18→17.5。
     像素对账 `cmp-序号12v1-设计PNGvs实现截图-结构带.txt` **命中 60 / 未命中 11**（3 条投影衰减步长 + 8 条卡2 以下 +3~4 顺延，均非页面缺陷）。
     交互相两轮逐字段相同 + serve 实收请求行逐字节相同（7 行/轮）：首屏零请求 · 选择凭证 → `GET /credentials` + `GET /credentials/c1` → chip「已选 1 / 2」·
     保存并继续 → 真实 `POST /quotes` + `POST /quotes/q9/items` → toast「保存成功」→ `#/pages/model-pricing/index?quoteId=q9`。
     质量门：`npm test` 1178/1178 ×2 · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · `review-artifacts` 22/22 ·
     报告 `evidence/review-序号12v1-checks-报告.md` · 截图 `logs/screenshots/20260916-1412-序12v1-新增报价单初始态-checks轮-h5-430宽.png`。
     **下一轮开工第一件事**：队列 8 的 **序号 12-v2**（`page-apikey` → `/pages/quote-form/apikey`，mock `api-12-v2`；注意共用组件连带）。
   - ✅ **序号 12-v3 已完成 2026-09-16 15:0x**（cron 轮 `aap-tdd-run-20260916-1445`）：**新建**载体页 `__measure-quote-success.html`（430 宽 iframe + **259 条设计期望值 checks**，构建脚本 `build-probe-12v3.py` 切 12-v2 骨架）。红基线（`git stash push -- aap-client/src/pages/quote-form/success.vue` 复现修复前源码 + **同一份最终版探针**两轮）**30/259** · `docH 1018` → 绿 **0/259** · `docH 1018`（= 设计帧高）；两轮独立测量 **31/31 字段全等**（`cmp-measure-runs … phase1` 不一致 0）。
     修 **4 类偏差**（清单见台账序号 12-v3 行 用例(证据) 列 / `evidence/red-序号12v3-checks-设计期望值偏差.txt`）：
     ①**5 处 effects 投影**（三张卡 `drop_shadow(0,4,16,rgba(15,23,42,.06))` · 底栏 `(0,-4,16,.05)` · 主按钮 `(0,6,16,rgba(37,99,235,.28))`）；
     ②**8 个图标占位盒按设计图层**（盒 = 声明宽 × 字号×1.5 → 20×27 / 20×27 / 41×57 / 16×21 / 15×19.5 / 18×24 / 18×24 / 20×27，形状入 `::before`，颜色改由伪元素声明）；
     ③**单号行右侧组 gap 8→4**（设计「单号值行」55b312e3 gap=4，与密钥行「密钥信息」gap=8 不同）；
     ④提示卡文案按单行渲染（行盒 13.2；卡高 48 由图标行盒 24 决定 —— 旧注释「文案两行 26.4」作废）。
     **像素对账 `cmp-bands-6`（±3）：内容列 35/35 + 条列 15/15 = 50 命中 / 0 未命中**（`evidence/cmp-序号12v3-设计PNGvs实现截图-结构带.txt`）。
     **交互相有牙齿（四出口，各两轮逐字节相同）**：`?scenario=copy` 剪贴板写 `QT-20240615-0007` + toast「报价单号已复制」· hash 不变 · 零写请求；
     `?scenario=primary` → `#/pages/model-pricing/index?quoteId=q9`（渲染「模型定价」）；`?scenario=secondary` / `?scenario=close` → `#/pages/quotes/index`（5 张卡片）；
     每轮 serve 实收 2~3 行 **全为只读 GET**。**fixture 缺口先红后绿**：两个落地页 fixture 缺失（404 + 错误 toast）→ 补 `api-12-v3/v1/quotes/q9/items/index`（同 12-v1）与 `api-12-v3/v1/quotes/index`（同 12）→ 200 且 toast 空，`check-mock-fixtures --mock api-12-v3` **5 PASS / FAIL 0**。
     质量门：`npm test` **1178/1178 ×2** · `type-check` exit 0 · `build:mp-weixin` DONE · `build:h5` DONE · `review-artifacts` 22/22 ·
     **共用组件回归门**（本页无共用组件，仍复跑兄弟载体页）：12-v1 **286 条 0 失败** · 12-v2 **272 条 0 失败** ·
     截图 `evidence/20260916-序12v3-新增报价单保存成功-checks轮-h5-430宽.png`（430×1018 = 设计尺寸）。
     **下轮开工第一件事**：队列 8 的 **序号 15**（`page-15-2`「【合同与通知】合同签署 2」→ `/pages/contract/index`，载体页 `__measure-contract.html`，mock 目录 `api-15`）。
   - ⚠️ 本轮踩到并写进 §5 的坑：重抓前必须先确认 Calicat 编辑器在浏览器里打开（否则 22 帧全 FAIL `请先在浏览器中打开文件`）；
     `cmp-measure-runs.py` 对扁平文件也要传 phase 名（传 `flat`）；Chrome `--screenshot` 的中文路径会被 MSYS 弄坏 → 先写 ASCII 临时名再 `cp`；
     探针自身 4 处口径错误（`.card__hint` 只有 2 处不是 3 处、`.card__title-row` 首个是 APIKey 卡、`.card__field` 的 8px 是 padding 不是间距、`declared()` 不认 `[data-testid=...]`）。
   - ⚠️ 本轮踩到并写进探针的 3 条口径（**探针自身**的坑，不是页面缺陷）：①设计里 chip 的「待检测 3」是 dot+label+count 三个节点用 flex `gap` 隔开，`textContent` **没有空格** → 分开断言 `chip__label`/`chip__count`；
     ②在 `padding` 容器内的卡片，左右边要按容器内边算（序号 3 的卡是 20/410，不是 16/414）；③`0.8px` 描边的 computed 是 **used value**（Chrome 取整成 1px）→ 判「样式表声明值」（探针新增 `declared(sel, prop)` 读 CSSOM），used 值另记一条；
     ④box-shadow 颜色 alpha=1 时 Chrome 序列化成 `rgb()`（`norm()` 已改成 alpha 感知，否则误报）。
   - 探针工具：`python .agents/state/show-checks.py <run.json> [out.txt]` 打印 checks 概览 + 失败清单（红/绿基线转录）；拍 430 宽截图 `bash .agents/state/shot-430.sh <输出.png>`（自带静态服务器，用完即关）。
   - ✅ **序号 12-v2 已完成 2026-09-16 14:5x**（cron 轮 `aap-tdd-run-20260916-1420`）：**新建**载体页 `__measure-quote-apikey.html`
     （430 宽 iframe + **272 条设计期望值 checks**；由 `build-probe-12v2.py` 从 12-v1 载体页切「顶部作用域 / `collect()` helpers / 溢出统计」三段骨架复用）。
     红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**6/272** → 绿 **0/272**；两轮独立测量 **35/35 字段全等**；
     `docScrollHeight 1127`（设计帧 1128）· 溢出 0 · 文案缺失 0 · 共用组件回归门 12-v1 复跑 **286 条 0 失败**。
     修 6 类偏差：展开态占位色 #CBD5E1→**#94A3B8**（逐帧不同，加 `.select--open` 作用域）· 面板 `border`→**ring + 设计投影**
     `0 0 0 .8px #2563EB, 0 12px 24px rgba(15,23,42,.1)` · 选项行宽 **354**（x 38）· 图标盒 13×13→**17×22.5**（形状入 `::before/::after`）·
     选项行高 **55**（新增 `CRED_SUB_LINE_BOX = 16`：设计三个副行节点都显式 h16，不是 13.2）· 标签行盒 17.5→**17**（两帧共用）。
     像素对账 `evidence/cmp-序号12v2-设计PNGvs实现截图-结构带.txt` 命中 **54 / 未命中 4**（y=485 设计帧首行选中矛盾 + y=737/766/1008 的 ≤1px 小数坐标链，非页面缺陷）。
     交互相三场景两轮逐字节相同：`?scenario=actions`（7 行：选 c2 → 重开验选中态 → 收起 → 保存 → 模型定价落地）·
     `?scenario=settings`（2 行：**/pages/settings/index 已实现并渲染**，改正旧台账「未实现 → hash 不变」口径）· 纯测量轮 1 行。
     质量门：`npm test` 1178/1178 ×2 · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · `review-artifacts` 22/22 ·
     `check-mock-fixtures --mock api-12-v2` **7/7 PASS**（本轮新增 6 条 + `v1/auth/me` fixture）。
     **下一轮开工第一件事**：队列 8 的 **序号 12-v3**（`page-29`「新增报价单-保存成功」→ `/pages/quote-form/success`，
     载体页 `__measure-quote-success.html`，mock 目录 `api-12-v3`），做完再依次收尾 **15 / 20 / 21 / 22 / 23** 五页（队列 8 剩余）。
9. **决策台账 `aap-decisions.md` 的待执行项优先于本队列**（前台会话 2026-09-16 建立该文件，状态文件顶部已加提醒）：
   - ✅ **D3 · 图例百分比统一且最优** —— **已完成 2026-09-16 09:26**（口径落在 `src/utils/percentage.ts`，执行证据见 `aap-decisions.md` D3）。**下轮第一件事 = 队列 8**（给序号 3 的载体页补「设计期望值 checks」维度，照 `__measure-login.html` 的 `chk(k,got,want)` 做法）。
   - **D1 的循环侧收尾**：把台账里 `missing-prd` 的接口备注改成「依据 `docs/api/接口字段级schema.md` §x」，并核对已实现页面字段名与该 schema 是否一致（不一致以 schema 为准改代码）。
   - D2 已完成（2026-09-16 09:15）；**D4/D5 的循环侧小改已完成 2026-09-16 09:26**（`src/styles/tokens.scss` 顶部注释改为「主色=设计稿蓝（D4）+ 图标维持 CSS 占位（D5）」；`docs/aap-client-page-plan.md` §4 表格三行冲突结论更新）。D1~D6 至此全部有结论。
   - ⚠️ 已向人类提一条拍板：D2 的验收「`src/` 内 grep 钱包 = 0」与设计稿冲突（mine 页的「我的钱包」卡是 page-21-2 图层），建议改为按 `src/pages/workbench/**` 计。

### 本轮小结（追加式，一行一轮）

- 2026-09-16 17:20（cron 轮 `aap-tdd-run-20260916-1710`）· **队列 1 余下行质量门 + 队列 7（uni-picker 溢出口径）+ D1 循环侧收尾**：
  ①**队列 1**：`npm test` **1181/1181 · 72 files 连跑两轮**（17:12 / 17:13）· `npm run type-check` exit 0 · `build:mp-weixin` DONE（22 路由产物齐备）· `build:h5` DONE · `review-artifacts` **22/22 三件套齐备且注册**。
  ②**队列 7（uni-picker 溢出口径）**：`__measure-usage.html` 的溢出统计排除谓词由 `uni-resize-sensor` 扩为 `uni-resize-sensor, uni-picker`（同族口径，与其它 5 个载体页一致）；改后复跑两轮独立测量 **50/50 字段全等、不一致 0、checkFailCount 0/267、overflowing 0、docH 1138 = 设计帧高**（`evidence/review-序号22-q7-run{1,2}.json` + `requests-序号22-q7-run{1,2}.txt` 各 1 行只读 GET）。
  ③**D1 循环侧收尾（字段级 schema 备注 + 字段名一致性核对）**：台账序号 2 / 22 行的 `missing-prd` 接口备注改为引用 `docs/api/接口字段级schema.md` §1/§2/§3；字段名核对结论——用量域（total_tokens/request_count/amount_total/mom_rate/platform_fee_rate/cache_read_tokens/cache_hit_rate/quota_raw/stat_hour 等）与档案域（provider_code/company_name/phone_masked/qualification_files/recheck_interval_days）**全部与 schema 一致**；唯一别名：schema §3 写 `uscc`，实现与 15-数据字典用 `unified_social_credit_code`（符合 D1「1:1 与字典同名」规则本身），已在上文登记待人类定夺是否统一。
  ④提交 `b016502`（先误把 `.playwright-mcp/` + 两个 pnpm 残留 `git add -A` 卷进来，已 `git rm --cached` 后 amend 还原，现工作区只剩这 3 个规定的不跟踪项）。**下轮**：队列 1 若还有余行则续跑；否则队列 3（15 条待拍板缺口——只做可自主部分）或等人类指示。

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

- 2026-09-16 12:21（cron 轮 `aap-tdd-run-20260916-1205`）· **队列 8 第 8 页：序号 9「模型报价设置」载体页补「设计期望值 checks」维度（272 条 · 偏差 53→0）+ 12 类设计偏差修复 + 整页对齐设计帧 1211（像素对账 68/68 命中）**：
  ①**口径纠正**：状态文件在办项曾把序号 9 写成「→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`」，与台账「目标路由 = `/pages/quote-models/index`」
  及仓库实际不符（`/pages/model-pricing/index` 是**序号 11**）→ 本轮按台账执行（载体页 `__measure-quote-setup.html`），并已把状态文件改成与台账一致。
  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-9`（layer_id `bbdb4ec0-…`）→ `design.json` sha256 `bb278d4e…` **逐字节相同**（无漂移）。
  ③**TDD 红→绿（本轮主交付）**：载体页重写为 430 宽 iframe + 272 条 checks；红基线（`git stash` 复现修复前源码、同一份探针两轮）**53/272**、`docH 1202`
  → 绿 **0/272**、`docH 1212`；两轮独立测量 33/33 全等；复位后复跑同值。
  ④**修掉 12 类偏差**（清单见台账序号 9 行 / `review-序号9-checks-报告.md` §4）：三处投影（卡片/底栏/保存按钮）· 三处 0.8 描边 `border`→`box-shadow` ·
  字数提示行框 16→15 · 凭证说明图标盒 20×20→14×18 · 模型工具栏 40→44 · 模型行高 58→59 · 底部说明 padding 12→16 且图标盒 13→15×20 · 提示卡行距 16→14（卡高 56→52）·
  12 处图标盒按设计图层且形状移入 `::before` · 返回/帮助圆角 50%→18px。
  ⑤**本页定标**：CJK 文本行框 = fontSize×1.4 取整（15→20 · 14→19 · 13→18 · 12→16 · 11→15，**显式 height 优先**）；remixicon 字形行框 = fontSize×1.5；
  `stroke{align:center,thickness:0.8}` → `box-shadow: 0 0 0 .8px`（**used 值不取整**）；`effects.drop_shadow` → `box-shadow`。
  ⑥**交互相有牙齿**：`?scenario=actions` 两轮 → 勾选/全选/全不选 3→4→5→0 · 保存 → 真实 `POST /quotes` + `POST /quotes/q9/items` → toast「保存成功」→ `model-pricing?quoteId=q9`；
  纯测量轮实收仅 3 行（profile + credentials + credentials/c1）· 溢出 0 · 文案缺失 0。
  ⑦**质量门**：`npm test` **1172/1172 · 72 files ×2** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含本轮设计值）· `build:h5` DONE ·
  像素对账 68/68 命中 · 截图 `evidence/20260916-1221-序号9-模型报价设置-checks轮-h5-430宽.png`。
  ⑧**设计稿静态假数据留痕**：字数提示「13/30」与同帧名称文案 12 字矛盾 → 实现按真实字数（12/30），探针断言「格式 + 与名称长度一致」，
  设计字面量登记在 `designLiteralDiff`（同族于 D3 图例百分比，不照抄）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 10**（`page-10-2`「供应商档案编辑 2」→ `/pages/profile-edit/index`，载体页 `__measure-profile-edit.html`，mock 目录 `api-10-2`）。

- 2026-09-16 12:5x（cron 轮 `aap-tdd-run-20260916-1231`）· **队列 8 第 9 页：序号 10「供应商档案编辑」载体页补「设计期望值 checks」维度（229 条 · 偏差 36→0）+ 9 类设计偏差修复 + 整页对齐设计帧 1409（像素对账 56/56 命中 · 未命中 0）**：
  ①**改名**：未执行 —— 队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-10-2`（layer_id `45f4d7f9-…`）→ `design.json` sha256 `46e9cfee…` **逐字节相同**（无漂移）。
  ③**TDD 红→绿（本轮主交付）**：`__measure-profile-edit.html` 由 355 行旧体例重写为 **430 宽 iframe + 229 条 checks**
     （want = `design.tree.json` 声明值 + `show-node-json.py`/`show-children.py` 节点子树 + 设计 PNG 430×1409 色带/墨迹实测）；
     红基线（`git stash` 复现修复前源码、同一份探针两轮）**36/229**、`docH 1409` → 绿 **0/229**；两轮独立测量 **28/28 字段全等**；`git stash pop` 后重建复跑**逐字段相同**（stash 循环干净）。
  ④**修掉 9 类偏差**（清单见台账序号 10 行 / `review-序号10-checks-报告.md` §3）：卡头图标盒 18×18→**20×27**（形状入 `::before`）·
     卡标题左界 60→**62** · 输入框/半栏框描边 `border`→**ring**（内容左界 13→12、内容宽 332→**334**）· 地区 chevron 盒 11×11→**20×27**（x 186/371→**176/362**）·
     已上传角标勾盒 9×9→**13×16**（角标宽 56→**62**、右边 255→**263**）· 资质行尾部两枚图标间距 0→**8**（删除盒 354..374→**346..366**）·
     **删掉空态行设计里没有的「上传」chevron**（PNG 该区间无 ink + 设计节点 children 只有 [图标][信息容器]）· 草稿按钮描边 `border`→ring ·
     保存按钮按设计节点组合 **[文案 91 宽左对齐][padding-left 4][箭头 22×30]**（文案 ink 277→**240**、箭头 x 309→**335**）。
  ⑤**本页定标**：remixicon 字形行框 = fontSize × 1.5（本页三处自洽：顶部栏 24→36 定内容行、卡头 18→27 定头部行、已上传勾 11→16）·
     文本行框**显式 height 优先**（标签 18 / 文件名与提示 16 / 简介文本 40），`lineHeight:1.2` 不决定行框 ·
     **字段步进 86（标签 18+8+框 44+16），但类型 chip 行只有 40 → 该组 82**（第一轮 want 按统一 86 写错，量成 4px 假偏差）。
  ⑥**交互相有牙齿**：`?scenario=guard` 两轮 serve 实收 **0 行写请求**（校验门证明）；`?scenario=actions` 两轮逐字节相同 →
     chip 切换 · 计数 5/200 · 清空企业名称点保存 toast「请输入企业名称」+ 草稿写 localStorage · `PUT /provider/profile`（12 字段 body）→ 完整度 72%→**78%** ·
     uni-modal「删除资质文件」→ `DELETE /provider/qualifications/q1` → toast「已删除」→ 重拉列表；纯测量轮各 2 行 GET。
  ⑦**质量门**：`npm test` **1173/1173 · 72 files 连跑两轮**（+1 新用例）· `type-check` exit 0 · `build:mp-weixin` DONE（`pages/profile-edit` 四件套 + app.json 已注册）·
     `build:h5` DONE · 像素对账 `cmp-bands-6`（±3）结构带 **56/56 命中 · 未命中 0** · 截图 `evidence/20260916-序10-供应商档案编辑-checks轮-h5-430宽.png`。
  ⑧**跨代对比**：与上一轮留证（`review-序号10-run1.json`）公共几何块 `topbar`/`bar`/`draftBtn`/`saveBtn`/`chip` **完全相同**、
     `fieldBoxes` 除新增 `bottom` 字段外逐项相同 → 本轮修的全是盒内细节，没动页面骨架；`evidence/cmp-序号10-checks-上一轮vs本轮.txt`（`review-compare --tag 10-checks`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 10.1**（`page-10-1-2`「【档案与凭证】供应商档案 2」→ `/pages/profile/index`，载体页 `__measure-profile.html`，mock 目录 `api-10-1-2`）。

- 2026-09-16 15:0x（cron 轮 `aap-tdd-run-20260916-1445`）· **队列 8 第 15 页：序号 12-v3「新增报价单-保存成功」载体页补「设计期望值 checks」维度（259 条 · 偏差 30→0）+ 4 类设计偏差修复 + 像素对账首个零未命中（50/50）**：
  ①**设计帧重抓（人工指令 C）**：帧「新增报价单-保存成功」+ layer_id `49d2fa52-959d-4415-9fda-edf38415d6bd` 重抓 →
     `design.json` sha256 `cdd34a51…` **逐字节相同**（无漂移）。
  ②**TDD 红→绿（本轮主交付）**：**新建**载体页 `__measure-quote-success.html`（430 宽 iframe + **259 条 checks**；`build-probe-12v3.py` 切 12-v2 骨架，新增 `dump-layout.py` 全字段 dump 出 want）；
     红基线（`git stash push -- aap-client/src/pages/quote-form/success.vue` 复现修复前源码 + **同一份最终版探针**两轮）**30/259** → 绿 **0/259**；
     两轮独立测量 **31/31 字段全等**；`docScrollHeight 1018` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 4 类偏差**：5 处 effects 投影（三卡/底栏/主按钮）· 8 个图标占位盒按设计图层（盒 = 声明宽 × 字号×1.5，形状入 `::before`，颜色改判伪元素）·
     单号行右侧组 gap 8→4 · 提示卡文案单行（旧注释「两行 26.4」作废）。
  ④**像素对账 50 命中 / 0 未命中**（`evidence/cmp-序号12v3-设计PNGvs实现截图-结构带.txt`）—— 本循环首个零未命中页：
     本页几何（1018）本来已对齐，本轮修的都是盒内效果/图标盒，且该页无 CJK 换行残差。
  ⑤**交互四出口两轮逐字节相同**（copy / primary / secondary / close）+ **fixture 缺口先红后绿**（补 api-12-v3 两个落地页 fixture，5 PASS / FAIL 0）。
  ⑥**质量门**：`npm test` **1178/1178 ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · `review-artifacts` 22/22 ·
     共用组件回归门（12-v1 286/0 · 12-v2 272/0）· 截图 `evidence/20260916-序12v3-新增报价单保存成功-checks轮-h5-430宽.png`。
  ⑦**下轮开工第一件事**：队列 8 的 **序号 15**（`page-15-2`「合同签署 2」→ `/pages/contract/index`，载体页 `__measure-contract.html`，mock 目录 `api-15`）。

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
- **本轮（12:05 轮 · 序号 9）新增工具**：`png-rowmodal.py`（逐行主色 + 白占比判卡片/间隙，`--runs` 打印分段；带投影的卡片页首选）·
  `png-colorat.py <png> h|v <idx> <rrggbb> [tol] [minLen]`（某行/列上「接近指定颜色」的连续区间 → 元素横向边界）·
  `show-json.py <file.json> [phase]`（pretty 打印某相）· `show-ledger-rows.py <序号...>`（打印台账整行可见内容）·
  `gen-9-checks-evidence.py`（红/绿 + 交互回放转录合成，后续页面照抄改 tag）· `shot-9.sh`（430×1211 整页截图）。
- ⚠️ **探针断言「容器高」而不是「行框」**：`padding-top` 与内容行同在一个元素上的结构（本页 `.counter` / `.hint`），
  `chkR` 要断 `padding-top + 行框` 的合计（本页字数提示 21 = 6+15 · 凭证说明 24 = 6+18）；行框本身用 `lineHeight` / 图标盒高断言。
- ⚠️ **`box-shadow` 的 used 值不取整**：Chrome 对 `box-shadow: 0 0 0 .8px` 的 computed 实测为 `rgb(..) 0px 0px 0px 0.8px`；
  旧口径「0.8px 的 computed 取整成 1px」只对 `border` 成立（本页两条 stroke 检查都用 0.8px 作为期望值）。
- ⚠️ **PNG 卡片边界：三张卡都带投影时**卡片之间的间隙被两张卡的阴影同时染色，`png-cardmap --x 30` 会把卡片与间隙连成一段；
  用 `png-rowmodal.py --runs`（逐行主色）才能得到 118..265 / 282..558 / 575.. 这类边界。

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

### 5.6 本轮（12:31 轮 · 序号 10）新增的工具与口径

- **按 id/名字读设计节点子树**：`python .agents/state/show-node-json.py <design.json> <节点名> [limit]`
  —— 打印该节点（含 children）的完整 JSON（`dump-node-fields.py` 的 children 会被截断）。
- **读一行的布局骨架**：`python .agents/state/show-children.py <design.json> <节点名>`
  —— 打印该节点**直接子节点**（+ 孙节点）的 name/id/type/width/height/padding/fills/fs/文案，
  一眼看清「行 = [缩略图][信息容器][删除盒][container padding-left 8 → 查看盒]」这类结构（本页靠它定出尾部图标间距 8）。
- **探针语法自检**：`python .agents/state/js-depth.py <extracted.js>`（`extract-inline-js.py` 之后跑）
  —— 大括号净值必须为 0；载体页从别的探针**切片拼接**时最容易漏掉 `collect()` 的收尾 `}`（本轮踩到，`node --check` 只报「Unexpected end of input」不给行号）。
- ⚠️ **`chkList` 只做数值比较**：字符串数组会被 `Math.abs(NaN) > tol` → false **静默放过** → 颜色/字号这类字符串数组必须用 `chkStrs()`。
- ⚠️ **横排元素不能用 `gapBetween()`**（它算 `b.top − a.bottom`，横排得负值）→ 用 `hgap(a, b) = b.x − a.right`。
- ⚠️ **`splitSel` 只认第一个 `@@`**：`A@@0 B@@1` 会拼进 `root.querySelector()` 抛「不是合法选择器」→ 需要「第几个匹配」时改用**全局序**（`.field__box--half@@0` / `.icon-tap@@0`）。
- ⚠️ **`collect()` 内的 `textOf(sel)` 闭包了 `doc`**，外层 `load` 回调用它会 `doc is not defined` 而**静默不 sink**（本轮 phase2/phase4 整相丢失，页面动作却照跑）→ 载体页另给顶层 `textIn(sel)`；
  排查法：`show-phases.py` 打印的 `phases=[…]` 少了哪一相，就去那一相的 sink 参数里找外层借用的 collect 内部函数。
- ⚠️ **字段步进不能一刀切**：卡片里 `标签 18 + 8 + 框 44 + 16 = 86`，但**控件行高度不同时整段会偏**（本页类型 chip 行只有 40 → 该组步进 82、其后恢复 86）；
  写 want 前先用 PNG 引一条「框 ink 起点」序列，别用统一步进递推。
- **本页新增脚本**：`build-probe-10.py`（从 `__measure-quote-setup.html` 切 head/helpers/tail 拼本页载体页）· `shot-10.sh`（430×1409 整页截图）·
  `check-js-balance.py` / `js-depth.py`（载体页内联脚本体检）· `show-node-json.py` / `show-children.py`（设计节点子树）。

- 2026-09-16 13:0x（cron 轮 `aap-tdd-run-20260916-1255`）· **队列 8 第 10 页：序号 10.1「供应商档案」载体页补「设计期望值 checks」维度（271 条 · 偏差 22→0）+ 3 类设计偏差修复 + 整页对齐设计帧 1414（像素对账 31/33 = 97% 命中）**：
  ①**设计帧重抓**（人工指令 C）：`page-10-1-2`（layer_id `54ad46b0-1f7c-498a-ac1a-70dff723b35d`）重抓，`design.json` sha256 `e7983634…` **逐字节相同**（无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-profile.html` 由 314 行旧体例重写为 **430 宽 iframe + 271 条 checks**；红基线（修复前源码 + 同一份探针两轮）**22/271** → 绿 **0/271**；两轮独立测量 **43/43 字段全等**；`docH 1414` = 设计帧高。
  ③**修 3 类偏差**（清单见台账序号 10.1 行 / `evidence/review-序号10.1-checks-报告.md` §4）：8 处图标占位盒按设计图层（形状入 `::before`）· 2 处 center 描边 `border`→ring · 胶囊宽 91→95。
  ④**交互相两轮逐字节相同**：保存 → 真实 `PUT /provider/profile`（完整度 72%→78%，pill/percent/bar 三处一致）· 四个入口均跳 `/pages/profile-edit/index` · 返回 = navigateBack · 每轮 serve 实收 24 行 = 1 写 + 11 对只读 GET。
  ⑤**工具卫生**：`check-mock-fixtures.py` 默认模式对 api-11 的路径假 FAIL → 改为「按每条 check 自带的 mock 目录分组、各起一次 serve」（api / api-11 各 FAIL 0）。
- ⚠️ **载体页 `main()` 的异步链必须 try/catch 并把错误 `sink('error', …)` 出来**：本轮 `main()` 借用了 `collect()` 作用域内的 `textOf` → `ReferenceError` 让 phase2~4 **整段静默丢失**（dump 里只有 phase1，看起来像「跑完了但没交互」）。
  与上一轮「`textOf` 闭包 `doc` 静默不 sink」同类；`show-phases.py` 看 `phases=[…]` 少了哪相即可定位，`show-err.py` 打印错误相。
- ⚠️ **文本带对账不能按 index 配对**：设计 PNG 存在 h=1 的抗锯齿残带（本页 y=602），一按序对齐即**全表串位**、误报 18 条未命中；改「按最近 y0 一对一匹配」后同一对图是 **31/33 = 97%**。写 want / 对账前先看带数与 h=1 残带。
- ⚠️ **`A@@N B` 型选择器在 list 助手里必须组感知**：`querySelectorAll(splitSel(sel).base)` 会退化成「全部 A 的文本」（本页误报 5 条）；`texts/colors/textColors/rects` 统一走新增的 `resolveAll()`。
- **本页新增脚本**：`shot-10.1.sh`（430×1414 整页截图）· `cmp-bands-10.1.py`（设计 PNG vs 实现截图文本带对账，最近 y0 匹配）· `node-by-id.py`（按 layer_id 查设计声明值）·
  `ink-bbox.py` / `ink-runs.py` / `scan-row.py` / `scan-col.py`（墨迹包围盒 / y 带内 x 向墨迹段 / 单行·单列颜色分段）· `show-fails.py`（打印 checkFails 清单）· `show-err.py`（打印载体页错误相）。

- 2026-09-16 13:2x（cron 轮 `aap-tdd-run-20260916-1315`）· **队列 8 第 11 页：序号 11「【报价管理】模型定价-详情」载体页补「设计期望值 checks」维度（271 条 · 偏差 21→0）+ 5 类设计偏差修复（含卡片投影与图标盒）**：
  ①**改名**：未执行 —— 队列 0 已被决策 D6 挂起（`hioas-*` 是仓库名约定，勿再重试），按「人类决策 > prompt」处理。
  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-11`（layer_id `46c3747b-3aca-419f-a302-22cf9de8cff8`）→ `design.json` sha256 `fcec8353…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ③**TDD 红→绿（本轮主交付）**：`__measure-model-pricing.html` 由 285 行旧体例重写为 **430 宽 iframe + 271 条 checks**（构建脚本 `build-probe-11.py`，helpers 与 `__measure-profile.html` 同源）；
     红基线（**修复前源码 + 同一份探针两轮**）**256 条 · 21 失败**（`red-序号11-checks-设计期望值偏差.txt`）→ 绿 **0/271**（`green-序号11-checks-设计期望值.txt`）；
     两轮独立测量 **15/15 字段全等**（`cmp-measure-runs … phase1` 不一致 0）；docH **1540**（设计框高算术 98.4+1365+76 = 1539.4，PNG 1541 含底投影 AA）。
  ④**红基线 21 条的分诊**（写进 red 转录末尾，避免把探针 bug 记到页面账上）：**15 条真页面偏差 + 6 条探针自身期望值 bug**
     （`normShadow()` 会把 alpha=1 的 box-shadow 颜色归一成 `rgb(...)`，而我 want 写了 `rgba(…, 1)`）+ 1 条索引写错（`card3.tokenBoxTops` 用 `slice(0,3)`，而 `.card--box--input` 的 DOM 顺序是行内成对）。
  ⑤**修掉 5 类偏差**（清单见 `evidence/review-序号11-checks-报告.md` §3）：①四张卡补设计 effects `drop_shadow(0,4,16,rgba(15,23,42,.06))` ②保存按钮补 `drop_shadow(0,6,16,rgba(37,99,235,.28))` ③**图标盒改为「盒子 = 设计图层盒、形状入 `::before`」**（卡1 折叠箭头 20×20 · 计费 caret 18×18 · 加分支 + 18×18 · 保存按钮 ✓ 22×22 · 媒体/规则箭头 18×18 · 规则组删除 18×18 · 条件行 + 15×15）④连带布局回到设计值（添加计费分支按钮 **111→119** = 12+18+4+73+12 · 计费方式选择框 **245→237** · 按钮 x **287→279**）⑤媒体列勾选框描边 0.8→**1px**（设计 thickness=1，`:not(.check--on)` 保证勾选态仍无描边）。
  ⑥**本页定标（与其它页不同，必须记住）**：本页 remixicon/字形行框 ≈ **fontSize × 1.1**，不是 ×1.5 —— 三条独立实测自洽（媒体定价头 17.6≈18 · 条件操作行 15.4≈16 · 返回图标盒 26.4≈26）；用 ×1.5 会把卡1 顶成 83（设计 82）、卡3 顶成 603（设计 597）。
  ⑦**像素对账**：`cmp-bands-6-design-vs-impl.py`（±3）内容列 **59/62** + 条列 **19/19** = 78 命中 / 3 未命中；未命中 3 条用 `scan-col` 逐条判读 = 卡2/卡3 顶边 **−2px**（Figma 小数坐标链 211.4→210 / 378.4→377）与底栏内 AA 行的带起点边界效应 → **非页面缺陷**（本轮不在 1–2px 上 churn，避免把下游越改越偏）。
  ⑧**交互相有牙齿**：`requests-序号11-checks-run{1,2}.txt` 各 6 行且两轮逐字节相同 —— 首屏 `GET /quotes/items/qi1`；点顶栏「保存」→ 真实 `PUT /quotes/items/qi1`（body 含 input/output/tier/billing_mode/request_rules）→ toast「保存成功」；勾选「缓存读取价格」→ `.check--on` 2→3 → 底部「保存价格」→ `PUT` body 多出 `cache_read_price`；折叠规则 → 组消失且出现设计里 `visible=false` 的「点击展开，配置计费请求规则」；新增规则组 → 标题 `[规则组 #1, 规则组 #2]`；返回 = navigateBack。
  ⑨**回落载体页一并复跑**：`__measure-model-pricing-q9.html`（`?quoteId=q9`，mock `api`）两轮 20/20 字段全等，docH 1540，未受本轮改动影响。
  ⑩**质量门**：`npm test` **1173/1173 · 72 files 连跑两轮**（13:25:19 / 13:25:48）· `type-check` exit 0 · `build:mp-weixin` DONE（wxss 内含 `box-shadow:0 0 0 1px #cbd5e1` / `0 6px 16px rgba(37,99,235,.28)` / `width:18px;height:18px`）· `build:h5` DONE · `review-artifacts` 22/22 · 截图 `logs/screenshots/20260916-序11-模型定价详情-checks轮-h5-430宽.png`。
  ⑪**下轮开工第一件事**：队列 8 的 **序号 12**（`page-12-2`「报价预览与提交 2」→ `/pages/quote-preview/index`，载体页 `__measure-quote-preview.html`，mock 目录 `api-12`）。

### 5.7 本轮（13:15 轮 · 序号 11）新增的工具与口径

- **按页组装 checks 探针**：`python .agents/state/build-probe-11.py`（读 `__measure-profile.html` 的**顶部作用域**（var f/acc/SCENARIO/SHOT_ONLY/NO_ACTION + splitSel）再拼本页 collect/checks/phases）。
  ⚠️ 切片边界必须落在 `function collect(doc, win, withChecks) {` **之前**：若按 `var CARDS = '.card'` 切，会把上一页的 `collect()` 打开却不闭合（build-probe-10.py 之所以能那样切，是因为它的 BODY 接着写 collect 内部）。
  没切干净时 `node --check` 只报 `Unexpected end of input`，用 `js-depth.py` 看大括号净值更直接。
- **红基线不需要 `git stash`**：本轮的红 = 「新探针 + 未修改的源码」（本轮的修复在前，探针在后），直接跑 `review-measure.sh <tag>-red …` 两轮即可；只有「探针先于修复存在」的页面才需要 stash 复现修复前代码。
- ⚠️ **`normShadow()` 的 want 必须写 `rgb(...)`**：Chrome 对 alpha=1 的 box-shadow 颜色序列化成 `rgb(r, g, b)`，探针的 `normColor()` 也按 alpha 感知归一 → 6 条 `*.ring` 检查全假失败（本轮踩到）。
- ⚠️ **list 类 rect 顺序是 DOM 序，不是「视觉行序」**：`.card--price .box--input` 的前三项是「行1 的输入/输出 + 行2 的输入」，按行取要显式用下标 `[0,2,4]`（本轮踩到，误报 1 条）。
- **图标盒口径的判据**：先看设计图层是否给了**声明 width**（给了就按它定盒宽），行框高再由该页实测字形行框（本页 ×1.1）定；`fit_content` 的图标（折叠箭头/删除/加号）则取「所在行的行盒高」上限，**不要**一律套 fontSize×1.5 —— 套错会把卡高/行位整体顶偏（本页可差 5–6px）。
- **本轮新增脚本**：`shot-11.sh`（430×1541 整页截图）· `gen-11-checks-evidence.py`（红/绿转录合成）· `annotate-11-evidence.py`（给红转录补「探针 bug vs 页面缺陷」分诊段）。

### 5.8 本轮（13:30 轮 · 序号 12）新增的工具与口径

- **文本叶子行高全字段 dump**：`python .agents/state/text-lineheight.py <page-id> [--geom]`
  —— 打印设计树里**每个文本叶子**的 `fontSize / lineHeight / 显式宽高 / 字色 / 文案`（比 `text-fields.py` 多打 lineHeight，判「声明行框」的第一入口）；
  `--geom` 打印每个节点的 x/y/宽高/内边距（实测本页除根帧外 x/y 全为 None → **fit_content 尺寸只能靠 PNG 实测**）。
- **描边行定位（判卡片上下边界的第一工具）**：`python .agents/state/stroke-rows.py <png> <rrggbb> [tol] [mincount] [x0] [x1] [y0] [y1]`
  —— 找出「接近指定色」的横向量 ≥mincount 的行（本页 `eef2f7 6 150` → 卡2 上下 392/612、卡3 624/788、确认卡 800/926，**一次把四张卡的边定死**）。
  比 `png-colorat v 16` 更硬：1px 中心描边在小数坐标下只在圆角附近整行匹配，直线段反而被 AA 摊薄。
- **看文件结构**：`python .agents/state/show-structure.py <relpath>`（`design.tree.json` 是**单个节点 dict** 而不是 `[{id,layer_data}]` —— 直接按 layer_data 遍历会得到 nodes:0）。
- **按页组装 checks 探针**：`python .agents/state/build-probe-12.py`（从 `__measure-model-pricing.html` 切**三段**骨架：顶部作用域 / `collect()` helpers / 溢出统计；
  ⚠️ 溢出统计里引用了 `NEED_TEXT`，必须切在它**之后**并在本页 BODY 里先定义 `var CARDS/NEED_TEXT` 再拼，否则 `NEED_TEXT is not defined`）。
  切片自带 helper 不含 `textColors`（字色版）→ 本页 BODY 里补一个同实现版本（`resolveAll` + `normColor(getComputedStyle(e).color)`）。
- **本页定标（供同族「逐模型价格卡」长页复用）**：顶部导航 96（48 + 图标字形行框 fs24×1.5=36 + 12）· 卡 padding 20 r16 · **头行 26**（标签胶囊 h20 居中）·
  **基础价行 = 标签 16 + 值 22 = 38**（设计显式 height，别用 fontSize 反推）· **规则行 = padding 10 + max(图标盒, 文本行框) + 10**，
  峰谷/阶梯行内容 24（图标盒 fs16×1.5）→ 44、**请求规则行内容 20 → 40**（该行设计图标图层 `width=fit_content`）·
  确认行 = fs12 行框 19.2 · 提示条 = padding 10 + n×18 + 10（11px 文本行框 18）· 操作条 84 = 12 + 48 + 24。
- ⚠️ **卡片效果要逐卡断言**：同一页里卡1 只有 `effects drop_shadow`（无 stroke）、卡2/卡3/确认卡只有 `stroke`（无 effects）→
  探针必须按卡写 want（`chkC('.card@@0','boxShadow',…)`），不能一句「统一 ring」。PNG 佐证法：卡下方若有投影染色（本页 381..391 带 `rgb(240,242,245)`）= 有 effects；
  卡左边缘 x=16 行内若无描边像素 = 无 stroke。
- ⚠️ **`align-items:center` + `min-height` 的组合会静默把文字墨迹整体推低**：本页 `.rule__wrap{min-height:24px;align-items:center}` 让 11px 文字的行框在 24 高盒里居中，
  墨迹下沉 3.5px；**改 line-height 几乎没用**（盒子居中 + 行框内居中的两项互相抵消），必须让容器 `align-items:flex-start` 且高度由内容决定。
  探针只测盒子、量不到这种墨迹偏移，**只能靠像素对账发现**（本页 `cmp-序号12…` 未命中从 6 → 3 就是这一处）。
- ⚠️ **Figma `stroke{align:center}` 落地成 `box-shadow: 0 0 0 1px`（ring）会把可见描边行外移 1px**：设计描边跨边（392/393 两行各半），ring 只占 392 上侧一行；
  像素对账里表现为「设计带起点 392/398 未命中」而 `scan-col` 逐列颜色两侧一致 → 判为投影/AA 类，**不在 1px 上 churn**。
- **提交类交互的 toast 采样点必须在跳转前**（本页 phase3 于点击后 900ms 采样，1.5s 后 uni 会收起 toast；落地页自己的取数 toast 也会覆盖它）。
- **落地页的 fixture 也算本页的测量面**：提交成功 → `/pages/quotes/index` 会取 `GET /api/v1/quotes`，缺 fixture 时落地页弹错误 toast 并让「提交成功」证据失真 → 一并补进该页 mock 目录。
- **本轮新增脚本**：`shot-12.sh`（430×1027 整页截图）· `append-12-note.py`（台账第 12 行回写，走文件避免引号转义问题）。

### 5.9 本轮（13:55 轮 · 序号 12-v1）新增的工具与口径

- **读 design.json（原始，非 tree）里某节点的完整 JSON**：`python .agents/state/raw-node.py <pageId> <idPrefix> ...`
  —— `node-by-id.py` 打的是 tree 且值截断（220 字符），判「设计到底声明了什么」的最终依据用这个
  （本轮靠它确认「空态说明」与「须知条目」两处 12px 文本的声明**完全一样**：fs12 / lineHeight 1.2 / fit_content，只有 width 不同）。
- **PNG 尺寸**：`python .agents/state/png-size.py <a.png> [b.png]`（读 IHDR，比开图快）。
- ⚠️ **同一页里同字号文本可以有不同行盒，且都从 PNG 反推**：page-26 实测 11px 文本行盒 **16.5**（字数提示盒 330..346.5，用 13.2 会把分隔线拉到 359 而非 362.5）、
  12px 空态说明 **14.4**（空态盒 164.4 反证）、12px 须知条目 **18**（条目3 两行 36；用 14.4 只给 26 行墨迹而实测 31 行）。
  → **不要用「1.2 还是 1.5」一刀切**：先量「该节点所在盒子的边界」再定行盒；同一页出现两套口径时**各按实测落地并登记 `designLiteralDiff`**（不统一、也不照抄）。
- ⚠️ **判「卡片上下边界」的容差链**：卡片带 `drop_shadow(0,4,16)` 时，卡与卡之间 16px 间隙会被两张卡的投影同时染色 →
  `png-rowclass`（白占比阈值）比 `png-rows`（同色带）稳，但两者都会把 AA/阴影首行并入相邻段；**定卡边界要用「卡内避文字的列」做 `scan-col` 并容忍 ±1**。
- ⚠️ **`declared()` 的用途**：本轮用它把「设计 stroke 只能用 ring 表达」写成**反向断言**（`declared('.input-box','border') === null`），
  比只断言 ring 更硬 —— 既锁住现值，也锁住「别再用 border 实现中心描边」。
- ⚠️ **红基线要跑两遍（探针版本必须与绿一致）**：先建立探针 → 立刻用 `git stash push -- <源码文件>` + `build:h5` 跑红（两轮），
  再 `git stash pop` + `build:h5` 跑绿（两轮）。本轮因此发现**探针初版自身 8 条期望值 bug**（nav.back.top 48→51、counter 行盒 13.2→16.5、
  counter.right 382→398、pill.right 382→384、qno.box.top 404→406、hint 盒高 18→24、card2 高 287→291、若干容差）——
  若不重跑，红基线数字（53）里混着探针 bug，红/绿不同版探针也失去意义（重跑后红 45 全为页面缺陷）。
- ⚠️ **累计位移要拆开表述**：本页「卡2 以下整体 +3~4px」**唯一来源**是提示卡文案在设计稿里一行、浏览器 CJK 必然两行（盒 46 vs 42.5）；
  因此 `page.cardHeights`/`docHeight`/`bar.top`/`notice.rowTops` 的绝对 want 只能给容差 2→4，
  同时**补三条相对断言**（`page.gap12`/`gap23`/`gapToBar` = 16/16/20，容差 1）—— 相对断言不受累计取整影响，才是真的有牙齿。
- **截面断言 vs 墨迹断言**：本页 `chkR('.hint@@0', 24)` 这类「容器 pad-top + 行盒」的合计必须**算在一起**（6 + 18），
  只断行盒会漏掉 padding（此前轮次也踩过同一坑）。
- **本轮新增脚本**：`shot-12v1.sh`（430×1241 整页截图）· `gen-12v1-checks-evidence.py`（红/绿/交互三段转录合成，含两轮一致性 + serve 实收请求行）·
  `raw-node.py` / `png-size.py`（已在上一节说明）。
- **共用组件帧的连带影响必须显式登记**：`QuoteFormView.vue` 由 12-v2 帧与 12-v1 共用 → 本轮改样式同时作用于 page-apikey 帧；
  已核对 page-apikey 的卡/栏 effects 与本帧一致（0,4,16,.06 ×2 + 0,-4,16,.05，无冲突），但**标签行行盒 −0.5 会让该帧卡高微移**，写在台账备注里留给 12-v2 轮按本帧 PNG 重锚。

- 2026-09-16 13:5x（cron 轮 `aap-tdd-run-20260916-1330`）· **队列 8 第 12 页：序号 12「报价预览与提交 2」载体页补「设计期望值 checks」维度（126 条 · 偏差 10→0）+ 7 类设计偏差修复 + 整页对齐设计帧 1027（像素对账 55 命中 / 3 未命中）**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-12-2`（layer_id `55b40659-f198-4a04-b36b-ce699c55c75d`）→ `design.json` sha256 `20f0f362…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-quote-preview.html` 由 241 行旧体例重写为 **430 宽 iframe + 126 条 checks**（构建脚本 `build-probe-12.py`，三段骨架取自 `__measure-model-pricing.html`）；
     红基线（修复前源码 + 同一份探针两轮）**10/126**（`red-序号12-checks-设计期望值偏差.txt`）→ 绿 **0/126**（`green-序号12-checks-设计期望值.txt`）；
     两轮独立测量 **24/24 字段全等**；`docScrollHeight 1027` = 设计帧高；单测红 4 failed → 全量 **1178/1178 ×2**。
  ③**7 类偏差清单**见台账序号 12 行 / 报告 §3：逐卡卡片效果 · 基础价行 34→38（标签 12→16）· 规则行 40/44 分行高（新增 `RuleKind`）·
     请求规则行文字行框 13.2 · `.rule__wrap` 去 `min-height+center`（墨迹 −3.5px）· 确认行 22→19 · 提示条 53→56。
  ④**本页定标**（PNG 实测）：导航 96 · 卡 108/392/624/800（高 273/221/165/127）· 头行 26 · 基础价行 38（声明 16+22）· 规则行 = 10 + max(图标盒, 文本行框) + 10 ·
     **请求规则行内容 20 → 40**（设计该行图标 `width=fit_content`）· 确认行 19.2 · 提示条 10 + n×18 + 10 · 操作条 84。
  ⑤**像素对账**：`cmp-bands-6`（±3）**命中 55 / 未命中 3**（修前 52/6）；未命中 3 条逐条判读 = 卡1→卡2 投影带的逐行主色归一化差（`scan-col x=20 388..396` 两侧同为 `rgb(245,247,249)`）+ 提交按钮文案底缘 AA 的 1 行带阈值效应 → 非页面缺陷。
  ⑥**交互相有牙齿**：`?scenario=actions` 两轮逐字节相同 —— 取消勾选后提交 → toast「请先确认报价条款」· hash 不变 · **零写请求**；重新勾选 → 真实 `POST /api/v1/quotes/q7/submit`（body 为空）→ toast「已提交审核」→ `#/pages/quotes/index`（列表渲染）；
     纯测量轮两轮各只 1 行请求。**fixture 缺口先红后绿**：补 `api-12/v1/quotes/index`（落地页取数，缺则 404 且错误 toast 盖掉提交成功 toast）。
  ⑦**质量门**：`npm test` 1178/1178 ×2 · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含本轮设计值）· `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api-12` 本页三条 PASS。
  ⑧**下轮开工第一件事**：队列 8 的 **序号 12-v1**（`page-26`「新增报价单-初始态」→ `/pages/quote-form/index`，载体页 `__measure-quote-form.html`，mock 目录 `api-12-v1`）。

- 2026-09-16 14:1x（cron 轮 `aap-tdd-run-20260916-1355`）· **队列 8 第 13 页：序号 12-v1「新增报价单-初始态」载体页补「设计期望值 checks」维度（286 条 · 偏差 45→0）+ 7 类设计偏差修复（6 处 effects 投影 / 4 处 center 描边 border→ring / 13 处图标盒按设计图层）+ 整页对齐设计帧 1238（像素对账 60 命中 / 11 未命中）**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-26`（layer_id `e9214640-519e-4671-a23e-ac03e92add54`）→ `design.json` sha256 `2e8d879b…` **逐字节相同**（无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-quote-form.html` 由 277 行旧体例重写为 **430 宽 iframe + 286 条 checks**
     （want = `design.tree.json` 声明值 + 设计 PNG 430×1238 像素实测；两类来源口径写进探针头部注释）；
     红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**45/286** → 绿 **0/286**；两轮独立测量 **28/28 字段全等**；
     `docScrollHeight 1241`（= 设计 1238 + 提示卡 CJK 换行 3）· 溢出 0 · 文案缺失 0。
  ③**修掉 7 类偏差**（清单见 `evidence/review-序号12v1-checks-报告.md` §3）：6 处 effects 投影（4 卡/条 + 保存按钮）· 4 处 center 描边 `border`→ring ·
     13 处图标盒（盒 = 声明宽 × 字号1.5，形状入 `::before`）+ 返回/帮助圆角 50%→18px · 须知卡标题图标行盒 27→24 ·
     须知条目文案行盒 14.4→18（PNG 实测两行 36）· 模型 chip 文案 10px/600→11px/500 · 标签行行盒 18→17.5。
  ④**本页定标**：图标字形行盒 = 字号 × 1.5（四处交叉验证：底栏 fs13→19.5 使底栏恰 117.5 · 卡3 标题 fs16→24 使卡3 恰 156 · 提示卡 fs15→22.5 使卡高 42.5 · nav fs18→27）·
     文本行盒 11px→**16.5** / 12px 空态说明→**14.4** / 12px 须知条目→**18**（设计自身两套口径，各按 PNG 实测落地并登记）；
     卡高：步骤卡 65 · 卡1 425.5 · 卡2 287.5 · 卡3 156 · 底栏 117.5 = 12 + 19.5 + 10 + 48 + 28。
  ⑤**像素对账**：`cmp-bands-6`（±3）**命中 60 / 未命中 11**；未命中逐条 `scan-col` 判读 —— 3 条在卡片投影**渐变**上（Figma/Chrome 阴影衰减步长差）·
     8 条全落在**卡2 以下**（+3~4，唯一来源 = 提示卡文案「带出的模型数量与凭证权限相关…」设计稿一行、浏览器 CJK 必然两行，盒 46 vs 42.5）→ 已 `designLiteralDiff` 登记，不在 1–4px 上 churn。
  ⑥**交互相有牙齿**：`?scenario=actions` 两轮逐字段相同 + serve 实收请求行**逐字节相同**（7 行/轮）——
     首屏**零请求**（guard 证明）· 点选择框 `GET /credentials` → 选 c1 `GET /credentials/c1` → chip「已选 1 / 2」+ 2 行模型 ·
     填名称「12/30」→ 保存并继续 → 真实 `POST /quotes`（body `{name, credential_id}`）+ `POST /quotes/q9/items` → toast「保存成功」→ `#/pages/model-pricing/index?quoteId=q9` 落地页渲染。
     **fixture 缺口先红后绿**：补 `api-12-v1/v1/quotes/q9/items`（落地页取数，缺则 404 且错误 toast 盖掉成功 toast）。
  ⑦**质量门**：`npm test` **1178/1178 · 72 files 连跑两轮**（14:08 / 14:13）· `type-check` exit 0 · `build:mp-weixin` DONE（组件 wxss 含本轮设计值：ring ×4/×1/×1 · 投影 ×4 ·
     `width:29px;height:39px` · `height:22.5px` ×2 · `line-height:17.5px` ×2 · `line-height:18px` ×5）· `build:h5` DONE · `review-artifacts` 22/22 ·
     截图 `logs/screenshots/20260916-1412-序12v1-新增报价单初始态-checks轮-h5-430宽.png`（430×1241）。
  ⑧**探针自身 8 条期望值 bug** 已修正并留证（见 §5.9 与报告 §5）；**共用组件连带**：`QuoteFormView.vue` 同批改动也作用于 12-v2 帧（page-apikey 的卡/栏 effects 与本帧一致，
     无冲突；标签行行盒 −0.5 会让该帧卡高微移，留给 12-v2 轮按本帧 PNG 重锚）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 12-v2**（`page-apikey`「新增报价单-APIKey下拉展开」→ `/pages/quote-form/apikey`，
     载体页需扩 `__measure-quote-form.html`（iframe src 切 `#/pages/quote-form/apikey`）或另立 `__measure-quote-apikey.html`，mock 目录 `api-12-v2`）。

### 5.10 本轮（14:20 轮 · 序号 12-v2）新增的工具与口径

- **按页组装 checks 探针（第三例）**：`python .agents/state/build-probe-12v2.py`
  —— 从 `__measure-quote-form.html`（**同一页/同一共用组件**的 12-v1 载体页）切三段骨架
  （`var f = …` 顶部作用域 / `function collect(doc, win, withChecks) {` … `/* ============ 溢出` helpers / 溢出统计），逐字节复用；
  ⚠️ 三段切片的边界：`i_checks` 必须用 `/* ===================== 整页` 这类**不带半角括号的锚**（原文件的注释是全角括号 `（设计帧 …）`）。
- ⚠️ **D5 下「字形颜色」不在元素的 `color` 上**：图标一律是 CSS 占位形状，颜色落在 `::before` 的 `border-color` / `background`。
  探针直接 `getComputedStyle(el).color` 会得到 `rgb(0, 0, 0)` → 误判成页面缺陷（本轮踩到 2 条）。
  正解：`getComputedStyle(el, '::before')[prop]`，本页封装成 `pseudoStyle()` / `chkP()`。
- ⚠️ **断「容器 gap」前先确认那个容器真的是横排组**：组件里 `.nav__titles` 是**竖排**的标题块（组件把返回按钮与标题块并排，
  没有单独的「左侧组」节点）→ 断 `columnGap` 永远得 `normal`。横排间距改为断「后者的 x − 前者的 right」。
- ⚠️ **同一页里同字号文本可以有两套行盒，且「设计显式 height」优先于任何倍数**：page-apikey 的三个选项副行节点都显式 h16
  （同页 11px 另有走 1.2 的 13.2）；用 13.2 时选项信息 32.2 < 图标盒 34 → 行高被图标盒接管 → 每行 54（设计 55）、面板短 3px。
  **做法**：给这类「显式 height」建常量（本页 `CRED_SUB_LINE_BOX = 16`）并把它绑到模板的内联 `lineHeight` 上
  —— 只改 CSS 类会被内联样式覆盖（本轮先踩到）。判据链：PNG 逐行取色定出「盒边界」→ 反推行盒 → 再写进常量注释。
- ⚠️ **面板/卡片这类「整块由若干行拼成」的盒子，容差要能抓住 1 行高差**：`panel.h` 的 want 226（设计 225.5）配 tol 2，
  才能在「选项行 54」时红；tol 3 会静默放过（本轮把 tol 从 3 收到 2 后才成为有效断言）。
- **落地页在别轮被实现后，旧备注会变成假口径**：本页原备注写「/pages/settings/index（序号 23）未实现 → hash 不变」，
  本轮实测该页**已实现且注册在 pages.json**。复核任何「落点 hash 不变」的旧结论前，先查 `src/pages.json` 与产物；
  载体页的相序也要随之拆开（一个相里既跳走又想继续点原页元素 = 后续相全 `NOT_FOUND`）。
  本轮拆成 `?scenario=actions`（线性到底）与 `?scenario=settings`（落点核对）两个场景，各自两轮取证。
- **本轮新增脚本**：`shot-12v2.sh`（430×1129 整页截图）· `gen-12v2-checks-evidence.py`（红/绿/交互/落点四段转录合成）·
  `append-12v2-note.py`（台账第 12-v2 行回写）· `append-12v2-state.py`（本文件回写）· `show-ledger-cols.py`（写回前核列位）·
  `list-not-verified.py`（按状态列列未完成行）· `show-ledger-cols.py`。

- 2026-09-16 14:5x（cron 轮 `aap-tdd-run-20260916-1420`）· **队列 8 第 14 页：序号 12-v2「新增报价单-APIKey 下拉展开」载体页补「设计期望值 checks」维度（272 条 · 偏差 6→0）+ 6 类设计偏差修复（展开态文案色 / 面板 ring+投影 / 选项行宽 354 / 图标盒 17×22.5 / 选项行高 55 / 标签行盒 17）**：
  ①**设计帧重抓（人工指令 C）**：重抓 `page-apikey`（layer_id `c861ae72-865c-42b6-b314-bef4da1b2277`）→ `design.json` sha256 `29a2c80f…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ②**TDD 红→绿（本轮主交付）**：**新建** `__measure-quote-apikey.html`（430 宽 iframe + 272 条 checks，构建脚本 `build-probe-12v2.py` 切 12-v1 骨架）；
  红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**6/272** · `docH 1126` → 绿 **0/272** · `docH 1127`（设计 1128）；两轮独立测量 **35/35 字段全等**；`git stash pop` 后重建复跑同值。
  ③**修 6 类偏差**（清单见台账序号 12-v2 行 / `evidence/review-序号12v2-checks-报告.md` §3）：展开态占位文案色 #CBD5E1→#94A3B8（加 `.select--open` 作用域，不动 12-v1）·
  面板描边 `border`→ring 并补设计 effects `0 0 0 .8px #2563EB, 0 12px 24px rgba(15,23,42,.1)` · 选项行宽 352→354（x 38）·
  图标盒 13×13→17×22.5（形状入 ::before/::after，加号两笔用两层渐变）· 选项行高 54→55（新增 `CRED_SUB_LINE_BOX = 16` + `.panel__title` line-height 19）· 标签行盒 17.5→17（两帧共用）。
  ④**本页定标**：面板 = 6 + 3×选项行 55 + (4+1 分隔线) + (4 + 8+22.5+8 底部操作) + 6 ≈ 225.5；选项行 = 10 + max(图标盒 34, 名称行 19 + 副行 16) + 10；
  卡1 = 118..748（630）· 卡2 = 764..990.4（226.4 = 16+20+16+158.4+16）· 底栏 1010.4..1128（117.5）· 页高 1128（PNG 1129 行）。
  ⑤**共用组件回归门**：12-v1 同帧（`__measure-quote-form.html`）复跑 **286 条 0 失败**，`docH 1241→1240`（标签行 17.5→17 的预期结果；与设计 1238 的差仍是提示卡 CJK 换行的既有残差）。
  ⑥**交互相有牙齿（三场景）**：`?scenario=actions` 两轮 7 行请求逐字节相同（选 c2 → 重开验选中行 #EFF6FF + 对勾 `cred-check-c2` → 收起 → 名称 12/30 → 真实 `POST /quotes{name,credential_id}` + `POST /quotes/q9/items` → toast「保存成功」→ `#/pages/model-pricing/index?quoteId=q9` 落地页渲染）；
  `?scenario=settings` 两轮 2 行 → **`#/pages/settings/index` 已实现并渲染**（标题「账号与设置」）；纯测量轮 1 行（仅首屏 `GET /credentials`）。
  **旧台账口径改正**：原备注③⑦的「序号 23 未实现 → hash 不变」作废；并给 `api-12-v2` 补 `v1/auth/me` fixture（否则落地页弹「数据加载失败」盖住落点证据）。
  ⑦**质量门**：`npm test` **1178/1178 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（组件 wxss 含本轮设计值）· `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api-12-v2` **7/7 PASS**；
  像素对账 **54 命中 / 4 未命中**（判读见表）· 截图 `logs/screenshots/20260916-序12v2-新增报价单APIKey下拉展开-checks轮-h5-430宽.png`（430×1129）。
  ⑧**探针自身 3 处口径 bug** 已修（见 §5.10）：nav.left.gap 断错容器 · 字形颜色读元素 `color`（D5 占位形状）· 面板首行选中态属设计帧矛盾。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 12-v3**（`page-29`「新增报价单-保存成功」→ `/pages/quote-form/success`，载体页 `__measure-quote-success.html`，mock `api-12-v3`）；其后 15 / 20 / 21 / 22 / 23。

### 5.11 本轮（14:45 轮 · 序号 12-v3）新增的工具与口径

- **设计节点全字段 dump**：`python .agents/state/dump-layout.py <page-id> [--match 子串] [--depth N]`
  —— 打印全树每节点的 layout/`gap`/padding/宽高/圆角/fills/stroke/**effects**/fontSize/fontFamily/**lineHeight**/文案；
  `tree-view.py` **不打印 `gap` 与 `lineHeight`**（本页要断「顶部左侧 gap12」「密钥行 gap8 vs 单号行 gap4」「11px 行盒」就靠它）。
- **按页组装 checks 探针（第四例）**：`python .agents/state/build-probe-12v3.py`（从 `__measure-quote-apikey.html` 切四段骨架：
  顶部作用域 / `collect()` helpers / 溢出统计 / `sink+phase+点击工具`）。
  ⚠️ 溢出统计的切片终点必须是 `find("/* ===================== 整页", i_over)` —— 用 `function sink(` 当终点会把上一页的 checks + return 一并切进来。
  ⚠️ 本页 NEED_TEXT/CARDS 必须写在**溢出统计之前**（切片顺序：top + preamble + 本页 PRELUDE + overflow + 本页 CHECKS + return + tail + main）。
- ⚠️ **载体页里不要放可见的说明元素**（本轮首版加了一个 `#note` div，整页截图被它整体下移 ~20px，像素对账 40 条假未命中）；
  说明一律写进 HTML 注释。判据：实现截图的带起点列表比设计整体偏一个常量 → 先查 iframe 之前有没有渲染元素。
- ⚠️ **`show-checks.py` 只认扁平单段文件**；多相（phase1..N）载体页要用 `show-phases.py <run.json> [out.txt]`（本轮踩到：show-checks 报 `checkCount=None`）。
- ⚠️ **`review-measure.sh` 的 requests 证据偶发 0 行**（serve 日志在 kill 前未刷新完）→ 该轮重跑一次；两轮必须 `diff` 逐字节相同才算证据。
- **本页定标（供同族「成功/结果页」复用）**：图标字形行盒 = 字号 × 1.5（三条交叉验证：单号行 fs13→19.5 使卡2 恰 249.5 ·
  卡3 标题行 fs16→24 使卡3 恰 132 · 提示卡 fs16→24 使提示卡恰 48）；13px 文本行盒 18（卡2 五行算术自洽）；
  15px 标题行盒 20（卡2 高 249.5 反推）；11px 走显式 height（单号标签 15）或 13.2（提示卡文案，单行）；
  三张卡 effects 同值且**无 stroke** → 只能 `box-shadow`；**同一页里两处相邻元素间距可以不同**（密钥信息 gap8 / 单号值行 gap4）—— 探针要分别断言。
- **本轮新增脚本**：`dump-layout.py` · `build-probe-12v3.py` · `shot-12v3.sh`（430×1018 整页截图）· `gen-12v3-checks-evidence.py`（红/绿/四出口/请求行合成）·
  `append-12v3-checks-note.py`（台账回写）· `append-12v3-state.py`（本文件回写）。

- 2026-09-16 15:2x（cron 轮 `aap-tdd-run-20260916-1505`）· **队列 8 第 16 页：序号 15「【合同与通知】合同签署 2」载体页补「设计期望值 checks」维度（239 条 · 偏差 5→0）+ 5 类设计偏差修复（含像素对账抓出的提示卡文案行盒）**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-15-2`（layer_id `14d79713-8314-41a4-a8df-b4aff9ecd7b8`）→
  `design.json` sha256 `ca94e93e…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-contract.html` 由 297 行旧体例（无 checks）重写为 **430 宽 iframe + 239 条 checks**
  （want = `page-15-2` design.tree.json 声明值 + design.json 的 effects/stroke + 设计 PNG 430×1231 色带/墨迹实测）；
  红-1（239 条，want 全按声明值）**5/239** → 修正探针自身 4 条期望值 bug → 红-2（把 `tip.text.lh` 的 want 按 PNG 改为 16）**1/239** →
  绿 **0/239**；每阶段两轮独立测量全等（绿轮 37/37 字段全等，不一致 0）；`docH 1231` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 5 类偏差**（清单见台账序号 15 行 / `evidence/review-序号15-checks-报告.md` §3）：①合同状态卡投影改回设计 effects
  `drop_shadow(0,6,20,rgba(15,23,42,.06))`（旧备注「设计树读不到投影参数」作废）②状态图标字形补 **26×36** 行盒（fs24×1.5）③
  待签署标文字 `line-height` 22→**13.2**（设计 1.2）④下载 PDF 按钮描边 ring 0.8→**1px**（设计 `stroke{thickness:1}`）⑤
  **提示卡文案行盒 13.2→16**（**像素对账抓出**：设计墨迹 221..232 vs 修前实现 219..230）。
  ④**本页定标**：图标字形行盒 = 字号×1.5（fs24→26×36 · fs18→20×27，5 处交叉一致）；文本行盒**显式 height 优先**，无显式 height 的
  11px 用 PNG 实测 16（期限行/记录时间/提示卡文案三处自洽）；`stroke{thickness:1}` → `box-shadow: 0 0 0 1px`；`effects.drop_shadow` → `box-shadow`。
  ⑤**像素对账**：`cmp-bands-6`（±3）内容列 35/38 + 条列 17/17 = **52 命中 / 3 未命中**，位移中位 +1（无整体平移）；
  3 条未命中逐条判读 = 设计导出图提示卡顶部 207..217 整行均匀 `rgb(252..254)` 的软染色（实现纯白），差 1~3/255 → **非页面缺陷**。
  `text-rows.py` 26 行文本带：16 行区间完全相同、其余 ±1（H5 回退字体墨迹上下沿），已无 2px 差。
  ⑥**交互相有牙齿（三出口，各两轮逐字节相同）**：`?scenario=pdf` → `GET /contracts/c1/file` 后 **真下载 `GET /files/CT-2024-0613-008.pdf` 200**、无 toast；
  `?scenario=sign` → uni-modal「确认签署 / 确认对当前合同发起签署？」→ **真实 `POST /contracts/c1/sign`（body 空）** → toast「签署申请已提交」→ 重载；
  `?scenario=back` → `navigateBack`（栈内无上一页 → hash 不变 + 零额外请求，栈内返回由 `contract-flow.spec.ts` 断言）；纯测量轮只 1 行请求。
  **fixture 体检补齐**：`check-mock-fixtures.py` 新补 3 条 api-15 检查（`GET /contracts/c1` / `GET /contracts/c1/file` / `POST /contracts/c1/sign`）→ `--mock api-15` FAIL 0。
  ⑦**质量门**：`npm test` **1178/1178 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（`pages/contract/index.{js,json,wxml,wxss}`，wxss 含本轮设计值）·
  `build:h5` DONE · `review-artifacts` 22/22 · 截图 `logs/screenshots/20260916-序15-合同签署-checks轮-h5-430宽.png`（430×1231 = 设计尺寸）。
  ⑧**工具侧修正**：`check-mock-fixtures.py` 的 `--mock <dir>` 变体前缀回退原写成「只要以 base- 开头就算变体」→ `api-15` 被误判成 `api` 变体、
  一次报 8 条无关 FAIL；收窄为只对 `*-tmp-*` 生效 + 零匹配时打印 WARN（`api-tmp-*` 变体回退实测仍有效）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 20**（`page-20-2`「【合同与通知】站内信列表 2」→ `/pages/messages/index`，载体页 `__measure-messages.html`，mock `api-20`）。

### 5.12 本轮（15:05 轮 · 序号 15）新增的工具与口径

- **按页组装 checks 探针（第五例）**：`python .agents/state/build-probe-15.py`（从 `__measure-quote-success.html` 切四段骨架；
  tail 与 main 的切点用 `async function main() {`，因为 12-v3 载体页里已没有旧版 `/** uni-app H5 的 <input>` 注释 —— 用旧锚会 SystemExit）。
- **文本行带逐行对账**：`python .agents/state/cmp-textrows.py <design.txt> <impl.txt>`（`text-rows.py` 两次输出喂进来，
  打印「区间完全相同的行数 + 每行起点差」；比手工对数省事，也避免把「上下沿差 1px」误读成「整体平移」）。
- ⚠️ **探针两处口径坑**（本轮踩到并修正，会记到页面账上）：
  ①`chkStrs` 收到的是 `css()` 归一化后的值（`'16px'` → 数值 `16`）→ want 必须写数值，写 `'16px'` 必假失败；
  ②设计里「容器 + padding-left」的结构，实现常把 padding 挂在**后一个元素自身**（`status__content` / `record__body` / `nav__title` / `tip__text`）
  → 断「后元素盒子左 − 前元素右 = 12」必得 0；正解 = 断**墨迹左界** = 盒子左 + 该元素 paddingLeft。
- ⚠️ **11px 文本的行盒要看「它属于哪一类」**：同帧里 `h16`（期限行/记录时间，显式 height）与提示卡文案（PNG 反推 16）一致，
  而 `nav__no`（居中行内）走 13.2 无碍 —— **只看设计树 `lineHeight 1.2` 会漏掉顶对齐的那一处 2px 墨迹偏移**（探针量不到，只有像素对账能抓）。
- **本轮新增脚本**：`shot-15.sh`（430×1231 整页截图）· `gen-15-checks-evidence.py`（红/绿/三出口/像素对账合成）·
  `append-15-checks-note.py`（台账回写）· `append-15-state.py`（本文件回写）· `cmp-textrows.py`。
- **本页定标（供同族「详情 + 底栏双按钮」页复用）**：顶栏 96（48 + 字形行盒 36 + 12）· 内容区 padding 12/16/0/16 + 卡距 12 ·
  字段卡 = 20 + 标题 20 + 16 + n×18 + (n−1)×12 + 20 · 记录卡条目 34（18 + 16）· 底栏 84（12 + 48 + 24）+ 外包裹 padding-top 16 ·
  底栏双按钮 = 固定 126（ghost, ring 1px #CBD5E1）+ 12 间距 + fill_container（primary #2563EB）。

- 2026-09-16 15:4x（cron 轮 `aap-tdd-run-20260916-1525`）· **队列 8 第 17 页：序号 20「【合同与通知】站内信列表 2」载体页补「设计期望值 checks」维度（148 条 · 偏差 14→0）+ 5 类设计偏差修复 + 像素对账 26 命中 / 0 未命中**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-20-2`（layer_id `76700922-02b2-45f3-9343-256eb34bace0`）→
  `design.json` sha256 `02600c1b…` **逐字节相同**；设计 PNG 重下载 sha256 `b1398fdd…` 与建页时同（430×760）→ 无漂移。
  ②**TDD 红→绿（本轮主交付）**：`__measure-messages.html` 由 292 行旧体例（只报文案/溢出）重写为 **430 宽 iframe + 148 条设计期望值 checks**
  （want = `page-20-2` design.tree.json 声明值 + `dump-layout.py`/`text-fields.py` 全字段 + 设计 PNG 430×760 色带/墨迹实测）；
  红基线（源码未改 + 同一份探针两轮）**14/144**（`evidence/red-序号20-checks-设计期望值偏差.txt`，两轮逐条相同）→ 绿 **0/148**
  （`evidence/green-序号20-checks-设计期望值.txt`）；两轮独立测量 **30/30 字段全等**；`docH 760` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 5 类页面偏差**（清单见台账序号 20 行 / `evidence/review-序号20-checks-报告.md` §3）：未读胶囊文本行盒 14→**13.2** ·
  「全部已读」文本行盒 15→**14.4** · chip 文本行盒 15→**14.4**（三处均为设计 `lineHeight 1.2`）· **卡图标新增 22×30 字形盒**
  （设计字形层 `ca015b92` fs20 remixicon **声明 w22**、字形行盒 = 字号×1.5 = 30；形状 17×17 画在盒内）·
  **TabBar 高亮字重逐帧**（page-20-2 四行文本**全为 SourceHanSans-Regular**，而 page-21-2 高亮项是 SemiBold →
  共享组件新增 `activeWeight` prop（默认 600 = 21-2，本帧传 400），CSS 不再写死 `font-weight`）。
  ④**红基线分诊（2 处探针自身 bug + 1 处测量面过期，均未记到页面账上）**：
  `card.contentRow*`/`card.timeRow*` 我把「文本行盒 18/16」当成容器盒写 want —— 设计是「容器 padding-top 4 + 文本行」两层 →
  容器盒 = **22 / 20**（已改为该值，另补 `card.contentBox*`/`card.timeBox*` 直接断言文本盒，与 PNG 墨迹 193..205 / 214..224 互证）；
  `filters.chipX/W` 设计声明文本宽 25（chip 49）而 H5 回退字体 CJK 每字**恰 12** → 文本盒 24 → chip **实测 48**、第 4 枚 x 190→**187**
  （want 改为链算值并登记残差，**不写死 49**）；`card.times`/`missingTexts` 的「10 分钟前」漂成「13 分钟前」= **测量面过期**：
  mock 时间戳是绝对值而设计写的是相对时间（08:11 复核轮就因此报过两条假缺陷）→ 新增 `refresh-notification-mock.py`（按 `formatMessageTime`
  同规则把 5 条时间重置为「相对现在」），**测量前必跑**。
  ⑤**本页定标**：图标字形盒 = 声明宽 × 字号×1.5（卡图标 fs20→22×30 · 全部已读 fs16→18×24）；文本行盒**显式 height 优先**（摘要 18 / 时间 16），
  无显式 height 走设计 `lineHeight 1.2`（12→14.4 · 11→13.2），只有「标题行 18」「导航内容行 26」取 PNG 实测；
  「容器 padding-top N + 文本行」容器盒 = N + 行盒；`stroke{align:center,thickness:1}` → `box-shadow: 0 0 0 1px #EEF2F7`（本页 5 卡无 drop_shadow）。
  ⑥**像素对账**：`cmp-bands-6`（±3）内容列 **14/14 命中** + 明细条列 **12/12 命中** = **26 命中 / 0 未命中**；位移中位 +1；
  实现截图 430×760 = 设计帧尺寸（`evidence/cmp-序号20-设计PNGvs实现截图-结构带.txt`，脚本标题文案固定写「序号 6」属复用遗留）。
  ⑦**交互相有牙齿（四出口 + guard，各两轮 requests 逐字节相同）**：`?scenario=guard` 实收 **1 行**（点已选中 chip 不重复取数）·
  `?scenario=filter` 2 行（`GET /notifications?...&unread=true`，chipBgs [灰,蓝,灰,灰]、hash 不变）·
  `?scenario=readall` **3 条真实 `POST /notifications/n{1,2,3}/read`**（18-API 无批量接口 → 逐条，不臆造 read-all；设计无 toast 故成功不弹）·
  `?scenario=card` POST n1/read → 落 `#/pages/report/index?reportId=r1`（biz_type REPORT + biz_id r1）· `?scenario=tab` → `#/pages/workbench/index`（落地页渲染完整）。
  **fixture 补齐**：api-20 新增 `v1/reports/r1/{index,export}`、`v1/provider/profile`、`v1/usage/summary`；`check-mock-fixtures.py` 新增 5 条 api-20 check → **5 PASS / FAIL 0**。
  ⑧**质量门**：`npm test` **1181/1181 · 72 files 连跑两轮**（+3 新用例）· `type-check` exit 0 · `build:mp-weixin` DONE（`pages/messages/index.{js,json,wxml,wxss}`；
  wxss 含 `.msg__glyph-box{width:22px;height:30px}` / `.msg__glyph{width:17px;height:17px}` / `line-height:13.2px` / `line-height:14.4px` ×2）·
  `build:h5` DONE · `review-artifacts` 22/22 · **共用组件回归门**：序号 21 载体页复跑两轮 73/73 全等、`tabbarActiveStyle.fontWeight` 仍 600（默认值未变）·
  截图 `logs/screenshots/20260916-序20-站内信列表-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 21**（`page-21-2`「【工作台与我的】我的 2」→ `/pages/mine/index`，载体页 `__measure-mine.html`，mock `api-21`）。

### 5.13 本轮（15:25 轮 · 序号 20）新增的工具与口径

- **按页组装 checks 探针（第六例）**：`python .agents/state/build-probe-20.py`（从 `__measure-contract.html` 切四段骨架；本页 iframe 取数高度 = 760，
  因为页面 `min-height:100vh` 会把测量高度顶到 iframe 高 —— 760 时 `docScrollHeight` 恰等于设计帧高）。
- ⚠️ **切片坑（本轮踩到）**：`__measure-contract.html` 里 `function bgsIn` 的收尾 `}` 与 `async function main() {` **在同一行**
  （`      }      async function main() {`）→ 按行切片到 `main` 之前会把它切掉，大括号净值 +1；`node --check` 只报「Unexpected end of input」**不给行号**。
  载体页脚本里**显式补回**该 `}`，并用新增的 `python .agents/state/js-depth-lines.py <extracted.js>`（逐行大括号净值）复验净值 0。
- **相对时间 mock 重置**：`python .agents/state/refresh-notification-mock.py [--mock api-20] [--check]`
  —— 站内信列表的 5 条时间文案是**相对时间**（10 分钟前 / 2 小时前 / 昨天 18:20 / 3 天前 / 5 天前），而 mock 的 `created_at` 是绝对值 →
  不重置就会在测量时报「N 小时前」假缺陷（08:11 复核轮的 `missingTexts ['10 分钟前','2 小时前']` 即此）。**凡 mock 里带相对时间的页面，测量前必跑。**
- ⚠️ **「容器 padding-top N + 文本行」的 want 要分两层写**：容器盒 = `N + 行盒`（本页摘要 4+18=22、时间 4+16=20），
  文本盒另测（`.msg__content` 18 / `.msg__time` 16）。只写一层会把行盒当容器盒 → 自造 4 条假偏差。
- ⚠️ **逐帧差异要连"字重"一起比**：page-20-2 与 page-21-2 共用 TabBar，除高亮**色**不同（#007AFF vs #2563EB）外，高亮**字重**也不同（400 vs 600）→
  都做成 prop（`activeColor` / `activeWeight`），CSS 不再写死 `font-weight`（写死会让内联值失效且"看类名猜不出实际字重"）。
- **本轮新增脚本**：`build-probe-20.py` · `shot-20.sh`（430×760 整页截图）· `refresh-notification-mock.py` · `js-depth-lines.py`；
  `check-mock-fixtures.py` 新增 api-20 五条 check；设计 PNG 存 `.agents/state/design-shots/page-20-2.png`。

- 2026-09-16 16:0x（cron 轮 `aap-tdd-run-20260916-1545`）· **队列 8 第 18 页：序号 21「【工作台与我的】我的 2」载体页补「设计期望值 checks」维度（230 条 · 偏差 17→0）+ 10 类设计偏差修复 + 像素对账 29 命中 / 0 未命中**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-21-2`（layer_id `e537204e-faf7-416b-8669-1347d581490c`）→
  `design.json` sha256 `cd12a92b…` **逐字节相同**（`cmp` 无差异）；设计 PNG 重下载 sha256 `d73cf39a…`（430×990）→ 无漂移。
  ②**TDD 红→绿（本轮主交付）**：`__measure-mine.html` 由 248 行旧体例（只报文案/溢出）重写为 **430 宽 iframe + 230 条设计期望值 checks**
  （want = `page-21-2` design.tree.json 声明值 + `dump-layout.py`/`text-fields.py` 全字段 + 设计 PNG 430×990 色带/墨迹实测）；
  红基线（源码未改 + **同一份最终版探针**两轮）**17/230**（`evidence/red-序号21-checks-设计期望值偏差.txt`，两轮逐条相同）→ 绿 **0/230**
  （`evidence/green-序号21-checks-设计期望值.txt`）；两轮独立测量 **43/43 字段全等**（不一致 0）；`docH 990` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 10 类页面偏差**（清单见台账序号 21 行 / `evidence/review-序号21-checks-报告.md` §3）：①头像字形盒 16×16 → **33×45**
  （设计 `85003c7e` fs30 remixicon **声明 w33** × 行盒 30×1.5；形状头 14 + 肩 26×11 按设计字形墨迹 26×25 画在盒内）②4 处文本行盒未按设计 `lineHeight 1.2`：
  类型标签/已认证 16→**13.2** · 钱包标题 21→**16.8** · 提现文案 20→**15.6** ③行图标字形盒 16×16 → **20×27**（字形层声明 w20 + fs18 行盒 27；
  x 44→42、top 逐行 +6，与 PNG 图标墨迹 43..59 / 373..388 对齐；形状 17×16 移入 `::before`）④行标签行盒 19.5→**15.6** ⑤行值行盒 18→**14.4**
  ⑥胶囊文字行盒 14→**12** ⑦字形颜色改由伪元素承载（原 `background: currentColor` 在元素自身 → 探针读 `::before` 拿不到色）。
  ⑧`routes.ts` 两处注释口径改正（序号 22/23 落点页**已实现**）。
  ④**红基线分诊（2 条探针自身期望值 bug，已修正并重跑红基线，保证红/绿同版探针）**：
  `head.tags.top` 把「带 `padding-top: 8` 的容器」当「子行」写 want 82 → 改断容器 74 + 新增 `.head__type.top = 82`（设计是「容器 a3c59082 + 标签行」两层）；
  `entries.values` 只写 3 个值，漏了第 5 行「我的消息」的「待阅读 3」（设计 row5 确有值节点）→ 改 4 值 / 4 右边 / 4 色
  （第 4 个是设计字面量 `rgba(0,0,0,1)`，与同卡其它值 #94A3B8 不同 → 逐值断言不统一）。
  ⑤**本页定标（供同族「个人中心 / 卡片列表」页复用）**：图标字形盒 = **设计声明宽 × 字号×1.5**（头像 fs30 声明 w33 → 33×45 · 行图标 fs18 声明 w20 → 20×27 · TabBar fs22 → 33）；
  文本行盒 **显式 height 优先**（公司名 26 · 余额标签 16 · 金额 34 · 明细值 22），无显式 height 走 `lineHeight 1.2`
  （14→16.8 · 13→15.6 · 12→14.4 · 11→13.2 · 10→12）—— **同一页里 fs11 也可能有显式 h16**（余额标签）→ 逐节点判，切忌一刀切；
  卡片结构账：钱包卡 20+30+16+52+16+38+20 = **192** · 入口卡 8+5×56+3×1+8 = **299** · 证照卡 8+4×54+3×1+8 = **235** · TabBar 8+33+3+16+24 = **84**。
  ⑥**像素对账**：`cmp-bands-6`（±3）内容列 **16/16 命中** + 明细/图标列 **13/13 命中** = **29 命中 / 0 未命中**（位移中位 0 · min −2 · max +1）；
  实现截图 430×990 = 设计帧尺寸（`evidence/cmp-序号21-设计PNGvs实现截图-结构带.txt`）。
  ⑦**交互相有牙齿（六出口，各两轮）**：纯测量轮 7 行只读 GET（profile/payments/quotes/credentials/reports/contracts?status=PENDING_SIGN/notifications?unread=true）**零写请求** ·
  `?scenario=withdraw` toast「提现功能暂未开放」+ hash 不变（client-only，missing-prd）· `?scenario=rows-quotes` → `#/pages/quotes/index`（requests 逐字节相同）·
  `?scenario=usage` → `#/pages/usage/index`（渲染「用量概览」）· `?scenario=settings` → `#/pages/settings/index`（渲染「账号与设置」）·
  `?scenario=tab-workbench` → `#/pages/workbench/index`（数据台完整渲染）· `?scenario=tab-mine` hash 不变。
  ⚠️ **requests 比对口径**：首屏 7 个 GET 是 `Promise.all` 并发 → 落盘**顺序抖动**，用「**集合相等**」判一致（已逐行核对内容），确定性场景仍逐字节相同。
  **口径改正**：台账序号 21 备注⑧「用量与对账 / 账号与设置 落点页未实现 → 跳转由 uni 侧降级」**作废** —— 序号 22/23 均已实现并注册在 pages.json。
  ⑧**质量门**：`npm test` **1181/1181 · 72 files 连跑两轮**（15:56:51 / 15:57:25）· `type-check` exit 0 · `build:mp-weixin` DONE
  （`pages/mine/index.{js,json,wxml,wxss}` 齐备 + app.json 注册；wxss 含 `width:33px;height:45px` / `width:17px;height:16px` / `line-height:13.2px ×2` / `15.6px ×2` / `16.8px` / `14.4px` / `12px` / `box-shadow:0 0 0 1px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api-21` **9 PASS + 反向体检 PASS / FAIL 0**（本轮新补 9 条）·
  **共用组件回归门**（`AppTabBar` 被 page-20-2 / page-21-2 共用）：序号 20 载体页复跑 **148 条 0 失败**、两轮 30/30 全等
  （**先跑 `refresh-notification-mock.py --mock api-20` 修测量面相对时间过期** —— 未跑时那 2 条失败与本轮改动无关）·
  截图 `logs/screenshots/20260916-序21-我的页-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 22**（`page-22-2`「【工作台与我的】我的与用量概览 2」→ `/pages/usage/index`，
  载体页 `__measure-usage.html`（293 行旧体例、无 checks）→ 同本轮做法重写，mock 目录 `api-22`）。

### 5.14 本轮（15:45 轮 · 序号 21）新增的工具与口径

- **按页组装 checks 探针（第七例）**：`python .agents/state/build-probe-21.py`（从 `__measure-messages.html` 切四段骨架；
  本页 iframe 取数高度 = **990** = 设计帧高，因为页面 `min-height:100vh` 会把测量高度顶到 iframe 高 —— 990 时 `docScrollHeight` 恰等于设计帧高）。
  ⚠️ 与 §5.13 的切片坑对照：`__measure-messages.html` 里 `bgsIn` 的收尾 `}` **单独一行** → 本页无需补 `}`（净值复核仍要做：`js-depth.py`）。
- **证据合成（第七例）**：`python .agents/state/gen-21-checks-evidence.py`（红/绿两轮 + 六出口 + 共用组件回归门 → 两个转录文件）。
- **整页截图**：`bash .agents/state/shot-21.sh [文件名]`（`--window-size=430,990`；ASCII 临时名 → `cp` 中文名，Chrome 中文路径坑见 §5）。
- ⚠️ **首屏并发请求的 requests 证据不能用 `diff` 逐字节判**：`Promise.all` 的 7 个 GET 落盘顺序会抖动（同一轮两份 dump 也可能不同序）→
  用「排序后集合相等」判一致，并在转录里写明口径；**确定性场景（点击后串行发请求）仍用逐字节 diff**。
- ⚠️ **共用组件回归门遇到相对时间 mock 会假红**：序号 20 载体页的 148 条里有 `page.missingTextCount`（相对时间文案），
  时间一过就漂成「14 分钟前」→ **测量前必跑** `python .agents/state/refresh-notification-mock.py --mock api-20`（§5.13 的工具，本轮再次踩到）。
- ⚠️ **落地页被后续轮次实现后，旧台账口径会变成假缺陷**：序号 22/23 页面早已实现并注册，`?scenario=usage` / `?scenario=settings`
  实测均正常落地 → 复核「落点 hash 不变 / 降级」类旧结论前，先查 `src/pages.json` 与 `src/pages/<route>/`。
- **本轮新增脚本**：`build-probe-21.py` · `shot-21.sh` · `gen-21-checks-evidence.py` · `append-21-checks-note.py` · `append-21-state.py`；
  `check-mock-fixtures.py` 新增 9 条 api-21 check；设计 PNG 存 `.agents/state/design-shots/page-21-2.png`。

- 2026-09-16 16:3x（cron 轮 `aap-tdd-run-20260916-1605`）· **队列 8 第 19 页：序号 22「【工作台与我的】我的与用量概览 2」载体页补「设计期望值 checks」维度（267 条 · 偏差 8→0）+ 5 类设计偏差修复 + 像素对账 39 命中 / 8 未命中（2 类非页面缺陷）**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-22-2`（layer_id `8bc59233-3854-4725-b85b-bfaf4518e934`）→
  `design.json` sha256 `63d7ce0c…` **逐字节相同**；设计 PNG 重下载 sha256 `ce50a955…`（430×1138）相同 → 无漂移。
  ②**TDD 红→绿（本轮主交付）**：`__measure-usage.html` 由 293 行旧体例（只报文案/溢出）重写为 **430 宽 iframe + 267 条设计期望值 checks**
  （want = `page-22-2` design.tree.json 声明值 + `dump-layout.py`/`text-fields.py`/`raw-node.py` 全字段 + 设计 PNG 430×1138 色带/墨迹实测）；
  红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**8/267**（`evidence/red-序号22-checks-设计期望值偏差.txt`，两轮逐条相同）→ 绿 **0/267**
  （`evidence/green-序号22-checks-设计期望值.txt`）；两轮独立测量 **50/50 字段全等**（不一致 0）；`docH 1138` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 5 类页面偏差**（清单见台账序号 22 行 / `evidence/review-序号22-checks-报告.md` §2.1）：①**汇总卡 padding 20 → 20/16**
  （设计 811a53eb padding=[20,16,20,16] → 宫格 175→178.5 宽、x 36→32、标题 x 36→32，一条改动解掉 3 条 check）
  ②**补设计 effects `drop_shadow(0,6,20,rgba(15,23,42,.06))`**（该卡**无 stroke**，此前只给趋势/模型/成本/明细四卡写了 ring，汇总卡投影整体漏实现）
  ③月份日历字形盒 17×15 → **17×22.5**、下箭头字形盒 18×15 → **18×24**（= 声明宽 × 字号×1.5），并去掉下箭头形状的 `margin-bottom:3px`
  （把墨迹从中心上移 1.5px；设计墨迹中心 = 胶囊中心 66）④月份文字行盒 18 → **14.4**（设计 lineHeight 1.2 × 12）。
  ④**红基线分诊（3 条探针自身期望值 bug，已修正并重跑红基线，保证红/绿同版探针）**：
  `summary.tiles1.top/h` 把「容器（含 padding-top）」当「宫格行」（改断容器 148/88 + 新增 `tileTops [164,164,244,244]`）；
  `models.trackW` 误以为 4 行同宽（轨道是 `fill_container` → 末行「6%」百分比盒窄 7，PNG 实测行 1 为 192、行 4 为 199 → want 改 `[192,192,192,199]`）；
  `summary.shadow` want 缺 Chrome 序列化的尾随 spread `0px`（同序号 12/15 口径）。
  另把 `trend.img.src` 从「读元素 src」改为「从 uni-image innerHTML 取 data-URI → `atob` 解码回 SVG」，新增 5 条硬断言
  （viewBox `0 0 358 150` · 4 条网格线 · 7 个数据点 · 折线 `#2563EB` · 面积 `rgba(191,219,254,0.35)`）。
  ⑤**本页定标（供同族「概览 / 仪表盘」长页复用）**：图标字形盒 = 设计声明宽 × 字号×1.5
  （返回 fs24 声明 w26 → 26×36 · 日历 fs15 → 17×22.5 · 下箭头 fs16 → 18×24 · 明细列表 fs18 声明 w20 → 20×27；**chevron-right fs20 实测 22×28，非 ×1.5**）；
  文本行盒 **显式 height 优先**（标题 20 · 图例标题行 20 · 值 26 · 标签 16 · 合计值 21 · 底部 16 · 横轴 11.3），无显式 height 走 `lineHeight 1.2`（12 → 14.4）、
  模型/成本行内容取 PNG 实测 **18**；设计里「容器 padding-top N + 行」的**容器盒 = N + 行盒**（探针必须分两层写，否则自造假偏差）；
  **逐卡断言不统一**：汇总卡只有 effects、其余四卡只有 `stroke #EEF2F7`（无 effects）→ 逐卡写 want。
  卡片结构账：汇总卡 20+20+16+72+8+72+20 = **228** · 趋势卡 20+20+12+150+20 = **222** · 模型卡 20+20+16+4×18+3×12+20 = **184** ·
  成本卡 20+20+16+3×18+3×12+41+20 = **207** · 明细卡 16+28+16 = **60** · 底部说明 24+16+16+24 ≈ **80~81**（页高 1138 = 96 + 5×12 + 901 + 81）。
  ⑥**像素对账**：`cmp-bands-6`（±3）内容列 27/31 + 明细/进度列 12/16 = **39 命中 / 8 未命中**，位移中位 0（内容列 0 位移 14 个 · min −3 / max +3）；
  未命中逐条判读 = ①汇总卡**投影衰减尾**（x=200 列：设计 336..345 (238,240,243)→(243,245,247) 后 349..359 仍有 252..254 淡染、实现 348+ 纯白；
  起点/峰值两侧同值 → Figma/Chrome 模糊衰减步长差 1~3/255）②成本行右对齐值的 **H5 回退字体字距/右留白**（设计墨迹 353..391、实现 355..393，同右对齐 394、墨迹同宽 39）→ 均非页面缺陷。
  `cmp-textrows.py`：21 ↔ 21 行文本带，8 行完全相同、其余 ±1（无 2px 级位移）。
  ⑦**交互相有牙齿（三出口，各两轮 requests 逐字节相同）**：纯测量轮 1 行只读 GET · `?scenario=back` hash 不变 / 无 toast / 零写请求 / `cardCount 5`，
  并用 `windowMark=null` **证明 uni H5 无栈时降级为整页重载**（第二次 GET 同 URL，不是重复取数）· `?scenario=month` 点开真 `uni-picker`
  （`uni-picker-container uni-date-select` + `uni-picker-action-confirm`）→ 确认 → **第二次真取数 `GET /api/v1/usage/summary?month=2024-06`**（首屏 `?month=2026-09`）·
  `?scenario=detail` **no-op**（画布 30 页无明细页）：hash 不变 / 无 toast / 无新请求。**fixture 体检补齐**：`check-mock-fixtures.py` 新增 5 条 api-22 check → FAIL 0。
  ⑧**质量门**：`npm test` **1181/1181 · 72 files 连跑两轮**（16:18:51 / 16:19:28）· `type-check` exit 0 · `build:mp-weixin` DONE
  （`pages/usage/{index.js,index.json,index.wxml,index.wxss}` 齐备 + app.json 注册；wxss 含 `padding:20px 16px` / `box-shadow:0 6px 20px rgba(15,23,42,.06)` / `height:22.5px` / `height:24px` / `line-height:14.4px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · **共用消费方回归门**（序号 2 工作台同用 `usage-model.ts` 的 D3 环形/图例口径）`__measure-workbench.html` 复跑 **103 条 0 失败**（两轮 `docH 1146` 全等）·
  截图 `logs/screenshots/20260916-序22-用量概览-checks轮-h5-430宽.png`（430×1138 = 设计帧尺寸，同件入 `.agents/state/evidence/`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 23**（`page-23-2`「【工作台与我的】账号与设置 2」→ `/pages/settings/index`，
  载体页 `__measure-settings.html` → 同本轮做法重写，mock 目录 `api-23`；**做完即队列 8（20 个载体页）收尾**，
  随后回到队列 1 余下行与队列 7（uni-picker 溢出口径，本页已按同族做法排除 `uni-resize-sensor`，uni-picker 内部空 div 因父级 `overflow:hidden` 不影响 `docScrollWidth`）。

### 5.15 本轮（16:05 轮 · 序号 22）新增的工具与口径

- **按页组装 checks 探针（第八例）**：`python .agents/state/build-probe-22.py`（从 `__measure-mine.html` 切四段骨架；
  iframe 取数高度 = **1138** = 设计帧高，页面 `min-height:100vh` 会把测量高度顶到 iframe 高 → `docScrollHeight` 恰等于设计帧高）。
  ⚠️ **两处切片坑（本轮踩到并写进脚本断言）**：①`__measure-mine.html` 里 `function bgsIn` 的收尾 `}` 与 `async function main() {` **同一行** →
  按行切片会把它切掉（大括号净值 +1，`node --check` 只报「Unexpected end of input」不给行号）→ 脚本显式 `tail += "\n      }"` 并用
  `python .agents/state/js-depth-lines.py <extracted.js>` 复验净值 0；②**`pickerProbe` / `clickOverlayConfirm` 不在共享骨架里**
  （它们原本只写在旧版 `__measure-usage.html` 自己的脚本里）→ month 相直接 `ReferenceError: pickerProbe is not defined`，本页必须在主脚本里自带。
- **看某次测量某个 phase 的指定字段**：`python .agents/state/show-phase-fields.py <run.json> <phase> <field...>`
  （`show-phases.py` 打的是检查项汇总，字段级要另取；本页用它读 `windowMark` / `monthAfter`）。
- **看某个 phase 的 checkFails**：`python .agents/state/show-fails2.py <run.json> [phase]`（字段名容错版，用于 103 条旧体例探针的 FAIL 逐条）。
- ⚠️ **`review-measure.sh` 的 mock 参数必须是「仓库相对路径」**：脚本内部拼 `"$ROOT/$MOCK"`，传裸 `api` 会变成 `<root>/api` →
  **整页 404、checkFails 全假红**（本轮共用回归门首跑 19 条假失败即此；SKILL §5「every call 404s → 先怀疑自己的参数」已记该陷阱）。
  正确写法：`review-measure.sh 2-sharedgate __measure-workbench.html .agents/state/h5-measure/api 5352`。
- ⚠️ **探针 want 的两条硬口径（本轮各踩一次）**：
  ①`box-shadow` 的 want 必须带 Chrome 序列化的**尾随 spread `0px`**（`rgba(15, 23, 42, 0.06) 0px 6px 20px 0px`）；
  ②**`fill_container` 的轨道/占位宽度逐行可能不同**（本页模型轨道 192/192/192/199，因末行百分比盒更窄）→ 不要写 4 个同值。
- ⚠️ **uni-image 读不到元素 `src`**：H5 下 `uni-image` 把图塞进内部 `img`/背景图 → 探针要从 `element.innerHTML` 里取 data-URI 并
  `atob()` 解码回 SVG 再断言（本轮据此给趋势图加了 viewBox / 网格线数 / 数据点数 / 折线色 / 面积色 5 条硬断言）。
- **本页截图**：`bash .agents/state/shot-22.sh [文件名]`（`--window-size=430,1138`；ASCII 临时名 → `cp` 中文名）。
- **本轮新增脚本**：`build-probe-22.py` · `shot-22.sh` · `gen-22-checks-evidence.py` · `append-22-checks-note.py` · `append-22-state.py` ·
  `show-phase-fields.py` · `show-fails2.py`；`check-mock-fixtures.py` 新增 5 条 api-22 check；设计 PNG 存 `.agents/state/design-shots/page-22-2.png`。

- 2026-09-16 17:26（cron 轮 `aap-tdd-run-20260916-1726`）· **队列 3 自主部分：序号 12「保存并继续」落点按设计接上成功页（SUCCESS_PAGE）+ 两类载体页实测证明**：
  ①**TDD RED→GREEN**：先改两个 flow spec 文件的导航断言（模型定价页→保存成功页）+ 用例名（2 条红 → 绿）；全量 npm test **1181/1181 · 72 files 连跑两轮**（17:31:58 / 17:34:31）· type-check exit 0 · build:mp-weixin DONE（含 success 路由产物）· build:h5 DONE · review-artifacts **22/22**。
  ②**代码改动**：`src/utils/quote-form-model.ts` 新增 `SUCCESS_PAGE = '/pages/quote-form/success'`；`src/components/quote-form/QuoteFormView.vue` onSave 导航由 `MODEL_PRICING_PAGE` 改为 `SUCCESS_PAGE`（按设计：保存并继续→保存成功页，成功页内「继续设置模型报价」主按钮再进 MODEL_PRICING_PAGE，与 12-v3 实现一致）。
  ③**测量面证据（430 宽 iframe 两轮）**：12-v1 `__measure-quote-form.html` phase3 — `hashAfterSave: "#/pages/quote-form/success?quoteId=q9"` · `successRendered: true` · checkFailCount **0/286**；12-v2 `__measure-quote-apikey.html` phase4 — `hashAfterSave: "#/pages/quote-form/success?quoteId=q9"` · `successRendered: 1` · checkFailCount **0/272**；两页各两轮 BYTE-IDENTICAL（run1/run2）。
  ④**serve 实测请求链验证**：POST /quotes → POST /quotes/q9/items → GET /quotes/q9（success 页取报价单详情）→ GET /credentials/c1（success 页取凭证明细）—— 全 200，零 404。两轮逐字节相同。
  ⑤**mock 补齐**：api-12-v1 和 api-12-v2 各补 `v1/quotes/q9/index`（quote detail GET）+ api-12-v2 补 `v1/credentials/c1`（success 页落地取数）；check-mock-fixtures 两目录 FAIL 0。
  ⑥**台账更新**：12-v3 备注①「入口未接线（待拍板）」→「已确认（prompt）：保存并继续按设计接 success」；12-v1/12-v2 备注追记落地已改。
  ⑦**下轮开工第一件事**：队列 3 余下 15 条待拍板缺口（仅自主部分已执行完毕；非自主的保持原样等待人类拍板），各页 pending 项详情见 `python .agents/state/triage-pending.py`。

### 5.16 本轮（17:45 轮 · 序号 6/7 报告编号口径）新增的工具与口径

- **跨页断言核定脚本**：`python .agents/state/verify-report-no-prefix.py` —— 按**内容特征**（`DR-########-####`）
  在两帧设计树里找「报告编号」文本叶子，并对设计 PNG 量「顶部栏右侧墨迹包围盒」；输出转录
  `evidence/序号6-报告编号前缀核定.txt`。§7 的「一切以当前画布为准」要求这类跨页结论必须可复现，别靠 grep。
- **台账 CSV 体检**：`python .agents/state/validate-ledger-csv.py <file>`（逐行打印字段数，标出 ≠11 的行）。
  `normalize-ledger-eol.py` 已改为**先在内存生成完整文本 + csv 复解析校验，通过后才落盘**
  （旧版直接以 `"w"` 打开目标文件逐行写 → 中途解析报错会把已写部分留在盘上，实测把 22 行截成 6 行；本轮踩到并已修）。
- ⚠️ **往台账 CSV 追加文本的两条硬规则**：①追加进**带引号**字段（「用例(证据)」列）的文本里**不能出现 ASCII 双引号**
  —— 会提前闭合字段、把后续内容拆成新列；②追加进**不带引号**字段（序号 7 的「备注」列历史写入未加引号）的文本里
  **不能出现 ASCII 逗号**。写前先 `diag-ledger-boundary.py <序号>` 看边界形态，写完必须两条体检都过。
- ⚠️ **「设计里出现过该串」≠「设计文本含该串」**：page-6 `design.json` 里确实有 `报告编号` 字样，但那是
  **图层名**（frame `5d860a4b`），文本叶子 `202cd360` 的 content 只是 `DR-20240613-0758`。
  跨页断言前必须读**文本叶子的 content**（`text-fields.py` / `raw-node.py` / `node-by-id.py`），不要 grep 整个 design.json。
- ⚠️ **同族页的同一位置可以有两套行框口径，逐帧判**：序号 6 顶部「报告编号」是 frame **h=16**（叶子 height=fill_container）
  → 行框 16；序号 7-2 是单叶子 h=fit_content + lineHeight 1.2 → 行框 **13.2**。把一页的结论复制到另一页必错。
- **字符宽度可作独立证据**：同 fs 同字体的两串，墨迹宽之比 ≈ 字符数之比
  （page-6 95px / 15 字符 vs page-7-2 142px / 21 字符）→ 可反证「某串到底有没有前缀」，比只看设计树更硬。
- **口径锁要有牙齿的证明方式（变异测试）**：新增的「禁止型」断言（本轮的 `报告编号不带「报告编号」前缀`）
  天生是绿的 → 必须用**变异**证明：临时把被测行为改回错误形态 → 跑该用例看红 → 还原
  （`evidence/red-序号6-前缀口径锁-变异测试.txt`）。没做变异的「禁止型断言」等于没断言。
- **本轮新增脚本**：`verify-report-no-prefix.py` · `validate-ledger-csv.py` · `diag-ledger-row.py` · `diag-ledger-boundary.py` ·
  `append-6-reportno-note.py` · `append-6-reportno-state.py`；`shot-6.sh` 复用（430×5400）；设计 PNG 存
  `.agents/state/design-shots/page-6.png`（430×5342 · sha256 a505a58c…）。

- 2026-09-16 17:5x（cron 轮 `aap-tdd-run-20260916-1745`）· **序号 6/7 顶部栏「报告编号」口径核定 + 行框偏差修复（红 1+2 → 绿 0）**：
  ①**设计帧重抓（人工指令 C）**：序号 6（layer_id `0f0755e4-…`）`design.json` sha256 `08ad8ea5…` **逐字节相同**；
     序号 7-2（layer_id `47815a05-…`，首抓误用了序号 15 的 layer_id → 已纠正）sha256 `f2780416…` **逐字节相同**；
     两帧设计 PNG 重下载 sha256（`a505a58c…` / `6891e547…`）与留证一致 → **无漂移**。
  ②**核定结论（本轮主交付）**：序号 7 台账备注⑩ 的跨页断言「序号 6 也缺『报告编号』前缀、待回炉修」= **误判**。
     证据 ①设计树：page-6 叶子 `202cd360` content = `DR-20240613-0758`（w=97 · fs11）；page-7-2 叶子 `57f828cc`
     content = `报告编号 DR-20240614-0312`（w=143）。证据 ②设计 PNG 顶部栏右侧墨迹：page-6 **x318..412 w=95**（15 字符）
     vs page-7-2 **x271..412 w=142**（21 字符）。同 fs 同字体 → 差值恰是「有无前缀」之差。误判来源 =
     把 page-6 design.json 里的**图层名**「报告编号」当成文本内容。**序号 6 保持无前缀**，并加口径锁防回炉误改。
  ③**TDD 红→绿**：两页载体页各加 7 / 5 条设计声明值 checks（text / prefixAbsent·prefixPresent / h / top / right / lineHeight / fw）
     + `topbarNo` 实测留证字段。红基线（修复前源码 + 同一份最终版探针两轮）**序号 6 = 1/228**
     （`topbar.no.lineHeight: got normal want 16`）· **序号 7 = 2/201**（lineHeight normal→13.2 · h 16→13.2）→
     绿 **0/228 · 0/201**；两轮独立测量 25/25 · 31/31 字段全等（不一致 0）；docH 5343 / 1111 = 设计帧高。
  ④**修 2 处页面偏差**：`src/pages/report/index.vue` 的 `.report-page__no` 补 `line-height:16px`（design 5d860a4b frame 显式 h=16）；
     `src/pages/report-failed/index.vue` 的 `.rf-page__no` 补 `line-height:13.2px`（design 57f828cc h=fit_content · lineHeight 1.2）。
     两处都写明「逐帧不同」的理由与证据路径。
  ⑤**口径锁（变异测试证明有牙齿）**：`tests/pages/report.spec.ts` 新增「报告编号不带『报告编号』前缀」；
     临时把前缀写回模板 → 该文件 **2 failed**（新断言 + 原有精文断言）→ 还原后 17/17。
     证据 `evidence/red-序号6-前缀口径锁-变异测试.txt`。
  ⑥**像素对账**：`evidence/cmp-序号6-reportno-设计PNGvs实现截图-顶部栏.txt` —— 右区设计 x318..412 w95 y60..69 vs 实现
     x320..413 w94 y61..70（±2 横向 / +1 纵向 = 设计小数坐标 56.5 取整 + H5 回退字体墨迹，非页面缺陷）。
  ⑦**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮**（+1 新用例）· `type-check` exit 0 ·
     `build:mp-weixin` DONE（report wxss 含 `line-height:16px` · report-failed wxss 含 `line-height:13.2px`）·
     `build:h5` DONE · `review-artifacts` **22/22** · 截图 `evidence/20260916-1755-序06-检测报告-报告编号前缀核定-h5-430宽.png`（430×5400）。
  ⑧**台账回写**：序号 6 追加用例证据 + 备注⑫（核定结论与误判来源）；序号 7 备注⑩ 改写为**更正**（跨页结论作废）。
     顺带修好两个取证工具缺陷：`normalize-ledger-eol.py` 改为「内存生成 + 复解析校验后落盘」（旧版中途报错会截断台账，
     本轮实测把 22 行写成 6 行并已 `git checkout` 复原）、新增 `validate-ledger-csv.py` 逐行字段数体检。
  ⑨**下轮开工第一件事**：队列 3 余下 15 条待人类拍板缺口（自主部分已尽）——若无可自主项，则按队列 1 口径
     把「逐页复核」扩到**每页的顶部栏/导航区**这类跨页同族位置的一致性核对（本轮已示范序号 6↔7-2 的做法）。

- 2026-09-16 18:1x（cron 轮 `aap-tdd-run-20260916-1800`）· **队列 1 当前修订版全量复核（22 载体页 × 2 轮）+ 画布「全新版本」覆盖核对 + 跨页「导航标题行盒」一致性核对与修正（5 页红 1→绿 0 · 声明保真）**：
  ①**设计真源重抓（人工指令 C）**：`python E:/agent/aap-tools/recapture-all.py` → 22 帧 = **21 SAME + 1 DIFF**；唯一 DIFF = 序号 8「新建按钮」`width 97→100`
  （08:55 基线的同一差异：自动布局算得、与子节点 18+4+54+padding 自洽，实现早已按 100、台账已记）→ **无漂移**。另重抓 inventory：30 帧列表与留证**逐字节相同**（仅 `capturedAt` 变化）。
  ②**画布覆盖核对（新增 `canvas-coverage-check.py`，本轮主交付之一）**：台账 22 行的 `layer_id` + 帧名**全部仍在当前画布上**（失配 0）；当前画布 30 帧中未被台账覆盖的
  = 根容器 + **8 个管理端·PC 帧**（范围外）→ **画布上不存在未实现的报价端帧**。证据 `evidence/canvas-coverage-20260916-1800.txt`。
  ③**队列 1 全量复核（新增 `coverage-rerun.sh` + `coverage-report.py`）**：22 个载体页 × 2 轮 = **28 个相全部 `checkFailCount 0`、两轮独立测量差异字段 0**、溢出 0；
  3 个相被工具标注后逐条判读为**非回归**：序号 20 相对时间「10 分钟前」漂成 12 分钟（测量面时间偏移 → 已把 `refresh-notification-mock.py` 挪到该页测量**紧前**，并修好 `coverage-report.py` 不认扁平单段文件导致 序号 3/4 漏报的缺陷）、
  序号 4-v1 phase1 空态 2 条文案缺失（该相定义）、序号 9 phase1 首屏取数前快照（0 checks/19 缺文案，与各页 checks 轮留证逐字段相同）。证据 `evidence/coverage-20260916-1800.{json,txt}`。
  ④**跨页同族位置核对（人工指令 B 的扩展）**：新增 `topbar-matrix.py`（设计侧顶部栏声明矩阵）/`nav-title-decl.py`（顶部栏文本叶子声明）/`nav-title-audit.py`（21 页 want vs 实现）/`nav-cross-matrix.py`（实现侧矩阵）
  → 查出**同一设计声明（标题 fs17 或 fs20 · lineHeight 1.2）在 5 个页面被写成 4 个不同行盒**，其中序号 22 的载体页更把实现值 25.5 写成 want（自证绿）。逐页**先红后绿**（want 先按设计声明改 → 看红 → 改源码 → 两轮绿）：
  序号 8 **30→24** · 10 **22→20.4** · 10.1 **22→20.4** · 12 **21→20.4** · 22 **25.5→20.4**（15/23 两页原本已是 20.4）。
  ⑤**性质与证据（不夸大）**：5 页均为**声明保真 + 跨页一致性**修正，**几何与墨迹不变** —— `docH` 1206/1409/1414/1027/1138 全不变、序号 22 标题盒中心恒 66（改前 53..79 / 改后 56..76）、
  实现截图标题墨迹 58..74 vs 设计 PNG 57..73（+1 行 = H5 回退字体，同族既有记录）；红基线各 1 失败 → 绿 0、两轮差异字段 0
  （`evidence/redgreen-导航标题行盒-20260916-1800.txt` · `review-序号*-navtitle-run{1,2}.json` · 截图 `evidence/20260916-1800-序22-用量概览-导航标题行盒口径-h5-430宽.png`）。**未改**：序号 20（26 由设计 PNG 导航高 86 反推、有依据）、序号 2/21（核对器选择器未覆盖 → 登记为未判读）。
  台账 序号 8/10/10.1/12/22 行已逐行回写（`append-navtitle-note.py` + `normalize-ledger-eol.py` + `validate-ledger-csv.py` 22 行 × 11 字段体检通过）。
  ⑥**下轮开工第一件事**：①把序号 3（`.cred__title` 声明 h24 vs 实现 21.6）与 序号 2/21 的标题选择器补进核对器后重跑；②**把同一口径扩展到「文本 vs 图标字形层」的全量扫描**
  —— 本轮只扫了导航标题，同类偏差在**卡片标题**上同样存在：序号 8 `.quote-card__title`（设计叶子 `930bc97e` fs15 lh1.2 fit_content → 声明行盒 **18**）实现为 **22.5**（= 15×1.5），
  且其载体页的 want 也写成 22.5（`__measure-quotes.html:299`）；用法：把 `nav-title-audit.py` 的「标题叶子」选择扩成「任意文本叶子 ↔ 任意文本类」的映射表，逐页出红再修（先红后绿、逐页复跑两轮）。

- 2026-09-16 18:5x（cron 轮 `aap-tdd-run-20260916-1820`）· **新维度：设计文本叶子 ↔ 实现 DOM 全量审计（22/22 页）+ 序号 1「字重 / 行盒」两步 RED→GREEN（红 10+10 → 绿 0+0 · docH 1085→1098 · PNG 品牌区逐带与设计相同）**：
  ①**审计工具（本轮主交付）**：route 参数化载体页 `__measure-textleaf.html`（**一处代码覆盖全部路由**，不再逐页复制）+ `textleaf-scan.py`
  （逐页用自己的 mock 目录 + **带参路由** + 稳定性收口）+ `textleaf-audit.py`（按**渲染文案**配对设计叶子与 DOM 叶子，比行盒/字号/字重）+ `textleaf-accept.json`（人工核定表）。
  22 页全跑：设计文本叶子 **1131** · 匹配 **970（86%）** · 未渲染 88 · **待判读 class 172** —— 这正是前 22 轮「页面级 checks」没覆盖到的声明值维度，已成为后续轮次队列。
  ②**序号 1（本轮修完的页面）**：载体页新增 `fw.*` 10 条（字重，want = 设计 fontFamily → Bold 700 / SemiBold 600 / Medium 500）与 `be.*` 10 条（行盒，want = 设计**显式 height**）；
  红基线 **10/103** 与 **10/113**（两轮一致）→ 绿 **0/103 · 0/113**；两轮独立测量 phase1 **33/33 字段全等**；`docScrollHeight 1085 → 1098`（+13 = 各盒声明差之和）；
  PNG 色带实测：修前品牌区逐带落后（标题 -1 · 副标题 -5 · 卡片顶 -8）→ 修后 **逐带与设计相同（±0）**。
  ③**序号 8 的四类探针告警经 PNG 判定为非偏差**：卡 **pitch 两侧同为 190**（= 卡高 178 + 间距 12；scan-col x=215 设计白起 157/卡2 347 vs 实现 156/346）
  → 设计**渲染**行盒就是 22.5/19.5/16，缩到 fs×1.2 会破坏像素对齐；登记 `evidence/textleaf-accept-序号8-png-pitch.txt`。
  ④**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮**（18:36:47 / 18:37:18）· `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 font-weight 700×4/600×2/500×4 与 line-height 36/28×2/24/20×2/18×2/16.8/14.4）· `build:h5` DONE · `review-artifacts` 22/22。
  证据：`evidence/redgreen-序号1-字重行盒-20260916.txt` · `red-序号1-fw-字重偏差.txt` · `20260916-序01-登录注册-行盒字重对齐-h5-430宽.png`（430×1114）· `textleaf-audit-20260916-1905.txt` · `textleaf-scan-20260916-1855.log`。
  ⑤**下轮开工第一件事**：序号 1 余 **16px** 残差（首个字段标签前的间距比设计少 4px：设计 ink 339→367 = 28、实现 24；免责摘要正文设计为**两行**（叶子 e5e24331 fs12 h=40 = 2×20）而实现渲染成一行）
  → 修完再按 §5.18 的 172 条待判读清单**按页聚类、一页一轮**推进。

### 5.17 本轮（18:00 轮）新增的工具与口径

- **全量复核一条龙**：`bash .agents/state/coverage-rerun.sh [起点序号]`（build:h5 → 逐页 `review-measure.sh cov-<序号>` 两轮，序号 20 测量前**紧前**重置相对时间 mock）
  + `python .agents/state/coverage-report.py [--json out.json]`（逐页逐相 checks/失败/**两轮差异字段**/docH/溢出/缺文案，**兼容扁平单段文件**）。
- **画布覆盖核对**：`python .agents/state/canvas-coverage-check.py [--out …]`（台账每行 ↔ 当前画布 layer_id/帧名；未覆盖帧按「报价端 / 范围外」分类 → 回答「当前画布上有没有没实现的报价端帧」）。
- **跨页同族位置核对四件套**：`topbar-matrix.py`（设计侧：逐帧顶部栏节点 + 子树声明值）· `nav-title-decl.py`（逐帧顶部栏文本叶子 fs/fam/lineHeight/height）·
  `nav-title-audit.py`（21 页 want vs 实现；want = 显式 height 优先，否则 fs×lineHeight；实现侧支持 `$font-*` token 与无单位 line-height 换算）· `nav-cross-matrix.py`（实现侧 nav/topbar 字段矩阵）。
- ⚠️ **「文本行盒 = 字号×1.5」只适用于图标字形层**：本轮查出 5 个页面把该倍数用到了**文本**标题上（20→30 / 17→25.5 等），而设计对文本一律 `lineHeight 1.2`
  （或显式 height）。跨页核对时先读**该帧**该文本叶子的声明值，再判实现；探针 want 更不许照抄实现（序号 22 曾把 25.5 写成 want → 自证绿）。
- ⚠️ **居中单行文本的 line-height 不改变墨迹位置**：这类偏差在像素对账里**量不到**（盒中心不变），只在「换行/对齐方式变化」时才外显 ——
  本轮仍按「want = 声明值」修正并留证，判读结论写「几何与墨迹不变、属声明保真」，不夸大成视觉缺陷。
- **CSS 里同位置多值 = 排查线索**：同一 `.nav__title`/`.topbar__title` 在 5 个页面出现 4 个不同 line-height，靠 `nav-title-audit.py` 的跨页表一眼可见。

### 5.18 本轮（18:20 轮 · 全量文本叶子审计 + 序号 1）新增的工具与口径

- **全量审计三件套（一处代码覆盖全路由，取代逐页复制）**：
  - 载体页 `h5-measure/__measure-textleaf.html?route=%23/pages/x/index` —— 430 宽 iframe 载入任意路由；收口条件 = 「叶子数 + docH **连续 16 次采样（≈4s）不变**且 ≥24 次采样」或 25s 超时
    （**旧版按「叶子数 >12」2 秒就收口 → 数据未回来时抓到半成品，「未渲染」虚高**）；输出每个文本叶子（无元素子节点且非 head）的 文案 / 自身类 / **祖先类链** / computed fs,lh,fw,textAlign / rect。
  - `python .agents/state/textleaf-scan.py --all [--from <序号>]` —— 逐页起 serve.py（**每页自己的 mock 目录**）+ Chrome dump → `evidence/textleaf-<序号>.json`；
    **带参路由必须与各页载体页的 iframe src 一致**（`ROUTE_OVERRIDE`：4=id=c1 · 5=jobId=j1 · 6=reportId=DR-1 · 7=reportId=DR-7 · 11=itemId=qi1 · 12=quoteId=q7 · 12-v3=quoteId=q9 · 15=contractId=c1），
    不传参会渲染空态（实测：序号 6 **39→288** 叶子 · 序号 12 **6→35** · 序号 15 **29→41**，docH 也才等于设计帧高）。
  - `python .agents/state/textleaf-audit.py [序号 ...] [--out …] [--all-classes]` —— 设计叶子 ↔ DOM 叶子**按渲染文案配对**，比 行盒（want = 显式 height 优先，否则 fs×lineHeight）/ 字号 / 字重；
    文案在设计里**多义**（同一文案多个叶子且声明不同）→ 整条跳过并打印「口径跳过」；`textleaf-accept.json` 里的（页面, class）标为**已核定(非偏差)**（附理由与证据路径）。
- ⚠️ **探针的 declared-box ≠ 设计渲染值**：CJK `fit_content` 文本在 Figma 里的渲染行框 = 字体自然行框（实测 11px→16 · 13px→19.5 · 15px→22.5），而 `lineHeight: 1.2` 只是设计里记的倍数 →
  两边差 2.8~4.5px。**判据优先级：①设计显式 height ②design PNG 实测（卡 pitch / 卡边界 / 墨迹带）③fs×lineHeight；②③冲突以 ② 为准**
  （序号 8 是 ② 否掉 ③；序号 1 是 ① 被 PNG 证实 —— 同一轮里两种情形都出现过，必须逐页裁定）。
- ⚠️ **`uni-text` 的类名不在文本节点上**：uni-app H5 把 `<text class="x">` 渲染成 `<uni-text class="x"><span>` → 探针要取**祖先类链**（取 5 层）。
  只读自身 `className` 会把整页文本归进一个空 `span` 桶（第一版聚合出 n=364 的无意义行）。
- ⚠️ **台账「目标路由」列不带 `#/`**：旧写法 `route.replace('#/','%23/')` 是**空操作** → iframe 变成 `/index.html/pages/x/index` → 404 错误页（只有 5 个叶子、docH = iframe 高度），
  现象是「页面空的」而不是「参数没传对」。正解：显式拼 `?route=%23/<route.lstrip('/')>`，并先 `curl -s -o /dev/null -w '%{http_code}'` 自证一次。
- ⚠️ **假叶子**：uni-app 把页面标题写进 `document.title` → `<title>` 被当成文本叶子（fs 18.3467 / fw 400）。载体页排除 `el.closest('head')`，审计端也按 `tg` 过滤（旧 dump 仍可用）。
- **判卡高/卡 pitch 的取法**：`scan-col.py <png> <x> <y0> <y1>`（卡内**避文字**的白带起止 → 两卡白起之差 = **pitch = 卡高 + 间距**）+
  `png-textbands.py`（行墨迹带，不受投影染色干扰）→ 组合即能裁「行盒该多高、该不该改」。
- **序号 1 设计声明速查**：文本叶子**一律给显式 height**（fs20→28 · fs26→36 · fs14→24 · fs12→20 · fs13→18 · fs11→18 · fs14→16.8 = fs×1.2），字重按 fontFamily 映射。
- **批量改 CSS 的安全做法**：`apply-login-fw.py` / `apply-login-boxes.py` —— 按「父选择器 + 子选择器（+ 上下文行）」定位块，**每个锚点必须恰好命中 1 次**，任一不满足则整文件不写；先 `--dry` 看计划再落盘。
- **本轮新增脚本**：`__measure-textleaf.html` · `textleaf-scan.py` · `textleaf-audit.py` · `textleaf-accept.json` · `list-textleaf-dumps.py` · `ancestors-of.py`（叶子的祖先链声明）·
  `subtree-of.py`（子树声明，做卡高算术）· `apply-login-fw.py` · `apply-login-boxes.py` · `show-login-blocks.py` · `shot-login.sh`（430×1114）· `gen-1-evidence.py`。
- **设计 PNG 留档**：`curl -o .agents/state/design-shots/page-1-2.png "<.calicat/raw/pages/<id>/screenshot.json 里的 URL>"`（本页 430×1114）。

- 2026-09-16 18:45（cron 轮 `aap-tdd-run-20260916-1845`）· **序号 1「16px 残差」收口（红 19/133 · docH 1098 → 绿 0/133 · docH 1114 = 设计帧高）+ 像素对账 42 命中 / 6 未命中全部判读为非缺陷**：
  ①**设计真源口径（人工指令 C）**：本轮为**同一画布当前状态**的复核，未再整包重抓（上一轮 18:20 已重抓：22 帧 21 SAME + 1 DIFF 且该 DIFF 已登记）→ 页面期望值全部取自 `.calicat/raw/pages/page-1-2/design.tree.json` + 设计 PNG（430×1114）。
  ②**TDD 红→绿（本轮主交付）**：载体页 `__measure-login.html` 再扩 **19 条设计期望值 checks（合计 133 条）**；红基线（**同版最终探针两轮**、源码未改）**19/133** · `docH 1098` → 绿 **0/133** · `docH 1114`（= 设计帧高）；
  两轮独立测量 phase1 **全字段逐字节相同** · 溢出 0 · 文案缺失 0。
  ③**修 6 类偏差**（清单见台账序号 1 行 / `evidence/review-序号1-16px-checks-报告.md` §3）：首字段前间距 16→**20**（设计 spacer 9113d86d h20）·
  提示行 14.4→**21** 且图标占位盒 12×12→**16×21**（设计 c7f5db13 w16 fs14；形状 13×13 按 PNG 墨迹 x37..49/y630..642 画在盒内，色改设计字形填充灰 rgba(148,163,184,1)）·
  免责卡标题行 20→**27**（图标盒 14×14→**20×27**，设计 477e4b3f w20 fs18；填充 rgba(37,99,235,1)）·
  免责正文 38→**40**（设计 e5e24331 **显式 height 40** = 两行；`line-height` 1.6→**14.4px** + 垂直居中 → 墨迹行距 15 与设计逐行相同）·
  免责卡描边 `border`→**`box-shadow: 0 0 0 1px`**（设计 stroke align=center；border 会把卡高撑成 109、内容宽挤掉 2px）·
  分隔行 17→**18**（spacer 669abf96）· 协议行 20→**18**（对齐 center + 去掉勾选框 `margin-top:2px`）。
  ④**像素对账**：`cmp-bands-6`（±3）**命中 42 / 未命中 6**；6 条逐条用 `cmp-pixel-rows.py` 同列取色判读（y656/891 = 投影衰减起点差 1~2/255 · y914/920 = 设计导出图软染色 · y819/y415 = 带分割阈值效应且两侧取值完全相同）→ **非页面缺陷**；
  `text-rows.py` 逐行对账：两行免责正文墨迹 **设计 965..975 / 980..990 = 实现 966..976 / 980..990**，其余全行 ≡ 或 ±1。
  ⑤**交互相有牙齿**：phase2~6 两轮 requests **逐字节相同** —— 空表单 / 缺短信码 / 未勾协议三处校验门 **零请求**（toast 逐字）→ 获取验证码真发 `POST /api/v1/auth/sms/send` → 登录真发 `POST /api/v1/auth/sms/login` → 写 token → `#/pages/workbench/index`（落地页 2 个只读 GET）。
  ⑥**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 `width:16px;height:21px` / `height:40px` / `line-height:14.4px`×2 / `0 0 0 1px #eef2f7` / `min-height:18px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · 共用消费方回归门 序号 2 工作台两轮 **103 条 0 失败**（docH 1146）。
  ⑦**本轮发现并留证（下轮第一件事）**：本页仍有 **5 处 center 描边用 `border` 实现** + **3 个输入框图标占位盒 16×16**（应 20×27、填充灰）——实测设计占位文本左界 **76** vs 实现 **73**；另设计帧协议行勾选框为选中态而实现默认未选中（按 PRD 校验门保留，属状态差非几何差）。
  ⑧**探针/工具**：`show-fields.py`（打印某相指定字段）· `show-fails3.py`（兼容 checkFails 为**字符串数组**的老探针）· `cmp-pixel-rows.py`（两 PNG 同列取色 → 判「未命中是页面缺陷还是阴影/AA」）· `gen-1-16px-evidence.py`（红/绿/交互/像素四段转录合成）。

### 5.19 本轮（18:45 轮 · 序号 1）新增的工具与口径

- **两 PNG 同列取色**：`python .agents/state/cmp-pixel-rows.py <design.png> <impl.png> <y1,y2,...> [x]`
  —— 判「结构带未命中」性质的第一工具（本页 6 条未命中全部靠它定为「投影衰减 / 导出图软染色 / 带分割阈值」）。
- **打印某相字段 / 失败清单（老探针兼容）**：`python .agents/state/show-fields.py <run.json> <phase> [key...]` ·
  `python .agents/state/show-fails3.py <run.json>`（`show-phases.py` 只认 checkFails 为**对象数组**；本页这类老探针是**字符串数组**，会 AttributeError）。
- **设计期望值的「盒 + 形状」两层口径（本轮两例）**：图标一律「**盒 = 设计声明宽 × 字号×1.5**，形状（含颜色）入 `::before`」——
  提示行图标盒 16×21 / 形状 13×13 灰 · 免责卡图标盒 20×27 / 形状 15×17 蓝；**颜色必须读 `::before` 的 backgroundColor**（元素自身是空盒，探针读元素会得到 `rgb(0,0,0)` 假红）。
- ⚠️ **「文本行盒 = 设计显式 height」时，行盒本身与块内居中要一起做**：免责正文设计 `height 40` + `textAlignVertical=middle`
  → 实现 = `height:40px` + `line-height:14.4px` + `display:flex; align-items:center`；只把 height 写到 40 会让墨迹停在盒顶（PNG 会量出两行位置整体上移约 6px）。
- ⚠️ **`text-rows.py` 的「深色行带」会把设计里的矢量图标算进去、把 CSS 浅色占位形状排除**：同族比对时这类「设计有、实现无」的 1~2 行带属 D5 占位口径差异，**不要**记成页面缺陷（本页 601..602 即此）。
- ⚠️ **设计帧的静态状态 ≠ 实现默认状态**：page-1-2 协议行勾选框在设计里是**选中态**（蓝底 + tick），实现默认未选中（PRD 校验门要求用户显式勾选）→ 该行墨迹带（设计 849..866 / 实现 853..863）差异属**状态差**，判读写清楚，不要按几何缺陷处理。
- **本轮新增脚本**：`show-fields.py` · `show-fails3.py` · `cmp-pixel-rows.py` · `gen-1-16px-evidence.py` · `append-1-16px-note.py`；报告 `evidence/review-序号1-16px-checks-报告.md`。
