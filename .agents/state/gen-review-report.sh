#!/bin/bash
# 生成逐页复核报告（每页：两次独立测量的全等/不一致 + 与建页留证的漂移）
set -u
cd /e/workspaces/hioas/hioas-aap-001
OUT=.agents/state/evidence/review-measure-20260916-0811.md
E=.agents/state/evidence

{
  echo "# 逐页复核 · 430 宽 iframe DOM 实测（两轮独立测量 + 与建页留证对比）"
  echo
  echo "- 轮次: aap-tdd-run-20260916-0805 · 生成时间 $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- 测量面: \`npm run build:h5\` 产物 + \`.agents/state/h5-measure/serve.py\`（含 /api/v1 mock）+ 无头 Chrome 430x900 iframe"
  echo "- 一次命令: \`bash .agents/state/review-measure.sh <序号> <载体页> <mock目录> <端口>\` → \`python .agents/state/review-compare.py --tag <序号> --old <建页留证>\`"
  echo "- 覆盖: 台账 22 行里 20 行有 \`__measure-*.html\` 载体页并已复跑；序号 1（登录注册）/ 2（工作台）无载体页 → 本轮以「产物 + 建页留证」复核，下轮补载体页。"
  echo
  while IFS='|' read -r tag harness mock old desc; do
    [ -z "$tag" ] && continue
    echo "## $tag（$desc · $harness · mock=$mock）"
    if [ -n "$old" ] && [ -f "$E/$old" ]; then
      python .agents/state/review-compare.py --tag "$tag" --old "$E/$old" 2>&1 | grep -v "^warning"
    else
      python .agents/state/review-compare.py --tag "$tag" 2>&1 | grep -v "^warning"
      echo "  （无同轮建页留证文件可对：仅两轮一致性）"
    fi
    echo
  done <<'TABLE'
3|__measure.html|api|measure-序号3-无滚动条430.json|凭证列表
4|__measure-submit.html|api|—|提交接入凭证（storage 注入式载体页）
4-v1|__measure-form.html|api|measure-序号4v1-430宽.json|提交接入凭证-表单
5|__measure-detecting.html|api|measure-序号5-430宽.json|检测进行中
6|__measure-report.html|api|measure-序号6-430宽.json|检测报告
7|__measure-report-failed.html|api|measure-序号7-430宽.json|报告-不通过
8|__measure-quotes.html|api|measure-序号8-430宽.json|报价单列表
9|__measure-quote-setup.html|api|measure-序号9-430宽.json|模型报价设置-列表
10|__measure-profile-edit.html|api-10-2|measure-序号10-430宽-修后2.json|供应商档案编辑
10.1|__measure-profile.html|api-10-1-2|measure-序号10.1-run2.json|供应商档案
11|__measure-model-pricing.html|api-11|measure-序号11-run3.json|模型定价
12|__measure-quote-preview.html|api-12|—|报价预览
12-v1|__measure-quote-form.html|api-12-v1|—|新增报价单-初始态
12-v2|__measure-apikey.html|api-12-v2|—|新增报价单-APIKey
12-v3|__measure-quote-success.html|api-12-v3|—|新增报价单-成功
15|__measure-contract.html|api-15|—|合同
20|__measure-messages.html|api-20|—|站内信列表
21|__measure-mine.html|api-21|—|我的页
22|__measure-usage.html|api-22|measure-序号22-run3.json|用量概览
23|__measure-settings.html|api-23|measure-序号23-run2.json|我的设置
TABLE
  echo "## 未通过一致性判读的三处（均已定位，非页面缺陷）"
  echo
  echo "1. **序号 6**：与 01:26 的 \`measure-序号6-430宽-修后.json\` 有 3 处不同（radarLabels/radarLabelRects 缺失、radarRect 差 6px）。原因是该留证**早于同轮 01:28 更新的载体页**（旧版没有雷达标签探测项）。与最新留证 \`measure-序号6-430宽.json\` 全等 65/65 → 判为探测项演进。docScrollHeight 两版一致（4886）＝页面高度未变。"
  echo "2. **序号 10**：与 02:42 留证有 3 处不同（qualBadges/qualBadgeRects/qualBadgeBg）。原因是该留证**早于本页提交 a5916ac（02:46:57）**，即「双角标补红」修复前的快照；当前实现的 3 个独立角标（必传 #FEF2F2/#B91C1C · 已上传 #ECFDF5/#15803D · 条件必传 #FFF7ED/#B45309）与设计树 \`page-10-2-nodes.txt\` 第 130/133/151 行逐字段一致 → 以设计为准，判为快照过期。"
  echo "3. **序号 9**：与 02:22 留证有 phase4 差异（toast 由「保存成功」变成服务端回读文案「mock 未定义该接口: /api/v1/quotes/q9/items」，hash 由停在 quote-models 变成跳到 \`model-pricing?quoteId=q9\`）。原因同上：留证早于本页提交 cc98e23（02:24:51）。新 hash 指向设计序号 11「模型定价」，符合保存后的设计流向；toast 文案来自测量面 mock 缺 GET \`/quotes/q9/items\` fixture（页面按 \`src/api/quote.ts:90\` 的回落入口取明细行）→ 判为**测量面 fixture 缺口**，下轮补 fixture 并复跑（补后需回跑所有用 \`api\` 目录的页面）。"
  echo "4. **序号 22**：\`overflowing\` 字段两轮不同（同一元素 left 在 -99606 / 36 之间跳）。该元素是 uni-app 内置 \`<uni-picker>\` 的空 div，父级 \`overflow:hidden\`（见 \`.agents/state/evidence/diag-序号22-overflow.json\`），\`docScrollWidth\` 两轮均为 430 = innerWidth → **无可见溢出**，载体页探测噪音。"
} > "$OUT" 2>&1

echo "written $OUT ($(wc -c < "$OUT") bytes)"
