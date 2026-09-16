# 序号 4-v1 · 文本叶子维度收口报告（`page-24`「接入凭证-表单」）

- 轮次：cron `aap-tdd-run-20260916-2046`（2026-09-16 21:1x）
- 页面：台账序号 **4-v1** · `page-24` · 帧 `layer_id cb1de468-0658-4ccb-a1c3-46c2f48f6314` · 路由 `/pages/credential-submit/form`
- 维度：设计**文本叶子**（`textleaf-scan.py` → `textleaf-audit.py`）× 实现 DOM 的 computed 行盒 / 字号 / 字重
- 结果：**待判读 class 8 → 0**（全部判非偏差并登记）· 新增 1 条断言 + 源码变异证明 · **无源码改动**

## 1. 设计真源（人工指令 C：一切以当前画布为准）

| 项 | 结果 |
|---|---|
| 重抓帧（`recapture-page.py page-24 cb1de468-…`） | `design.json` sha256 `bd2498588806…` **逐字节相同** |
| `screenshot.json` | sha 变化 ⇒ **不是漂移**：它只存**导出资产 URL/ID**（`2099902651224866816` → `2100205357995782144`） |
| 重抓新导出的设计 PNG | 下载后 sha256 `f77955ca…`（430×1137）= 与本轮下载的留证 PNG **逐字节相同** ⇒ **无像素漂移** |

## 2. 红基线 → 判读 → 绿

- `textleaf-scan.py 4-v1`：mock `api` · 路由 `/pages/credential-submit/form` · `leafs 26` · `docH 1071`（空态）
- 红基线：**待判读 class 8**（`evidence/red-序号4v1-textleaf-待判读.txt`，两轮逐条相同）
- 判读后复跑：**待判读 0 · 已核定 8**（`evidence/green-序号4v1-textleaf-待判读0.txt`）

### 2.1 判据链（优先级 ①同帧显式 height ②design PNG 盒/盒算术 ③逐类墨迹 ④fs×lh；②③冲突以 ② 为准）

**硬证据 A · 同帧显式 height（判据①）**：page-24 的文本叶子除 4 个外全是 `fit_content + lineHeight 1.2`，但那 4 个是：

| 叶子 | 字号 | 显式 height | 用途 |
|---|---|---|---|
| `d09f9feb` 单个文件不超过 10MB | 11 | **16** | 印证 fs11 行盒 = 16（`card__tip` · `footnote__text`） |
| `919871df` 2.4 MB | 11 | **16** | 同上（文件行内副标） |
| `ee12aef8` 点击上传凭证文件 | 13 | **20** | 印证 fs13 行盒 = 20（两个占位类） |
| `7549512f` 营业执照扫描件.pdf | 12 | **18** | 印证 fs12 行盒 = 18（label / star / chip 文本） |

**硬证据 B · 整页盒算术（判据②）**：同一列 `x=25` 的**白卡段在设计与实现逐段相同**（`94..473 / 498..587 / 612..877 / 902..1011`）⇒ 卡片边界一致；
卡 pitch `404 / 114 / 290` = 卡高 `388 / 98 / 274` + 卡片间距 16（内容区 `gap=16` 为设计声明），且必须闭合到整页 1137：

```
顶部栏 74 = 16 + max(返回 36, 标题块 42) + 16            （42 = 标题 24 + 副标题 18）
基本信息卡 388 = 16 + 标题行 + 14 + 4×(标签行 + 8 + 44) + 3×14 + 16   ⇒ 标题行 20 · 标签行 18
检测类型卡  98 = 16 + 标题行 + 12 + chip(8 + 行盒 + 8) + 16           ⇒ chip 行盒 18（chip 34）
资料上传卡 274 = 16 + 标题行 + 12 + 上传区 144 + 12 + 文件行 54 + 16  （144 内含 fs13 的 h20 与 fs11 的 h16）
备注卡     118 = 16 + 标题行 + 10 + 备注框 56 + 16                    ⇒ 备注框 56 = 12 + 行盒 + 24 ⇒ 行盒 20
提交提示    25 = remixicon 字形盒 21(fs14×1.5) + padding-bottom 4      ⇒ 该行文本不承重
整页 1137 = 74 + 16 + 388 + 16 + 98 + 16 + 274 + 16 + 118 + 16 + 48 + 16 + 25 + 16  ✔
```

按声明模型 `fs×1.2` 落地（16.8 / 14.4 / 14.4 / 15.6）⇒ 四张卡各短 3.2~5.6px、整页 ≈1124，与设计 PNG 逐带冲突。

