# -*- coding: utf-8 -*-
"""给序号 11 的红/绿转录补「探针自身 bug vs 页面缺陷」的分诊段（避免读者把探针 bug 当页面缺陷）。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVD = os.path.join(ROOT, '.agents', 'state', 'evidence')

RED_NOTE = u"""

--------------------------------------------------------------------------------
红基线分诊（21 条 = 15 条真页面偏差 + 6 条探针自身期望值 bug；另 1 条 want 索引写错）
--------------------------------------------------------------------------------
A. 探针自身口径 bug（**不是**页面缺陷，已在探针里修正后复跑）：
   1) 6 条 `*.ring` 的 want 写成 `rgba(226, 232, 240, 1) ...`，而 Chrome 对 alpha=1 的
      box-shadow 颜色序列化成 `rgb(...)`，探针的 normShadow() 也按此归一 → 期望值写错。
      改为 `rgb(226, 232, 240) 0px 0px 0px 0.8px` / `rgb(147, 197, 253) ...` / `rgb(203, 213, 225) ...`。
      涉及：card2.tierBox.ring · card2.branch.ring · card3.box.ring · card3.checkOff.ring ·
            card4.cond.ring · card4.addBtn.ring
   2) `card3.tokenBoxTops` 写了 slice(0,3)，而 `.card--price .box--input` 的 DOM 顺序是
      「行1 输入/输出 → 行2 缓存读/写 → 行3 1h」（got `454,454,537`）→ 取下标 [0,2,4] 才对
      （`454,537,620`）。属探针索引写错，非页面缺陷。
B. 真页面偏差（15 条，本轮已修，见台账序号 11 行与 evidence/review-序号11-checks-报告.md §4）：
   1) 四张卡缺设计声明的 `drop_shadow(0,4,16,rgba(15,23,42,0.06))`（page.card1~4.shadow）→ 补 box-shadow。
   2) 保存按钮缺设计声明的 `drop_shadow(0,6,16,rgba(37,99,235,0.28))`（bar.save.shadow）→ 补 box-shadow。
   3) 图标盒只有形状大小、没有设计图层盒大小 → 6 类图标盒按设计声明改（盒子变化会改 flex 占位）：
      卡1 折叠箭头 20×20（原 17×17，右界 400→398）· 计费方式 caret 18×18（原 11）·
      添加计费分支 + 18×18（原 11）· 保存按钮 ✓ 22×22（原 14）·
      媒体/规则折叠箭头 18×18 · 规则组删除 18×18 · 条件行 + 15×15。
   4) 由 3) 连带：添加计费分支按钮宽 111→119（= 12+18+4+73+12，设计值），
      计费方式选择框 245→237（设计值），按钮 x 287→279（设计值）。
   5) 媒体列勾选框描边：设计 stroke thickness=1（token 列 0.8）→ `.media__col .check:not(.check--on)`
      单独声明 `0 0 0 1px`（card3.mediaCheck.ring 红 → 绿）。
"""

GREEN_NOTE = u"""

--------------------------------------------------------------------------------
本轮补的 checks 维度（新增 15 条，覆盖本轮修掉的图标盒/描边，防止回归）
--------------------------------------------------------------------------------
card1.chevron.h · card2.branchIcon.h · card2.selectCaret.h · card3.mediaCheck.radius ·
card3.mediaArrow.w/.h/.right · card4.ruleArrow.w/.h · card4.trash.w/.h ·
card4.actionPlus.w/.h · card4.addPlus.w/.h
（红基线那轮探针还没有这些 check，故 red 的 checkCount=256 < green 的 271）
"""

with io.open(os.path.join(EVD, 'red-序号11-checks-设计期望值偏差.txt'), 'a', encoding='utf-8') as f:
    f.write(RED_NOTE)
with io.open(os.path.join(EVD, 'green-序号11-checks-设计期望值.txt'), 'a', encoding='utf-8') as f:
    f.write(GREEN_NOTE)
print('annotated')
