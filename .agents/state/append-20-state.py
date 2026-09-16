#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""状态文件回写（序号 20 checks 轮）：STATUS 第 1 行 + LEASE 释放 + 追加本轮小结与 §5.13 工具段。

用法: python .agents/state/append-20-state.py
"""
import io
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aap-tdd-state.md")

OLD_NEXT = ("下一轮开工做 序号 20（`page-20-2`「【合同与通知】站内信列表 2」→ `/pages/messages/index`，"
            "载体页 `__measure-messages.html`，mock 目录 `api-20`；队列 8 余 20/21/22/23）")

NEW_NEXT = (
    "✅ **序号 20 已完成 2026-09-16 15:4x（`page-20-2`「【合同与通知】站内信列表 2」→ `/pages/messages/index`："
    "载体页 `__measure-messages.html` 由 292 行旧体例（无 checks）重写为 430 宽 iframe + **148 条 checks**"
    "（构建脚本 `build-probe-20.py`，四段骨架切自 `__measure-contract.html`）；红基线 14/144 → 绿 **0/148** · "
    "两轮独立测量 30/30 全等 · `docH 760` = 设计帧高 · 溢出 0 · 文案缺失 0 · 像素对账 **命中 26 / 未命中 0** · "
    "修 5 类偏差（未读胶囊/全部已读/chip 文本行盒按设计 lineHeight 1.2 → 13.2/14.4/14.4 · 卡图标新增 22×30 字形盒 · "
    "TabBar 高亮字重逐帧 = 共享组件新增 `activeWeight` prop，本帧 400）· 交互相五出口（guard/filter/readall/card/tab）"
    "各两轮 serve 请求行逐字节相同 · 新增 `refresh-notification-mock.py` 修掉相对时间测量面过期）** → "
    "下一轮开工做 序号 21（`page-21-2`「【工作台与我的】我的 2」→ `/pages/mine/index`，载体页 `__measure-mine.html`"
    "（现为 355 行级旧体例、无 checks 维度 → 同本轮做法重写为 430 宽 iframe checks 探针），mock 目录 `api-21`；队列 8 余 21/22/23）"
)

RUNDOWN = """
- 2026-09-16 15:4x（cron 轮 `aap-tdd-run-20260916-1525`）· **队列 8 第 17 页：序号 20「【合同与通知】站内信列表 2」载体页补「设计期望值 checks」维度（148 条 · 偏差 14→0）+ 5 类设计偏差修复 + 像素对账 26 命中 / 0 未命中**：
  ①**设计帧重抓（人工指令 C）**：先 `cmd /c start ""` 拉起编辑器，再重抓 `page-20-2`（layer_id `76700922-02b2-45f3-9343-256eb34bace0`）→
  `design.json` sha256 `02600c1b…` **逐字节相同**；设计 PNG 重下载 sha256 `b1398fdd…` 与建页时同（430×760）→ 无漂移。
  ②**TDD 红→绿（本轮主交付）**：`__measure-messages.html` 由 292 行旧体例（只报文案/溢出）重写为 **430 宽 iframe + 148 条设计期望值 checks**
  （want = `page-20-2` design.tree.json 声明值 + `dump-layout.py`/`text-fields.py` 全字段 + 设计 PNG 430×760 色带/墨迹实测）；
  红基线（源码未改 + 同一份探针两轮）**14/144**（`evidence/red-序号20-checks-设计期望值偏差.txt`，两轮逐条相同）→ 绿 **0/148**
  （`evidence/green-序号20-checks-设计期望值.txt`）；两轮独立测量 **30/30 字段全等**；`docH 760` = 设计帧高 · 溢出 0 · 文案缺失 0。
  ③**修 5 类页面偏差**（清单见台账序号 20 行 / `evidence/review-序号20-checks-报告.md` §3）：未读胶囊文本行盒 14→**13.2** ·
  「全部已读」文本行盒 15→**14.4** · chip 文本行盒 15→**14.4**（三处均为设计 `lineHeight 1.2`）· **卡图标新增 22×30 字形盒**
  （设计字形层 `ca015b92` fs20 remixicon **声明 w22**、字形行盒 = 字号×1.5 = 30；形状 17×17 画在盒内）·
  **TabBar 高亮字重逐帧**（page-20-2 四行文本**全为 SourceHanSans-Regular**，而 page-21-2 高亮项是 SemiBold →
  共享组件新增 `activeWeight` prop（默认 600 = 21-2，本帧传 400），CSS 不再写死 `font-weight`）。
  ④**红基线分诊（2 处探针自身 bug + 1 处测量面过期，均未记到页面账上）**：
  `card.contentRow*`/`card.timeRow*` 我把「文本行盒 18/16」当成容器盒写 want —— 设计是「容器 padding-top 4 + 文本行」两层 →
  容器盒 = **22 / 20**（已改为该值，另补 `card.contentBox*`/`card.timeBox*` 直接断言文本盒，与 PNG 墨迹 193..205 / 214..224 互证）；
  `filters.chipX/W` 设计声明文本宽 25（chip 49）而 H5 回退字体 CJK 每字**恰 12** → 文本盒 24 → chip **实测 48**、第 4 枚 x 190→**187**
  （want 改为链算值并登记残差，**不写死 49**）；`card.times`/`missingTexts` 的「10 分钟前」漂成「13 分钟前」= **测量面过期**：
  mock 时间戳是绝对值而设计写的是相对时间（08:11 复核轮就因此报过两条假缺陷）→ 新增 `refresh-notification-mock.py`（按 `formatMessageTime`
  同规则把 5 条时间重置为「相对现在」），**测量前必跑**。
  ⑤**本页定标**：图标字形盒 = 声明宽 × 字号×1.5（卡图标 fs20→22×30 · 全部已读 fs16→18×24）；文本行盒**显式 height 优先**（摘要 18 / 时间 16），
  无显式 height 走设计 `lineHeight 1.2`（12→14.4 · 11→13.2），只有「标题行 18」「导航内容行 26」取 PNG 实测；
  「容器 padding-top N + 文本行」容器盒 = N + 行盒；`stroke{align:center,thickness:1}` → `box-shadow: 0 0 0 1px #EEF2F7`（本页 5 卡无 drop_shadow）。
  ⑥**像素对账**：`cmp-bands-6`（±3）内容列 **14/14 命中** + 明细条列 **12/12 命中** = **26 命中 / 0 未命中**；位移中位 +1；
  实现截图 430×760 = 设计帧尺寸（`evidence/cmp-序号20-设计PNGvs实现截图-结构带.txt`，脚本标题文案固定写「序号 6」属复用遗留）。
  ⑦**交互相有牙齿（四出口 + guard，各两轮 requests 逐字节相同）**：`?scenario=guard` 实收 **1 行**（点已选中 chip 不重复取数）·
  `?scenario=filter` 2 行（`GET /notifications?...&unread=true`，chipBgs [灰,蓝,灰,灰]、hash 不变）·
  `?scenario=readall` **3 条真实 `POST /notifications/n{1,2,3}/read`**（18-API 无批量接口 → 逐条，不臆造 read-all；设计无 toast 故成功不弹）·
  `?scenario=card` POST n1/read → 落 `#/pages/report/index?reportId=r1`（biz_type REPORT + biz_id r1）· `?scenario=tab` → `#/pages/workbench/index`（落地页渲染完整）。
  **fixture 补齐**：api-20 新增 `v1/reports/r1/{index,export}`、`v1/provider/profile`、`v1/usage/summary`；`check-mock-fixtures.py` 新增 5 条 api-20 check → **5 PASS / FAIL 0**。
  ⑧**质量门**：`npm test` **1181/1181 · 72 files 连跑两轮**（+3 新用例）· `type-check` exit 0 · `build:mp-weixin` DONE（`pages/messages/index.{js,json,wxml,wxss}`；
  wxss 含 `.msg__glyph-box{width:22px;height:30px}` / `.msg__glyph{width:17px;height:17px}` / `line-height:13.2px` / `line-height:14.4px` ×2）·
  `build:h5` DONE · `review-artifacts` 22/22 · **共用组件回归门**：序号 21 载体页复跑两轮 73/73 全等、`tabbarActiveStyle.fontWeight` 仍 600（默认值未变）·
  截图 `logs/screenshots/20260916-序20-站内信列表-checks轮-h5-430宽.png`（同件入 `.agents/state/evidence/`）。
  ⑨**下轮开工第一件事**：队列 8 的 **序号 21**（`page-21-2`「【工作台与我的】我的 2」→ `/pages/mine/index`，载体页 `__measure-mine.html`，mock `api-21`）。

