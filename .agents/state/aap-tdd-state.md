STATUS: RUNNING
LEASE: free until -

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

🟢 本轮（2026-09-16 03:11~03:28，租约 aap-tdd-run-20260916-0311 → 已释放）· **序号 11「模型定价-详情」（page-11）收口**：
- **Calicat 侧**：`calicat_source.py page` 一次成功（本轮**没有**再需要 `cmd /c start` 拉编辑器）；page-11 设计树（81KB）+ 截图（430×1541，1:1 帧图）已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 06-PRD 计费编译规则 / 15-数据字典 / 17-spec / 18-API + 设计稿控件语义。
  **新增可复用工具**：`rows-gap.py <png> <probeX> <refX> [tol] [from] [to]` —— 按行比较「卡内列 vs 页边距列」找**近似同色段**，
  一把量出所有卡片的 top/height 与间隙（比 `png-bg-runs.py` 抗模糊；本轮据此定死 卡1 114..196(82) / 卡2 211..363(153) / 卡3 378..974 / 卡4 989..1448 / 底栏 1465，间隙一律 14）。
  另：设计树里**隐藏节点带 `visible:false`**（本页「规则提示」），排查「算术对不上设计总高」时先 grep visible —— 本轮卡4 有 24px 差额就是它在作乱（隐藏节点不参与布局）。
- **这页到底是什么**：gpt-4o 的报价明细行定价页（设计总高 1541，无 TabBar）：顶栏（返回 /「gpt-4o」18px Bold +「模型定价」10px / 右侧「保存」）·
  卡1 模型信息（蓝圆序号 1 + 模型名 + 灰 chevron + 摘要「始终匹配（默认档位）· 输入 $2.50 输出 $10.00 / 1M token」）·
  卡2 计费方式（「档位」标签 + base 输入框 + 「按 token」选择框 + 蓝描边「添加计费分支」）·
  卡3 Token 价格（标题 + 灰胶囊「$/1M token」；输入/输出/缓存读取/缓存写入/1 小时缓存写入 5 字段两列栅格、行3 单列；
  1px 分隔线 + 「媒体定价」小节 + 图像列 3 项 / 音频列 2 项）·
  卡4 请求规则计费（蓝竖条标题 + 说明 + 「规则组 #1」（时间/小时 · Asia/Shanghai/大于等于 · 值 · 新增参数/Header · 新增时间条件 · 倍率 1.0 · 换算说明）+ 删除红标 + 「新增规则组」）·
  底栏「保存价格」398×48 #2563EB。
- **TDD（3 切片，逐切片红→绿；新增 60 例）**：`tests/unit/model-pricing-model.spec.ts`(28) · `tests/unit/quote-item-api.spec.ts`(5) ·
  `tests/pages/model-pricing.spec.ts`(27)；红基线 `evidence/red-序号11-切片1/2/3.txt`（切片1/3 = `Failed to resolve import`，切片2 = `quoteApi.getItem/listItems/saveItem is not a function`）；
  实现 `src/utils/model-pricing-model.ts`、`src/api/quote.ts`（+getItem/listItems/saveItem）、`src/pages/model-pricing/index.vue`、`pages.json` 路由；
  **tokens 0 新增**（全部色值命中既有 tokens.scss）；绿 **640/640 连跑两轮一致**（`evidence/green-序号11-轮1/轮2.txt`）+ `npm run type-check` **exit 0**。
- **由 DOM 数字抓出的真偏差（vision 完全看不出）**：卡3 比设计矮 5px、卡4 之后整体上移 5px —— 根因 = 「单位标签 $/1M token」的 11px 文本行盒
  我按 `line-height:13.2px`（1.2 倍）写了，而设计里**盒装标签的 11px 行盒是 18px**（`padding 3/8 + 18` → 头高 24）：
  改前 价格行1 框 top **450**、1h缓存框 top **616**、媒体框 top **747**、页高 **1536**；
  改后 价格行1 框 top **454**、1h缓存框 **620**、媒体框 **752**、卡3 高 **598**、卡4 top **990**、底栏 top **1464**、页高 **1540**（设计 1541，仅差 1）。
  **判定法（本轮最值钱）**：用「价格行框实际 y − 卡顶 − padding − 间距」**反推头部高度**（455−378.4−14−14 = 48.6 = 头24 + 标签18 + 7），
  不要凭「11px 就该 13.2」猜 —— 本页 11px 文本有两种行盒：**盒装标签 18 / fit_content 说明 13.2**（卡4 说明两行 26.4 反证了后者）。
- **客观证据链**：`build:mp-weixin` 产出 `pages/model-pricing/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号11-run2.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 **0** ·
  文案缺失 `['base']`（= 输入框 value，innerText 不含 input.value 的既知假象，已用 `tierValue='base'` 单独断言）·
  卡 top 114/210/377/990 高 82/153/**598**/459（设计 114.4/211.4/378.4/989 与 82/153/597/459）· 价格行 pitch 83 · 勾选 2 个 bg rgb(37,99,235)、
  未勾选 ring rgb(203,213,225) · 底栏 1464..1540(76) · 保存价格 x16..414(398×48) · input 11 个 · 无 TabBar；
  **两次独立测量 85 字段全等**（`evidence/cmp-序号11-两轮.txt`，0 差异）；**像素墨迹核验**（`png-ink.py`）：底栏 runs `[(16,413)]` 与设计**完全一致**、
  媒体行 `[(44,50),(233,239)]` 与设计**完全一致**、价格行1 边界一致（maxInkX 264 / 右留白 165 相同）、顶部带仅返回箭头+标题+保存（右留白 320，无载体污染）；
  截图 `logs/screenshots/20260916-0322-序号11-模型定价-h5-430宽.png`（430×1541）；
  **浏览器内真实交互（phase2/3/4）**：点顶栏「保存」→ serve.py 日志实测 **`PUT /api/v1/quotes/items/qi1`**（body 含 input/output/tier/billing_mode/request_rules 6 键，未勾选字段不出现）→ toast「保存成功」；
  勾选「缓存读取价格」（checkOn 2→3）→ 点底部「保存价格」→ 真实 `PUT`，body 多出 **`"cache_read_price":0`**（勾选=启用）；
  折叠「请求规则计费」→ 规则组 0 个 + 设计里 visible=false 的提示「点击展开，配置计费请求规则」渲染出来；「新增规则组」→ `["规则组 #1","规则组 #2"]`；点返回 hash 不变（navigateBack 无栈）。
- ⚠️ 待人类拍板（不阻塞本轮，15 条全部写进台账序号 11 备注）：①价格字段「启用」勾选无 PRD 字段 → 取「值>0 视为启用」、未勾选省略；②计价方式选项集合零命中 → 只回显不造选项；
  ③卡1 固定语「始终匹配（默认档位）」为设计常量；④提交键 `tier` 为推断（aap_quote_item 无该列）；⑤媒体 4/5 个键名为推断；⑥新增类按钮 schema 无依据 → 只做本地操作；
  ⑦请求规则条件枚举与 06-PRD §1.3 不同口径；⑧18-API 只列路径 → GET/PUT 推断；⑨规则组 6 键为设计直译；⑩「值」是设计占位；⑪校验/toast 文案占位（阈值锚定 06-PRD §1.2/§4.2）；
  ⑫图标 CSS 占位（折叠箭头实测 x387..399 vs 设计 386..393）；⑬价格行3/媒体末行单列留白是设计本意（设计树 价格行3 kids=1、音频列 kids=2）；⑭本页无「编译预览」入口而 18-API 有 → 不接线；
  ⑮**设计/PRD 冲突**：17-spec 写「请求级加价 R5 本期只在管理端高级模式开放」，而小程序设计稿本页有完整「请求规则计费」卡 → 已按设计实现，等拍板是否下架。

⏳ 下一步（下一轮）：台账序号 **12「报价预览与提交 2」**（page-12-2，`/pages/quote-preview/index`）——本页保存后的报价链路下一页，按 §2 八步走；
  可复用本轮全部工具链：`rows-gap.py`（量卡边界与间隙）/ `png-ink.py` 同带对账 / `api-11` 式**独立 mock 集** / `__measure-model-pricing.html` 载体模板
  （**先 grep 设计树 visible:false 再算高度**；**盒装标签的 11px 行盒可能不是 13.2**）。


🟢 本轮（2026-09-16 02:51~03:10，租约 aap-tdd-run-20260916-0251 → 已释放）· **序号 10.1「供应商档案 2」（page-10-1-2）收口**：
- **Calicat 侧**：`calicat_source.py page` 先报「请先在浏览器中打开文件」→ `cmd /c start "" <design-url>` 拉起后正常；
  page-10-1-2 设计树（78KB / 158 节点）+ 截图（430×1414）已抓；`interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 17-spec/18-API + 设计稿控件语义。
  **新增可复用工具**：`rows-ink.py`（按横向区间逐行找墨迹 → 一把量出字段/文本行的 y 区间）、
  `colors-all.py`（**全部**颜色含 fontFill + 标注 tokens 是否已有 → 决定本页要不要新增 token；`extract-tokens.py` 只看 fills 会漏 fontFill）。
