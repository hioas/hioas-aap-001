# -*- coding: utf-8 -*-
"""回写 `.agents/state/aap-tdd-state.md`：替换第 1 行 STATUS、追加 §5.25 与「本轮小结」（序号 10.1 一行）。

用法: python .agents/state/append-10.1-textleaf-state.py [--dry]
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
    '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：**序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 已归零**'
    '（本 cron 轮 = 序号 10.1：待判读 9→0（+9 键 · 已核定 8），其中 **2 处真偏差先红后绿改源码**；'
    '判法新增「**多行文本模型**」——设计里 fs12 文本的**块高 = n × 18**（自然 CJK 行框/显式声明），'
    '而**字形行按 lh1.2 = 14.4 排布并在块内垂直居中**（n=1 与 n=2 两个实测同解），见 §5.25）；'
    '②**下轮第一件事 = 序号 22**（待判读 9 条，本页还有 13 条「未渲染叶子」= 设计里的内联 SVG 折线/网格，'
    '需判「实现用什么画、是否等价」）：`python .agents/state/textleaf-scan.py 22` → `python .agents/state/textleaf-audit.py 22` → '
    '按 10.1 同法（判据 ①显式 height ②设计 PNG 盒/带实测 ③盒算术 ④fs×lh，②③冲突以 ② 为准；'
    '真偏差先红后绿改源码，否则登记 `textleaf-accept.json`）；'
    '其后按待判读数：4-v1(8) / 5(8) / 10(7) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 20(2) / 4(2) / 12(6) … 直到清零'
    '（本轮后：待判读 74 → **65** · 已核定 78 → **86**）。'
    '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = """
### 5.25 本轮（20:15 轮 · 序号 10.1）新增的工具与口径

- **「多行文本模型」（本轮主交付的判法，解释了两类看似矛盾的实测）**：设计里 fs12 文本的
  **块高 = n × 18**（自然 CJK 行框；或设计直接声明的显式 height，如简介 40），
  而**字形行按 lh1.2 = 14.4 排布并在块内垂直居中** —— 两个 n 的实测同解：
  `n=1`（主体锁定提示，块 18）墨迹 636..648 = 实现 636..648（行盒 18 顶对齐，两模型差 <1px）；
  `n=2`（简介块 40 / 闸门块 36）设计墨迹 917..929 / 932..943 与 202..214 / 217..228，只有「14.4 + 块内居中」能同时对上两行。
  ⇒ **单行文本不需要动**（两模型同解、差 <1px），**只有多行块才要**：块高保持不变、行高写 14.4px、盒内居中。
  与 序号 1 `.disclaimer__body` 的既有口径一致。
- **判「块高」而不是「行盒」**：`chkR(..., '<块高>')` + `line-height: 14.4px` + `align-items: center` 三件套，
  这样 `docScrollHeight` 与设计帧高不变（本页 1414 前后不变），只把第 2 行墨迹搬回设计位置。
- **填充盒高法在多行块上要先排除圆角**：`png-colorat.py <png> v <x> <RRGGBB>` 若 x 落在圆角半径内
  （本页闸门盒 x=36..394、r=12，取 x=40）会把 60 量成 54（= 60 − 2×3.1）—— 要看 `60` 就得取盒中心列（x=215）。
  两列一起量还能反证半径：54 = 60 − 2×(12 − √(12²−8²))。
- **「图标盒子不承重」也要用墨迹中心反证**：闸门图标行框 27（fs18 × 1.5）在设计与实现的**墨迹中心同为 211.5**
  ⇒ 设计那一侧的图标盒也是 27（若为 36，中心会落在 216）—— 这样才敢断言 36 是**文本块**贡献的。
- **`display:flex` 会把 uni-app 的 `uni-text > span` 变成块级 flex item**：叶子 rect 会从「墨迹宽」变成「容器宽」
  （本页简介 x 47..372 → 47..383），band 对账窗口随之变宽，但**墨迹带与换行不变**——看到 rect 变宽不要当成回归。
- **本轮新增脚本**：`recapture-10.1.py`（单帧重抓 + design/design.tree/screenshot 三文件 sha256 比对）·
  `accept-10.1-textleaf.py` · `append-10.1-textleaf-note.py` · `append-10.1-textleaf-state.py` · `layer-id-of.py`。
