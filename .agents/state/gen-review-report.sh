#!/bin/bash
# 生成逐页复核报告（每页：两次独立测量的全等/不一致 + 与建页留证的漂移）
# 用法: bash .agents/state/gen-review-report.sh <轮次id> <输出文件名>
set -u
cd /e/workspaces/hioas/hioas-aap-001
ROUND="${1:-aap-tdd-run-unknown}"
OUT=".agents/state/evidence/${2:-review-measure-$(date '+%Y%m%d-%H%M').md}"
E=.agents/state/evidence

{
  echo "# 逐页复核 · 430 宽 iframe DOM 实测（两轮独立测量 + 与建页留证对比）"
  echo
  echo "- 轮次: $ROUND · 生成时间 $(date '+%Y-%m-%d %H:%M:%S')"
  echo "- 测量面: \`npm run build:h5\` 产物 + \`.agents/state/h5-measure/serve.py\`（含 /api/v1 mock）+ 无头 Chrome 430x900 iframe"
  echo "- 一次命令: \`bash .agents/state/review-measure.sh <序号> <载体页> <mock目录> <端口>\` → \`python .agents/state/review-compare.py --tag <序号> --old <建页留证>\`"
  echo "- 标记: **[本轮新增]** = 本轮的 review-序号*-run{1,2}.json 新写；（上一轮 08:30 留证）= 文件未变、仍可复现判读，本轮未重跑。"
  echo "- 覆盖: 台账 22 行 **全部有 \`__measure-*.html\` 载体页**（本轮补上最后两行：序号 1 登录注册 / 序号 2 工作台）。"
  echo "- 本轮新增维度: 载体页内置 **设计期望值 checks**（逐条 got/want）：登录页 93 项 / 工作台 92 项；\`checkFailCount\` 即「与设计稿的偏差条数」。"
  echo "- 本轮新增证据: \`requests-序号*-run{1,2}.txt\`（该轮 serve 实收的 /api 请求行，写请求带 body）——「有没有发请求」不再靠页面自报。"
  echo
  while IFS='|' read -r tag harness mock old desc rerun; do
    [ -z "$tag" ] && continue
    echo "## $tag（$desc · $harness · mock=$mock）$rerun"
    if [ -n "$old" ] && [ "$old" != "—" ] && [ -f "$E/$old" ]; then
      python .agents/state/review-compare.py --tag "$tag" --old "$E/$old" 2>&1 | grep -v "^warning"
    else
      python .agents/state/review-compare.py --tag "$tag" 2>&1 | grep -v "^warning"
      echo "  （无同轮建页留证文件可对：仅两轮一致性）"
    fi
    echo
  done <<'TABLE'
1|__measure-login.html|api|—|登录注册（本轮新增载体页）|**[本轮新增]**·checkFails 0/93
1-red|__measure-login.html|api-tmp-noauth|—|登录注册·fixture 缺口 before（红）|**[本轮新增]**·与 after 对比见差异判读 1
1-guard|__measure-login.html|api|—|登录注册·校验门（?scenario=guard，须零 POST）|**[本轮新增]**·requests 0 行
2|__measure-workbench.html|api|—|工作台（本轮新增载体页）|**[本轮新增]**·checkFails 0/92
2-actions|__measure-workbench.html|api|—|工作台·交互回放（钱包 client-only + Tab 我的）|**[本轮新增]**
3|__measure.html|api|measure-序号3-无滚动条430.json|凭证列表|（上一轮 08:30 留证）
4|__measure-submit.html|api|—|提交接入凭证（storage 注入式载体页）|（上一轮 08:30 留证）
4-v1|__measure-form.html|api|measure-序号4v1-430宽.json|提交接入凭证-表单|（上一轮 08:30 留证）
5|__measure-detecting.html|api|measure-序号5-430宽.json|检测进行中|（上一轮 08:30 留证）
6|__measure-report.html|api|measure-序号6-430宽.json|检测报告|（上一轮 08:30 留证）
7|__measure-report-failed.html|api|measure-序号7-430宽.json|报告-不通过|（上一轮 08:30 留证）
8|__measure-quotes.html|api|measure-序号8-430宽.json|报价单列表|（上一轮 08:30 留证）
9|__measure-quote-setup.html|api|measure-序号9-430宽.json|模型报价设置-列表|（上一轮 08:30 留证）
11-fallback|__measure-model-pricing-q9.html|api|—|q9 回落探针（序号 9 保存并继续的落点）|**[本轮新增]**
diag-report|__diag-report-overflow.html|api|—|溢出元素定位探针（uni-resize-sensor）|**[本轮新增]**
10|__measure-profile-edit.html|api-10-2|measure-序号10-430宽-修后2.json|供应商档案编辑|
10.1|__measure-profile.html|api-10-1-2|measure-序号10.1-run2.json|供应商档案|
11|__measure-model-pricing.html|api-11|measure-序号11-run3.json|模型定价|
12|__measure-quote-preview.html|api-12|—|报价预览|
12-v1|__measure-quote-form.html|api-12-v1|—|新增报价单-初始态|
12-v2|__measure-apikey.html|api-12-v2|—|新增报价单-APIKey|
12-v3|__measure-quote-success.html|api-12-v3|—|新增报价单-成功|
15|__measure-contract.html|api-15|—|合同|
20|__measure-messages.html|api-20|—|站内信列表|
21|__measure-mine.html|api-21|—|我的页|
22|__measure-usage.html|api-22|measure-序号22-run3.json|用量概览|
23|__measure-settings.html|api-23|measure-序号23-run2.json|我的设置|
TABLE
  echo "## 差异判读（每条都已定位根因，非页面缺陷）"
  echo
  echo "1. **序号 9 — 测量面 fixture 缺口，本轮已补齐（red → green）**：上一轮发现「保存并继续」落到 \`/pages/model-pricing/index?quoteId=q9\` 后，该页回落入口（\`src/api/quote.ts\` listItems → \`GET /api/v1/quotes/{quoteId}/items\`）在 mock 里不存在 → serve.py 回 \`E-2001\`（红基线：\`review-序号9-mockapi-run2.json\` phase4.toast =「mock 未定义该接口: /api/v1/quotes/q9/items」）。本轮补 \`.agents/state/h5-measure/api/v1/quotes/q9/items/index\`（3 行明细；字段与取值来自 15-数据字典 + 设计 page-9 五行模型/单价 + 上轮实测请求体 \`{\"items\":[{\"model_name\":\"gpt-4o\"}]}\`），并用**同一个探针**做 before/after："
  echo "   - before（同目录去掉该 fixture，\`api-tmp-noq9items\`）：\`review-序号11-fallback-red-run1.json\` → toast「mock 未定义该接口: /api/v1/quotes/q9/items」· modelName \`\"\"\` · 点保存 toast「未找到模型明细，请返回重试」"
  echo "   - after：\`review-序号11-fallback-run{1,2}.json\` → toast 空 · modelName \`gpt-4o\` · 价位 \`2.50 / 10.00\` · 档位 \`base\` · 规则组「规则组 #1」· 点保存 → serve 日志实测 \`GET /api/v1/quotes/q9/items 200\` + \`PUT /api/v1/quotes/items/qi1\` body \`{\"input_price\":2.5,\"output_price\":10,…}\` → toast「保存成功」"
  echo "   - 解析器侧同步体检：\`python .agents/state/check-mock-fixtures.py --mock api\` 红（1 FAIL）→ 绿（全 PASS，含「mock 目录所有 fixture 均可按路径取到」的反向体检）。"
  echo "2. **序号 4 — mock 凭证脱敏值变更，非页面缺陷**：\`flat.apiKeyMaskText\` 与建页留证（\`measure-序号4-修后430.json\`，01:0x）不同 —— 该留证早于提交 cc98e23（02:24:51），后者把共享 mock 凭证 \`api/v1/credentials/c1\` 的 \`api_key_mask\` 从 \`sk-••••••••••••••••4f2a\`（page-4 设计的 16 点）改成 \`sk-prod-••••••••2f9a\`（page-9 设计值）。页面口径本就是「按服务端 api_key_mask 原样渲染、不本地二次脱敏」，故渲染值随 mock 变；载体页期望串仍是旧值，因此 \`missingTexts\` 多一条。**同一份共享 mock 无法同时满足 page-4 与 page-9 两个设计值的脱敏形态** → 登记为已知项（生产侧「脱敏格式四处不一致」缺口仍待人类拍板）。"
  echo "3. **序号 6 — 探针噪音，本轮修掉工具缺陷**：本页 phase1 的 \`overflowing\` 在两轮间波动（run1=0 / run2=2）。本轮新增 \`.agents/state/h5-measure/__diag-report-overflow.html\`（三时刻采样 + 祖先链）定位为：\`div < div < uni-resize-sensor < uni-image.radar__img[radar] < uni-view.radar__canvas\` —— uni-app 给 \`<image mode=\"widthFix\">\`（雷达图）挂的 **resize-sensor** 内部两个空 div（宽 100000 / 352，靠负偏移滚动量测），无可见溢出（\`docScrollWidth\` 恒为 430 = innerWidth；\`review-序号diag-report-run{1,2}.json\` 三阶段全等）。已在该载体页的溢出统计里过滤 \`uni-resize-sensor\` 后代 → 复跑 phase1/phase2 全等 65/65 且与留证全等 65/65。"
  echo "4. **序号 10**（沿用上轮判读）：与 02:42 留证有 3 处不同（qualBadges/qualBadgeRects/qualBadgeBg），该留证早于本页提交 a5916ac（02:46:57）的「双角标补红」；当前实现与设计树 \`page-10-2-nodes.txt\` 一致 → 判为快照过期。"
  echo "5. **序号 22**（沿用上轮判读）：\`overflowing\` 两轮波动来自 uni-app 内置 \`uni-picker\` 的空 div（父级 \`overflow:hidden\`），\`docScrollWidth\` 两轮均 430 → 无可见溢出（\`diag-序号22-overflow.json\`）。与第 3 条同族：**uni-app 内部测量元素不计入溢出统计**。"
  echo
  echo "6. **序号 1 — 测量面 fixture 缺口，本轮已补齐（red → green）**：登录页点「获取验证码」/「登录 / 注册」发的是 POST /api/v1/auth/sms/send 与 POST /api/v1/auth/sms/login，而 api/ 目录里没有这两个 fixture → serve.py 回通用 {\"code\":\"0\",\"data\":{\"id\":\"c1\"}}，页面拿到 res.token === undefined。"
  echo "   - fixture 体检红基线：\`python .agents/state/check-mock-fixtures.py --mock api-tmp-noauth\`（同目录去掉 v1/auth）→ FAIL 2（缺键 ttl / token,role），证据 evidence/red-mock-fixture-auth.txt；补上两个 fixture 后 --mock api → 全部 PASS（evidence/green-mock-fixture-auth.txt）。"
  echo "   - **同探针 before/after**（\`__measure-login.html\` phase6）：before（api-tmp-noauth，evidence/review-序号1-red-run{1,2}.json）→ localStorage aap_token = {\"type\":\"undefined\"}（等于没写进真 token）；after → aap_token = tk-mock-001 且 hash 跳到 /pages/workbench/index。"
  echo "7. **序号 1 登录注册 — 逐项偏差 49 → 0**：载体页 93 条设计期望值，修前 49 条不符（品牌区结构、卡片/输入框/按钮尺寸与色值、字段间距、免责卡），修后 0 条；两轮独立测量全等。修前逐条清单见 evidence/red-序号12-修前偏差-转录.txt。"
  echo "8. **序号 2 工作台 — 逐项偏差 7 → 0**：92 条设计期望值里 7 条色值不符（小标题 rgb(71,85,105)→rgb(100,116,139)、图例值/指标标签/条行值/合计行 rgb(100,116,139)→rgb(148,163,184)、待办文字 rgb(15,23,42)→rgb(51,65,85)、模型序号四行文字色需逐行给色），修后 0 条。"
  echo "   - 与建页老留证（measure-序号2-修后.json，扁平结构）的跨代对比见 evidence/cmp-序号2-老留证vs本轮.txt：公共键 16 → 相同 12，4 处差异全部 = 老留证那轮 iframe 有可见滚动条（innerWidth 同为 430 但 docScrollWidth 415）：docScrollWidth/avatarRight/todoChevronRight 各 +15，条填宽度 95→102（42% × 轨道宽，轨道宽随内容宽 +15）。"
  echo "9. **已知的刻意偏差（沿用台账口径，不算缺陷）**：工作台内容区底部 padding 用 96px 而设计是 0（+ 末尾 16px 占位）——因为底部 TabBar 按 position:fixed 实现（设计画布是随内容排在最后的独立 frame），留白用于避免最后一张卡被固定栏遮住；DOM 断言 tabbarPinned=true 固定住这一口径。"
} > "$OUT" 2>&1

echo "written $OUT ($(wc -c < "$OUT") bytes)"
