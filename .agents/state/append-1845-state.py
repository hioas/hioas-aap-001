# -*- coding: utf-8 -*-
"""回写状态文件：STATUS / LEASE / §4 序号 1 待办 / 本轮小结 + §5.19（保留原 CRLF 行尾）。

用法: python .agents/state/append-1845-state.py
"""
import io
import os
import sys

REPO = 'E:/workspaces/hioas/hioas-aap-001'
PATH = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

with io.open(PATH, encoding='utf-8', newline='') as fh:
    text = fh.read()

STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
    '①新维度「设计文本叶子 ↔ 实现 DOM」全量审计 ✅（22/22 页 · 1131 设计叶子 · 匹配 970 · 待判读 class 172 · 序号 8 四类经 PNG 判定非偏差已登记 textleaf-accept.json）'
    '②序号 1 登录页「字重 10 处 + 行盒 10 处」修正 ✅'
    '③序号 1「16px 残差」收口 ✅（18:45 轮：载体页再扩 19 条 checks → 红 19/133 · docH 1098 → 绿 0/133 · docH 1114 = 设计帧高；像素对账 42 命中 / 6 未命中全部判读为非缺陷）'
    '④**下轮第一件事 = 序号 1 的两个新待办**（5 处 center 描边 `border`→ring · 3 个输入框图标盒 16×16→20×27 且填充改灰 rgba(148,163,184,1)），'
    '其后按 172 条待判读清单逐页推进。队列 0 挂起（D6）；管理端 8 页范围外。'
)

pending = (
    '   - **序号 1 的两个新待办（18:45 轮发现并留证，下轮先红后绿做）**：'
    '(a) 5 处 center 描边仍用 `border` 实现（`.field__box`×3 · `.captcha` · `.sms-btn` · `.wechat` · `.agree__box`）→ 按同族页口径改 `box-shadow: 0 0 0 1px`'
    '（border 占布局：输入框内容左界 设计 48 vs 实现 49、右界 382 vs 381）；'
    '(b) 3 个输入框图标占位盒 16×16 → **20×27**（设计 `df37d41e` 等声明 w20 fs18）+ 填充改灰 rgba(148,163,184,1) —— '
    '实测设计占位文本左界 **76** vs 实现 **73**（`ink-runs y407..421`）。证据见台账序号 1 行 备注 与 `evidence/review-序号1-16px-checks-报告.md` §7。'
)

