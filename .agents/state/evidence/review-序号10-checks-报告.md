# 序号 10 checks 轮报告 · 【档案与凭证】供应商档案编辑（page-10-2 → `/pages/profile-edit/index`）

- 轮次 id：`aap-tdd-run-20260916-1231`（cron）· 日期 2026-09-16 12:31~13:0x
- 载体页：`.agents/state/h5-measure/__measure-profile-edit.html`（由 355 行旧体例重写为 **430 宽 iframe + 229 条设计期望值 checks**）
- mock：`.agents/state/h5-measure/api-10-2`（fixture 体检 PASS，反向体检「目录下所有 fixture 均可按路径取到」PASS）
- 设计帧：`page-10-2`（layer_id `45f4d7f9-17d7-4f24-b0d0-af81807d0f18`）

## 1. 设计帧重抓（人工指令 C：复核前必须重抓）

编辑器先 `cmd /c start "" https://www.calicat.cn/design/2095515676955668480` 拉起，再

```
python .../calicat_source.py page --url .../design/2095515676955668480 \
  --layer-id 45f4d7f9-17d7-4f24-b0d0-af81807d0f18 --page-id page-10-2 --out "$LOCALAPPDATA/Temp/aap-live"
sha256sum  live/design.json  .calicat/raw/pages/page-10-2/design.json
→ 46e9cfee142a223b4a9d1f0c90a4095bce31d186a8aaa6b589ed90ce76a9fd22（两边逐字节相同）
```

**无漂移**：画布当前状态 = 实现所依据的那份，本轮不需要按新帧重做。

## 2. TDD 红 → 绿（本轮主交付）

| 轮 | 命令 | 结果 |
|---|---|---|
| 红基线 | `git stash push -- aap-client/src/pages/profile-edit/index.vue aap-client/tests/pages/profile-edit.spec.ts` → `build:h5` → `review-measure.sh 10-checks-red …` | `checkCount 229 · checkFailCount **36**` · `docH 1409`（两次独立测量 27/27 字段全等） |
| 绿 | `git stash pop` → `build:h5` → `review-measure.sh 10-checks …` | `checkCount 229 · checkFailCount **0**` · `docH 1409`（两次独立测量 28/28 字段全等） |
| 复位复测 | 同一份源码再跑 `10-checks-final` | 与首轮绿**逐字段相同**（27/27 全等，不一致 0）→ stash 循环干净 |

转录用例：`evidence/red-序号10-checks-设计期望值偏差.txt`（36 条失败清单）· `evidence/green-序号10-checks-设计期望值.txt`（0 条）·
两轮一致性 `evidence/review-序号10-checks-run{1,2}.json`（`cmp-measure-runs.py … phase1`）。

单测红→绿：`tests/pages/profile-edit.spec.ts` 新增「尾部图标只出现在已上传行」结构用例 →
红 `1 failed | 25 passed`（`expected 1 to be +0`：空态行多一枚 `.icon-tap`）→ 绿 `26 passed`。

## 3. 修掉的 9 类设计偏差（`aap-client/src/pages/profile-edit/index.vue`）

