# 逐页复核 · 430 宽 iframe DOM 实测（两轮独立测量 + 与建页留证对比）

- 轮次: aap-tdd-run-20260916-0820 · 生成时间 2026-09-16 08:28:00
- 测量面: `npm run build:h5` 产物 + `.agents/state/h5-measure/serve.py`（含 /api/v1 mock）+ 无头 Chrome 430x900 iframe
- 一次命令: `bash .agents/state/review-measure.sh <序号> <载体页> <mock目录> <端口>` → `python .agents/state/review-compare.py --tag <序号> --old <建页留证>`
- 标记: **[本轮复跑]** = 本轮的 review-序号*-run{1,2}.json 已重写；其余行为上一轮留证（文件未变，仍可复现判读）。
- 覆盖: 台账 22 行里 20 行有 `__measure-*.html` 载体页；序号 1（登录注册）/ 2（工作台）无载体页 → 待补（队列第 6 项）。

## 3（凭证列表 · __measure.html · mock=api）**[本轮复跑]**
序号 3 · phases=atBottom,card,flat,submitBtn
  atBottom run1vsrun2: 全等 4 / 不一致 0
  atBottom 留证vs本轮: 全等 4 / 不一致 0
  card     run1vsrun2: 全等 5 / 不一致 0
  card     留证vs本轮: 全等 5 / 不一致 0
  flat     run1vsrun2: 全等 29 / 不一致 0
  flat     留证vs本轮: 全等 29 / 不一致 0
  submitBtn run1vsrun2: 全等 5 / 不一致 0
  submitBtn 留证vs本轮: 全等 5 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 4（提交接入凭证（storage 注入式载体页） · __measure-submit.html · mock=api）**[本轮复跑]**
序号 4 · phases=apikeyMaskRect,atBottom,bar,firstCard,firstCheckBox,firstInputBox,firstModelRow,firstVendor,flat,ghostBtn,submitBtnRect,topbarRect
  apikeyMaskRect run1vsrun2: 全等 6 / 不一致 0
  atBottom run1vsrun2: 全等 3 / 不一致 0
  bar      run1vsrun2: 全等 6 / 不一致 0
  firstCard run1vsrun2: 全等 6 / 不一致 0
  firstCheckBox run1vsrun2: 全等 6 / 不一致 0
  firstInputBox run1vsrun2: 全等 6 / 不一致 0
  firstModelRow run1vsrun2: 全等 6 / 不一致 0
  firstVendor run1vsrun2: 全等 6 / 不一致 0
  flat     run1vsrun2: 全等 47 / 不一致 0
  ghostBtn run1vsrun2: 全等 6 / 不一致 0
  submitBtnRect run1vsrun2: 全等 6 / 不一致 0
  topbarRect run1vsrun2: 全等 6 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 4-v1（提交接入凭证-表单 · __measure-form.html · mock=api）**[本轮复跑]**
序号 4-v1 · phases=empty,filled
  empty    run1vsrun2: 全等 60 / 不一致 0
  empty    留证vs本轮: 全等 60 / 不一致 0
  filled   run1vsrun2: 全等 60 / 不一致 0
  filled   留证vs本轮: 全等 60 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 5（检测进行中 · __measure-detecting.html · mock=api）**[本轮复跑]**
序号 5 · phases=phase1,phase2
  phase1   run1vsrun2: 全等 41 / 不一致 0
  phase1   留证vs本轮: 全等 41 / 不一致 0
  phase2   run1vsrun2: 全等 41 / 不一致 0
  phase2   留证vs本轮: 全等 41 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 6（检测报告 · __measure-report.html · mock=api）**[本轮复跑]**
序号 6 · phases=phase1,phase2
  phase1   run1vsrun2: 全等 65 / 不一致 0
  phase1   留证vs本轮: 全等 65 / 不一致 0
  phase2   run1vsrun2: 全等 65 / 不一致 0
  phase2   留证vs本轮: 全等 65 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 7（报告-不通过 · __measure-report-failed.html · mock=api）**[本轮复跑]**
序号 7 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 75 / 不一致 0
  phase1   留证vs本轮: 全等 75 / 不一致 0
  phase2   run1vsrun2: 全等 75 / 不一致 0
  phase2   留证vs本轮: 全等 75 / 不一致 0
  phase3   run1vsrun2: 全等 3 / 不一致 0
  phase3   留证vs本轮: 全等 3 / 不一致 0
  phase4   run1vsrun2: 全等 5 / 不一致 0
  phase4   留证vs本轮: 全等 5 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 8（报价单列表 · __measure-quotes.html · mock=api）**[本轮复跑]**
序号 8 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 61 / 不一致 0
  phase1   留证vs本轮: 全等 61 / 不一致 0
  phase2   run1vsrun2: 全等 61 / 不一致 0
  phase2   留证vs本轮: 全等 61 / 不一致 0
  phase3   run1vsrun2: 全等 5 / 不一致 0
  phase3   留证vs本轮: 全等 5 / 不一致 0
  phase4   run1vsrun2: 全等 9 / 不一致 0
  phase4   留证vs本轮: 全等 9 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 9（模型报价设置-列表 · __measure-quote-setup.html · mock=api）**[本轮复跑]**
