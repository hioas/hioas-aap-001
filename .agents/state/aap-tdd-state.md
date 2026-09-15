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

🟢 本轮（2026-09-16 05:15~05:45，租约 aap-tdd-run-20260916-0515 → 已释放）· **序号 20「站内信列表 2」（page-20-2）收口**：
- **取件**：`list-pending.py -n 1` 最小未完成 = 20（page-20-2，`/pages/messages/index`，台账「设计否」）；开工前 `git status` 干净、
  `git log -1` = 05:10 的 15-合同签署提交 → 空闲租约，写成本轮 id + 45 分钟。
- **Calicat 侧**：`page` 先报「请先在浏览器中打开文件」→ `cmd /c start` 拉起后一次成功；设计树（49KB / 106 节点）+ 截图 **430×760（1:1 帧图）** 已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 **18-API「Audit/Notification」Tag（/notifications、/notifications/{id}/read）**
  + 15-数据字典 `aap_notification`（read_at/channel/event_code/biz_type…）+ 设计稿控件语义。
- **这页到底是什么**：带 TabBar（高亮「我的」）的站内信列表（设计总高 760）：顶部导航 0..86（「消息」20px Bold + 「3 条未读」h22 胶囊 + 「全部已读」）·
  筛选行 86..140（全部/未读/订单/系统 四 chip h30 r10，选中 #2563EB）· 消息列表区 140..676（5 卡 × 92 + 间隙 12：图标 38×38 r12 五色 / 标题 13px SemiBold +
  未读红点 9×8 / 摘要 12px / 时间 11px；3 未读 + 2 已读，已读整行降灰 #94A3B8/#CBD5E1）· 底部 TabBar 84（4 项各 104，图标 33 块 + 3 + 文字 16）。
- **TDD（4 切片，逐切片红→绿；新增 84 例）**：`tests/unit/messages-model.spec.ts`(48) · `tests/unit/notification-api.spec.ts`(9) ·
  `tests/pages/messages.spec.ts`(14) · `tests/pages/messages-flow.spec.ts`(13)；红基线 `evidence/red-序号20-切片1/2/3.txt`（Failed to resolve import）
  + `切片4.txt`（**真红 8/13**：`expected '全部' to be '未读'`、`expected [] to deeply equal [ '/api/v1/notifications/n1/read' ]`、
  `expected [] to contain '/pages/report/index?reportId=r1'`）；绿 **935/935 连跑两轮一致**（`evidence/green-序号20-轮1/轮2.txt`）+ `npm run type-check` **exit 0**；tokens **0 新增**（18 个色值全部命中既有 tokens.scss）。
- **★ 本轮最值钱的取证教训（已写进 dev SKILL §4.16）**：**取数脚本里同名字段会被后写的键静默覆盖** ——
  载体页 collect() 里先写 `titleStyle: styleOf('.messages__title')`、后又写 `titleStyle: styleOf('.msg__title')`，
  于是「顶部标题样式」字段实测读成了**消息行标题**（13px/600），与像素/布局（导航高 86 ⇒ 标题行盒 26）自相矛盾；
  写 `__diag-messages-title.html` 单独探针才发现真值 **20px / line-height 26 / UNI-TEXT.messages__title**。
  **规矩：一个测量对象一个键名（navTitleStyle / msgTitleStyle），数字与像素矛盾时先怀疑取数脚本，再怀疑页面。**
- **相对时间页面的取证套路（新）**：设计文案「10 分钟前 / 2 小时前 / 昨天 18:20 / 3 天前 / 5 天前」是**相对当前时刻**的 →
  ①mock 用 `.agents/state/gen-mock-20.py` 按**运行时刻**反推 created_at（写死时间戳下次就文案对不上）；
  ②单测用 `vi.useFakeTimers({ toFake: ['Date'] })` 只冻 Date（不动 setTimeout，`flushPromises` 才能解析）；
  ③jsdom 把行内 `#RRGGBB` 规范化成 `rgb()` → 断言前用 `rgbOf(hex)` 换算（**改的是测试不是代码**）。
- **客观证据链**：`build:mp-weixin` 产出 `pages/messages/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome 实测 `evidence/measure-序号20-run2.json`：`innerWidth 430` · `docScrollWidth 430` · 页高 **760 = 设计** · 溢出 **0** ·
  文案缺失 **[]（need 26 条设计原文，含 5 条相对时间）** · 导航 0..86 · 筛选行 86..140 · 列表 140..660 · 卡 **5×92 @152/256/360/464/568**（间隙 12）·
  图标 38×38 @x32 · 未读点 9×8 ×3 @233/259/181 · TabBar **676..760(84) 固定** · 输入控件 0；
  **run2/run3 两次独立测量 70 字段全等**（`cmp-measure-runs.py`，0 差异）；**像素对账**（`png-bands v25` 同脚本跑设计与实现）：
  chip 蓝 98..127 · 卡 153..242/257..346/361..450/465..554/569..658 · 卡间隙 245..254 · TabBar 676..759 **逐段吻合（±1~2 AA）**；
  `text-rows.py` 12 个文本带 **9 个 0 差**、其余 +1~2；截图 `logs/screenshots/20260916-0525-序号20-站内信列表-h5-430宽.png`（430×760 = 设计尺寸）；
  顶部带墨迹 runs 仅「消息 + 3 条未读 + 全部已读」（右留白 17，无载体污染）。
  **浏览器内真实交互回放**：`?scenario=filter` 点「未读」→ `chipBgs` 实测 [灰,蓝,灰,灰]（高亮切换）；
  `?scenario=readall` 点「全部已读」→ `serve-5263.log` 实测**连续** `POST /api/v1/notifications/n1|n2|n3/read`（无批量接口 → 逐条）；
  `?scenario=card` 点首条未读卡 → 日志实测 `POST /api/v1/notifications/n1/read` + hash 跳 `#/pages/report/index?reportId=r1`；
  `?scenario=tab` 点「工作台」→ hash `#/pages/workbench/index`。
- **新增可复用工具**：`.agents/state/gen-mock-20.py`（按运行时刻生成相对时间 mock；**凡是相对时间/相对日期页面都该这么做**）、
  `show-m20.py <json> [phase1|cmp|phase2|raw]`、`__measure-messages.html`（含 `?scenario=filter|readall|card|tab` 四个出口回放）。
