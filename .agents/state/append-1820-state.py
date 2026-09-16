# -*- coding: utf-8 -*-
"""回写状态文件（STATUS 行 · 本轮小结 · §5.18 工具与口径 · 释放租约）。"""
import io
import re
import sys

PATH = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-tdd-state.md'
src = io.open(PATH, encoding='utf-8', newline='').read()
src_lf = src.replace('\r\n', '\n')

STATUS = ('STATUS: RUNNING — 报价端小程序 22 页已全部实现（台账待取件 0）。当前在办：'
          '①新维度「设计文本叶子 ↔ 实现 DOM」全量审计 ✅（22/22 页 · 1131 设计叶子 · 匹配 970 · 待判读 class 172 · 序号 8 的四类经 PNG 判定非偏差已登记 textleaf-accept.json）'
          '②序号 1 登录页「字重 10 处 + 行盒 10 处」修正 ✅（字重红 10/103 → 绿 0/103 · 行盒红 10/113 → 绿 0/113 · docH 1085→1098 · PNG 品牌区逐带与设计相同）'
          '③序号 1 余 16px 残差（首字段前间距 4px + 免责摘要正文应两行 h=40）= 下轮第一件事；其后按 172 条待判读清单逐页推进。'
          '队列 0 挂起（D6）；管理端 8 页范围外。')

SUMMARY = """
- 2026-09-16 18:5x（cron 轮 `aap-tdd-run-20260916-1820`）· **新维度：设计文本叶子 ↔ 实现 DOM 全量审计（22/22 页）+ 序号 1「字重 / 行盒」两步 RED→GREEN（红 10+10 → 绿 0+0 · docH 1085→1098 · PNG 品牌区逐带与设计相同）**：
  ①**审计工具（本轮主交付）**：route 参数化载体页 `__measure-textleaf.html`（**一处代码覆盖全部路由**，不再逐页复制）+ `textleaf-scan.py`
  （逐页用自己的 mock 目录 + **带参路由** + 稳定性收口）+ `textleaf-audit.py`（按**渲染文案**配对设计叶子与 DOM 叶子，比行盒/字号/字重）+ `textleaf-accept.json`（人工核定表）。
  22 页全跑：设计文本叶子 **1131** · 匹配 **970（86%）** · 未渲染 88 · **待判读 class 172** —— 这正是前 22 轮「页面级 checks」没覆盖到的声明值维度，已成为后续轮次队列。
  ②**序号 1（本轮修完的页面）**：载体页新增 `fw.*` 10 条（字重，want = 设计 fontFamily → Bold 700 / SemiBold 600 / Medium 500）与 `be.*` 10 条（行盒，want = 设计**显式 height**）；
  红基线 **10/103** 与 **10/113**（两轮一致）→ 绿 **0/103 · 0/113**；两轮独立测量 phase1 **33/33 字段全等**；`docScrollHeight 1085 → 1098`（+13 = 各盒声明差之和）；
  PNG 色带实测：修前品牌区逐带落后（标题 -1 · 副标题 -5 · 卡片顶 -8）→ 修后 **逐带与设计相同（±0）**。
  ③**序号 8 的四类探针告警经 PNG 判定为非偏差**：卡 **pitch 两侧同为 190**（= 卡高 178 + 间距 12；scan-col x=215 设计白起 157/卡2 347 vs 实现 156/346）
  → 设计**渲染**行盒就是 22.5/19.5/16，缩到 fs×1.2 会破坏像素对齐；登记 `evidence/textleaf-accept-序号8-png-pitch.txt`。
  ④**质量门**：`npm test` **1182/1182 · 72 files 连跑两轮**（18:36:47 / 18:37:18）· `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 font-weight 700×4/600×2/500×4 与 line-height 36/28×2/24/20×2/18×2/16.8/14.4）· `build:h5` DONE · `review-artifacts` 22/22。
  证据：`evidence/redgreen-序号1-字重行盒-20260916.txt` · `red-序号1-fw-字重偏差.txt` · `20260916-序01-登录注册-行盒字重对齐-h5-430宽.png`（430×1114）· `textleaf-audit-20260916-1905.txt` · `textleaf-scan-20260916-1855.log`。
  ⑤**下轮开工第一件事**：序号 1 余 **16px** 残差（首个字段标签前的间距比设计少 4px：设计 ink 339→367 = 28、实现 24；免责摘要正文设计为**两行**（叶子 e5e24331 fs12 h=40 = 2×20）而实现渲染成一行）
  → 修完再按 §5.18 的 172 条待判读清单**按页聚类、一页一轮**推进。
"""