序号 9 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 79 / 不一致 0
  phase1   留证vs本轮: 全等 79 / 不一致 0
  phase2   run1vsrun2: 全等 79 / 不一致 0
  phase2   留证vs本轮: 全等 79 / 不一致 0
  phase3   run1vsrun2: 全等 7 / 不一致 0
  phase3   留证vs本轮: 全等 7 / 不一致 0
  phase4   run1vsrun2: 全等 3 / 不一致 0
  phase4   留证vs本轮: 全等 2 / 不一致 2 → hash,savedCountText
结论: 两次独立测量一致（留证对比见上）

## 11-fallback（q9 回落探针（序号 9 保存并继续的落点） · __measure-model-pricing-q9.html · mock=api）**[本轮新增]**
序号 11-fallback · phases=phase1,phase2
  phase1   run1vsrun2: 全等 21 / 不一致 0
  phase2   run1vsrun2: 全等 4 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## diag-report（溢出元素定位探针（uni-resize-sensor） · __diag-report-overflow.html · mock=api）**[本轮新增]**
序号 diag-report · phases=phase1,phase2,phase3
  phase1   run1vsrun2: 全等 5 / 不一致 0
  phase2   run1vsrun2: 全等 5 / 不一致 0
  phase3   run1vsrun2: 全等 5 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 10（供应商档案编辑 · __measure-profile-edit.html · mock=api-10-2）
序号 10 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 86 / 不一致 0
  phase1   留证vs本轮: 全等 83 / 不一致 3 → qualBadgeBg,qualBadgeRects,qualBadges
  phase2   run1vsrun2: 全等 7 / 不一致 0
  phase2   留证vs本轮: 全等 7 / 不一致 0
  phase3   run1vsrun2: 全等 6 / 不一致 0
  phase3   留证vs本轮: 全等 6 / 不一致 0
  phase4   run1vsrun2: 全等 10 / 不一致 0
  phase4   留证vs本轮: 全等 10 / 不一致 0
结论: 两次独立测量一致（留证对比见上）

## 10.1（供应商档案 · __measure-profile.html · mock=api-10-1-2）
序号 10.1 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 96 / 不一致 0
  phase1   留证vs本轮: 全等 96 / 不一致 0
  phase2   run1vsrun2: 全等 6 / 不一致 0
  phase2   留证vs本轮: 全等 6 / 不一致 0
  phase3   run1vsrun2: 全等 4 / 不一致 0
  phase3   留证vs本轮: 全等 4 / 不一致 0
  phase4   run1vsrun2: 全等 4 / 不一致 0
  phase4   留证vs本轮: 全等 4 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 11（模型定价 · __measure-model-pricing.html · mock=api-11）
序号 11 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 86 / 不一致 0
  phase1   留证vs本轮: 全等 86 / 不一致 0
  phase2   run1vsrun2: 全等 3 / 不一致 0
  phase2   留证vs本轮: 全等 3 / 不一致 0
  phase3   run1vsrun2: 全等 5 / 不一致 0
  phase3   留证vs本轮: 全等 5 / 不一致 0
  phase4   run1vsrun2: 全等 4 / 不一致 0
  phase4   留证vs本轮: 全等 4 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 12（报价预览 · __measure-quote-preview.html · mock=api-12）
序号 12 · phases=phase1,phase2,phase3
  phase1   run1vsrun2: 全等 63 / 不一致 0
  phase2   run1vsrun2: 全等 7 / 不一致 0
  phase3   run1vsrun2: 全等 4 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 12-v1（新增报价单-初始态 · __measure-quote-form.html · mock=api-12-v1）
序号 12-v1 · phases=phase1,phase2,phase3
  phase1   run1vsrun2: 全等 85 / 不一致 0
  phase2   run1vsrun2: 全等 8 / 不一致 0
  phase3   run1vsrun2: 全等 6 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 12-v2（新增报价单-APIKey · __measure-apikey.html · mock=api-12-v2）
序号 12-v2 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 86 / 不一致 0
  phase2   run1vsrun2: 全等 16 / 不一致 0
  phase3   run1vsrun2: 全等 5 / 不一致 0
  phase4   run1vsrun2: 全等 6 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 12-v3（新增报价单-成功 · __measure-quote-success.html · mock=api-12-v3）
序号 12-v3 · phases=phase1
  phase1   run1vsrun2: 全等 87 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 15（合同 · __measure-contract.html · mock=api-15）
序号 15 · phases=phase1
  phase1   run1vsrun2: 全等 84 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 20（站内信列表 · __measure-messages.html · mock=api-20）
序号 20 · phases=phase1
  phase1   run1vsrun2: 全等 71 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 21（我的页 · __measure-mine.html · mock=api-21）