- ⚠️ 待人类拍板（不阻塞本轮，15 条全部写进台账序号 20 备注）：①18-API 只列路径 → GET/POST 方法与 `unread`/`category` 参数名是 REST 推断；
  ②`aap_notification` 无「分类」列 → 「订单/系统」chip 取值集合为推断（前端只透传）；③18-API **无「全部已读」批量接口** → 逐条 `/notifications/{id}/read`（不臆造 read-all）；
  ④相对时间写法 PRD 零定义 → 派生规则；⑤图标类型 detect/quote/contract/bill/system 由 event_code/biz_type 派生（PRD 无枚举）；
  ⑥徽标「N 条未读」取自当前列表（无汇总字段，超一页不等价全站）；⑦未读判定 read_at 为空（兼容 readAt/read/is_read）；
  ⑧卡片落点 biz_type→路由为推断（CONTRACT/REPORT|DETECTION/QUOTE；未知不跳转）；⑨「全部已读」成功无 toast、失败与加载失败文案为占位；
  ⑩空态「暂无站内信」为占位；⑪图标 CSS 实心圆占位（避开勾选框同形）；⑫TabBar「我的」为当前模块不跳转，/pages/mine/index 属序号 21；
  ⑬**字号度量残差**：chip 实测 48（设计 49）、徽标 58（设计 59）、消息标题 143（声明 144）—— 每 2 个 CJK 字少 1px（浏览器回退字体 vs 思源黑体），**未写死宽度**；
  ⑭H5 mock 静态 → 写操作后列表不变（仍显「3 条未读」），真实请求以 serve 日志为准；⑮本页无 query/storage 入口，入口页待序号 21。

⏳ 下一步（下一轮）：台账序号 **21「我的 2」**（page-21-2，`/pages/mine/index`）——**设计尚未抓取**（台账「设计否」），
  先 `python .agents/state/fetch-design.py page-21-2` 与 `calicat_source.py page --layer-id e537204e-faf7-416b-8669-1347d581490c --page-id page-21-2`，再按 §2 八步走；
  **它就是本页 TabBar「我的」的目标页（同位帧）→ 先 `cmp-frames.py page-20-2 page-21-2` 判是否同页多帧**，
  若 TabBar 完全一致优先抽共用组件（12-v2 的 variantFlags 套路）；可复用本轮：`gen-mock-20.py`（相对时间 mock 生成法）、`show-m20.py` 取数脚本式样、
  `__measure-messages.html` 的 `?scenario=` 多出口回放模板、`cmp-measure-runs.py` 两次独立测量比对。

🟢 本轮（2026-09-16 04:55~05:20，租约 aap-tdd-run-20260916-0455 → 已释放）· **序号 15「合同签署 2」（page-15-2）收口**：
- **取件**：`list-pending.py` 最小未完成 = 15（page-15-2，/pages/contract/index，台账「设计否」）；开工前 `git status` 干净、
  `git log -1` = 04:50 的 12-v3 提交 → 空闲租约，写成本轮 id + 45 分钟。
- **Calicat 侧**：`page` 先报「请先在浏览器中打开文件」→ `cmd /c start` 拉起后一次成功；设计树（56KB / 117 节点）+ 截图 **430×1231（1:1 帧图）** 已抓；
  `interaction.json` 仍「不存在图层交互数据」→ 交互真源退 10-PRD §4.2 状态机 / 17-spec R-41 / 18-API「Contract」Tag + 设计稿控件语义。
- **这页到底是什么**：无 TabBar 的只读「合同签署」详情页（设计总高 1231）：顶栏（返回 /「合同签署」17px Bold / 右「编号 CT-2024-0613-008」11px）·
  合同状态卡（46 琥珀圆角图标 +「API 接入服务合同」15px SemiBold +「待签署」h22 琥珀标 +「请在 2024-06-20 前完成签署，逾期将自动作废」）·
  电子签提示卡（白底描边 + 蓝盾 +「本合同采用电子签章，签署后即时生效并具备法律效力。」）· 合同基本信息 4 行 · 费用与分成 3 行（值右对齐 Bold）·
  关键条款 4 条 · 签署信息 3 行 · 签署记录 2 条（绿点「平台方已盖章」+ 琥珀点「等待供应商签署」）· 底栏（PDF 126×48 描边 + 去签署 260×48 #2563EB）。
- **新增可复用工具与判定法**：`col-bands.py <png> <x> [from] [to]`（逐像素分类 W/B/S/X → **一次拿到全部卡片边界**；
  本页状态卡有柔和投影，`rows-gap` 会把 12px 卡距读成 13px 描边色带）· 设计树声明的 height 逐块加即得卡高，且
  **字段行实测 18 = 12px 文本的 1.5 倍**（`lineHeight:1.2` 只作用于文本盒；图标段落仍是 fontSize×1.5=27）·
  **图标盒宽必须取设计声明值 20/26**（本轮唯一真偏差：提示卡文案盒 x50 / 墨迹 58，设计 x56 / 墨迹 64 —— 页高、卡片 rect、`missingTexts` 全对，只有横向 rect 抓得到）。
- **TDD（4 切片，逐切片红→绿；新增 44 例）**：`tests/unit/contract-model.spec.ts`(19) · `tests/unit/contract-api.spec.ts`(5) ·
  `tests/pages/contract.spec.ts`(11) · `tests/pages/contract-flow.spec.ts`(9)；红基线 `evidence/red-序号15-切片1/2/3.txt`（Failed to resolve import）
  + `切片4.txt`（**真红 8/9**：`expected [] to deeply equal [ { delta: 1 } ]`、downloadFile 未调用、showModal 未弹出）；
  绿 **851/851 连跑两轮一致**（`evidence/green-序号15-轮1/轮2.txt`）+ `npm run type-check` **exit 0**；tokens **0 新增**（15 个色值全部命中既有 tokens.scss）。
- **一处「改的是测试不是代码」**：`pushResponse` 是 FIFO，`mountLoaded()` 已 push 一次详情响应，我在「签署被拒」用例里又手工 push 一次 →
  POST 吃掉详情响应、断言读到 `['签署申请已提交','状态非法流转']`；删掉多余 push 后 9/9 绿（实现无缺陷，规则已记 SKILL §4.15）。
