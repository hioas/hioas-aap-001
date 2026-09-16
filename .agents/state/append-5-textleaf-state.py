# -*- coding: utf-8 -*-
"""回写状态文件 aap-tdd-state.md：STATUS 行（下轮第一件事 = 序号 10）、LEASE 释放、追加 §5.28 与本轮小结。

用法: python .agents/state/append-5-textleaf-state.py [--dry]
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
          '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：'
          '**序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 / 22 / 4-v1 / 5 已归零**'
          '（本 cron 轮 = 序号 5：待判读 8→0 · 已核定 8；8 条全判非偏差，判据 ①同帧显式 height + ②盒算术/PNG 行距，'
          '**新增 3 条行盒断言（237→240）+ 源码变异证明有牙齿**，**无源码改动**，见 §5.28）；'
          '②**下轮第一件事 = 序号 10**（待判读 7 条）：`python .agents/state/textleaf-scan.py 10` → '
          '`python .agents/state/textleaf-audit.py 10` → 按序号 5 / 4-v1 / 10.1 / 22 同法'
          '（判据 ①同帧显式 height ②设计 PNG 盒/带实测 ③盒算术 ④fs×lh，②③冲突以 ② 为准；'
          '真偏差先红后绿改源码，否则登记 `textleaf-accept.json`；**mock 目录 api-10-2**）；'
          '其后按待判读数：12(6) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 4(2) / 20(2) 直到清零'
          '（本轮后：待判读 48 → **40** · 已核定 103 → **111**）。'
          '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。'
          '队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = '''
### 5.28 本轮（21:01 轮 · 序号 5）新增的工具与口径

- **文本叶子声明值全量 dump**：`python .agents/state/leaves-5.py <page-id> [--fs 12]`
  —— 一行一个文本叶子：`id / fontSize / fontFamily / lineHeight / width / height / 文案`；
  判「**同帧同字号的显式 height**」（判据①）的第一入口。本帧一跑就得到
  `fs15→h22 · fs13→h18 ×8 · fs12→h18 · fs11→h16 ×9`（其余为 fit_content）。
- **逐类盒/带并排对账（一页一脚本）**：`python .agents/state/tl-5-evidence.py <design.png> <impl.png> [out.txt]`
  —— 14 个窗口（卡1 白带 / 进度条蓝带 / 成本块 / 标题行两段墨迹 / 元信息行 / 提示卡白带与两行墨迹 /
  顶部胶囊盒与文案 / D1 胶囊盒与文案 / 底栏按钮带与文案）逐一打印「设计 vs 实现」并标 SAME/diff、
  自动算墨迹中心差；`ink_bands()` 先取**该窗口主色**再统计逐行 ink（旧版写死白底 → 在 #F1F5F9 底色的
  按钮窗口里会把整行当墨迹）。
- **整页 430 宽截图**：`bash .agents/state/shot-5.sh [文件名]`（`--window-size=440,1000`，载体页 `?shot=1`
  时 iframe 高 960；ASCII 临时名 → `cp` 中文名）。
- ⚠️ **「盒算术 = 行盒」的用法（本页主交付的判据）**：卡1（padding 20 · fit_content）=
  `20 + 标题行 T + 16 + 进度条 10 + 12 + 元信息行 M + 16 + 成本块 58 + 20 = 196`；
  两侧 PNG 在 x=60 的**进度条蓝带同为 170..179** ⇒ `T = 170 − 108 − 20 − 16 = 26`；
  x=60 的**成本块起点同为 226** ⇒ `M = 226 − 208 = 18`；x=25 的卡1 白带同为 110..301 ⇒ 卡高 196。
  一处等式同时定死两个行盒，比逐类 ink 快且更硬。
- ⚠️ **多行文本块：行距 = 行盒**（判据②优于 ③）：提示卡文案两行墨迹
  **设计 785..795 / 800..810（行距 16）= 实现 785..795 / 801..811（行距 16）** ⇒ 行盒 16；
  按声明的 `fs12 × lh1.2 = 14.4` 落地会得行距 14.4。且卡高 72 = 16 + 40 + 16 由**块高 40 + 盒内居中**
  贡献（2 行 × 16 = 32 居中于 40）——只按行盒顶对齐会让两行墨迹整体上移约 4 行。
- ⚠️ **定高盒内文本「不承重」的判据是墨迹中心，不是墨迹带高**：本页三处（顶部胶囊 h24 · 行胶囊 h22 ·
  底栏按钮 h48）两侧**盒带逐行相同**、文本**墨迹中心差 0.0**（886.5 / 65.5 / 390.5）；
  而「查看历史检测报告」的带高 设计 18 vs 实现 14 是**设计字体与 H5 回退字体的字形墨迹高度差**，
  不是行盒差 —— 判读时看中心与盒带，别被带高带偏。
- ⚠️ **「禁止/锁定型」断言（天生是绿的）必须变异证明**：本轮新增 3 条行盒断言后
  **同时**把三处源码改成声明模型值（`/* MUTATION-TEST */ line-height: 13.2px / 13.2px / 16.8px`）→
  `npm run build:h5` → 一轮实测 **3 条红**（`chip.textLineHeight` / `rowChip.lineHeight` / `history.textLineHeight`）
  → `git checkout -- aap-client/src/pages/detecting/index.vue` → 重建 → **0/240 ×2 绿**。
- ⚠️ **无源码改动的轮次也要给回归门**：载体页两轮（32/32 字段全等）· requests **排序集合**逐字节相同
  （轮询的成对 GET 落盘顺序会抖）· 430 宽整页截图与上一轮 checks 轮截图 **sha256 逐字节相同**
  （`0eecb24e…`）—— 这是「本轮没碰页面」的最强证据。
'''

SUMMARY = '''
- 2026-09-16 21:2x（cron 轮 `aap-tdd-run-20260916-2101`）· **文本叶子维度第 10 页：序号 5（`page-5-2`「检测进行中」）8 条待判读全部收口（判为非偏差 · `textleaf-accept.json` +8 键）· 新增 3 条行盒断言（237→240）并以源码变异证明有牙齿 · 无源码改动 · 两轮 240 条全绿**：
  ①**设计真源（人工指令 C）**：`recapture-page.py page-5-2 b2d065a3-34a0-45e3-8e2e-b9bd9a810126` → `design.json` sha256 `4ed8ad58…` **逐字节相同**；重抓后 `screenshot.json` 只换导出资产 ID，按新 URL 与旧 URL 各下载一次 PNG → sha256 **同为 `b64ef9e8…`（430×934）** ⇒ **无漂移**。
  ②**RED→GREEN**：`textleaf-scan.py 5`（mock `api` · 路由 `/pages/detecting/index?jobId=j1` · leafs 35 · docH 934）→ 红基线 **待判读 class 8**（`evidence/red-序号5-textleaf-待判读.txt`）→ 逐条判读 → 登记后复跑 **待判读 0 · 已核定 8**（`green-序号5-textleaf-待判读0.txt`）。
  ③**8 条判读（全部非偏差）**：判据①**同帧显式 height**（`leaves-5.py` 一次取全）—— fs15 `ea3a0a0d` h22 · fs13 D1..D8 标题 ×8 h18 · fs12 `ff72fdea` h18 · fs11 副行 ×9 h16 ⇒ `card__title` 22 · `meta__done`/`meta__eta` 18 · `chip__text` 16 · `probe-chip__text` 16；判据②**盒算术** —— 卡1 = 20+标题行 **26**+16+进度条 10+12+元信息行 **18**+16+成本块 58+20 = 196，两侧 PNG 进度条蓝带同为 170..179、成本块起点同为 226、卡1 白带同为 110..301 ⇒ `card__percent` 26；判据②**多行行距** —— 提示卡文案两行墨迹 设计 785..795/800..810（行距 16）= 实现 785..795/801..811 ⇒ `tip__text` 16（声明模型 14.4 与 PNG 冲突）；`history-bar__text` 为定高 48 按钮内不承重项（墨迹中心两侧同为 886.5）。
  ④**新增断言 + 变异证明**：载体页补 3 条（`chip.textLineHeight` · `rowChip.lineHeight` · `history.textLineHeight`；这三类此前只断言了字号/字重/颜色）→ 237 → **240 条**；临时把三处源码改成声明模型值（13.2/13.2/16.8）→ `build:h5` → **3 条红** → `git checkout` 还原 → 重建 → 两轮 **0/240**（`evidence/red-序号5-tlchecks-变异测试.txt`）。
  ⑤**回归门**：载体页 `__measure-detecting.html` 两轮 **phase1/phase2 各 240 条 · 0 失败**（`docH 934` = 设计帧高 · `docW 430` · 溢出 0 · 文案缺失 0 · 逐相 **32/32 字段全等，不一致 0**）· serve 实收 10 行/轮 = 5 对轮询 GET（`GET /detection-jobs/j1` + `/results`）**零写请求**，两轮**排序集合逐字节相同** · 430 宽整页截图 `evidence/20260916-序05-检测进行中-textleaf轮-h5-430宽.png` 与 10:42 轮 checks 轮截图 **sha256 逐字节相同**（`0eecb24e…`）· `npm test` **1185/1185 · 72 files 连跑两轮**（21:07:59 / 21:08:56）· `type-check` exit 0 · `review-artifacts` 22/22 · **本轮无 `src/**` 改动**（未跑 build:mp-weixin，沿用上一轮产物）。
  ⑥**证据**：`evidence/cmp-序号5-文本叶子行盒-逐类带.txt`（14 窗口逐类盒/带）· `evidence/review-序号5-textleaf-报告.md` · `evidence/{red,green}-序号5-textleaf-*.txt` · `evidence/textleaf-audit-20260916-2120.txt` · `evidence/review-序号5-tl{,2,final,mut}-run{1,2}.json` · design PNG 留档 `.agents/state/design-shots/page-5-2.png`。
  ⑦**累计**：序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 / 22 / 4-v1 / 5 已归零 ⇒ 待判读 **48 → 40** · 已核定 **103 → 111**。
  ⑧**下轮开工第一件事**：**序号 10**（`page-10-2`「供应商档案编辑 2」· 待判读 7 条 · mock `api-10-2`），同法一页一轮推进。
  ⑨**改名（队列 0）**：按决策 D6 **本轮未再重试** `git mv`（人类已裁定「不重命名」）。
'''


def main():
    s = io.open(P, encoding='utf-8', newline='').read()
    lines = s.split('\n')
    assert lines[0].startswith('STATUS:'), lines[0][:40]
    assert lines[1].startswith('LEASE:'), lines[1][:40]
    lines[0] = STATUS
    lines[1] = 'LEASE: free until -'
    s = '\n'.join(lines)
    s = re.sub(r'\n\s*$', '\n', s)
    s = s + SECTION + SUMMARY
    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    print('STATUS 已更新 · LEASE → free · 追加 §5.28 与本轮小结（共 %d 字节）' % len(s))


main()
