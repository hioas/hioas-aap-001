# -*- coding: utf-8 -*-
"""把序号 10.1 checks 轮的小结与坑追加到状态文件末尾（保持 CRLF）。"""
import io

P = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/aap-tdd-state.md'

BLOCK = """
- 2026-09-16 13:0x（cron 轮 `aap-tdd-run-20260916-1255`）· **队列 8 第 10 页：序号 10.1「供应商档案」载体页补「设计期望值 checks」维度（271 条 · 偏差 22→0）+ 3 类设计偏差修复 + 整页对齐设计帧 1414（像素对账 31/33 = 97% 命中）**：
  ①**设计帧重抓**（人工指令 C）：`page-10-1-2`（layer_id `54ad46b0-1f7c-498a-ac1a-70dff723b35d`）重抓，`design.json` sha256 `e7983634…` **逐字节相同**（无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-profile.html` 由 314 行旧体例重写为 **430 宽 iframe + 271 条 checks**；红基线（修复前源码 + 同一份探针两轮）**22/271** → 绿 **0/271**；两轮独立测量 **43/43 字段全等**；`docH 1414` = 设计帧高。
  ③**修 3 类偏差**（清单见台账序号 10.1 行 / `evidence/review-序号10.1-checks-报告.md` §4）：8 处图标占位盒按设计图层（形状入 `::before`）· 2 处 center 描边 `border`→ring · 胶囊宽 91→95。
  ④**交互相两轮逐字节相同**：保存 → 真实 `PUT /provider/profile`（完整度 72%→78%，pill/percent/bar 三处一致）· 四个入口均跳 `/pages/profile-edit/index` · 返回 = navigateBack · 每轮 serve 实收 24 行 = 1 写 + 11 对只读 GET。
  ⑤**工具卫生**：`check-mock-fixtures.py` 默认模式对 api-11 的路径假 FAIL → 改为「按每条 check 自带的 mock 目录分组、各起一次 serve」（api / api-11 各 FAIL 0）。
- ⚠️ **载体页 `main()` 的异步链必须 try/catch 并把错误 `sink('error', …)` 出来**：本轮 `main()` 借用了 `collect()` 作用域内的 `textOf` → `ReferenceError` 让 phase2~4 **整段静默丢失**（dump 里只有 phase1，看起来像「跑完了但没交互」）。
  与上一轮「`textOf` 闭包 `doc` 静默不 sink」同类；`show-phases.py` 看 `phases=[…]` 少了哪相即可定位，`show-err.py` 打印错误相。
- ⚠️ **文本带对账不能按 index 配对**：设计 PNG 存在 h=1 的抗锯齿残带（本页 y=602），一按序对齐即**全表串位**、误报 18 条未命中；改「按最近 y0 一对一匹配」后同一对图是 **31/33 = 97%**。写 want / 对账前先看带数与 h=1 残带。
- ⚠️ **`A@@N B` 型选择器在 list 助手里必须组感知**：`querySelectorAll(splitSel(sel).base)` 会退化成「全部 A 的文本」（本页误报 5 条）；`texts/colors/textColors/rects` 统一走新增的 `resolveAll()`。
- **本页新增脚本**：`shot-10.1.sh`（430×1414 整页截图）· `cmp-bands-10.1.py`（设计 PNG vs 实现截图文本带对账，最近 y0 匹配）· `node-by-id.py`（按 layer_id 查设计声明值）·
  `ink-bbox.py` / `ink-runs.py` / `scan-row.py` / `scan-col.py`（墨迹包围盒 / y 带内 x 向墨迹段 / 单行·单列颜色分段）· `show-fails.py`（打印 checkFails 清单）· `show-err.py`（打印载体页错误相）。
"""

s = io.open(P, encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
if '队列 8 第 10 页：序号 10.1' in s:
    raise SystemExit('已经追加过本轮的记录，勿重复')
block = BLOCK.replace('\n', nl)
s = s.rstrip('\r\n') + nl + block
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('appended %d chars, eol=%r' % (len(block), nl))