- **客观证据链**：`build:mp-weixin` 产出 `pages/contract/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome 实测 `evidence/measure-序号15-run2.json`：`innerWidth 430` · `docScrollWidth 430` · 页高 **1231 = 设计** · 溢出 **0** ·
  文案缺失 **[]（need 42 条设计原文）** · **7 张卡 top/height 与像素量尺基线逐值 0 差**（108/206/269/465/631/809/975 → 86/51/184/154/166/154/156）·
  底栏 1147..1231(84) · 字段行 pitch 30 · 条款行 pitch 26 · 记录行 1031/1077 · 记录点 11×10 + 色 rgb(22,163,74)/rgb(245,158,11) · 输入控件 0 · 无 TabBar；
  **run2/run3 两次独立测量 83 字段全等**（`cmp-measure-runs.py`，0 差异）；**像素对账**（`text-rows.py` 同脚本跑设计与实现）：27 行文本 **16 行 0 差**、其余 ±1~2；
  顶部带墨迹 runs=[(21,29),(54,70),(72,86),(88,121),(299,308)…(396,413)]（右留白 16，无载体污染）· 底栏带 [(57,70),(80,86),(88,95),(97,103),(154,413)]；
  截图 `logs/screenshots/20260916-0515-序号15-合同签署-h5-430宽.png`（430×1231 = 设计尺寸）；修前偏差留证 `evidence/measure-序号15-run1.json`。
  **浏览器内真实交互回放**：`?scenario=sign` → 真实 `uni-modal`（「确认签署 / 确认对当前合同发起签署？ / 取消 确定」）→ 点确定 →
  日志实测 **`POST /api/v1/contracts/c1/sign`（body 空 —— 18-API 无请求体 schema）** → toast「签署申请已提交」→ **`GET /api/v1/contracts/c1` 重载**；
  `?scenario=pdf` → 日志实测 **`GET /api/v1/contracts/c1/file` 200 → `GET /files/CT-2024-0613-008.pdf` 200**（真实下载、无错误 toast）；
  `?scenario=back` → hash 不变（navigateBack 无栈）。
- **★ 本轮最值钱的取证教训（已写进 SKILL §4.15）**：**uni-app H5 构建把 uni API 以「模块绑定」内联**
  （页面 chunk `import{…N as downloadFile…}from index-*.js`）→ 给 `window.uni.downloadFile` 打桩**打不到真实调用链**
  （patch 确实生效、却一次都没被调用，toast 反而是「合同文件获取失败」）；正解 = **让 mock 返回可达的本地 URL + 用 serve.py 访问日志取证**。
  另实测 H5 的 `window.uni` 上**没有** downloadFile/openDocument（`__diag-uni.html`）→「浏览器里跑通」≠「API 存在」，两条证据分开写。
- ⚠️ 待人类拍板（不阻塞本轮，14 条全部写进台账序号 15 备注）：①**设计/PRD 冲突**：设计帧「电子签章 / 短信验证码签署 / 去签署」 vs
  10-PRD §4.2 + 17-spec R-41 + 数据字典 Contract(sign_channel=OFFLINE)「合同线下、线上电子签一期不做」→ 本轮按设计稿实现，是否下架待拍板；
  ②18-API 只列路径 → GET/POST 方法与 `/sign` 归属为 REST 推断；③详情字段名容错读取（字段级 schema 未定义）；④状态胶囊中文标签为派生（PRD 只有英文状态机）；
  ⑤记录 tone 字段未定义 → 缺省 pending（琥珀）；⑥手机号脱敏三处口径不一致 → 服务端 masked 优先；⑦`/file` 响应无 schema → url/file_url 兼容、缺失只 toast；
  ⑧toast/弹窗文案占位（弹窗按钮用平台默认）；⑨「编号 」前缀连渲染（同序号 7 教训）；⑩状态卡柔和投影为近似值（设计树读不到投影参数）；
  ⑪图标 CSS 占位；⑫只读页无输入控件/无 TabBar，入口未接线（`?contractId=` / storage `aap_contract_id` 直进）；
  ⑬签署方式取服务端 sign_method、缺失退 sign_channel；⑭uni H5 取证规则见 SKILL §4.15。

⏳ 下一步（下一轮）：台账序号 **20「站内信列表 2」**（page-20-2，`/pages/messages/index`）——**设计尚未抓取**（台账「设计否」），
  先 `python .agents/state/fetch-design.py page-20-2` 与 `calicat_source.py page --layer-id <inventory 的 sourceLayerId> --page-id page-20-2`，再按 §2 八步走；
  可复用本轮：`col-bands.py`（一次拿全部卡片边界）、`__measure-contract.html` 载体模板（`?scenario=` 逐个回放 + 真实请求取证 + `apiProbe`）、
  `api-15` 式独立 mock 集、`cmp-measure-runs.py`、`text-rows.py` 像素对账；**新规矩：uni API 的浏览器取证走「可达 URL + serve 日志」，别打 window.uni 的桩**（SKILL §4.15）。

🟢 上一轮（2026-09-16 04:35~05:00，租约 aap-tdd-run-20260916-0435 → 已释放）· **序号 12-v3「新增报价单-保存成功」（page-29）收口**：
- **取件**：`list-pending.py` 最小未完成 = 12-v3（page-29，/pages/quote-form/success，台账「设计否」）；开工前 `git status` 干净、`git log -1` = 04:31 的 12-v2 提交 → 空闲租约，写成本轮 id + 45 分钟（中途续到 06:05）。
- **Calicat 侧**：`cmd /c start` 拉起编辑器后 `page` 一次成功；设计树 41KB + 截图 **430×1018（1:1 帧图）** 已抓；`interaction.json` 仍是「不存在图层交互数据」→ 交互真源退 PRD 10/15/17-spec/18-API + 设计稿控件语义。
  **先用 `cmp-frames.py page-26 page-29` 判同页/异页** → 逐层 diff 显示结构完全不同（成功头部卡 / 结果摘要卡 / 带出模型卡 / 提示卡 vs 步骤卡 / 基本信息卡…）
  → **不是同页帧，新写页面**（没有套 12-v1/v2 的 variant 机制）。
- **这页到底是什么**：无 TabBar 的「报价单创建成功」结果页（设计总高 1018）：
  顶栏（返回 36 圆 /「报价单已创建」18px Bold +「报价单号已自动生成」12px / 关闭 36 圆）·
  成功头部卡（64 绿圆勾 + 「报价单创建成功」+「已保存基本信息并带出模型清单」+ 单号展示条〔「报价单号」11px + 17px 蓝单号 + 复制按钮 h32 #EFF6FF〕）·
  结果摘要卡 5 行（报价单名称 / 凭证名称〔环境小标 h18 #EFF6FF + 脱敏 key〕/ 参与报价模型〔「已勾选 N 个」h18 #ECFDF5〕/ 报价单号〔绿勾 + 蓝字〕/ 当前状态〔灰点 7×6 + 「草稿」h20 #F1F5F9〕）·
  带出模型卡（「已带出模型」+「共 5 个 / 勾选 3 个」+ 两行标签：勾选 3 个蓝底 #EFF6FF / 未勾选 2 个灰底 #F8FAFC）·
  下一步提示卡（图标 + 「下一步可为勾选模型设置输入/输出单价，设置完成即可提交审核。」#EFF6FF）·
  底栏「继续设置模型报价」398×48 #2563EB + 「返回报价单列表」398×48 幽灵。
- **TDD（3 切片 + 1 次补红；新增 37 例）**：`tests/unit/quote-success-model.spec.ts`(20) · `tests/pages/quote-success.spec.ts`(9) · `tests/pages/quote-success-flow.spec.ts`(8)；
  红基线 `evidence/red-序号12-v3-切片1.txt`（`Failed to resolve import @/utils/quote-success-model`）· `切片2.txt`（同页组件缺失）· `切片3.txt`（**7 条真红**：`expected [] to have a length of 1` / `expected [] to deeply equal ['/pages/model-pricing/index?quoteId=q9']`）；
  绿 **807/807 连跑两轮一致**（`evidence/green-序号12-v3-轮1/轮2/轮3.txt`）+ `npm run type-check` **exit 0**。
- **切片3 的红是「先删实现再看红」拿到的**：第一遍把页面连交互一起写完 → 为守铁律，把 5 个 `@tap` 绑定与 5 个 handler 从页面里**删掉**再跑切片3（7 失败）→ 从快照恢复 → 8/8 绿。**新规矩：交互切片也要先看红，别因为「顺手写完了」就跳过。**
- **由类型门禁抓到的真错**：`npm run type-check` 报 `TS2322: '"void"' is not assignable to type 'QuoteChipKey | "unknown"'`（`SuccessStatus.key` 少了 `'void'`）→ 补红断言 `resolveStatus('VOID')` 后修类型 → exit 0。
- **由 DOM 数字抓到的真偏差（vision/肉眼完全看不出）**：首轮 摘要卡 **218**（设计 250）、模型卡 **100**（设计 132）、页高 **954**（设计 1018）——
  根因 = **两张卡片的内边距 16 没写**（`.card` 只给了背景与圆角；`.succ` 自己有 28/16 所以成功卡没露馅），两卡各 -32。修后逐值相等：
  页高 **1018 = 设计** · 成功头部卡 118..374(256) · 摘要卡 390..640(250) · 模型卡 656..788(132) · 提示卡 804..852(48) · 底栏 872..1018(146)。
  **判定法：`rects(doc,'.srow')` 逐行量行盒（38/38/38/40/30）比量整卡更快定位「少了 padding 还是少了行」——行对了而卡矮 = 卡片内边距问题。**
- **客观证据链**：`build:mp-weixin` 产出 `pages/quote-form/{success.js,success.json,success.wxml,success.wxss}`（app.json 已注册 quote-form/success）；
  430 宽 iframe + 无头 Chrome 实测 `evidence/measure-序号12-v3-run2.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 **0** · 文案缺失 **[]（need 27 条设计原文）** ·
  摘要 5 行 440/478/516/554/594 · 环境小标 488..506(h18) · 模型数标 526..544(h18) · 状态标 604..624(h20) + 点 7×6 · 标签两行 708..736 / 744..772（x32/102/203 与 x32/149）·
  单号条 284..346(62,x32..398) · 复制按钮 x320..384 h32 · 主/次按钮 884..932 / 942..990 · 无 TabBar · 无输入控件；
  **run2/run3 两次独立测量 86 字段全等**（`cmp-measure-runs.py`，0 差异）；**像素对账**（`text-rows.py` 同脚本跑设计与实现）：结果摘要标题行/名称行/模型数行/状态行/标签两行/主按钮 **10 行 0 差**，其余 ±1~2；
  `png-ink` 顶部带 runs=[(64,80),(82,99),(102,115),(119,133),(136,152),(154,171)] vs 设计 [(64,80),(82,98),(102,115),(119,132),(136,148),(150,152),(155,170)]（右留白 258 vs 259，无载体污染）· 底栏带 [(16,413)] = 设计；
  截图 `logs/screenshots/20260916-0455-序号12-v3-保存成功-h5-430宽.png`（430×1018）；修前偏差留证 `evidence/measure-序号12-v3-run1.json`。
  **浏览器内真实交互（scenario 逐个回放，新增载体页 `__measure-quote-success.html` + 独立 mock 集 `api-12-v3/`）**：
  copy → iframe 内实测 **`navigator.clipboard.writeText('QT-20240615-0007')`** + toast「报价单号已复制」（`evidence/measure-序号12-v3-copy.json`）·
  primary → hash **`#/pages/model-pricing/index?quoteId=q9`** · secondary / close → **`#/pages/quotes/index`** · back → hash 不变（navigateBack 无栈）·
  `serve-5245.log` 实测 **14 次 `GET /api/v1/quotes/q9` + 13 次 `GET /api/v1/credentials/c1`，0 条写请求**（本页只读）。