- **这页到底是什么**：只读的「主体档案」视图页（无 TabBar、无任何输入控件，设计总高 1414）：顶栏（返回 /「主体档案」17px Bold / 右侧橙胶囊「完整度 72%」h24 r12 #FFF7ED）·
  卡1 档案完整度（标题 + 蓝「72%」+ 进度条 h10 #E2E8F0 填充 72% + 琥珀闸门提示「…当前还缺 2 项资质文件。」h60）·
  卡2 主体信息（右上灰角标「已认证 · 不可编辑」h22 r11 #F1F5F9；企业名称 / 统一社会信用代码 / **供应商类型蓝 chip + 所在地区 同一行两栏** / 详细地址 / 官网（蓝字）/ 灰底锁定提示 h51）·
  卡3 联系信息（右上「编辑」；联系人+职务 / 手机号+邮箱 两列；公司简介灰框 h64）· 卡4 资质文件（右上「管理」；三行固定：营业执照〔已上传 · 2024-06-10 + 绿标已通过〕/ 上游授权书〔未上传 + 橙标条件必传〕/ 增值电信业务许可证〔选传 · 可后续补充 + chevron〕；
  全宽「上传新资质」描边按钮 #93C5FD）· 底栏「保存」193×48 幽灵 +「去补全资质」自适应 #2563EB。
- **TDD（2 切片：模型 → 页面；新增 48 例）**：`tests/unit/profile-model.spec.ts`(21) · `tests/pages/profile.spec.ts`(27)；
  红基线 `evidence/red-序号10.1-切片1.txt`（`Failed to resolve import @/utils/profile-model`）· `red-序号10.1-切片2.txt`（`Failed to resolve import @/pages/profile/index`）；
  实现 `src/utils/profile-model.ts`、`src/pages/profile/index.vue`、`pages.json` 路由、tokens **新增 1 个**（#93C5FD 上传按钮描边）；
  绿 **580/580 连跑两轮一致**（`evidence/green-序号10.1-轮1/轮2.txt`）+ `npm run type-check` **exit 0**。
- **由 DOM 数字抓出的真偏差（vision 完全看不出）**：锁定提示盒实测 **42 vs 设计 51** —— 根因 = 我把图标画成 18 高的 CSS 形状，
  而设计里 `paragraph fontSize=18 remixicon` 的**行盒是 27**（18×1.5）→ 盒高该是 12+27+12=51；只差这 9px，
  **卡2 之后整页元素全部上移 9px**（简介框 890 vs 899、资质缩略图 1049 vs 1058、底栏 1321 vs 1330、页高 1409 vs 1414）。
  加 27 高包裹层后逐值相等：页高 **1414 = 设计 1414**、资质缩略图 1058/1122/1186、上传按钮 1250、底栏 1330 全部与设计一致。
- **客观证据链**：`build:mp-weixin` 产出 `pages/profile/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号10.1-run1.json`：`docScrollWidth 430` · 溢出 **0** · 文案缺失 **[]（need 53 条设计原文）** ·
  卡 top 108/278/704/995 高 **158/414/279/319**（设计 158/413/279/319）· 进度条 x36 w358 h10 填充 258 · 闸门 186..245(60) · 锁定角标 top301 h22 ·
  类型 chip top473 h24 · 简介框 899..962(64) · 上传按钮 1250..1293(44) · 底栏 1330..1413(84)（保存 x16..208 193 / 去补全资质 x221..413 193）· 无 TabBar · 输入控件 0；
  **两次独立测量 95 字段全等**（`cmp-序号10.1-两轮.txt`，0 差异）；**像素级对照**实现截图 vs 设计截图同列 215 页面底色带逐段吻合
  （锁定提示 621..671 · 卡间隙 693..702 · 简介框 899..962 · 卡4/底栏间隙 1315..1329）；行2 橙角标色带实现 x340..387 vs 设计 x339..387；
  像素墨迹核验顶部带仅返回箭头+标题+胶囊（右留白 24，无载体污染）· 底栏右留白 16；截图 `logs/screenshots/20260916-0304-序号10.1-供应商档案-h5-430宽.png`（430×1414）；
  **浏览器内真实交互（phase2/3/4）**：点「保存」→ serve.py 日志实测 **`PUT /api/v1/provider/profile`**（body 12 个数据字典字段）→ toast「保存成功」→ 完整度 **72%→78%**（取自响应）且进度条 width 78%；
  四个入口（编辑/管理/上传新资质/去补全资质）各自实测 iframe hash → `#/pages/profile-edit/index`；点返回 hash 不变（navigateBack 无栈）。
- **工具/流程踩坑（已写进 `.agents/skills/dev/SKILL.md` §4.9）**：①图标行盒 = 字号×1.5（见上）；②无头 Chrome 会**静默不写文件**
  （本轮 dump 字节数与上一轮完全相同 → 差点拿旧证据当新证据；规矩 = 查 mtime + 字节数 + **只在新版本里出现的标记串**）；
  ③`--screenshot=<中文路径>` 被 MSYS 参数转码搞坏、Chrome 静默不落盘 → 先写 ASCII 临时路径再 `mv`；
  ④H5 交互回放要**轮询等元素就绪再点**、hash 要**延迟 700~900ms 再读**（click 后立即读会拿到旧值，误判「没跳转」）；
  ⑤`serve.py` 启动必须重定向 stderr 到文件（否则「真实请求」证据随进程消失）。
- ⚠️ 待人类拍板（不阻塞本轮，15 条全部写进台账序号 10.1 备注）：①完整度/闸门提示在 22 份 PRD 零命中 → 只在服务端给数字时渲染，闸门文案（含「还缺 2 项」）为设计常量不派生；
  ②省市/地址/官网/职务/简介字段名为推断；③18-API 只列路径 → GET/PUT 方法为推断；④「上传新资质」落编辑页（本页固定三行、无新增行位、分类码全 PRD 无定义 → 不臆造 POST/category）；
  ⑤「编辑」「管理」「去补全资质」同落 page-10-2；⑥只读页有「保存」而 PRD 无该页保存语义 → 按序号 10 同义的 /provider/profile 实现；⑦资质审核状态字段未定义 → 已上传行统一「已通过」；
  ⑧上传日期字段未定义 → 取 uploaded_at/created_at；⑨第 3 行分类码取 OTHER；⑩手机号脱敏四处口径不一致 → 服务端 mask 优先、否则按设计格式；⑪空值占位「—」；⑫toast 文案占位；
  ⑬图标 CSS 占位；⑭字号度量差异（胶囊设计 95/实测 91、锁定角标 128/125）；⑮进度条填充设计 259/实测 258。

