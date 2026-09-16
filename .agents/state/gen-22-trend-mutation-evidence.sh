#!/bin/bash
# 序号 22 趋势图 checks 的变异测试证据合成
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
cd "$ROOT"
OUT="evidence/red-序号22-trendchecks-变异测试.txt"
{
  echo "序号 22 趋势图 checks（本轮新增 8 条）的「有牙齿」证明 —— 源码变异测试"
  echo "变异（临时改 aap-client/src/utils/usage-model.ts，未提交）："
  echo "  ① 末条网格线色 '#E2E8F0' → '#F1F5F9'"
  echo "  ② 末点半径 'last ? 5 : 4' → 'last ? 4 : 4' 且末点色 '#1D4ED8' → '#2563EB'"
  echo "步骤：npm run build:h5 → bash .agents/state/review-measure.sh 22-tlmut __measure-usage.html .agents/state/h5-measure/api-22 5364"
  echo "变异后结果（.agents/state/evidence/review-序号22-tlmut-run{1,2}.json）："
  python .agents/state/show-phases.py .agents/state/evidence/review-序号22-tlmut-run1.json
  echo
  echo "还原：git checkout -- aap-client/src/utils/usage-model.ts → npm run build:h5 → 复跑 22-tl"
  echo "还原后结果（.agents/state/evidence/review-序号22-tl-run{1,2}.json）："
  python .agents/state/show-phases.py .agents/state/evidence/review-序号22-tl-run1.json
  echo
  echo "=> 8 条新 checks 中 3 条随变异变红、还原后全绿 —— 它们确实盯住了渲染出来的折线图（非空断言）。"
} > "$OUT" 2>&1
cat "$OUT"
