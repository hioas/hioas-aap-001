STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）；本轮新增两件事：①目录命名对齐 hioas-aap-client（用户在跑 dev server，句柄占用 → 每轮重试，锁一放就搬）②按序号 1→23 逐页复核。历史流水已归档到 aap-notes-archive-2026-09-16.md，**不要每轮读**。
LEASE: free until -

# AAP TDD 推进 · 状态与目标（自驱动循环的单一事实来源）

> 每轮：读本文件 → 看 STATUS/LEASE → 取件 → 做透（严格 TDD）→ 提交 → 回写本文件 → 飞书简报。
> 本文件只留**当前状态 + 硬约束 + 关键命令**；历史流水追加到 `aap-notes-archive-*.md`，**不要每轮读**。

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

## 5. 关键命令（照抄可用）

- 项目根：`E:\workspaces\hioas\hioas-aap-001`（远端 https://github.com/hioas/hioas-aap-001）
- 客户端：`cd aap-client`（改名后为 `hioas-aap-client`）；`npm test`（vitest run）；`npm run build:mp-weixin`；`npm run build:h5`；`npm run dev:h5`；`npm run type-check`
- **目录对齐**：仓库根 `git mv aap-client hioas-aap-client`（`Permission denied` = 用户进程持有句柄 → 顺延，别 kill）
- 台账统计：`python .agents/state/gen-ledger.py`
- 设计树探针：`python .agents/state/node-probe.py <page-id>`（产出 `.agents/state/<page-id>-nodes.txt`，含几何/填充/内边距/文字）
- 设计截图像素量尺：`python .agents/state/png-bands.py <png> v|h <idx> [from] [to]`（同色色带 = 盒子边界；定卡高/间距/栏高最硬的依据）
- 像素对账：`python .agents/state/text-rows.py`（同一脚本跑设计与实现，逐行文本带对比）
- 台账取件：`python .agents/state/list-pending.py`（按序号列出未完成页面）
- 两次独立测量一致性：`python .agents/state/cmp-measure-runs.py <runA.json> <runB.json>`
- 静态取证服务器（本循环自用，用完即关）：`python .agents/state/h5-measure/serve.py <h5 产物目录> .agents/state/h5-measure/api <端口>`
- Calicat CLI：`calicat status` / `calicat tools-call --name get_screenshots --args '{...}'`；
  技能脚本目录 `C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/`
- gh：`E:\tools\bin\gh.exe`（已登录 geeker-lait）
- 平台坑：中文 Windows `netstat` 是 GBK；`taskkill` 要写 `/PID`（`//PID` 报「无效参数」）；
  bash 把中文塞 JSON body 会变 GBK（要发中文请求体用 Node/Python 的 utf-8）；
  `npm run build:h5` 会清空 `dist/build/h5` → `__measure*.html` 载体页每次 build 后要重新拷贝。
