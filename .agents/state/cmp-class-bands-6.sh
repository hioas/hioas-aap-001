#!/bin/bash
# 逐类对账：设计 PNG vs 实现 PNG 在同一窗口里的行墨迹带（判「行盒是否为设计渲染值」）。
# 用法: bash .agents/state/cmp-class-bands-6.sh
set -u
cd "$(dirname "$0")/../.." || exit 1
DESIGN=.agents/state/design-shots/page-6.png
IMPL="${IMPL:-logs/screenshots/20260916-1755-序06-检测报告-报告编号前缀核定-h5-430宽.png}"

run() {
  local label="$1" x0="$2" y0="$3" x1="$4" y1="$5"
  echo "=== $label  x=$x0..$x1 y=$y0..$y1"
  echo "  [design]"
  python .agents/state/png-textbands.py "$DESIGN" "$x0" "$y0" "$x1" "$y1" --minink 2 | sed 's/^/    /'
  echo "  [impl]"
  python .agents/state/png-textbands.py "$IMPL" "$x0" "$y0" "$x1" "$y1" --minink 2 | sed 's/^/    /'
}

run "card__title--cover 综合检测结论" 56 116 134 154
run "card__title 关键指标" 46 544 112 580
run "metric__label 模型指纹相似度" 45 594 124 622
run "metric__value 0.93" 45 612 92 650
run "metric__sub 30 分钟观测窗口" 229 830 308 860
run "group__title A · 时延与性能" 46 1505 144 1538
run "score__meta-text 综合评分/满分" 93 164 148 208
run "detail-summary" 33 1468 385 1500
run "radar__label 性能" 204 950 232 980
