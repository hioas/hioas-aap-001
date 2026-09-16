# -*- coding: utf-8 -*-
"""回写 `.agents/state/aap-tdd-state.md`：替换第 1 行 STATUS、追加 §5.27 与「本轮小结」（序号 4-v1）。

用法: python .agents/state/append-4v1-textleaf-state.py [--dry]
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
    '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：**序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 / 22 / 4-v1 已归零**'
    '（本 cron 轮 = 序号 4-v1：待判读 8→0 · 已核定 8；8 条全判非偏差，**新增 1 条 `star.lineHeight` 断言 + 源码变异证明有牙齿**，'
    '**无源码改动**；并更正一条口径：本页无参路由，见 §5.27）；'
    '②**下轮第一件事 = 序号 5**（待判读 8 条）：`python .agents/state/textleaf-scan.py 5` → '
    '`python .agents/state/textleaf-audit.py 5` → 按 4-v1/10.1/22 同法（判据 ①同帧显式 height ②设计 PNG 盒/带实测 '
    '③盒算术 ④fs×lh，②③冲突以 ② 为准；真偏差先红后绿改源码，否则登记 `textleaf-accept.json`；'
    '**mock 目录 api**、带参路由 `/pages/detecting/index?jobId=j1`）；'
    '其后按待判读数：10(7) / 12(6) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 4(2) / 20(2) 直到清零'
    '（本轮后：待判读 56 → **48** · 已核定 95 → **103**）。'
    '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = """
### 5.27 本轮（20:46 轮 · 序号 4-v1）新增的工具与口径

- **单帧重抓通用脚本**：`python .agents/state/recapture-page.py <page-id> <layer-id> [out_dir]`
  —— 重抓一帧并与 `.calicat/raw/pages/<id>/` 的留证逐文件 sha256 比对（取代逐页复制的 `recapture-NN.py`；
  前提仍是 Calicat 编辑器开在浏览器里 `cmd /c start "" https://www.calicat.cn/design/2095515676955668480`）。
- ⚠️ **重抓后 `screenshot.json` 的 sha 必然变**：它只存**导出资产的 URL/ID**（本轮 `2099902651224866816` → `2100205357995782144`），
  不是设计内容。判「有没有像素漂移」要**按新 URL 下载 PNG 再与留证 PNG 比 sha256**（本轮两侧同为 `f77955ca…` = 无漂移），
  **结构漂移**看 `design.json` 的 sha（本轮 `bd249858…` 逐字节相同）。
- ⚠️ **卡片内还有输入框的页面不能用 `png-rowclass --x0 16 --x1 414` 读卡片边界**（`#F8FAFC` 的输入框行会被判成 GAP，一张卡被切成好几段）；
  正解 = `scan-col.py <png> <x> <y0> <y1>` 逐段读颜色（本轮 x=25 一次读出四张卡的顶/底与卡下阴影带）。
  注意**圆角**：r16 时沿距卡左缘 5px 的列，白带起点比卡顶低约 5 行（`r − √(r²−(r−5)²)`），别把 5px 当漂移。
- **「整页高度闭合」是最省事的盒算术（本轮主交付的判法）**：把设计树的 padding / gap / 显式 height 抄成一行等式
  （page-24：`1137 = 74 + 16 + 388 + 16 + 98 + 16 + 274 + 16 + 118 + 16 + 48 + 16 + 25 + 16`），任何一处行盒取错值都会让等式差 1px 以上。
  本轮凭它一次定死 5 个行盒（标题行 20 · 标签行 18 · chip 行盒 18 · 备注框内 20 · 提交提示 25 = 字形盒 21 + 4），
  比逐类做墨迹带快得多；**逐类墨迹带用于交叉验证**（±1 行即等效）。
- **判据①的扩展用法：同帧同字号的显式 height 可以直接当判据**。page-24 的文本叶子除 4 个外全是 `fit_content + lh1.2`，
  但 fs11 有两处显式 `h=16`（`d09f9feb`/`919871df`）、fs13 有一处 `h=20`（`ee12aef8`）、fs12 有一处 `h=18`（`7549512f`）
  ⇒ 同帧同字号的行盒 = 16/20/18，直接印证其余 `fit_content` 叶子该取同值（不必逐类量 PNG）。
  取证命令：`python .agents/state/decl-leaves.py page-24 <id 前缀…>`（一行一个文本叶子）。
- ⚠️ **`tl-bands.py` 的窗口坐标来自 dump（空态）**：若实现截图是**已上传态**，只有上半页（卡片 1/2 区）的窗口仍对齐，
  页面底部的类（如 `footnote__text`）要另用 `png-textbands.py <png> <x0> <y0> <x1> <y1>` 直接给窗口量，
  或换同状态截图。本轮 footnote 用「设计 1101..1111 vs 实现 1102..1112」直接判定。
- **变异测试的固定流程（第二次用，可照抄）**：改 src（加 `MUTATION-TEST` 注释）→ `npm run build:h5` →
  `review-measure.sh <tag>mut …` 跑一轮看红 → `git checkout -- <文件>` → 再 `npm run build:h5` → 跑两轮绿。
  `build:h5` 会清空 `dist/build/h5`，但载体页由 `review-measure.sh` 自己重新拷贝，无需手工补。