序号 21 · phases=phase1
  phase1   run1vsrun2: 全等 75 / 不一致 0
结论: 两次独立测量一致（留证对比见上）
  （无同轮建页留证文件可对：仅两轮一致性）

## 22（用量概览 · __measure-usage.html · mock=api-22）
序号 22 · phases=phase1
  phase1   run1vsrun2: 全等 80 / 不一致 1 → overflowing
  phase1   留证vs本轮: 全等 80 / 不一致 1 → overflowing
结论: **存在不一致，需定位**

## 23（我的设置 · __measure-settings.html · mock=api-23）
序号 23 · phases=phase1
  phase1   run1vsrun2: 全等 80 / 不一致 0
  phase1   留证vs本轮: 全等 80 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 差异判读（每条都已定位根因，非页面缺陷）

1. **序号 9 — 测量面 fixture 缺口，本轮已补齐（red → green）**：上一轮发现「保存并继续」落到 `/pages/model-pricing/index?quoteId=q9` 后，该页回落入口（`src/api/quote.ts` listItems → `GET /api/v1/quotes/{quoteId}/items`）在 mock 里不存在 → serve.py 回 `E-2001`（红基线：`review-序号9-mockapi-run2.json` phase4.toast =「mock 未定义该接口: /api/v1/quotes/q9/items」）。本轮补 `.agents/state/h5-measure/api/v1/quotes/q9/items/index`（3 行明细；字段与取值来自 15-数据字典 + 设计 page-9 五行模型/单价 + 上轮实测请求体 `{"items":[{"model_name":"gpt-4o"}]}`），并用**同一个探针**做 before/after：
   - before（同目录去掉该 fixture，`api-tmp-noq9items`）：`review-序号11-fallback-red-run1.json` → toast「mock 未定义该接口: /api/v1/quotes/q9/items」· modelName `""` · 点保存 toast「未找到模型明细，请返回重试」
   - after：`review-序号11-fallback-run{1,2}.json` → toast 空 · modelName `gpt-4o` · 价位 `2.50 / 10.00` · 档位 `base` · 规则组「规则组 #1」· 点保存 → serve 日志实测 `GET /api/v1/quotes/q9/items 200` + `PUT /api/v1/quotes/items/qi1` body `{"input_price":2.5,"output_price":10,…}` → toast「保存成功」
   - 解析器侧同步体检：`python .agents/state/check-mock-fixtures.py --mock api` 红（1 FAIL）→ 绿（全 PASS，含「mock 目录所有 fixture 均可按路径取到」的反向体检）。
2. **序号 4 — mock 凭证脱敏值变更，非页面缺陷**：`flat.apiKeyMaskText` 与建页留证（`measure-序号4-修后430.json`，01:0x）不同 —— 该留证早于提交 cc98e23（02:24:51），后者把共享 mock 凭证 `api/v1/credentials/c1` 的 `api_key_mask` 从 `sk-••••••••••••••••4f2a`（page-4 设计的 16 点）改成 `sk-prod-••••••••2f9a`（page-9 设计值）。页面口径本就是「按服务端 api_key_mask 原样渲染、不本地二次脱敏」，故渲染值随 mock 变；载体页期望串仍是旧值，因此 `missingTexts` 多一条。**同一份共享 mock 无法同时满足 page-4 与 page-9 两个设计值的脱敏形态** → 登记为已知项（生产侧「脱敏格式四处不一致」缺口仍待人类拍板）。
3. **序号 6 — 探针噪音，本轮修掉工具缺陷**：本页 phase1 的 `overflowing` 在两轮间波动（run1=0 / run2=2）。本轮新增 `.agents/state/h5-measure/__diag-report-overflow.html`（三时刻采样 + 祖先链）定位为：`div < div < uni-resize-sensor < uni-image.radar__img[radar] < uni-view.radar__canvas` —— uni-app 给 `<image mode="widthFix">`（雷达图）挂的 **resize-sensor** 内部两个空 div（宽 100000 / 352，靠负偏移滚动量测），无可见溢出（`docScrollWidth` 恒为 430 = innerWidth；`review-序号diag-report-run{1,2}.json` 三阶段全等）。已在该载体页的溢出统计里过滤 `uni-resize-sensor` 后代 → 复跑 phase1/phase2 全等 65/65 且与留证全等 65/65。
4. **序号 10**（沿用上轮判读）：与 02:42 留证有 3 处不同（qualBadges/qualBadgeRects/qualBadgeBg），该留证早于本页提交 a5916ac（02:46:57）的「双角标补红」；当前实现与设计树 `page-10-2-nodes.txt` 一致 → 判为快照过期。
5. **序号 22**（沿用上轮判读）：`overflowing` 两轮波动来自 uni-app 内置 `uni-picker` 的空 div（父级 `overflow:hidden`），`docScrollWidth` 两轮均 430 → 无可见溢出（`diag-序号22-overflow.json`）。与第 3 条同族：**uni-app 内部测量元素不计入溢出统计**。
