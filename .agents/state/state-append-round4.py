#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本轮收尾：把序号 4 的小结插到状态文件 §4 顶部，并把租约释放为 free。

用法: python .agents/state/state-append-round4.py
"""
import io
import re

PATH = ".agents/state/aap-tdd-state.md"
MARK = u"\U0001F7E2 本轮（2026-09-16 00:10~00:24"

BLOCK = u"""🟢 本轮（2026-09-16 00:25~00:47，租约 aap-tdd-run-20260916-0025 → 已释放）· **类型门禁修复 + 序号 4「提交接入凭证 2」收口**：
- **先修类型门禁（独立提交 `62b61d2`）**：上一轮记的 `TS5070` 根因是 `typescript 4.9.5` 撞上 `@vue/tsconfig 0.5.1` 的 TS5 语义
  （`moduleResolution: bundler`）→ vue-tsc 一条真实错误都报不出来。修法：tsconfig 显式 `moduleResolution: node`；
  随之暴露的 `http.ts` 两条真错误按 `uni.request` 类型对齐（method 联合不含 PATCH；`res.data` 经 unknown 转换）。
  红/绿留证 `evidence/typecheck-red-ts5070.txt`、`evidence/typecheck-green-序号0-类型门禁.txt`（exit 2 → exit 0，`npm test` 129/129 无回归）。
  **该坑与修法已写进 `.agents/skills/dev/SKILL.md` §6：后续每页提交前都要跑 `npm run type-check`**。
- **Calicat 侧**：设计类工具照旧要先 `cmd /c start "" <design-url>` 拉起编辑器；page-4-2 设计树（97 图层）+ 截图已抓
  （`interaction.json` 仍为「不存在图层交互数据」→ 交互真源退 PRD + 画布 30 页清单）。
- **TDD（4 条红基线 → 各自到绿）**：①模型切片 `Failed to resolve import`；②接口切片 7 条 `credentialApi.xxx is not a function`；
  ③页面切片 `Failed to resolve import`；④**由 DOM 数字抓出真缺陷后补的红断言**——脱敏值 34px 高（= 两行）。
  实现：`src/utils/credential-form-model.ts`、`src/api/credential.ts`（+detail/save/precheck）、
  `src/pages/credential-submit/index.vue`、`pages.json` 路由、tokens 4 个新色值。绿 **187/187 连跑两轮一致**。
- **本轮抓出并修掉的真缺陷**：脱敏框里 `.input-box__value{flex:1}` 与 `.input-box__spacer{flex:1}` 争空间 →
  脱敏值只拿到 143px 换行（高 34px）；去掉 spacer + `white-space:nowrap` 后 **高 17px 单行、宽 286px**（DOM 数字前后对比留证）。
  另修 2px：`.submit-bar__ghost` 加 `box-sizing:border-box`，固定操作条总高回到设计的 84px（12+48+24）。
- **客观证据链**：`build:mp-weixin` 产出 `dist/build/mp-weixin/pages/credential-submit/{js,json,wxml,wxss}`；
  430 宽 iframe + 无头 Chrome DOM 实测 `evidence/measure-序号4-修后430.json`：`innerWidth 430` · `docScrollWidth 430` · 溢出 `0` ·
  `bar h84 barPinned true` · `atBottom.lastCardFullyAboveBar true` · `checkedCount 3` · `modelRowCount 5` · `vendorGroupCount 2` ·
  `已选 3 个` · 卡片 `x16 w398` · 输入框高 `46` · 勾选框 `18×18` · 色值 `已配置 #ECFDF5/#15803D`、安全提示 `#FFFBEB/#92400E`、主色 `#2563EB`；
  像素墨迹核验（`png-crop` + `png-ink`）标题/脱敏行/底部按钮右留白 24/54/16 均未触边；文案缺失 `[]`（仅剩两个 `<input>` 值 ——
  innerText 不含 input.value 的既知假象，已由 aliasValue/baseUrlValue 单独断言）。
  截图 `logs/screenshots/20260916-0039-序号04-提交接入凭证-h5-430宽.png`。
- **工具修复**：`gen-ledger.py` 之前只看 `interaction.json` 是否存在 → 把 page-4-2 记成「交互已抓 是」（其实一个字都没有）。
  已改为**读文件内容判定**（命中「不存在图层交互数据」即记「否」），并把截图列改为优先取 `screenshot.json` 里的 COS URL；
  修后台账显示「交互已抓 **0/22**」——这是事实，也是「交互真源缺失」这条长期缺口的量化体现。
- **平台坑（新，已写进 `.agents/skills/dev/SKILL.md` §4.1）**：①`npm run build:h5` 会**清空** `dist/build/h5` →
  `__measure*.html` 载体页必须在每次 build:h5 之后重新拷贝（否则 404，Chrome 只回 404 页，取数脚本会静默读到上一轮 JSON：**先看 dump 文件字节数**）；
  ②无头 Chrome 复用同一 `--user-data-dir` 可能不产出 dump → 每次换新目录；③uni-app H5 把 `<input>` 渲染成 `<uni-input>` 包装元素，取数要读内层原生 `input.value`；
  ④`/api/v1/credentials/{id}` 这类「同名文件与子路径共存」用静态文件 mock 无解 → 新增 `.agents/state/h5-measure/serve.py`（静态 + JSON mock 一体，先目录后文件）。
- ⚠️ 待人类确认（不阻塞本轮，全部写进台账序号 4 备注）：①18-API 卡片只列路径未列方法 → `/credentials/{id}` 的 GET/PUT 为 REST 语义推断；
  ②模型清单候选目录（未勾选的 gpt-3.5-turbo/claude-3-opus 从哪来）在 18-API 无供应商侧目录接口 → 前端按响应字段 `model_catalog` 消费（missing-prd）；
  ③「凭证名称」= `aap_credential.alias`，但 18-API 无字段级 schema；④脱敏格式四处不一致（设计 16 圆点 / R-05 前4***后4 / 15-数据字典 `sk-a***5678` / 18-API `sk-****abcd`）；
  ⑤「已配置」不在 CredentialStatus 枚举内；⑥本页入口未确认（画布「查看」列只有报告链接）→ 按 id 入参实现（query 优先、storage `aap_credential_id` 兜底）；
  ⑦系统字体圆点墨迹小于设计稿字体（度量差异）；⑧「建议 6–24 字」为设计原文的「建议」→ 不拦截提交。

⏳ 下一步（下一轮）：台账序号 **4-v1「接入凭证-表单」（page-24，`/pages/credential-submit/form`）**——与本轮同族的「新建」空态表单，
按 §2 八步走；可直接复用 `credential-form-model.ts` 与 `.agents/state/h5-measure/serve.py`（记得 build:h5 之后重拷载体页）。
（序号 1/2/3/4 均已实现并留证，状态为「部分」是因为登记了等人类拍板的缺口，不要重复回炉。）

"""

text = io.open(PATH, encoding="utf-8").read()
if u"aap-tdd-run-20260916-0025" in text and u"序号 4「提交接入凭证 2」收口" in text:
    print("already appended")
else:
    if MARK not in text:
        raise SystemExit("marker not found: %s" % MARK)
    text = text.replace(MARK, BLOCK + MARK, 1)
text = re.sub(u"(?m)^LEASE:.*$", u"LEASE: free", text, count=1)
io.open(PATH, "w", encoding="utf-8").write(text)
print(u"\n".join(text.splitlines()[:2]))
print("bytes:", len(text.encode("utf-8")))
