# -*- coding: utf-8 -*-
"""回写 `.agents/state/aap-tdd-state.md`：替换第 1 行 STATUS、追加 §5.23 与「本轮小结」一行。

保留文件原有行尾（逐行读取并沿用主导终止符），避免整文件在 git 里显示改动。
用法: python .agents/state/append-12v3-textleaf-state.py [--dry]
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
          '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：**序号 1 / 6 / 12-v1 / 12-v2 / 12-v3 已归零**'
          '（本轮 12-v3 待判读 11→**0**（9 键覆盖 11 条 class）：8 条由设计**显式 height** 的定高盒'
          '（胶囊 h18/h20/h28 · 复制按钮 h32 · 按钮 h48）判「行盒不承重」，fs13 摘要行由墨迹行距 38 = 10 + 行盒 + 10 解出行盒 18，'
          'fs15/fs14 卡片标题行由 ink 起点 + 卡区带 8/8 命中佐证；逐类 ink 带与设计相同或 ±1 · 整页 4 区 24/25 命中；**无源码改动**）；'
          '②**下轮第一件事 = 序号 7**（当前待判读最多 · 10 条）：`python .agents/state/textleaf-scan.py 7` → '
          '`python .agents/state/textleaf-audit.py 7` → 按 12-v3 同法（判据 ①显式 height ②设计 PNG 盒/带实测 ③fs×lh，②③冲突以 ② 为准；'
          'want 是真偏差就先红后绿改源码，否则登记 `textleaf-accept.json`）；'
          '其后按待判读数：10.1(9) / 22(9) / 4-v1(8) / 5(8) / 10(7) / 12(6) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 20(2) / 4(2) … '
          '直到 **84** 条清零（本轮收口后全量审计：待判读 84 · 已核定 68 · `evidence/textleaf-audit-20260916-2015.txt`）。'
          '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = """
### 5.23 本轮（20:00 轮 · 序号 12-v3 文本叶子收口）新增的工具与口径

- **分区并排对账支持换页**：`python .agents/state/tl-page-bands.py <设计PNG> <实现PNG> --regions "区名:y0:y1,..."`
  —— 内置 REGIONS 只覆盖 page-26；换页必须用 `--regions` 显式给窗口，**y 从设计 PNG 的卡片色带读出**（
  `png-rowclass.py --x0 16 --x1 414` 一眼看出卡 392..639 / 658..787 / 底栏 956..1017），别凭感觉写。
- ⚠️ **判「行盒是否承重」先看设计给没给显式 height**：12-v3 的 11 条待判读里有 **8 条**落在设计声明高度的盒子里
  （模型数标/环境小标 h18 · 状态标 h20 · 模型标签 h28 · 复制按钮 h32 · 按钮 h48），文本 `textAlignVertical=middle` →
  行盒变动只移动墨迹 ≤1px，属「不承重」，**登记非偏差而不是改 CSS**；只有行高由内容决定的容器才需要盒算术。
- **盒算术的又一例（fs13）**：`摘要行 = padding [10,0,10,0] + alignItems=center` → 行高 = 10 + 行盒 + 10；
  设计 PNG 相邻行同字号标签的墨迹起点差 **38** ⇒ 行盒 **18**（声明模型 fs×1.2 = 15.6 会算出 ≈37，与实测不符）。
  同页 fs15 标题 20、fs14 标题 18~24(字形层定) —— **一页里多套行盒，逐节点判**。
- ⚠️ **「审计 want」来自 `fs × lineHeight`，与设计渲染值天然差 2.8~4.5px**（CJK fit_content 的自然行框）：
  逐页收口的动作 = 把每条 want 用「①显式 height ②PNG 盒/带 ③盒算术」重判一次，**不要拿 fs×1.2 去改 CSS**。
- **无源码改动的轮次也要有回归门**：复用该页载体页两轮（`review-measure.sh`，mock 目录必须传仓库相对路径）
  + `cmp-measure-runs.py <a> <b> phase1`（字段全等）+ `requests-序号*-run{1,2}.txt` 逐字节 diff + 430 宽整页截图与上一轮 `cmp` 逐字节相同。