- ⚠️ 待人类拍板（不阻塞本轮，12 条全部写进台账序号 12-v3 备注）：①**入口未接线**：画布 page-29 是「保存成功」页，但 12-v1/12-v2 的「保存并继续」现仍直跳模型定价页（= 12-v1 备注④）
  → 本轮按「不回炉已验收页面」只实现本页（支持 `?quoteId=` / storage 直接进入），**是否改保存落点需拍板**；②18-API 只列路径 → GET 方法与字段名（name/title/quote_name、credential_alias、api_key_mask…）为推断（容错读取）；
  ③「共 M 个 / 勾选 N 个」两个数字来源未定义（M=model_list 长度或明细行数；N=明细行数或 model_list.selected）；④环境小标「生产环境」在 22 份 PRD 零命中 → 消费 env_tag，缺则不渲染；
  ⑤凭证别名在本帧无位置 → 仅在脱敏 key 缺失时兜底；⑥关闭/返回列表同落 /pages/quotes/index（reLaunch 清栈）为推断；⑦复制/无单号 toast 文案为占位；
  ⑧**设计帧自相矛盾**：单号信息固定 155 宽装不下 17px 单号（设计帧末位折行）→ 实现单行渲染；⑨图标 CSS 占位（复制按钮宽 64 vs 设计 70）；⑩状态胶囊复用序号 8 STATUS_META，VOID 走中性灰「作废」。

⏳ 下一步（下一轮）：台账序号 **15「合同签署 2」**（page-15-2，`/pages/contract/index`）——**设计尚未抓取**（台账「设计否」），
  先 `python .agents/state/fetch-design.py page-15-2` 与 `calicat_source.py page --layer-id <inventory 的 sourceLayerId> --page-id page-15-2`，再按 §2 八步走；
  可复用本轮：`__measure-quote-success.html` 载体模板（`?scenario=` 逐个回放出口 + `#sink` 隐藏取数区）、`serve.py`（先 `curl` 验 mock 内容）、`cmp-measure-runs.py`（两次独立测量逐字段比对）、
  `text-rows.py` 同脚本跑设计与实现做像素对账、`png-ink` 顶部/底栏带核验；**新规矩：交互切片也先删实现看红再写**（见本轮切片3）。

