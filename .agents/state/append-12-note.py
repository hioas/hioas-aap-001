# -*- coding: utf-8 -*-
"""序号 12 checks 轮的台账回写（沿 append-ledger-note.py 的 ｜ 分隔约定，长文本走文件避免引号问题）。"""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
LEDGER = ROOT / ".agents/state/aap-feature-status.csv"

CASE = (
    "本轮 checks 维度（队列 8 第 12 页，2026-09-16 13:5x · cron 轮 aap-tdd-run-20260916-1330）："
    "__measure-quote-preview.html 由 241 行旧体例重写为 430 宽 iframe + 126 条设计期望值 checks"
    "（want = design.tree.json 声明值 + 设计 PNG 430×1027 像素实测）· "
    "红基线（git stash 复现修复前源码 + 同一份探针两轮）10/126（red-序号12-checks-设计期望值偏差.txt）→ 绿 0/126"
    "（green-序号12-checks-设计期望值.txt）· 两轮独立测量 24/24 字段全等 · docScrollHeight 1027 = 设计帧高 · "
    "溢出 0 · 文案缺失 0 · 单测红 4 failed（red-序号12-checks-结构用例.txt）→ 全量 npm test 1178/1178 连跑两轮 · "
    "type-check exit 0 · build:mp-weixin 产物 pages/quote-preview/index.{js,json,wxml,wxss}（wxss 含 .card--lead 投影 / "
    ".rule--compact{height:40px} / height:38px / line-height:13.2px / min-height:56px）· 像素对账 "
    "cmp-序号12-设计PNGvs实现截图-结构带.txt 命中 55 / 未命中 3（均为投影衰减步长与 AA 阈值，非页面缺陷）· "
    "报告 evidence/review-序号12-checks-报告.md · 截图 logs/screenshots/20260916-序12-报价预览与提交-checks轮-h5-430宽.png"
)

NOTE = (
    "本轮修掉 7 类设计偏差（先红后绿）：①卡片效果按设计逐卡不同——卡1 drop_shadow(0,6,20,rgba(15,23,42,.06)) 无描边、"
    "卡2/卡3/确认卡 stroke 1px #EEF2F7 无投影（修前四卡统一 ring；PNG 佐证：卡1 下方 381..391 有投影染色、x=16 行内无描边像素）"
    "②基础价行 34→38（标签盒 12→16、line-height 16，= 设计显式 height 16/22；PNG 标签墨迹 170..179 中心 = 盒 167..183 中心）"
    "③规则行按类型分行高：请求规则行 40（内容 20）、峰谷/阶梯行 44（内容 24）——模型侧新增 RuleKind，页面加 .rule--compact"
    "（PNG #F8FAFC 色带 217..260/269..312/**321..360**、501..544/**553..592**/**729..768**）"
    "④请求规则行文字行框 13.2（设计墨迹位于行顶 +11）、峰谷/阶梯行 18（+13）"
    "⑤.rule__wrap 去掉 min-height:24px + align-items:center（它把 11px 行框在 24 高盒里居中 → 整行墨迹下沉 3.5px，"
    "像素对账抓出；设计该容器是 alignItems=start 的行）⑥确认行 22→19（= fs12 行框 19.2；提示条顶回到 851=800+20+19+12）"
    "⑦提示条 53→56（文本行框 16.5→18，= 10+2×18+10；PNG #FFFBEB 851..906）｜ "
    "设计骨架定标（PNG 实测，供同族长页复用）：顶部导航 96 · 卡 108/392/624/800 · 卡 padding 20 r16 · 头行 26 · "
    "基础价行 = 标签 16 + 值 22 · 规则行 = padding 10 + max(图标盒, 文本行框) + 10 · 确认行 = fs12 行框 19.2 · "
    "提示条 = padding 10 + n×18 + 10 ｜ "
    "fixture 缺口（先红后绿）：提交成功落地 /pages/quotes/index 会取 GET /api/v1/quotes?page=1&pageSize=10，api-12 缺该 fixture "
    "→ 首轮实测 404 且落地页 toast「数据加载失败，请稍后重试」盖掉提交成功 toast；补 api-12/v1/quotes/index（从 api 同款拷贝）后 200，"
    "toast 采样点移到跳转前 → 「已提交审核」；check-mock-fixtures --mock api-12 该条 FAIL→PASS ｜ "
    "交互相两轮逐字节相同：取消勾选后提交 → toast「请先确认报价条款」+ hash 不变 + 零写请求；重新勾选 → 真实 "
    "POST /api/v1/quotes/q7/submit（body 为空）→ toast「已提交审核」→ #/pages/quotes/index（列表渲染）｜ "
    "⚠️ 台账原备注⑦⑧⑫ 的口径已按当前帧更新：设计里卡1 无 stroke（原「四卡统一 ring」为当时的偏差口径）、"
    "请求规则行 40（原备注⑩的「价格行取 34」系按旧模型反推，本轮按 PNG 色带 321..360 与声明值 16+22 重新定标为 38）"
)

with LEDGER.open(encoding="utf-8", newline="") as fh:
    rows = list(csv.reader(fh))

SEP = " ｜ "
hit = 0
for r in rows:
    if r and r[0] == "12":
        r[8] = (r[8] + SEP + CASE) if r[8] else CASE
        if len(r) > 10:
            r[10] = (r[10] + SEP + NOTE) if r[10] else NOTE
        hit += 1
        break
if not hit:
    sys.exit("序号 12 行未找到")

with LEDGER.open("w", encoding="utf-8", newline="") as fh:
    csv.writer(fh, lineterminator="\n").writerows(rows)
print("ledger row 12 updated; cols:", len(rows[0]))
