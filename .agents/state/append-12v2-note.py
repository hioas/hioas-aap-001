# -*- coding: utf-8 -*-
"""序号 12-v2 checks 轮的台账回写（沿 append-ledger-note.py 的 ｜ 约定；长文本走文件避免引号问题）。"""
import csv
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
LEDGER = ROOT / ".agents/state/aap-feature-status.csv"

CASE = (
    "本轮 checks 维度（队列 8 第 14 页，2026-09-16 14:4x · cron 轮 aap-tdd-run-20260916-1420）："
    "新增载体页 __measure-quote-apikey.html（430 宽 iframe + **272 条设计期望值 checks**；由 build-probe-12v2.py 从 12-v1 载体页切"
    "「顶部作用域 / collect helpers / 溢出统计」三段骨架复用，只写本帧的 checks/return/phases）· "
    "want 两类来源：①design.tree.json 声明值（node-probe.py / text-lineheight.py / raw-node.py 逐节点读）"
    "②设计 PNG 430×1129 像素实测（png-rows.py / png-textbands.py 单列色带、x=34 竖条中心、x=390 盒边界、x=60 选项图标盒、x=90 面板行底）· "
    "红基线（git stash 复现修复前源码 + **最终版探针**两轮）6/272（red-序号12v2-checks-设计期望值偏差.txt）→ 绿 **0/272**"
    "（green-序号12v2-checks-设计期望值.txt）· 两轮独立测量 **35/35 字段全等**（不一致 0）· docScrollHeight 1127（设计帧 1128）· "
    "溢出 0 · 文案缺失 0 · 共用组件回归门 12-v1 同帧复跑 **286 条 · 0 失败**（docH 1241→1240，见备注）· "
    "交互相（?scenario=actions 两轮，serve 实收各 7 行逐字节相同）：首屏仅 GET /credentials → 选 c2 GET /credentials/c2 → "
    "chip「已选 1 / 2」+ 2 行模型 → 重开面板（选中行 #EFF6FF + 对勾 cred-check-c2 + 其余行仍显环境标）→ 收起 → 填名称（12/30）→ "
    "真实 POST /quotes{name,credential_id} + POST /quotes/q9/items → toast「保存成功」→ #/pages/model-pricing/index?quoteId=q9（落地页渲染）· "
    "?scenario=settings 两轮：点「前往「我的设置」新建凭证」→ **#/pages/settings/index 落地并渲染**（标题「账号与设置」· 落地页 toast 空）· "
    "质量门：npm test **1178/1178 · 72 files 连跑两轮** · type-check exit 0 · build:mp-weixin 产物 "
    "pages/quote-form/{index,apikey}.{js,json,wxml} + components/quote-form/QuoteFormView.wxss（含本轮设计值："
    "box-shadow:0 0 0 .8px #2563eb,0 12px 24px rgba(15,23,42,.1) · line-height:19px/17px/16px · width:17px;height:22.5px · "
    ".select--open .select__value{color:#94a3b8}）· build:h5 DONE · review-artifacts 22/22 · "
    "check-mock-fixtures --mock api-12-v2 **7/7 PASS**（新增本页 6 条 + 反向体检）· "
    "像素对账 cmp-序号12v2-设计PNGvs实现截图-结构带.txt 命中 54 / 未命中 4 · 截图 "
    "logs/screenshots/20260916-序12v2-新增报价单APIKey下拉展开-checks轮-h5-430宽.png（同件入 evidence/）· "
    "报告 evidence/review-序号12v2-checks-报告.md"
)