🟢 上一轮（2026-09-16 04:10~04:35，租约 aap-tdd-run-20260916-0410 → 已释放）· **序号 12-v2「新增报价单-APIKey 下拉展开」（page-apikey）收口**：
- **取件**：`list-pending.py` 最小未完成 = 12-v2（page-apikey，/pages/quote-form/apikey）；开工前 `git status` 仅 1 个未跟踪临时文件、`git log -1` = 04:04 的 12-v1 提交 → 空闲租约，写成本轮 id + 45 分钟。
- **Calicat 侧**：`page` 先报「请先在浏览器中打开文件」→ `cmd /c start "" <design-url>` 拉起后一次成功；设计树（95KB / 108 节点）+ 截图 **430×1129（1:1 帧图）** 已抓；`interaction.json` 仍是「不存在图层交互数据」→ 交互真源退 10-PRD §5.1 / 15-数据字典 / 17-spec / 18-API + 设计稿控件语义。
  **新增可复用工具**：`fetch-design.py <page-id>`（下载设计帧 PNG 到 ASCII 临时路径并打印宽高 —— 之前每轮都要临时写下载脚本）· `cmp-frames.py <pageA> <pageB>`（逐层比对两帧设计树，输出子节点数量/名称差异）·
  `tree-names.py <page-id> [起始节点名] [深度]`（打印某节点开始的名称层级）· `pad-of.py <page-id> <节点名>`（打印某节点父链上的 padding —— 本轮据此定死「凭证说明包裹层 page-26=6 / page-apikey=10」）·
  `node-tree-raw.py <page-id> <id前缀>`（按 id 打印子树；**设计树用 `children` 不是 `kids`**，中文参数在本机 MSYS 会被转码 → 一律走 id 前缀或 `\uXXXX`）· `show-a12v2.py`（本页取数）。
- **这页到底是什么**：page-26（12-v1）**同一页的「凭证下拉展开态」帧**（设计帧 430×1129，无 TabBar）：
  顶栏（返回 /「新增报价单」18px Bold +「填写基本信息并设置模型报价」/ 帮助）· **无步骤卡** · 基本信息卡（**无「为必填项」标**；
  报价单名称* h48 框 + 字数；分隔线；报价单号 +「系统生成」标 + 只读框（**无说明行**）；分隔线；凭证名称* → **展开态选择框**（h48 r[12,12,0,0] 描边 #2563EB + 钥匙底 28×28 +「请选择凭证」+ 上箭头）
  **紧贴**下拉面板（padding 6 r[0,0,12,12] 同色描边）：三行候选项（图标 34×34 r10 + 名称 14px SemiBold + 推荐标「常用」h16 r8 #2563EB + 脱敏副行「sk-prod-••••••••2f9a · 12 个模型」11px #94A3B8；右侧已选=对勾 / 未选=环境标「沙箱」「专用」h20 r10 #F1F5F9）
  + 分隔线 + 底部操作「前往「我的设置」新建凭证」12px Medium #2563EB）· 凭证说明（wrapper pt10）· 模型列表卡（chip「待带出」+ 空态盒 158 高，**无提示卡**）
  · 底栏（说明 + 存为草稿 128×48 + 保存并继续 258×48 #2563EB）。
- **本轮最大结构性决定**：**12-v1/12-v2 是同页两帧 → 抽成共用视图** `src/components/quote-form/QuoteFormView.vue`（新增 `variant` prop + 纯函数 `variantFlags(variant)`）；
  `pages/quote-form/index.vue`（variant=initial）与新增 `pages/quote-form/apikey.vue`（variant=expanded）都只是 5 行薄壳 → **12-v1 的 740 例全绿**、无重复实现。
- **TDD（3 切片 + 2 次补红；新增 38 例）**：`tests/unit/quote-form-variant.spec.ts`(16) · `tests/pages/quote-form-apikey.spec.ts`(13) · `tests/pages/quote-form-apikey-flow.spec.ts`(9)；
  红基线 `evidence/red-序号12-v2-切片1.txt`（`buildCredOptions is not a function`）· `切片2/3.txt`（`Failed to resolve import @/pages/quote-form/apikey.vue`）；
  **补红①** `red-序号12-v2-补红-帧级结构.txt`（variantFlags 少 3 个开关 + `「为必填项」expected true to be false`）→ **补红②** `red-序号12-v2-补红2-凭证说明间距.txt`（少 credHintGap）；
  绿 **770/770 连跑两轮一致**（`green-序号12-v2-轮1/轮2.txt`，轮3 复跑仍 770）+ `npm run type-check` **exit 0**。
- **★ 本轮最值钱的判定法（已写进 dev SKILL 待补）**：**同页多帧必须以「设计树逐层 diff」为准，不能只看文案差集** ——
  page-26 与 page-apikey 的文案差集只暴露了步骤卡/空态说明等，**逐层比对子节点才发现还有 3 处「少了什么」**：
  ①基本信息卡标题行少「必填提示」（kids 5→4）；②字段-报价单号少 `container{单号说明}`（3→2 kids）；③内容区少「填写须知卡」。
  首轮实现只删了步骤卡 → DOM 实测第三张卡 top 1019、页高 1308（设计 1129）才暴露；**帧级差异要全部落成 variantFlags 开关并逐条断言**。
- **本轮第二值钱的判定法**：**同一元素在不同帧的间距可能不同，要逐帧读设计树的 padding** —— 「凭证说明」包裹层 page-26 = **6** / page-apikey = **10**
  （`pad-of.py` 实测），差 4px 会顺着卡片一路传到底栏（实测凭证说明 709 → 713、模型卡 762、页高 1121 → 1125）。
- **由 DOM 数字抓出的真偏差（vision 完全看不出）**：①首轮多渲染 3 块（见上，页高 1308 → 修后 1116）；②面板底部操作行 33 高（设计 42.5）= 图标没按「字号×1.5」包行盒且文案行盒 14.4 →
  包 22.5 行盒后 **面板 217 → 223（设计 224）、页高 1116 → 1121**；③空态盒 160 → **158（= 设计）**：把 `.empty` 的 `border` 换成 **ring（box-shadow）**（§4.8 描边在盒外规则），**这一改动同时让 12-v1 的空态盒 166 → 164（= 该帧设计）**。