| # | 偏差 | 依据 |
|---|---|---|
| 1 | **卡头图标盒 18×18 → 20×27**（三张卡都是），形状移入 `::before` | design `dd2e0031`/`9d28f082`/`e77c2b79` = remixicon `w=20`、`fs=18` → 字形行框 18×1.5 = 27 |
| 2 | 连带 **卡标题左界 60 → 62**（36 + 图标 20 + 设计 container padding-left 6） | design `2ea26a8a`/`66c204cb`/`39b5c9ad` |
| 3 | **输入框/半栏框描边 `border` → `box-shadow: 0 0 0 1px`**：内容左界 13 → **12**、内容宽 332 → **334**（半栏同样） | design `59b598a7` 等 `stroke{align:center,thickness:1,rgba(226,232,240,1)}` + `padding[0,12,0,12]`（Figma 中心描边不占布局） |
| 4 | **地区框 chevron 盒 11×11 → 20×27**，x 186/371 → **176/362**，色改由 `currentColor` 承载 | design `fbc191db`/`1556519d` = remixicon `w=20 fs=18`，fill `rgba(148,163,184,1)` |
| 5 | **「已上传」角标勾盒 9×9 → 13×16**（宽 13 = design 声明），角标宽 56 → **62**、右边 255 → **263** | design `acdea136` = `w=13 fs=11`、`22a50a57` padding 0/8 + 勾 + container padding-left 2 + 文字 31 → 62 |
| 6 | **资质行尾部两枚图标间距 0 → 8**：删除盒 354..374 → **346..366**（查看盒保持 374..394） | design `609c6cb5` `padding-left 8`；PNG y=1136/1142 实测 删除 ink 347..363 · 查看 ink 380..386 |
| 7 | **删掉空态行的「上传」chevron**（设计里授权书/选传两行**没有**尾部图标） | PNG y=1192~1210 / 1254~1266 在 x 370..415 无 ink；design `资质-授权书`/`选传资质` children 只有 [图标][信息容器] |
| 8 | **「保存草稿」按钮描边 `border` → ring**（`rgba(203,213,225,1)` 中心描边） | design `2908e264` `stroke{align:center,thickness:1}` |
| 9 | **保存按钮内容按设计组合**：文案盒 30 → **91 宽且左对齐**（ink 277 → **240**）+ 箭头盒 14×14 → **22×30**（x 309 → **335**） | design `0cd71f4f` children = [文本 `width 91 textAlign left`][container padding-left 4][remixicon `w=22 fs=20`] → 组合 117 居中；PNG y=1360 实测文案 ink 240..270 · 箭头 ink ~345..352 |

连带：`.glyph--check`（USCC 勾）/`.glyph--check-sm`/`.glyph--chevron`/`.glyph--arrow-white`/卡头三图标 统一改为
**「盒 = 设计图层尺寸、形状入 `::before`、颜色用 `color` + `currentColor`」**（D5 仍为 CSS 占位），使颜色也能被探针客观读到。

**未改（有意保留，附依据）**：
- `.glyph--doc`（资质缩略图内图标）：设计为 remixicon 文档字形（ink ≈18×20），实现是 24×24 实心方块占位；缩略图盒 47×46 固定、图标居中 → **不影响任何布局量**，属 D5 占位形状差异（等正式图标资产整批替换）。
- `.qual-row__info` 的 `padding: 0 12px`：设计 container `623e8cdd` 只声明 `padding-left 12`；该行内没有右对齐内容 → 无可观测差异，不动（避免无意义 churn）。
- `.glyph--back` / `.glyph--trash`：`.icon-btn`(26×36) 与 `.icon-tap`(20×46) 两个**盒**已与设计一致，形状为 D5 占位。

## 4. 交互相（有牙齿）

`?scenario=actions` 两轮逐字节相同（`evidence/review-序号10-actions-run{1,2}.json`）：

| 相 | 实测 |
|---|---|
| phase2 | chip 原厂 → 渠道商：`[true,false,false] → [false,true,false]`；简介输入 5 字 → 计数 `5/200`（与输入长度一致） |
| phase3 | 清空企业名称 + 点保存 → toast **「请输入企业名称」**（校验拦截）；点保存草稿 → toast「已存为草稿」+ `localStorage.aap_provider_profile_draft` 写入草稿 JSON |
| phase4 | 恢复企业名称 → 保存：serve 实收 **`PUT /api/v1/provider/profile`**（body 12 字段，含 `website:""`）→ toast「保存成功」→ 完整度 `72% → 78%`；删资质 → **uni-modal**「删除资质文件 / 确认删除该资质文件？删除后不可恢复。 / 取消 · 确定」→ 确定 → `DELETE /api/v1/provider/qualifications/q1` → toast「已删除」→ 重新 `GET` 列表 |

`?scenario=guard`（只跑「必填被清空 + 点保存」）两轮 serve 实收 **仅 2 行 GET、0 行写请求**
（`evidence/requests-序号10-guard-run{1,2}.txt`）→ **校验门不发请求**由服务端日志直接证明。
纯测量轮两轮各 2 行（`GET /provider/profile` + `GET /provider/qualifications`）。

