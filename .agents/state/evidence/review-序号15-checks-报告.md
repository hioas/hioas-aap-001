# 序号 15 ·【合同与通知】合同签署 2 —「设计期望值 checks」补维度报告

- 帧：`15. 报价端·小程序 ｜ 【合同与通知】合同签署 2`，layer_id **`14d79713-8314-41a4-a8df-b4aff9ecd7b8`**（画布 1，文件 `2095515676955668480`）
- 目标路由：`/pages/contract/index`（台账序号 15 行「目标路由」列为准）
- 载体页：`.agents/state/h5-measure/__measure-contract.html`（430 宽 iframe + **239 条设计期望值 checks**；构建脚本 `build-probe-15.py`，四段骨架切自 `__measure-quote-success.html`）
- mock 目录：`api-15`
- 轮次：cron `aap-tdd-run-20260916-1505`

## 1. 设计真源与漂移核对（人工指令 C）

- 重抓前先 `cmd /c start "" <design-url>` 拉起 Calicat 编辑器（否则整包重抓会 FAIL「请先在浏览器中打开文件」）。
- 重抓 `page-15-2` → `design.json` sha256 **`ca94e93e…`**，与实现所依据的存档 `cmp` 报 **BYTE-IDENTICAL** → 画布当前状态 = 实现所依据版本，**无漂移**。
- 设计截图 PNG：`430×1231`（`.agents/state/design-shots/page-15-2.png`，本轮下载）。

## 2. 红 → 绿（本轮主交付）

| 阶段 | 探针 | 结果 |
|---|---|---|
| 红-1 | 239 条（want 全按设计声明） | `checkFailCount 5/239` · `docH 1231` |
| 红-2 | 239 条（其中 `tip.text.lh` 的 want 按 PNG 改为 16） | `checkFailCount 1/239` |
| 绿 | 同上（修复后源码） | **`checkFailCount 0/239`** · `docH 1231` = 设计帧高 · 溢出 0 · 文案缺失 0 |

- 每阶段两轮独立测量 `run1/run2` 全等（`cmp-measure-runs.py … phase1` 不一致 0；绿轮 37/37 字段全等）。
- 红基线转录：`evidence/red-序号15-checks-设计期望值偏差.txt`（含「探针 bug vs 页面偏差」分诊）。
- 绿基线转录：`evidence/green-序号15-checks-设计期望值.txt`。

## 3. 修掉的 5 类设计偏差（`src/pages/contract/index.vue`）

1. **合同状态卡投影** —— 设计 `effects = drop_shadow(0,6,20,rgba(15,23,42,0.06))`，实现写成近似值 `0 2px 10px rgba(15,23,42,0.05)`。
   （旧台账备注「设计树读不到投影参数」**作废**：`dump-layout.py` 实测 `a05669ed` 就带该 effects。）
2. **状态图标字形行盒** —— 字形 `864f86d5` fs24 w26 缺 26×36 行盒（与同帧返回字形、提示卡/按钮字形口径不一致）→ 加 `.icon-line--24` 包裹，形状仍在 `.ic-contract`。
3. **待签署标文字行高** —— 设计 `lineHeight 1.2`（13.2），实现写 22（= 标高）→ 改 13.2（文字在 22 高标内居中，视觉不变，锁住声明值）。
4. **下载 PDF 按钮描边** —— 设计 `stroke{thickness:1}`，实现写 `0.8px` → 改 `0 0 0 1px`。
5. **提示卡文案行盒（像素对账抓出）** —— 设计文案墨迹 `221..232`（行盒 16），实现 13.2 → 墨迹整行高 2px；改 `line-height: 16px` 后实现墨迹 `221..232` 与设计**逐行相同**。
   （设计树 `lineHeight 1.2` 是陈旧值：同帧 11px 的期限行/记录时间节点都显式 `h16`。）

## 4. 像素对账（设计 PNG vs 实现 430 宽整页截图，±3）

- 整页尺寸：实现截图 `430×1231` = 设计尺寸。
- 内容列（x 36..394）：命中 **35/38**；条列（x 194..356）：命中 **17/17** → 合计 **52 命中 / 3 未命中**。
- 命中处位移：中位 **+1**（min −3 / max +3，0 位移 11 个）→ 无整体平移。
- 视觉文本行（`text-rows.py` 同区间对比，26 行）：**16 行区间完全相同**，其余为 ±1（标题类行起点 +1，一行 −1）—— H5 回退字体的墨迹上下沿差；唯一 2px 差 = 提示卡文案（修前实现 `220..239`），修后为 `222..239`，与设计 `222..238` **起点相同**。
- 3 条未命中（y = 208 / 211 / 217）判读：全在设计导出图**提示卡顶部 207..217 的「雾」带**内。
  实测依据：设计 PNG 该区间整行均匀 `rgb(252..254)`（`scan-col x=300` → `207..217 rgb(252,252,252)`；`scan-row y=210 x30..200` → 均匀 `rgb(253,253,254)`），实现为纯白 `rgb(255,255,255)` —— 差 1~3/255 的导出软染色，**非页面缺陷**（同族于前几页记过的「Figma 阴影/导出渐变台阶」）。
