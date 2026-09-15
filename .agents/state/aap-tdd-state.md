STATUS: RUNNING
LEASE: free

# AAP TDD 推进 · 状态与目标（自驱动循环的单一事实来源）

> 每轮：读本文件 → 看 STATUS/LEASE → 从台账取件 → 做透（严格 TDD）→ 提交 → 回写台账与本文件 → 飞书简报。
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

## 1. 目标

在 `E:\workspaces\hioas\hioas-aap-001\aap-client` 用 **uni-app（Vue3 + Vite + TS）** 实现 Calicat 画布上
**报价端·小程序**全部页面与交互，**按页面序号逐个执行**，每个页面走严格 TDD。

- 设计真源：Calicat 文件 `2095515676955668480`，画布 `2095515676976640000`（见 `.calicat/`）。
- 页面序号/顺序/目标路由：`.agents/state/aap-feature-status.csv`（台账，序号列即执行顺序）。
- 需求真源：`.calicat/prd/*.md`（22 份 PRD 卡；关键 = `01-PRD总览`、`09-检测验证引擎PRD`、
  `10-报价与合同结算PRD`、`11-同步与用量统计PRD`、`13-管理端PRD`、`17-零歧义执行规格spec`、`18-API设计OpenAPI`、`21-验收标准`）。
- 页面计划说明：`docs/aap-client-page-plan.md`。

## 2. 每页的标准动作（固定顺序，不得跳步）

1. **抓设计**：`python C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/calicat_source.py page
   --url https://www.calicat.cn/design/2095515676955668480 --layer-id <sourceLayerId> --page-id <页面ID> --out .calicat`
   → 产出 `raw/pages/<页面ID>/{design,interaction,screenshot}.json`（截图 URL 用 vision_analyze 看图，别猜样式）。
2. **列功能清单**：从 design.json + interaction.json + 相关 PRD 抽出该页的每个可见元素与交互，
   逐条落到台账行（一条交互一行，`用例(证据)` 先写**计划中的用例名**）。
3. **梳理接口**：该页每个 `api` 类交互必须指向 `18-API设计OpenAPI.md` 的路径与方法；
   无接口依据的写 `missing-prd` 并标 `阻塞`，**不得臆造**。
4. **先写红测试**：`aap-client/tests/**` 下写断言 → 跑 `npm test` 看**真红**（贴报错行）。
5. **实现到绿**：写 `src/**` 代码 → 复跑 → **连跑两轮全绿**才算过。
6. **构建证明**：`npm run build:mp-weixin` 产出 `dist/build/mp-weixin`（能编译过 = 小程序可导入）；
   `npm run build:h5` + 浏览器截图（`logs/screenshots/`）作为可视化证据。**本机未装微信开发者工具**，
   故 mp-weixin 只做编译证明，真机/开发者工具验收留给人类。
7. **回写**：台账该行状态改 `已验证`/`部分`，`用例(证据)` 写真实用例名与命令；本文件 §4 追加一行本轮小结。
8. **提交**：只提交自己改动的文件，提交信息 `feat(aap-client): <序号>-<页面> <做了什么>`。

## 3. 硬约束

1. **严格 TDD**：先写会红的断言 → 看红基线 → 实现 → 复跑绿 → **连跑两轮**一致才算过。
2. **不得臆造**：接口、字段、错误码、页面元素一律来自 `.calicat/` 证据或 PRD；缺依据就标 `阻塞` 并写进简报。
3. **一页一提交**：不跨页面混装；台账、状态文件与该页代码同批提交。
4. **证据要有牙齿**：vitest 真跑输出（不是"应该能过"）+ H5 截图 + mp-weixin 编译产物存在。
   `npm run dev` 能起 ≠ 页面能用。
5. **中文页面文案**必须与设计稿一致（design.json 里的文字为准），不得自己改写。
6. **设计系统先抽取**：第 1 页实现时同步抽出 `src/styles/tokens.scss` + 基础组件，
   后续页面复用，不许每页各写一套。
7. 凭证/密钥不落盘、不打印；不把 `.calicat/raw` 大文件提交进仓库（`.gitignore` 已挡）。
8. cron 会话里 `python -c` / `node -e` / `execute_code` 可能被安全策略拦 → 脚本一律先 `write_file` 落成 `.py`/`.mjs` 再执行。

