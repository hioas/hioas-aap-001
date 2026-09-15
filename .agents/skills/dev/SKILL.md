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
   ⚠️ **2026-09-16 补（序号 9 实测，最坑）**：`data-testid` 放在 `<input>` 上时**落在 `<uni-input>` 宿主元素**上。
   载体页给宿主 `el.value = '…'` + `dispatchEvent(new Event('input'))` **完全不触发 v-model**（实测字数一直 `0/30`、保存被「请输入报价单名称」拦住 → 会误判成页面缺陷）。
   正解 = 先取宿主再进内层：`host = doc.querySelector('uni-input[data-testid="x"]'); el = host.querySelector('input')`，
   `el.focus(); el.value = '…'; el.dispatchEvent(new Event('input', { bubbles: true }))`；**且 uni 侧更新有 ~1s 延迟**（1s 后才出现 `12/30`，取数时间点要留够）。
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

## 4.7 表单页取证 + 从设计截图反推卡片边界（2026-09-16 序号 9 模型报价设置）

- **设计稿的「多层 padding」要在实现里逐层落**：page-9 报价主体卡 无字段标签行，但选择框前仍有一层 `padding-top 8` 的容器（设计 5f243d40）→
  漏掉后主体选择框 top 实测 170（设计 **178**）、卡高 140（设计 ~148）。**规矩：卡片内每个直接子块都要回 design.tree.json 数一遍 padding**，
  只按「同族卡片长得一样」会稳定差 8px（此类偏差只有 DOM 数字能抓，vision 与像素比对都很难看出来）。
- **从设计截图反推卡片边界**：用 `python .agents/state/png-bg-runs.py <png> <x> "#f5f7fb" 3` —— 沿列扫描**页面底色色带**（= 卡片之间的间距/页边距），
  比 `png-bands.py` 直接读整列更抗文字墨迹（卡中央的列会被文字打断成碎片）。注意**别选卡边缘的列**（x=22 会被 16px 圆角吃掉首尾各 6px，把 16 的间距读成 8）。
  得到「导航结束 102 / 卡1 118..268 / 卡2 285..562 / 卡3 578..」这类硬边界后，再与 DOM 的 `cardRects` 逐条对账。
- **判重同名/疑似重复帧**：画布页名与帧内容可能不一致（page-9 名为「…-列表」、内容却是「新增报价单」已填态）。
  先抓相邻疑似帧（如 page-26「新增报价单-初始态」）并做**文本差集**：`python .agents/state/diff-node-text.py <nodesA.txt> <nodesB.txt>`，
  差集为空才是重复帧；有差异就是不同页面，不要合并实现。

## 4.8 描边在盒内还是盒外 + 表单页取证（2026-09-16 序号 10 供应商档案编辑）

- ⚠️ **设计稿的 `stroke` 有的画在盒外、有的画在盒内 —— 必须对每个盒子单独量，不能一刀切**：
  page-10-2 实测：①**卡片 / chips / 简介框 = 盒外** —— 卡高 579 = 20 + 内容 + 20（**不含**描边）、chip 声明 `height=40` 而截图可见 **42**；
  用 CSS `border` 会让盒高 +2 且把**卡内每个字段整体下推 1px**（实测框 top 198 vs 设计 197）。
  正解 = `box-shadow: 0 0 0 1px <color>`（ring，不参与布局）：改后卡高 **579/345** 与设计逐值相等、页高正好 **1409**。
  ②**输入框 / 未上传缩略图 = 盒内**（声明 44、可见 42）→ 保留 `border`。
  判定法：`png-bands.py v <列> <from> <to>` 量同一元素在**中心列**的可见色带高度，与 design.tree.json 声明值比：
  可见 = 声明 → 描边在盒外；可见 = 声明 − 2 → 描边在盒内。
- ⚠️ **表单页禁止用 `.field + .field` 这类相邻兄弟选择器做字段间距**：两列行（`.two-col`）里的第二个半栏也是 `.field`，
  会被加上 `margin-top` → 实测"职务"框比"联系人"框低 **16px**。正解 = `.card > .field, .card > .two-col, .card > .qual-row { margin-top: 16px }`，
  并把 `.card__head { margin-bottom: 0 }`（否则"卡头 16 + 首字段 16" = 首字段被下推 16）。
