#!/bin/bash
# 序号 12-v1「新增报价单-初始态」文本叶子维度收口 · 证据合成（可重跑）
#   A. 逐类 ink 带对账（设计 PNG vs 实现 PNG，窗口取实现叶子 rect ±14）
#   B. 盒算术实测（label 行盒 / 须知卡高 / 底部条 / 卡片头行）—— 判「行盒是否为设计渲染值」
# 用法: bash .agents/state/gen-12v1-textleaf-evidence.sh [实现截图]
set -u
cd "$(dirname "$0")/../.." || exit 1
D=.agents/state/design-shots/page-26.png
I="${1:-logs/screenshots/20260916-1945-序12v1-新增报价单初始态-checks轮-h5-430宽.png}"
OUT=.agents/state/evidence/cmp-序号12v1-文本叶子行盒-逐类带.txt
OUT2=.agents/state/evidence/cmp-序号12v1-行盒盒算术.txt

{
  echo "# 序号 12-v1（page-26「新增报价单-初始态」）文本叶子行盒 · 逐类 ink 带对账"
  echo "# 生成: bash .agents/state/gen-12v1-textleaf-evidence.sh"
  echo "# 设计 PNG = $D（430×1238，设计帧导出） 实现 PNG = $I"
  echo "# 窗口 = 该 DOM 叶子 rect 左右 ±1、上下 ±14；带 = 与窗口主色不同的行"
  echo "# 判据: 同一文案的 ink 带起点差 ≤2 且带高相同 ⇒ 渲染行盒一致（H5 回退字体墨迹差计入 ±2）"
  echo "# 例外: 卡2 提示条以下整体 +3~4 = 设计 1 行 / 浏览器 CJK 必然两行（既有 designLiteralDiff）"
  echo
  python .agents/state/tl-bands.py .agents/state/evidence/textleaf-12-v1.json --all-pending --impl "$I" --design "$D"
} > "$OUT" 2>&1

{
  echo "# 序号 12-v1 行盒判定的「盒算术」实测（判据优先级 ② design PNG 实测）"
  echo "# 生成: bash .agents/state/gen-12v1-textleaf-evidence.sh"
  echo
  echo "## 1. 字段标签行行盒 = 17（设计声明 padding 链 + PNG 反推，两条独立链）"
  echo "# 设计树: 字段-报价单名称(61760d8d) = [字段标签行(fit_content)][container padTop 8 → 名称输入框 h=48][container padTop 6 → 字数提示]"
  echo "#         卡片间由 container(padTop 16 → 1px 分隔线) 连接"
  echo "# 反推: 输入框顶 = 标签行顶 + 8 + L；标签墨迹 = 标签行顶 + (L-13)/2"
  echo "#       链1 报价单名称: 输入框顶 277、标签墨迹 254 → 0.5L = 8.5 → L = 17"
  echo "#       链2 报价单号:   输入框顶 405、标签墨迹 382 → L = 17"
  echo "--- design scan-col x=215 y=265..350（名称输入框 fill 248,250,252 的上下界）"
  python .agents/state/scan-col.py $D 215 265 350
  echo "--- design scan-col x=215 y=395..470（报价单号 readonly 盒 fill 241,245,249）"
  python .agents/state/scan-col.py $D 215 395 470
  echo
  echo "## 2. 须知卡条目 3 = 两行 × 18（行盒 18），卡高 154 两边相同"
  echo "# 设计树: 填写须知卡(f4fab5a4) padding 16、无 gap；children = 须知标题行 + container(padTop 12→条目1) + container(8→条目2) + container(8→条目3)"
  echo "# 卡高 = 16 + 标题行 T + (12+H1) + (8+H2) + (8+H3) + 16 = 118 + H3；PNG 实测卡高 154 → H3 = 36 = 2×18"
  echo "# 序号点 18×18、条目间 padding 8 → 点距 26（设计 995/1021/1047 = 实现 998/1024/1050，两边 26）"
  echo "--- design scan-col x=402 y=930..1130（须知卡白区上下界）"
  python .agents/state/scan-col.py $D 402 930 1130
  echo "--- impl   scan-col x=402 y=930..1130"
  python .agents/state/scan-col.py $I 402 930 1130
  echo "--- 序号点列 x=30..56（设计）"
  python .agents/state/png-textbands.py $D 30 940 56 1110 --minink 1
  echo "--- 序号点列 x=30..56（实现）"
  python .agents/state/png-textbands.py $I 30 940 56 1110 --minink 1
  echo "--- 条目 3 文字 x=57..70（设计）—— 两行墨迹起点差 = 字体墨迹差（两边行盒同为 18）"
  python .agents/state/png-textbands.py $D 57 1040 70 1095 --minink 1
  echo "--- 条目 3 文字 x=57..70（实现）"
  python .agents/state/png-textbands.py $I 57 1040 70 1095 --minink 1
  echo
  echo "## 3. 底部操作条：说明行盒由图标字形盒 19.5 决定（文本行盒不承重）"
  echo "# 设计树: 底部操作条(0bf8e01d) padding[12,16,28,16] → [保存说明 横排 gap4 align-center][container padTop 10 → 按钮行]"
  echo "# 条高 118 = 12 + 19.5(图标字形盒 fs13×1.5) + 10 + 48 + 28 ✓（实现 119 含 AA）"
  echo "--- design scan-col x=8 y=1090..1238（页面底色→白条上界）"
  python .agents/state/scan-col.py $D 8 1090 1238
  echo "--- impl   scan-col x=8 y=1090..1241"
  python .agents/state/scan-col.py $I 8 1090 1241
  echo
  echo "## 4. 卡片头行（card__title fs15）：竖条 217..232 两侧相同 ⇒ 头行高一致（18~20 均在 ±1 内，取 20）"
  echo "--- 卡片 1 白区上界（x=402）design / impl"
  python .agents/state/scan-col.py $D 402 190 340
  python .agents/state/scan-col.py $I 402 190 340
  echo "--- 卡片 1/2 之间（x=402）design / impl"
  python .agents/state/scan-col.py $D 402 600 720
  python .agents/state/scan-col.py $I 402 600 720
} > "$OUT2" 2>&1

echo "written: $OUT"
echo "written: $OUT2"
wc -l "$OUT" "$OUT2"
