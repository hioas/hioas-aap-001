# -*- coding: utf-8 -*-
"""序号 5（page-5-2 检测进行中 2）· 队列 8 checks 轮：台账追加（逻辑同 append-ledger-note.py，文本较长故落脚本）。

用法: python .agents/state/append-5-note.py
"""
import csv
from pathlib import Path

path = Path(".agents/state/aap-feature-status.csv")

CASE = (
    "队列 8 · 设计期望值 checks 维度（2026-09-16 10:42）：载体页 __measure-detecting.html 由 129 行旧体例重写为 430 宽 iframe + "
    "237 条 checks（want = page-5-2 design.json 声明值 + design PNG 色带/墨迹实测）· 红基线（git stash 复现修复前代码、同一份探针两轮）"
    "phase1/phase2 各 95/237、docH 900 → 绿 0/237、docH 934（= 设计帧高）· 两轮独立测量 32/32 字段全等（cmp-measure-runs.py，phase1+phase2 各一次）· "
    "交互相 ?scenario=interaction：点「查看历史检测报告」= client-only → toast「历史检测报告可在凭证列表中查看」· hashUnchanged true · 行数仍 8 · "
    "serve 实收 10 行全为成对 GET /detection-jobs/j1 + /results（5s 轮询 5 次）、零写请求 · "
    "命令 bash .agents/state/review-measure.sh 5-checks __measure-detecting.html .agents/state/h5-measure/api 5357 ｜ "
    "修后 npm test 1168/1168 ×2 · type-check exit 0 · build:mp-weixin 产物 pages/detecting/index.{js,json,wxml,wxss} · "
    "build:h5 + 430 宽截图 logs/screenshots/20260916-1042-序号5-检测进行中-checks轮-h5-430宽.png ｜ "
    "设计帧重抓 2026-09-16 10:27：design.json sha256 4ed8ad581e7b836037e3f4c07fe43c1e4411c60eabc1199f9b9ff678e7a1a792 与留证逐字节相同（无漂移）"
)

NOTE = (
    "队列 8 在 序号 5 修掉 9 类与设计稿的偏差（全部先红后绿）：①顶部栏 84→96（返回图标盒按设计 594997da 24×24→26×36 = fontSize 24 行框）；"
    "②卡1 184→196（标题行 24→26 = 「58%」line 26）；③卡2 416→434（行高 32→34、行距 44→46 = 13px 名 18 + 11px 详情 16）；"
    "④提示卡 68→72（文案行高 16.8→16 + align-self:center，设计 PNG ink 784..810 居中）；⑤成本块 52→58（标题/副文案行高→18/16）；"
    "⑥元信息行 14→18；⑦卡2/提示卡描边 border→box-shadow 0 0 0 1px（Figma center 描边不占布局；修前内容宽 356、行左 37、chip 右 393）；"
    "⑧卡1 补设计 effects drop_shadow(0,6,20,rgba(15,23,42,0.06))；⑨7 个图标盒按设计图层尺寸（26×36 / 22×30 / 20×27 / 22×30 / 22×30，形状移入 ::before）。"
    "像素对账（evidence/cmp-序号5-设计PNGvs实现截图-色带.txt，±1 容差）：x=62 列 41 个粗边界 36 命中，全部关键结构行命中"
    "（顶部栏 96 · 卡 108/749 · 进度条 170/180 · 成本块 226/284 · 提示卡 765/833 · 底栏 850/862/910 + 8 图标块 377…699）；"
    "未命中 22 行全为两类非页面缺陷：卡1 投影渐变台阶（Figma vs Chrome 衰减步长差异）与 H5 回退字体字形墨迹边界（块级几何与居中位置逐项相同，"
    "如底栏文案 ink 中心 设计 886.5 = 实现 886.5）。探针同轮自纠 2 处口径：norm() 数值直通（number 与 '32px' 不可比）、tip.textLines 改读 computed height。"
)

raw = path.open(encoding="utf-8", newline="").read()
rows = list(csv.DictReader(raw.splitlines()))
fields = list(rows[0].keys())
hit = 0
for r in rows:
    if r["序号"] == "5":
        r["用例(证据)"] = (r["用例(证据)"] or "") + " ｜ " + CASE
        r["备注"] = (r["备注"] or "") + " ｜ " + NOTE
        hit += 1

with path.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)

print("追加 %d 行 · 序号 5（case %d 字 / note %d 字）" % (hit, len(CASE), len(NOTE)))