- **卡内头部高度 = 图标字号 × 1.5**：设计 `主体标题行` 声明 `height=fit_content`，图标是 18px 的 paragraph → 实测头部 **27**；
  若把它当成标题的 18 写死，卡内所有字段会整体上移 9px（page-10-2 实测差值）。**规矩：设计里 fit_content 的行盒按「最大子项的 1.5 倍行高」估，再用像素量尺校正。**
- **字符计数控件（`48/200`）必须按真实字数渲染**：page-10-2 设计写「48/200」而示例文本只有 40 字（设计自身不自洽）→
  渲染 `len(text)/max`，并把设计原值写进台账备注。`python .agents/state/count-text.py "<文本>"` 可量设计文本长度。
- **结构差异 vision 先发现、像素带确认**：第一版把设计的「必传」(红底) 与「已上传」(绿底) **合并成一个角标**，DOM 数字（文案/尺寸/溢出）全都正常，
  只有 vision 描述"标签后有绿色对勾 + 绿色文字「必传 已上传」"暴露了它；随后用 `png-bands.py h <y> <from> <to>` 在设计截图同一行量出两个色带
  （红 #FEF2F2 x157..191、绿 #ECFDF5 x202..261）坐实。**规矩：角标/标签这类"一个还是两个"的结构问题，vision 描述 + 横向量色带双确认。**
- **同一个接口在不同设计帧里样例值不同时，用独立 mock 集隔离**：page-9 与 page-10-2 都读 `/provider/profile`，但设计里的公司名分别是
  「上海徽石科技国外」「云智科技有限公司」→ 新 mock 放 `.agents/state/h5-measure/api-<序号>/v1/...`，`serve.py` 的第二个参数指过去即可，
  不要改既有 `api/`（否则历史证据不可复现）。
- **H5 版「连跑两轮一致」= 两次独立 dump 比同一 phase**：`python .agents/state/cmp-measure-runs.py <a.json> <b.json> phase1`
  （载体页的 phase2 若只装交互结果、不含全量 collect，就不能用 `compare-phases.py` 比 phase1/phase2）。
- 新增工具：`count-text.py`（量文本长度）、`grep-dump.py <dump> <关键字>`（在 dump-dom 里抓上下文，排查 uni H5 真实 DOM 结构）、
  `show-measure10.py <json> <phase|cmp> …`（按 phase 取数 / 比两 phase）、`cmp-measure-runs.py`（两次独立测量逐字段比对）、
  `kill-port.py <端口>`（收尾结束测量用 mock 服务；cron 里 `taskkill /F` 会被安全策略拦，故用 ctypes TerminateProcess）。
- **uni-app H5 的 `placeholder` 是渲染成文本层的**（会进 `innerText`），不在内层原生 `input` 的 `placeholder` 属性上 →
  文案完整性检查可直接把占位文案写进 `need` 列表。（序号 10 实测：`placeholderAttr=null`、`placeholderInText=true`。）

## 4.9 图标占位的行盒 + 取证脚本的两处静默失败（2026-09-16 序号 10.1 供应商档案）

- ⚠️ **图标「字号 × 1.5」不只是卡片头部，所有图标所在的行盒都是**：设计稿里 `paragraph fontSize=18 fontFamily=remixicon`
  的行盒 = **27**（18 × 1.5），不是 18。page-10-1-2 的「主体锁定提示」盒高 **51 = 12 + 27 + 12**，
  只画一个 18 高的 CSS 形状 → 实测 42（矮 9px），并且**卡2 之后的整页元素全部上移 9px**
  （简介框 890 vs 设计 899、资质缩略图 1049 vs 1058、底栏 1321 vs 1330、页高 1409 vs 1414）。
  正解 = 给图标套一个 `height: 27px; display:flex; align-items:center` 的包裹层（宽取设计声明的 20），
  盒子高度立刻逐值相等。**判定法：盒子高度 = padding×2 + max(文本行盒, 图标行盒=字号×1.5)**，
  两边都算一遍再写 CSS；这类偏差 vision 完全看不出，只有 DOM 数字/像素带能抓。