- **本轮新增脚本**：`accept-12v3-textleaf.py`（accept 登记 · 幂等 + `--reset`）· `append-12v3-textleaf-state.py`（本文件回写）。
"""

SUMMARY = """
- 2026-09-16 20:1x（cron 轮 `aap-tdd-run-20260916-2000`）· **文本叶子维度第 5 页：序号 12-v3（page-29「新增报价单-保存成功」）11 条待判读 class 全部收口（判为非偏差 · `textleaf-accept.json` +9 键覆盖 11 条）· 无源码改动 · 回归门全绿**：
  ①**设计真源（人工指令 C）**：重抓帧「新增报价单-保存成功」+ `layer_id 49d2fa52-959d-4415-9fda-edf38415d6bd` → `design.json` sha256 `cdd34a51…` **逐字节相同**（无漂移）。
  ②**RED→GREEN**：`textleaf-scan.py 12-v3`（带参路由 `#/pages/quote-form/success?quoteId=q9` + mock `api-12-v3`，leafs 29 · docH 1018）→ `textleaf-audit.py 12-v3` 红基线 **11 条待判读**（`evidence/red-序号12v3-textleaf-待判读11.txt`）→ 逐条判读并登记 → 复跑 **待判读 0 · 已核定 11**（`green-序号12v3-textleaf-待判读0.txt`）。
  ③**判读（判据 ①显式 height ②PNG 盒/带 ③盒算术）**：8 条落在设计**显式声明高度**的定高盒（模型数标/环境小标 h18 · 状态标 h20 · 模型标签 h28 · 复制按钮 h32 · 按钮 h48）→ 行盒不承重；
  fs13 摘要行 `padding [10,0,10,0] + align center` ⇒ 行高 = 10 + 行盒 + 10，PNG 实测相邻行标签墨迹起点差 **38** ⇒ **行盒 18**（= 实现值；声明模型 15.6 会算出 ≈37）；
  fs15 结果摘要 / fs14 已带出模型（标题行内含 fs16 字形层 → 24 定行高）由 ink 起点与卡区带 8/8 命中佐证。逐类 ink 带与设计相同或 ±1（H5 回退字体）。
  ④**像素/结构证据**：`evidence/cmp-序号12v3-文本叶子行盒-逐类带.txt`（逐类同窗口双侧带）· `evidence/cmp-序号12v3-分区并排对账.txt`（整页 4 区 **24/25 命中**，唯一未命中 = 底栏次按钮 ring 的 1 行 AA 带归属）。
  ⑤**回归门（本轮无源码改动，仍证明页面绿）**：载体页 `__measure-quote-success.html` 两轮 **259 条 checks 0 失败**（`docH 1018` · 31/31 字段全等 · requests 两轮逐字节相同 = 2 行只读 GET）·
  430 宽整页截图与 15:0x 轮 `cmp` **逐字节相同**· `npm test` **1185/1185 · 72 files** 连跑两轮（20:05:47 / 20:06:19）· `npm run type-check` exit 0 · 未重跑 build（无 `src/**` 改动）。
  ⑥**工具**：`tl-page-bands.py` 新增 `--regions`（换页时按设计 PNG 卡片色带显式给窗口，`png-rowclass` 取边界）；报告 `evidence/review-序号12v3-textleaf-报告.md`。
  ⑦**下轮开工第一件事**：**序号 7**（待判读 10 条），同法一页一轮推进，直到 84 条清零。
"""

path = P
raw = io.open(path, 'r', encoding='utf-8', newline='').read()
lines = raw.splitlines(True)
crlf = raw.count('\r\n')
lf_only = raw.count('\n') - crlf
term = '\r\n' if crlf >= lf_only else '\n'
print('行尾统计: CRLF %d · LF-only %d → 本轮用 %r' % (crlf, lf_only, term))

lines[0] = STATUS + term
for block in (SECTION, SUMMARY):
    text = block.lstrip('\n')
    for ln in text.split('\n'):
        lines.append((ln + term) if ln else term)

print('新第 1 行: %s' % lines[0][:120])
print('总行数 %d → %d' % (len(raw.splitlines()), len(lines)))
if '--dry' not in sys.argv:
    io.open(path, 'w', encoding='utf-8', newline='').write(''.join(lines))
    print('已写盘 %s' % path)