S518 = """
### 5.18 本轮（18:20 轮 · 全量文本叶子审计 + 序号 1）新增的工具与口径

- **全量审计三件套（一处代码覆盖全路由，取代逐页复制）**：
  - 载体页 `h5-measure/__measure-textleaf.html?route=%23/pages/x/index` —— 430 宽 iframe 载入任意路由；收口条件 = 「叶子数 + docH **连续 16 次采样（≈4s）不变**且 ≥24 次采样」或 25s 超时
    （**旧版按「叶子数 >12」2 秒就收口 → 数据未回来时抓到半成品，「未渲染」虚高**）；输出每个文本叶子（无元素子节点且非 head）的 文案 / 自身类 / **祖先类链** / computed fs,lh,fw,textAlign / rect。
  - `python .agents/state/textleaf-scan.py --all [--from <序号>]` —— 逐页起 serve.py（**每页自己的 mock 目录**）+ Chrome dump → `evidence/textleaf-<序号>.json`；
    **带参路由必须与各页载体页的 iframe src 一致**（`ROUTE_OVERRIDE`：4=id=c1 · 5=jobId=j1 · 6=reportId=DR-1 · 7=reportId=DR-7 · 11=itemId=qi1 · 12=quoteId=q7 · 12-v3=quoteId=q9 · 15=contractId=c1），
    不传参会渲染空态（实测：序号 6 **39→288** 叶子 · 序号 12 **6→35** · 序号 15 **29→41**，docH 也才等于设计帧高）。
  - `python .agents/state/textleaf-audit.py [序号 ...] [--out …] [--all-classes]` —— 设计叶子 ↔ DOM 叶子**按渲染文案配对**，比 行盒（want = 显式 height 优先，否则 fs×lineHeight）/ 字号 / 字重；
    文案在设计里**多义**（同一文案多个叶子且声明不同）→ 整条跳过并打印「口径跳过」；`textleaf-accept.json` 里的（页面, class）标为**已核定(非偏差)**（附理由与证据路径）。
- ⚠️ **探针的 declared-box ≠ 设计渲染值**：CJK `fit_content` 文本在 Figma 里的渲染行框 = 字体自然行框（实测 11px→16 · 13px→19.5 · 15px→22.5），而 `lineHeight: 1.2` 只是设计里记的倍数 →
  两边差 2.8~4.5px。**判据优先级：①设计显式 height ②design PNG 实测（卡 pitch / 卡边界 / 墨迹带）③fs×lineHeight；②③冲突以 ② 为准**
  （序号 8 是 ② 否掉 ③；序号 1 是 ① 被 PNG 证实 —— 同一轮里两种情形都出现过，必须逐页裁定）。
- ⚠️ **`uni-text` 的类名不在文本节点上**：uni-app H5 把 `<text class="x">` 渲染成 `<uni-text class="x"><span>` → 探针要取**祖先类链**（取 5 层）。
  只读自身 `className` 会把整页文本归进一个空 `span` 桶（第一版聚合出 n=364 的无意义行）。
- ⚠️ **台账「目标路由」列不带 `#/`**：旧写法 `route.replace('#/','%23/')` 是**空操作** → iframe 变成 `/index.html/pages/x/index` → 404 错误页（只有 5 个叶子、docH = iframe 高度），
  现象是「页面空的」而不是「参数没传对」。正解：显式拼 `?route=%23/<route.lstrip('/')>`，并先 `curl -s -o /dev/null -w '%{http_code}'` 自证一次。
- ⚠️ **假叶子**：uni-app 把页面标题写进 `document.title` → `<title>` 被当成文本叶子（fs 18.3467 / fw 400）。载体页排除 `el.closest('head')`，审计端也按 `tg` 过滤（旧 dump 仍可用）。
- **判卡高/卡 pitch 的取法**：`scan-col.py <png> <x> <y0> <y1>`（卡内**避文字**的白带起止 → 两卡白起之差 = **pitch = 卡高 + 间距**）+
  `png-textbands.py`（行墨迹带，不受投影染色干扰）→ 组合即能裁「行盒该多高、该不该改」。
- **序号 1 设计声明速查**：文本叶子**一律给显式 height**（fs20→28 · fs26→36 · fs14→24 · fs12→20 · fs13→18 · fs11→18 · fs14→16.8 = fs×1.2），字重按 fontFamily 映射。
- **批量改 CSS 的安全做法**：`apply-login-fw.py` / `apply-login-boxes.py` —— 按「父选择器 + 子选择器（+ 上下文行）」定位块，**每个锚点必须恰好命中 1 次**，任一不满足则整文件不写；先 `--dry` 看计划再落盘。
- **本轮新增脚本**：`__measure-textleaf.html` · `textleaf-scan.py` · `textleaf-audit.py` · `textleaf-accept.json` · `list-textleaf-dumps.py` · `ancestors-of.py`（叶子的祖先链声明）·
  `subtree-of.py`（子树声明，做卡高算术）· `apply-login-fw.py` · `apply-login-boxes.py` · `show-login-blocks.py` · `shot-login.sh`（430×1114）· `gen-1-evidence.py`。
- **设计 PNG 留档**：`curl -o .agents/state/design-shots/page-1-2.png "<.calicat/raw/pages/<id>/screenshot.json 里的 URL>"`（本页 430×1114）。
"""

# 1) STATUS 行
lines = src_lf.split('\n')
assert lines[0].startswith('STATUS:'), lines[0][:40]
lines[0] = STATUS
src_lf = '\n'.join(lines)

# 2) 小结插到「### 5.17」之前
anchor = '### 5.17 本轮（18:00 轮）新增的工具与口径'
assert src_lf.count(anchor) == 1
src_lf = src_lf.replace(anchor, SUMMARY.strip('\n') + '\n\n' + anchor)

# 3) §5.18 追加到文件末尾
assert '### 5.18' not in src_lf
src_lf = src_lf.rstrip('\n') + '\n' + S518

io.open(PATH, 'w', encoding='utf-8', newline='\n').write(src_lf)
print('状态文件已回写：STATUS 更新 · 小结插入 · §5.18 追加（%d 字节）' % len(src_lf.encode('utf-8')))
