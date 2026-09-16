# -*- coding: utf-8 -*-
"""本轮（序号 9 checks 轮）回写状态文件：STATUS 行 + §4 队列 8 条目 + §5 工具 + 本轮小结（追加） + 释放租约。"""
import io
import re
import subprocess
import sys

P = '.agents/state/aap-tdd-state.md'
src = io.open(P, encoding='utf-8', newline='').read()
lines = src.split('\n')

STATUS = (
    'STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。**每轮先读 `aap-decisions.md`**（待执行决策优先于本文件在办项）。'
    '**D1~D6 已全部执行完**（D6 挂起=不重命名）。当前在办：'
    '①**队列 8（给载体页补「设计期望值 checks」维度，一页一轮）：序号 3 已完成 09:38（160 条 · 15→0）· 序号 4 已完成 09:55（212 条 · 45→0）'
    '· 序号 4-v1 已完成 10:20（249 条 · 78→0）· 序号 5 已完成 10:42（237 条 · 95→0）· 序号 6 已完成 11:5x（221 条 · 45→0，docH 4886→5343 = 设计帧高 5342）'
    '· 序号 7 已完成 11:3x（196 条 · 51→0，docH 1063→1111 = 设计帧高 1110）· 序号 8 已完成 11:5x（138 条 · 27→0，docH 1198→1206 = 设计帧高 1206）'
    '· 序号 9 已完成 2026-09-16 12:21（272 条 · 53→0，docH 1202→1212 = 设计帧高 1211，像素对账 68/68 命中，报告 `evidence/review-序号9-checks-报告.md`）'
    '→ 下一轮开工做 序号 10**（`page-10-2`「供应商档案编辑 2」→ `/pages/profile-edit/index`，载体页 `__measure-profile-edit.html`，mock 目录 `api-10-2`；'
    '对照表 `python .agents/state/survey-harness-routes.py`） ②队列 1 逐页复核（余下行的 checks 维度待补） ③队列 7（uni-picker 溢出口径）'
    '④D1 循环侧收尾余项（台账 `missing-prd` 接口备注改成「依据 `docs/api/接口字段级schema.md` §x」+ 字段名一致性核对；D1 本体的 schema 文档已由前台会话建好）。'
    '⚠️ **序号↔路由映射一律以台账「目标路由」列为准**（序号 9 = `/pages/quote-models/index`；`/pages/model-pricing/index` 是序号 11）——'
    '此前在办项写错过一次（2026-09-16 12:05 轮已改正），勿再沿用。历史流水归档在 `aap-notes-archive-2026-09-16.md`，**不要每轮读**。'
)

assert lines[0].startswith('STATUS:'), lines[0][:40]
lines[0] = STATUS

