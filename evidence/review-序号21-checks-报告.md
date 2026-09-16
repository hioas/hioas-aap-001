# 序号 21 复核报告 · page-21-2「【工作台与我的】我的 2」→ `/pages/mine/index`

- 轮次：cron `aap-tdd-run-20260916-1545`（2026-09-16 16:0x）
- 设计真源：Calicat 文件 `2095515676955668480` / 画布 `2095515676976640000`
- 帧引用：**帧名「21. 报价端·小程序 ｜ 【工作台与我的】我的 2」+ layer_id `e537204e-faf7-416b-8669-1347d581490c`**
- **设计帧重抓**（人工指令 C）：`calicat_source.py page --layer-id e537204e…` → `design.json` sha256 `cd12a92b…` 与留证**逐字节相同**（`cmp` 无差异）→ 无漂移
- 设计 PNG：430×990（本轮重下载 sha256 `d73cf39a…`，与建页时同一张）

## 1. 交付物

| 项 | 内容 |
|---|---|
| 载体页 | `.agents/state/h5-measure/__measure-mine.html`（由 248 行旧体例、无 checks 重写为 430 宽 iframe + **230 条设计期望值 checks**） |
| 生成脚本 | `.agents/state/build-probe-21.py`（四段骨架切自 `__measure-messages.html`，逐字节复用 helpers） |
| 截图 | `evidence/20260916-序21-我的页-checks轮-h5-430宽.png`（430×990 = 设计帧尺寸；同件入 `logs/screenshots/`） |
| 证据 | `evidence/red-序号21-checks-设计期望值偏差.txt` · `evidence/green-序号21-checks-设计期望值.txt` · `evidence/review-序号21-*-run{1,2}.json` · `evidence/requests-序号21-*.txt` |
| 像素对账 | `evidence/cmp-序号21-设计PNGvs实现截图-结构带.txt` |
| mock | `.agents/state/h5-measure/api-21`（本轮补 `v1/usage/summary`、`v1/auth/me` 两个落地页 fixture；`check-mock-fixtures --mock api-21` 9 PASS + 反向体检 PASS / FAIL 0） |

## 2. 红→绿（严格 TDD）

- 红基线（**最终版探针** + 未修改源码，两轮）：**17 / 230** 失败，`docH 990`；两轮失败清单逐条相同。
- 绿（修复后 + 同一份探针，两轮）：**0 / 230**，`docH 990` = 设计帧高，溢出 0，文案缺失 0；两轮独立测量 **43/43 字段全等**（不一致 0）。
- 红基线里有 **2 条是探针自身期望值 bug**（已在探针里修正后**重跑红基线**，保证红/绿同版探针）：
  1. `head.tags.top` 把「带 `padding-top: 8` 的容器」当成「子行」写 want 82 → 改为容器 74 + 新增 `.head__type.top = 82`（设计是「容器 a3c59082 + 标签行」两层）；
  2. `entries.values` 只写了 3 个值，漏了第 5 行「我的消息」的「待阅读 3」（设计 row5 确有值节点）→ 改为 4 值 / 4 右边 / 4 色。

## 3. 修掉的 10 类页面偏差（先红后绿）

| # | 偏差 | 设计依据 | 修法 |
|---|---|---|---|
| 1 | 头像字形盒 16×16 | `85003c7e` fs30 remixicon **声明 w33** → 字形行盒 33×45 | 盒改 33×45，形状（头 14 + 肩 26×11，合计墨迹 26×25）画在盒内 `::before/::after` |
| 2 | 类型标签文字行盒 16 | `dec24f88` fs11 无显式 height → `lineHeight 1.2` = 13.2 | `line-height: 13.2px` |
| 3 | 「已认证」文字行盒 16 | `ba4503ea` 同上 | 13.2px |
| 4 | 钱包标题行盒 21 | `a5722e5c` fs14 无显式 height → 16.8（行高 30 由 chevron 字形盒决定） | 16.8px |
| 5 | 提现文案行盒 20 | `1926f470` fs13 → 15.6 | 15.6px |
| 6 | 行图标字形盒 16×16（两卡共 9 处） | 字形层**声明 w20** + fs18 行盒 27 | 盒改 20×27；形状 17×16 移入 `::before`（x 44→42、top 逐行 +6，与 PNG 图标墨迹 43..59 / 373..388 对齐） |
| 7 | 行标签行盒 19.5 | `efe090dd` 等 fs13 无显式 height → 15.6 | 15.6px |
| 8 | 行值行盒 18 | `1d6d01c9` 等 fs12 → 14.4 | 14.4px |
| 9 | 胶囊文字行盒 14 | `36fd8a4c` fs10 → 12 | 12px |
| 10 | 字形颜色读不到（`background: currentColor` 挂在元素自身） | D5：占位形状画在伪元素上 | 形状移入 `::before`（`background: currentColor`），探针读 `::before` |

