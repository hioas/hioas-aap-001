# 序号 1【账号接入】登录注册 — center 描边 → ring + 输入框图标字形盒 + 设计 effects（2026-09-16 19:0x 轮）

设计真源：`.calicat/raw/pages/page-1-2/design.tree.json`（Calicat 文件 `2095515676955668480` / 画布 `2095515676976640000` 当前状态）
+ 设计 PNG `430×1114`（`.agents/state/design-shots/page-1-2.png`，sha256 与留证一致）。
载体页：`.agents/state/h5-measure/__measure-login.html`（430 宽 iframe，本轮 **165 条 checks** + phase5 勾选态 5 条）。
命令：`bash .agents/state/review-measure.sh <tag> __measure-login.html .agents/state/h5-measure/api <port>`。

## 1. 本轮交付（TDD 红 → 绿）

| 阶段 | 检查数 | 失败 | docH | 证据 |
|---|---|---|---|---|
| RED ①（源码未改，两轮） | 163 | **34**（两轮逐条相同） | 1114 | `evidence/review-序号1-ringred-run{1,2}.json` |
| RED ②（补 effects checks，源码未改，两轮） | 165 | **2**（两轮逐条相同） | 1114 | `evidence/review-序号1-effred-run{1,2}.json` |
| GREEN（实现后两轮） | 165 | **0 / 0** | **1114 = 设计帧高** | `evidence/review-序号1-final-run{1,2}.json` |
| phase5 勾选态（两轮） | 5 | 0 / 0 | — | 同上 `phase5` |

两轮独立测量 `phase1` **42/42 字段全等、不一致 0**；溢出 0 · 文案缺失 0 · 两轮 `requests-序号1-final-run{1,2}.txt` 各 6 行（与修前同集合）。
转录：`evidence/redgreen-序号1-ring图标盒投影-20260916.txt`。

## 2. 修掉的 3 类偏差（want 一律取设计声明值 / 设计 PNG 实测）

① **5 处 Figma `stroke{align:center,thickness:1}` 用 `border` 实现 → 改 `box-shadow: 0 0 0 1px`**
center 描边不占布局，而 `border` 会把内容盒挤掉 2px：

| 元素 | 设计声明 | 实测偏差（修前 → 修后） |
|---|---|---|
| `.field__box`（3 个输入框 0969fe4e / 4b7f22fc / 1b3579fd） | rgba(226,232,240,1) | 内容左界 **49 → 48**（设计 48）· 右界 381 → **382** |
| `.captcha`（1bb97e22） | rgba(224,231,255,1) | 块左界 **269 → 270**（设计 270） |
| `.sms-btn`（b4fa89d5） | rgba(191,219,254,1) | 同上 |
| `.wechat`（6cf8d63a） | rgba(187,247,208,1) | 同上 |
| `.agree__box`（927a3b46，选中态 fill-only 无描边） | 选中 rgba(37,99,235,1) 无描边 | 未选中态用 ring 1px #E2E8F0；选中态 `box-shadow:none` + `background:#2563EB`（phase5 实测 `{bg: rgb(37,99,235), shadow: none, borderWidth: 0px}`） |

② **3 个输入框图标字形盒 16×16 → 20×27，填充改灰**（设计 `df37d41e` / `930dc950` / `c59ce992`：`w=20 fs=18 remixicon fill=rgba(148,163,184,1)`）
盒口径 = 声明宽 × 字号×1.5；形状按设计 PNG 墨迹画在 `::before`（手机 11×16 · 盾 15×17 · 锁 15×17，2px 描边灰）。
连带修掉两处行内几何：
- 占位文本左界 **73 → 76**（设计 76 = 内容左界 48 + 图标盒 20 + spacer 8；修前 49+16+8）
- 手机号输入框左界 **123 → 119**（设计 165e103e / 515ac9c7 = 竖分隔两侧 spacer 8/8；修前 `$gap-md=12`）
- `+86` 固定 `width:25px`（设计 `c825d0d3` 声明宽 25；修前随回退字体宽 24 → 竖分隔/输入框左界漂移）