# §4 队列 8：在「序号 8 已完成」条目后补 序号 9 的完成条目
marker = '   - ⚠️ 本轮踩到并写进 §5 的坑：重抓前必须先确认 Calicat 编辑器在浏览器里打开'
entry = (
    '   - ✅ **序号 9 已完成 2026-09-16 12:21**（cron 轮 `aap-tdd-run-20260916-1205`）：`__measure-quote-setup.html` 由 284 行旧体例重写为 430 宽 iframe + **272 条 checks**\n'
    '     （want = `page-9` design.tree.json 声明值 + `text-fields.py` 全字段 + 设计 PNG 430×1211 像素实测）。\n'
    '     红基线（`git stash push` 复现修复前源码、同一份探针两轮）**53/272**、`docH 1202` → 绿 **0/272**、`docH 1212`（设计帧 1211）；\n'
    '     两轮独立测量 **33/33 字段全等**；`git stash pop` 复位后重建复跑同值。\n'
    '     修掉 12 类偏差：卡片/底栏/保存按钮投影（设计 effects）· 三处 0.8 描边 `border`→`box-shadow`（内容左界回到 46）· 字数提示行框 16→15 ·\n'
    '     凭证说明图标盒 20×20→14×18 · 模型工具栏 40→44（全选图标行框 24）· 模型行高 58→59（型号名行框 19）· 底部说明 `padding-top` 12→16 且图标盒 13→15×20 ·\n'
    '     提示卡文案行距 16→14（卡高 56→52）· 12 处图标盒按设计图层且形状（含旋转）移入 `::before` · 返回/帮助圆角 50%→18px。\n'
    '     交互相 `?scenario=actions` 两轮逐字节相同：勾选第 4 行/全选/全不选 计数 3→4→5→0 · 保存 → 真实 `POST /quotes` + `POST /quotes/q9/items` →\n'
    '     toast「保存成功」→ `/pages/model-pricing/index?quoteId=q9` · 纯测量轮 serve 实收仅 3 行。\n'
    '     像素对账（实现截图 vs 设计 PNG，±3）内容列 **49/49** + 条列 **19/19** = **68/68 命中、未命中 0**。\n'
    '     质量门：`npm test` **1172/1172 ×2** · `type-check` exit 0 · `build:mp-weixin` / `build:h5` DONE · 截图 `evidence/20260916-1221-序号9-模型报价设置-checks轮-h5-430宽.png`。\n'
    '     **下一轮：序号 10**（`page-10-2`「供应商档案编辑 2」→ `/pages/profile-edit/index`，载体页 `__measure-profile-edit.html`，mock 目录 `api-10-2`）。\n'
)
if '序号 9 已完成 2026-09-16 12:21' not in src:
    idx = [i for i, l in enumerate(lines) if l.startswith(marker)]
    assert idx, 'marker not found'
    lines.insert(idx[0], entry)

# §5：补本轮新增工具
tools_marker = '- **D3 测量面（本轮新增）**'
tools = (
    '- **本轮（12:05 轮 · 序号 9）新增工具**：`png-rowmodal.py`（逐行主色 + 白占比判卡片/间隙，`--runs` 打印分段；带投影的卡片页首选）·\n'
    '  `png-colorat.py <png> h|v <idx> <rrggbb> [tol] [minLen]`（某行/列上「接近指定颜色」的连续区间 → 元素横向边界）·\n'
    '  `show-json.py <file.json> [phase]`（pretty 打印某相）· `show-ledger-rows.py <序号...>`（打印台账整行可见内容）·\n'
    '  `gen-9-checks-evidence.py`（红/绿 + 交互回放转录合成，后续页面照抄改 tag）· `shot-9.sh`（430×1211 整页截图）。\n'
    '- ⚠️ **探针断言「容器高」而不是「行框」**：`padding-top` 与内容行同在一个元素上的结构（本页 `.counter` / `.hint`），\n'
    '  `chkR` 要断 `padding-top + 行框` 的合计（本页字数提示 21 = 6+15 · 凭证说明 24 = 6+18）；行框本身用 `lineHeight` / 图标盒高断言。\n'
    '- ⚠️ **`box-shadow` 的 used 值不取整**：Chrome 对 `box-shadow: 0 0 0 .8px` 的 computed 实测为 `rgb(..) 0px 0px 0px 0.8px`；\n'
    '  旧口径「0.8px 的 computed 取整成 1px」只对 `border` 成立（本页两条 stroke 检查都用 0.8px 作为期望值）。\n'
    '- ⚠️ **PNG 卡片边界：三张卡都带投影时**卡片之间的间隙被两张卡的阴影同时染色，`png-cardmap --x 30` 会把卡片与间隙连成一段；\n'
    '  用 `png-rowmodal.py --runs`（逐行主色）才能得到 118..265 / 282..558 / 575.. 这类边界。\n'
)
if 'png-rowmodal.py' not in src:
    idx = [i for i, l in enumerate(lines) if l.startswith(tools_marker)]
    assert idx, 'tools marker not found'
    lines.insert(idx[0], tools)

