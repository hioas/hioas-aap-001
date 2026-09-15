---
name: dev
description: hioas-aap-001 项目开发/验证标准流程（uni-app 小程序 + TDD + Calicat 设计还原）。当需要在本仓库「实现页面 / 跑测试 / 构建小程序 / 联调验证 / 还原设计稿」时使用。
---

# SKILL · hioas-aap-001 开发与验证 SOP

> 本文件是本仓库的**流程真源**。与 PRD 冲突时：**领域约束依 `.calicat/prd/`，流程约束依本文件，不得放松。**
> 版本 v1.0 · 2026-09-15 · 随实战迭代。

## 1. 项目结构

```
E:\workspaces\hioas\hioas-aap-001\
├── aap-client/      ← 本轮主战场：uni-app（Vue3 + Vite + TS）供应商报价端（小程序 + H5）
├── aap-server/      Spring Boot（待开始）
├── aap-admn/        管理端 Web（待开始，注意目录名疑似笔误 aap-admin）
├── .calicat/        Calicat 设计/PRD/交互真源（raw/ 不入库）
├── .agents/         状态文件 + 台账 + 脚本 + 本 SOP
├── docs/            人类可读的页面计划等
└── logs/screenshots/ 可视化证据
```

## 2. 七条不可协商的原则

1. **TDD 强制**：先写会红的断言 → 留红基线 → 实现 → 复跑 → **连跑两轮全绿**才可提交。
2. **设计稿是像素级真源**：文案、层级、颜色、间距从 `.calicat/raw/pages/<page-id>/design.tree.json` 取，
   不凭印象改写；截图用 `vision_analyze` 看图核对，不靠猜。
3. **接口不得臆造**：一律指向 `.calicat/prd/18-API设计OpenAPI.md` 的路径与方法；无依据标 `阻塞` 并上报。
4. **一页一提交**：`feat(aap-client): <序号>-<页面名> <做了什么>`；台账 / 状态文件与该页代码同批提交。
5. **应用经 IDE（IDEA）启动与联调**：能用 IDE MCP 就不用命令行起服务（`node scripts/idea-mcp-call.mjs` 见姊妹仓库 hioas-aim 做法）；
   本仓库暂无 IDEA 工程与 run configuration，首次需要时先建 `aap-client` 的 npm 运行配置。
6. **证据要有牙齿**：vitest 真跑输出、`dist/build/mp-weixin` 产物、H5 截图、日志。`npm run dev` 能起 ≠ 页面能用。
7. **不碰别人的改动**：`git status` 里不是自己改的文件不提交、不回滚。

## 3. aap-client 命令（照抄可用）

```bash
cd aap-client
npm test                 # vitest run（全部用例）
npm test -- tests/unit   # 只跑逻辑单测
npx vitest run tests/pages/login.spec.ts   # 单文件
npm run type-check       # vue-tsc --noEmit
npm run build:h5         # 产出 dist/build/h5（可浏览器验收）
npm run build:mp-weixin  # 产出 dist/build/mp-weixin（小程序可导入；本机未装微信开发者工具）
npm run dev:h5           # 本地联调（端口 5173）
```

- 测试环境：`vitest` + `jsdom` + `@vue/test-utils`；`tests/setup.ts` 给 `uni.*` 打桩，
  断言"页面到底调了哪些 uni API"用 `getCalls('request' | 'showToast' | 'navigateTo' | 'login')`。
- 页面组件**不要**在测试里依赖 `onLoad/onShow`（vitest 下不触发），用 `onMounted` 承载首屏逻辑。

## 4. Calicat 设计/交互获取（页面级，一次一页）

```bash
SK=C:/Users/laitz/AppData/Local/hermes/skills/calicat/scripts
python $SK/calicat_source.py page \
  --url https://www.calicat.cn/design/2095515676955668480 \
  --layer-id <sourceLayerId> --page-id <页面ID> --out .calicat
```

产物：`raw/pages/<页面ID>/{design,interaction,screenshot}.json`。
`design.json` 是 `[{id, layer_data}]`，`layer_data` 才是图层树（写出 `design.tree.json` 再摘要）：

```bash
python - <<'PY'
import json;d=json.load(open(".calicat/raw/pages/<页面ID>/design.json",encoding="utf-8"))
inner=json.loads(d[0]["layer_data"])
json.dump(inner,open(".calicat/raw/pages/<页面ID>/design.tree.json","w",encoding="utf-8"),ensure_ascii=False)
PY
python .agents/state/design-summary.py .calicat/raw/pages/<页面ID>/design.tree.json --text-only
python .agents/state/extract-tokens.py .calicat/raw/pages/<页面ID>/design.tree.json
```