- ⚠️ **无头 Chrome 会「静默不写文件」**：同一份 `--screenshot` / `--dump-dom` 命令偶发不产出文件，
  而 shell 的 `>` 重定向**已经截断了旧文件**时更难分辨。规矩：跑完先看**文件 mtime + 字节数 + 一个只有新版本才有的标记串**
  （本轮用 `noteIconBox`）——三者都新才是真证据；只比字节数会被「上一轮的输出」骗过（本轮踩过：dump 字节数与上一轮完全相同）。
- ⚠️ **`--screenshot=<中文路径>` 会被 MSYS→Windows 参数转码搞坏，Chrome 静默不落盘**：
  截图一律先写到纯 ASCII 临时路径（`C:/Users/<user>/AppData/Local/Temp/xxx.png`）再用 `mv` 改成中文名。
- 新增脚本：
  - `rows-ink.py <png> <x0> <y0> <x1> <y1> [bghex] [tol]` —— 在横向区间内逐行找墨迹行，一把量出**一列字段/文本行的 y 区间**
    （本轮用它定死「字段 pitch 54、类型行 pitch 64、资质行 1058/1122/1186」）。
  - `colors-all.py <design.tree.json> [tokens.scss]` —— 列出**全部**颜色（`fills` + `fontFill` + `stroke.fills`）并标 OK/NEW，
    一次确定「本页要新增哪些 token」（`extract-tokens.py` 只看 `fills`，会漏掉 `fontFill`，别用它做 token 决策）。
  - `serve.py` 的访问日志是「真实请求」的唯一硬证据：本轮 `PUT /api/v1/provider/profile` 的 body 直接从日志取；
    启动时**必须把 stderr 重定向到文件**（`python serve.py ... > serve-<port>.log 2>&1`），否则日志随进程消失。
- **H5 版的页面交互回放必须「等就绪再点」**：一次性 `iframe.src` 重载后固定 `sleep` 会踩空（本轮 phase3 前三次点击全部 `NOT_FOUND`，
  只有最后一次成功）。正解 = 轮询等待目标元素出现（200ms × 最多 40 次）再点，**hash 也要延迟 700~900ms 再读**
  （uni 的 router 更新是异步的，在 `click` 后立刻读 hash 会拿到旧值、误判成「没跳转」）。
- **只读页也可能有「保存」**：page-10-1-2 是只读档案页却有「保存 + 去补全资质」。不要因为「没有输入框」就把它归成 client-only——
  先找同族页面的写接口（本轮用序号 10 的 `PUT /provider/profile`）并**在台账写明语义缺口**，再实现。

## 4.10 设计树的隐藏节点 + 盒装标签行盒（2026-09-16 序号 11 模型定价）

- ⚠️ **设计树里 `"visible": false` 的节点不参与布局**：page-11 卡4 的「规则提示」（11px 折叠态文案）在树里存在但 `visible:false`，
  按「所有子块高度相加」算卡高会**多出 24px**，表现为「卡片逐值对不上设计总高」。
  **规矩：算设计高度前先 grep 一遍 `visible`**（`grep -o '"name": "[^"]*", "type": "[^"]*"[^}]*visible' design.tree.json`
  或直接 `python .agents/state/dump-raw-node.py ...` 看单个节点），隐藏节点一律**不计入**高度、也不要在首屏渲染
  （序号 11 实测：该提示只在折叠态才显示 → 已作为折叠态文案实现）。
- ⚠️ **同一种字号在本页可能有多种行盒，不能一刀切**：page-11 的 11px 文本有两种——**盒装标签 18px**（设计树里带显式 `height=18`，
  如卡1 摘要、`$/1M token` 胶囊）与 **fit_content 说明文案 13.2px**（卡4 的三处灰字，两行说明实测 26.4 = 2×13.2）。
  把胶囊里的 11px 按 13.2 写 → 卡3 矮 5px、卡4 之后**整页元素上移 5px**（序号 11 实测页高 1536 vs 设计 1541）。
  **判定法（反推头部高度）**：`行框实际 y − 卡顶 − 卡片 padding − 区块间距` = 头部高度，再减去 padding 得到文本行盒。
  page-11 实测 `455 − 378.4 − 14 − 14 = 48.6 = 头24 + 标签18 + 7` → 头 24 = 单位标签 `3 + 18 + 3`。
  改后逐值对齐：价格行1 框 top 454（设计 455）· 1h缓存框 620（621）· 媒体框 752（751）· 卡3 高 598（597）· 页高 **1540（设计 1541）**。