# 本轮小结（追加到「### 本轮小结」段落末尾，即下一个二级标题 §5 之前）
summary = (
    '- 2026-09-16 12:21（cron 轮 `aap-tdd-run-20260916-1205`）· **队列 8 第 8 页：序号 9「模型报价设置」载体页补「设计期望值 checks」维度（272 条 · 偏差 53→0）+ 12 类设计偏差修复 + 整页对齐设计帧 1211（像素对账 68/68 命中）**：\n'
    '  ①**口径纠正**：状态文件在办项曾把序号 9 写成「→ `/pages/model-pricing/index`，载体页 `__measure-model-pricing.html`」，与台账「目标路由 = `/pages/quote-models/index`」\n'
    '  及仓库实际不符（`/pages/model-pricing/index` 是**序号 11**）→ 本轮按台账执行（载体页 `__measure-quote-setup.html`），并已把状态文件改成与台账一致。\n'
    '  ②**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-9`（layer_id `bbdb4ec0-…`）→ `design.json` sha256 `bb278d4e…` **逐字节相同**（无漂移）。\n'
    '  ③**TDD 红→绿（本轮主交付）**：载体页重写为 430 宽 iframe + 272 条 checks；红基线（`git stash` 复现修复前源码、同一份探针两轮）**53/272**、`docH 1202`\n'
    '  → 绿 **0/272**、`docH 1212`；两轮独立测量 33/33 全等；复位后复跑同值。\n'
    '  ④**修掉 12 类偏差**（清单见台账序号 9 行 / `review-序号9-checks-报告.md` §4）：三处投影（卡片/底栏/保存按钮）· 三处 0.8 描边 `border`→`box-shadow` ·\n'
    '  字数提示行框 16→15 · 凭证说明图标盒 20×20→14×18 · 模型工具栏 40→44 · 模型行高 58→59 · 底部说明 padding 12→16 且图标盒 13→15×20 · 提示卡行距 16→14（卡高 56→52）·\n'
    '  12 处图标盒按设计图层且形状移入 `::before` · 返回/帮助圆角 50%→18px。\n'
    '  ⑤**本页定标**：CJK 文本行框 = fontSize×1.4 取整（15→20 · 14→19 · 13→18 · 12→16 · 11→15，**显式 height 优先**）；remixicon 字形行框 = fontSize×1.5；\n'
    '  `stroke{align:center,thickness:0.8}` → `box-shadow: 0 0 0 .8px`（**used 值不取整**）；`effects.drop_shadow` → `box-shadow`。\n'
    '  ⑥**交互相有牙齿**：`?scenario=actions` 两轮 → 勾选/全选/全不选 3→4→5→0 · 保存 → 真实 `POST /quotes` + `POST /quotes/q9/items` → toast「保存成功」→ `model-pricing?quoteId=q9`；\n'
    '  纯测量轮实收仅 3 行（profile + credentials + credentials/c1）· 溢出 0 · 文案缺失 0。\n'
    '  ⑦**质量门**：`npm test` **1172/1172 · 72 files ×2** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含本轮设计值）· `build:h5` DONE ·\n'
    '  像素对账 68/68 命中 · 截图 `evidence/20260916-1221-序号9-模型报价设置-checks轮-h5-430宽.png`。\n'
    '  ⑧**设计稿静态假数据留痕**：字数提示「13/30」与同帧名称文案 12 字矛盾 → 实现按真实字数（12/30），探针断言「格式 + 与名称长度一致」，\n'
    '  设计字面量登记在 `designLiteralDiff`（同族于 D3 图例百分比，不照抄）。\n'
    '  ⑨**下轮开工第一件事**：队列 8 的 **序号 10**（`page-10-2`「供应商档案编辑 2」→ `/pages/profile-edit/index`，载体页 `__measure-profile-edit.html`，mock 目录 `api-10-2`）。\n'
)
if '队列 8 第 8 页' not in src:
    idx = [i for i, l in enumerate(lines) if l.startswith('## 5. 关键命令')]
    assert idx, '§5 marker not found'
    lines.insert(idx[0], summary)

out = '\n'.join(lines)
io.open(P, 'w', encoding='utf-8', newline='').write(out)
print('state file written, bytes=%d' % len(out))

subprocess.check_call([sys.executable, '.agents/state/lease-set.py', 'free'])