## 4. 进度（细表看台账 CSV，这里只留能力组）

🟢 本轮（2026-09-16 00:25~00:47，租约 aap-tdd-run-20260916-0025 → 已释放）· **类型门禁修复 + 序号 4「提交接入凭证 2」收口**：
- **先修类型门禁（独立提交 `62b61d2`）**：上一轮记的 `TS5070` 根因是 `typescript 4.9.5` 撞上 `@vue/tsconfig 0.5.1` 的 TS5 语义
  （`moduleResolution: bundler`）→ vue-tsc 一条真实错误都报不出来。修法：tsconfig 显式 `moduleResolution: node`；
  随之暴露的 `http.ts` 两条真错误按 `uni.request` 类型对齐（method 联合不含 PATCH；`res.data` 经 unknown 转换）。
  红/绿留证 `evidence/typecheck-red-ts5070.txt`、`evidence/typecheck-green-序号0-类型门禁.txt`（exit 2 → exit 0，`npm test` 129/129 无回归）。
  **该坑与修法已写进 `.agents/skills/dev/SKILL.md` §6：后续每页提交前都要跑 `npm run type-check`**。
- **Calicat 侧**：设计类工具照旧要先 `cmd /c start "" <design-url>` 拉起编辑器；page-4-2 设计树（97 图层）+ 截图已抓
  （`interaction.json` 仍为「不存在图层交互数据」→ 交互真源退 PRD + 画布 30 页清单）。
- **TDD（4 条红基线 → 各自到绿）**：①模型切片 `Failed to resolve import`；②接口切片 7 条 `credentialApi.xxx is not a function`；
  ③页面切片 `Failed to resolve import`；④**由 DOM 数字抓出真缺陷后补的红断言**——脱敏值 34px 高（= 两行）。
  实现：`src/utils/credential-form-model.ts`、`src/api/credential.ts`（+detail/save/precheck）、
  `src/pages/credential-submit/index.vue`、`pages.json` 路由、tokens 4 个新色值。绿 **187/187 连跑两轮一致**。
- **本轮抓出并修掉的真缺陷**：脱敏框里 `.input-box__value{flex:1}` 与 `.input-box__spacer{flex:1}` 争空间 →
  脱敏值只拿到 143px 换行（高 34px）；去掉 spacer + `white-space:nowrap` 后 **高 17px 单行、宽 286px**（DOM 数字前后对比留证）。
  另修 2px：`.submit-bar__ghost` 加 `box-sizing:border-box`，固定操作条总高回到设计的 84px（12+48+24）。
- **客观证据链**：`build:mp-weixin` 产出 `dist/build/mp-weixin/pages/credential-submit/{js,json,wxml,wxss}`；
  430 宽 iframe + 无头 Chrome DOM 实测 `evidence/measure-序号4-修后430.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 `0` ·
  `bar h84 barPinned true` · `atBottom.lastCardFullyAboveBar true` · `checkedCount 3` · `modelRowCount 5` · `vendorGroupCount 2` ·
  `已选 3 个` · 卡片 `x16 w398` · 输入框高 `46` · 勾选框 `18×18` · 色值 `已配置 #ECFDF5/#15803D`、安全提示 `#FFFBEB/#92400E`、主色 `#2563EB`；
  像素墨迹核验（`png-crop` + `png-ink`）标题/脱敏行/底部按钮右留白 24/54/16 均未触边；文案缺失 `[]`（仅剩两个 `<input>` 值 ——
  innerText 不含 input.value 的既知假象，已由 aliasValue/baseUrlValue 单独断言）。
  截图 `logs/screenshots/20260916-0039-序号04-提交接入凭证-h5-430宽.png`。
- **工具修复**：`gen-ledger.py` 之前只看 `interaction.json` 是否存在 → 把 page-4-2 记成「交互已抓 是」（其实一个字都没有）。
  已改为**读文件内容判定**（命中「不存在图层交互数据」即记「否」），并把截图列改为优先取 `screenshot.json` 里的 COS URL；
  修后台账显示「交互已抓 **0/22**」——这是事实，也是「交互真源缺失」这条长期缺口的量化体现。