- ⚠️ **本轮口径更正**：序号 4-v1 的载体页 iframe 与台账「目标路由」都是 `/pages/credential-submit/form`（**无参数**；
  `src/pages/credential-submit/form.vue` 不读任何参数），前轮 §4/STATUS 里写的「带参路由 `?id=c1`」作废。
  凡「带参路由」清单新增条目，先看页面源码有没有读参（`grep -n "onLoad\\|query"`）再写。
- **本轮新增脚本**：`recapture-page.py`（通用单帧重抓 + 三文件 sha 比对）· `accept-4v1-textleaf.py`（accept 登记 · 幂等 + `--reset`）·
  `append-4v1-textleaf-note.py`（台账回写 · csv.DictWriter 重写 + 内存复解析体检）· `append-4v1-textleaf-state.py`（本文件回写）。
"""

SUMMARY = """
- 2026-09-16 21:1x（cron 轮 `aap-tdd-run-20260916-2046`）· **文本叶子维度第 9 页：序号 4-v1（`page-24`「接入凭证-表单」）8 条待判读全部收口（判为非偏差 · `textleaf-accept.json` +8 键）· 新增 1 条 `star.lineHeight` 断言并以源码变异证明有牙齿 · 无源码改动 · 250 条 checks 两轮全绿**：
  ①**设计真源（人工指令 C）**：`recapture-page.py page-24 cb1de468-0658-4ccb-a1c3-46c2f48f6314` → `design.json` sha256 `bd249858…` **逐字节相同**；
  重抓后 `screenshot.json` 必变（换的是导出资产 ID），按新 URL 下载 PNG 与留证 PNG 比 sha256 **同为 `f77955ca…`（430×1137）** ⇒ **无漂移**。
  ②**RED→GREEN**：`textleaf-scan.py 4-v1`（mock `api` · 路由 `/pages/credential-submit/form` · leafs 26 · docH 1071 空态）→ 红基线 **待判读 class 8**
  （`evidence/red-序号4v1-textleaf-待判读.txt`）→ 逐条判读（判据 ①同帧显式 height ②design PNG 盒/盒算术 ③逐类墨迹）→ 全部登记 → 复跑 **待判读 0 · 已核定 8**（`green-序号4v1-textleaf-待判读0.txt`）。
  ③**8 条判读（全部非偏差）**：`card__title` 行盒 20 · `field__label`/`field__star` 18 · `type-chip__text` 18 · `card__tip` 16 · `uni-input-placeholder`/`uni-textarea-placeholder` 20 · `footnote__text` 16 ——
  硬证据 = **整页闭合算术**（设计 PNG 四张卡 388/98/274/118 与 `1137 = 74 + 16 + 388 + 16 + 98 + 16 + 274 + 16 + 118 + 16 + 48 + 16 + 25 + 16` 逐项自洽；
  按声明的 fs×1.2 落地会让四卡各短 3.2~5.6px、整页 ≈1124）+ **同帧显式 height**（fs11 两处 h16 · fs13 一处 h20 · fs12 一处 h18）+ **逐类墨迹 ±1 行**
  （`evidence/cmp-序号4v1-文本叶子-逐类带.txt`：label/star/chip 三处**起点逐值相同**）。
  ④**新增断言 + 变异证明**：载体页补 `star.lineHeight`（本页此前只断言了 `.field__label`，星号这条无断言）→ phase2 **249→250 条**；
  临时把 `.field__star` 的 line-height 改成 14.4（= 声明模型的落地形态）→ `build:h5` → **FAIL star.lineHeight: got 14.4 want 18**（1 条红）→ `git checkout` 还原 → 两轮 **250 条 0 失败**（`evidence/red-序号4v1-starcheck-变异测试.txt`）。
  ⑤**回归门**：载体页 `__measure-form.html` 两轮 **phase1 6 条 / phase2 250 条 · 0 失败**（`docH 1137` = 设计帧高 · `docW 430` · 溢出 0 · 文案缺失 0 ·
  两轮独立测量 **phase1 32/32 · phase2 33/33 字段全等，不一致 0**）· serve 实收 12 行**排序集合逐字节相同**（1 条真实 `POST /api/v1/provider/qualifications` + 落地页 detecting 的 5 对轮询 GET）。
  ⑥**质量门**：`npm test` **1185/1185 · 72 files 连跑两轮**（20:51:40 / 20:53:03）· `type-check` exit 0 · `build:mp-weixin` DONE（`pages/credential-submit/form.{js,json,wxml,wxss}` 齐备）·
  `review-artifacts` 22/22 · `check-mock-fixtures --mock api` FAIL 0 · 截图 `logs/screenshots/20260916-2115-序号4v1-接入凭证表单-textleaf轮-h5-430宽.png`。
  ⑦**口径更正**：本页无参路由（页面源码不读参数）—— §4/上轮简报的「带参路由 `/pages/credential-submit/form?id=c1`」作废。
  ⑧**累计**：序号 1 / 6 / 7 / 10.1 / 12-v1 / 12-v2 / 12-v3 / 22 / 4-v1 已归零 ⇒ 待判读 **56 → 48** · 已核定 **95 → 103**。
  ⑨**下轮开工第一件事**：**序号 5**（`page-5-2` 检测进行中 · 待判读 8 条 · mock `api` · 带参路由 `/pages/detecting/index?jobId=j1`），同法一页一轮推进。
  ⑩**改名（队列 0）**：按决策 D6 **本轮未再重试** `git mv`（人类已裁定「不重命名」，`hioas-*` 是仓库名约定）。
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
