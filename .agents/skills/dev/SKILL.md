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
