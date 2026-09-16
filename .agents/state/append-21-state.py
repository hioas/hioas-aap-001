#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""状态文件回写（序号 21 checks 轮）：STATUS 第 1 行 + LEASE 释放 + 追加本轮小结与 §5.14 工具段。

用法: python .agents/state/append-21-state.py
"""
import io
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-tdd-state.md")

OLD_NEXT = ("下一轮开工做 序号 21（`page-21-2`「【工作台与我的】我的 2」→ `/pages/mine/index`，"
            "载体页 `__measure-mine.html`（现为 355 行级旧体例、无 checks 维度 → 同本轮做法重写为 430 宽 iframe checks 探针），"
            "mock 目录 `api-21`；队列 8 余 21/22/23）")

NEW_NEXT = (
    "✅ **序号 21 已完成 2026-09-16 16:0x（`page-21-2`「【工作台与我的】我的 2」→ `/pages/mine/index`："
    "载体页 `__measure-mine.html` 由 248 行旧体例（无 checks）重写为 430 宽 iframe + **230 条 checks**"
    "（构建脚本 `build-probe-21.py`，四段骨架切自 `__measure-messages.html`）；红基线 17/230 → 绿 **0/230** · "
    "两轮独立测量 43/43 全等 · `docH 990` = 设计帧高 · 溢出 0 · 文案缺失 0 · "
    "像素对账 **29 命中 / 0 未命中**（内容列 16/16 + 条列 13/13，位移中位 0）· "
    "修 10 类偏差（头像字形盒 33×45 · 4 处文本行盒按设计 lineHeight 1.2 = 13.2/16.8/15.6 · 行图标字形盒 20×27 + 形状入 `::before` · "
    "标签 15.6 / 值 14.4 / 胶囊 12）· 六出口交互两轮 requests 集合相等 · 共用组件回归门 序号 20 复跑 148 条 0 失败）** → "
    "下一轮开工做 序号 22（`page-22-2`「【工作台与我的】我的与用量概览 2」→ `/pages/usage/index`，"
    "载体页 `__measure-usage.html`（293 行旧体例、无 checks 维度 → 同本轮做法重写为 430 宽 iframe checks 探针），"
    "mock 目录 `api-22`；队列 8 余 22/23）"
)

RUNDOWN = """
- 2026-09-16 16:0x（cron 轮 `aap-tdd-run-20260916-1545`）· **队列 8 第 18 页：序号 21「【工作台与我的】我的 2」载体页补「设计期望值 checks」维度（230 条 · 偏差 17→0）+ 10 类设计偏差修复 + 像素对账 29 命中 / 0 未命中**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start \"\"` 拉起编辑器，再重抓 `page-21-2`（layer_id `e537204e-faf7-416b-8669-1347d581490c`）→
  `design.json` sha256 `cd12a92b…` **逐字节相同**（`cmp` 无差异）；设计 PNG 重下载 sha256 `d73cf39a…`（430×990）→ 无漂移。
  ②**TDD 红→绿（本轮主交付）**：`__measure-mine.html` 由 248 行旧体例（只报文案/溢出）重写为 **430 宽 iframe + 230 条设计期望值 checks**
  （want = `page-21-2` design.tree.json 声明值 + `dump-layout.py`/`text-fields.py` 全字段 + 设计 PNG 430×990 色带/墨迹实测）；
  红基线（源码未改 + **同一份最终版探针**两轮）**17/230**（`evidence/red-序号21-checks-设计期望值偏差.txt`，两轮逐条相同）→ 绿 **0/230**
  （`evidence/green-序号21-checks-设计期望值.txt`）；两轮独立测量 **43/43 字段全等**（不一致 0）；`docH 990` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 10 类页面偏差**（清单见台账序号 21 行 / `evidence/review-序号21-checks-报告.md` §3）：①头像字形盒 16×16 → **33×45**
  （设计 `85003c7e` fs30 remixicon **声明 w33** × 行盒 30×1.5；形状头 14 + 肩 26×11 按设计字形墨迹 26×25 画在盒内）②4 处文本行盒未按设计 `lineHeight 1.2`：
  类型标签/已认证 16→**13.2** · 钱包标题 21→**16.8** · 提现文案 20→**15.6** ③行图标字形盒 16×16 → **20×27**（字形层声明 w20 + fs18 行盒 27；
  x 44→42、top 逐行 +6，与 PNG 图标墨迹 43..59 / 373..388 对齐；形状 17×16 移入 `::before`）④行标签行盒 19.5→**15.6** ⑤行值行盒 18→**14.4**
  ⑥胶囊文字行盒 14→**12** ⑦字形颜色改由伪元素承载（原 `background: currentColor` 在元素自身 → 探针读 `::before` 拿不到色）。
  ⑧`routes.ts` 两处注释口径改正（序号 22/23 落点页**已实现**）。
  ④**红基线分诊（2 条探针自身期望值 bug，已修正并重跑红基线，保证红/绿同版探针）**：
  `head.tags.top` 把「带 `padding-top: 8` 的容器」当「子行」写 want 82 → 改断容器 74 + 新增 `.head__type.top = 82`（设计是「容器 a3c59082 + 标签行」两层）；
  `entries.values` 只写 3 个值，漏了第 5 行「我的消息」的「待阅读 3」（设计 row5 确有值节点）→ 改 4 值 / 4 右边 / 4 色
  （第 4 个是设计字面量 `rgba(0,0,0,1)`，与同卡其它值 #94A3B8 不同 → 逐值断言不统一）。
  ⑤**本页定标（供同族「个人中心 / 卡片列表」页复用）**：图标字形盒 = **设计声明宽 × 字号×1.5**（头像 fs30 声明 w33 → 33×45 · 行图标 fs18 声明 w20 → 20×27 · TabBar fs22 → 33）；
  文本行盒 **显式 height 优先**（公司名 26 · 余额标签 16 · 金额 34 · 明细值 22），无显式 height 走 `lineHeight 1.2`
  （14→16.8 · 13→15.6 · 12→14.4 · 11→13.2 · 10→12）—— **同一页里 fs11 也可能有显式 h16**（余额标签）→ 逐节点判，切忌一刀切；
  卡片结构账：钱包卡 20+30+16+52+16+38+20 = **192** · 入口卡 8+5×56+3×1+8 = **299** · 证照卡 8+4×54+3×1+8 = **235** · TabBar 8+33+3+16+24 = **84**。
  ⑥**像素对账**：`cmp-bands-6`（±3）内容列 **16/16 命中** + 明细/图标列 **13/13 命中** = **29 命中 / 0 未命中**（位移中位 0 · min −2 · max +1）；
  实现截图 430×990 = 设计帧尺寸（`evidence/cmp-序号21-设计PNGvs实现截图-结构带.txt`）。
  ⑦**交互相有牙齿（六出口，各两轮）**：纯测量轮 7 行只读 GET（profile/payments/quotes/credentials/reports/contracts?status=PENDING_SIGN/notifications?unread=true）**零写请求** ·
  `?scenario=withdraw` toast「提现功能暂未开放」+ hash 不变（client-only，missing-prd）· `?scenario=rows-quotes` → `#/pages/quotes/index`（requests 逐字节相同）·
  `?scenario=usage` → `#/pages/usage/index`（渲染「用量概览」）· `?scenario=settings` → `#/pages/settings/index`（渲染「账号与设置」）·
  `?scenario=tab-workbench` → `#/pages/workbench/index`（数据台完整渲染）· `?scenario=tab-mine` hash 不变。
  ⚠️ **requests 比对口径**：首屏 7 个 GET 是 `Promise.all` 并发 → 落盘**顺序抖动**，用「**集合相等**」判一致（已逐行核对内容），确定性场景仍逐字节相同。
  **口径改正**：台账序号 21 备注⑧「用量与对账 / 账号与设置 落点页未实现 → 跳转由 uni 侧降级」**作废** —— 序号 22/23 均已实现并注册在 pages.json。
  ⑧**质量门**：`npm test` **1181/1181 · 72 files 连跑两轮**（15:56:51 / 15:57:25）· `type-check` exit 0 · `build:mp-weixin` DONE
  （`pages/mine/index.{js,json,wxml,wxss}` 齐备 + app.json 注册；wxss 含 `width:33px;height:45px` / `width:17px;height:16px` / `line-height:13.2px ×2` / `15.6px ×2` / `16.8px` / `14.4px` / `12px` / `box-shadow:0 0 0 1px`）·
  `build:h5` DONE · `review-artifacts` 22/22 · `check-mock-fixtures --mock api-21` **9 PASS + 反向体检 PASS / FAIL 0**（本轮新补 9 条）·
  **共用组件回归门**（`AppTabBar` 被 page-20-2 / page-21-2 共用）：序号 20 载体页复跑 **148 条 0 失败**、两轮 30/30 全等
  （**先跑 `refresh-notification-mock.py --mock api-20` 修测量面相对时间过期** —— 未跑时那 2 条失败与本轮改动无关）·
  截图 `logs/screenshots/20260916-序21-我的页-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 22**（`page-22-2`「【工作台与我的】我的与用量概览 2」→ `/pages/usage/index`，
  载体页 `__measure-usage.html`（293 行旧体例、无 checks）→ 同本轮做法重写，mock 目录 `api-22`）。

### 5.14 本轮（15:45 轮 · 序号 21）新增的工具与口径

- **按页组装 checks 探针（第七例）**：`python .agents/state/build-probe-21.py`（从 `__measure-messages.html` 切四段骨架；
  本页 iframe 取数高度 = **990** = 设计帧高，因为页面 `min-height:100vh` 会把测量高度顶到 iframe 高 —— 990 时 `docScrollHeight` 恰等于设计帧高）。
  ⚠️ 与 §5.13 的切片坑对照：`__measure-messages.html` 里 `bgsIn` 的收尾 `}` **单独一行** → 本页无需补 `}`（净值复核仍要做：`js-depth.py`）。
- **证据合成（第七例）**：`python .agents/state/gen-21-checks-evidence.py`（红/绿两轮 + 六出口 + 共用组件回归门 → 两个转录文件）。
- **整页截图**：`bash .agents/state/shot-21.sh [文件名]`（`--window-size=430,990`；ASCII 临时名 → `cp` 中文名，Chrome 中文路径坑见 §5）。
- ⚠️ **首屏并发请求的 requests 证据不能用 `diff` 逐字节判**：`Promise.all` 的 7 个 GET 落盘顺序会抖动（同一轮两份 dump 也可能不同序）→
  用「排序后集合相等」判一致，并在转录里写明口径；**确定性场景（点击后串行发请求）仍用逐字节 diff**。
- ⚠️ **共用组件回归门遇到相对时间 mock 会假红**：序号 20 载体页的 148 条里有 `page.missingTextCount`（相对时间文案），
  时间一过就漂成「14 分钟前」→ **测量前必跑** `python .agents/state/refresh-notification-mock.py --mock api-20`（§5.13 的工具，本轮再次踩到）。
- ⚠️ **落地页被后续轮次实现后，旧台账口径会变成假缺陷**：序号 22/23 页面早已实现并注册，`?scenario=usage` / `?scenario=settings`
  实测均正常落地 → 复核「落点 hash 不变 / 降级」类旧结论前，先查 `src/pages.json` 与 `src/pages/<route>/`。
- **本轮新增脚本**：`build-probe-21.py` · `shot-21.sh` · `gen-21-checks-evidence.py` · `append-21-checks-note.py` · `append-21-state.py`；
  `check-mock-fixtures.py` 新增 9 条 api-21 check；设计 PNG 存 `.agents/state/design-shots/page-21-2.png`。
"""

with io.open(PATH, encoding="utf-8", newline="") as fh:
    text = fh.read()

# 本文件是纯 CRLF → 先归一成 \n 处理，写回时统一转回 CRLF，否则整文件显示改动。
text = text.replace("\r\n", "\n").replace("\r", "\n")

assert OLD_NEXT in text, "状态文件第 1 行里找不到待替换的「下一轮开工做 序号 21」片段（格式变了？）"
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
print("STATUS 含序号 21 完成:", "✅ **序号 21 已完成" in text)
print("STATUS 含下一轮 序号 22:", "下一轮开工做 序号 22" in text)