- **客观证据链**：`build:mp-weixin` 产出 `pages/quote-form/{index,apikey}.{js,json,wxml}` + **`components/quote-form/QuoteFormView.{js,json,wxml,wxss}`**（app.json 已注册 quote-form/apikey；**样式随组件 wxss 产出，13.5KB** —— 抽组件后必须确认这一步，否则小程序会裸奔）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号12-v2-run7.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 **0** · 文案缺失 **[]（need 32 条本帧原文）** ·
  页高 **1125（设计 1129，-4 = 0.35%）** · 卡 118..746(628，设计 630) / 762..988(226，设计 224) · 凭证选择框 **433..481（设计 432..480，+1）** · 面板 **481..703(223，设计 224)** ·
  选项行 3×54 @487/541/595（设计 54/55/55）· 推荐标 499..515 · 环境标 558..578 / 612..632（设计 558..576 / 613..631）· 空态盒 **158 = 设计** · 底栏 1001..1125(118) ·
  存为草稿 x16..144(128×48) / 保存并继续 x156..414(258×48) · 无 TabBar · `stepCardCount/requiredCount/quoteNoHintCount/tipCount/noticeCardCount` **全 0**（帧级差异的硬断言）；
  **run7 与 run8 两次独立测量 85 字段全等**（`cmp-measure-runs.py`，0 差异）；**像素对账**（`text-rows.py` 同脚本跑设计与实现）：
  名称标签 173..184 **0 差** · 选择框下边框 480 **0 差** · 面板下边框 -2 · 字数 +1 · 单号标签 +2 · 凭证标签 +2（面板以下累积 -6~-8，已登记残差）；
  `png-ink` 顶部带 runs=[(64,98),(100,116),(118,135),(138,151)] 右留白 **278 = 设计 278**（无载体污染）· 底栏带右留白 16（设计 16）；截图 `logs/screenshots/20260916-0430-序号12-v2-新增报价单下拉展开-h5-430宽.png`（430×1125）。
  **浏览器内真实交互（phase2/3/4）**：点候选项 c2 → serve 日志实测 **`GET /api/v1/credentials/c2`** → 面板收起、选择框「测试环境密钥」、chip「已选 1 / 2」、模型行 2 条；
  再展开 → **c2 行 `data-selected=true` + 选中底 rgb(239,246,255) + 图标底 rgb(37,99,235) + 对勾 @364..380**、其余行「专用」环境标；点「前往「我的设置」新建凭证」→ **hash 不变**（目标 /pages/settings/index 未实现）；
  填名称（内层原生 input）→「12/30」→ 点「保存并继续」→ 日志实测 **`POST /api/v1/quotes body={"name":"2024Q3 主线路报价","credential_id":"c2"}`** + **`POST /api/v1/quotes/q9/items`** → toast「保存成功」→ hash 跳 `#/pages/model-pricing/index?quoteId=q9`。
  **新增独立 mock 集** `.agents/state/h5-measure/api-12-v2/`（3 条凭证 = 12/8/5 个模型 + env_tag/is_primary，逐字复刻设计帧；`serve.py` 换端口后先 `curl` 验 mock 再用）。
- ⚠️ 待人类拍板（不阻塞本轮，12 条全部写进台账序号 12-v2 备注）：①与 12-v1 是否合并同一路由；②帧级差异 5 处按帧实现（是否统一）；
  ③设计帧自相矛盾（占位 + 首项画成选中态）→ 按真实选择驱动；④环境标「沙箱/专用」与推荐标「常用」22 份 PRD 零命中 → 消费服务端字段，缺则不渲染；
  ⑤脱敏 key 原样展示（两种字段命名都认）；⑥「N 个模型」取 model_list 长度；⑦「前往「我的设置」新建凭证」落序号 23（未实现，hash 不变）；
  ⑧残差登记（页高 -4：选择框 +1 / 面板 -1 / 模型卡 +2（卡头 20 vs 18，改动会波及 12-v1 已对齐锚点）/ 底栏 -2）；⑨名称框设计示例态不预填；
  ⑩图标 CSS 占位（候选项改实心圆避免被误读成复选框）；⑪帮助按钮 client-only；⑫接口方法为 REST 推断、字段级 schema missing-prd。

⏳ 下一步（下一轮）：台账序号 **12-v3「新增报价单-保存成功」**（page-29，`/pages/quote-form/success`）——**设计尚未抓取**（台账「设计否」），
  先 `python .agents/state/fetch-design.py page-29` 与 `calicat_source.py page --layer-id <inventory 里的 sourceLayerId> --page-id page-29`，
  再按 §2 八步走；可复用本轮：`cmp-frames.py`（**先与 page-26/page-apikey 逐层 diff，别只看文案**）、`pad-of.py`（逐帧读间距）、`fetch-design.py`、`show-a12v2.py` 式取数脚本、
  共用视图 `QuoteFormView.vue` 的 variant 机制（若 page-29 仍是同页帧，优先加开关而不是新写一页）。

🟢 本轮（2026-09-16 03:50~04:15，租约 aap-tdd-run-20260916-0350 → 已释放）· **序号 12-v1「新增报价单-初始态」（page-26）收口**：
- **取件**：`list-pending.py` 最小未完成 = 12-v1（page-26，/pages/quote-form/index）；开工前 `git status` 干净、`git log -1` 为上一轮提交（03:48）→ 判空闲租约，写成本轮 id + 45 分钟。
- **Calicat 侧**：设计树（page-26，02:13 已抓）+ 截图（430×1238，1:1 帧图）直接可用；`interaction.json` 仍「不存在图层交互数据」→
  交互真源退 10-PRD §5.1 V1/A2 · 15-数据字典 · 17-spec · 18-API + 设计稿控件语义。
  **新增可复用工具**：`show-qf.py <measure.json> [字段…]`（按字段打印 phase1 + 自动附 phase2/3）· `count-26.py`（打印设计文本层原文与字符数）·
  **设计像素量尺新套路**：`color-runs.py v <列> blue --from/--to`（按颜色特征）＋ `pxdump.py` 精读边界 → 一次定死「提示条 869..911(43)、空态盒 691..858(164)、卡3 944..1098(155)、底栏 1120..1237(118)」。
- **这页到底是什么**：无 TabBar、底栏随文档流的新建报价单初始态（设计总高 1238）：顶栏（返回 36 圆 /「新增报价单」18px Bold +「填写基本信息并设置模型报价」12px / 帮助 36 圆）·
  **步骤卡**（步骤1 蓝圆点 26 + 「填写信息」+「名称 / 密钥 / 单号」；连线；步骤2 灰圆点 +「设置报价」+「模型定价」）·
  卡1 基本信息（标题行 + 「为必填项」；报价单名称* 输入框 h48 bg #F8FAFC + 清除 + 右侧「0/30」；分隔线；报价单号 + 「系统生成」标 + 只读框 h48 bg #F1F5F9
  （「保存后自动生成」+ 右侧白底胶囊「QT-XXXXXXXX-XXXX」）+ 说明行；分隔线；凭证名称* 选择框 h48（钥匙底 28×28 r8 + 「请选择凭证」+ chevron）+ 蓝图标说明行）·
  卡2 模型列表（chip「待带出」+ 空态盒（56 圆图标 + 「尚未加载模型」+ 说明）+ 提示卡「带出的模型数量与凭证权限相关…」）·
  卡3 填写须知（图标 + 标题 + 三条：1 名称建议 / 2 凭证决定范围 / 3 首次保存成功后…）· 底栏（说明「保存成功后系统将自动生成报价单号」+ 存为草稿 128×48 + 保存并继续 258×48 #2563EB）。