- `interaction.json` 返回 `"不存在图层交互数据"` 时，交互真源退到 PRD（写进台账备注，不要假装抓到了）。
  ⚠️ 但 `.calicat/inventory.json` 里的 `interactionCaptured` 是工具的「抓过就算」标记：page-24 实测该字段为 `true`，
  而 `interaction.json` 内容仍是「不存在图层交互数据」→ **一律以 interaction.json 的内容判定**（`gen-ledger.py` 已按内容判定并显示「交互已抓 0/22」）。
- 截图 URL 在 `screenshot.json`，用 `vision_analyze` 打开看图（模型看得见像素，别猜）。
- **画布里的页面层必须在 Calicat 编辑器里打开过**，否则部分工具会返回空。
- ⚠️ **设计类工具要求「文件已在浏览器中打开」**：`get_canvas_list` / `get_design_page_list` / `get_design_data` /
  `get_meta_data` / `get_screenshots` 会统一返回 `{"error_message":"请先在浏览器中打开文件"}`（PRD 类工具 `get_prd_list`
  不受影响）。cron/无头会话里不用找登录态、也不用重新 login，直接拉起默认浏览器打开设计 URL 即可恢复：
  ```bash
  export MSYS_NO_PATHCONV=1
  cmd /c start "" "https://www.calicat.cn/design/<FILE_ID>"   # 打开后约 10~20s，设计类工具即可用
  ```
  验证：`calicat tools-call --name get_canvas_list --args '{"file_id":"<FILE_ID>"}'` 返回 `status:"success"`。

## 4.1 视觉验收：DOM 数字优先，模型描述只作参考

`vision_analyze` 对 430 宽的小程序截图**会误报"右侧被裁切"**（实测三次，均被 DOM 数据推翻）。
⚠️ **2026-09-16 补：截图本身也可能真的被裁**——headless Chrome **不认 `--window-size`**
（实测 `--window-size=430,944` 时页面 `innerWidth=500`），此时直接对应用 URL 截图，得到的是「500 宽布局裁出 430 像素」的假图，
vision 看到的「右侧贴边/缺字」是**截图假象**而非页面缺陷。因此截图必须走确定性路径：

1. 用 430 宽 iframe 载体页（`.agents/state/h5-measure/__measure.html`）+ `--hide-scrollbars`
   （hide-scrollbars 同时让 iframe 内容宽度 = 430，与小程序一致），先把载体页拷进 `dist/build/h5`；
2. 截图后按 iframe 矩形裁剪：`python .agents/state/png-crop.py <in.png> <out.png> 0,0,430,900`；
3. 用**像素级墨迹核验**确认没有内容越界：`python .agents/state/png-ink.py <out.png> "band=280,146,430,172"`
   会打印每条墨迹的 x 区间与右侧留白；右留白 20px = 与设计稿页边距一致。
   若墨迹触到最后一列（留白 0），先怀疑截图尺寸（第 1 条），再怀疑布局溢出。
视觉验收固定两步：

1. 把 `dist/build/h5/__measure.html`（iframe 固定 430 宽 + `getBoundingClientRect` 统计）放进构建产物，
   用无头 Chrome 取数：

   ```bash
   "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
     --virtual-time-budget=25000 --user-data-dir="$LOCALAPPDATA/Temp/chrome-measure-$$" \
     --dump-dom "http://127.0.0.1:<port>/__measure.html" > "$LOCALAPPDATA/Temp/measure.html"
   ```

   看三个数：`docScrollWidth <= innerWidth`、`overflowingCount == 0`、关键文案完整。
2. `vision_analyze` 只用于"人眼感受"层判断（层级、留白、色彩关系），与步骤 1 冲突时**以数字为准**。

⚠️ **2026-09-16 补（序号 4-v1 实测）**：载体页里取数的 `<pre id="m">` **不能靠 `left:-9999px` 藏**——
无头 `--screenshot` 会把页外内容也截进来（实测截进了整段 MEASURE_JSON 文本，vision 报成"顶部黑色 JSON 调试条"的**假象**，
而只看 DOM 数字完全发现不了）。正解：把 `<pre>` 包进 `#sink { width:0; height:0; overflow:hidden }`（textContent 仍可读）。
**规矩：每次截图后必须用 `png-ink.py "<out.png>" "band=0,0,430,60"` 核验顶部带**（底部同理）——
正常只有返回箭头/标题/按钮几个 run；出现满行密集 run 就是载体页污染或内容越界，先修载体再谈页面。
整页截图：把 iframe 高度设成 `docScrollHeight`（如 1120）再 `--window-size=430,1120`。
两段测量模板见 `.agents/state/h5-measure/__measure-form.html`（空态 + 给 `uni.chooseFile` 打桩后点上传区，走真实 `onPickFile`）。

