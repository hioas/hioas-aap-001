# -*- coding: utf-8 -*-
"""本文件回写：STATUS/LEASE 两行 + 末尾追加本轮小结（追加式）。"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
          '①新维度「设计文本叶子 ↔ 实现 DOM」全量审计（22 页）后**逐页收口**：'
          '**序号 6 本轮收口 ✅**（待判读 27 class → **0**：修 7 组声明值偏差（导出 PDF 字重 500 · 发现标题 600 · 维度名 500 · '
          '维度分 700 · 状态标签 pill 600 · G 组值 pill fs11/400 · 明细说明行盒 24→16）+ **2 处结构偏差**（分组之间补 1px 分隔线×6 = '
          'design 分隔线A–F；明细说明 frame h=24 被当成行盒 → 整卡 +8px）；18 组经设计 PNG 逐类 ink 带实测登记非偏差 → '
          '`textleaf-accept.json` 19 条；载体页 228→**243 条 checks**，红 16/243（两轮逐字节相同）→ 绿 **0/243**，'
          'docH **5341**（设计 5342）、`cardTops` 与设计逐项相同、像素对账 14 类逐条相同）；'
          '序号 1 复扫后仅剩 1 条（`disclaimer__body` 块高 40 = 2 行 × 20，属审计模型口径差 → 下轮顺手登记 accept）。'
          '②**下轮第一件事 = 序号 12-v1**（当前待判读最多 · 17 条）：`python .agents/state/textleaf-scan.py 12-v1` → '
          '`python .agents/state/textleaf-audit.py 12-v1` → 按序号 6 同法（want = 设计声明值 / 设计 PNG 实测 · 先红后绿 · '
          '两轮一致 + 逐类 ink 带对账 · 非偏差登记 `textleaf-accept.json`）。其后按待判读数从多到少：'
          '12-v2(12) / 12-v3(11) / 7(10) / 10.1(9) / 22(9) / 4-v1(8) / 5(8) / 10(7) / 12(6) / 15(6) … 直到 172 条清零。'
          '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')
LEASE = 'LEASE: free until -'

src = io.open(P, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in src else '\n'
lines = src.split(nl)
assert lines[0].startswith('STATUS:'), lines[0][:40]
assert lines[1].startswith('LEASE:'), lines[1][:40]
lines[0] = STATUS
lines[1] = LEASE

SUMMARY = """

- 2026-09-16 19:3x（cron 轮 `aap-tdd-run-20260916-1915`）· **队列 8/文本叶子维度第 2 页：序号 6「大模型检测报告」27 条待判读 class 全部收口（修 7 组声明值偏差 + 2 处结构偏差 · 18 组登记非偏差）· 载体页 228→243 条 checks · 红 16/243 → 绿 0/243 · docH 5343→5341**：
  ①**设计真源（人工指令 C）**：本轮为**同一画布当前状态**的复核（17:45 轮已重抓 `page-6` 且 sha256 `08ad8ea5…` 逐字节相同、设计 PNG `a505a58c…` 相同）→ want 全部取自 `.calicat/raw/pages/page-6/design.tree.json` + 设计 PNG（430×5342）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-report.html` 由 228 → **243 条设计期望值 checks**（新增 15 条 `tl.*` + 改 3 条旧 want）；
  红基线（`git stash push -- src/pages/report/index.vue src/utils/report-model.ts` + **同一份最终版探针**两轮）**16/243** · docH 5343
  → 绿 **0/243** · docH **5341**；两轮 JSON 逐字节相同、`cmp-measure-runs` 25/25 字段全等；单测红 3 failed → 绿 **1185/1185 · 72 files ×2**。
  ③**修 7 组声明值偏差**：`.action__ghost-text` 字重 500（design `a3023014` Medium）· `.finding__title` 700→**600**（`2ba0333a` SemiBold）·
  `.dim__text` **500**（`177b7f5f` Medium）· `.dim__score` **700**（`0947f700` Bold）· 状态标签 pill **600**（`e247efe0`/`1b3c9a9f`/`66800e15` SemiBold）·
  G 组「值 pill」**fs11/400**（`ef69fd0e` fs11 w142 vs 实现 127 → 模型新增 `statusIsValue` + `item__pill--value`）·
  `.detail-summary` 行盒 **24→16**（design `8485b93b` frame h=24 = padding-top 8 + 行盒 16）。
  ④**修 2 处结构偏差（本轮像素对账抓出，非样式猜测）**：①分组之间缺 design 的 **1px 分隔线**（分隔线A–F，`stroke-rows eef2f7`：设计 1926/2321/2716/3197/3592/3987 六行、实现 0 行）→ 补 `.group__sep`（margin-top 16 + 1px），
  改后六条分隔线落在**与设计相同**的行；②`.detail-summary` 把 frame 的 24 当行盒 → 盒高 32（设计 24）、说明行墨迹低 4px、其下 7 个分组整体低 8px → 改后说明行 **1476..1486 = 设计**、组标题 A **1508..1520 = 设计**、7 个组标题与设计 ±1 内、
  明细卡下缘→风险卡标题 **4423..4437 = 设计**、`cardTops` 与设计逐项相同。
  ⑤**18 组登记「非偏差」**（判据 ①显式 height ②PNG 实测 ③fs×lh，②③冲突以 ② 为准）：多行块高 vs 单行行盒 5 类（`disclaimer__body` 51=3×17 · `evidence-row__value` 32=2×16 · `finding__body` 34=2×17 · `note-box` 48=3×16 · `verdict-box__text` 38=2×19）+
  设计渲染行盒 ≠ fs×1.2 的 8 类（`card__title` 18/20 · `metric__label` 15 · `metric__sub` 14 · `metric__value` 24 · `group__title` 18 · `score__meta-text` 17 · `dim__text`/`dim__score` 16）+
  `radar__label`（设计叶子自身 `lh 1.31` 与 `h 12.43` 矛盾）· `report-page__no`（frame 显式 h=16，17:45 轮已核定）。
  证据 `evidence/cmp-序号6-设计PNGvs实现截图-行盒判读-修后.txt` · `cmp-序号6-明细卡纵向对账-修后.txt` · `cmp-序号6-维度行距对账.txt`；审计复跑 **待判读 class 0 · 已核定 23**。
  ⑥**交互相有牙齿**：`?scenario=actions` 两轮 requests **逐字节相同**（各 4 行 200）：导出 PDF → `GET /reports/DR-1/export 200` + toast + hash 不变；填写报价 → `#/pages/quote-models/index`。
  ⑦**质量门**：`npm test` **1185/1185 · 72 files 连跑两轮**（+3 新用例）· `type-check` exit 0 · `build:mp-weixin` DONE（wxml 含 `group__sep`、js 含 `item__pill--value`/`statusIsValue`、wxss 含 `font-size:11px`/`font-weight:600`/`line-height:16px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api` FAIL 0 · 截图 `logs/screenshots/20260916-1935-序06-检测报告-文本叶子维度收口-h5-430宽.png` · 报告 `evidence/review-序号6-textleaf-报告.md`。
  ⑧**探针自纠 2 处**（写进 §5.21）：`chkR` 的字段名由 **key 末段**决定（`tl.summary.boxH` 会返回整个 rect 对象 → 改 `tl.summary.outer.h`）；
  `cardTops` 是 sink 里的对象属性、不是变量 → 在 checks 区直接引用会 `cardTops is not defined`（第一次跑得到 `phases=['error']`，就地 `rects('.card').map(r=>r.top)` 修正）。
  ⑨**下轮开工第一件事**：**序号 12-v1**（待判读 17 条最多），按本题同法一页一轮推进，直到 172 条清零。

