# 序号 9「【报价管理】模型报价设置-列表」载体页「设计期望值 checks」轮 · 报告

- 轮次：cron 轮 `aap-tdd-run-20260916-1205`（队列 8 第 8 页）
- 页面：`page-9`「9. 报价端·小程序 ｜ 【报价管理】模型报价设置-列表」→ 路由 **`/pages/quote-models/index`**（台账「目标路由」列）
- 帧引用：**帧名 + layer_id** = 「【报价管理】模型报价设置-列表」`bbdb4ec0-104b-4e96-b856-c1ddc529f18e`
- 载体页：`.agents/state/h5-measure/__measure-quote-setup.html`（430 宽 iframe · **272 条 checks**）
- mock：`.agents/state/h5-measure/api`
- ⚠️ 口径纠正：状态文件在办项曾把序号 9 写成「→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`」，
  与台账（`aap-feature-status.csv` 序号 9「目标路由 = /pages/quote-models/index」）及仓库实际不符；
  `/pages/model-pricing/index` 是**序号 11**。本轮按台账执行，并已把状态文件改回与台账一致。

## 1. 设计帧重抓（复核前必做）

- 先 `cmd /c start "" https://www.calicat.cn/design/2095515676955668480` 拉起 Calicat 编辑器（否则整包报「请先在浏览器中打开文件」），再
  `calicat_source.py page --url … --layer-id bbdb4ec0-… --page-id page-9 --out %TEMP%/aap-live9`。
- 与实现所依据的一份**逐字节比对**：`sha256 = bb278d4e8ffca932ef01d64ee673180c18eeba9c1cd370d02040269f815d2565` **完全相同** ⇒ 画布当前状态 = 实现所依据版本，**无漂移**。

## 2. 期望值口径（want 两类来源，零目测）

1. **声明值**：`.calicat/raw/pages/page-9/design.tree.json`
   - `python .agents/state/tree-view.py page-9` → 盒子的几何/内边距/圆角/stroke/effects/gap/布局
   - `python .agents/state/text-fields.py page-9` → 72 个文本叶子的 `fontSize / fontFamily→字重 / fontFill / 宽高 / 文案`
   - `python .agents/state/dump-node-fields.py page-9 <名>` → 单节点全字段（padding / gap / effects / stroke 的硬依据）
2. **fit_content 盒的真实几何**：设计截图 PNG 430×1211 像素实测
   - 本轮新增 **`png-rowmodal.py`**（逐行主色 + 白占比 → 卡片/间隙边界，`--runs` 打印分段）
     与 **`png-colorat.py`**（某行/列上「接近指定颜色」的连续区间 → 元素横向边界，如保存按钮蓝色 156..413、状态标 `#ECFDF5` 329..365）
   - 复用 `png-bands.py` / `png-textbands.py` / `png-xruns.py`

实测骨架（**整页 1211** = 顶栏 102 + 内容区 16/16/20/16 + 三卡 148/277/451 + 提示卡 52 + 底栏 98）：

| 区块 | 设计实测 |
|---|---|
| 顶部导航 | 0..102（内容行 48..90：返回 36×36 顶 51 · 标题块 24+18 = 42） |
| 卡1 报价主体 | 118..266（**148**）· 选择框描边行 177/178 + 225/226（盒 178..226） |
| 卡2 基本信息 | 282..559（**277**）· 名称输入框 360..408 · 凭证选择框 471..519 |
| 卡3 模型列表 | 575..1026（**451**）· 工具栏 `#F8FAFC` 623..666 · 模型行首 679/738/797/856/915（**行高 59**）· 底部说明 ink 994..1005 |
| 联动提示卡 | `#EFF6FF` 1043..1092（**52**）· 文本行 ink 1055..1065 / 1069..1078（**行距 14**） |
| 底部操作条 | 1113..1211（**98**）· 保存按钮蓝行 1134..1182 |

**本页定标的设计模型**（可直接复用于同族表单页）：

- CJK 文本行框 = `fontSize × 1.4` 取整（15→20 · 14→19 · 13→18 · 12→16 · 11→15），**设计显式 height 优先**（选择框主行 17 / 副行 15 / 价格行 16 / 副标题 18 / 标题 24）
- remixicon 字形行框 = `fontSize × 1.5`（20→30 · 18→27 · 16→24 · 13→20 · 12→18 · 11→17）
- `stroke{align:center,thickness:0.8}` → `box-shadow: 0 0 0 .8px`（`border` 占布局：选择框内容左界会从 **46** 变 46.8）——
  本轮实测 **Chrome 对 box-shadow 的 used 值保留 0.8px**（不取整；旧记录「computed 取整成 1px」仅适用于 border）
