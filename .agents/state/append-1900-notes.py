# -*- coding: utf-8 -*-
"""台账序号 1 / 8 行回写（本轮的审计 + 字重行盒修正 + 序号 8 判定登记）。

用法: python .agents/state/append-1900-notes.py
"""
import csv
from pathlib import Path

PATH = Path(".agents/state/aap-feature-status.csv")

CASE_1 = (
    "全量文本叶子审计 + 字重/行盒修正 2026-09-16 18:5x：新增维度「设计文本叶子 ↔ 实现 DOM computed」（textleaf-scan.py + "
    "textleaf-audit.py，22 页 / 1131 设计叶子 / 匹配 970），本页查出 **20 处声明不符**（此前载体页连一条字重检查都没有）。"
    "①字重（10 处，want = 设计 fontFamily：Bold 700 / SemiBold 600 / Medium 500）载体页新增 fw.* 10 条："
    "红 **10/103**（evidence/red-序号1-fw-字重偏差.txt）→ 绿 **0/103**；"
    "②行盒（10 处，want = 设计**显式 height**：fs20→28 · fs26→36 · fs14→24 · fs12→20 · fs13→18 · fs11→18 · fs14→16.8）"
    "载体页新增 be.* 10 条：红 **10/113**（be.brandName got 24 want 28 … be.placeholder got 19.6 want 16.8）→ 绿 **0/113**；"
    "两轮独立测量 phase1 **33/33 字段全等**、不一致 0。"
    "**整页 docScrollHeight 1085 → 1098**（+13 = 各盒声明差之和，几何按预期变化而非\"无感\"）。"
    "PNG 色带实测（png-textbands x=24..406，设计 430×1114）：修前品牌区逐带落后（设计 143..168/185..198/268..271 vs "
    "实现 142..167/180..193/260..263，标题 -1 · 副标题 -5 · 卡片顶 -8）→ 修后 **逐带与设计相同（±0）**。"
    "质量门：npm test **1182/1182 · 72 files ×2**（18:36:47 / 18:37:18）· type-check exit 0 · build:mp-weixin DONE"
    "（wxss 含 font-weight 700×4 / 600×2 / 500×4 · line-height 36/28×2/24/20×2/18×2/16.8/14.4）· build:h5 DONE · "
    "截图 evidence/20260916-序01-登录注册-行盒字重对齐-h5-430宽.png · 转录 evidence/redgreen-序号1-字重行盒-20260916.txt"
)

NOTE_1 = (
    "本页仍有 **16px 残差**（实现 1098 vs 设计帧 1114）：①首个字段标签前的间距比设计少 4px（设计 提示行 ink 339 → 字段标签 ink 367 = 28；实现 24）；"
    "②免责摘要正文设计为**两行**（叶子 e5e24331 fs12 h=40 = 2×20），实现渲染成一行（19.2）。下轮按同样口径（先红后绿 + PNG 色带）继续。"
    "另：协议行「我已阅读并同意《服务协议》与《隐私政策》」在设计里是**单个文本叶子**（4352f1e4，fs12 h=fit_content fw400），"
    "实现拆成 3 个节点（两个 agree__link 着色）→ 审计按「文本叶子精确匹配」判为未渲染，属结构差异，已登记待与人类确认是否保留链接着色。"
)

NOTE_8 = (
    "文本叶子审计（2026-09-16 18:5x）：本页 74 个设计文本叶子全部匹配，探针报 4 个 class 的「行盒 want=fs×lh1.2 与实际不符」"
    "（.quote-card__title 22.5 vs 18 · .quote-card__no-label 19.5 vs 15.6 · .quote-card__meta-part 16 vs 13.2 ×2 桶）。"
    "经 design PNG 实测**判定为非偏差**：卡 pitch 两侧同为 **190**（= 卡高 178 + 间距 12，scan-col x=215：设计白起 157/卡2 347、"
    "实现 156/346），即设计**渲染**出来的行盒就是 22.5/19.5/16（CJK fit_content 文本的自然行框），缩到 fs×1.2 会让卡高变 175.7、pitch 187.7 而与设计不符；"
    "卡内四条墨迹带（176..191 / 214..226 / 244..254 / 287..299）两侧逐条同位。已登记 evidence/textleaf-accept-序号8-png-pitch.txt + "
    "state/textleaf-accept.json（判定表，供后续轮次不再重复开庭）。"
)

raw = PATH.open(encoding="utf-8", newline="").read()
rows = list(csv.DictReader(raw.splitlines()))
fields = list(rows[0].keys())
hit = 0
for r in rows:
    if r["序号"] == "1":
        r["用例(证据)"] = (r["用例(证据)"] or "") + " ｜ " + CASE_1
        r["备注"] = (r["备注"] or "") + " ｜ " + NOTE_1
        hit += 1
    elif r["序号"] == "8":
        r["备注"] = (r["备注"] or "") + " ｜ " + NOTE_8
        hit += 1

with PATH.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)
print("回写 %d 行（序号 1 用例+备注 · 序号 8 备注）" % hit)
