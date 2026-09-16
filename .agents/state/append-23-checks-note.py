#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""台账序号 23 行回写（checks 复核轮）。"""
import subprocess
import sys

CASE = (
    "复核通过 2026-09-16 16:5x（cron 轮接管死租约 aap-tdd-run-20260916-1630，该轮 16:36 中断留下未提交半成品）· "
    "430 宽 iframe 载体页 `__measure-settings.html` 由旧体例重写为 430 宽 iframe + "
    "**207 条设计期望值 checks**：红基线（重抓设计帧后、源码修复前 + 同一份最终版探针两轮）**1/207**（account.shadow）→ 绿 **0/207** · "
    "两轮独立测量 38/38 字段全等（不一致 0）· docH 797 = 设计帧高 · 溢出 0 · 文案缺失 0 · "
    "像素对账（设计 PNG 430×797 vs 实现截图 440×1000）**命中 25 / 未命中 4**（未命中 = 投影衰减 4，非页面缺陷；位移中位 0）· "
    "7 交互出口全量两轮 requests 逐字节相同（back/hash不变/3卡 · identity → #/pages/profile/index(landing render) · legal no-op · "
    "account no-op · toggle true→false(blue→gray, client-only, 零写请求) · logout modal→confirm→POST /auth/logout→reLaunch 登录页 · "
    "logout-cancel modal→cancel→hash不变）· "
    "`check-mock-fixtures --mock api-23` **2 PASS + 反向体检 PASS / FAIL 0**（本轮新补 2 条）· `review-artifacts` 22/22 · "
    "npm test **1181/1181 ×2** · type-check exit 0 · build:mp-weixin 产物 pages/settings/{index.js,json,wxml,wxss} · "
    "截图 `.agents/state/evidence/20260916-序23-账号与设置-checks轮-h5-430宽.png`（430×797 = 设计帧高）· "
    "设计帧重抓 sha256 逐字节相同（无漂移）· "
    "队列 8 全部收尾（20 个载体页 checks 维度全覆盖）"
)

NOTE = (
    "接管死租约后的修复项：①死轮 1630 已补 CSS `.card--account {box-shadow:...}` 但未重建 H5 验证 → 接手续跑后杯绿 0/207 "
    "②shot-430.sh 默认 mock 为 `api` 而非 `api-23`，首张截图 render 异常（44451 vs 37827 bytes）→ 改用 api-23 后像素对账从 8 未命中降到 4 "
    "③已给 api-23 补 `provider/profile` + `provider/qualifications/index`（identity 场景落点页取数）并为 base `api` mock 清理新增的 `auth/me`（从 api-23 复制后回删）"
    "④`check-mock-fixtures.py` 新增 2 条 api-23 check（GET /auth/me / POST /auth/logout）"
    "⑤像素对账 4 条未命中全部为投影衰减（与之前所有页同族）：y=107 账号卡顶部投影带（D 245/248 vs I 246/249, ≤1/255）· y=345/348 通知卡顶部设计渐变 340..353（图 242/247→254/254）vs 实现纯白 343+（Chrome shadow decay 更快）"
    "⑥其 docH task 归零：队列 8 20 个载体页全部完成 cap. 下轮做队列 1 逐页复核（余下行的 checks 维度）"
)

cmd = [sys.executable, ".agents/state/append-ledger-note.py", "23", "--case", CASE, "--note", NOTE]
print(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout)
print(subprocess.run([sys.executable, ".agents/state/normalize-ledger-eol.py"], capture_output=True, text=True, encoding="utf-8").stdout)