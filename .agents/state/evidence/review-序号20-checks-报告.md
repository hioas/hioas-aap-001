# 序号 20 ·【合同与通知】站内信列表 2 —「设计期望值 checks」补维度报告

- 帧：`20. 报价端·小程序 ｜ 【合同与通知】站内信列表 2`，layer_id **`76700922-02b2-45f3-9343-256eb34bace0`**（画布 1，文件 `2095515676955668480`）
- 目标路由：`/pages/messages/index`（台账序号 20 行「目标路由」列为准）
- 载体页：`.agents/state/h5-measure/__measure-messages.html`（430 宽 iframe + **148 条设计期望值 checks**；构建脚本 `build-probe-20.py`，四段骨架切自 `__measure-contract.html`）
- mock 目录：`api-20`
- 轮次：cron `aap-tdd-run-20260916-1525`

## 1. 设计真源与漂移核对（人工指令 C）

- 重抓前先 `cmd /c start "" <design-url>` 拉起 Calicat 编辑器，再重抓 `page-20-2`：
  `design.json` sha256 **`02600c1b…`** 与实现所依据的存档 `cmp` 报 **BYTE-IDENTICAL** → 画布当前状态 = 实现所依据版本，**无漂移**。
- 设计截图 PNG：`430×760`，重下载 sha256 **`b1398fdd…`** 与建页时存档**逐字节相同** → `.agents/state/design-shots/page-20-2.png`。

## 2. 红 → 绿（本轮主交付）

| 阶段 | 探针 | 结果 |
|---|---|---|
| 红 | 144 条（同一份探针两轮） | `checkFailCount 14/144` · `docH 760`（13 条真偏差 + 1 条测量面过期） |
| 绿 | 148 条（修正 2 处探针 want + 5 处页面偏差后） | **`checkFailCount 0/148`** · `docH 760` = 设计帧高 · 溢出 0 · 文案缺失 0 |

- 两轮独立测量 `run1/run2` 全等：`cmp-measure-runs.py … phase1` → **30/30 字段全等 · 不一致 0**（红/绿两阶段各自都做了两轮）。
- 红基线转录：`evidence/red-序号20-checks-设计期望值偏差.txt`（含分诊）；绿基线转录：`evidence/green-序号20-checks-设计期望值.txt`。
- 单测红→绿：`evidence/red-序号20-单测-tabbar字重.txt`（3 failed | 12 passed）→ 绿 **15/15**。

## 3. 红基线 14 条的分诊（避免把探针 bug 记到页面账上）

**① 页面真偏差 5 类（本轮修掉）**

| # | 键 | got → want | 依据 | 修法 |
|---|---|---|---|---|
| 1 | `nav.badgeText.lh` | 14 → **13.2** | 未读胶囊文本 `f947ddee` fs11 · lineHeight 1.2（胶囊 h22 固定，行盒不影响布局） | `line-height: 13.2px` |
| 2 | `nav.readAllText.lh` | 15 → **14.4** | 「全部已读」文本 `9225bd30` fs12 · lineHeight 1.2 | `line-height: 14.4px` |
| 3 | `filters.chipText.lh` | 15 → **14.4** | chip 文本 `0240859d` fs12 · lineHeight 1.2 | `line-height: 14.4px` |
| 4 | `card.glyphBox*` | 选择器不存在 → **22×30 @172/276/…** | 卡图标字形层 `ca015b92` fs20 remixicon **声明 w22** · 字形行盒 = 字号×1.5 = 30（同 12-v3/15 的图标盒口径） | 新增 `.msg__glyph-box`（22×30）+ 形状 `.msg__glyph` 17×17 画在盒内 |
| 5 | `tabbar.labelWeights` | `400,400,400,600` → **全 400** | page-20-2 的 TabBar 四行文本**全为 SourceHanSans-Regular**（page-21-2 的高亮项才是 SemiBold 600）→ 字重逐帧 | 共享组件新增 `activeWeight` prop（默认 600，本帧传 400） |

**② 探针自身 bug 2 类（改探针，不改页面）**