**未改**（设计↔实现的有意差异，已登记 `designLiteralDiff`）：三张卡用 ring（盒外 1px）表达 Figma 中心描边 → 可见描边行比设计外移 1px，而卡内容盒 140/192 · 344/299 · 655/235 与设计逐值相等。

## 4. 像素对账（设计 PNG vs 实现截图，±3）

- 卡片内容区 x=36..394：设计 16 带 / 实现 16 带 → **命中 16 / 未命中 0**（位移中位 0，min −2 max +1）
- 明细条/图标列 x=194..356：设计 13 / 实现 17 → **命中 13 / 未命中 0**（位移中位 0，max +1）
- **合计 29 命中 / 0 未命中**（本循环第二个零未命中页）

## 5. 交互相（六出口，各两轮）

| 场景 | 实测 |
|---|---|
| 首屏（纯测量） | 7 行只读 GET（profile / payments / quotes / credentials / reports / contracts?status=PENDING_SIGN / notifications?unread=true），**零写请求** |
| `?scenario=withdraw` | toast「提现功能暂未开放」· hash 不变 `#/pages/mine/index` · 7 行全只读（client-only + missing-prd：18-API 无提现端点） |
| `?scenario=rows-quotes` | → `#/pages/quotes/index`（落地渲染「报价单」）· requests 两轮**逐字节相同** |
| `?scenario=usage` | → `#/pages/usage/index`（落地渲染「用量概览」）**序号 22 已实现** → 旧台账「未实现 → 降级」口径作废 |
| `?scenario=settings` | → `#/pages/settings/index`（落地渲染「账号与设置」）**序号 23 已实现** |
| `?scenario=tab-workbench` | → `#/pages/workbench/index`（数据台完整渲染：图例 42/28/14/4/6/6、模型 4 行） |
| `?scenario=tab-mine` | hash 不变 `#/pages/mine/index`（当前模块不跳转）· 行数仍 5 |

> requests 比对口径：首屏 7 个 GET 由 `Promise.all` 并发发出，落盘**顺序**会抖动 → 用「**集合相等**」判一致（已逐行核对内容）；确定性场景（rows-quotes）仍逐字节相同。

## 6. 质量门

- `npm test` **1181/1181 · 72 files 连跑两轮**（15:56:51 / 15:57:25）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE（`pages/mine/index.{js,json,wxml,wxss}` 齐备 + app.json 已注册；wxss 内含本轮设计值 `width:33px;height:45px` · `width:17px;height:16px` · `line-height:13.2px ×2` · `15.6px ×2` · `16.8px` · `14.4px` · `12px`）
- `npm run build:h5` DONE
- `python .agents/state/review-artifacts.py`：台账 22 条路由的 mp-weixin 三件套齐备且注册
- **共用组件回归门**（`AppTabBar` 被 page-20-2 与 page-21-2 共用）：序号 20 载体页复跑 **148 条 0 失败**、两轮 30/30 全等（先跑 `refresh-notification-mock.py --mock api-20` 修掉测量面的相对时间过期 —— 该失败与本轮改动无关）
- `python .agents/state/check-mock-fixtures.py --mock api-21`：**9 PASS + 反向体检 PASS / FAIL 0**

## 7. 本页定标（供同族「个人中心 / 卡片列表」页复用）

- 图标字形盒 = **设计声明宽 × 字号×1.5**（头像 fs30 声明 w33 → 33×45；行图标 fs18 声明 w20 → 20×27；TabBar fs22 → 33）。
- 文本行盒：**设计显式 height 优先**（公司名 26 · 余额标签 16 · 金额 34 · 明细值 22）；无显式 height 走 `lineHeight 1.2`
  （14 → 16.8 · 13 → 15.6 · 12 → 14.4 · 11 → 13.2 · 10 → 12）。**同一页里 fs11 也可能有显式 h16**（余额标签）→ 逐节点判，不能一刀切。
- 卡片结构账：钱包卡 20 + 标题行 30 + 16 + 余额行 52 + 16 + 明细行 38 + 20 = **192**；
  入口卡 8 + 5×56 + 3×1 + 8 = **299**；证照卡 8 + 4×54 + 3×1 + 8 = **235**；TabBar 8 + 33 + 3 + 16 + 24 = **84**。
- 「容器 padding-top N + 子行」= 两层（容器盒 = N + 行盒）→ 探针要分两层断，否则自造假偏差。
- 设计帧字面量（不照抄/派生）：`待阅读 3` 的字色是字面量 `rgba(0,0,0,1)`；`提现` 按钮 missing-prd；相对时间/计数均由接口派生。
