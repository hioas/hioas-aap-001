#!/bin/bash
# 序号 6：明细卡内部纵向对账（设计 PNG vs 实现 PNG）—— 定位「说明行 +4 / 组标题 +8」的来源。
# 用法: bash .agents/state/cmp-card4-bands-6.sh
set -u
cd "$(dirname "$0")/../.." || exit 1
DESIGN=.agents/state/design-shots/page-6.png
IMPL="${IMPL:-logs/screenshots/20260916-1755-序06-检测报告-报告编号前缀核定-h5-430宽.png}"

run() {
  local label="$1" x0="$2" y0="$3" x1="$4" y1="$5"
  echo "=== $label  x=$x0..$x1 y=$y0..$y1"
  echo "  [design] $(python .agents/state/png-textbands.py "$DESIGN" "$x0" "$y0" "$x1" "$y1" --minink 2 2>/dev/null | tail -n +2 | tr '\n' ' ')"
  echo "  [impl]   $(python .agents/state/png-textbands.py "$IMPL" "$x0" "$y0" "$x1" "$y1" --minink 2 2>/dev/null | tail -n +2 | tr '\n' ' ')"
}

# 明细卡头：卡顶 1425 + padding 20 → 标题行；标题行 → 说明行
run "明细卡标题 全维度明细" 33 1440 180 1476
run "说明行 46 项计入总分…" 33 1470 385 1500
# 7 个组标题（impl rect top：1512 1949 2343 2737 3217 3611 4005）
for t in 1512 1949 2343 2737 3217 3611 4005; do
  y0=$((t - 12)); y1=$((t + 18))
  run "组标题 top=$t" 46 "$y0" 214 "$y1"
done
# 权重说明盒（impl 4298..4370）
run "权重说明盒" 33 4290 385 4374
# 卡底边（设计 4400 / 实现 4390）
run "明细卡下缘→风险卡标题" 33 4380 200 4440