- **平台坑（新，已写进 `.agents/skills/dev/SKILL.md` §4.1）**：①`npm run build:h5` 会**清空** `dist/build/h5` →
  `__measure*.html` 载体页必须在每次 build:h5 之后重新拷贝（否则 404，Chrome 只回 404 页，取数脚本会静默读到上一轮 JSON：**先看 dump 文件字节数**）；
  ②无头 Chrome 复用同一 `--user-data-dir` 可能不产出 dump → 每次换新目录；③uni-app H5 把 `<input>` 渲染成 `<uni-input>` 包装元素，取数要读内层原生 `input.value`；
  ④`/api/v1/credentials/{id}` 这类「同名文件与子路径共存」用静态文件 mock 无解 → 新增 `.agents/state/h5-measure/serve.py`（静态 + JSON mock 一体，先目录后文件）。
- ⚠️ 待人类确认（不阻塞本轮，全部写进台账序号 4 备注）：①18-API 卡片只列路径未列方法 → `/credentials/{id}` 的 GET/PUT 为 REST 语义推断；
  ②模型清单候选目录（未勾选的 gpt-3.5-turbo/claude-3-opus 从哪来）在 18-API 无供应商侧目录接口 → 前端按响应字段 `model_catalog` 消费（missing-prd）；
  ③「凭证名称」= `aap_credential.alias`，但 18-API 无字段级 schema；④脱敏格式四处不一致（设计 16 圆点 / R-05 前4***后4 / 15-数据字典 `sk-a***5678` / 18-API `sk-****abcd`）；
  ⑤「已配置」不在 CredentialStatus 枚举内；⑥本页入口未确认（画布「查看」列只有报告链接）→ 按 id 入参实现（query 优先、storage `aap_credential_id` 兜底）；
  ⑦系统字体圆点墨迹小于设计稿字体（度量差异）；⑧「建议 6–24 字」为设计原文的「建议」→ 不拦截提交。

⏳ 下一步（下一轮）：台账序号 **4-v1「接入凭证-表单」（page-24，`/pages/credential-submit/form`）**——与本轮同族的「新建」空态表单，
按 §2 八步走；可直接复用 `credential-form-model.ts` 与 `.agents/state/h5-measure/serve.py`（记得 build:h5 之后重拷载体页）。
（序号 1/2/3/4 均已实现并留证，状态为「部分」是因为登记了等人类拍板的缺口，不要重复回炉。）

🟢 本轮（2026-09-16 00:10~00:24，租约 aap-tdd-run-20260916-0010 → 已释放）· **序号 3「凭证列表-有数据」收口**：
- **Calicat 侧**：设计类工具报「请先在浏览器中打开文件」→ `cmd /c start "" <design-url>` 拉起后恢复；page-3 设计树 + 截图已抓
  （`interaction.json` 仍无数据 → 交互退 PRD + 画布 30 页清单）。
- **TDD**：红基线 2 个用例文件 `Failed to resolve import`（91 通过，`evidence/red-序号3.txt`）；实现
  `src/utils/credentials-model.ts`、`src/api/credential.ts`、`src/pages/credentials/index.vue`、`src/pages.json` 路由、tokens 4 个新色值；
  绿 **129/129 连跑两轮一致**（`evidence/green-序号3.txt`）。