### 4.2 测量/取证流水线（2026-09-16 起，踩过的四个坑）

本地起服务：`python .agents/state/h5-measure/serve.py aap-client/dist/build/h5 .agents/state/h5-measure/api 5199`
（静态托管 + `/api/v1/**` JSON mock：**先查目录再查文件**，所以 `/api/v1/credentials` 与 `/api/v1/credentials/{id}`
可以同时 mock —— 纯静态文件做不到「同名文件与子路径共存」；非 GET 返回 `{"code":"0"}` 并打印方法/路径）。

坑与规矩：
1. **`npm run build:h5` 会清空 `dist/build/h5`** → `__measure*.html` 必须在每次 build:h5 **之后**重新拷进产物目录；
   否则 Chrome 拿到 404 页，取数脚本会**静默读到上一轮 JSON**（等于拿旧数据当新证据）。
   规矩：取数前先 `wc -c` 看 dump 字节数（几百字节 = 404 页），异常就重取。
2. **无头 Chrome 复用同一个 `--user-data-dir` 会偶发不产出 dump** → 每次用一个新目录（`chrome-measure-$$`）。
3. **uni-app H5 把 `<input>` 渲染成 `<uni-input>` 包装元素**，`el.value` 是 undefined；取值要读内层原生 `input.value`。
   同理 `innerText` **不含 input 的值** → 文案完整性检查里会把表单值误报为「缺失」（既知假象，需单独断言 input.value）。
4. **`--window-size` 不可靠**（见 4.1 第 1 条）+ 页面可滚动时，430×900 截图只覆盖文档前 900px：
   模型/vision 可能把「折叠区」误判成「被裁掉/被固定栏遮挡」→ 一律用 DOM（`docScrollHeight`、`atBottom` 断言）否定或确认。

### 4.3 轮询型页面（检测进行中类）的取证补充（2026-09-16 序号 5）

- 带轮询的页面，载体页做**两段测量**：`phase1`（首次加载后）与 `phase2`（跨过一次轮询间隔后），
  两侧关键数字应**全等**——这既是「连跑两轮一致」的可视化版本，也能顺带证明轮询不会破坏布局。
- 「轮询真的在发请求」不能只靠单测：`serve.py` 会打印每条访问日志，跑完看日志里是否出现**连续成对**
  的 `GET /api/v1/...`（序号 5 实测成对出现）——这是比 mock 断言更硬的证据。
- 模板：`.agents/state/h5-measure/__measure-detecting.html`（含 `#sink` 隐藏取数区 + 按 `docScrollHeight`
  自动设置 iframe 高度，便于整页截图）。
- **`unwrap-design.py` 的入参是页面 id（如 `page-5-2`），不是 `design.json` 路径** —— 传路径会拼成
  `.calicat/raw/pages/.calicat/.../design.json/design.json` 直接报错。
- 设计帧里**同一种卡片的内边距可能不同**（page-5-2 的提示卡片 c960eff4 是 `padding 16/20`，其余卡片是 `20`）
  → 每张卡都要回 design.tree.json 看 padding，别用同一个 class 一把梭；这类偏差只能靠 DOM 数字发现
  （vision 对 8px 差异无感）。

## 4.4 大图/矢量图页面的取证补充（2026-09-16 序号 6 检测报告）

- **vision 与 DOM 数字是互补的，缺一不可**：序号 6 实测 vision 先发现「雷达 6 轴标签整块没渲染」（DOM 的 `missingTexts` 因为我没把那 6 个短标签写进 `need` 而漏报）；
  而横向溢出、flex 子项被压缩这类问题只有 DOM 数字（`overflowingCount`、元素 `left/w`）才看得见。
  **规矩**：文案完整性清单必须覆盖「设计稿里每一个独立文本图层」（含雷达轴标签这种短词），并对溢出元素打印 `left/w/right/outerHTML`。