- **新增工具 `rows-gap.py <png> <probeX> <refX> [tol] [from] [to]`**：按行比较「卡内列（如 x=215）」与「页边距列（如 x=8，恒为页面底色）」的颜色距离，
  输出**近似同色段** = 卡片之间的间隙。比 `png-bg-runs.py`（精确同色）抗模糊：设计截图经缩放后卡片底与页面底色是渐变过渡，精确匹配会漏掉所有间隙。
  序号 11 据此一次量出 卡1 114..196(82) / 卡2 211..363(153) / 卡3 378..974 / 卡4 989..1448 / 底栏 1465 与「间隙一律 14」。
- **设计帧图若是 1:1 导出**（page-11 的 `screenshot` 就是 430×1541 的整帧），它的**像素高度就是设计总高** —— 这是最硬的对账锚点，
  比逐块相加更可靠：序号 11 用「页高 1541 + 底栏 76 = 底栏 top 1465」反推出卡4 高 459，再逐块核对的。

## 4.11 卡片页的像素对账 + 后台服务路径（2026-09-16 序号 12 报价预览）

- ⚠️ **`background=true` 启动 `serve.py` 必须传绝对 Windows 路径**：相对路径（`aap-client/dist/build/h5`）在后台会话里解析不到，
  表现是页面能开、但所有 mock 接口 404（`{"code":"E-2001","message":"mock 未定义该接口…"}`）—— 极易误判成前端接线错。
  正解：`python serve.py "E:/…/aap-client/dist/build/h5" "E:/…/.agents/state/h5-measure/api-12" <port>`（脚本内给原生工具也一律用 `E:/…` 形式）。
- **卡片高度对账的最强锚点 = 卡间 1px 描边像素，不是算术**：设计截图里 1px `#EEF2F7` 描边在卡边缘形成**清晰暗像素行**
  （序号 12 实测 612 / 624 / 800 / 926），由它们一次定死「卡2 220 / 卡3 164 / 确认卡 127 / 底栏 943..1027 / 页高 1027」；
  再去反推卡内盒高。**当设计树声明的盒高之和（标签 16 + 值 22 = 38）与卡高互相矛盾时，以「卡间描边 + 页总高」为准**，
  把差值写进台账备注（序号 12 因此取 价格行 34 而非声明值 38，DOM 实测 4 张卡 top 108/392/624/800 与设计逐值一致）。
  量法：`python .agents/state/color-runs.py <设计png> v <列> bg`（列取卡中央 x=215 或卡内留白 x=40）。
- ⚠️ **同一设计里「同类块的首块间距」可能不一致**：page-12-2 的卡1/卡2 首个规则块 wrapper `padding-top 12`、其后 8，
  而卡3**唯一**的规则块是 **8**。用 12 会让卡3 高 **168**（设计 164）、整页高 **1031**（设计 1027）。
  正解 = 把它写成**可测的纯函数**（`ruleBlockClass(index, count)`）→ **先补红断言看红**（`ReferenceError: ruleBlockClass is not defined`）→ 再实现，
  然后重建 H5 复测（本轮先留 pre-fix 的 `measure-序号12-run1.json` 当偏差证据）。这类偏差 **vision 完全看不出**。
