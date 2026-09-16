# 逐页复核 · 430 宽 iframe DOM 实测（两轮独立测量 + 与建页留证对比）

- 轮次: aap-tdd-run-20260916-0805 · 生成时间 2026-09-16 08:15:12
- 测量面: `npm run build:h5` 产物 + `.agents/state/h5-measure/serve.py`（含 /api/v1 mock）+ 无头 Chrome 430x900 iframe
- 一次命令: `bash .agents/state/review-measure.sh <序号> <载体页> <mock目录> <端口>` → `python .agents/state/review-compare.py --tag <序号> --old <建页留证>`
- 覆盖: 台账 22 行里 20 行有 `__measure-*.html` 载体页并已复跑；序号 1（登录注册）/ 2（工作台）无载体页 → 本轮以「产物 + 建页留证」复核，下轮补载体页。

## 3（凭证列表 · __measure.html · mock=api）
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

## 4（提交接入凭证（storage 注入式载体页） · __measure-submit.html · mock=api）
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

## 4-v1（提交接入凭证-表单 · __measure-form.html · mock=api）
序号 4-v1 · phases=empty,filled
  empty    run1vsrun2: 全等 60 / 不一致 0
  empty    留证vs本轮: 全等 60 / 不一致 0
  filled   run1vsrun2: 全等 60 / 不一致 0
  filled   留证vs本轮: 全等 60 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 5（检测进行中 · __measure-detecting.html · mock=api）
序号 5 · phases=phase1,phase2
  phase1   run1vsrun2: 全等 41 / 不一致 0
  phase1   留证vs本轮: 全等 41 / 不一致 0
  phase2   run1vsrun2: 全等 41 / 不一致 0
  phase2   留证vs本轮: 全等 41 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 6（检测报告 · __measure-report.html · mock=api）
序号 6 · phases=phase1,phase2
  phase1   run1vsrun2: 全等 65 / 不一致 0
  phase1   留证vs本轮: 全等 65 / 不一致 0
  phase2   run1vsrun2: 全等 65 / 不一致 0
  phase2   留证vs本轮: 全等 65 / 不一致 0
结论: 两次独立测量一致，且与建页留证无漂移

## 7（报告-不通过 · __measure-report-failed.html · mock=api）
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

## 8（报价单列表 · __measure-quotes.html · mock=api）
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

## 9（模型报价设置-列表 · __measure-quote-setup.html · mock=api）
序号 9 · phases=phase1,phase2,phase3,phase4
  phase1   run1vsrun2: 全等 79 / 不一致 0
  phase1   留证vs本轮: 全等 76 / 不一致 3 → missingTexts,subjectCode,subjectValue
  phase2   run1vsrun2: 全等 79 / 不一致 0
  phase2   留证vs本轮: 全等 50 / 不一致 29 → bar,barInner,body,cards,chipLabels,chips,credHint,credMask
  phase3   run1vsrun2: 全等 7 / 不一致 0
  phase3   留证vs本轮: 全等 2 / 不一致 5 → countAfterSelectAll,countAfterToggle,countAfterUnselectAll,statusAfterToggle,toggleClicked
  phase4   run1vsrun2: 全等 4 / 不一致 0
  phase4   留证vs本轮: 全等 2 / 不一致 2 → savedCountText,toast
结论: 两次独立测量一致（留证对比见上）

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

## 未通过一致性判读的三处（均已定位，非页面缺陷）

1. **序号 6**：与 01:26 的 `measure-序号6-430宽-修后.json` 有 3 处不同（radarLabels/radarLabelRects 缺失、radarRect 差 6px）。原因是该留证**早于同轮 01:28 更新的载体页**（旧版没有雷达标签探测项）。与最新留证 `measure-序号6-430宽.json` 全等 65/65 → 判为探测项演进。docScrollHeight 两版一致（4886）＝页面高度未变。
2. **序号 10**：与 02:42 留证有 3 处不同（qualBadges/qualBadgeRects/qualBadgeBg）。原因是该留证**早于本页提交 a5916ac（02:46:57）**，即「双角标补红」修复前的快照；当前实现的 3 个独立角标（必传 #FEF2F2/#B91C1C · 已上传 #ECFDF5/#15803D · 条件必传 #FFF7ED/#B45309）与设计树 `page-10-2-nodes.txt` 第 130/133/151 行逐字段一致 → 以设计为准，判为快照过期。
3. **序号 9**：与 02:22 留证有 phase4 差异（toast 由「保存成功」变成服务端回读文案「mock 未定义该接口: /api/v1/quotes/q9/items」，hash 由停在 quote-models 变成跳到 `model-pricing?quoteId=q9`）。原因同上：留证早于本页提交 cc98e23（02:24:51）。新 hash 指向设计序号 11「模型定价」，符合保存后的设计流向；toast 文案来自测量面 mock 缺 GET `/quotes/q9/items` fixture（页面按 `src/api/quote.ts:90` 的回落入口取明细行）→ 判为**测量面 fixture 缺口**，下轮补 fixture 并复跑（补后需回跑所有用 `api` 目录的页面）。
4. **序号 22**：`overflowing` 字段两轮不同（同一元素 left 在 -99606 / 36 之间跳）。该元素是 uni-app 内置 `<uni-picker>` 的空 div，父级 `overflow:hidden`（见 `.agents/state/evidence/diag-序号22-overflow.json`），`docScrollWidth` 两轮均为 430 = innerWidth → **无可见溢出**，载体页探测噪音。