- **TDD（3 切片 + 1 次补红；新增 49 例）**：`tests/unit/quote-form-model.spec.ts`(20) · `tests/pages/quote-form.spec.ts`(14) · `tests/pages/quote-form-flow.spec.ts`(15)；
  红基线 `evidence/red-序号12-v1-切片1/2/3.txt`（切片1/2 = `Failed to resolve import`，切片3 = 13 条真实断言失败）＋ 补红 `red-序号12-v1-补红-行盒规则.txt`（`iconLineBox is not a function`）；
  实现 `src/utils/quote-form-model.ts`（文案常量 + stepsFor + modelChipText + buildQuoteNoBox + validateForSave + buildFormPayload + **iconLineBox/textLineBox**）、
  `src/pages/quote-form/index.vue`、`pages.json` 路由、tokens **新增 1 个**（#FAFCFF 空态底）；
  绿 **740/740 连跑两轮一致**（`evidence/green-序号12-v1-轮4/轮5.txt`）+ `npm run type-check` **exit 0**
  （⚠️ 修前 type-check 真报 `TS2305: MODEL_STATUS_OPTIONAL/SELECTED 不在 quote-form-model` —— vitest 不查类型，**类型门禁抓到了实现错**）。
- **由 DOM 数字抓出的真偏差（vision 完全看不出）**：①卡2 高 **303**（设计 287）、卡3 **150**（设计 155）、底栏 **115**（设计 118）、页高 **1242**（设计 1238）；
  根因 = **本页设计树的文本节点 lineHeight 全是 1.2，而我按 1.5 写**（空态说明 18 vs 14.4、提示条文案 16.5 vs 13.2）＋ **两处图标没有按「字号×1.5」包行盒**
  （须知标题图标 18 → 27、底栏说明图标 13 → 19.5）。修法 = 抽出纯函数 `iconLineBox/textLineBox`（**先补红断言**再实现），模板用 `:style` 绑定；
  修后逐值对齐：页高 **1237（设计 1238，-1）** · 顶栏 102（=设计）· 步骤卡 118..183(65)（=设计）· 卡1 424（425）· 底栏 1119..1237(118=设计) · 凭证选择框 **536..584（设计 536..584 完全一致）** · 名称框 277（设计 276）。
- **本轮最值钱的一条判定法（已写进 dev SKILL §4.12）**：**先读设计树每个文本节点的 `lineHeight` 再写 CSS** —— 同一份设计里 11px/12px 文本可能声明 1.2，
  而图标段落是 1.5；把「一行还是两行」「盒高多少」都建立在设计截图像素（提示条 43 / 空态 164 / 卡3 155）上，而不是自己的换算。
- **客观证据链**：`build:mp-weixin` 产出 `pages/quote-form/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号12-v1-run3.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 **0** · 文案缺失 **[]（need 34 条设计原文）** ·
  卡 199..623(424) / 639..932(293) / 947..1099(152) · 空态盒 691..857(166，设计 164) · 提示条 869..915(46，设计 43) · 须知点 1002/1028/1054（设计 999/1025/1051）·
  存为草稿 x16..144(128×48) · 保存并继续 x156..414(258×48) · 无 TabBar · 输入控件 1；**run3/run4 两次独立测量 84 字段全等**（`cmp-measure-runs.py`，0 差异）；
  **像素对账**（`text-rows.py` 同脚本跑设计与实现）：8 行文本 **0 差**（步骤卡 / 基本信息标题行 / 名称标签 / 凭证标签 / 尚未加载模型 / 空态说明 / 底栏说明 / 按钮），其余 ±1~3；
  `png-ink` 顶部带 runs 右留白 **278 = 设计 278**（无载体污染）· 底栏带右留白 16（设计 16）；截图 `logs/screenshots/20260916-0410-序号12-v1-新增报价单初始态-h5-430宽.png`（430×1237）。
  **浏览器内真实交互（phase2/phase3）**：点凭证选择框 → serve 日志实测 **`GET /api/v1/credentials?page=1&pageSize=20`** → 候选 2 条；选 c1 → **`GET /api/v1/credentials/c1`**
  → 模型行 2 条（价格行「输入 $2.50 / 输出 $10.00 / 1M token」）、chip「待带出」→「**已选 1 / 2**」、空态消失；填名称（写内层原生 input）→ 字数 **12/30** → 点「保存并继续」→
  日志实测 **`POST /api/v1/quotes body={"name":"2024Q3 主线路报价","credential_id":"c1"}`** + **`POST /api/v1/quotes/q9/items body={"items":[{"model_name":"gpt-4o"}]}`**
  → iframe hash 跳 `#/pages/model-pricing/index?quoteId=q9`（序号 11 路由已渲染）。
- ⚠️ 待人类拍板（不阻塞本轮，13 条全部写进台账序号 12-v1 备注）：①与序号 9 是否合并同一路由；②本帧无「报价主体」控件 → provider_id 有意不发送；
  ③18-API 只列路径 → 方法与字段级 schema 为推断；④「保存并继续」落点（模型定价 / page-29 保存成功）待拍板；⑤已带出模型态与 chip 文案复用序号 9 同族帧、工具栏不实现；
  ⑥校验/toast 文案为占位；⑦**字体度量冲突**：提示条文案设计稿一行（实测 9.9px/字）而浏览器 11px/字必然两行 → 提示条 43→46，是卡2 +6 的唯一来源，需拍板是否改字号/文案；
  ⑧图标 CSS 占位；⑨帮助按钮 client-only；⑩单号示例格式为常量；⑪空态底 #FAFCFF 新增 token；⑫设计 11/12px 文本 lineHeight=1.2 已按 textLineBox 落地；⑬已带出态无全选入口。

⏳ 下一步（下一轮）：台账序号 **12-v2「新增报价单-APIKey下拉展开」**（page-apikey，`/pages/quote-form/apikey`）——**设计尚未抓取**（台账「设计否」），
  先按 `.calicat/inventory.json` 取该页 `sourceLayerId` 跑 `calicat_source.py page`，再按 §2 八步走；可复用本轮 `show-qf.py` 式取数脚本、
  `color-runs.py blue/pxdump.py` 像素量尺、`api-12-v1` 式独立 mock 集（**serve.py 端口先 curl 验一次 mock 内容再用**，本轮 5221 撞上旧实例返回了别的 mock 集）、
  `__measure-quote-form.html` 载体模板（**先读设计树每个文本节点的 lineHeight 再写 CSS**）。

