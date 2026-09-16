# 序号 4 复核报告 · 载体页「设计期望值 checks」轮（2026-09-16 09:55）

- 页面：`4. 报价端·小程序 ｜ 【检测验真】提交接入凭证 2`（`layer_id 9eaacf9c-a873-4046-b8b5-f7e695d18cca`，抓取 id `page-4-2`）
- 路由：`/pages/credential-submit/index`（载体页 `.agents/state/h5-measure/__measure-submit.html`，mock 目录 `api`）
- 本轮轮次 id：`aap-tdd-run-20260916-0945`

## 1. 设计真源与帧重抓（人工指令 C）

| 项 | 结果 |
|---|---|
| 帧 design 重抓（2026-09-16 09:59，`calicat_source.py page --layer-id 9eaacf9c…`） | `design.json` **sha256 逐字节相同** `29757a6fc46e8c5e1835c2eb35dfc2e5af12111ebbe90b2c5c745f13b2e6f6c7` |
| 结论 | 画布当前状态 = 实现所依据的版本，**无漂移**，无需重做 |
| 重抓前状态 | 首次整包重抓 22 帧全部 FAIL（`请先在浏览器中打开文件`）→ `cmd /c start "" https://www.calicat.cn/design/2095515676955668480` 拉起编辑器后成功（该步骤已写进状态文件 §5） |

## 2. 期望值来源（两类，逐条可复现）

- **A 声明值**：`.calicat/raw/pages/page-4-2/design.tree.json` + `page-4-2-nodes.txt` + `dump-node-fields.py`（padding / gap / 固定宽高 / cornerRadius / stroke / fills / fontSize / fontFamily / 文案）。
- **B 盒子高度（fit_content 行的真实高度）**：设计 PNG 色带实测 ——
  ```bash
  curl -o design.png https://prototype-prod-1254106194.cos.ap-beijing.myqcloud.com/calicat/file/2099898044323852288/canvas/image/2099898044323852288.png
  python .agents/state/png-rows.py design.png v 30 90 960 1        # 卡边界 108/241 · 253/425 · 437/574 · 586/940
  python .agents/state/png-rows.py design.png v 44 100 260 1       # 输入框 150..196（46 高）
  python .agents/state/png-profile.py design.png 36 353 394 409    # 安全提示盒 353..408（56 高）
  ```
  得到：顶部导航 **96** · 卡高 **133/172/137/354** · 卡间距 **12** · 底部操作条 **84** · frame 1040。

**设计内部模型（B 与 A 自洽）**：设计里 fit_content 行的真实高度 = **图标字形的行框 = fontSize × 1.5**
（返回图标 24 → 36，撑出顶部栏 48+36+12 = 96；提示行图标 14 → 21，撑出卡1/卡3 的 21 高提示行）；
文本图层自带固定高 18（13px 标签/厂商名/模型名）与 16（11px 说明行/底部提示）。
逐项验算：卡1 16+18+8+46+8+21+16 = 133 ✓ · 卡2 16+18+8+46+12+56+16 = 172 ✓ · 卡3 16+22+8+46+8+21+16 = 137 ✓ ·
卡4 16+18+12+16+12+126+12+98+12+16+16 = 354 ✓（vendor1 126 / vendor2 98 与 PNG 的 126/98 逐项相同）。

## 3. 红 → 绿（严格 TDD：先写会红的断言）

| 阶段 | 结果 |
|---|---|
| 红基线 | `checkCount 206 · checkFailCount 45`（两轮完全相同；转录 `red-序号4-checks-设计期望值偏差.txt`） |
| 绿 | `checkCount 212 · checkFailCount 0`（`green-序号4-checks-设计期望值.txt`） |
| 两次独立测量 | `flat` 33/33 字段全等，0 不一致（`cmp-measure-runs.py … run1 run2 flat`） |
| 溢出 | `overflowingCount 0` · `docScrollWidth 430 = innerWidth` |
| 缺文案 | `missingTexts []` |

### 修掉的 45 条偏差（全部有设计依据）