## 5. 像素对账（实现截图 vs 设计 PNG，±3）

```
python .agents/state/cmp-bands-6-design-vs-impl.py \
  .agents/state/design-shots/page-10-2.png \
  ".agents/state/evidence/20260916-序10-供应商档案编辑-checks轮-h5-430宽.png" out.txt 3
→ 内容列 x=36..394：设计 37 个带起点 / 实现 37 个，命中 37 · **未命中 0**（位移中位 0，min −2 max +2）
→ 明细列 x=194..356：设计 19 / 实现 21，命中 19 · **未命中 0**
→ **结构带未命中合计 0（命中 56）**
```

整页 `docScrollHeight 1409` = 设计帧高 1409（无滚动、无 TabBar）。430 宽截图：
`evidence/20260916-序10-供应商档案编辑-checks轮-h5-430宽.png`（同件入 `logs/screenshots/`）。

## 6. 质量门

- `npx vitest run` **1173/1173 · 72 files 连跑两轮全绿**（12:44:38 / 12:45:13；本轮新增 1 例）
- `npm run type-check` exit 0
- `npm run build:mp-weixin` DONE → `dist/build/mp-weixin/pages/profile-edit/index.{js,json,wxml,wxss}` 齐备，`app.json` 已注册
- `npm run build:h5` DONE（430 宽 DOM 实测用）
- `check-mock-fixtures.py --mock api-10-2`：反向体检 PASS（列表里的 7 条 FAIL 是其它页共享 fixture 的检查项，与 `api-10-2` 无关）

## 7. 本页定标与探针口径（写进状态文件 §5）

- **remixicon 字形行框 = fontSize × 1.5**：本页三处独立验证（顶部栏 24→36 决定内容行 36、卡头 18→27 决定头部行 27、已上传勾 11→16.5→16）。
- **文本行框**：设计**显式 height 优先**（标签 18 · 文件名/提示 16 · 简介文本 40）；`lineHeight: 1.2` 是 Figma 文本属性、不决定行框（本页标题 17px 的 ink 落在内容行 48..84 中央，两种取值都成立）。
- **字段步进**：标签 18 + 8 + 框 44 + 16 = **86**，但**类型 chip 行只有 40 高** → 该组步进 82（其后恢复 86）。第一轮探针按统一 86 写 want，把这段量成 4px 偏差 —— **want 错误，非页面偏差**（PNG 实测框位 196/282/368/450/536/622 逐项支持实现）。
- **Figma 中心描边**：`border` 会占布局（内容左界 +1、内容宽 −2）→ 一律 `box-shadow: 0 0 0 <thickness>`；**未上传缩略图的 46 宽盒同理**（设计 ink 47 = 46 + 中心描边）。
- **`chkList` 只做数值比较**：字符串数组走 `Math.abs(NaN)` 会**静默放过** → 本轮补 `chkStrs()`；横排元素的间距不能用 `gapBetween()`（纵向定义，横排得负值）→ 补 `hgap()`。
- **`splitSel` 只认第一个 `@@`**：`A@@0 B@@1` 这种嵌套会在 `querySelector` 处抛「不是合法选择器」→ 需要「第几个匹配」时用全局序（本页 `.field__box--half@@0/@@1`、`.icon-tap@@0/@@1`）。
- **`collect()` 里的 `textOf(sel)` 用闭包 `doc`**，外层 `load` 回调不能借用（本轮 phase2/phase4 因此静默不 sink）→ 载体页另给顶层 `textIn(sel)`。

## 8. 遗留 / 需要拍板

- 无新增待拍板项。台账行原有的 15 条 `missing-prd` 备注不变（接口方法为 REST 语义推断、字段名按 `docs/api/接口字段级schema.md` 约定）。
- 下一轮开工：**序号 10.1**（`page-10-1-2`「【档案与凭证】供应商档案 2」→ `/pages/profile/index`，载体页 `__measure-profile.html`，mock 目录 `api-10-1-2`）。
