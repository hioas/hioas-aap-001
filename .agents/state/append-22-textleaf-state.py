# -*- coding: utf-8 -*-
"""回写 `.agents/state/aap-tdd-state.md`：替换第 1 行 STATUS、追加 §5.26 与「本轮小结」（序号 22）。

用法: python .agents/state/append-22-textleaf-state.py [--dry]
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
    '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：**序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 / 22 已归零**'
    '（本 cron 轮 = 序号 22：待判读 9→0 · 已核定 9；**本轮无源码改动**（9 条全判非偏差），'
    '另把 13 条「未渲染叶子」= 设计内联 SVG 图形层判为「实现 data-URI 等价画法（13 ↔ 13 逐元素）」'
    '并**新增 8 条硬断言 + 源码变异测试证明有牙齿**，见 §5.26）；'
    '②**下轮第一件事 = 序号 4-v1**（待判读 8 条）：`python .agents/state/textleaf-scan.py 4-v1` → '
    '`python .agents/state/textleaf-audit.py 4-v1` → 按 10.1/22 同法（判据 ①显式 height ②设计 PNG 盒/带实测 '
    '③盒算术 ④fs×lh，②③冲突以 ② 为准；真偏差先红后绿改源码，否则登记 `textleaf-accept.json`；'
    '**mock 目录 api**、带参路由 `/pages/credential-submit/form?id=c1`）；'
    '其后按待判读数：5(8) / 10(7) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 20(2) / 4(2) / 12(6) … 直到清零'
    '（本轮后：待判读 65 → **56** · 已核定 86 → **95**）。'
    '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = """
### 5.26 本轮（20:30 轮 · 序号 22）新增的工具与口径

- **「非文本叶子（SVG 图形层）」的判法（本轮主交付）**：设计把折线图拆成 13 个 `type=svg` 叶子（**没有 content 之外的
  文本**），审计里永远落在「未渲染叶子」。判法 = **逐元素对应表**：设计 13 层 ↔ 实现 13 个 SVG 元素
  （4 网格线色序 / 1 面积 fill+opacity / 1 折线 color+stroke-width+linecap / 6 点 r4 + 末点 r5 色），
  再把设计 path 的坐标按 **Figma transform（matrix 0.9944 + translate(-185,-130)）** 映射后逐点比 |Δ|。
  工具：`svg-leaves-22.py`（设计侧样式转储）· `chart-svg-22.py`（H5 DOM 里取 data-URI → base64 解码回 SVG）。
  ⚠️ 判别「未渲染」是**文本维度**的产物（`textleaf-audit.py` 按文案配对），**图形层要另立判法**，别当成缺实现。
- **坐标残差要判「谁自相矛盾」**：设计折线的 x 步距是 52/52/52/52/52/50（**非等距**），而设计自己的**横轴标签**是等距
  （56/107/159/210/261/313/364 → 中心 66..374）。实现取等距（与标签一致）⇒ 相对设计点距第 6 点差 1.84px，
  但若照抄设计点距会让数据点与标签错开 2px。**取更自洽的一侧并登记残差**，不要机械照抄坐标。
- **新断言要有牙齿就得变异**：本轮新增的 8 条 checks 天生是绿的 → 用**源码变异**证明（改末条网格线色 + 末点半径/色
  → 3 条红 → `git checkout` 还原 → 绿）。与 §5.16 的「禁止型断言必须变异」同族。
- **want 写成「实测残差表」比「0 + 宽容差」更有牙齿**：`trend.line.vsDesignX` 的 want = 逐点实测残差
  `[0, 0.38, 0.74, 1.11, 1.48, 1.84, 0.26]`（容差 0.35）—— 既记录已知残差，又把任何 >0.35px 的漂移判红（写 0 + 容差 2.0 会静默放过）。
- **卡高盒算术是本页唯一的硬判据**（内容驱动行）：`汇总卡 228 = 20 + 标题行 + (16 + 2×72 + 8) + 20`、
  `趋势卡 222 = 20 + 20 + 12 + 150 + 20`、`模型卡 184 = 20 + 20 + (16 + 4×18 + 3×12) + 20`、
  `成本卡 207 = 20 + 20 + (16 + 3×18 + 3×12) + (12 + 41) + 20`、`明细卡 60 = 16 + 28 + 16`（28 由 chevron 字形盒定）、
  `成本合计行 41 = 10 + 21 + 10` —— 一次把「标题行 = 20」「行内容 = 18」定死，无需对 fs×1.2 动刀。
- **设计声明自相矛盾时以「不参与布局」为准**：`trend__label` 同时写 h=11.3 与 lineHeight=1.31（=13.1）→ 该叶子绝对定位
  （top 122.95），行盒不承重 ⇒ 取 13.1（载体页 want 早已是 13.1 ± 0.3），登记非偏差而不是改 CSS。
- **本轮新增脚本**：`svg-leaves-22.py` · `list-svg-leaves.py` · `chart-svg-22.py` · `chart-cmp-22.py` ·
  `grid-rows-22.py` · `recapture-22.py` · `accept-22-textleaf.py` · `append-22-textleaf-note.py` ·
  `gen-22-trend-mutation-evidence.sh` · `fix-unicode-esc-22.py`（证据文件里被 echo 原样写出的 \\uXXXX 转义）。