| # | 偏差 | 依据 | 修法 |
|---|---|---|---|
| 1 | 顶部导航 **84 → 96** | PNG `v 8`：白色 0..95 | 返回图标盒 24×24 → **26×36**（remixicon 24px 行框 36） |
| 2 | 卡片高 **126/169/132/343 → 133/172/137/354** | PNG `v 30` 卡边界 | 行框改 18/16/21（见 §2 模型）；安全提示文本行框 18 → 盒 56 |
| 3 | 卡片内容宽 **356 → 358**（inputBox/vendor/已配置 chip 右边 393 → 394） | 设计 padding [16,20,16,20] → 398-40 = 358 | 卡描边 `border` → **`box-shadow: 0 0 0 1px`**（Figma center 描边不占布局） |
| 4 | 图标占位盒偏小（提示 12→16 · 输入 14→20 · 密钥 12→20 · 已配置 9→14 · 提交 14→22） | 设计图标图层 width = 26/20/16/14/22 | `.glyph` 改为设计尺寸盒 + 形状移入 `::before`（D5 仍为 CSS 占位，只改盒子） |
| 5 | 提示文本左移 **6 → 4** | 设计容器 padding [0,0,0,4] | `margin-left: 4px` |
| 6 | 「已配置」字重 **600 → 500** | 设计 fontFamily SourceHanSans-Medium | `.chip__text--success { font-weight: 500 }` |
| 7 | 编辑图标盒 24×24 → 20×27 | 设计 236156ed（18px → 20×27） | `.input-box__action` |

## 4. 像素级对账（实现截图 vs 设计 PNG 墨迹带）

同列 x=30 逐带比对（实现截图 `20260916-0955-序号4-提交接入凭证-checks轮-h5-430宽.png`，440×1000 窗）：

| 带 | 设计 PNG | 实现截图 |
|---|---|---|
| 顶部栏白 | 0..95 (96) | 0..95 (96) ✓ |
| 页面底 | 96..106 (11) | 96..106 (11) ✓ |
| 卡1 | 109..239 (131) | 109..239 (131) ✓ |
| 卡间距 | 242..251 (10) | 242..251 (10) ✓ |
| 卡2 | 254..423 (170) | 254..423 (170) ✓ |
| 卡间距 | 426..435 (10) | 426..435 (10) ✓ |
| 卡3 | 438..572 (135) | 438..572 (135) ✓ |
| 卡间距 | 575..584 (10) | 575..584 (10) ✓ |
| 卡4 | 587..938 (352) | 587..938 ✓（816 起被固定操作条覆盖，见下） |

**唯一有意偏离**：设计里操作条在文档流末尾（956..1040），实现用 `position: fixed`（小程序固定底栏）→ 栏高 84 与 `barPinned true` 仍与设计一致；表单区 `padding-bottom 108`（设计 0+16）避免遮挡，`atBottom.lastCardFullyAboveBar true`。

## 5. 与上一轮留证（08:11）的差异判读

`cmp-序号4-上一轮vs本轮.txt`：公共字段 14 全等；53 处差异全部可解释 ——
① 本轮的 7 类修复（卡边界 96/234/415/560 → 108/253/437/586；`docScrollHeight 1011 → 1048` 增量 +37 = 卡片堆叠增量 +37，别无漂移）；
② 探针字段集升级（旧载体页无 `checkCount/checkFails/...`，本轮无 `firstInputBox/glyphCount/...`）；
③ 脱敏值：设计字面量 `sk-••••••••••••••••4f2a` 与共享 mock `sk-prod-••••••••2f9a` 的已知冲突 → 本轮改为**断言 mock 值 + 记录 knownMockConflicts**（旧留证把它报成 missingTexts，属口径问题不是页面缺陷）。

## 6. 质量门

- `npm test` **1168/1168 · 72 files 连跑两轮**（`green-序号4-checks-全量轮{1,2}.txt`）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE → `pages/credential-submit/{index,form}.{js,json,wxml,wxss}`；
  产物含本轮修复（`box-shadow:0 0 0 1px` · `line-height:18px` ×3 · `width:26px;height:36px` · `width:16px;height:21px`）
- `npm run build:h5` DONE；`review-artifacts.py`：台账 22 路由三件套齐备且注册

## 7. 遗留

- 真机/微信开发者工具验收仍留给人类（本机未装开发者工具）；H5 为可视化面。
- 交互复核：本载体页是**单段几何测量**（与上一轮 `__measure-submit.html` 的体例一致，无交互回放段）；
  本页交互证据仍由建页轮与 08:11 复核轮的 2 段测量 + `tests/pages/credential-submit.spec.ts`(23) 覆盖。
  本轮只改 SCSS 与图标形状（形状移入 `::before`），事件绑定（`.model-row` / `[data-testid="apikey-edit"]` /
  `save-btn` / `submit-btn`）未动，23 条交互用例全绿。
- 本轮实测只用 `h5-measure/api` 的 fixture（serve 实收 1 行：`GET /api/v1/credentials/c1 200`）；
  `npm run dev:h5` 的 dev-only 假后端只拦 `/api/v1/auth/*`（vite.config.ts 第 22 行），本页取不到数，故不作为数据源。
- 队列 8 下一页：**4-v1**（`page-24` 接入凭证-表单 → `/pages/credential-submit/form`，载体页 `__measure-form.html`，仍是旧的非 iframe 体例）。
