#!/bin/bash
# 序号 6：维度总览卡 6 行的行距对账（dim__text / dim__score 行盒 16 vs 模型 14.4）
# 用法: bash .agents/state/cmp-dim-rows-6.sh
set -u
cd "$(dirname "$0")/../.." || exit 1
DESIGN=.agents/state/design-shots/page-6.png
IMPL="${IMPL:-logs/screenshots/20260916-1935-序06-检测报告-文本叶子维度收口-h5-430宽.png}"

# run <label> <x0> <y0> <x1> <y1>
run() {
  echo "=== $1  x=$2..$4 y=$3..$5"
  echo "  [design] $(python .agents/state/png-textbands.py "$DESIGN" "$2" "$3" "$4" "$5" --minink 2 2>/dev/null | tail -n +2 | tr '\n' ' ')"
  echo "  [impl]   $(python .agents/state/png-textbands.py "$IMPL" "$2" "$3" "$4" "$5" --minink 2 2>/dev/null | tail -n +2 | tr '\n' ' ')"
}

run "维度名列（6 行）" 46 1195 120 1375
run "维度分列（6 行）" 366 1195 400 1375
