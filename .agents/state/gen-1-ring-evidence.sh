#!/bin/bash
# gen-1-ring-evidence.sh — 序号 1「center 描边→ring / 输入框图标字形盒 / 设计 effects」红绿与像素对账转录。
# 用法: bash .agents/state/gen-1-ring-evidence.sh
set -u
ROOT="E:/workspaces/hioas/hioas-aap-001"
cd "$ROOT" || exit 1
EVD="$ROOT/.agents/state/evidence"
OUT="$EVD/redgreen-序号1-ring图标盒投影-20260916.txt"

{
  echo "== 序号 1 登录注册：center 描边 → ring（5 处） + 输入框图标字形盒 20×27 + 设计 effects（卡/主按钮投影） =="
  echo "设计真源：.calicat/raw/pages/page-1-2/design.tree.json（画布 2095515676976640000 当前状态）+ 设计 PNG 430×1114"
  echo "时间：$(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo "---- RED ①（载体页新增 29 条 checks，源码未改，两轮）----"
  python .agents/state/show-fails3.py "$EVD/review-序号1-ringred-run1.json" | head -3
  echo "  红清单条数 run1：$(python .agents/state/show-fails3.py "$EVD/review-序号1-ringred-run1.json" | grep -c '^    FAIL')"
  echo "  红清单条数 run2：$(python .agents/state/show-fails3.py "$EVD/review-序号1-ringred-run2.json" | grep -c '^    FAIL')"
  python .agents/state/show-fails3.py "$EVD/review-序号1-ringred-run1.json" | grep FAIL
  echo
  echo "---- RED ②（补 2 条 effects checks：卡片/主按钮投影，源码未改，两轮）----"
  python .agents/state/show-fails3.py "$EVD/review-序号1-effred-run1.json" | head -4
  echo "  run2："
  python .agents/state/show-fails3.py "$EVD/review-序号1-effred-run2.json" | head -4
  echo
  echo "---- GREEN（实现后复跑两轮）----"
  python .agents/state/show-fails3.py "$EVD/review-序号1-final-run1.json" | head -7
  python .agents/state/show-fails3.py "$EVD/review-序号1-final-run2.json" | head -7
  echo
  echo "---- 两轮独立测量一致性 ----"
  python .agents/state/cmp-measure-runs.py "$EVD/review-序号1-final-run1.json" "$EVD/review-序号1-final-run2.json" phase1 | tail -3
  echo "  phase5（勾选态）：$(python .agents/state/show-phase-fields.py "$EVD/review-序号1-final-run1.json" phase5 checkCount checkFailCount | grep -E 'checkCount|checkFailCount' | tr '\n' ' ')"
  echo "  agreeBoxChecked run1：$(python .agents/state/show-phase-fields.py "$EVD/review-序号1-final-run1.json" phase5 agreeBoxChecked | head -1)"
  echo "  agreeBoxChecked run2：$(python .agents/state/show-phase-fields.py "$EVD/review-序号1-final-run2.json" phase5 agreeBoxChecked | head -1)"
  echo
  echo "---- 像素对账（设计 PNG 430×1114 vs 实现截图 430×1114，±3 结构带）----"
  cat "$EVD/cmp-序号1-设计PNGvs实现截图-结构带.txt"
  echo
  echo "---- 新增结构：图标墨迹 / 文本左界（设计 PNG vs 实现截图，同一 y 带 ink-runs）----"
  echo "[设计 page-1-2.png]"
  python .agents/state/ink-runs.py .agents/state/design-shots/page-1-2.png 40 430 407 423 30 1 | tail -6
  python .agents/state/ink-runs.py .agents/state/design-shots/page-1-2.png 40 430 496 513 30 1 | tail -4
  python .agents/state/ink-runs.py .agents/state/design-shots/page-1-2.png 40 430 586 603 30 1 | tail -4
  echo "[实现 20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png]"
  python .agents/state/ink-runs.py "$EVD/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png" 40 430 407 423 30 1 | tail -6
  python .agents/state/ink-runs.py "$EVD/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png" 40 430 496 513 30 1 | tail -4
  python .agents/state/ink-runs.py "$EVD/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png" 40 430 586 603 30 1 | tail -4
  echo
  echo "---- 投影（卡底 / 主按钮下）同列取色：设计 vs 实现 ----"
  python .agents/state/cmp-pixel-rows.py .agents/state/design-shots/page-1-2.png "$EVD/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png" "721,725,730,735,740,891,895,900,905,910,913,914,920" 200 | tail -14
  echo
  echo "---- 质量门 ----"
  echo "npm test：1182/1182 · 72 files 连跑两轮（19:08:34 / 19:09:23）"
  echo "type-check：exit 0"
  echo "build:mp-weixin：dist/build/mp-weixin/pages/login/{index.js,index.json,index.wxml,index.wxss}（19:07）"
  echo "  wxss 关键值：box-shadow:0 0 0 1px #e2e8f0 ×2 · #e0e7ff · #bfdbfe · #bbf7d0 · border:2px solid #94a3b8（::before 形状）· width:20px;height:27px ×2 · width:25px · box-shadow:0 8px 24px rgba(15,23,42,.08) · box-shadow:0 8px 20px rgba(37,99,235,.28)"
  echo "build:h5：DONE（19:07）"
  echo "review-artifacts：22/22 路由 mp-weixin 三件套齐备且已注册"
  echo "check-mock-fixtures --mock api：全部 PASS（FAIL 0）"
} > "$OUT"

echo "wrote $OUT ($(wc -l < "$OUT") 行)"