- **新工具（本轮新增，一把量全页）**：
  - `text-rows.py <png> <x0> <x1> [thresh] [minCount]` —— 按行统计深色墨迹像素数，直接列出**整页所有文本行的 y 区间**。
    设计截图与实现截图跑同一个脚本即可逐行对账（本轮 20 行文本逐一对比：卡边界/底栏 0 差，卡内文本 -3~-5 = 设计 PNG 自身偏移）。
  - `color-runs.py <png> v|h <idx> [white|bg|blue|green|amber|gray|ink]` —— 按颜色特征找色段（量标签胶囊、提示条、卡片底与卡间隙）。
  - `geom.py <design.tree.json> [minDepth] [maxDepth]` —— 打印带 x/y 的节点清单（注意：**只有 frame 根节点有坐标，子节点 x/y 为 null**，
    别指望靠它算卡高，仍要回像素量尺）。
  - `node-raw.py <design.tree.json> <id前缀>` —— 打印单个节点**完整原始 JSON**。用于确认 `padding=[a,b,c,d]` 的语义：
    **顺序是 Figma 的 top / right / bottom / left**（实测 `[0,0,0,6]` 是左内边距 6、`[12,0,0,0]` 是上内边距 12），
    也用于判断某节点有没有 `stroke` / `visible:false`。
  - `pxdump.py <png> v|h <idx> <from> <to> [step]` —— 逐像素打印 RGB 与 CARD/PAGEBG 标记，看清边界过渡（判描边在盒内还是盒外）。
  - `find-tint.py <png> <x0> <y0> <x1> <y1> [blue|green|amber] [delta]` —— 在矩形内找偏色墨迹像素，
    用来判定「设计里这段文字到底是不是链接色」（序号 12 实测：整行 `#475569`，`B-R≈34` 但 `min>220` 的判定要放宽，勿被 vision 带偏）。
- ⚠️ **vision 在本轮两处误报，判定法已固化**：①把单色 `#475569` 的确认文案报成「蓝色链接」→ 用 `find-tint.py` 逐像素测；
  ②把 CSS 图标占位（14×14 圆角方块）报成「未勾选的方形勾选框」→ 图标占位（R-26 禁 emoji）在 430 宽下必然被这样误读，
  只要 DOM 断言里 `data-checked`/勾选数正确就忽略它。**规矩：颜色/结构类质疑一律回像素与设计树，vision 只作「少了什么」的提示器。**

## 4.12 行盒真源：先读设计树的 lineHeight，再写 CSS（2026-09-16 序号 12-v1 新增报价单-初始态）

- ⚠️ **同一份设计里「文本行盒」不是同一个比例：`design.tree.json` 每个文本节点都有自己的 `lineHeight`，必须先读再用**：
  page-26 全部文本节点 `lineHeight: 1.2`（11px → 13.2、12px → 14.4），而**图标段落**（remixicon，type=paragraph）仍是 `字号 × 1.5`（10-1-2 的规则）。
  本轮一开始按 1.5 写所有 11/12px 文本 → 空态说明 18（设计 14.4）、提示条文案 16.5（设计 13.2）→ 卡2 高 **303**（设计 287）、页高 **1242**（设计 1238）；
  改成 1.2 后卡2 293、页高 **1237（设计 1238，-1）**。**判定法**：`pxdump.py <设计png> v <列> <from> <to>` 读单列像素，
  用设计 PNG 里目标块的首末行（白↔底色/纯色）当硬边界，反推盒高（本轮：提示条 869..911=43、空态盒 691..858=164、卡3 944..1098=155、底栏 1120..1237=118）。
- ⚠️ **图标行盒 = 字号 × 1.5 这条规则不止卡片头部**：page-26 命中两处——「填写须知」标题图标（18 → 27，差 9px 会让卡3 矮 9px、整页上移）、
  底栏「保存成功…」说明图标（13 → 19.5，差 3px 会让底栏矮 3px）。**做法**：给图标套 `height: 字号×1.5; display:flex; align-items:center` 包裹层，
  并把它写成**可测的纯函数**（`iconLineBox(size)` / `textLineBox(size)`，先补红断言 `iconLineBox is not a function` 再实现），模板用 `:style` 绑定 → DOM 里可直接量到。
- ⚠️ **设计稿「一行 vs 两行」与浏览器字体度量会打架，必须留证而不是偷偷改**：page-26 的蓝色提示条文案设计稿是**一行**
  （设计 PNG 实测墨迹 328px ≈ 9.9px/字），而浏览器 CJK 11px/字 = 363px > 卡片内宽 334 → 必然折两行 → 提示条 43 → 46（卡2 +6、页高 +1 的唯一来源）。
  这类「真源字号装不下设计的一行」只能改字号或改文案，**写进台账待拍板**，不要为了凑高度改字号。