- `effects.drop_shadow` → `box-shadow`（卡片 (0,4,16,rgba(15,23,42,.06)) · 底栏 (0,-4,16,rgba(15,23,42,.05)) · 保存按钮 (0,6,16,rgba(37,99,235,.28))）

## 3. TDD 红 → 绿

| 步骤 | 命令 | 结果 |
|---|---|---|
| 红（探针侧） | `git stash push -- aap-client/src/pages/quote-models/index.vue` → `npm run build:h5` → `review-measure.sh 9-checks-red …`（**同一份探针两轮**） | **53 / 272**（两轮完全一致，`evidence/red-序号9-checks-设计期望值偏差.txt`），`docH 1202` |
| 绿 | `git stash pop` → `npm run build:h5` → `review-measure.sh 9-checks …` | **0 / 272**（`green-序号9-checks-设计期望值.txt`），`docH 1212`（设计帧 1211） |
| 一致性 | `cmp-measure-runs.py … phase2` | 两轮独立测量 **33/33 字段全等**，不一致 0（`cmp-序号9-checks-两轮.txt`；红基线同样 33/33 全等） |
| 复位干净 | `git stash pop` 后重建复跑 | 仍 **0 / 272** 且与复位前逐字段相同 |
| 数据侧 | `npm test` | **1172 / 1172 · 72 files 连跑两轮** |
| 类型 | `npm run type-check` | exit 0 |

## 4. 修掉的 12 类设计偏差

| # | 位置 | 修前 | 修后（设计依据） |
|---|---|---|---|
| 1 | 三张卡片投影 | 无（`box-shadow: none`） | **`0 4px 16px rgba(15,23,42,.06)`**（`5e64dc90`/`0b5dd403`/`ec8f4041` 的 `effects`） |
| 2 | 底栏 / 保存按钮投影 | 无 | **`0 -4px 16px rgba(15,23,42,.05)`**（`c0413210`）· **`0 6px 16px rgba(37,99,235,.28)`**（`259b9824`） |
| 3 | 三处 0.8 描边 | `border: 0.8px`（占布局） | **`box-shadow: 0 0 0 .8px`**（选择框 `#2563EB` / 输入框 `#E2E8F0` / 存为草稿 `#E2E8F0`）→ 内容左界回到设计值 46 |
| 4 | 字数提示行框 | `normal`（实测 16） | **15**（卡2 高 280 → 277 的第一项） |
| 5 | 凭证说明行（卡2） | 图标盒 20×20 → 行框 26 | **图标盒 14×18**（`98d26c37` fs=12）/ 行框 18（`#16A34A`） → 卡2 −2 |
| 6 | 模型工具栏 | 高 40 · 顶 626 | **高 44**（= 10 + 全选图标行框 24 + 10）· 顶 **623**（`6844bc87` padding 10/12 + `508d5ef9` fs=16） |
| 7 | 模型行 | 行高 58 · 首行 678 | **行高 59**（型号名行框 18 → **19**；PNG 行首步进 59）· 首行 **679** |
| 8 | 模型卡底部说明 | `padding-top 12` · 图标盒 13 | **`padding-top 16`**（外层 container 4 + 说明行容器 12）· 图标盒 **15×20**（`cddf5b02` fs=13） → 卡3 +17 |
| 9 | 联动提示卡 | 卡高 56（文案行距 16） | **卡高 52**（文案行距 **14**，PNG 两行 ink 间距 14） |
| 10 | 12 处图标盒 | 元素自身带尺寸/旋转（返回 17×17、下拉 14×14、行尾箭头 11×11…） | **按设计图层**：返回/帮助 20×27 · 钥匙 17×23 · 下拉 22×30 · 勾选 22×30 · 行尾 20×27 · chip 13×17 · 清空 18×24 · 工具栏 18×24 · 来源 14×18 · 凭证说明 14×18 · 底部说明 15×20 · 提示卡 18×24 · 保存 20×27；**形状（含旋转）移入 `::before`**，元素包围盒 = 设计尺寸 |
| 11 | 返回/帮助圆角 | `50%` | **`18px`**（设计声明的 r=18） |
| 12 | 整页高度 | `docScrollHeight 1202` | **1212**（设计帧 1211，差 1 = 内容区 `padding-bottom 20` 与 Figma 小数坐标链取整） |

修后整页链路与设计逐项吻合：`118/282/575` 卡顶 + `148/277/451` 卡高 + 提示卡 `1042..1094` + 底栏 `1114..1212`（PNG 1113..1211）。

## 5. 交互相有牙齿（`?scenario=actions`，两轮）