- 文字带对账明细：`evidence/cmp-序号15-设计PNGvs实现截图-结构带.txt`。

## 5. 交互相（三出口，每口两轮）

| 场景 | 证据（phase2） | serve 实收（两轮逐字节相同） |
|---|---|---|
| `?scenario=pdf` | `clicked=CLICKED` · toast 空 · hash 不变 | `GET /api/v1/contracts/c1` → `GET /api/v1/contracts/c1/file` → **`GET /files/CT-2024-0613-008.pdf` 200**（uni H5 真实下载链路） |
| `?scenario=sign` | `confirmed=CONFIRMED` · modalText「确认签署 确认对当前合同发起签署？ 取消确定」· toast「签署申请已提交」· hash 不变 | `POST /api/v1/contracts/c1/sign`（body 空）→ 重载 `GET /api/v1/contracts/c1` |
| `?scenario=back` | `clicked=CLICKED` · hash 不变 | 无额外请求（`navigateBack`，iframe 内无上一页 → hash 不变属预期；栈内返回由 `tests/pages/contract-flow.spec.ts` 断言） |

纯测量轮（无 scenario）每轮只 **1 行**请求（首屏 `GET /contracts/c1`），无多余请求。

## 6. 质量门

- `npm test` **1178/1178 · 72 files 连跑两轮**（15:16:19 / 15:16:50）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE（`dist/build/mp-weixin/pages/contract/index.{js,json,wxml,wxss}` 齐备；wxss 含 `box-shadow:0 6px 20px rgba(15,23,42,.06)`、`box-shadow:0 0 0 1px #cbd5e1`、`line-height:16px`×3、`line-height:13.2px`×2）
- `npm run build:h5` DONE
- `review-artifacts.py`：台账 22 条路由 mp-weixin 三件套齐备且注册（22/22）
- `check-mock-fixtures.py --mock api-15` **FAIL 0**（新补 3 条：`GET /contracts/c1` / `GET /contracts/c1/file` / `POST /contracts/c1/sign`）
- 截图：`logs/screenshots/20260916-序15-合同签署-checks轮-h5-430宽.png`（另存 `.agents/state/evidence/` 同名，430×1231）

## 7. 探针 / 工具侧本轮修正（不计页面账）

- `page.cardRadius`：want 写 `'16px'`，而探针 `norm()` 把 computed `16px` 归一成数值 16 → `chkStrs` 的 String 比较必失败。
- `status.content.inkX` / `rec.body.inkX`：原按「后元素盒子左边 − 前元素右边」断 12，但本帧的 `padding-left` 挂在后元素自身 → 改断墨迹左界（94 / 59）。
- `status.deadline.toCardBottom`：want 写 20，实际是卡 `padding-bottom 20 + 内容列(42) 在 46 高盒里的居中余量 2 = 22`。
- `tip.text.w`：want 写盒子宽 276，而该元素 `padding-left 8` → 盒子 284、内容宽 276 → 改判 computed `width`。
- `check-mock-fixtures.py` **假 FAIL 修复**：`--mock <dir>` 的「变体前缀回退」原写成「只要以 base- 开头就算变体」，导致 `api-15` 这类页面专属 mock 目录误匹配 `api` 的全部检查（一次报 8 条无关 FAIL）→ 收窄为只对 `*-tmp-*` 变体生效，并在零匹配时打印 WARN；`--mock api-15` 与默认分组模式现均 **FAIL 0**，`api-tmp-*` 变体回退仍有效（实测 `api-tmp-probe15` PASS 后已清理）。

## 8. 遗留（不变，等人类拍板）

- 设计帧「电子签章 / 短信验证码签署 / 去签署」与 10-PRD §4.2、17-spec R-41、数据字典 `Contract(sign_channel=OFFLINE)`「合同线下签」冲突 —— 本轮仍按**设计稿优先**实现，冲突留在台账序号 15 备注①。
- toast / 二次确认弹窗文案设计帧无稿 → 占位（`missing-prd`）。
- 签署记录 `tone(success/pending)`、`signer_phone_masked` 脱敏格式、`/contracts/{id}/file` 响应体 schema 未定义 → `missing-prd`（沿用建页轮口径）。
