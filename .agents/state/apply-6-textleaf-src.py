# -*- coding: utf-8 -*-
"""序号 6（page-6 / 检测报告）文本叶子维度收口 —— 源码改动（按设计声明值 / 设计 PNG 实测）。

8 处：
  ① .detail-summary line-height 24 → 16（design 明细说明 8485b93b frame h=24 = pad-top 8 + 行盒 16）
  ② 分组之间补 1px 分隔线（design 分隔线A–F）→ .group__sep
  ③ .action__ghost-text 补 font-weight 500（design a3023014 Medium）
  ④ .finding__title 700 → 600（design 2ba0333a SemiBold）
  ⑤ .dim__text 补 font-weight 500（design 177b7f5f Medium）
  ⑥ .dim__score 补 font-weight 700（design 0947f700 Bold）
  ⑦ 状态标签 pill（未申报/仅证据/不可测）font-weight 600（design 2ba0333a/66800e15/1b3c9a9f SemiBold）
  ⑧ G 组「值 pill」font-size 11 / Regular（design ef69fd0e fs11 w142）→ 新增 --value 变体 + 模型 statusIsValue

用法: python .agents/state/apply-6-textleaf-src.py [--dry]
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VUE = os.path.join(REPO, 'aap-client', 'src', 'pages', 'report', 'index.vue')
TS = os.path.join(REPO, 'aap-client', 'src', 'utils', 'report-model.ts')

EDITS = {
    VUE: [
        # ① 明细说明行盒
        ("""  color: $color-text-placeholder;
  line-height: 24px;
}""",
         """  color: $color-text-placeholder;
  /* design 8485b93b「明细说明」frame h=24 = padding-top 8 + 行盒 16（叶子 068c8976 fs11）
     修前把 frame 的 24 当成行盒 → 盒高 32、说明行墨迹比设计低 4px、其下 7 个分组整体低 8px
     （设计 PNG 实测 1476..1486 vs 修前实现 1480..1490，evidence/cmp-序号6-明细卡纵向对账.txt） */
  line-height: 16px;
}""",
         'summary lh'),
        # ② 分组之间的 1px 分隔线（CSS）
        ("""/* design：分组之间（以及最后一个分组与权重说明盒之间）有 16 高间隔条
   （design.tree.json 的 spacer 8a882495 = 357×16；PNG 实测组标题 ink 间距 A→B = 437 与 421+16 自洽） */
.group + .group {
  margin-top: 16px;
}""",
         """/* design：分组之间 = spacer 16（如 79fe8295）+ 1px 分隔线（分隔线A–F，rgba(238,242,247,1)）；
   末组与权重说明盒之间只有 spacer 16（design 8a882495）。
   旧注释「PNG 实测组标题 ink 间距 A→B = 437」是拿实现自己的算术（421+16）反证自己 —— 漏了这条 1px 分隔线；
   设计 PNG 实测 A→B = 438，分隔线落在 1926..1927（evidence/cmp-序号6-明细卡纵向对账.txt）。 */