"""

SUMMARY = """
- 2026-09-16 20:1x（cron 轮 `aap-tdd-run-20260916-2015`）· **文本叶子维度第 7 页：序号 10.1（page-10-1-2「供应商档案」）9 条待判读全部收口 —— 2 处真偏差先红后绿（简介/闸门行盒 20/18→14.4 + 块内居中）· 8 类登记非偏差 · 载体页 275→277 条 checks 两轮 0 失败**：
  ①**设计真源（人工指令 C）**：重抓帧「供应商档案 2」+ `layer_id 54ad46b0-1f7c-498a-ac1a-70dff723b35d` → `design.json` sha256 `e7983634…` **逐字节相同**（无漂移）；设计 PNG 430×1414。
  ②**RED→GREEN 两段（同一份最终版探针两轮）**：红① `review-序号10.1-tlred-run{1,2}` **2/275**（`c3.introText.lh` got 20 want 14.4px · `c3.introText.align` got normal want center）→ 改源码 → 绿① `tlg` **0/275**；
  红② `tlred2` **2/277**（`c1.gateText.lh` got 18 want 14.4px · `c1.gateText.align`）→ 改源码 → 绿② `tlg2` **0/277**；`docScrollHeight` 全程 **1414 = 设计帧高**；两轮独立测量 **43/43 字段全等**；requests 两轮集合逐字节相同（24 行 = 1 写 + 11 对只读 GET）。
  ③**两处真偏差（设计 PNG 实测驱动，非样式猜测）**：`.intro-box__text` —— design `234362e0` **显式 height=40 是块高（2 行）**，行盒按设计渲染 = fs12×lh1.2 = **14.4**（设计墨迹 917..929 / 932..943，行距 15；修前 915..927 / 936..946 行距 21）；
  `.gate__text` —— 闸门提示 `87815f1d` padding12 的 **#FFFBEB 盒两侧同为 60 = 12 + 36 + 12 ⇒ 块高 36**（图标行框 27 由「墨迹中心两侧同为 211.5」反证不承重），行盒同为 14.4（设计 202..214 / 217..228；修前 220..230 低 3px）。改后两处墨迹 **±1**。
  ④**8 类非偏差登记**（`textleaf-accept.json` +9 键，累计 73）：定高胶囊/角标/按钮内单行文本（h24/h24/h22/h20/h44，墨迹 ±1 或逐值相同）×6 + 单行 `note__text`（636..648 两侧逐值相同）+ 定高标题行的 `head-line__percent`（+1、卡高 158 = 设计）。
  ⑤**质量门**：`npm test` **1185/1185 · 72 files 连跑两轮**（20:24:18 / 20:24:59）· `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 `line-height:14.4px`×2 / `height:36px` / `height:40px` / `align-items:center`）· `build:h5` DONE · `review-artifacts` 22/22 · 台账 22 行 × 11 字段体检 bad 0。
  ⑥**累计**：序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 已归零 ⇒ 待判读 **74 → 65** · 已核定 **78 → 86**；报告 `evidence/review-序号10.1-textleaf-报告.md`。
  ⑦**下轮开工第一件事**：**序号 22**（待判读 9 + 未渲染叶子 13 = 设计内联 SVG 折线/网格，需判「实现等效画法」），同法一页一轮推进。
"""

raw = io.open(P, 'r', encoding='utf-8', newline='').read()
lines = raw.splitlines(True)
crlf = raw.count('\r\n')
lf_only = raw.count('\n') - crlf
term = '\r\n' if crlf >= lf_only else '\n'
print('行尾: CRLF %d · LF-only %d → %r' % (crlf, lf_only, term))

lines[0] = STATUS + term
for block in (SECTION, SUMMARY):
    for ln in block.lstrip('\n').split('\n'):
        lines.append((ln + term) if ln else term)
print('新第 1 行: %s' % lines[0][:110])
print('总行数 %d → %d' % (len(raw.splitlines()), len(lines)))
if '--dry' not in sys.argv:
    io.open(P, 'w', encoding='utf-8', newline='').write(''.join(lines))
    print('已写盘 %s' % P)