| 相 | 动作 | 实测（两轮逐字节相同） |
|---|---|---|
| phase3 | 点第 4 行 `gemini-1.5-pro` → 状态标变「已选」 | 计数 `已选 3 / 5` → **`已选 4 / 5`** · 第 4 行状态 **可选 → 已选** · hash 不变（client-only） |
| phase3 | 点「全选模型」→ 再点一次 | **`已选 5 / 5`** → **`已选 0 / 5`** |
| phase3 | 名称输入框填写「2024Q3 主线路报价」 | 字数提示 **`12/30`**（= 真实字数 12） |
| phase4 | 点底部「保存」 | serve 实收 **`POST /api/v1/quotes`**（body `{"name":"2024Q3 主线路报价","provider_id":"p1","credential_id":"c1"}`）+ **`POST /api/v1/quotes/q9/items`**（body `{"items":[{"model_name":"gpt-4o"}]}`）→ toast **「保存成功」** → hash → **`#/pages/model-pricing/index?quoteId=q9`**（台账序号 11 路由） |
| 纯测量轮 | 无场景 | 实收 **3 行**：`GET /provider/profile` · `GET /credentials?page=1&pageSize=20` · `GET /credentials/c1`（无多余请求） |

evidence：`requests-序号9-checks-run{1,2}.txt` · `requests-序号9-checks-actions-run{1,2}.txt` · `green-序号9-checks-交互回放.txt`。

## 6. 像素对账（实现截图 vs 设计 PNG）

`python .agents/state/cmp-bands-6-design-vs-impl.py <设计PNG> <实现截图> out.txt 3` →
**内容列 49/49 命中 · 条列 19/19 命中 · 未命中合计 0**（位移中位 0，范围 −3..+3）：
`evidence/cmp-序号9-设计PNGvs实现截图-结构带.txt`。
截图（430×1211）`evidence/20260916-1221-序号9-模型报价设置-checks轮-h5-430宽.png`（同件入 `logs/screenshots/`）。

## 7. 质量门

- `npm test` **1172 / 1172 · 72 files 连跑两轮**（12:19 / 12:20）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE → `dist/build/mp-weixin/pages/quote-models/index.{js,json,wxml,wxss}` 四件套；
  wxss 含本轮设计值：`box-shadow:0 0 0 .8px` ×2 · `box-shadow:0 4px 16px` · `box-shadow:0 -4px 16px` · `box-shadow:0 6px 16px` ·
  `line-height:19px` · `line-height:14px` · `line-height:15px` · `width:22px` · `height:30px` · `border-radius:18px`
- `npm run build:h5` DONE（430 宽 iframe 实测 + 截图）
- **本机无微信开发者工具** → mp-weixin 只作编译证明，真机/开发者工具验收留给人类（导入 `aap-client/dist/build/mp-weixin`）

## 8. 记入探针的口径 / 坑（本轮）

1. **状态文件与台账的序号↔路由映射冲突**：以台账「目标路由」列与仓库实际为准（本轮已在状态文件改正）。
2. **盒子的 rect 含 padding**：`counter.row.h`/`credHint.row.h` 这类「容器 + 行」结构，
   探针要断言**容器高**（= padding-top + 行框），行框本身靠 `lineHeight` / 图标盒高断言（首版写错 3 条）。
3. **`box-shadow` 的 used 值与声明值一致**：Chrome 保留 `0.8px`（旧口径「取整成 1px」只对 `border` 成立）。
4. **PNG 卡片边界必须用「逐行主色 + 白占比」**：本页三张卡都带投影、卡片之间的间隙被两张卡的阴影同时染色，
   `png-cardmap --x 30` 会把卡片与间隙连成一段；`png-rowmodal.py --runs` 才能给出 118..265 / 282..558 / 575.. 这类边界。
5. **设计稿自身的静态假数据**：字数提示写「13/30」，而同一帧的名称文案「2024Q3 主线路报价」只有 **12** 字 ⇒
   属设计稿 mock 数据（同族于 D3 的图例百分比）。实现按真实字数计算（`12/30`），探针只断言「格式 + 与名称长度一致」，
   并把设计字面量登记在 `designLiteralDiff` 字段留痕，**不照抄**。
6. **`model__check` 类**：模型行勾选框加了显式类名，避免 `.model > .ic` 同时命中行尾箭头。

## 9. 下一轮开工第一件事

队列 8 的 **序号 10**（台账「10. 报价端·小程序 ｜ 【报价管理】报价单详情」，载体页与 mock 目录按 `survey-harness-routes.py` 对照表取；
mock 目录 `api-10-2`）。