### 5.13 本轮（15:25 轮 · 序号 20）新增的工具与口径

- **按页组装 checks 探针（第六例）**：`python .agents/state/build-probe-20.py`（从 `__measure-contract.html` 切四段骨架；本页 iframe 取数高度 = 760，
  因为页面 `min-height:100vh` 会把测量高度顶到 iframe 高 —— 760 时 `docScrollHeight` 恰等于设计帧高）。
- ⚠️ **切片坑（本轮踩到）**：`__measure-contract.html` 里 `function bgsIn` 的收尾 `}` 与 `async function main() {` **在同一行**
  （`      }      async function main() {`）→ 按行切片到 `main` 之前会把它切掉，大括号净值 +1；`node --check` 只报「Unexpected end of input」**不给行号**。
  载体页脚本里**显式补回**该 `}`，并用新增的 `python .agents/state/js-depth-lines.py <extracted.js>`（逐行大括号净值）复验净值 0。
- **相对时间 mock 重置**：`python .agents/state/refresh-notification-mock.py [--mock api-20] [--check]`
  —— 站内信列表的 5 条时间文案是**相对时间**（10 分钟前 / 2 小时前 / 昨天 18:20 / 3 天前 / 5 天前），而 mock 的 `created_at` 是绝对值 →
  不重置就会在测量时报「N 小时前」假缺陷（08:11 复核轮的 `missingTexts ['10 分钟前','2 小时前']` 即此）。**凡 mock 里带相对时间的页面，测量前必跑。**