- **mp-weixin 不能渲染内联 `<svg>` 标签**（wxml/wxss 无 svg）。矢量图（雷达/图表）正解 = 把 SVG 字符串编成
  `data:image/svg+xml;base64,…` 交给 `<image>`（H5 与小程序同源，纯函数可单测：见 `src/utils/report-model.ts` 的 `radarSvg/radarDataUri/base64Ascii`）。
  取数时注意 uni-app H5 的 `<image>` 渲染成 `<uni-image>`，**src 在子节点上**（`host.querySelector('img')` 或读背景图），读外层元素的 `src` 会得到空串。
- **设计稿自身的横向自洽性要算一遍**：把卡片内宽（430 − 2×页面边距 − 2×卡片 padding）与子项宽度之和对比。
  序号 6 的未计分行「150 + 8 + 163 + 8 + 62 = 391 > 358」是设计自身溢出（表现为两个 flex 子项被压缩 + 1 处 `overflowingCount`）；
  修法 = 固定列 `flex-shrink: 0` + 弹性列 `flex: 1; min-width: 0`，并在台账写明「设计不自洽、实现按零溢出」。
- 通用取数：`python .agents/state/show-measure6.py <measure.json> phase2 <字段名…>`（按 phase 取指定字段，替代页面专用的 show-measure*.py）。

## 4.5 uni-app H5 行盒陷阱 + 取数脚本（2026-09-16 序号 7 检测未通过报告）

- ⚠️ **`<text>` 在 H5 是 inline（UNI-TEXT），非 flex 容器里行盒由父级撑**：父级 UNI-VIEW 继承 uni 默认 **16px** 字号，
  行盒 ≈24px，实测 `分项行高 24（设计 14.4）`、`说明盒 72（设计 60）`、`详情行 24（设计 20）`、`文本块 40（设计 36）`。
  **规矩：设计稿给了明确行高/盒高的文本，样式里一律补 `display: block`**（或让其父级是 flex，flex 子项会被块级化）；
  改完必须回 measure 复核，这类偏差 **vision 完全看不出来**，只有 DOM 数字能抓（序号 7 一次抓出 4 处，卡片高度差最大 79px）。
- **报告编号类「前缀 + 值」**：设计稿里常是**单个**文本图层（如「报告编号 DR-20240614-0312」）→ 必须连前缀一起渲染，
  否则 H5 取数的 `missingTexts` 会命中（序号 6 历史欠账，序号 7 已按设计补齐）。
- **写类接口也要能 mock**：`serve.py` 现在支持 `MOCK/<path>/post`（如 `.agents/state/h5-measure/api/v1/detection-jobs/post`），
  否则 POST 一律回 `{"id":"c1"}`，验证「重新提交检测」拿不到真实 job_id。
- **截图与交互回放必须分开跑**：交互回放会点按钮把 iframe 导航走（序号 7 点「重新提交检测」→ 跳检测页），
  同一份载体页再截图就会**截成下一页**（第一次截图截成了「检测进行中」，墨迹/vision 都对不上本页数字）。
  载体页用 `?noaction=1` 跳过点击阶段；截图走 noaction，交互结论（toast / hash 跳转）写进 measure JSON 的 phase3/phase4。
- 新增脚本：`extract-measure-json.py`（dump-dom → measure JSON）、`compare-phases.py`（两个 phase 逐字段比对，
  "连跑两轮一致"的 H5 版本）、`png-size.py`（PNG 宽高自检，确认截图尺寸真的是 430 宽）。
- **卡片高度要拿设计推导值对账**：把设计各子块高度相加（padding + 文本行高 + 子块间距）与 DOM 实测比，
  序号 7 封面卡 240 = 设计推导 240（完全一致）才能说明前 4 处行盒偏差已修净。

## 4.6 设计稿尺寸的「像素量尺」+ 列表页取证（2026-09-16 序号 8 报价单列表）

- **design.tree.json 的几何不可全信，设计截图才是硬证据**：page-8-2 的设计树写「卡片列表 gap=12 / 操作行 padding=[16,0,16,0] 且 height=60」，
  单看声明算不出卡高（自算 175/155 两个版本都不对）。正解 = 用设计截图量色带：
  ```bash
  python .agents/state/png-bands.py <design.png> v 215 0 1206     # 沿中列 → 卡盒/间距/栏高
  python .agents/state/png-bands.py <design.png> h 292 0 430      # 沿横排 → 元素 x 位置与宽度
  ```
  page-8-2 实测：卡盒 **178**（含 1px 描边）· 卡间距 **12** · 操作行 **60** · TabBar **84** · 页高 **1206** ——
  这才让 DOM 实测的 177/12/60/84 有得对账（差 1px 可解释，差 20px 就是实现错）。**注意量卡盒要选卡片中央的列**（x=215），
  选 x=20 会被 16px 圆角吃掉首尾各 6px，把 178 误读成 166。