.group__sep {
  margin-top: 16px;
  height: 1px;
  flex-shrink: 0;
  background: $color-border-chip; /* rgba(238,242,247,1) */
}""",
         'group sep css'),
        # ② 分组之间的 1px 分隔线（模板）
        ('<view v-for="section in model.sections" :key="section.code" class="group">',
         '<view v-for="(section, index) in model.sections" :key="section.code" class="group">',
         'group vfor'),
        ("""          </view>

          <view class="note-box">{{ model.weightNote }}</view>""",
         """          </view>

          <!-- design：只在分组之间补 1px 分隔线（分隔线A–F），末组与权重说明盒之间无 -->
          <view v-if="index < model.sections.length - 1" class="group__sep" />

          <view class="note-box">{{ model.weightNote }}</view>""",
         'group sep template'),
        # ③ 导出 PDF 字重
        (""".action__ghost-text {
  margin-left: 6px;
  font-size: 14px;""",
         """.action__ghost-text {
  margin-left: 6px;
  font-size: 14px;
  font-weight: 500; /* design a3023014 fontFamily=SourceHanSans-Medium */""",
         'ghost fw'),
        # ④ 发现标题字重
        ("  font-weight: 700; /* design：发现标题 Bold */",
         "  font-weight: 600; /* design 2ba0333a fontFamily=SourceHanSans-SemiBold */",
         'finding fw'),
        # ⑤ 维度名行字重
        (""".dim__text {
  margin-left: 6px;
  font-size: 12px;""",
         """.dim__text {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 500; /* design 177b7f5f fontFamily=SourceHanSans-Medium */""",
         'dim text fw'),
        # ⑥ 维度分列字重
        ("""  text-align: right;
  margin-left: 8px;
  font-size: 12px;
  line-height: 16px;
  color: $color-text-primary;
}""",
         """  text-align: right;
  margin-left: 8px;
  font-size: 12px;
  font-weight: 700; /* design 0947f700 fontFamily=SourceHanSans-Bold */
  line-height: 16px;
  color: $color-text-primary;
}""",
         'dim score fw'),
        # ⑦⑧ pill
        (""".item__pill--evidence .item__pill-text {
  color: $color-text-muted;
}""",
         """.item__pill--evidence .item__pill-text {
  color: $color-text-muted;
}

/* G 组各类的「值 pill」：设计里值是**数据**图层（ef69fd0e 等 fs11 / Regular），
   与状态标签 pill（未申报/仅证据/不可测，fs10 / SemiBold）不是同一套字号字重 */
.item__pill--value .item__pill-text {
  font-size: 11px;
  font-weight: 400;
}""",
         'pill value css'),
        (""".item__pill-text {
  font-size: 10px;
  color: $color-text-muted;
}""",
         """.item__pill-text {
  font-size: 10px;
  /* design 状态标签 pill：e247efe0「未申报」/ 66800e15「不可测」/ 1b3c9a9f「仅证据」均 SemiBold */
  font-weight: 600;
  color: $color-text-muted;
}""",
         'pill status css'),
        # ⑧ 模板加 --value 修饰
        ('<view v-else class="item__pill" :class="`item__pill--${row.statusKey}`">',
         """<view
                v-else
                class="item__pill"
                :class="[`item__pill--${row.statusKey}`, { 'item__pill--value': row.statusIsValue }]"
              >""",
         'pill template'),
    ],
    TS: [
        ("""export interface ReportItemRow {
  code: string
  label: string
  metric: string
  scoreText: string
  barPercent: number
  color: string
  statusKey: ItemStatusKey
}""",
         """export interface ReportItemRow {
  code: string
  label: string
  metric: string
  scoreText: string
  barPercent: number
  color: string
  statusKey: ItemStatusKey
  /** true = pill 里显示的是该项的**服务端值**（G 组「真实源证据」各类），
   *  不是「未申报 / 仅证据 / 不可测」这类状态标签 —— 两者字体规格不同（设计：值 fs11/Regular，标签 fs10/SemiBold） */
  statusIsValue: boolean
}""",
         'type field'),
        ("""    scoreText,
    barPercent: statusKey === 'scored' && score !== null ? Math.round(score) : 0,
    color,
    statusKey
  }""",
         """    scoreText,
    barPercent: statusKey === 'scored' && score !== null ? Math.round(score) : 0,
    color,
    statusKey,
    statusIsValue: !meta && !status && !sectionScored && value !== ''
  }""",
         'model field'),
    ],
}


def apply(path, edits, dry):
    src = io.open(path, encoding='utf-8').read()
    for old, new, tag in edits:
        n = src.count(old)
        if n != 1:
            print('锚点命中 %d 次（必须恰好 1 次）: %s @ %s' % (n, tag, os.path.basename(path)))
            return None
        src = src.replace(old, new)
        print('OK  %-18s %s' % (tag, os.path.basename(path)))
    if not dry:
        io.open(path, 'w', encoding='utf-8', newline='').write(src)
    return src


dry = '--dry' in sys.argv
ok = True
for p, edits in EDITS.items():
    if apply(p, edits, dry) is None:
        ok = False
print('全部锚点唯一' if ok else '有锚点不唯一 —— 未写盘')
sys.exit(0 if ok else 2)