- ⚠️ **载体页解析 SVG 时 `<line>` 的属性抽取用正则即可**，但 `chkStrs` 收的是**字符串数组**（本页色值 `#F1F5F9` /
  半径 `'4'` 都按字符串比）；数值数组（y 坐标）要用 `chkList`。
"""

SUMMARY = """
- 2026-09-16 21:0x（cron 轮 `aap-tdd-run-20260916-2030`）· **文本叶子维度第 8 页：序号 22（page-22-2「我的与用量概览 2」）9 条待判读 + 13 条未渲染叶子全部收口 · 本轮无源码改动 · 新增 8 条趋势图硬断言并以源码变异证明有牙齿 · 载体页 267→275 条两轮 0 失败**：
  ①**设计真源（人工指令 C）**：重抓帧「22. 报价端·小程序 ｜ 【工作台与我的】我的与用量概览 2」+ `layer_id 8bc59233-3854-4725-b85b-bfaf4518e934` → `design.json` sha256 `63d7ce0c…` **逐字节相同**（无漂移）；设计 PNG `ce50a955…`（430×1138）相同。
  ②**RED→GREEN**：`textleaf-scan.py 22`（mock api-22 · leafs 344 · docH 1137）→ 红基线 **待判读 class 9**（`evidence/red-序号22-textleaf-待判读.txt`）→ 逐条判读 → 登记后复跑 **待判读 0 · 已核定 9**（`green-序号22-textleaf-待判读0.txt`）。
  ③**9 条判读（全部非偏差，判据 ①显式 height ②PNG 盒/带 + 盒算术 ③fs×lh）**：`card__title` 行盒 20 由**四张卡高算术**定死（228/222/184/207 全自洽，声明模型 16.8 会让四卡各短 3.2px 与 PNG 卡边界冲突）；
  `crow__label/value` + `mrow__name/pct` 行盒 18 由 **PNG 行内容步进 30 = 18 + 12** 与卡高算术定死（墨迹**逐值相同**）；
  `cost-total__label`（合计行 41 = 10+21+10）/ `detail__text`（明细卡 60 = 16+28+16，28 由 chevron 字形盒定）/ `legend__text`（趋势标题行 20 由 fs14 标题定）三处**居中盒内不承重**；
  `trend__label` 设计**自相矛盾**（显式 h=11.3 vs lh1.31×fs10 = 13.1）且绝对定位不参与布局 ⇒ 取 13.1（载体页 want 13.1±0.3 早已绿）。
  ④**13 条「未渲染叶子」= 设计内联 SVG 图形层**：逐元素 13 ↔ 13 等价（4 网格线色序 / 面积 fill+opacity / 折线色+线宽 / 6 点 r4 + 末点 r5 色全同，y 映射后 |Δ| ≤ 0.79px）；
  x 侧设计步距非等距（52…50）而实现取等距（与设计自己的等距横轴标签一致）⇒ 第 6 点 |Δ| ≤ 1.84px，登记为已知残差。
  像素侧：网格线行两侧 n=**306/306**（tol 6 时 425/460/529 两侧同值）、数据点列 66/118/170.5/221/273/325/374.5 vs 66/116.5/169/219.5/270.5/322/373.5（±1~2 = H5 回退渲染）。
  ⑤**新增 8 条 checks（267 → 275）+ 变异证明**：`trend.grid.ys` · `grid.strokes` · `line.pointCount` · `line.vsDesignX`（want = 实测残差表，容差 0.35）· `line.vsDesignY` · `dots.radii` · `dots.fills` · `img.elemCount`；
  临时变异源码（末条网格线色 + 末点半径/色）→ `build:h5` → **3 条红** → `git checkout` 还原 → **0/275 绿**（`evidence/red-序号22-trendchecks-变异测试.txt`）。
  ⑥**回归门**：载体页 **275 条 0 失败 ×2**（`docH 1138` = 设计帧高 · 50 字段全等 · 溢出 0 · 文案缺失 0）· requests 两轮**逐字节相同**（1 行只读 `GET /usage/summary?month=2026-09`）·
  430 宽整页截图与 16:05 轮 checks 轮**逐字节相同** · 像素结构带 39 命中/8 未命中（与 16:05 轮完全一致，未命中项判读同前）· `npm test` **1185/1185 · 72 files 连跑两轮** · `type-check` exit 0 · 未重跑 build（无 src 改动）。
  ⑦**证据**：`evidence/review-序号22-textleaf-报告.md` · `evidence/cmp-序号22-文本叶子-逐类带.txt` · `evidence/cmp-序号22-趋势图区-设计SVGvs实现dataURI.txt` ·
  `evidence/{red,green}-序号22-textleaf-*.txt` · 截图 `logs/screenshots/20260916-2100-序22-用量概览-textleaf轮-h5-430宽.png`（430×1138）。
  ⑧**累计**：序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 / 22 已归零 ⇒ 待判读 **65 → 56** · 已核定 **86 → 95**。
  ⑨**下轮开工第一件事**：**序号 4-v1**（待判读 8 条，mock `api`，带参路由 `/pages/credential-submit/form?id=c1`），同法一页一轮推进。
  ⑩**改名顺延（队列 0 已由决策 D6 挂起）**：本轮开工按 prompt 又试了一次 `git mv aap-client hioas-aap-client` → 仍 `Permission denied`（用户自己的 dev server / IDE 持句柄）→ 记一行顺延、**未 kill 任何用户进程**；按 D6「勿再重试」下轮不再试。
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