🟢 本轮（2026-09-16 03:31~04:00，租约 aap-tdd-run-20260916-0331 → 已释放）· **序号 12「报价预览与提交 2」（page-12-2）收口**：
- **Calicat 侧**：`calicat_source.py page` 报「请先在浏览器中打开文件」→ `cmd /c start "" <design-url>` 拉起后一次成功；
  page-12-2 设计树（58KB / 123 节点）+ 截图（430×1027，1:1 帧图）已抓；`interaction.json` 仍「不存在图层交互数据」→ 交互真源退 10-PRD §3.2/§4.1/§5.1 · 06-PRD §1.2~1.4 · 17-spec · 18-API + 设计稿控件语义。
  **新增可复用工具**：`text-rows.py`（按行统计墨迹 → 一把列出整页文本行 y 区间，设计/实现同脚本逐行对账）、`color-runs.py`（按颜色特征找色段）、
  `node-raw.py`（单节点完整原始 JSON → 确认 `padding=[top,right,bottom,left]` 语义）、`geom.py`、`pxdump.py`、`find-tint.py`、`white-runs.py`。
- **这页到底是什么**：gpt-4o-mini / claude-3-5-sonnet / gpt-4o 三个模型的报价预览页（设计总高 1027，无 TabBar）：
  顶栏（返回 /「报价预览」17px Bold，无副标题）· 三张逐模型卡（头行 图标+模型名 14px SemiBold + 右上标签胶囊〔时段价 + 阶梯价 蓝 / 阶梯价 绿 / 仅基础价 灰〕；
  三列价格〔输入/输出 + 缓存读或缓存写〕；规则行〔时段价行·琥珀图标 / 阶梯价行·蓝 / 请求规则行·蓝，文案 11px〕）· 确认提交卡（蓝底白勾勾选框 + 「我确认以上价格真实有效，并同意《报价服务条款》」+ 琥珀提示条两行）· 白底操作条（返回编辑 156×48 描边 + 提交报价 230×48 #2563EB）。
- **TDD（3 切片 + 1 次补红；新增 51 例）**：`tests/unit/quote-preview-model.spec.ts`(30) · `tests/unit/quote-submit-api.spec.ts`(5) · `tests/pages/quote-preview.spec.ts`(16)；
  红基线 `evidence/red-序号12-切片1/2/3.txt`（切片1/3 = `Failed to resolve import`，切片2 = `quoteApi.detail/submit is not a function`）；
  实现 `src/utils/quote-preview-model.ts`、`src/api/quote.ts`（+detail/submit）、`src/pages/quote-preview/index.vue`、`pages.json` 路由；
  **tokens 0 新增**（17 个色值全部命中既有 tokens.scss）；绿 **691/691 连跑两轮一致**（`evidence/green-序号12-轮1/轮2.txt`）+ `npm run type-check` **exit 0**。
- **由 DOM 数字抓出的真偏差（vision 完全看不出）**：卡3 实测高 **168**（设计 164）、整页 **1031**（设计 1027）——
  根因 = 卡3 只有**一条**规则行，而设计里它唯一规则块的 wrapper `padding-top` 是 **8**（卡1/卡2 的首块才是 12）。
  修法 = 抽出纯函数 `ruleBlockClass(index, count)`，**先补红断言**（`evidence/red-序号12-补红-规则块间距.txt`：`ruleBlockClass is not defined`）再改；
  修后逐值对齐：卡 108/392/624/800 高 **272/220/164/127** · 底栏 **943..1027(84)** · 页高 **1027 = 设计**。
- **本轮最值钱的一条判定法**：**卡片高度对账以「卡间 1px 描边像素」为准，不是算术** —— 设计稿 `#EEF2F7` 描边在截图上留下清晰暗像素行
  （612/624/800/926），一次定死卡2 220 / 卡3 164 / 确认卡 127；而设计树声明的「价格标签 16 + 值 22 = 38」会算出卡2 224（与描边矛盾）→ **取 34**，差值写进台账。
  另：`padding=[a,b,c,d]` 是 Figma 的 top/right/bottom/left（`[0,0,0,6]` 是左内边距）。
- **客观证据链**：`build:mp-weixin` 产出 `pages/quote-preview/{index.js,index.json,index.wxml,index.wxss}`（app.json 已注册）；
  430 宽 iframe + 无头 Chrome **四段实测** `evidence/measure-序号12-run2.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 **0** ·
  文案缺失 **[]（need 32 条设计原文，含三个模型名与 9 个价格值）** · 卡 x16 w398 · 头行 h26 · 价格行 h34 · 规则行 h44（卡1 212/264/316，pitch 52）·
  标签底 `#EFF6FF/#ECFDF5/#F1F5F9` · 勾选盒 18×18 `rgb(37,99,235)` + `data-checked=true` · 提示条 854..907(53) bg `#FFFBEB` maxWidth 316 · 
  返回编辑 x16..172 · 提交报价 x184..414(230×48)；**run2 与 run3 两次独立测量 62 字段全等**（`cmp-measure-runs.py`，0 差异）；
  **像素对账**（`text-rows.py` 同脚本跑设计与实现）：20 行文本卡边界/底栏 **0 差**，卡内文本 -3~-5（设计 PNG 自身抗锯齿偏移），
  `png-ink` 顶部带右留白 314（无载体污染）、底部带 `(66,79)(81,121)(184,413)` 与设计 `(66,78)(80,92)(94,106)(108,120)(184,413)` **完全吻合**；
  截图 `logs/screenshots/20260916-0346-序号12-报价预览-h5-430宽.png`（430×1027 = 设计尺寸）。
  **浏览器内真实交互（phase2/phase3）**：点「返回编辑」→ hash **不变**（navigateBack 无栈）· 取消勾选 → 点「提交报价」→ toast **「请先确认报价条款」**、
  serve 日志**无 POST**；重新勾选 → 点「提交报价」→ 真实 **`POST /api/v1/quotes/q7/submit`（body 为空 —— 18-API 无请求体 schema）** → 跳 `#/pages/quotes/index`（列表页渲染）。
- ⚠️ 待人类拍板（不阻塞本轮，15 条全部写进台账序号 12 备注）：①18-API `/submit` 无请求体 schema → 不发字段；②标签文案与三底色为派生推断；
  ③第三列取缓存读/缓存写、1 小时缓存写不展示；④规则行文案为派生（有 label 用「N 档阶梯：label / label」、无 label 用设计卡2 措辞）；⑤请求规则行为设计常量；
  ⑥勾选默认已勾选；⑦toast 文案占位；⑧提交成功跳报价单列表为推断；⑨返回编辑 = navigateBack；⑩设计声明 价格行 38 vs 卡高只允许 34；
  ⑪规则块首块间距设计逐卡不一致（已按 ruleBlockClass 还原）；⑫卡1 未声明 stroke（四卡统一 ring）；⑬提示条按设计声明宽度 316 换两行；
  ⑭vision 误报链接色 + 图标占位；⑮未接线 /withdraw、/versions、/compile-preview。

✅ 序号 12-v1 已于 2026-09-16 03:50~04:15 轮完成（见最上方本轮块；现为「部分」，13 条待拍板已记台账）。

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
