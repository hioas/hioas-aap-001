# -*- coding: utf-8 -*-
"""台账序号 12-v3 行回写：追加「设计期望值 checks 轮」证据到 用例(证据) 列 + 备注补充。

用法: python .agents/state/append-12v3-checks-note.py
（写完必须跑 normalize-ledger-eol.py 把行尾改回 LF）
"""
import io
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, '.agents/state/aap-feature-status.csv')

CASE_ADD = (
    ' · 📐 设计期望值 checks 轮（2026-09-16 15:0x · cron 轮 aap-tdd-run-20260916-1445）：新建/重写载体页 '
    '`.agents/state/h5-measure/__measure-quote-success.html`（430 宽 iframe + **259 条设计期望值 checks**，'
    '构建脚本 `build-probe-12v3.py` 切 12-v2 骨架；want 两类来源 = `design.tree.json` 声明值（新增 `dump-layout.py` 全字段 dump）'
    '+ 设计 PNG 430×1018 色带/文字带实测）。红基线（`git stash push -- success.vue` 复现修复前源码 + **同一份最终版探针**两轮）'
    '**30/259** · docH 1018 → 绿 **0/259**；两轮独立测量 **31/31 字段全等**（`cmp-measure-runs … phase1` 不一致 0）；'
    '`docScrollHeight 1018` = 设计帧高 · 溢出 0 · 文案缺失 0。'
    '修 4 类偏差：①**5 处 effects 投影缺**（三张卡 `drop_shadow(0,4,16,rgba(15,23,42,.06))` + 底栏 `(0,-4,16,.05)` '
    '+ 主按钮 `(0,6,16,rgba(37,99,235,.28))`）②**8 个图标占位盒按设计图层**（盒 = 声明宽 × 字号×1.5：返回 20×27 · 关闭 20×27 · '
    '成功勾 41×57 · 复制 16×21 · 单号绿勾 15×19.5 · 模型 18×24 · 提示 18×24 · 盾牌 20×27；形状入 `::before`，颜色改判伪元素）'
    '③**单号行右侧组 gap 8→4**（设计「单号值行」55b312e3 gap=4，与密钥行「密钥信息」gap=8 不同）'
    '④提示卡文案按单行渲染（行盒 13.2，卡高 48 由图标行盒 24 决定；旧注释「文案两行 26.4」作废）。'
    '像素对账 `cmp-bands-6`（±3）设计 PNG vs 实现 430×1018 截图：内容列 **35/35** + 条列 **15/15** = **50 命中 / 0 未命中**'
    '（`evidence/cmp-序号12v3-设计PNGvs实现截图-结构带.txt`；位移中位 0，min −3 max 2）。'
    '交互四出口两轮逐字节相同：`?scenario=copy` 剪贴板写 `QT-20240615-0007` + toast「报价单号已复制」（hash 不变、零写请求）· '
    '`?scenario=primary` → `#/pages/model-pricing/index?quoteId=q9` 渲染「模型定价」· '
    '`?scenario=secondary` / `?scenario=close` → `#/pages/quotes/index` 渲染 5 张卡片；每轮 serve 实收 2~3 行全为只读 GET。'
    '质量门：`npm test` **1178/1178 ×2** · `type-check` exit 0 · `build:mp-weixin` DONE（wxss 含 6 条 box-shadow、'
    '`width:20px;height:27px` ×3、`width:41px;height:57px`、`width:15px;height:19.5px`、`gap:4px`）· `build:h5` DONE · '
    '`review-artifacts` 22/22 · 共用组件回归门（12-v1 载体页 286 条 0 失败 · 12-v2 载体页 272 条 0 失败）· '
    '截图 `evidence/20260916-序12v3-新增报价单保存成功-checks轮-h5-430宽.png`'
)

NOTE_ADD = (
    '⑬**checks 轮（2026-09-16 15:0x）**：设计帧重抓（帧名「新增报价单-保存成功」+ layer_id '
    '`49d2fa52-959d-4415-9fda-edf38415d6bd`）→ `design.json` sha256 `cdd34a51…` **逐字节相同**（无漂移）；'
    '**fixture 缺口先红后绿**：两个出口的落地页缺 fixture（primary → 落地页取 `GET /api/v1/quotes/q9/items` 404；'
    'secondary/close → `GET /api/v1/quotes` 404 + toast「数据加载失败，请稍后重试」）→ 补 `api-12-v3/v1/quotes/q9/items/index`'
    '（同 12-v1）与 `api-12-v3/v1/quotes/index`（同 12）后两落地页 200、toast 空；`check-mock-fixtures.py --mock api-12-v3` '
    '新增 4 条检查 → **5 条 PASS（含反向体检）/ FAIL 0**。'
    '另：本页只读，四出口请求全部为 GET；「关闭/返回列表」两出口同落 /pages/quotes/index（本条已登记在⑥）。'
    '⚠️ 台账旧口径修正：『复制按钮 x320..384 h32 / 图标宽 12 vs 设计 16』已按设计图层改为盒 16×21、按钮右界 384 与设计一致（本轮 checks 断言 noBar.copy.right=384 · w=69±5）。'
)

with io.open(LEDGER, encoding='utf-8', newline='') as fh:
    rows = list(csv.reader(fh))

hdr = rows[0]
i_seq = hdr.index('序号')
i_case = hdr.index('用例(证据)')
i_note = hdr.index('备注')

hits = 0
for r in rows[1:]:
    if len(r) <= max(i_seq, i_case, i_note):
        continue
    if r[i_seq].strip() != '12-v3':
        continue
    if '设计期望值 checks 轮' in r[i_case]:
        print('已存在 checks 轮证据，跳过追加')
        hits = -1
        break
    r[i_case] = r[i_case].rstrip() + CASE_ADD
    r[i_note] = r[i_note].rstrip() + NOTE_ADD
    hits += 1

if hits == 0:
    raise SystemExit('未找到序号 12-v3 行')

if hits > 0:
    with io.open(LEDGER, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
        w.writerows(rows)
    print('台账序号 12-v3 行已回写（用例(证据) + 备注）')