- **客观证据链**：`npm run build:mp-weixin` 产出 `dist/build/mp-weixin/pages/credentials/{js,json,wxml,wxss}`；
  430 宽 iframe + 无头 Chrome DOM 实测 `evidence/measure-序号3-无滚动条430.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 `0` ·
  文案缺失 `[]` · chip `待检测3/检测中2/不通过1/通过4` · 10 行 / 报告 5 条 · 列宽 `226/48/42/42` · `tabbarPinned true` ·
  滚到底 `cardFullyAboveTabbar true`；像素墨迹核验「共 10 条」四字完整（右留白 20px）；
  截图 `logs/screenshots/20260916-0022-序号03-凭证列表-h5-430宽.png`。
- ⚠️ **新踩的平台坑（已写进 `.agents/skills/dev/SKILL.md` §4.1）**：headless Chrome **不认 `--window-size`**
  （实测传 `430,944` 时 `innerWidth=500`）→ 直接对应用截图会得到「右边被裁掉」的**假象**（vision 也会跟着误报）；
  正解 = 用 430 宽 iframe 载体页截图 + 像素裁剪（`.agents/state/png-crop.py`），并用 `png-ink.py` 核验墨迹右边界。
- ⚠️ 待人类确认（不阻塞本轮）：①`GET /credentials` 字段级 schema 未定义（missing-prd）；②设计 4 态 vs 09-PRD R-25 五分支的对应由服务端派生；
  ③状态统计计数取自当前列表（接口未定义汇总字段）；④「报告」路由映射（通过→`/pages/report/index`、不通过→`/pages/report-failed/index`）为推断；
  ⑤空态文案「暂无接入凭证」为占位。
- ⚠️ **既有缺陷（非本轮引入）**：`npm run type-check`（vue-tsc）报 `TS5070: Option '--resolveJsonModule' cannot be specified without 'node' module resolution strategy`
  —— `aap-client/tsconfig.json` 自序号 1 提交后未再改动（`git log` 可证），修法 = 加 `"moduleResolution": "node"` 或去掉 `resolveJsonModule`；
  为守「一页一提交」本轮未动它，**下一轮开工前顺手修掉并单独提交**，让类型门禁重新可用。

⏳ 下一步（下一轮）：台账序号 4「提交接入凭证 2」（page-4-2，`/pages/credential-submit/index`），按 §2 八步走；
  截图一律走「430 宽 iframe 载体页 + 裁剪」这条确定性路径。

🟢 本轮（2026-09-15 23:47~2026-09-16 00:10，租约 aap-tdd-run-20260915-2347 → 已释放）· **序号 2「工作台 · 方案B 数据台」收口**：
- **Calicat 侧**：设计类工具一开始全部报「请先在浏览器中打开文件」→ 定位为**编辑器会话前置条件**（PRD 类工具不受影响）；
  用 `cmd /c start "" <design-url>` 拉起默认浏览器后恢复，`page-2-b` 设计树 + 截图已抓（`interaction.json` 仍无数据 → 交互退 PRD）。
- **TDD**：红基线 16 失败/49 通过（`evidence/red-序号2.txt`）；实现 `src/utils/format.ts`、`src/utils/workbench-model.ts`、
  `src/api/usage.ts`、`src/api/provider.ts`、重写 `src/pages/workbench/index.vue`；绿 **91/91 连跑两轮一致**（`evidence/green-序号2.txt`）。
- **客观证据链**：`npm run build:mp-weixin` 产出 `dist/build/mp-weixin/pages/workbench/{js,json,wxml,wxss}`；
  H5 + 无头 Chrome DOM 实测 `evidence/measure-序号2-修后.json`：`docScrollWidth 415 ≤ innerWidth 430`、`overflowingCount 0`、
  `missingTexts []`、`modelRowCount 4`、数字与接口 mock 一致（3.86B / ¥54,200 / 合计 ¥128,640 · 4 个模型）；
  截图 `logs/screenshots/20260916-0005-序号02-工作台-h5-修后.png`。
- **修掉的真缺陷（由数字发现）**：底部 TabBar 原来在文档流里（`tabbarBottom 1128 vs innerHeight 900`）→ 改 `position: fixed` +
  内容区 `padding-bottom:96px`，复测 `tabbarPinned true`。
- ⚠️ **再次验证的教训**：`vision_analyze` 对 430 宽截图**继续误报**「顶部圆形头像被右边缘裁切」，
  DOM 实测 `avatarRight 399 ≤ 430` 予以推翻 → 视觉验收一律以 `__measure.html` 数字为准。
- ⚠️ 待人类确认（不阻塞本轮）：①`/usage/summary` 与 `/provider/profile` **字段级 schema 未在 18-API 定义**
  （现按 15-数据字典 usage 域字段名映射，记 `missing-prd`）；②设计稿图例「音频 6%·0.23B + 视频 6%·0.23B」合计 106%（设计内部矛盾，按原样实现）；
  ③「钱包」在设计画布无对应页面（现为 client-only toast）；④设计稿主色蓝 `#1D4ED8` vs PRD08 深青（沿用序号 1 的按设计实现）。

⏳ 下一步（下一轮）：台账序号 3「凭证列表-有数据」（page-3，`/pages/credentials/index`），按 §2 八步走；
  可复用 `.agents/state/h5-measure/`（measure 页 + mock 接口）做 DOM 数字验收。