- ⚠️ **「容器 padding-top N + 文本行」的 want 要分两层写**：容器盒 = `N + 行盒`（本页摘要 4+18=22、时间 4+16=20），
  文本盒另测（`.msg__content` 18 / `.msg__time` 16）。只写一层会把行盒当容器盒 → 自造 4 条假偏差。
- ⚠️ **逐帧差异要连"字重"一起比**：page-20-2 与 page-21-2 共用 TabBar，除高亮**色**不同（#007AFF vs #2563EB）外，高亮**字重**也不同（400 vs 600）→
  都做成 prop（`activeColor` / `activeWeight`），CSS 不再写死 `font-weight`（写死会让内联值失效且"看类名猜不出实际字重"）。
- **本轮新增脚本**：`build-probe-20.py` · `shot-20.sh`（430×760 整页截图）· `refresh-notification-mock.py` · `js-depth-lines.py`；
  `check-mock-fixtures.py` 新增 api-20 五条 check；设计 PNG 存 `.agents/state/design-shots/page-20-2.png`。
"""

with io.open(PATH, encoding="utf-8", newline="") as fh:
    text = fh.read()

# 本文件是纯 CRLF（show-eol 实测 CRLF=LF=CR）→ 先归一成 \n 处理，写回时统一转回 CRLF，否则整文件显示改动。
text = text.replace("\r\n", "\n").replace("\r", "\n")

assert OLD_NEXT in text, "状态文件第 1 行里找不到待替换的「下一轮开工做 序号 20」片段（格式变了？）"
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
print("STATUS 含序号 20 完成:", "✅ **序号 20 已完成" in text)
print("STATUS 含下一轮 序号 21:", "下一轮开工做 序号 21" in text)