**硬证据 C · 逐类墨迹带（判据③，交叉验证）**：`evidence/cmp-序号4v1-文本叶子-逐类带.txt`
（窗口 = DOM 叶子 rect ±1 x / ±14 y）

| class | 设计 PNG ink 带 | 实现截图 ink 带 | 结论 |
|---|---|---|---|
| `card__title`（4 处） | 109..122 · 513..526 · 627..640 · 834..848 | 110..123 · 514..527 · 628..641 · 834..847 | ±1（H5 回退字体） |
| `field__label`（客户名称 / 信用代码） | 143..154 · 227..239 | 143..154 · 227..239 | **起点逐值相同** |
| `field__star`（2 处） | 144..148 · 228..232 | 144..148 · 228..232 | **起点逐值相同** |
| `type-chip__text`（3 处） | 553..564（三处） | 553..564 | **起点逐值相同** |
| `card__tip` | 628..640（带长 66） | 629..641（带长 66） | 起点 +1、带长相同 |
| `uni-input-placeholder`（4 处） | 182..193 · 266..277 · 350..362 · 434..445 | 183..194 · 266..277 · 350..361 · 434..445 | 1 处 +1、1 处逐值相同 |
| `uni-textarea-placeholder` | 917..923 | 918..923 | 起点 +1、带高相同 |
| `footnote__text`（`png-textbands` 直量） | 1101..1111（len 11） | 1102..1112（len 11） | 起点 +1、带长相同 |

### 2.2 未渲染叶子（3 条，**非缺陷**）

`深圳市恒信科技有限公司` / `营业执照扫描件.pdf` / `2.4 MB` = 设计帧的**示例数据**（已上传态）。textleaf 载体页只加载**空态**，故不渲染；
其渲染路径由同一载体页的 phase2（真实 `onPickFile` 后的已上传态）覆盖，并已断言 `fileName` / `fileSize` 的文案与行盒
（`__measure-form.html` 426 / 432 行；shot 模式还会把设计帧的示例值 `深圳市恒信科技有限公司` 打进输入框，见 612~624 行）。

## 3. 新增断言 + 变异证明（有牙齿）

- 本页此前只断言了 `.field__label` 的行盒，**星号（`.field__star`）无断言** → 载体页新增：
  `chk('star.lineHeight', c('.field__star', 'lineHeight'), '18px')`（phase2 **249 → 250** 条）
- 变异：`.field__star { line-height: 18px → 14.4px }`（= 声明模型的落地形态）→ `build:h5` → 测量 →
  **`FAIL star.lineHeight: got 14.4 want 18`（1 条红）** → `git checkout -- …/form.vue` → `build:h5` → 两轮 **250 条 0 失败**
- 证据：`evidence/red-序号4v1-starcheck-变异测试.txt` · `.agents/state/evidence/review-序号4v1-tlmut-run{1,2}.json`

## 4. 回归门（本轮无源码改动，仍需证明页面仍绿）

| 项 | 结果 |
|---|---|
| 载体页 `__measure-form.html` ×2 轮 | phase1 **6 条 0 失败** · phase2 **250 条 0 失败** · `docH 1137`（= 设计帧高）· `docW 430` · 溢出 0 · 文案缺失 0 |
| 两轮独立测量 | phase1 **32/32** · phase2 **33/33** 字段全等 · **不一致 0** |
| serve 实收请求行 | 两轮各 12 行 · **排序后集合逐字节相同**（1 条真实 `POST /api/v1/provider/qualifications` + 落地页 detecting 的 5 对轮询 GET） |
| `npm test` | **1185/1185 · 72 files** 连跑两轮（20:51:40 / 20:53:03） |
| `npm run type-check` | exit 0 |
| `npm run build:mp-weixin` | DONE（`pages/credential-submit/form.{js,json,wxml,wxss}`） |
| `review-artifacts.py` | 22/22 路由三件套齐备且注册 |
| `check-mock-fixtures.py --mock api` | FAIL 0 |
| 430 宽截图 | `logs/screenshots/20260916-2115-序号4v1-接入凭证表单-textleaf轮-h5-430宽.png` |

## 5. 口径更正（本轮）

序号 4-v1 的载体页 iframe 与台账「目标路由」都是 `/pages/credential-submit/form`（**无参数**；
`src/pages/credential-submit/form.vue` 不读任何参数，`grep -n "onLoad\|query"` 无命中）——
§4 与上轮简报里写的「带参路由 `/pages/credential-submit/form?id=c1`」**作废**。凡新增「带参路由」条目，先看页面源码是否读参。
