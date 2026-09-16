# 序号 1【账号接入】登录注册 · 16px 残差收口（checks 轮）报告

- 日期/轮次：2026-09-16 18:45 轮 · cron `aap-tdd-run-20260916-1845`
- 页面：台账序号 1 · `page-1-2` 帧「1. 报价端·小程序 ｜【账号接入】登录注册 2」（layer_id `e494f9e7…`）→ `/pages/login/index`
- 载体页：`.agents/state/h5-measure/__measure-login.html`（430 宽 iframe，mock 目录 `api`）
- 设计真源：`.calicat/raw/pages/page-1-2/design.tree.json` + 设计 PNG `.agents/state/design-shots/page-1-2.png`（430×1114）
- 红/绿同一份**最终版探针**（133 条 checks）：先建探针 → 两轮红 → 改源码 → 两轮绿

## 1. 结论（一句话）

上一轮遗留的「实现 1098 vs 设计帧 1114」16px 残差**已收口**：`docScrollHeight = 1114` = 设计帧高，
133 条设计期望值 checks **0 失败**，像素对账 42 命中 / 6 未命中（逐条判读均为非页面缺陷）。

## 2. RED → GREEN

| 步骤 | 探针 | checks | 失败 | docH | 两轮一致 |
|---|---|---|---|---|---|
| RED  | `__measure-login.html`（最终版 133 条） | 133 | **19** | 1098 | 是（phase1 全字段逐字节相同） |
| GREEN | 同上（源码已修） | 133 | **0** | **1114** | 是（phase1 全字段逐字节相同） |

红基线 19 条清单与绿基线转录：`evidence/redgreen-序号1-16px残差-20260916.txt`。

## 3. 修掉的 6 类偏差（先红后绿）

| # | 项 | 修前 → 修后 | 设计依据 |
|---|---|---|---|
| 1 | 首字段前间距 | 16 → **20** | spacer `9113d86d` h20（其余字段之间 = 16：`1e64457c` / `b87793a2`） |
| 2 | 验证码提示行 | 14.4 → **21** | 行 = [图标 `c7f5db13` w16 fs14 remixicon] + spacer 4×18 + [文本 `345fa279` fs12]；行高 = 字形行框 = fs×1.5 |
| 3 | 提示行图标占位盒 | 12×12 → **16×21**，形状 13×13 入 `::before`，色 `$color-primary` → **rgba(148,163,184,1)** | 设计字形墨迹 PNG 实测 x37..49 / y630..642；字形填充 = rgba(148,163,184,1) |
| 4 | 免责卡标题行 + 图标盒 | 20 → **27**（盒 14×14 → **20×27**，形状 15×17，填充 rgba(37,99,235,1)） | 图标层 `477e4b3f` w20 fs18；卡高 107 = 16+27+8+40+16 |
| 5 | 免责正文 | 38 → **40**；`line-height` 1.6 → **14.4px** + 垂直居中 | 叶子 `e5e24331` **显式 height 40**（两行）· fs12 · lh1.2 · textAlignVertical=middle |
| 6 | 分隔行 / 协议行 | 17 → **18** · 20 → **18** | spacer `669abf96` h18；协议行 `07a3c1d3` alignItems=center（去掉勾选框 `margin-top:2px`） |

另：免责卡描边 `border` → **`box-shadow: 0 0 0 1px`**（设计 `stroke{align:center}`）——
`border` 会把卡高撑成 109（设计 107）并把内容宽挤掉 2px（356 → 358）。

## 4. 像素对账（设计 PNG 430×1114 vs 实现截图 430×1114）

- 结构带（`cmp-bands-6`，±3）：**命中 42 / 未命中 6**（修前同脚本下未命中更多）。
- 未命中逐条判读（`cmp-pixel-rows.py` 同列取色）：
  - y656/657 设计 `(254,254,255)` vs 实现 `(255,255,255)` → 主按钮 `drop_shadow(0,8,20,.28)` 的 Figma/Chrome 衰减起点差 1~2/255（阴影类）。
  - y891 设计 `(235,237,240)` vs 实现 `(248,250,252)` → 卡片底边亚像素边界 + 卡投影（设计 268..891，实现 `[268,891)`）。
  - y914/920 设计 `(253,253,253)` vs 实现 `(255,255,255)` → 设计导出图在免责卡上方 908..921 的均匀软染色（同族已在 page-15 登记）。
  - y819（内容列）/ y415（条列）→ 两侧取值完全相同（微信按钮填充 `(240,253,244)` / 输入框底 `(248,250,252)`），属带分割阈值效应。
- 文本行逐行对账（`text-rows.py` x36..394）：两行免责正文墨迹 **设计 965..975 / 980..990 = 实现 966..976 / 980..990（行距 15）**；
  其余全部 ≡ 或 ±1；两处非几何差异已判读（设计 601..602 = 设计字形图标墨迹 vs D5 浅色占位；设计 849..866 = 勾选框选中态 vs 实现默认未选中）。

## 5. 交互相（同一次绿轮，两轮 requests 逐字节相同）

- phase2 空表单 → toast「请输入正确的手机号」· hash 不变 · 无请求
- phase3 缺短信码 → toast「请输入 6 位短信验证码」· 无请求
- phase4 未勾协议 → toast「请先阅读并同意服务协议与隐私政策」· 无请求
- phase5 获取验证码 → 真实 `POST /api/v1/auth/sms/send`（body phone+captcha）→ toast「验证码已发送」· 按钮「59s 后重发」
- phase6 登录 → 真实 `POST /api/v1/auth/sms/login` → 写 token → `#/pages/workbench/index`（落地页 2 个只读 GET）

## 6. 质量门

`npm test` **1182/1182 ×2**（72 files）· `npm run type-check` exit 0 · `npm run build:mp-weixin` DONE
（wxss 含 `width:16px;height:21px` / `height:40px` / `line-height:14.4px`×2 / `0 0 0 1px #eef2f7` / `min-height:18px`）·
`npm run build:h5` DONE · `review-artifacts` **22/22** · 共用消费方回归门 序号 2 工作台两轮 **103 条 0 失败**（docH 1146）。

## 7. 未决项（已登记台账 + 状态文件，下轮按先红后绿做）

1. 本页仍有 **5 处 center 描边用 `border` 实现**（`.field__box`×3 · `.captcha` · `.sms-btn` · `.wechat` · `.agree__box`）
   → 按同族页口径应改 `box-shadow: 0 0 0 1px`；影响：输入框内容左界 设计 48 vs 实现 49、右界 382 vs 381。
2. **3 个输入框图标占位盒 16×16**（设计 `df37d41e` 等声明 w20 fs18 → 应 **20×27**）且填充应为灰 `rgba(148,163,184,1)`
   → 实测设计占位文本左界 **76** vs 实现 **73**（`ink-runs` y407..421）。
3. 协议行文案在设计里是**单个文本叶子**（`4352f1e4`）而实现拆成 3 个节点（两个 `agree__link` 着色）——结构差异，待人类确认是否保留着色（上一轮已登记）。

## 8. 证据索引

- 转录：`evidence/redgreen-序号1-16px残差-20260916.txt`
- 实测：`evidence/review-序号1-red-run{1,2}.json` · `review-序号1-green-run{1,2}.json` · `requests-序号1-green-run{1,2}.txt`
- 像素：`evidence/cmp-序号1-设计PNGvs实现截图-结构带.txt` · 实现截图 `evidence/20260916-1945-序01-登录注册-16px残差对齐-h5-430宽.png`（430×1114）
- 回归门：`evidence/review-序号2-sharedgate-run{1,2}.json`
