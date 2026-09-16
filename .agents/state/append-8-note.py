# -*- coding: utf-8 -*-
"""序号 8（报价单列表）checks 轮的台账回写：向「用例(证据)」与「备注」列追加本轮内容。

用法: python .agents/state/append-8-note.py
（中文直接写在脚本里，避免 bash 传参被转成 GBK —— 见状态文件 §5 平台坑）
"""
import csv
from pathlib import Path

PATH = Path(".agents/state/aap-feature-status.csv")

CASE = (
    "checks 轮（设计期望值维度）2026-09-16 11:5x：载体页 __measure-quotes.html 由 249 行旧体例重写为 430 宽 iframe + "
    "**138 条 checks**（want = page-8-2 design.tree.json 声明值 + text-fields.py 全字段 + 设计 PNG 430×1206 色带/墨迹实测）；"
    "红基线（git stash 复现修复前源码、同一份探针两轮）**27/138**（evidence/red-序号8-checks-设计期望值偏差.txt，两轮完全一致）→ 绿 **0/138**"
    "（green-序号8-checks-设计期望值.txt），两轮独立测量 **30/30 字段全等**；整页 docScrollHeight **1198 → 1206 = 设计帧高**（90+54+962+16+84）。"
    "修掉 11 类偏差：顶部标题字重 600→700、行框 24→30；「新建报价」宽 88→**100**（当前画布重抓值）、图标盒 12×12→**18×24**、文案 400→500 且行框 14→16；"
    "卡片描边 border→**box-shadow 0 0 0 1px**（内容宽 356→358 · 操作链接左界 37→36 · 卡高 177→**178** · 卡顶 156/346/536/726/916）；"
    "标题行框 18→22.5 · 状态胶囊文字 13.2→16 · 单号标签 16→19.5 · 元信息行框 13→16；"
    "元信息行由单文本节点改为设计里的 **5 个节点（3 段 + 2 个分隔点，节点间 8px）**，分隔点用设计另一套浅灰 #CBD5E1（原实现 #94A3B8）；"
    "操作图标盒 16×16→**16×24**（形状入 ::before）· TabBar 图标盒 18×18→**22×33** · 列表底留白 108→112 · 待签署胶囊底色 **#FFFBEB → #FFFCEB**（design c426702b，先红后绿 1 条单测）。"
    "像素对账 cmp-序号8-设计PNGvs实现截图-色带.txt：内容列 **24/24** + 条列 **18/18** 全部命中（±10），位移中位 0/1（min −1 max +1）。"
    "交互相：?scenario=actions 两轮 → 点「已驳回」chip serve 实收 GET /api/v1/quotes?page=1&pageSize=10&status=REJECTED 且高亮 rgb(37,99,235)；"
    "点卡1「删除」→ 真实 uni-modal（取消/删除）→ 确认 → serve 实收 DELETE /api/v1/quotes/q1 200 → toast「已删除」→ 重拉列表；"
    "两轮请求行逐字节相同（requests-序号8-actions-run{1,2}.txt）。质量门：npm test **1172/1172 · 72 files 连跑两轮** · type-check exit 0 · "
    "build:mp-weixin 产物 pages/quotes/index.{js,json,wxml,wxss}（wxss 含 box-shadow:0 0 0 1px #eef2f7 / width:100px / font-weight:700 / line-height:16px）· "
    "build:h5 DONE · check-mock-fixtures FAIL 0 · review-artifacts 22/22 · 截图 logs/screenshots/20260916-序08-报价单列表-checks轮-h5-430宽.png"
)

NOTE = (
    "checks 轮设计帧重抓 2026-09-16 11:42（layer_id 56142177-5e03-487d-ba5d-3a5c3c3b4071）与留证逐字节比对："
    "**唯一差异 = 「新建按钮」width 97→100**（自动布局按子节点重算 12+18+4+54+12 = 100，与子节点自洽）→ 已按当前帧实现为 100 宽；其余节点逐字节相同。"
    "另：本页底部 TabBar 设计里在文档流内（1122..1206），实现为固定底栏 + 列表底留白 112 → 整页高度与设计帧一致（1206），"
    "截图载体页在 shot 模式把 iframe 高度设为 1206 使固定栏落在设计位置（否则像素对账会在 TabBar 带出现 35px 偏移）。"
)

raw = PATH.open(encoding="utf-8", newline="").read()
rows = list(csv.DictReader(raw.splitlines()))
fields = list(rows[0].keys())
hit = 0
for r in rows:
    if r["序号"] == "8":
        r["用例(证据)"] = (r["用例(证据)"] or "") + " ｜ " + CASE
        r["备注"] = (r["备注"] or "") + " ｜ " + NOTE
        hit += 1
print("命中行数 =", hit)
with PATH.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
print("written")