🟢 本轮（2026-09-15 23:20~23:45，租约 aap-tdd-run-20260915-2320 → 已释放）· **循环基础设施 + 序号 1 页面收口**：
- **Calicat 侧**：CLI 已登录；技能已装进 Hermes（`AppData/Local/hermes/skills/calicat`）；
  `inventory` + `prd` 已导出（30 页 / 22 份 PRD 卡）；`page-1-2` 设计树与截图已抓（`interaction.json` 无数据，交互退 PRD）。
- **台账/脚本**：`.agents/state/` 下 `gen-ledger.py`（生成/统计）、`list-pending.py`（按序号取件）、
  `design-summary.py`（设计树可读摘要）、`extract-tokens.py`（token 抽取）、`check-crop.py`（截图裁切客观检查）。
- **aap-client 骨架**：官方 uni-preset-vue#vite-ts 模板（uni-app 3.0.0-5020420260813003 / vite 5.2.8）+
  vitest/jsdom/@vue/test-utils；`src/styles/tokens.scss` 为设计 token 单一来源。
- **序号 1 登录注册页（page-1-2）→ 台账 `已验证`**：
  - 红基线：4 个用例文件全部 `Failed to resolve import`（实现不存在）。
  - 实现：`src/utils/validators.ts`、`src/utils/cooldown.ts`、`src/api/http.ts`、`src/api/auth.ts`、
    `src/pages/login/index.vue`（430 宽；品牌蓝 #1D4ED8 / 主按钮 #2563EB）。
  - 绿：`npm test` **49/49 连跑两轮一致**；`npm run build:mp-weixin` 产出 `dist/build/mp-weixin/pages/login/{js,json,wxml,wxss}`；
    `npm run build:h5` + 无头 Chrome 截图 `logs/screenshots/20260915-2337-序号01-登录注册-h5-修复后.png`。
  - **修掉的真缺陷**（第一版截图后修）：标题/副标题挤一行（容器缺 flex column）、
    `<input type="checkbox">` 在 uni-app 里根本不是复选框（改成自绘 view + `@tap`）、
    输入框 `trim is not a function`（H5 `type=number` 的 v-model 是 number → `normalize()` 归一）、
    emoji 图标违反 PRD08（改 CSS 色块占位）。
  - 客观证据链：DOM 实测 `innerWidth 430 / docScrollWidth 415 / 溢出元素 0`，验证码文案 `A7K9` 与按钮文案 `获取验证码` 完整。
- ⚠️ **教训**：`vision_analyze` 对 430 宽窄截图**两次误报"右侧被裁切"**，与 DOM 实测矛盾。
  以后视觉验收必须配 `__measure.html`（iframe=430 + getBoundingClientRect）给出数字，别只信模型描述。
- ⚠️ 待人类确认：设计稿主色（蓝 #1D4ED8）与 08-前端原型说明（深青）冲突；图标方案（现为 CSS 占位）。
⏳ 下一步（下一轮）：台账序号 2「工作台 · 方案B 数据台」（page-2-b），按 §2 八步走；顺带把
  `.agents/skills/dev/SKILL.md` 的视觉验收条款改成"DOM 数字优先"。

## 5. 关键命令（照抄可用）

- 项目根：`E:\workspaces\hioas\hioas-aap-001`（远端 https://github.com/hioas/hioas-aap-001）
- 客户端：`cd aap-client`；`npm test`（vitest run）；`npm run build:mp-weixin`；`npm run build:h5`；`npm run dev:h5`
- 台账统计：`python .agents/state/gen-ledger.py`
- 台账取件：`python .agents/state/list-pending.py`（按序号列出未完成页面）
- Calicat CLI：`calicat status` / `calicat tools-call --name get_screenshots --args '{...}'`；
  技能脚本目录 `C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/`
- gh：`E:\tools\bin\gh.exe`（已登录 geeker-lait）
- 平台坑：中文 Windows `netstat` 是 GBK；`taskkill` 需 `MSYS_NO_PATHCONV=1`；
  bash 把中文塞 JSON body 会变 GBK（要发中文请求体用 Node/Python 的 utf-8）。