- `card.contentRowTops/H`、`card.timeRowTops/H`：设计是**两层**（`container padding-top 4` + 文本行）→ 容器盒 = `4 + 行盒`（22 / 20），
  我第一版把文本行的 18/16 写成了容器盒 → 假偏差 4 条。另补 `card.contentBox*` / `card.timeBox*` 直接断言文本盒（18/16），与 PNG 墨迹（摘要 193..205 · 时间 214..224）互证。
- `filters.chipX` / `filters.chipW`：设计声明文本宽 25（chip 49），而 H5 回退字体 CJK 每字**恰 12** → 文本盒 24 → chip **实测 48**，其后每枚累计 −1（第 4 枚 190→**187**）。
  want 改为「同一 padding(12)/gap(9) + 实测文本宽」链算值 [16,73,130,187]/48，并登记残差（**不写死 49**：换字体/真机字体不该被硬编码掩盖）。

**③ 测量面过期 1 条（假缺陷）**

- `card.times` / `missingTexts`：`10 分钟前` 变 `13 分钟前` —— mock 的 `created_at` 是**绝对**时间戳，而设计写的是**相对**时间；
  建页轮（05:2x）写死的时间戳在 08:11 复核轮就已经漂成 `['10 分钟前','2 小时前']` 两条假缺陷。
  本轮新增 `refresh-notification-mock.py`（按 `formatMessageTime` 同规则把 5 条时间重置为「相对现在」），并在测量前重跑 —— 绿轮 `missingTexts []`。

## 4. 本页定标（供同族「列表 + 底部 TabBar」页复用）

- **图标字形盒 = 声明宽 × 字号×1.5**（卡图标 fs20 → 22×30；「全部已读」fs16 → 18×24）；形状画在盒内（D5），墨迹按设计（本页 17）。
- **文本行盒**：显式 `height` 优先（摘要 18 / 时间 16）；无显式 height 的走设计 `lineHeight 1.2`（12px→14.4 · 11px→13.2）；
  只有「标题行 18」「导航内容行 26」两处取 PNG 实测（设计树 lineHeight 1.2 算不出 26）。
- **「容器 padding-top N + 文本行」结构**：容器盒 = N + 行盒（摘要/时间行 22 / 20），文本盒另测 —— 探针两套都要断，否则会自造假偏差。
- **`stroke{align:center,thickness:1}` → `box-shadow: 0 0 0 1px #EEF2F7`**（`border` 会占布局）；本页 5 张卡**只有描边、无 drop_shadow**。
- 页面结构：导航 86（48 + 内容行 26 + 12）· 筛选行 54（12 + chip 30 + 12）· 列表 140..660（padding-top 12 · 5×92 · 间隙 12）·
  卡内 16 + (18 + 4 + 18 + 4 + 16) + 16 = 92 · TabBar 676..760（16 + 8 + 33 + 3 + 16 + 24）。

## 5. 像素对账（设计 PNG vs 实现截图，±3）

`python .agents/state/cmp-bands-6-design-vs-impl.py <设计PNG> <实现PNG> evidence/cmp-序号20-设计PNGvs实现截图-结构带.txt 3`

- 卡片内容列 x=36..394：设计带起点 14 个 / 实现 14 个 → **命中 14 / 未命中 0**，位移中位 +1（0/1）。
- 明细条列 x=194..356：设计 12 / 实现 12 → **命中 12 / 未命中 0**，位移 min −3 max +1 中位 0（−3 = 第 4 枚 chip 的 CJK 残差）。
- **结构带未命中合计 0（命中 26）**；实现截图 `430×760` = 设计帧尺寸。
- 脚本标题文案固定写「序号 6」（`cmp-bands-6` 复用未改文案），与本次对账对象无关。

## 6. 交互相（四出口 + guard，各两轮，serve 实收请求行逐字节相同）