- **工具与流程**：
  - `color-runs.py <png> v <列> blue|green|amber|gray` 支持按颜色特征取段（`--from/--to` 限定区间）→ 与 `pxdump.py` 配合精读边界，比 `bg` 模式更准。
  - `show-qf.py <measure.json> [字段…]` 式**每页一个取数脚本**（打印指定字段 + 自动附 phase2/3 交互结论），比整份 JSON 读进上下文省事。
  - ⚠️ **serve.py 换端口后先 `curl` 验一次 mock 内容再用**：本轮 5221 撞上残留实例、返回了另一套旧 mock（`/credentials` 回 10 条、别名「华东主线路」），
    若没先 curl 会把「mock 不对」误判成「前端接线错」。验法：`curl -s http://127.0.0.1:<port>/api/v1/credentials | head -c 120`。
  - `extract-measure-json.py <dump.html> <out.json>` **必须两个参数**（只给一个会 IndexError，而重定向会把报错写进 JSON 文件 → 后续 json.load 全崩）。
  - 无头 Chrome 的 `--dump-dom` 两次输出**字节数相同也可能都是新鲜的**：核对 `mtime` + 「只有新版本才有的标记串」（本轮用 `phase3` 出现次数）。
- **字号/文案一致性检查清单**要覆盖「占位文本 + 计数文本 + 空态三行 + 提示条整句 + 须知三条 + 底栏说明」（本轮 need 34 条 → `missingTexts []`）。

## 4.13 同页多帧（同页不同态）的还原规矩（2026-09-16 序号 12-v2 新增报价单-APIKey 下拉展开）

- ⚠️ **同页多帧必须先做「设计树逐层 diff」，不能只看文案差集**：page-apikey 与 page-26 是同一页的两个状态帧。
  文案差集（`diff-node-text.py`）只暴露了步骤卡、空态说明等显性差异；用 `cmp-frames.py <pageA> <pageB>`
  逐层比对子节点数量，才发现还有 3 处**「少了什么」**：①基本信息卡标题行少「必填提示」（kids 4→3）；
  ②字段-报价单号少 `container{单号说明}`（kids 3→2）；③内容区少「填写须知卡」（kids 4→2）。
  首轮实现只删了步骤卡 → DOM 实测第三张卡 top 1019、页高 **1308**（设计 1129）才暴露。
  **规矩：帧级差异一律落成 `variantFlags(variant)` 开关（纯函数 + 逐条断言），并在 H5 取数里断言
  `stepCardCount/requiredCount/quoteNoHintCount/tipCount/noticeCardCount` 全 0 —— 「多渲染了东西」只有数字能抓。**
- ⚠️ **同一元素在不同帧的间距可能不同**：`pad-of.py <page-id> <节点名>` 打印父链 padding ——
  「凭证说明」包裹层 page-26 = **6** / page-apikey = **10**（设计树实测 10.000030517578125）。
  差 4px 会顺着卡片传到底栏（凭证说明 709 → 713、模型卡 762、页高 1121 → 1125）。
  **判定法：跨帧复用组件时，凡是「间距」都要回各自的帧读一遍 padding，别用同一个 class 一把梭。**
- **抽共用视图是首选，但要确认产物**：12-v1/12-v2 共用 `src/components/quote-form/QuoteFormView.vue`
  （`variant` prop + `variantFlags`），页面只剩 5 行薄壳 → 旧页 740 例全绿、无重复实现。
  ⚠️ 抽组件后**必须 `ls dist/build/mp-weixin/components/**/`** 确认组件 `wxss` 真的产出了（本轮 13.5KB），
  否则小程序会裸奔（页面自己的 wxss 里已经没有任何页面样式）。
- **`<text>` 的行盒同理要逐帧读**：本页 `.card__title` 写 20（设计该帧 18）会造成模型卡 +2；
  但改它会波及 12-v1 已对齐的 4 处锚点 → **保留原值并把残差写进台账**（残差登记比强行对齐更诚实）。
- **描边在盒外/盒内是两种实现**：`.empty` 用 `border` 会让盒高 +2（166 / 160），改用
  `box-shadow: 0 0 0 0.8px` 后两帧同时命中设计值（164 / 158）。**凡「设计声明尺寸 = 真实可见尺寸」的盒子都用 ring。**
- **图标占位的可读性**：候选项图标最初画成「描边圆角方块」→ vision 与人都读成**复选框**（与「已选对勾」语义打架）。
  改成**实心圆**即可避免误读；**教训：CSS 形状占位要避开与真实控件同形**（勾选框/单选框形状不要用）。