✅ 序号 11 已于 2026-09-16 03:11~03:28 轮完成（见上方本轮块；现为「部分」，15 条待拍板已记台账）。

🟢 本轮（2026-09-16 02:30~02:52，租约 aap-tdd-run-20260916-0230 → 已释放）· **序号 10「供应商档案编辑 2」（page-10-2）收口**：
- **Calicat 侧**：`calicat_source.py page` 直接可用（无需先拉起浏览器）；page-10-2 设计树（93KB / 172 节点）+ 截图已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 15/17-spec/18-API + 设计稿控件语义。
  **新增可复用工具**：`count-text.py`（量设计文本长度，核对字符计数控件）、`grep-dump.py`（dump-dom 里抓上下文，排查 uni H5 真实 DOM）、
  `show-measure10.py`（按 phase 取数 / cmp 两 phase）、`cmp-measure-runs.py`（**两次独立测量的同一 phase 逐字段比对** = H5 版「连跑两轮一致」）。
- **这页到底是什么**：顶栏（返回 /「编辑主体档案」17px Bold / 右侧「72%」完整度胶囊 r12 #EFF6FF）· 卡1 主体信息（企业名称*/USCC*+绿勾/供应商类型* 三 chip〔原厂·渠道商·中转商，渠道商选中〕/
  所在地区* 省+市两个选择框/详细地址*/官网〔占位「请输入企业官网地址」〕）· 卡2 联系信息（联系人*+职务、手机号*+邮箱 两列；公司简介 + 右上计数）·
  卡3 资质文件（右上「支持 JPG/PNG/PDF，≤10MB」；三行固定：营业执照〔必传+已上传**双角标**+文件名+删除+查看〕/上游授权书〔条件必传+「点击上传，仅支持单个文件」〕/其他选传资质〔描述〕）·
  底栏「保存草稿」156×48 + 「保存」自适应×48 #2563EB；**无 TabBar**，设计总高 1409。
- **TDD（3 切片逐切片红→绿 + 1 次补红；新增 61 例）**：`tests/unit/profile-edit-model.spec.ts`(29) · `tests/unit/provider-profile-api.spec.ts`(7) ·
  `tests/pages/profile-edit.spec.ts`(25)；红基线 `evidence/red-序号10-切片1/2/3.txt`（切片2 = `providerApi.saveProfile is not a function`）；
  实现 `src/utils/profile-edit-model.ts`、`src/api/provider.ts`（+saveProfile/qualifications/uploadQualification/removeQualification、补全档案字段）、
  `src/pages/profile-edit/index.vue`、`pages.json` 路由；**tokens 0 新增**（19 个色值全部命中既有 tokens.scss）；
  绿 **532/532 连跑两轮一致**（`evidence/green-序号10-轮1/轮2.txt`）+ `npm run type-check` **exit 0**。
  3 处失败是我自己测试写错（`attributes('value')` 读不到 v-model 的 DOM 属性、字符串长度数错），按真实行为改断言后才绿。
- **由设计截图像素量尺定死的几何（design.tree.json 的几何算不出卡高）**：顶栏 **96** · 卡1 **108..687(579)** · 卡2 **698..1042(345)** · 卡3 **1057..1308(251)** ·
  底栏 **1324..1408(84)** · 页高 **1409**；卡内头部 **27**（= 图标 18px 段落的 1.5 行高，不是标题的 18）· 字段 = 标签 18 + 8 + 框 44 · 字段/卡间距 16/12；
  框位 197/283 · chips 369..409 · 地区 451..495 · 537..581 · 623..667 · 卡2 787/872 · 简介框 957..1021 · 资质行 1119/1181/1243（各 46）。
- **★ 本轮最值钱的一条规矩（已写入 dev SKILL §4.8）：设计稿的 stroke 有的画在盒外、有的画在盒内，必须逐个量**——
  ①**卡片 / chips / 简介框 = 盒外**：卡高 579 = 20 + 内容 + 20（不含描边）、chip 声明 40 而可见 42 → 用 `border` 会多占 2px 并把**卡内每个字段整体下推 1px**；
  改用 `box-shadow: 0 0 0 1px`（ring）后卡高 579/345 与设计**逐值相等**、页高正好 1409。
  ②输入框 / 未上传缩略图 = 盒内（声明 44 可见 42）→ 保留 `border`。
  ③`.field + .field` 这类相邻选择器会把**两列行里的第二个半栏**也加上 margin-top（实测职务框 top +16）→ 必须写 `.card > .field`，并把卡头 margin-bottom 归零（否则首字段双份 16）。
- **vision 与 DOM 数字再次互补**：本轮 vision 唯一抓到的是**结构错**——设计的「必传」是红底角标、「已上传」是绿底独立角标（两枚），我第一版合并成一枚「必传 已上传」；
  回设计截图横向量色带证实（红 #FEF2F2 x157..191、绿 #ECFDF5 x202..261）→ 先补红断言（`evidence/red-序号10-补红-双角标.txt`）再拆成两枚；
  修后实现 y=1132 行色带 **155..190 红 / 200..253 绿**（对设计 ±1~6px，差在字体度量）。
- **客观证据链**：`build:mp-weixin` 产出 `pages/profile-edit/{js,json,wxml,wxss}`（app.json 已注册）；430 宽 iframe + 无头 Chrome 实测 `evidence/measure-序号10-430宽.json`：
  `docScrollWidth 430` · 溢出 **0** · 设计文案缺失 **[]** · 输入值缺失 **[]** · 占位渲染 ✓ · 页高 **1409（=设计）** · 卡 h579/345/253 · 资质行 1119/1181/1243 · 底栏 1325..1409 · 无 TabBar；
  **两轮独立测量 85 字段全等**（`cmp-measure-runs.py`，0 差异）；截图 `logs/screenshots/20260916-0247-序号10-*.png`（430×1409）+ `png-bands v 26` 与设计逐段吻合 + 顶部带墨迹右留白 281（无载体污染）；
  **浏览器内真实交互**：类型 chip 切换 ✓ · 简介 → `5/200` ✓ · 清空企业名称点保存 → toast「请输入企业名称」且无写请求 ✓ · 保存草稿 → 本地 draft 落盘 ✓ ·
  保存 → serve 日志实测 **`PUT /api/v1/provider/profile`**（body 含 12 个数据字典字段）→ toast「保存成功」+ 完整度 72%→78%（取自响应）✓ ·
  删除资质 → 真实 `uni-modal`（删除资质文件 / 确认删除该资质文件？删除后不可恢复。/ 取消·确定）→ 确认 → 日志实测 **`DELETE /api/v1/provider/qualifications/q1`** → toast「已删除」→ 重新 GET 列表 ✓。
  **新增独立 mock 集** `.agents/state/h5-measure/api-10-2/`（不与既有 `api/` 混用：同一 `/provider/profile` 在两个设计帧里公司名样例不同，不能共用一个 fixture）。
- ⚠️ 待人类拍板（不阻塞本轮，14 条全部写进台账序号 10 备注）：①省市/地址/官网/职务/简介/完整度零命中 → 字段名与归属推断；②18-API 只列路径 → 方法推断；
  ③资质分类码与 aap_provider_qualification 字段级 schema 无定义；④无文件上传接口 → 只登记元数据；⑤「保存草稿」PRD 无草稿语义 → 本地草稿；
  ⑥保存后跳转目标无依据 → 停留本页；⑦「查看」无接口 → client-only 占位；⑧校验/toast/弹窗文案无稿 → 占位；⑨占位文案多为推断；
  ⑩设计计数 48/200 与 40 字不自洽 → 按真实长度；⑪类型→industry_category 映射顺序推断；⑫原生 region picker 交互仅单测覆盖；⑬图标 CSS 占位；⑭删除后 mock 固定返回未删数据。

