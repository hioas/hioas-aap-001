# -*- coding: utf-8 -*-
"""append-1900-ring-note.py — 台账序号 1 行回写（本轮 center 描边→ring / 图标盒 / effects）。

用法: python .agents/state/append-1900-ring-note.py
然后 python .agents/state/normalize-ledger-eol.py + python .agents/state/validate-ledger-csv.py
"""
import csv
import subprocess
import sys
from pathlib import Path

PATH = Path(".agents/state/aap-feature-status.csv")

CASE = (
    "center 描边→ring + 输入框图标盒 + 设计 effects 2026-09-16 19:0x（cron aap-tdd-run-20260916-1900）：载体页 "
    "`__measure-login.html` 再扩 **32 条设计期望值 checks（合计 165 条 + phase5 勾选态 5 条）** —— "
    "红基线分两段（源码未改、同一份最终版探针两轮）：RED① **34/163** · RED②（补 effects 两条 checks）**2/165**，"
    "两轮红清单逐条相同 → 绿 **0/165 · 0/5**；两轮独立测量 42/42 字段全等、不一致 0 · `docH 1114` = 设计帧高 · 溢出 0 · 文案缺失 0。"
    "三处修正：①5 处 Figma `stroke{align:center}` 由 `border` 改 `box-shadow 0 0 0 1px`"
    "（`.field__box` ×3 · `.captcha` · `.sms-btn` · `.wechat` · `.agree__box`）—— 输入框内容左界 49→**48**（设计 48）、"
    "验证码块与获取验证码按钮左界 269→**270**（设计 270）；②3 个输入框图标盒 16×16→**20×27**（设计 df37d41e / 930dc950 / c59ce992 声明 w20 fs18），"
    "形状与颜色入 `::before`（手机 11×16 · 盾 15×17 · 锁 15×17 · 2px 描边 rgba(148,163,184,1)）—— "
    "占位文本左界 73→**76**（设计 76）、手机号输入框左界 123→**119**（竖分隔两侧 spacer 8/8，修前 `$gap-md=12`）、"
    "`+86` 固定 `width:25px`（设计 c825d0d3 声明宽 25）；③补设计 effects 两处投影（卡片 cab5940c 0/8/24 rgba(15,23,42,.08) · "
    "主按钮 7e26d478 0/8/20 rgba(37,99,235,.28)，由像素对账抓出：卡底 y891..911 设计 235→248 渐变/实现恒 248,250,252、"
    "按钮下 y721..740 设计 207,221,250→247,249,254/实现恒 255,255,255）。"
    "像素对账（设计 PNG 430×1114 vs 实现截图 430×1114，±3）：内容列 **命中 27 / 未命中 2**（修前 25/4）、条列 19/0，"
    "未命中仅 y914/920 = 设计导出图软染色 2/255 → 非页面缺陷；投影列 x=200 逐值：主按钮下 721/725/735 相同（730/740 ±1）· "
    "卡底 891/895/900 ±1 · 905 相同；行内墨迹段：手机号行 设计 52..62/76..99/109..110/119..202 = 实现 53..63/76..99/109..110/119..202"
    "（图标 ±1 = 20 宽盒内居中 11 宽字形的亚像素取整），验证码行与短信行文本 76..159 / 76..187 逐值相同。"
    "质量门：npm test **1182/1182 · 72 files 连跑两轮**（19:08:34 / 19:09:23）· type-check exit 0 · build:mp-weixin DONE"
    "（wxss 含 `box-shadow:0 0 0 1px #e2e8f0` ×2 / `#e0e7ff` / `#bfdbfe` / `#bbf7d0` · `border:2px solid #94a3b8` · "
    "`width:20px;height:27px` ×2 · `width:25px` · `box-shadow:0 8px 24px rgba(15,23,42,.08)` · `box-shadow:0 8px 20px rgba(37,99,235,.28)`）· "
    "build:h5 DONE · review-artifacts 22/22 · check-mock-fixtures --mock api FAIL 0（含反向体检）。"
    "命令 `bash .agents/state/review-measure.sh 1-ringred|1-effred|1-final __measure-login.html .agents/state/h5-measure/api 5321..5325` · "
    "证据 evidence/review-序号1-{ringred,effred,final}-run{1,2}.json · redgreen-序号1-ring图标盒投影-20260916.txt · "
    "review-序号1-ring-icon-checks-报告.md · 截图 evidence/20260916-1930-序01-登录注册-ring图标盒投影-h5-430宽.png"
)

NOTE = (
    "本页两个待办（16px 残差轮的 (a) 5 处 center 描边·(b) 3 个输入框图标盒）**已全部收口**，另发现并修掉设计 effects 缺失（卡片/主按钮投影）。"
    "定标（供同族输入框页复用）：①Figma `stroke{align:center}` 一律 `box-shadow 0 0 0 1px`（border 占布局、能差出 1~2px 并挤掉内容宽）；"
    "②输入框图标字形盒 = 设计声明宽 × 字号×1.5（20×27），形状按设计 PNG 墨迹画在 `::before`，颜色读 `::before` 的 `border-color`；"
    "③行内 spacer 用设计节点值（竖分隔两侧 8/8，不是 token `$gap-md=12`）；④文本左界是本轮最灵敏的几何指标（内容左界 48 + 图标盒 20 + spacer 8 = 76）。"
    "保持原样（有依据）：协议行勾选框默认未选中（设计帧画的是选中态，PRD 校验门 R-01/AC-01 要求显式勾选 → 状态差非几何差）；"
    "协议行文案设计为单叶子 4352f1e4 / 实现拆 3 节点着色（沿用登记待人类确认）。"
    "⚠️ 工具坑（已写进状态文件与报告）：apply 脚本只校验锚点唯一、不防重复插入 —— 先 `--probe-only` 再整跑会把同一段 checks 插两次"
    "（本轮实测 165→167、同名 check 两条），分两段跑的脚本落盘后必须复核 `grep -c` 与预期一致。"
)

raw = PATH.open(encoding="utf-8", newline="").read()
rows = list(csv.DictReader(raw.splitlines()))
fields = list(rows[0].keys())
hit = 0
for r in rows:
    if r["序号"] == "1":
        r["用例(证据)"] = (r["用例(证据)"] or "") + " ｜ " + CASE
        r["备注"] = (r["备注"] or "") + " ｜ " + NOTE
        hit += 1

with PATH.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)
print("回写 %d 行（序号 1 用例+备注）" % hit)

for cmd in (["normalize-ledger-eol.py"], ["validate-ledger-csv.py", "aap-feature-status.csv"]):
    out = subprocess.run([sys.executable, ".agents/state/" + cmd[0]] + cmd[1:],
                         capture_output=True, text=True, encoding="utf-8")
    print(out.stdout.strip()[-500:])