summary = '''
- 2026-09-16 18:45（cron 轮 `aap-tdd-run-20260916-1845`）· **序号 1「16px 残差」收口（红 19/133 · docH 1098 → 绿 0/133 · docH 1114 = 设计帧高）+ 像素对账 42 命中 / 6 未命中全部判读为非缺陷**：
  ①**设计真源口径（人工指令 C）**：本轮为**同一画布当前状态**的复核，未再整包重抓（上一轮 18:20 已重抓：22 帧 21 SAME + 1 DIFF 且该 DIFF 已登记）→ 页面期望值全部取自 `.calicat/raw/pages/page-1-2/design.tree.json` + 设计 PNG（430×1114）。
  ②**TDD 红→绿（本轮主交付）**：载体页 `__measure-login.html` 再扩 **19 条设计期望值 checks（合计 133 条）**；红基线（**同版最终探针两轮**、源码未改）**19/133** · `docH 1098` → 绿 **0/133** · `docH 1114`（= 设计帧高）；
  两轮独立测量 phase1 **全字段逐字节相同** · 溢出 0 · 文案缺失 0。
  ③**修 6 类偏差**（清单见台账序号 1 行 / `evidence/review-序号1-16px-checks-报告.md` §3）：首字段前间距 16→**20**（设计 spacer 9113d86d h20）·
  提示行 14.4→**21** 且图标占位盒 12×12→**16×21**（设计 c7f5db13 w16 fs14；形状 13×13 按 PNG 墨迹 x37..49/y630..642 画在盒内，色改设计字形填充灰 rgba(148,163,184,1)）·
  免责卡标题行 20→**27**（图标盒 14×14→**20×27**，设计 477e4b3f w20 fs18；填充 rgba(37,99,235,1)）·
  免责正文 38→**40**（设计 e5e24331 **显式 height 40** = 两行；`line-height` 1.6→**14.4px** + 垂直居中 → 墨迹行距 15 与设计逐行相同）·
  免责卡描边 `border`→**`box-shadow: 0 0 0 1px`**（设计 stroke align=center；border 会把卡高撑成 109、内容宽挤掉 2px）·
  分隔行 17→**18**（spacer 669abf96）· 协议行 20→**18**（对齐 center + 去掉勾选框 `margin-top:2px`）。
  ④**像素对账**：`cmp-bands-6`（±3）**命中 42 / 未命中 6**；6 条逐条用 `cmp-pixel-rows.py` 同列取色判读（y656/891 = 投影衰减起点差 1~2/255 · y914/920 = 设计导出图软染色 · y819/y415 = 带分割阈值效应且两侧取值完全相同）→ **非页面缺陷**；
  `text-rows.py` 逐行对账：两行免责正文墨迹 **设计 965..975 / 980..990 = 实现 966..976 / 980..990**，其余全行 ≡ 或 ±1。
  ⑤**交互相有牙齿**：phase2~6 两轮 requests **逐字节相同** —— 空表单 / 缺短信码 / 未勾协议三处校验门 **零请求**（toast 逐字）→ 获取验证码真发 `POST /api/v1/auth/sms/send` → 登录真发 `POST /api/v1/auth/sms/login` → 写 token → `#/pages/workbench/index`（落地页 2 个只读 GET）。
  ⑥**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 `width:16px;height:21px` / `height:40px` / `line-height:14.4px`×2 / `0 0 0 1px #eef2f7` / `min-height:18px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · 共用消费方回归门 序号 2 工作台两轮 **103 条 0 失败**（docH 1146）。
  ⑦**本轮发现并留证（下轮第一件事）**：本页仍有 **5 处 center 描边用 `border` 实现** + **3 个输入框图标占位盒 16×16**（应 20×27、填充灰）——实测设计占位文本左界 **76** vs 实现 **73**；另设计帧协议行勾选框为选中态而实现默认未选中（按 PRD 校验门保留，属状态差非几何差）。
  ⑧**探针/工具**：`show-fields.py`（打印某相指定字段）· `show-fails3.py`（兼容 checkFails 为**字符串数组**的老探针）· `cmp-pixel-rows.py`（两 PNG 同列取色 → 判「未命中是页面缺陷还是阴影/AA」）· `gen-1-16px-evidence.py`（红/绿/交互/像素四段转录合成）。

### 5.19 本轮（18:45 轮 · 序号 1）新增的工具与口径

- **两 PNG 同列取色**：`python .agents/state/cmp-pixel-rows.py <design.png> <impl.png> <y1,y2,...> [x]`
  —— 判「结构带未命中」性质的第一工具（本页 6 条未命中全部靠它定为「投影衰减 / 导出图软染色 / 带分割阈值」）。
- **打印某相字段 / 失败清单（老探针兼容）**：`python .agents/state/show-fields.py <run.json> <phase> [key...]` ·
  `python .agents/state/show-fails3.py <run.json>`（`show-phases.py` 只认 checkFails 为**对象数组**；本页这类老探针是**字符串数组**，会 AttributeError）。
- **设计期望值的「盒 + 形状」两层口径（本轮两例）**：图标一律「**盒 = 设计声明宽 × 字号×1.5**，形状（含颜色）入 `::before`」——
  提示行图标盒 16×21 / 形状 13×13 灰 · 免责卡图标盒 20×27 / 形状 15×17 蓝；**颜色必须读 `::before` 的 backgroundColor**（元素自身是空盒，探针读元素会得到 `rgb(0,0,0)` 假红）。
- ⚠️ **「文本行盒 = 设计显式 height」时，行盒本身与块内居中要一起做**：免责正文设计 `height 40` + `textAlignVertical=middle`
  → 实现 = `height:40px` + `line-height:14.4px` + `display:flex; align-items:center`；只把 height 写到 40 会让墨迹停在盒顶（PNG 会量出两行位置整体上移约 6px）。
- ⚠️ **`text-rows.py` 的「深色行带」会把设计里的矢量图标算进去、把 CSS 浅色占位形状排除**：同族比对时这类「设计有、实现无」的 1~2 行带属 D5 占位口径差异，**不要**记成页面缺陷（本页 601..602 即此）。
- ⚠️ **设计帧的静态状态 ≠ 实现默认状态**：page-1-2 协议行勾选框在设计里是**选中态**（蓝底 + tick），实现默认未选中（PRD 校验门要求用户显式勾选）→ 该行墨迹带（设计 849..866 / 实现 853..863）差异属**状态差**，判读写清楚，不要按几何缺陷处理。
- **本轮新增脚本**：`show-fields.py` · `show-fails3.py` · `cmp-pixel-rows.py` · `gen-1-16px-evidence.py` · `append-1-16px-note.py`；报告 `evidence/review-序号1-16px-checks-报告.md`。
'''

# 1) STATUS 行
lines = text.split('\r\n')
hit = 0
for i, ln in enumerate(lines):
    if ln.startswith('STATUS: RUNNING') or ln.startswith('STATUS: PAUSED') or ln.startswith('STATUS: DONE'):
        lines[i] = STATUS
        hit += 1
if hit != 1:
    sys.exit('STATUS 锚点命中 %d 次（要求 1）' % hit)

# 2) LEASE 行
hit = 0
for i, ln in enumerate(lines):
    if ln.startswith('LEASE:'):
        lines[i] = 'LEASE: free until -'
        hit += 1
if hit != 1:
    sys.exit('LEASE 锚点命中 %d 次（要求 1）' % hit)

text = '\r\n'.join(lines)

# 3) §4 队列 1 追加两个待办
anchor = '台账行写「复核通过 <时间> + 命令」。'
if text.count(anchor) != 1:
    sys.exit('§4 队列 1 锚点命中 %d 次（要求 1）' % text.count(anchor))
text = text.replace(anchor, anchor + '\r\n' + pending)

# 4) 追加本轮小结 + §5.19
text = text.rstrip('\r\n') + '\r\n' + summary.replace('\n', '\r\n')

with io.open(PATH, 'w', encoding='utf-8', newline='') as fh:
    fh.write(text)
print('state written · bytes=%d' % len(text.encode('utf-8')))