| 场景 | 实收请求 | 断言 |
|---|---|---|
| `?scenario=guard` | **1 行**（仅首屏 GET） | 点「已选中」的 chip 不重复取数（onFilterTap 同项短路）→ 「没有偷偷发请求」由请求行数直接证明 |
| `?scenario=filter` | 2 行 | 首屏 GET + **`GET /notifications?page=1&pageSize=20&unread=true`**；chipBgs 实测 `[灰,蓝,灰,灰]`、activeChip「未读」、hash 不变 |
| `?scenario=readall` | 8 行（= 1 GET + 3 POST + 1 GET，POST 各记两行） | **3 条真实 `POST /notifications/n{1,2,3}/read`**（18-API 无批量接口 → 逐条，不臆造 read-all）→ 重拉列表；toast 空（设计帧无稿，不臆造文案） |
| `?scenario=card` | 5 行 | **`POST /notifications/n1/read`** → 重拉 → 落 `#/pages/report/index?reportId=r1`（biz_type REPORT + biz_id r1）→ 落地页真实取数 `GET /reports/r1` |
| `?scenario=tab` | 3 行 | TabBar「工作台」→ 落 `#/pages/workbench/index`，落地页渲染出「数据台 · 2026-09-16」整页文案（fixture 齐备） |

- 纯测量轮两轮各只 **1 行**请求（`GET /notifications`），零写请求。

## 7. 质量门

- `npm test`：**1181/1181 · 72 files 连跑两轮**（`evidence/green-序号20-全量轮1.txt` / `轮2.txt`，+3 新用例）
- `npm run type-check`：exit 0
- `npm run build:mp-weixin`：DONE，`pages/messages/index.{js,json,wxml,wxss}` 齐备（wxss 含 `.msg__glyph-box{width:22px;height:30px}`、`.msg__glyph{width:17px;height:17px}`、`line-height:13.2px` ×1 / `line-height:14.4px` ×2；组件 wxml 内联 `font-weight`）
- `npm run build:h5`：DONE（430 宽实测与截图同源）
- `python .agents/state/check-mock-fixtures.py --mock api-20`：**5 PASS / FAIL 0** + 反向体检通过（本轮新增 5 条 check + 3 个落地页 fixture）
- `python .agents/state/review-artifacts.py`：**22/22** 路线三件套齐备且注册
- 共用组件回归门（AppTabBar 被改动）：序号 21 载体页 `__measure-mine.html` 复跑 → 两轮 **73/73 字段全等**、`docScrollHeight 990`、溢出 0、文案缺失 0、`tabbarActiveStyle.fontWeight` 仍 **600**（默认值未变，21-2 帧不受影响）
- 截图：`logs/screenshots/20260916-序20-站内信列表-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`，430×760）

## 8. 设计字面量登记（不照抄/派生项）

1. 徽标「3 条未读」由未读条数派生（`unreadBadgeText`），设计帧示例值 3 来自 mock 的 3 条未读。
2. 5 条时间文案是**相对时间**派生规则（PRD 零定义，台账序号 20 备注④）→ mock 时间戳由 `refresh-notification-mock.py` 按设计写法生成（测量前必跑）。
3. chip 宽设计 49 / H5 实测 48（CJK 残差，未写死）；标题「消息」设计 w41 / 实测 40。
4. 图标字形为 CSS 占位（D5）：卡图标形状墨迹 17（设计 remixicon 墨迹 17×20）；「全部已读」形状 14（设计墨迹 15）；TabBar 形状 18×18（设计墨迹 17×20，共享组件未改，避免越帧 churn）。
5. toast 文案（数据加载失败 / 操作失败）设计帧无稿 → 占位（missing-prd）。
6. 消息卡落点由 `biz_type` → 路由推断（PRD 零枚举，台账序号 20 备注⑧）→ 未知一律不跳转。

## 9. 本轮新增工具

`build-probe-20.py`（按页组装 checks 探针，第六例）· `shot-20.sh`（430×760 整页截图）·
`refresh-notification-mock.py`（相对时间 mock 重置）· `js-depth-lines.py`（逐行大括号净值，定位载体页切片不闭合）·
`check-mock-fixtures.py` 新增 api-20 五条 check。

## 10. 切点坑（写进状态文件 §5）

`__measure-contract.html` 里 `function bgsIn` 的收尾 `}` 与 `async function main() {` **在同一行**（`      }      async function main() {`），
按行切片到 `main` 之前会把它切掉 → 大括号净值 +1，`node --check` 只报「Unexpected end of input」不给行号。`build-probe-20.py` 显式补回该 `}` 并用 `js-depth.py` 复验净值 0。