③ **设计 effects 整体缺失 → 补 2 处投影**（像素对账抓出，非样式猜测）
- 表单卡片 `cab5940c` `drop_shadow(0,8,24,rgba(15,23,42,0.08))`：卡底下方 y891..911 设计 235→248 渐变，修前实现恒为页面底色 `248,250,252`
- 主按钮 `7e26d478` `drop_shadow(0,8,20,rgba(37,99,235,0.28))`：按钮下方 y721..740 设计 `(207,221,250)→(247,249,254)`，修前实现恒 `255,255,255`

## 3. 像素对账（设计 PNG vs 实现截图，均 430×1114）

- `cmp-bands-6`（±3）内容列 **命中 27 / 未命中 2**（修前 25 / 4）· 条列 **19 / 0** → 未命中仅剩 y914 / y920，逐条同列取色为设计导出图软染色（设计 253 vs 实现 255，2/255）→ **非页面缺陷**
- 投影列取色（x=200）：主按钮下 y721/725/735 **逐值相同**（730/740 ±1）；卡底 y891/895/900 **±1**、y905 相同
- 行内墨迹段（同一 y 带 `ink-runs`）：手机号行 设计 `52..62 / 76..99 / 109..110 / 119..202` = 实现 `53..63 / 76..99 / 109..110 / 119..202`（图标 ±1 = 20 宽盒内居中 11 宽字形的亚像素取整）；验证码行与短信行 文本 `76..159` / `76..187` **逐值相同**

## 4. 质量门

- `npm test` **1182/1182 · 72 files 连跑两轮**（19:08:34 / 19:09:23）
- `npm run type-check` exit 0 · `build:h5` DONE
- `build:mp-weixin` DONE（`pages/login/{index.js,index.json,index.wxml,index.wxss}`；wxss 含 `box-shadow:0 0 0 1px #e2e8f0 ×2` / `#e0e7ff` / `#bfdbfe` / `#bbf7d0`、`border:2px solid #94a3b8`（`::before` 形状）、`width:20px;height:27px ×2`、`width:25px`、`box-shadow:0 8px 24px rgba(15,23,42,.08)`、`box-shadow:0 8px 20px rgba(37,99,235,.28)`）
- `review-artifacts` **22/22** 路由 mp-weixin 三件套齐备且已注册 · `check-mock-fixtures --mock api` **FAIL 0**（含反向体检）
- 截图：`evidence/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png`（430×1114 = 设计帧尺寸）

## 5. 未改（保持原样，有依据）

- 协议行勾选框**默认未选中**：设计帧画的是选中态（蓝底 + tick），PRD 校验门（R-01/AC-01）要求用户显式勾选 → 属**状态差**，仅几何按设计（18×18 r6，ring 不占布局）。
- 协议行文案在设计里是**单个文本叶子**（`4352f1e4`），实现拆成 3 个节点以给《服务协议》《隐私政策》着色 → 结构差异已在台账登记待人类确认（沿用上轮口径）。
- 图标仍为 CSS 绘制占位（决策 D5；设计为 remixicon 矢量字形，PRD08 禁 emoji）。

## 6. 本轮新增工具

- `.agents/state/dump-1-decl.py`（逐页打印设计树声明值：w/h/fs/字体/行高/填充/描边/effects/文本）
- `.agents/state/ink-rowwidth.py`（区域内逐行墨迹 x 段 → 判字形是描边还是填充、取墨迹包围盒）
- `.agents/state/apply-1-ring-icon.py` · `fix-1-probe-left.py` · `apply-1-ring-icon-src.py` · `apply-1-effects.py` · `gen-1-ring-evidence.sh`

⚠️ 本轮踩到的坑（供后续轮次）：**`apply-*.py` 只做「锚点命中 1 次」校验，不检重复插入** ——
先跑 `--probe-only` 再整跑，会把同一段 checks 插两次（本轮实测 checks 165 → 167、同名 check 两条）。
凡分两段跑的脚本，第二次必须确认输出里 `grep -c "chk('<key>'"` 为 1（或把脚本做成幂等）。
