# -*- coding: utf-8 -*-
"""回写 `.agents/state/aap-tdd-state.md`：替换第 1 行 STATUS、追加 §5.24 与「本轮小结」第 2 页（序号 7）一行。

用法: python .agents/state/append-7-textleaf-state.py [--dry]
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
          '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：**序号 1 / 6 / 7 / 12-v1 / 12-v2 / 12-v3 已归零**（本 cron 轮两页：'
          '12-v3 待判读 11→0（9 键）· 7 待判读 10→0（10 键），全部判为非偏差；判法新增两件硬证据 —— '
          '**填充盒高直证行盒**（一票否决条 #FEF2F2 盒高 60 = 12 + 2×18 + 12 ⇒ 12px 行盒 18）与**显式 height 直证**（权重说明叶子 h=36 = 2×18）；'
          '逐类 ink 带与设计相同或 ±1~3（38px 数字的回退字体基线偏移）；两页均**无源码改动**，回归门 259 条 / 201 条 checks 各两轮 0 失败）；'
          '②**下轮第一件事 = 序号 10.1**（待判读 9 条）：`python .agents/state/textleaf-scan.py 10.1` → `python .agents/state/textleaf-audit.py 10.1` → '
          '按 12-v3 / 7 同法（判据 ①显式 height ②设计 PNG 盒/带实测 ③盒算术 ④fs×lh，②③冲突以 ② 为准；真偏差先红后绿改源码，否则登记 `textleaf-accept.json`）；'
          '其后按待判读数：22(9) / 4-v1(8) / 5(8) / 10(7) / 12(6) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 20(2) / 4(2) … 直到 **74** 条清零'
          '（收口后：待判读 74 · 已核定 78）。③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = """
### 5.24 本轮（20:00 轮 · 序号 12-v3 + 序号 7）新增的工具与口径

- **「填充盒高」是行盒最硬的一条证据**：多行文本块若在带底色的容器里（本页一票否决条 #FEF2F2 · padding 12），
  `png-colorat.py <png> v <x> <RRGGBB> <tol> <minLen>` 量出盒高后即得
  `盒高 = padding×2 + n × 行盒`：本页两侧同为 **60 = 12 + 2×18 + 12 ⇒ 12px 行盒 = 18**（声明模型 14.4 会给出 52.8）。
  比 ink 带可靠得多 —— ink 起点随每行首个字形的墨迹上下沿漂 ±2px（本页同块第 1 行 ±1、第 2 行 ±3）。
- ⚠️ **多行块的两行 ink 起点差 ≠ 行距**：同一块里第 1 行与第 2 行的首字不同 → 墨迹上沿不同（实测差 1~3px）。
  判行盒优先用「盒高 / 显式 height / 行距（同字号同内容的相邻行）」三类，**别用跨行 ink 差**。
- ⚠️ **换行点不同会让「带高」也变**：H5 回退字体与设计字体的 CJK/Latin 断行位置不同 → 第 2 行墨迹列数不同
  （本页 结论措辞 75 vs 86 · 权重说明 25 vs 14）→ 这类差异只判「第 1 行是否对齐 + 盒子是否等高等价」，不追第 2 行像素。
- **大字号的「回退字体基线偏移」按比例放大**：fs38 的数字实测偏移 +3（≈8% em），同字号小文本的 ±1 属同一族，
  **不要**因为「差 3px」就改行高（本页 57 = 38×1.5 由设计 PNG 的胶囊边界 176/203 反证）。
- **一页的 checks 轮留证（`evidence/review-序号*-checks-报告.md`）是判 want 的依据来源**：本轮 `score` 的 57
  直接引用该报告 §5（`.score` 行高 57px = 38×1.5），并在 accept 条目里写明「若按 45.6 会怎样」的反证。
- **本轮新增脚本**：`accept-7-textleaf.py` · `append-7-textleaf-state.py`（与 12-v3 的同类脚本同构 · 幂等 + `--reset`）。
"""

SUMMARY = """
- 2026-09-16 20:4x（**同一 cron 轮 `aap-tdd-run-20260916-2000` 的后半段**）· **文本叶子维度第 6 页：序号 7（page-7-2「检测未通过报告」）10 条待判读 class 全部收口（判为非偏差 · `textleaf-accept.json` +10 键）· 无源码改动 · 回归门 201 条 checks ×2 全绿**：
  ①**测量面**：`textleaf-scan.py 7`（带参路由 `#/pages/report-failed/index?reportId=DR-7` + mock `api`，leafs 38 · docH 1111）→ 红基线 **10 条待判读**（`evidence/red-序号7-textleaf-待判读.txt`）→ 逐条判读登记 → 复跑 **待判读 0 · 已核定 10**（`green-序号7-textleaf-待判读0.txt`）。
  ②**两条新的硬证据（本轮主交付的判法）**：**甲 · 填充盒高直证行盒** —— 一票否决条 `c93a930a`（padding 12 · #FEF2F2）盒高在设计与实现**同为 60 = 12 + 2×18 + 12** ⇒ 12px 行盒 = 18（声明模型 14.4 会给出 52.8），比 ink 带可靠（同块第 1 行 ±1 / 第 2 行 ±3）；
  **乙 · 显式 height 直证** —— 权重说明叶子 `18dda7b2` **height=36 = 2 × 18** ⇒ 行盒 18 = 实现值、2 行块高 36 ✓。
  其余：封面顶行（fit_content · 仅两个文本叶子）+ 封面卡 padding 20 ⇒ 行顶 128、设计墨迹 131 ⇒ **行盒 18**；fs13 摘要行同族；`score` 的 57 引用本页 checks 轮留证（`review-序号7-checks-报告.md` §5）并用「同卡结论胶囊 设计 176/203 = 实现 177/204」反证块高。
  ③**结构对账**：`evidence/cmp-序号7-设计PNGvs实现截图-结构带.txt` 内容列 34/38 + 条列 19/19 = **53/57 命中 · 位移中位 +1**（未命中 = 封面卡投影 AA ×3 + 换行差 ×1）；`png-rowclass` 全区段一一对应、最大差 +1；一票否决条盒高两侧同为 60。
  ④**回归门**：载体页 `__measure-report-failed.html` 两轮 **phase1/phase2 各 201 条 checks 0 失败**（docH 1111 · 逐相 30/30 字段全等）· requests 两轮逐字节相同（1 行只读 GET）· 430 宽整页截图 `evidence/20260916-2023-序07-…-h5-430宽.png`。
  ⑤**累计**：序号 1 / 6 / 7 / 12-v1 / 12-v2 / 12-v3 已归零 → 待判读 **84 → 74** · 已核定 **68 → 78**（报告 `evidence/review-序号7-textleaf-报告.md`）。
  ⑥**下轮开工第一件事**：**序号 10.1**（待判读 9 条），同法一页一轮推进。
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