NOTE = (
    "本轮修掉 6 类设计偏差（先红后绿，逐条对应红基线失败项）："
    "①展开态占位文案色 #CBD5E1→**#94A3B8**（设计 324d1612；收起态 page-26 才是 #CBD5E1 —— 逐帧不同，加 .select--open 作用域，不动 12-v1）"
    "②下拉面板描边 **border→ring** 并补设计 effects：box-shadow: 0 0 0 .8px #2563EB, 0 12px 24px rgba(15,23,42,.1)"
    "（设计 stroke{align:center,0.8} 不占布局；原 border 实现既无投影又把内容宽挤掉 1.6px）"
    "③连带选项行宽 352→**354**、x 39→38（= 366 − 2×6；这是「面板内容宽」的直接证据）"
    "④面板底部操作图标盒 13×13→**17×22.5**（设计图层 w17 fs15；形状（13px 圆形加号）移入 ::before/::after，"
    "加号两笔用两层 linear-gradient 画，不新增节点）"
    "⑤选项行高 54→**55**：新增常量 **CRED_SUB_LINE_BOX = 16**（设计三个副行节点 7a442214/40b8ef3a/2958b233 都显式 h16，"
    "不是 11px×1.2=13.2；13.2 时选项信息 32.2 被 34 的图标盒接管）+ .panel__title line-height 16.8→**19**（后两行名称节点显式 h19）"
    "⑥标签行行盒 17.5→**17**（两帧共用；page-26 名称框顶回到设计值 276、page-apikey 195）｜ "
    "整体效果：面板 223→**225**（设计 225.5）· 卡1 628→**629**（设计 630）· docH 1126→**1127**（设计 1128）；"
    "对齐后 12-v1 docH 1241→1240（提示卡 CJK 换行 +2.5 的既有残差，非新增偏差）｜ "
    "**台账旧口径改正**：③⑦ 原写「/pages/settings/index（序号 23）未实现 → H5 实测 hash 不变」——本轮实测该页**已实现且注册在 pages.json**，"
    "点「前往「我的设置」新建凭证」确实跳转并渲染（标题「账号与设置」）；载体页原 phase4 落在此帧后导致保存流程 NOT_FOUND，"
    "已拆成 ?scenario=actions（选凭证→保存→模型定价，线性到底）与 ?scenario=settings（设置页落点）两个场景，各留两轮证据；"
    "并给 api-12-v2 补 v1/auth/me fixture（落地页 authApi.me；缺则落地页弹「数据加载失败」盖住落点证据），check-mock-fixtures 新增该条 ｜ "
    "**像素对账 4 条未命中的分诊**：y=485 = 设计帧自身的「首行画成选中态」矛盾（不照抄，改由真实选择驱动）· "
    "y=737/766/1008 = 卡1 底 748 vs 747 触发的 ≤1px 小数坐标链（x=200 逐行取色两侧一致：设计 741..747 白 + 748 起投影 vs 实现 736..746 白 + 747 起投影）"
    "· 均非页面缺陷 ｜ 设计帧重抓 2026-09-16 14:20：design.json sha256 29a2c80f… 与实现所依据的一份**逐字节相同**（无漂移）｜ "
    "探针自身 3 处口径 bug 已修并记入 red 转录：nav.left.gap 断错容器（改断「标题 x − 返回右界」）· "
    "cred.chevron.color / empty.glyph.color 读元素自身 color（D5 下图标是 CSS 占位形状，颜色在 ::before 的 border-color/background 上 → 新增 chkP 读伪元素）"
)

with LEDGER.open(encoding="utf-8", newline="") as fh:
    rows = list(csv.reader(fh))

SEP = " ｜ "
hit = 0
for r in rows:
    if r and r[0] == "12-v2":
        r[8] = (r[8] + SEP + CASE) if r[8] else CASE
        if len(r) > 10:
            r[10] = (r[10] + SEP + NOTE) if r[10] else NOTE
        r[9] = "部分"  # 仍有一条待人类拍板：本帧路由是否与 12-v1 合并（?panel=open）
        hit += 1
        break
if not hit:
    sys.exit("序号 12-v2 行未找到")

with LEDGER.open("w", encoding="utf-8", newline="") as fh:
    csv.writer(fh, lineterminator="\n").writerows(rows)
print("ledger row 12-v2 updated; cols:", len(rows[0]))