- **无头 Chrome 取数的两个小规矩**：①`--dump-dom` 两次输出字节数相同也可能是新鲜的 → 核对 `mtime`
  （本轮 run7/run8 字节数一样、mtime 差 1 秒，比对后 85 字段 0 差异）；②`serve.py` 换端口后先
  `curl -s http://127.0.0.1:<port>/api/v1/<path>` 验 mock 内容，别把「mock 不对」误判成「前端接线错」。
- **新增工具**：`fetch-design.py <page-id>`（下载设计帧 PNG + 打印宽高）· `cmp-frames.py`（两帧设计树逐层 diff）·
  `tree-names.py <page-id> [起始节点] [深度]` · `pad-of.py <page-id> <节点名>`（支持 `\uXXXX` 转义避开中文参数编码）·
  `node-tree-raw.py <page-id> <id前缀>`（**设计树的子节点键是 `children` 不是 `kids`**）。

## 4.14 结果页/收口页 + 卡片内边距漏写 + 剪贴板取证（2026-09-16 序号 12-v3 新增报价单-保存成功）

- ⚠️ **卡片内边距漏写会让同类卡片同时矮一截，且 vision 完全看不出**：page-29 里我把 `.card` 只写成「背景 + 圆角」，
  忘记 `padding: 16px`（成功头部卡自己有 `.succ{padding:28px 16px}` 所以没露馅）→ 结果摘要卡 **218**（设计 250）、
  带出模型卡 **100**（设计 132）、整页 **954**（设计 1018）——两卡各 -32。
  **判定法：先 `rects(doc,'.srow')` 逐行量行盒** —— 行盒全对（38/38/38/40/30）而卡片矮 32 → 一定是卡片自身的内边距/边框问题，
  不用逐块猜。改后逐值相等：页高 1018 · 卡 256/250/132 · 提示卡 48 · 底栏 146。
- ⚠️ **`.card` 这种共享类被同页另一个卡类覆盖时要注意顺序**：`.succ` 必须写在其后（同权重、后者胜）；给共享类补 padding 前先确认覆盖关系。
- **结果页（无输入、只读）的取证清单**：`inputCount 0` · `tabbarExists false` · `missingTexts []`（含单号/脱敏 key/计数文案）·
  `rows` 逐行 · 芯片 h18/h20 · 底栏按钮 y/h；本页实测 10 行文本与设计 **0 差**、其余 ±1~2。
- **`?scenario=` 逐个回放出口**：结果页有多个出口（复制 / 主按钮 / 次按钮 / 关闭 / 返回），一次点击就会把 iframe 导航走 →
  载体页按 `location.search` 选场景，每次 Chrome 只跑一个场景（`?scenario=primary|secondary|close|back`），
  dump 也按场景分开（`evidence/measure-序号12-v3-<scenario>.json`），互不污染。
- **复制类 client-only 的硬证据**：无头 Chrome 里 click 非可信事件 → `navigator.clipboard` 读写会被拒（读必然 `READ_ERR`），
  **不能据此判页面坏**。做法 = 在 iframe 内 `Object.defineProperty(navigator,'clipboard',{value:{writeText:rec}})` +
  包一层 `document.execCommand`，再点按钮 → 拿到 **uni H5 真实调用链传出来的值**（本轮 `writeText('QT-20240615-0007')` + toast「报价单号已复制」），
  这比单测里的桩更硬，也比「读剪贴板」可行。
- ⚠️ **交互切片也要先看红**：本页第一遍把页面连交互一起写完，导致切片 3 一跑就绿（等于测试后写）。补救 = 从页面里**删掉**
  `@tap` 绑定与 handler（先 `cp` 快照到 `$LOCALAPPDATA/Temp/`）→ 跑出真红（7 失败）→ 从快照恢复 → 绿。
  **规矩：每个切片（含交互切片）都要有「看到红」的证据文件，别因为顺手写完就跳过。**
- **入口未接线的页要显式登记**：page-29 是「保存成功」页，但 12-v1/12-v2 的保存落点仍是模型定价页（历史推断）→
  本轮**不静默改**已验收页面，只实现本页（`?quoteId=` / storage 直进），把「是否改落点」写进台账待拍板。

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
