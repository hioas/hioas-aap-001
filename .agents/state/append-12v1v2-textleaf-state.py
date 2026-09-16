# -*- coding: utf-8 -*-
"""回写状态文件：STATUS/LEASE 头 + §5.22 工具与口径 + 本轮小结（追加式）。

用法: python .agents/state/append-12v1v2-textleaf-state.py [--dry]
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = os.path.join(REPO, '.agents', 'state', 'aap-tdd-state.md')

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
          '①新维度「设计文本叶子 ↔ 实现 DOM」逐页收口：**序号 1 / 6 / 12-v1 / 12-v2 已归零**'
          '（本轮 12-v1 待判读 17→**0**（14 键）· 12-v2 12→**0**（11 键），全部判为非偏差并登记 `textleaf-accept.json`；'
          '判法新增「**盒算术**」= 用设计树已声明的 padding/height/gap 反推行盒，再与设计 PNG 的盒边界/墨迹带互证；'
          '载体页复跑 12-v1 **286 条 0 失败**（docH 1240）· 12-v2 **272 条 0 失败**（docH 1127），两轮独立测量全等；**无源码改动**）；'
          '②**下轮第一件事 = 序号 12-v3**（当前待判读最多 · 11 条）：`python .agents/state/textleaf-scan.py 12-v3` → '
          '`python .agents/state/textleaf-audit.py 12-v3` → 按 12-v1 同法（want = 设计声明值 / 设计 PNG 实测 · 先红后绿 · '
          '两轮一致 + 逐类 ink 带对账 · 非偏差登记 `textleaf-accept.json`）；其后按待判读数：7(10) / 10.1(9) / 22(9) / 4-v1(8) / 5(8) / '
          '10(7) / 12(6) / 15(6) / 9(5) / 2(4) / 3(4) / 11(4) / 20(2) / 4(2) … 直到 **107** 条清零。'
          '③其后依次 队列 1 逐页复核余项、队列 3 的 15 条待人类拍板（只做可自主部分）。队列 0 挂起（D6）；管理端 8 页范围外。')

SECTION = '''
### 5.22 本轮（19:40 轮 · 序号 12-v1 / 12-v2 文本叶子收口）新增的工具与口径

- **逐类 ink 带对账（可换帧/换类）**：`python .agents/state/tl-bands.py <dump.json> --classes "a,b,c" --design <设计PNG> --impl <实现PNG> [--pad 14]`
  —— 窗口取「该 DOM 叶子 rect 左右 ±1、上下 ±pad」，打印两图在同一窗口里的 ink 带（与窗口主色不同的连续行）；
  **带起点差 ≤2 且带高相同 ⇒ 渲染行盒一致**。`--all-pending` 保留 12-v1 的 17 类历史用法。
- **分区并排对账**：`python .agents/state/tl-page-bands.py <设计PNG> <实现PNG> [--x0 30 --x1 410 --tol 2]` —— 一页 12 个纵区各打印
  「设计带起点列表 + 实现带起点列表 + 命中率」。本轮 12-v1 **31/36 命中**，未命中 5 条全部判读为：设计投影衰减台阶（2 行带 1~3/255）·
  设计导出图软染色 · 提示条 CJK 换行顺延——**非页面缺陷**（与既有 designLiteralDiff 同族）。
- **盒算术（本轮新增的「want」判法，判据优先级 ② 的可执行化）**：设计树里已声明 `padding` / `height` / `gap` 的容器链，
  可以**反推**被它包住的文本行盒：例如 `字段 = [标签行 fit_content][container padTop 8 → 输入框 h=48]` ⇒
  `输入框顶 − 8 − 标签行顶 = L` 且 `标签墨迹 = 标签行顶 + (L−13)/2` ⇒ 两条独立链各解出 **L = 17**（12-v1 与 12-v2 各两条）。
  同理须知卡 `卡高 = 118 + H3 = 154（PNG 实测）⇒ H3 = 36 = 2 × 18`。**这类「行盒承重」的类必须先做盒算术，不接受只靠 D 值感觉**。
- **新脚本**：`accept-12v1-textleaf.py` · `accept-12v2-textleaf.py` · `accept-1-textleaf.py`（accept 登记 · 幂等 + `--reset`）·
  `tl-show.py`（看 dump 的叶子 rect/类链）· `tl-bands.py` · `tl-page-bands.py` · `ascii-box.py`（把 PNG 矩形渲染成 ASCII，肉眼判字形/换行）·
  `design-ancestors.py <pageId> <leafIdPrefix>`（设计叶子祖先链声明）· `design-children.py <pageId> <idPrefix>`（按 id 列子节点声明）·
  `gen-12v1-textleaf-evidence.sh`（一页文本叶子证据合成）。
- ⚠️ **`textleaf-accept.json` 的键 = 叶子自身 class 链的**第一个 token**（`'hint__text hint__text--blue' → 'hint__text'`）：
  一个键会覆盖多个变体 → 理由里必须写清覆盖了哪些（本轮 `card__title` 覆盖 fs15 主标题与 fs13 的 `--sm` 两种）。
  登记前先跑一次 `textleaf-audit.py <序号>` 确认「待判读 0 · 已核定 N」。
- ⚠️ **`textleaf-audit.py` 的汇总口径已修**：`已核定` 计数此前跨页累加（全量跑会显示成几百），且末行把已核定的行也算进「有偏差」——
  现改为逐页重置 + 末行打印「待判读 class N · 已核定 M（有偏差行合计 K，含已核定）」。**排队取件看「待判读」列，别看末行 K**。
- ⚠️ **同族页必须逐帧做盒算术**：`page-26`（12-v1）与 `page-apikey`（12-v2）共用组件、声明结构相同，但**副行**不同 ——
  12-v2 面板第 2 项副行在设计帧里**换行成 2 行**（同文案实现墨迹宽 **207.3 < 声明宽 208** 故不换行），
  设计侧把它在 16px 定高盒内垂直居中 → 首行上移 `(26.4−16)/2 = 5.2px`、次行溢出到盒下 —— 实测设计 566..575 + 578..588 vs 实现 572..582，
  与算术完全吻合 ⇒ **非页面缺陷**。判读留证 `evidence/cmp-序号12v2-面板副行换行判读.txt`。
  另：该帧面板里的「沙箱 / 专用」是 `env-tag__text`（fs10，与设计 3291a0b7 / 9e2b7dbe 一致），别与 `tag__text`（fs10/fs11）混为一谈。
'''

BULLET = '''
- 2026-09-16 20:2x（cron 轮 `aap-tdd-run-20260916-1940`）· **文本叶子维度第 3/4 页：序号 12-v1（17→0）+ 12-v2（12→0）全部判为非偏差并登记 · 新增「盒算术」判法**：
  ①**设计真源（人工指令 C）**：同一画布当前状态；12-v2 的设计 PNG 本轮新下载 `page-apikey.png`（430×1129，sha256 与建页时同尺寸）。
  ②**逐类 ink 带对账**：`tl-bands` + `tl-page-bands`（12-v1 分区 31/36 命中，未命中 5 条逐条判读为非缺陷）。
  ③**盒算术（本轮主交付的判法）**：标签行盒 **17**（12-v1/12-v2 各两条独立链）· 须知条目 **18**（卡高 154 = 118 + H3 ⇒ H3 = 36 = 2×18）·
  底部说明行由图标字形盒 **19.5** 定（条高 118 = 12+19.5+10+48+28）· 卡片头行 20（设计渲染 18~20，±1 不可分辨）。
  ④**登记**：`textleaf-accept.json` +25 条（12-v1 14 键 / 12-v2 11 键）；另把 序号 1 残留的 `disclaimer__body`（块高 vs 单行行盒的模型口径差）登记。
  ⑤**质量门**：12-v1 载体页 **286 条 0 失败**（docH 1240）· 12-v2 **272 条 0 失败**（docH 1127）· 各两轮独立测量全等（28/28、35/35 字段）；
  **本轮无源码改动**（纯复核核定）→ 未跑 build，沿用上一轮 `build:mp-weixin`/`build:h5` 产物。
  ⑥**下轮第一件事**：序号 12-v3（待判读 11）。
'''

with io.open(P, encoding='utf-8', newline='') as fh:
    text = fh.read()
if '--dry' in sys.argv:
    print('STATUS 行长度 =', len(STATUS))
    print('SECTION 行数 =', SECTION.count('\n'))
    sys.exit(0)

lines = text.split('\n')
assert lines[0].startswith('STATUS:'), lines[0][:40]
lines[0] = STATUS
if len(lines) > 1 and lines[1].startswith('LEASE:'):
    lines[1] = 'LEASE: free until -'
text = '\n'.join(lines)
if '### 5.22' not in text:
    text = text.rstrip('\n') + '\n' + SECTION
text = text.rstrip('\n') + '\n' + BULLET
io.open(P, 'w', encoding='utf-8', newline='').write(text)
print('已回写 %s' % P)
print('STATUS:', text.split('\n')[0][:80], '...')
print('LEASE :', text.split('\n')[1])