### 5.21 本轮（19:15 轮 · 序号 6）新增的工具与口径

- **逐类 ink 带对账（一页多窗口）**：`bash .agents/state/cmp-class-bands-6.sh`（9 个类各一个窗口，设计 PNG vs 实现 PNG 的 `png-textbands` 并排；`IMPL=<截图>` 可切换实现图）
  + `bash .agents/state/cmp-card4-bands-6.sh`（明细卡内部 11 个窗口，定位「整体平移 vs 局部漂移」）+ `bash .agents/state/cmp-dim-rows-6.sh`（同列多行行距）。
  **判据**：同一 x 窗口内设计/实现 ink 带**起点相同**（长度可差 1 = H5 回退字体墨迹上下沿）⇒ 该类的**渲染行盒**一致，`fs × lineHeight` 的 declared 模型差属审计口径差，登记非偏差。
- **设计声明值速查**：`python .agents/state/decl-leaves.py <pageId> <idPrefix> ...`（一行一个文本叶子：id/type/name/fs/fontFamily/lineHeight/w/h/fills/text —— 判字重与行盒的第一手尺子）。
- **实现侧叶子 rect/computed**：`python .agents/state/leaf-rects.py <tag> <class ...>`（从 `textleaf-<tag>.json` 取，类名用空格表示类链包含）。
- ⚠️ **别把 frame 的 h 当行盒**：design 里「frame（如 明细说明 8485b93b）h=24 + padding-top 8」= 行盒 16。把 frame 高度写成 `line-height` 会让盒高翻倍（32）、单行墨迹居中下沉 4px、并且**其下所有内容整体下移 8px**
  —— 这类偏差探针的几何检查（卡高 ±3 容差）可能放过，**只有逐类 ink 带对账能抓**。
- ⚠️ **「组标题 ink 间距 = 组高 + margin」的自洽算术会骗过自己**：实现原先 `471+16` 与自己的 PNG 实测 437 完全自洽，但设计是 438 —— 差的那 1px 是 design 的 **spacer 16 + 1px 分隔线**；判「实现有没有少条线」要用
  `stroke-rows.py <png> <分隔线颜色> <tol> <mincount> <x0> <x1> <y0> <y1>` 直接在设计 PNG 里找那条线。**跨页同理**：任何「间隔条」在 design 里都可能由 2 个节点组成。
- ⚠️ **`chkR` 的字段名由 key 末段决定**（`.h/.w/.xN/.top/.right/.bottom`）；键名写成 `xxx.boxH` 这类会返回**整个 rect 对象**与数字比较 → 永久失败（本页 1 条假红）。
- ⚠️ **sink 里的对象属性不是变量**：`cardTops: rects('.card')…` 只能在 sink 里用，checks 区引用会 `ReferenceError`（整页 `phases=['error']`）→ 在 checks 区就地 `rects('.card').map(r => r.top)`。
- **本轮新增脚本**：`cmp-class-bands-6.sh` · `cmp-card4-bands-6.sh` · `cmp-dim-rows-6.sh` · `decl-leaves.py` · `leaf-rects.py` ·
  `apply-6-textleaf-probe.py`（载体页改动 · 幂等）· `apply-6-textleaf-src.py`（源码改动 · 锚点唯一校验）· `accept-6-textleaf.py`（accept 登记）· `append-6-tl-note.py`（台账回写）。
"""

src = nl.join(lines) + SUMMARY
io.open(P, 'w', encoding='utf-8', newline='').write(src)
print('已写盘 %s' % P)
print('STATUS 行长度 %d' % len(STATUS))
print('LEASE 行: %s' % LEASE)
