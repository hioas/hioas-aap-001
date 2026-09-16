#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""状态文件回写（序号 22 checks 轮）：STATUS 第 1 行 + LEASE 释放 + 追加本轮小结与 §5.15 工具段。

用法: python .agents/state/append-22-state.py
"""
import io
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-tdd-state.md")

OLD_NEXT = ("下一轮开工做 序号 22（`page-22-2`「【工作台与我的】我的与用量概览 2」→ `/pages/usage/index`，"
            "载体页 `__measure-usage.html`（293 行旧体例、无 checks 维度 → 同本轮做法重写为 430 宽 iframe checks 探针），"
            "mock 目录 `api-22`；队列 8 余 22/23）")

NEW_NEXT = (
    "✅ **序号 22 已完成 2026-09-16 16:3x（`page-22-2`「【工作台与我的】我的与用量概览 2」→ `/pages/usage/index`："
    "载体页 `__measure-usage.html` 由 293 行旧体例（无 checks）重写为 430 宽 iframe + **267 条 checks**"
    "（构建脚本 `build-probe-22.py`，四段骨架切自 `__measure-mine.html`）；红基线 8/267 → 绿 **0/267** · "
    "两轮独立测量 50/50 全等 · `docH 1138` = 设计帧高 · 溢出 0 · 文案缺失 0 · "
    "像素对账 **39 命中 / 8 未命中**（未命中 = 投影衰减尾 4 + H5 回退字体字距 4，均非页面缺陷）· "
    "修 5 类偏差（汇总卡 padding 20→20/16 + 补设计 effects 投影 · 日历/下箭头字形盒 17×22.5 / 18×24 · 月份文字行盒 14.4）· "
    "三出口交互两轮 requests 逐字节相同 · 共用消费方回归门 序号 2 复跑 103 条 0 失败）** → "
    "下一轮开工做 序号 23（`page-23-2`「【工作台与我的】账号与设置 2」→ `/pages/settings/index`，"
    "载体页 `__measure-settings.html`（旧体例、无 checks 维度 → 同本轮做法重写为 430 宽 iframe checks 探针），"
    "mock 目录 `api-23`；队列 8 余 23/23 —— 做完即队列 8 收尾）"
)

RUNDOWN = """
- 2026-09-16 16:3x（cron 轮 `aap-tdd-run-20260916-1605`）· **队列 8 第 19 页：序号 22「【工作台与我的】我的与用量概览 2」载体页补「设计期望值 checks」维度（267 条 · 偏差 8→0）+ 5 类设计偏差修复 + 像素对账 39 命中 / 8 未命中（2 类非页面缺陷）**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start \"\"` 拉起编辑器，再重抓 `page-22-2`（layer_id `8bc59233-3854-4725-b85b-bfaf4518e934`）→
  `design.json` sha256 `63d7ce0c…` **逐字节相同**；设计 PNG 重下载 sha256 `ce50a955…`（430×1138）相同 → 无漂移。
  ②**TDD 红→绿（本轮主交付）**：`__measure-usage.html` 由 293 行旧体例（只报文案/溢出）重写为 **430 宽 iframe + 267 条设计期望值 checks**
  （want = `page-22-2` design.tree.json 声明值 + `dump-layout.py`/`text-fields.py`/`raw-node.py` 全字段 + 设计 PNG 430×1138 色带/墨迹实测）；
  红基线（`git stash` 复现修复前源码 + **同一份最终版探针**两轮）**8/267**（`evidence/red-序号22-checks-设计期望值偏差.txt`，两轮逐条相同）→ 绿 **0/267**
  （`evidence/green-序号22-checks-设计期望值.txt`）；两轮独立测量 **50/50 字段全等**（不一致 0）；`docH 1138` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 5 类页面偏差**（清单见台账序号 22 行 / `evidence/review-序号22-checks-报告.md` §2.1）：①**汇总卡 padding 20 → 20/16**
  （设计 811a53eb padding=[20,16,20,16] → 宫格 175→178.5 宽、x 36→32、标题 x 36→32，一条改动解掉 3 条 check）
  ②**补设计 effects `drop_shadow(0,6,20,rgba(15,23,42,.06))`**（该卡**无 stroke**，此前只给趋势/模型/成本/明细四卡写了 ring，汇总卡投影整体漏实现）
  ③月份日历字形盒 17×15 → **17×22.5**、下箭头字形盒 18×15 → **18×24**（= 声明宽 × 字号×1.5），并去掉下箭头形状的 `margin-bottom:3px`
  （把墨迹从中心上移 1.5px；设计墨迹中心 = 胶囊中心 66）④月份文字行盒 18 → **14.4**（设计 lineHeight 1.2 × 12）。
  ④**红基线分诊（3 条探针自身期望值 bug，已修正并重跑红基线，保证红/绿同版探针）**：
  `summary.tiles1.top/h` 把「容器（含 padding-top）」当「宫格行」（改断容器 148/88 + 新增 `tileTops [164,164,244,244]`）；
  `models.trackW` 误以为 4 行同宽（轨道是 `fill_container` → 末行「6%」百分比盒窄 7，PNG 实测行 1 为 192、行 4 为 199 → want 改 `[192,192,192,199]`）；
  `summary.shadow` want 缺 Chrome 序列化的尾随 spread `0px`（同序号 12/15 口径）。
  另把 `trend.img.src` 从「读元素 src」改为「从 uni-image innerHTML 取 data-URI → `atob` 解码回 SVG」，新增 5 条硬断言
  （viewBox `0 0 358 150` · 4 条网格线 · 7 个数据点 · 折线 `#2563EB` · 面积 `rgba(191,219,254,0.35)`）。
  ⑤**本页定标（供同族「概览 / 仪表盘」长页复用）**：图标字形盒 = 设计声明宽 × 字号×1.5
  （返回 fs24 声明 w26 → 26×36 · 日历 fs15 → 17×22.5 · 下箭头 fs16 → 18×24 · 明细列表 fs18 声明 w20 → 20×27；**chevron-right fs20 实测 22×28，非 ×1.5**）；
  文本行盒 **显式 height 优先**（标题 20 · 图例标题行 20 · 值 26 · 标签 16 · 合计值 21 · 底部 16 · 横轴 11.3），无显式 height 走 `lineHeight 1.2`（12 → 14.4）、
  模型/成本行内容取 PNG 实测 **18**；设计里「容器 padding-top N + 行」的**容器盒 = N + 行盒**（探针必须分两层写，否则自造假偏差）；
  **逐卡断言不统一**：汇总卡只有 effects、其余四卡只有 `stroke #EEF2F7`（无 effects）→ 逐卡写 want。
  卡片结构账：汇总卡 20+20+16+72+8+72+20 = **228** · 趋势卡 20+20+12+150+20 = **222** · 模型卡 20+20+16+4×18+3×12+20 = **184** ·
  成本卡 20+20+16+3×18+3×12+41+20 = **207** · 明细卡 16+28+16 = **60** · 底部说明 24+16+16+24 ≈ **80~81**（页高 1138 = 96 + 5×12 + 901 + 81）。
  ⑥**像素对账**：`cmp-bands-6`（±3）内容列 27/31 + 明细/进度列 12/16 = **39 命中 / 8 未命中**，位移中位 0（内容列 0 位移 14 个 · min −3 / max +3）；
  未命中逐条判读 = ①汇总卡**投影衰减尾**（x=200 列：设计 336..345 (238,240,243)→(243,245,247) 后 349..359 仍有 252..254 淡染、实现 348+ 纯白；
  起点/峰值两侧同值 → Figma/Chrome 模糊衰减步长差 1~3/255）②成本行右对齐值的 **H5 回退字体字距/右留白**（设计墨迹 353..391、实现 355..393，同右对齐 394、墨迹同宽 39）→ 均非页面缺陷。
  `cmp-textrows.py`：21 ↔ 21 行文本带，8 行完全相同、其余 ±1（无 2px 级位移）。
  ⑦**交互相有牙齿（三出口，各两轮 requests 逐字节相同）**：纯测量轮 1 行只读 GET · `?scenario=back` hash 不变 / 无 toast / 零写请求 / `cardCount 5`，
  并用 `windowMark=null` **证明 uni H5 无栈时降级为整页重载**（第二次 GET 同 URL，不是重复取数）· `?scenario=month` 点开真 `uni-picker`
  （`uni-picker-container uni-date-select` + `uni-picker-action-confirm`）→ 确认 → **第二次真取数 `GET /api/v1/usage/summary?month=2024-06`**（首屏 `?month=2026-09`）·
  `?scenario=detail` **no-op**（画布 30 页无明细页）：hash 不变 / 无 toast / 无新请求。**fixture 体检补齐**：`check-mock-fixtures.py` 新增 5 条 api-22 check → FAIL 0。
  ⑧**质量门**：`npm test` **1181/1181 · 72 files 连跑两轮**（16:18:51 / 16:19:28）· `type-check` exit 0 · `build:mp-weixin` DONE
  （`pages/usage/{index.js,index.json,index.wxml,index.wxss}` 齐备 + app.json 注册；wxss 含 `padding:20px 16px` / `box-shadow:0 6px 20px rgba(15,23,42,.06)` / `height:22.5px` / `height:24px` / `line-height:14.4px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · **共用消费方回归门**（序号 2 工作台同用 `usage-model.ts` 的 D3 环形/图例口径）`__measure-workbench.html` 复跑 **103 条 0 失败**（两轮 `docH 1146` 全等）·
  截图 `logs/screenshots/20260916-序22-用量概览-checks轮-h5-430宽.png`（430×1138 = 设计帧尺寸，同件入 `.agents/state/evidence/`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 23**（`page-23-2`「【工作台与我的】账号与设置 2」→ `/pages/settings/index`，
  载体页 `__measure-settings.html` → 同本轮做法重写，mock 目录 `api-23`；**做完即队列 8（20 个载体页）收尾**，
  随后回到队列 1 余下行与队列 7（uni-picker 溢出口径，本页已按同族做法排除 `uni-resize-sensor`，uni-picker 内部空 div 因父级 `overflow:hidden` 不影响 `docScrollWidth`）。

### 5.15 本轮（16:05 轮 · 序号 22）新增的工具与口径

- **按页组装 checks 探针（第八例）**：`python .agents/state/build-probe-22.py`（从 `__measure-mine.html` 切四段骨架；
  iframe 取数高度 = **1138** = 设计帧高，页面 `min-height:100vh` 会把测量高度顶到 iframe 高 → `docScrollHeight` 恰等于设计帧高）。
  ⚠️ **两处切片坑（本轮踩到并写进脚本断言）**：①`__measure-mine.html` 里 `function bgsIn` 的收尾 `}` 与 `async function main() {` **同一行** →
  按行切片会把它切掉（大括号净值 +1，`node --check` 只报「Unexpected end of input」不给行号）→ 脚本显式 `tail += "\\n      }"` 并用
  `python .agents/state/js-depth-lines.py <extracted.js>` 复验净值 0；②**`pickerProbe` / `clickOverlayConfirm` 不在共享骨架里**
  （它们原本只写在旧版 `__measure-usage.html` 自己的脚本里）→ month 相直接 `ReferenceError: pickerProbe is not defined`，本页必须在主脚本里自带。
- **看某次测量某个 phase 的指定字段**：`python .agents/state/show-phase-fields.py <run.json> <phase> <field...>`
  （`show-phases.py` 打的是检查项汇总，字段级要另取；本页用它读 `windowMark` / `monthAfter`）。
- **看某个 phase 的 checkFails**：`python .agents/state/show-fails2.py <run.json> [phase]`（字段名容错版，用于 103 条旧体例探针的 FAIL 逐条）。
- ⚠️ **`review-measure.sh` 的 mock 参数必须是「仓库相对路径」**：脚本内部拼 `"$ROOT/$MOCK"`，传裸 `api` 会变成 `<root>/api` →
  **整页 404、checkFails 全假红**（本轮共用回归门首跑 19 条假失败即此；SKILL §5「every call 404s → 先怀疑自己的参数」已记该陷阱）。
  正确写法：`review-measure.sh 2-sharedgate __measure-workbench.html .agents/state/h5-measure/api 5352`。
- ⚠️ **探针 want 的两条硬口径（本轮各踩一次）**：
  ①`box-shadow` 的 want 必须带 Chrome 序列化的**尾随 spread `0px`**（`rgba(15, 23, 42, 0.06) 0px 6px 20px 0px`）；
  ②**`fill_container` 的轨道/占位宽度逐行可能不同**（本页模型轨道 192/192/192/199，因末行百分比盒更窄）→ 不要写 4 个同值。
- ⚠️ **uni-image 读不到元素 `src`**：H5 下 `uni-image` 把图塞进内部 `img`/背景图 → 探针要从 `element.innerHTML` 里取 data-URI 并
  `atob()` 解码回 SVG 再断言（本轮据此给趋势图加了 viewBox / 网格线数 / 数据点数 / 折线色 / 面积色 5 条硬断言）。
- **本页截图**：`bash .agents/state/shot-22.sh [文件名]`（`--window-size=430,1138`；ASCII 临时名 → `cp` 中文名）。
- **本轮新增脚本**：`build-probe-22.py` · `shot-22.sh` · `gen-22-checks-evidence.py` · `append-22-checks-note.py` · `append-22-state.py` ·
  `show-phase-fields.py` · `show-fails2.py`；`check-mock-fixtures.py` 新增 5 条 api-22 check；设计 PNG 存 `.agents/state/design-shots/page-22-2.png`。
"""

with io.open(PATH, encoding="utf-8", newline="") as fh:
    text = fh.read()

# 本文件是纯 CRLF → 先归一成 \n 处理，写回时统一转回 CRLF，否则整文件显示改动。
text = text.replace("\r\n", "\n").replace("\r", "\n")

assert OLD_NEXT in text, "状态文件第 1 行里找不到待替换的「下一轮开工做 序号 22」片段（格式变了？）"
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
print("STATUS 含序号 22 完成:", "✅ **序号 22 已完成" in text)
print("STATUS 含下一轮 序号 23:", "下一轮开工做 序号 23" in text)