⏳ 下一步（下一轮）：台账序号 **10.1「供应商档案 2」**（page-10-1-2，`/pages/profile/index`）——本页保存/返回的落点，按 §2 八步走；
  可复用本轮全部工具链：`api-10-2` 式**独立 mock 集**、`__measure-profile-edit.html` 载体模板、`cmp-measure-runs.py` + `show-measure10.py`、`png-bands` 反推盒边界；
  **先量 stroke 在盒内还是盒外再写 CSS**（本轮最大教训）。

🟢 本轮（2026-09-16 02:10~02:30，租约 aap-tdd-run-20260916-0210 → 已释放）· **序号 9「模型报价设置/新增报价单」（page-9）收口**：
- **Calicat 侧**：`get_canvas_list` 直接可用（未再需要 `cmd /c start`）；page-9 设计树（79KB / 159 节点）+ 截图已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 10/17-spec/18-API + 画布页码。
  **顺手核对同名疑点**：page-26「新增报价单-初始态」是**独立帧**（step 条/报价单号「系统生成」/空态提示），
  与 page-9（已填态 + 模型列表）文本差集不同 → 不是重复页；新脚本 `diff-node-text.py <nodesA> <nodesB>` 做差集。
- **这页到底是什么**：顶栏（返回 /「新增报价单」18px Bold /「填写基本信息并设置模型报价」12px / 帮助按钮）·
  卡1 报价主体（chip「去新增」+ 主体公司选择框〔公司名 13px SemiBold + 统一社会信用代码 11px〕+ 红星说明）·
  卡2 基本信息（chip「已完善」+ 报价单名称输入 + 「12/30」字数 + 凭证选择框〔别名 + 脱敏 key〕+ 绿字「已自动带出该凭证下 5 个可用模型」）·
  卡3 模型列表（chip「已选 3 / 5」+ 工具栏「全选模型 / 按凭证实时带出」+ 5 模型行〔勾选框 / 名称 14px SemiBold / 厂商标 / 「输入 $2.50 / 输出 $10.00 / 1M token」/ 状态标 已选|可选 / chevron〕+ 底部计价说明）·
  卡4 蓝色提示卡 · 底栏「存为草稿」(128×48) + 「保存」(fill×48 #2563EB)；**无 TabBar**，设计总高 1211。
- **TDD（3 切片，逐切片红→绿；新增 47 例）**：`tests/unit/quote-setup-model.spec.ts`(18) · `tests/unit/quote-create-api.spec.ts`(5) ·
  `tests/pages/quote-setup.spec.ts`(24)；红基线 `evidence/red-序号9-切片1/2/3.txt`（切片2 = `quoteApi.create/setItems is not a function`）；
  实现 `src/utils/quote-setup-model.ts`、`src/api/quote.ts`（+create/setItems）、`src/pages/quote-models/index.vue`、`pages.json` 路由、
  `src/api/provider.ts` 补 aap_provider 字段、tokens **新增 3 个**（#F0F0F0 / #189A47 / #777777）；
  绿 **471/471 连跑两轮一致**（`evidence/green-序号9.txt`）+ `npm run type-check` **exit 0**。
- **由设计像素反推抓出的真偏差（vision 完全看不出）**：卡1 少了设计 `5f243d40` 的 **padding-top 8** → 主体选择框实测 top 170（设计 178）、卡高 140（设计 ~148）：
  补 `.field__inner{padding-top:8px}` 后 **top 178 = 设计 178**、卡高 148、页高 1202（设计 1211，余下 -9 = 工具栏 40 vs 设计推导 37 + 文本行盒取整）。
  新工具 `png-bg-runs.py <png> <x> [hex] [minLen]`（沿列找**页面底色色带** = 卡间隙，用来反推卡片边界；比 png-bands 直接读整列更抗文字墨迹）。
- **客观证据链**：`build:mp-weixin` 产出 `pages/quote-models/{js,json,wxml,wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号9-430宽.json`（dump 留证）：`docScrollWidth 430` · 溢出 **0** ·
  文案缺失 **[]（need 44 条设计文本，含 5 条价格模板与提示卡换行）** · 卡 h 148/280/434 @top 118/282/578（设计与 118/578 完全一致）·
  模型行 5×{x32 w366 h58} · 底栏 h98 固定 · 无 TabBar；
  **浏览器内真实交互**：勾第 4 行 → `已选 4 / 5`；全选 → `5 / 5`；再全选 → `0 / 5`；填名称 → `12/30`；
  点「保存」→ serve.py 日志实测 **`POST /api/v1/quotes body={name,provider_id,credential_id}`** + **`POST /api/v1/quotes/q9/items body={items:[{model_name}]}`** → toast「保存成功」；
  截图 `logs/screenshots/20260916-0225-序号09-模型报价设置-h5-430宽.png`（430×1202）+ png-ink 核验顶/底带（右留白 30/16，无载体污染）。
- **平台坑（新，已写进 `.agents/skills/dev/SKILL.md` §4.2）**：**载体页给 uni-app H5 的 `<input>` 填值必须写「内层原生 input」**——
  `data-testid` 落在 **`<uni-input>` 宿主**上，给宿主设 `.value` + 派发 input **不触发 v-model**（实测字数一直 `0/30`、保存被「请输入报价单名称」拦住）；
  正解 = `host.querySelector('input')` 再派发 input 事件，且 uni 侧更新有 **~1s 延迟**（实测 1s 后才出现 `12/30`）。
- ⚠️ 待人类拍板（不阻塞本轮，11 条全部写进台账序号 9 备注）：①画布页名写「…-列表」但帧内容是「新增报价单」已填态，
  与序号 12-v1 `/pages/quote-form/index`（初始态）是否合并同一路由待拍板；②「报价单名称」PRD/数据字典**无对应列** → 提交体用 `name`（推断）；
  ③18-API 只列路径 → POST /quotes、/quotes/{id}/items 方法与字段级 schema 为推断；④18-API 无「我的公司」列表接口 → 「下拉」退化为单主体（profile）；
  ⑤`credential_id` 不在 aap_quote（全 PRD 零命中）→ 关联字段为推断；⑥模型参考价无接口依据 → 取 model_list 的 price，缺失不渲染价格行；
  ⑦设计「13/30」与 12 字示例不自洽 → 按真实长度；⑧「已选/可选」判定来源未定义 → 取 selected 标记；⑨保存后跳 `/pages/model-pricing/index?quoteId=` 为推断（该页未实现，H5 hash 不变）；
  ⑩toast 与校验文案无设计稿 → 占位；⑪图标仍为 CSS 形状占位。

⏳ 下一步（下一轮）：台账序号 **10「供应商档案编辑 2」**（page-10-2，`/pages/profile-edit/index`）——本页「去新增」正是跳它，
按 §2 八步走；可复用本轮全部工具链：`serve.py`（含 POST/DELETE mock）、`__measure-quote-setup.html` 载体模板、
`png-bg-runs.py` 反推卡片边界、**注意验证表单填值要走内层原生 input**（宿主 uni-input 设 value 无效）。
（序号 1~9 均已实现并留证，状态「部分」= 登记了等人类拍板的缺口，**不要回炉**。）

🟢 本轮（2026-09-16 01:55~02:15，租约 aap-tdd-run-20260916-0155 → 已释放）· **序号 8「报价单列表 2」（page-8-2）收口**：
- **Calicat 侧**：`get_design_page_list` 直接可用（未再需要先 `cmd /c start` 拉编辑器）；page-8-2 设计树（113KB / 240 节点）+ 截图已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 10/17-spec/18-API + 画布页码。
  **新增可复用工具**：`node-probe.py <page-id>`（通用设计树几何探针，替代每页写一个 probe）、
  `png-bands.py <png> v|h <idx> [from] [to]`（沿列/行量同色色带 = 从**设计截图像素**反推真实盒子尺寸；本轮靠它定死「卡高 178、间距 12、操作行 60、TabBar 84、页高 1206」）。
- **这页到底是什么**：顶部导航（「报价单」20px SemiBold + 右侧「+ 新建报价」97×30 r10 #2563EB）· 筛选行 6 chip（全部/草稿/已提交/已驳回/待签署/已完成；active #2563EB 白字 / inactive #F1F5F9+#64748B，高 30 r10 间距 9）·
  5 张报价卡（标题 15px SemiBold / 状态胶囊 h22 r11 dot8×6 / 「报价单号」13px #334155 + 单号 10px #94A3B8 / 元信息「2 个模型 · CNY · 更新于 06-14 15:20」/ 操作行 60 高、链接 40 高**左对齐** x36/112/188(/264)）·
  逐卡操作不同（待签署多「签署」、已完成多「合同」；**「删除」在设计稿里也是蓝 #2563EB 而不是红色** —— vision 报成红色，以 design.tree.json 为准）· 底部 TabBar 84 高、4 项各 104 宽。
- **TDD（3 切片，逐切片红→绿；新增 56 例）**：`tests/unit/quotes-model.spec.ts`(24) · `tests/unit/quote-api.spec.ts`(8) · `tests/pages/quotes.spec.ts`(24)；
  红基线逐切片留证 `evidence/red-序号8-切片1/2/3.txt`（Failed to resolve import，原 368 条不受影响）；
  实现 `src/utils/quotes-model.ts`、`src/api/quote.ts`、`src/pages/quotes/index.vue`、`pages.json` 路由、tokens **0 新增**（色值全部命中既有 tokens）；
  绿 **424/424 连跑两轮一致** + `npm run type-check` **exit 0** + `build:mp-weixin` 产出 `pages/quotes/{js,json,wxml,wxss}`（app.json 已注册）。
  测试基建：`tests/setup.ts` 新增 `uni.showModal` 桩 + `setModalAnswer()`（删除二次确认要用；桩走微任务，与 request 一致）。
- **客观证据链（DOM 数字 vs 设计像素带逐项对账）**：430 宽 iframe + 无头 Chrome 四段实测 `evidence/measure-序号8-430宽.json`：
  phase1/phase2 **60 字段全等**；`innerWidth 430` · `docScrollWidth 430` · 溢出 **0** · 文案缺失 **0**（need = 设计稿 20 条独立文本图层）· 顶栏 **90**（设计 90）· 筛选行 **54**（设计 54）·
  6 chip x16/73/130/199/268/337 高 30；卡 5 张 `x16 w398 h177` top 156/345/534/724/913（设计 156/346/536/726/916、卡高 178 → -1px）· 卡间距 **12**（设计 12）·
  状态胶囊 h22 right 393（设计 394），5 态 bg/dot/text 取色与设计逐值一致（含设计独有的 #FF9500）· 操作行 **h60**、链接 `h40 x37/113/189/265 w64`（设计 x36/112/188/264 w64）·
  TabBar **h84** 固定、`tab x0/109/217/326 w104`（设计 0/108.7/217.3/326）；**像素墨迹核验**（`png-ink.py`）：顶部带 runs `{(16,75),(326,413)}` 右留白 16（无载体页污染）、
  卡1操作行带 runs `45..244` 与设计量得的 `45..244` **完全吻合**；截图 `logs/screenshots/20260916-0208-序号08-报价单列表-h5-430宽.png`（430×1198，vision 复核与 DOM 数字一致）。
- **浏览器内真实交互回放（phase3/phase4，比 mock 断言更硬）**：点「已驳回」chip → chip 高亮 + `serve.py` 访问日志实测 `GET /api/v1/quotes?page=1&pageSize=10&status=REJECTED`；
  点卡1「删除」→ 真实 `uni-modal`（「删除报价单 / 确认删除该报价单？删除后不可恢复。/ 取消 · 删除」）→ 确认 → 日志实测 `DELETE /api/v1/quotes/q1` → toast「已删除」→ 再 GET 列表。
- **工具修复**：`serve.py` ①新增 `do_DELETE`；②写类 mock 从「只找 `post`」改为按方法名找（`MOCK/<path>/<method>`）→ DELETE 才能真正 mock（否则拿不到响应体、日志里也看不到）。
- ⚠️ 待人类拍板（不阻塞实现，10 条全部写进台账序号 8 备注）：①6 个 chip 与 QuoteStatus 不是一一对应（设计无「审核中」→ 现把 REVIEWING/IN_REVIEW/UNDER_REVIEW 归入「已提交」，取 `status=SUBMITTED,REVIEWING`；「待签署/已完成」是合同阶段口径）；
  ②18-API 只列路径未列方法/参数 → GET/DELETE 与 `status` 参数名及取值集合为推断；③卡片标题在 PRD Quote 无字段（**不拿单号冒充标题**，缺失用占位符）；④「N 个模型」计数来源未定义（item_count→items.length）；
  ⑤「更新于」字段未列（用 updated_at，MM-DD HH:mm 不做时区换算）；⑥币种冲突（PRD 写 USD、设计样例 CNY → 原样展示服务端值）；⑦设计无 PRD §4.1 的 提交/撤回/作废 动作，「删除」= DELETE 与「作废 VOID」口径差异待拍板；
  ⑧删除弹窗文案设计无稿 → 占位；⑨空态「暂无报价单」→ 占位；⑩**设计自身越界**：顶部「新建报价」按钮实际 x343..440（宽 97）超出 430 画面 10px、与本帧声明的 padding-right 16 不自洽 → 按「页面零溢出」实现为右对齐 16（实测 x326..414）。


🟢 本轮（2026-09-16 01:35~01:52，租约 aap-tdd-run-20260916-0135 → 已释放）· **序号 7「检测未通过报告 2」（page-7-2）收口**：
- **Calicat 侧**：page-7-2 设计树（62KB，130 节点）+ 截图已抓；`interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 09/17-spec/18-API/13-管理端 + 画布 30 页清单。
  新增探针 `page7-2-probe.py`（全节点几何/填充/内边距/文字 → `page-7-2-nodes.txt`）。
- **这页到底是什么**：顶部（返回 /「检测报告」/ 右上「报告编号 DR-…」）· 未通过封面卡（「综合检测结论」+ 通道名 / 38px 综合分 54 + 「综合评分·满分 100」+ 红底「未通过」胶囊 /
  红色一票否决条 / 结论措辞）· 分项评分总览卡（「分项总览」+ 8 行 D1 连通性 89 · D2 鉴权 12 · D3 模型一致性 55 · D4 上下文 82 · D5 稳定性 61 · D6 计费口径 66 · D7 合规安全 58 · D8 并发压测 0 +
  灰底权重说明盒）· D2 鉴权有效性 · 详情卡（红描边 + 12 分 + 现象/依据/影响/建议 四行）· 免责声明卡 · 底部白色操作条（导出 PDF 193×44 + 重新提交检测 193×44 #2563EB）；**无 TabBar**、底栏随文档流。
- **TDD（3 个用例文件先红 → 到绿；新增 39 例）**：`tests/unit/report-failed-model.spec.ts`(20) · `tests/unit/detection-job-api.spec.ts`(3) ·
  `tests/pages/report-failed.spec.ts`(16)；红基线 = 2 文件 `Failed to resolve import` + `detectionApi.create is not a function`（`evidence/red-序号7.txt`，原 329 条不受影响）；
  实现 `src/utils/report-failed-model.ts`、`src/pages/report-failed/index.vue`、`pages.json` 路由、`src/api/detection.ts` 新增 `create`（POST /detection-jobs 重测）、
  `src/api/report.ts` 的 `detail<T>` 泛型化（同一端点两种报告模板）、tokens 3 个新色值；绿 **368/368 连跑两轮一致**（`evidence/green-序号7.txt`）+ `npm run type-check` **exit 0**。
- **补红再绿（由 DOM 数字抓出的真缺口）**：H5 取数 `missingTexts` 命中「报告编号 DR-20240614-0312」——设计稿顶部右侧是**单个**文本图层（含前缀），页面只渲染了号码；
  先补断言看红（`evidence/red-序号7-补红-报告编号前缀.txt`：`expected 'DR-…' to be '报告编号 DR-…'`）→ 加 `REPORT_NO_PREFIX` → missingTexts `[]`，report-no 实测宽 **142（设计 143）**。
- **另两个由 DOM 数字抓出并修掉的真偏差**：①分项总览卡 432px（设计 353）——根因 = uni-app H5 的 `<text>` 是 inline，父级 UNI-VIEW 继承默认 **16px** 字号把行盒撑到 24px（设计行高 14.4）→
  给 `.dim__score` 加 `display:block` 后行高 14、卡高 **355**；②权重说明盒 72px（设计 60）——同类 inline 行盒撑高（实测文本块 40 vs 设计 36）→ `.weight-box__text{display:block}` 后 **356×60**；
  ③详情卡四行行距 30（设计 26）→ `.detail__line{display:block}` 后行高 20/行距 26、卡高 165（设计推导 163）；④顶栏 h86（设计 89）→ 返回图标盒按设计 26×28.8 取 29px。
  修后逐项对齐：顶栏 89 · 封面卡 240（= 设计推导 240 完全一致）· 分项卡 355 · 详情卡 165 · 免责卡 70 · 底栏 80 · 页面总高 1063。
- **客观证据链**：`build:mp-weixin` 产出 `dist/build/mp-weixin/pages/report-failed/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号7-430宽.json`：phase1/phase2 **74 字段全等**（`evidence/measure-序号7-phase1-vs-phase2.txt`，新脚本 `compare-phases.py`）；
  `innerWidth 430` · `docScrollWidth 430` · 溢出 **0** · 文案缺失 **0**（need 43 条设计原文）· 分项条底 x138 w231 · 填充 89/12/55/82/61/66/58/0% 取色 绿/红/琥珀；
  **浏览器内真实交互回放**（carrier phase3/phase4）：点「导出 PDF」→ toast「导出链接已生成，请在浏览器中打开」；点「重新提交检测」→ 真实 `POST /api/v1/detection-jobs body={"credential_id":"c1"}`
  → iframe 跳到 `#/pages/detecting/index?jobId=j7` 并渲染出「检测进行中」，`serve.py` 日志**连续 21 对** `GET /api/v1/detection-jobs/j7{,/results}`；
  像素墨迹核验顶部带仅返回箭头+标题+报告编号（右留白 24）· 分项卡右留白 37 · 底栏按钮右留白 16；截图 `logs/screenshots/20260916-0148-序号07-检测未通过报告-h5-430宽.png`（+ 顶部带裁剪图）。
- **工具修复**：`serve.py` 的写类请求（POST）现在支持 mock（`MOCK/<path>/post`）——否则「重新提交检测」拿不到 job_id，只能靠默认 `{"id":"c1"}`；
  载体页新增 `?noaction=1` 模式（交互回放会把 iframe 导航走，导致截图截到下一页——本页第一次截图就截成了「检测进行中」，已修）。
- ⚠️ 待人类拍板（不阻塞本轮，10 条全部写进台账序号 7 备注）：①设计 D1–D8 名与 09-PRD §2 的 D 列表**口径不同**（设计「D2 鉴权」PRD 零命中）→ 以服务端返回为准；
  ②一票否决维度冲突（设计「D2 鉴权」vs R-20 / 13-管理端「D7<40」）；③配色阈值取 **70/40**（09-PRD pass_score 70 + R-20 否决线 40；与设计样本自洽，未用 80/40）；
  ④分项条宽设计自身不自洽（6/8 行 ≈ 分值%，D1/D4 偏短）→ 统一按分值%，D8=0 保留 4px 残段；⑤字段级 schema 缺失（verdict/veto_note/dims[].name/detail.lines 无表可依）；
  ⑥18-API 只列路径未列方法（GET/POST 为推断）；⑦「重新提交检测」= PRD §5 重测（人工点击）→ POST /detection-jobs 只带 credential_id；⑧导出响应体无字段级 schema；
  ⑨图标仍为 CSS 形状占位；⑩**跨页发现：序号 6 顶部同样缺「报告编号」前缀**（本页已按设计补齐，序号 6 待回炉时一并修）。

⏳ 下一步（下一轮）：台账序号 **8「报价单列表 2」**（page-8-2，`/pages/quotes/index`）——检测链路之后的报价管理首页，按 §2 八步走；
  可复用 `compare-phases.py` + `extract-measure-json.py` + `serve.py`（POST mock）+ 载体页 `?noaction=1` 截图模式（**记得 build:h5 之后重拷载体页**）。

🟢 本轮（2026-09-16 01:16~01:40，租约 aap-tdd-run-20260916-0115 → 已释放）· **序号 6「大模型检测报告 · 多维度专业版」（page-6）收口**：
- **Calicat 侧**：page-6 设计树（425KB，411 图层容器 + 622 文本）+ 截图已抓；`interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 09/17-spec/18-API/21-验收 + 画布 30 页清单。
  新增探针脚本 `page6-probe.py`（长文本全文 + 容器几何）与 `subtree-6.py`（按 id 导子树取色/取间距），产物 `page-6-probe.txt` / `page-6-subtree.txt`。
- **这页到底是什么**：顶部（返回 / 「检测报告」/ 右上报告编号 DR-…）· 结论封面卡（图标+「综合检测结论」+通道名 / 40px 综合分 92 + 结论标签「通过」/ 状态四格
  「7/8 通过项 · 1 项 不可测 · 较高 置信度 · 未触发 一票否决」/ 结论措辞盒 / 信息清单 5 行）· 关键指标卡（核心 6 项，2 列 174×84 子卡）·
  维度总览卡（六边形雷达 176×176 + 6 轴标签 + 6 行均分条 + 3 项图例）· 全维度明细卡（说明行 + A–G 7 分组 55 项 + 权重说明盒）·
  风险发现卡（4 条）· 原始证据卡（6 行）· 免责声明卡 · 底部操作条（导出 PDF 126×48 + 填写报价 238×48）；**无 TabBar**。
- **TDD（3 个用例文件先红 → 到绿；合计 55 例）**：`tests/unit/report-model.spec.ts`(34) · `tests/unit/report-api.spec.ts`(5) ·
  `tests/pages/report.spec.ts`(16)；红基线 = 3 文件 `Failed to resolve import`（`evidence/red-序号6.txt`，275 条原用例不受影响）；
  实现 `src/utils/report-model.ts`（视图模型 + 雷达几何 + SVG data-URI）、`src/api/report.ts`、`src/pages/report/index.vue`、`pages.json` 路由、
  `tests/fixtures/report-fixture.ts`（**设计稿 55 项逐字抄录**作为文案一致性依据）；绿 **329/329 连跑两轮一致**（`evidence/green-序号6.txt`）+ `npm run type-check` **exit 0**。
- **补红再绿（真实缺口）**：vision 复核发现「雷达 6 轴标签（性能/吞吐/一致性/指纹/计费/安全）没渲染」→ 先补断言（`evidence/red-序号6-雷达轴标签.txt`：
  `expected [] to deeply equal [...]`）→ 加 `.radar__canvas` + 按设计坐标绝对定位 6 个 label → 复跑 329/329 全绿。
  **教训：vision 对"少了什么"比 DOM 数字更敏感，反之 DOM 数字对"多了/溢出什么"更敏感——两者都要跑。**
- **客观证据链**：`build:mp-weixin` 产出 `dist/build/mp-weixin/pages/report/{index.js,index.json,index.wxml,index.wxss}`；
  430 宽 iframe + 无头 Chrome **两段实测** `evidence/measure-序号6-430宽.json`：phase1/phase2 关键数字**全等** —— `innerWidth 430` · `docScrollWidth 430` ·
  `docScrollHeight 4886` · 溢出 **0** · 文案缺失 **0**（need 含 80+ 条设计原文）· 指标子卡 6×{174×84 @x36/x220} · 雷达 img 176×176 @x127（src=`data:image/svg+xml;base64,…`）·
  轴标签 6 个坐标与设计一致 · 均分行 fill 86/84/92/90/94/92% + 色点 #2563EB/#0891B2/#16A34A/#7C3AED/#D97706/#E11D48 · 明细 7 分组 **55 项** ·
  计分行条 {x194 w162 h6}（与设计完全一致）· 状态胶囊 未申报 #FFFBEB / 仅证据 #F1F5F9 · 一票否决提示盒 #F5F3FF · 底栏 {x16 w398 h72} · 导出 126×48 / 填写报价 238×48 #2563EB；
  像素墨迹核验顶部带右留白 **16**（仅返回箭头+标题+报告编号 → 无载体页污染）；截图 `logs/screenshots/20260916-0135-序号06-*.png`（顶部/雷达区/明细与风险）。
- **抓出的真偏差（由数字对比，非 vision）**：①未计分行「名称 150 + 占位 163 + 标签 62 + 间距 16 = 391 > 卡片内宽 358」→ 设计自身横向不自洽（+33），
  实测该行两个 flex 子项被压缩（名称 135 / 占位 145）且产生 1 处溢出 → 改 `flex-shrink:0` + 占位条 `flex:1`（实测 x194 w130）后**溢出 0**；
  ②雷达轴标签整块缺失（见上）。
- **新增工具**：`show-measure6.py`（按 phase + 字段名取数，替代页面专用的 show-measure.py）；载体页 `__measure-report.html`（含 `#sink` 隐藏取数区、
  溢出元素带 left/w/h/outerHTML、uni-image 内层取 src）；mock `api/v1/reports/DR-1/{index,export}`。
- ⚠️ 待人类拍板（不阻塞本轮，11 条全部写进台账序号 6 备注）：①设计 7 组 55 项与 09-PRD 的 D1–D8 **编号/口径完全不同**（55 项名在 22 份 PRD 零命中）→ 一律以服务端返回为准；
  ②一票否决口径冲突（设计「行为指纹 <0.70」vs 09-PRD「D7<40」）；③置信度措辞（设计「较高」vs PRD「高/中/低」）；④18-API 只列路径未列方法 → GET 为推断；
  ⑤导出响应体无字段级 schema；⑥`duration_text`/`cost_*` 在 18-API 无定义；⑦未计分行设计不自洽（已按零溢出实现）；⑧「一票否决说明」写死挂在 D 组；
  ⑨雷达轴短名 ≠ 明细分组名（两组文案分别固定）；⑩mp-weixin 无内联 svg → 雷达走 SVG base64 data-URI `<image>`；⑪图标仍为 CSS 形状占位。

⏳ 下一步（下一轮）：台账序号 **7「检测未通过报告 2」**（page-7-2，`/pages/report-failed/index`）——与序号 6 同族的失败态报告，按 §2 八步走；
可复用 `report-model.ts` 的骨架 + `__measure-report.html` 载体页 + `show-measure6.py` 取数（**记得 build:h5 之后重拷载体页**，且截图后核验顶部墨迹）。

🟢 本轮（2026-09-16 01:00~01:14，租约 aap-tdd-run-20260916-0100 → 已释放）· **序号 5「检测进行中」（page-5-2）收口**：
- **Calicat 侧**：`cmd /c start` 拉起编辑器后 page-5-2 设计树（129 图层）+ 截图已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD 09/14/15/17-spec/18-API + 画布 30 页清单。
- **这页到底是什么**：顶部（返回 / 「检测进行中」/「进行中」徽章 + 9×7 蓝点）· 总进度卡（「总进度」+「58%」+ 进度条 +
  「已完成 7 / 12 个检测项」「预计剩余 42 分钟」+ 绿色成本保护块两行）· 分项检测 8 行三态（完成 / 进行中 / 排队中）·
  提示卡 · 底部「查看历史检测报告」；**无 TabBar**、无固定底栏（底栏在文档流里）。
- **TDD（3 个用例文件先红 → 到绿）**：`tests/unit/detection-api.spec.ts`(5) · `tests/unit/detecting-model.spec.ts`(12) ·
  `tests/pages/detecting.spec.ts`(13)；红基线 = 3 个文件 `Failed to resolve import`（`evidence/red-序号5.txt`，
  原 245 条不受影响）；实现 `src/api/detection.ts`、`src/utils/detecting-model.ts`、`src/pages/detecting/index.vue`、`pages.json` 路由；
  绿 **275/275 连跑两轮一致**（`evidence/green-序号5.txt`）+ `npm run type-check` **exit 0**。
  本页 **不需要新增 token**（14 个色值全部命中既有 `tokens.scss`）。
- **客观证据链**：`build:mp-weixin` 产出 `dist/build/mp-weixin/pages/detecting/{index.js,index.json,index.wxml,index.wxss}`；
  430 宽 iframe + 无头 Chrome **两段实测**（跨一次 5s 轮询）`evidence/measure-序号5-430宽.json`：
  `docScrollWidth 430` · 溢出 0 · 文案缺失 0 · 行数 8 · 顶栏 h84 · 卡片 x16 w398 · 进度条 `x36 w358 h10`（轨道 rgb(226,232,240) /
  填充 rgb(37,99,235) 宽 208 —— 设计 209）· 成本块 h52 bg rgb(236,253,245) · 图标块 32×32 三态色
  rgb(236,253,245)/rgb(239,246,255)/rgb(248,250,252) · chip h22 文字色 rgb(21,128,61)/rgb(37,99,235)/rgb(100,116,139) ·
  行间距 12（top 347→655 每行 44）· 提示卡 h68 · 底栏 h84 按钮 398×48 · 页面高 888；**phase1 与 phase2 关键数字全等**；
  **真实轮询**由 `serve.py` 访问日志证实（连续成对 `GET /api/v1/detection-jobs/j1` + `/results`）；
  像素墨迹核验顶部带/提示卡/底栏右留白 24/58/150 均未触边（顶部带仅返回箭头+标题+徽章 → 无载体页污染）。
  截图 `logs/screenshots/20260916-0112-序号05-检测进行中-h5-430宽.png`。
- **抓出的真偏差（由数字对比，非 vision）**：提示卡片 padding 误用 20（设计 c960eff4 为 **16/20**）→ 卡高 76 修正为 68；
  `measure-序号5-修前430.json` 与修后对照留证。
- ⚠️ 待人类拍板（不阻塞本轮，全部写进台账序号 5 备注）：①设计 8 行名（网络连通性…峰值并发压测）在 22 份 PRD **零命中**，
  09-PRD §2 的 D1–D8 是 TTFT/P50 延迟/一致性/RPM/TPM/缓存命中/模型指纹/真实源 → 行名以服务端 probe_name 为准、缺失回退 PRD 短名；
  ②设计「已完成 7 / 12 个检测项」与画布 8 行**不自洽** → 进度取服务端 `progress`（missing-prd）否则按条数派生；
  ③17-spec ProbeStatus（SUCCESS/FAILED/SKIPPED/NOT_MEASURABLE）无 RUNNING/QUEUED，而设计有三态 → 映射字典 + 未覆盖状态原样直显；
  ④`DetectionJob.status` 三份 PRD 三套枚举（15-数据字典 / 14-领域模型 / 17-spec）；⑤设计无完成/失败态 → 本页不自动跳报告页（待拍板）；
  ⑥08-PRD 要求本页显示「已消耗 token 与成本」而设计稿无该区块 → 未实现（以设计稿为准）；⑦详情行度量摘要（「已通过 · 236ms」）
  缺字段级定义（missing-prd）；⑧轮询间隔 5s 为前端取值（PRD 未定义，missing-prd）。

⏳ 下一步（下一轮）：台账序号 **6「大模型检测报告 · 多维度专业版」**（page-6，`/pages/report/index`），按 §2 八步走；
  测量可复用 `.agents/state/h5-measure/__measure-detecting.html` 模板与 `serve.py`（**记得 build:h5 之后重拷载体页**）。

✅ 已于 2026-09-16 01:00~01:14 轮完成（见最上方本轮块；序号 5 现为「部分」，8 条待拍板已记台账）。

🟢 本轮（2026-09-16 00:45~01:05，租约 aap-tdd-run-20260916-0045 → 已释放）· **序号 4-v1「接入凭证-表单」（page-24）收口**：
- **取件规则修正**：`list-pending.py` 之前只把 `已验证` 当完成 → 「部分」行（1/2/3/4）每轮都被重新取到，与「别回炉」矛盾。
  已改为 `DONE = {已验证, 部分}`、`阻塞` 单独列出（本轮实测：待取件 17，最小未完成 = **序号 5**）。新增工具：
  `set-ledger-from-json.py`（台账字段值走 JSON，躲开 bash 里中文/逗号/`$` 的引号地狱）、`show-measure.py`（两段式 measure 取数并支持 `empty|filled`）。
- **设计侧**：page-24 设计树（78 图层）+ 截图已抓；`interaction.json` 仍「不存在图层交互数据」→ 交互真源退 PRD + 画布 30 页清单。
- **这页到底是什么**（此前只有「准入表单变体」一句）：文案为「接入凭证 / 填写客户信息并提交检测」+ 客户名称*/统一社会信用代码*/
  联系人/联系电话 / 检测类型（基础·深度·合规）/ 凭证资料（营业执照 jpg·png·pdf ≤10MB 虚线框）/ 备注 / 提交接入。
  字段与 15-数据字典 `aap_provider` 一一对上（company_name / unified_social_credit_code / contact_name / contact_phone_*），
  资质对应 17-spec `qualification_files`；手机号规则复用 R-01。
- **TDD（3 个用例文件先红 → 到绿）**：`tests/unit/access-application-model.spec.ts`(31) · `tests/unit/access-application-api.spec.ts`(5) ·
  `tests/pages/credential-submit-form.spec.ts`(22)；红基线 = 3 个文件 `Failed to resolve import`（`evidence/red-序号4v1.txt`，原 187 条不受影响）；
  实现 `src/utils/access-application-model.ts`、`src/api/access-application.ts`、`src/pages/credential-submit/form.vue`、`pages.json` 路由；
  绿 **245/245 连跑两轮一致**（`evidence/green-序号4v1.txt`）+ `npm run type-check` **exit 0**。
- **客观证据链**：`build:mp-weixin` 产出 `dist/build/mp-weixin/pages/credential-submit/form.{js,json,wxml,wxss}`；
  430 宽 iframe + 无头 Chrome **两段实测** `evidence/measure-序号4v1-430宽.json`：空态 `docScrollWidth 430` · 溢出 0 · 文案缺失 0 · 必填星号 2 ·
  chip 选中 `#2563EB` · 上传区 `dashed rgb(203,213,225)` · 输入框 44 高 · 备注框 52 高 · 提交按钮 390×48@x20 · 无 TabBar；
  已上传文件态（**在真实浏览器里给 `uni.chooseFile` 打桩后点上传区，走真实 `onPickFile`**）→ 文件行「营业执照扫描件.pdf / 2.4 MB」· 溢出 0。
  像素墨迹核验右留白 30/35/49/20 均未触边；截图 `logs/screenshots/20260916-0100-序号4v1-接入凭证表单-h5-430宽.png`。
- **抓出的真缺陷（工具层）**：`__measure*.html` 用 `left:-9999px` 把取数 `<pre>` 移出视口 → **无头 `--screenshot` 把页外内容也截进去了**，
  vision 看到「顶部黑色 JSON 调试条」（只看 DOM 数字发现不了）。修法：包进 `#sink{width:0;height:0;overflow:hidden}`，
  并用 `png-ink band=0,0,430,60` 复验顶部带（修前满行密集墨迹 → 修后仅返回箭头/标题/扫描按钮）。**已写进 `.agents/skills/dev/SKILL.md` §4.1**。
- ⚠️ 待人类拍板（不阻塞本轮，全部写进台账序号 4-v1 备注）：①「基础检测/深度检测/合规检测」在 22 份 PRD **零命中**、18-API 无入参
  → 只做 UI 选中态、**不进提交体**（有用例钉死）；②「备注」在 `aap_provider` 无对应列 → 同样不进提交体；③**18-API 无文件上传接口**
  （仅 Contract 有 `/contracts/{id}/file`）→ 只登记 file_name/file_size，**文件本体没上传**；④**18-API 无 provider 主体写接口**
  →「企业信息随申请体一起提交」的接口归属是推断（本页最大阻塞项）；⑤18-API 卡片只列路径未列方法 → POST 为 REST 语义推断；
  ⑥统一社会信用代码字符集（GB 32100-2015）未定义 → 只校验 18 位字母数字；⑦设计「客户名称」框是已填值、无占位 → 占位文案为推断；
  ⑧设计整页高 1137 vs 实测 1079（差额 = 设计示例态的文件行 +66 与画布底部留白，非布局缺陷）。

⏳ 下一步（下一轮）：台账序号 **5「检测进行中」**（page-5-2，`/pages/detecting/index`）——它正是序号 4 / 4-v1 提交后的跳转目标，
按 §2 八步走；可复用 `serve.py` 与 `__measure-form.html` 的两段测量模板（**记得 build:h5 之后重拷载体页，且截图后核验顶部墨迹**）。

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
✅ 已于 2026-09-16 00:45~01:05 轮完成（见上方本轮块；序号 4-v1 现为「部分」，待人类拍板的 8 条已记台账）。

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
- 设计树探针：`python .agents/state/node-probe.py <page-id>`（产出 `.agents/state/<page-id>-nodes.txt`，含几何/填充/内边距/文字）
- 设计截图像素量尺：`python .agents/state/png-bands.py <png> v|h <idx> [from] [to]`（同色色带 = 盒子边界；定卡高/间距/栏高最硬的依据）
- 台账取件：`python .agents/state/list-pending.py`（按序号列出未完成页面）
- Calicat CLI：`calicat status` / `calicat tools-call --name get_screenshots --args '{...}'`；
  技能脚本目录 `C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts/`
- gh：`E:\tools\bin\gh.exe`（已登录 geeker-lait）
- 平台坑：中文 Windows `netstat` 是 GBK；`taskkill` 需 `MSYS_NO_PATHCONV=1`；
  bash 把中文塞 JSON body 会变 GBK（要发中文请求体用 Node/Python 的 utf-8）。
