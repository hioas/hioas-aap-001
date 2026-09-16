#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""状态文件回写（序号 15 checks 轮）：STATUS 第 1 行 + LEASE 释放 + 追加本轮小结与 §5.12 工具段。

用法: python .agents/state/append-15-state.py
"""
import io
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-tdd-state.md")

OLD_NEXT = ("→ 下一轮开工做 序号 15**（`page-15-2`「【合同与通知】合同签署 2」→ `/pages/contract/index`，"
            "载体页 `__measure-contract.html`，mock 目录 `api-15`）")

NEW_NEXT = (
    "✅ **序号 15 已完成 2026-09-16 15:2x（`page-15-2`「【合同与通知】合同签署 2」→ `/pages/contract/index`："
    "载体页 `__measure-contract.html` 重写为 430 宽 iframe + **239 条 checks**（构建脚本 `build-probe-15.py`，"
    "四段骨架切自 12-v3 载体页）；红基线 5/239 → 绿 **0/239** · 两轮独立测量 37/37 全等 · `docH 1231` = 设计帧高 · "
    "溢出 0 · 文案缺失 0 · 像素对账 内容列 35/38 + 条列 17/17（3 条未命中全在设计导出图提示卡顶部 207..217 的 1~3/255 雾带内）· "
    "修 5 类偏差（状态卡投影改回设计 effects(0,6,20,.06) / 状态图标补 26×36 字形行盒 / 待签署标文字行高 22→13.2 / "
    "下载PDF按钮描边 0.8→1px / **提示卡文案行盒 13.2→16（像素对账抓出，修后墨迹 221..232 = 设计）**）· "
    "三出口交互（pdf/sign/back）两轮 requests 逐字节相同 · 工具侧修 `check-mock-fixtures.py` 对 api-15 的假 FAIL）** → "
    "下一轮开工做 序号 20（`page-20-2`「【合同与通知】站内信列表 2」→ `/pages/messages/index`，"
    "载体页 `__measure-messages.html`，mock 目录 `api-20`；队列 8 余 20/21/22/23）"
)

RUNDOWN = """
- 2026-09-16 15:2x（cron 轮 `aap-tdd-run-20260916-1505`）· **队列 8 第 16 页：序号 15「【合同与通知】合同签署 2」载体页补「设计期望值 checks」维度（239 条 · 偏差 5→0）+ 5 类设计偏差修复（含像素对账抓出的提示卡文案行盒）**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-15-2`（layer_id `14d79713-8314-41a4-a8df-b4aff9ecd7b8`）→
  `design.json` sha256 `ca94e93e…` **逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）。
  ②**TDD 红→绿（本轮主交付）**：`__measure-contract.html` 由 297 行旧体例（无 checks）重写为 **430 宽 iframe + 239 条 checks**
  （want = `page-15-2` design.tree.json 声明值 + design.json 的 effects/stroke + 设计 PNG 430×1231 色带/墨迹实测）；
  红-1（239 条，want 全按声明值）**5/239** → 修正探针自身 4 条期望值 bug → 红-2（把 `tip.text.lh` 的 want 按 PNG 改为 16）**1/239** →
  绿 **0/239**；每阶段两轮独立测量全等（绿轮 37/37 字段全等，不一致 0）；`docH 1231` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 5 类偏差**（清单见台账序号 15 行 / `evidence/review-序号15-checks-报告.md` §3）：①合同状态卡投影改回设计 effects
  `drop_shadow(0,6,20,rgba(15,23,42,.06))`（旧备注「设计树读不到投影参数」作废）②状态图标字形补 **26×36** 行盒（fs24×1.5）③
  待签署标文字 `line-height` 22→**13.2**（设计 1.2）④下载 PDF 按钮描边 ring 0.8→**1px**（设计 `stroke{thickness:1}`）⑤
  **提示卡文案行盒 13.2→16**（**像素对账抓出**：设计墨迹 221..232 vs 修前实现 219..230）。
  ④**本页定标**：图标字形行盒 = 字号×1.5（fs24→26×36 · fs18→20×27，5 处交叉一致）；文本行盒**显式 height 优先**，无显式 height 的
  11px 用 PNG 实测 16（期限行/记录时间/提示卡文案三处自洽）；`stroke{thickness:1}` → `box-shadow: 0 0 0 1px`；`effects.drop_shadow` → `box-shadow`。
  ⑤**像素对账**：`cmp-bands-6`（±3）内容列 35/38 + 条列 17/17 = **52 命中 / 3 未命中**，位移中位 +1（无整体平移）；
  3 条未命中逐条判读 = 设计导出图提示卡顶部 207..217 整行均匀 `rgb(252..254)` 的软染色（实现纯白），差 1~3/255 → **非页面缺陷**。
  `text-rows.py` 26 行文本带：16 行区间完全相同、其余 ±1（H5 回退字体墨迹上下沿），已无 2px 差。
  ⑥**交互相有牙齿（三出口，各两轮逐字节相同）**：`?scenario=pdf` → `GET /contracts/c1/file` 后 **真下载 `GET /files/CT-2024-0613-008.pdf` 200**、无 toast；
  `?scenario=sign` → uni-modal「确认签署 / 确认对当前合同发起签署？」→ **真实 `POST /contracts/c1/sign`（body 空）** → toast「签署申请已提交」→ 重载；
  `?scenario=back` → `navigateBack`（栈内无上一页 → hash 不变 + 零额外请求，栈内返回由 `contract-flow.spec.ts` 断言）；纯测量轮只 1 行请求。
  **fixture 体检补齐**：`check-mock-fixtures.py` 新补 3 条 api-15 检查（`GET /contracts/c1` / `GET /contracts/c1/file` / `POST /contracts/c1/sign`）→ `--mock api-15` FAIL 0。
  ⑦**质量门**：`npm test` **1178/1178 · 72 files 连跑两轮** · `type-check` exit 0 · `build:mp-weixin` DONE（`pages/contract/index.{js,json,wxml,wxss}`，wxss 含本轮设计值）·
  `build:h5` DONE · `review-artifacts` 22/22 · 截图 `logs/screenshots/20260916-序15-合同签署-checks轮-h5-430宽.png`（430×1231 = 设计尺寸）。
  ⑧**工具侧修正**：`check-mock-fixtures.py` 的 `--mock <dir>` 变体前缀回退原写成「只要以 base- 开头就算变体」→ `api-15` 被误判成 `api` 变体、
  一次报 8 条无关 FAIL；收窄为只对 `*-tmp-*` 生效 + 零匹配时打印 WARN（`api-tmp-*` 变体回退实测仍有效）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 20**（`page-20-2`「【合同与通知】站内信列表 2」→ `/pages/messages/index`，载体页 `__measure-messages.html`，mock `api-20`）。

### 5.12 本轮（15:05 轮 · 序号 15）新增的工具与口径

- **按页组装 checks 探针（第五例）**：`python .agents/state/build-probe-15.py`（从 `__measure-quote-success.html` 切四段骨架；
  tail 与 main 的切点用 `async function main() {`，因为 12-v3 载体页里已没有旧版 `/** uni-app H5 的 <input>` 注释 —— 用旧锚会 SystemExit）。
- **文本行带逐行对账**：`python .agents/state/cmp-textrows.py <design.txt> <impl.txt>`（`text-rows.py` 两次输出喂进来，
  打印「区间完全相同的行数 + 每行起点差」；比手工对数省事，也避免把「上下沿差 1px」误读成「整体平移」）。
- ⚠️ **探针两处口径坑**（本轮踩到并修正，会记到页面账上）：
  ①`chkStrs` 收到的是 `css()` 归一化后的值（`'16px'` → 数值 `16`）→ want 必须写数值，写 `'16px'` 必假失败；
  ②设计里「容器 + padding-left」的结构，实现常把 padding 挂在**后一个元素自身**（`status__content` / `record__body` / `nav__title` / `tip__text`）
  → 断「后元素盒子左 − 前元素右 = 12」必得 0；正解 = 断**墨迹左界** = 盒子左 + 该元素 paddingLeft。
- ⚠️ **11px 文本的行盒要看「它属于哪一类」**：同帧里 `h16`（期限行/记录时间，显式 height）与提示卡文案（PNG 反推 16）一致，
  而 `nav__no`（居中行内）走 13.2 无碍 —— **只看设计树 `lineHeight 1.2` 会漏掉顶对齐的那一处 2px 墨迹偏移**（探针量不到，只有像素对账能抓）。
- **本轮新增脚本**：`shot-15.sh`（430×1231 整页截图）· `gen-15-checks-evidence.py`（红/绿/三出口/像素对账合成）·
  `append-15-checks-note.py`（台账回写）· `append-15-state.py`（本文件回写）· `cmp-textrows.py`。
- **本页定标（供同族「详情 + 底栏双按钮」页复用）**：顶栏 96（48 + 字形行盒 36 + 12）· 内容区 padding 12/16/0/16 + 卡距 12 ·
  字段卡 = 20 + 标题 20 + 16 + n×18 + (n−1)×12 + 20 · 记录卡条目 34（18 + 16）· 底栏 84（12 + 48 + 24）+ 外包裹 padding-top 16 ·
  底栏双按钮 = 固定 126（ghost, ring 1px #CBD5E1）+ 12 间距 + fill_container（primary #2563EB）。
"""

with io.open(PATH, encoding="utf-8", newline="") as fh:
    text = fh.read()

# 本文件是**纯 CRLF**（show-eol 实测 900 CRLF / 900 LF / 900 CR）→ 先归一成 \n 处理，写回时再统一转回 CRLF，
# 否则会写成混合行尾、git 里整文件显示改动。
text = text.replace("\r\n", "\n").replace("\r", "\n")

assert OLD_NEXT in text, "状态文件第 1 行里找不到待替换的「下一轮做 序号 15」片段（格式变了？）"
text = text.replace(OLD_NEXT, NEW_NEXT)

lines = text.split("\n")
assert lines[1].startswith("LEASE:"), "第 2 行不是 LEASE（格式变了？）: %r" % lines[1][:60]
lines[1] = "LEASE: free until -"
text = "\n".join(lines)

text = text.rstrip("\n") + "\n" + RUNDOWN

with io.open(PATH, "w", encoding="utf-8", newline="\r\n") as fh:
    fh.write(text)
print("state file updated:", PATH)
print("LEASE 行:", text.split("\n")[1][:80])
print("STATUS 含序号 15 完成:", "✅ **序号 15 已完成" in text)