- **列表页「真实请求」比 mock 断言更硬**：载体页 phase3/phase4 点真实 chip / 真实「删除」按钮，
  再用 `serve.py` 的访问日志核对请求行（本轮实测 `GET /api/v1/quotes?page=1&pageSize=10&status=REJECTED` 与 `DELETE /api/v1/quotes/q1`）。
- **`serve.py` 现在按方法名找 mock**（`MOCK/<path>/<method>`，并保留 `post` 兼容）+ 已实现 `do_DELETE`：
  否则 DELETE/PUT 拿不到 mock 响应、日志里也不出现（列表页「删除后刷新」这类流程必须有它才能验）。
- **`uni.showModal` 需要自己打桩**（`tests/setup.ts` 已加）：`setModalAnswer(false)` 可测「取消路径」；
  桩走 `Promise.resolve().then(...)` 与 `uni.request` 一致，页面里必须 `await` 之后的异步逻辑才不会与桩竞态。
- **测试 mock 队列要按真实调用顺序 push**：`pushResponse` 是队列，页面「删除 → 重新拉列表」会连续消费两个响应，
  只 push 一个会把 DELETE 的响应吃掉、断言拿到空数据（本轮踩过：`cardCount 0`）。
- **vision 对颜色/位置会报错，design.tree.json 才是真源**：page-8-2 的「删除」在设计里是**蓝色 #2563EB**（与其它操作同色），
  vision 报成红色 #FF4D4F。规矩：颜色断言一律回设计树取 `fontFill/fills`，vision 只用于"层级/留白"这类主观判断。
- **设计帧自身越界也要记**：顶部「新建报价」按钮在设计里位于 x343..440（宽 97，超出 430 画面 10px），
  与同帧声明的 `padding-right 16` 不自洽 → 实现按「页面零溢出」右对齐 16，并把差异写进台账备注（不静默照抄越界）。

## 5. 页面实现顺序与取件

```bash
python .agents/state/list-pending.py -n 5      # 按序号取下一件
python .agents/state/gen-ledger.py             # 刷新台账（会保留已有状态/证据列）
```

台账列：`序号 / 页面ID / 页面名 / 模块 / 目标路由 / 设计抓取 / 交互抓取 / 截图 / 用例(证据) / 状态 / 备注`，
状态取值：`未做 | 进行中 | 部分 | 已验证 | 阻塞`。

## 6. 平台坑（本机实测）

- 中文 Windows `netstat` 输出是 GBK；`taskkill` 需要 `MSYS_NO_PATHCONV=1`。
- bash 里把中文塞进 JSON body 会变 GBK：要发中文请求体用 Node/Python 的 utf-8。
- `python -c` / `node -e` 在 cron 会话里可能被安全策略拦 → 脚本先落文件再执行。
- npm 走 `registry.npmmirror.com`（已全局配置）；GitHub 直连慢，必要时 `export https_proxy=http://127.0.0.1:7897`（Clash Verge）。
- 本机**未安装微信开发者工具**：小程序验收只到「编译产物存在 + H5 可视化」，
  真机/开发者工具导入由人类执行，汇报里要写清这一点。
- ⚠️ **类型门禁曾长期空转（已修，2026-09-16）**：`package.json` 装 `typescript 4.9.5` + `vue-tsc 1.8.27`，
  而 `@vue/tsconfig 0.5.1` 的基座是 TS5 语义（`moduleResolution: "bundler"` + `verbatimModuleSyntax`）。
  TS4.9 不认 `bundler` → `resolveJsonModule` 直接抛
  `TS5070: Option '--resolveJsonModule' cannot be specified without 'node' module resolution strategy`，
  于是 `npm run type-check` **一条真实错误都报不出来**（配置错误先把门禁打断）。
  **修法**：`tsconfig.json` 显式写 `"moduleResolution": "node"`；随后暴露的两条 `src/api/http.ts` 类型错误
  按 `uni.request` 的真实类型对齐（uni 的 method 联合**不含 PATCH**；`res.data` 是 `string|AnyObject|ArrayBuffer`，
  要经 `unknown` 转换）。**后续每页提交前都应跑 `npm run type-check`**，它现在真的会报错。
  （根治可考虑升到 typescript@5 + vue-tsc@2，但那是依赖变更，需单独评估。）
