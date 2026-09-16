"""Build __measure-mine.html (序号 21 · page-21-2「【工作台与我的】我的 2」) as a
430-wide iframe probe with design-expectation checks (chk/chkR/chkC/chkD/chkP/chkList/chkStrs).

做法与 build-probe-10/11/12/12v2/12v3/15/20 同：从 __measure-messages.html（同族载体页，含
`resolveAll` / `declared` / `normShadow` / `pseudoStyle` 等全套 helpers）切四段「与帧无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计 / sink+phase+点击工具）逐字节复用，
本文件只写 page-21-2 自己的 checks / return / main。

want 两类来源（先量再写，不凭截图目测）：
  (a) 声明值 .calicat/raw/pages/page-21-2/{design.json,design.tree.json}
      python .agents/state/dump-layout.py page-21-2      # 全字段（padding/gap/lineHeight/stroke/effects/圆角）
      python .agents/state/text-fields.py page-21-2      # 文本叶子 fontSize/字重/字色/宽高/文案
  (b) 设计截图 PNG 实测（430×990；本轮重抓设计帧 design.json sha256 cd12a92b… 逐字节相同）
      python .agents/state/ink-bbox.py <png> 36,364,68,396           # 行图标墨迹 43..59 × 373..388
      python .agents/state/ink-runs.py <png> 70 400 360 400 30 2     # 行标签 / 值 / chevron 的 x 段
      python .agents/state/stroke-rows.py <png> eef2f7 8 150 20 410 0 990   # 三张卡上下边界
      python .agents/state/scan-col.py <png> 25 136 340 6            # 钱包卡内上下内边距
      python .agents/state/scan-row.py <png> 293 200 240 10          # 竖分隔 x=214..215
      python .agents/state/ink-runs.py <png> 0 430 916 950 30 2      # TabBar 图标墨迹

设计骨架（逐条与 PNG 墨迹对过）：
  用户头部 0..128（padding 48/16/24/16 · 头像 56 r28 @x16 · 信息块 padding-left 12 ·
            公司行 h26 · 标签行 padding-top 8 → 82..104 · 类型标签 h22 r11 @84..134 · 状态标签 h22 @143..206）
  钱包卡 140..332（192 = 20 + 标题行 30 + 16 + 余额行 52 + 16 + 明细行 38 + 20 · r18 · ring #EEF2F7）
            余额行 = 标签 h16 + padding-top 2 + 金额 h34；明细行 = 标签 h16 + 值 h22；竖分隔 2×32 @214
  报价入口卡 344..643（299 = 8 + 5×56 + 3×1 + 8 · r18）行顶 352/409/466/523/579 · 分隔 408/465/522
            行内：图标盒 32×32 r10 @x36 · 字形盒 20×27 · 标签 ink x78 · 值右边 368 · chevron 盒 372..394
  主体与证照卡 655..890（235 = 8 + 4×54 + 3×1 + 8）行顶 663/718/773/828 · 分隔 717/772/827
            行内：字形盒 20×27 @x36 · 标签 ink x66 · 值/pill 右边 368 · chevron 盒 372..394
  底部 TabBar 906..990（84 = 8 + 图标块 33 + 3 + 文字 16 + 24 · 4 项各 104 · space_between · 高亮「我的」#2563EB）
  ?scenario=withdraw|rows-quotes|usage|settings|tab-workbench|tab-mine 逐个回放出口；
  不带 scenario（或 noaction / shot=1）只取 phase1 设计期望值相。

本页定标（与 §5.13 一致，并补两条）：
  · 图标字形盒 = 声明宽 × 字号×1.5（行图标 fs18 声明 w20 → 20×27；TabBar fs22 → 33；头像 fs30 声明 w33 → 33×45），
    形状画在盒内（D5 占位），颜色落在伪元素上（读元素 color 会得 rgb(0,0,0) → 探针口径 bug）。
  · 文本行盒：**设计显式 height 优先**（公司 26 · 余额标签 16 · 金额 34 · 明细值 22 · 可提现余额 16）；
    无显式 height 走设计 `lineHeight 1.2`（14 → 16.8 · 13 → 15.6 · 12 → 14.4 · 11 → 13.2 · 10 → 12）。
  · stroke{align:center,thickness:1} → box-shadow: 0 0 0 1px（border 会占布局）· 三张卡均无 effects。
"""

import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-messages.html")
DST = os.path.join(HM, "__measure-mine.html")

with io.open(SRC, encoding="utf-8") as fh:
    src = fh.read().split("\n")


def find(needle, start=0):
    for i in range(start, len(src)):
        if needle in src[i]:
            return i
    raise SystemExit("not found: " + needle)


i_var = find("var f = document.getElementById('f')")
i_collect = find("function collect(doc, win, withChecks) {")
i_over = find("/* ============ 溢出")
i_checks = find("/* ===================== 整页", i_over)
i_sink = find("function sink(n, payload) {")
i_main = find("async function main() {")

top = "\n".join(src[i_var:i_collect])
top = top.replace(
    "if (SHOT_ONLY) f.style.height = '760px' /* = 设计帧高 */",
    "if (SHOT_ONLY) f.style.height = '990px' /* = 设计帧高 */",
)
assert "'990px'" in top, "SHOT 高度替换失败（顶部作用域切片变了？）"
preamble = "\n".join(src[i_collect:i_over])   # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])    # over / missing 统计（引用 NEED_TEXT / CARDS）
tail = "\n".join(src[i_sink:i_main])          # sink / phase / clickIn / toastText / hashNow / waitFor / sleep / textIn / countIn / bgsIn
assert "f.style.height = '760px'" in tail, "phase() 取数高度锚变了（应把 760 改成 990）"
tail = tail.replace("f.style.height = '760px'", "f.style.height = '990px'")

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-mine</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      /* iframe 取数高度 = 设计帧高 990：页面 min-height:100vh 会把测量高度顶到 iframe 高，
         990 时 docScrollHeight 恰好等于设计帧高（TabBar fixed 在 906..990）。 */
      iframe { width: 430px; height: 990px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜（uni-app 技能 §5 口径）
         页面 21：/pages/mine/index（【工作台与我的】我的 2，page-21-2 · layer_id e537204e-faf7-416b-8669-1347d581490c）
         设计真源：.calicat/raw/pages/page-21-2/design.tree.json（本轮重抓 sha256 cd12a92b… 逐字节相同）
         设计骨架（声明值 + 设计 PNG 430x990 实测）：
           用户头部 0..128（padding 48/16/24/16 · 头像 56 r28 @x16 · 信息块 padding-left 12 ·
                     公司行 h26 · 标签行 padding-top 8 · 类型标签 h22 r11 · 状态标签 h22 #DBEAFE）
           钱包卡 140..332（192 · r18 · ring #EEF2F7 · 标题行 30 · 余额行 52 · 明细行 38 · 竖分隔 2×32 @214）
           报价入口卡 344..643（299 = 8 + 5×56 + 3×1 + 8 · 行顶 352/409/466/523/579 · 分隔 408/465/522）
           主体与证照卡 655..890（235 = 8 + 4×54 + 3×1 + 8 · 行顶 663/718/773/828 · 分隔 717/772/827）
           底部 TabBar 906..990（84 · 4 项各 104 · space_between · 高亮「我的」#2563EB / SemiBold 600）
         ?scenario=withdraw|rows-quotes|usage|settings|tab-workbench|tab-mine 逐个回放出口；
         不带 scenario（或 noaction / shot=1）只取 phase1 设计期望值相 -->
    <iframe id="f" src="/index.html#/pages/mine/index"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

PRELUDE = r"""
        var CARDS = '.card'
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-21-2 design.tree.json；
           图标字形层 content 是 remixicon 私有码位（\uf274 之类）→ 不进清单）。
           值文案与 mock（api-21）一致：3 个 / 2 份 / 待签署 1 / 3 条 / 待阅读 3 / 100% / ¥12,860.00 …
           「待阅读 3」的设计字色是 rgba(0,0,0,1)（与同卡其它值 #94A3B8 不同）→ 逐值断言，不统一。 */
        var NEED_TEXT = [
          '云智科技有限公司', '渠道商', '已认证',
          '我的钱包', '可提现余额', '¥12,860.00', '提现', '待结算', '¥3,240', '累计结算', '¥86,420',
          '我的报价单', '3 个', '检测报告', '2 份', '我的合同', '待签署 1', '用量与对账', '我的消息', '待阅读 3',
          '主体档案', '100%', '接入凭证', '3 条', '结算账户', '已绑定', '账号与设置',
          '工作台', '报告', '报价', '我的'
        ]
"""

CHECKS = r"""
        /* ===================== 整页（设计帧 430×990） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 990, 2) /* 128+12+192+12+299+12+235+100(底部留白) */
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.mine', 'backgroundColor', 'rgb(248, 250, 252)') /* 我的页 c7f9938f fills rgba(248,250,252,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 3)
        chk('page.inputCount', doc.querySelectorAll('input,textarea').length, 0)
        chkC('page.padBottom', '.mine', 'paddingBottom', 100) /* 卡3 止于 890 + 16 间隙 + TabBar 84 */

        /* ===================== 用户头部（design ab268cad padding[48,16,24,16] · #1D4ED8） ===================== */
        chkR('head.top', '.head', 0, 1)
        chkR('head.h', '.head', 128, 1) /* 48 + 头像 56 + 24（PNG 0..127 蓝底） */
        chkR('head.w', '.head', 430, 1)
        chkC('head.pad', '.head', 'padding', '48px 16px 24px')
        chkC('head.bg', '.head', 'backgroundColor', 'rgb(29, 78, 216)')
        chkC('head.align', '.head', 'alignItems', 'center')
        chkR('head.avatar.x', '.head__avatar', 16, 1)
        chkR('head.avatar.top', '.head__avatar', 48, 1)
        chkR('head.avatar.w', '.head__avatar', 56, 1)
        chkR('head.avatar.h', '.head__avatar', 56, 1)
        chkC('head.avatar.radius', '.head__avatar', 'borderRadius', '28px')
        chkC('head.avatar.bg', '.head__avatar', 'backgroundColor', 'rgb(255, 255, 255)')
        /* 头像字形盒 = 设计 85003c7e fs30 声明 w33 × 行盒 30×1.5（形状画在盒内，D5） */
        chkR('head.avatarGlyph.w', '.head__avatar-glyph', 33, 1)
        chkR('head.avatarGlyph.h', '.head__avatar-glyph', 45, 1)
        chk('head.info.padLeft', css('.head__info', 'paddingLeft'), 12) /* container 814906bc padding-left 12 */
        chkR('head.company.x', '.head__company', 84, 1) /* 16 + 56 + 12（PNG 公司墨迹左界 84） */
        chkC('head.company.fs', '.head__company', 'fontSize', 18) /* bf25e2d2 fs18 Bold h26 */
        chkC('head.company.fw', '.head__company', 'fontWeight', 700)
        chkC('head.company.lh', '.head__company', 'lineHeight', 26) /* 设计显式 height 26 */
        chkC('head.company.color', '.head__company', 'color', 'rgb(255, 255, 255)')
        chkStrs('head.company.text', [textOf('.head__company')], ['云智科技有限公司'])
        chkC('head.tags.padTop', '.head__tags', 'paddingTop', 8) /* a3c59082 padding-top 8 */
        chkR('head.tags.top', '.head__tags', 74, 1) /* 48 + 公司行 26（容器本身含 padding，设计是「容器 + 子行」两层） */
        chkR('head.type.top', '.head__type', 82, 1) /* 容器 padding-top 8 → 标签行 82..104（PNG 82..104） */
        chkR('head.type.x', '.head__type', 84, 1)
        chkR('head.type.h', '.head__type', 22, 1) /* 4cd966ac h22 r11 padding[0,8] */
        chkC('head.type.pad', '.head__type', 'padding', '0px 8px')
        chkC('head.type.radius', '.head__type', 'borderRadius', '11px')
        chkC('head.type.bg', '.head__type', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('head.typeText.fs', '.head__type-text', 'fontSize', 11) /* dec24f88 fs11 SemiBold #1D4ED8 */
        chkC('head.typeText.fw', '.head__type-text', 'fontWeight', 600)
        chkC('head.typeText.lh', '.head__type-text', 'lineHeight', 13.2, 0.2) /* 无显式 height → 设计 1.2 × 11 */
        chkC('head.typeText.color', '.head__type-text', 'color', 'rgb(29, 78, 216)')
        chkStrs('head.typeText.text', [textOf('.head__type')], ['渠道商'])
        chk('head.tagGap', rect('.head__verified').x - rect('.head__type').right, 9, 2) /* spacer d156b34f w9 */
        chkR('head.verified.h', '.head__verified', 22, 1) /* 0c3b8278 h22 r11 padding[0,8] */
        chkC('head.verified.pad', '.head__verified', 'padding', '0px 8px')
        chkC('head.verified.radius', '.head__verified', 'borderRadius', '11px')
        chkC('head.verified.bg', '.head__verified', 'backgroundColor', 'rgb(219, 234, 254)')
        chkR('head.dot.w', '.head__dot', 9, 1) /* deef00f5 9×7 r4 rgba(22,163,74,1) */
        chkR('head.dot.h', '.head__dot', 7, 1)
        chkC('head.dot.radius', '.head__dot', 'borderRadius', '4px')
        chkC('head.dot.bg', '.head__dot', 'backgroundColor', 'rgb(22, 163, 74)')
        chkC('head.verifiedText.lh', '.head__verified-text', 'lineHeight', 13.2, 0.2) /* ba4503ea fs11 Medium */
        chkC('head.verifiedText.fs', '.head__verified-text', 'fontSize', 11)
        chkC('head.verifiedText.fw', '.head__verified-text', 'fontWeight', 500)
        chkC('head.verifiedText.color', '.head__verified-text', 'color', 'rgb(30, 64, 175)')
        chkStrs('head.verifiedText.text', [textOf('.head__verified')], ['已认证'])
        chk('head.verifiedText.padLeft', css('.head__verified-text', 'marginLeft'), 4) /* b072ec21 padding-left 4 */

        /* ===================== 我的钱包卡（design 0a649e83 padding 20 r18 · stroke 1px #EEF2F7） ===================== */
        chkR('wallet.x', '.card--wallet', 16, 1)
        chkR('wallet.top', '.card--wallet', 140, 1) /* PNG 描边行 139/140 */
        chkR('wallet.w', '.card--wallet', 398, 1)
        chkR('wallet.h', '.card--wallet', 192, 1) /* 20+30+16+52+16+38+20（PNG 卡 140..332） */
        chkC('wallet.pad', '.card--wallet', 'padding', '20px')
        chkC('wallet.radius', '.card--wallet', 'borderRadius', '18px')
        chkC('wallet.bg', '.card--wallet', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('wallet.ring', '.card--wallet', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('wallet.borderDeclared', '.card--wallet', 'border', null) /* 反向断言：中心描边只能用 ring 表达 */
        chkR('wallet.titleRow.top', '.wallet__title-row', 160, 1) /* 140 + 20 */
        chkR('wallet.titleRow.h', '.wallet__title-row', 30, 1) /* = chevron 字形行盒 fs20×1.5 */
        chkC('wallet.titleRow.align', '.wallet__title-row', 'alignItems', 'center')
        chkR('wallet.title.x', '.wallet__title', 36, 1) /* 卡内 padding 20（PNG 标题墨迹 36..91） */
        chkC('wallet.title.fs', '.wallet__title', 'fontSize', 14) /* a5722e5c fs14 SemiBold */
        chkC('wallet.title.fw', '.wallet__title', 'fontWeight', 600)
        chkC('wallet.title.lh', '.wallet__title', 'lineHeight', 16.8, 0.2) /* 无显式 height → 设计 1.2 × 14 */
        chkC('wallet.title.color', '.wallet__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('wallet.title.text', [textOf('.wallet__title')], ['我的钱包'])
        chkR('wallet.chev.x', '.wallet__title-row .chevron', 372, 1) /* 图层 ccc682aa w22 → 盒 372..394 */
        chkR('wallet.chev.right', '.wallet__title-row .chevron', 394, 1)
        chkR('wallet.chev.w', '.wallet__title-row .chevron', 22, 1)
        chkR('wallet.chev.h', '.wallet__title-row .chevron', 30, 1)
        chkR('wallet.balRow.top', '.wallet__balance-row', 206, 1) /* container eea35add padding-top 16 */
        chkR('wallet.balRow.h', '.wallet__balance-row', 52, 1) /* 标签 16 + 2 + 金额 34 */
        chkR('wallet.balBlock.x', '.wallet__balance', 36, 1)
        chkR('wallet.balBlock.w', '.wallet__balance', 134, 1)
        chkR('wallet.label.h', '.wallet__label', 16, 1) /* 6c6918a9 fs11 h16（显式） */
        chkC('wallet.label.fs', '.wallet__label', 'fontSize', 11)
        chkC('wallet.label.fw', '.wallet__label', 'fontWeight', 400)
        chkC('wallet.label.lh', '.wallet__label', 'lineHeight', 16)
        chkC('wallet.label.color', '.wallet__label', 'color', 'rgb(148, 163, 184)')
        chkStrs('wallet.labels', texts('.wallet__label'), ['可提现余额', '待结算', '累计结算'])
        chkR('wallet.amount.h', '.wallet__amount', 34, 1) /* 13b1f830 fs24 ExtraBold h34（显式） */
        chkC('wallet.amount.fs', '.wallet__amount', 'fontSize', 24)
        chkC('wallet.amount.fw', '.wallet__amount', 'fontWeight', 800)
        chkC('wallet.amount.lh', '.wallet__amount', 'lineHeight', 34)
        chkC('wallet.amount.color', '.wallet__amount', 'color', 'rgb(15, 23, 42)')
        chk('wallet.amount.marginTop', css('.wallet__amount', 'marginTop'), 2) /* container 72781c25 padding-top 2 */
        chkStrs('wallet.amount.text', [textOf('.wallet__amount')], ['¥12,860.00'])
        chkR('wallet.withdraw.top', '.withdraw', 213, 1) /* 余额行 206..258 内 38 高居中（PNG 213..250 蓝底） */
        chkR('wallet.withdraw.h', '.withdraw', 38, 1)
        chkR('wallet.withdraw.right', '.withdraw', 394, 1)
        chkC('wallet.withdraw.radius', '.withdraw', 'borderRadius', '10px')
        chkC('wallet.withdraw.pad', '.withdraw', 'padding', '0px 16px')
        chkC('wallet.withdraw.bg', '.withdraw', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('wallet.withdrawText.fs', '.withdraw__text', 'fontSize', 13) /* 1926f470 fs13 Medium #FFF */
        chkC('wallet.withdrawText.fw', '.withdraw__text', 'fontWeight', 500)
        chkC('wallet.withdrawText.lh', '.withdraw__text', 'lineHeight', 15.6, 0.2)
        chkC('wallet.withdrawText.color', '.withdraw__text', 'color', 'rgb(255, 255, 255)')
        chkStrs('wallet.withdrawText.text', [textOf('.withdraw')], ['提现'])
        chkR('wallet.detailRow.top', '.wallet__detail-row', 274, 1) /* container 2987a1a1 padding-top 16 */
        chkR('wallet.detailRow.h', '.wallet__detail-row', 38, 1) /* 标签 16 + 值 22 */
        chkR('wallet.detail1.x', '.wallet__detail@@0', 36, 1)
        chkR('wallet.detail1.w', '.wallet__detail@@0', 178, 1)
        chkR('wallet.detail2.x', '.wallet__detail@@1', 216, 1)
        chkR('wallet.detail2.w', '.wallet__detail@@1', 178, 1)
        chkR('wallet.divider.x', '.wallet__divider', 214, 1) /* c487a7ed 2×32 rgba(226,232,240,1)（PNG 214..215） */
        chkR('wallet.divider.w', '.wallet__divider', 2, 1)
        chkR('wallet.divider.h', '.wallet__divider', 32, 1)
        chkR('wallet.divider.top', '.wallet__divider', 277, 2)
        chkC('wallet.divider.bg', '.wallet__divider', 'backgroundColor', 'rgb(226, 232, 240)')
        chkR('wallet.sub.h', '.wallet__sub-amount', 22, 1) /* 20477709 fs14 SemiBold h22（显式） */
        chkC('wallet.sub.fs', '.wallet__sub-amount', 'fontSize', 14)
        chkC('wallet.sub.fw', '.wallet__sub-amount', 'fontWeight', 600)
        chkC('wallet.sub.lh', '.wallet__sub-amount', 'lineHeight', 22)
        chkC('wallet.sub.color', '.wallet__sub-amount', 'color', 'rgb(15, 23, 42)')
        chkStrs('wallet.subs', texts('.wallet__sub-amount'), ['¥3,240', '¥86,420'])

        /* ===================== 我的报价入口卡（design cda20980 padding 8/20 · 5 行 ×56 + 3×1） ===================== */
        chkR('entries.x', '.card--entries', 16, 1)
        chkR('entries.top', '.card--entries', 344, 1) /* PNG 描边行 343/344 */
        chkR('entries.w', '.card--entries', 398, 1)
        chkR('entries.h', '.card--entries', 299, 1) /* 8 + 5×56 + 3×1 + 8（PNG 344..643） */
        chkC('entries.pad', '.card--entries', 'padding', '8px 20px')
        chkC('entries.radius', '.card--entries', 'borderRadius', '18px')
        chkC('entries.ring', '.card--entries', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('entries.borderDeclared', '.card--entries', 'border', null)
        chk('entries.rowCount', doc.querySelectorAll('.card--entries .row').length, 5)
        chkList('entries.rowTops', rects('.card--entries .row').map(function (r) { return r.top }), [352, 409, 466, 523, 579], 1)
        chkList('entries.rowH', rects('.card--entries .row').map(function (r) { return r.h }), [56, 56, 56, 56, 56], 1)
        chkList('entries.rowX', rects('.card--entries .row').map(function (r) { return r.x }), [36, 36, 36, 36, 36], 1)
        chkList('entries.rowW', rects('.card--entries .row').map(function (r) { return r.w }), [358, 358, 358, 358, 358], 1)
        chk('entries.rowPadY', css('.card--entries .row', 'paddingTop'), 12) /* 569aae67 padding[12,0,12,0] */
        chk('entries.sepCount', doc.querySelectorAll('.card--entries .row__sep').length, 3) /* 设计 kids 只有 横分隔1~3 */
        chkList('entries.sepTops', rects('.card--entries .row__sep').map(function (r) { return r.top }), [408, 465, 522], 1)
        chkList('entries.sepH', rects('.card--entries .row__sep').map(function (r) { return r.h }), [1, 1, 1], 1)
        chkC('entries.sep.bg', '.card--entries .row__sep', 'backgroundColor', 'rgb(241, 245, 249)') /* 645b78b6 rgba(241,245,249,1) */
        chk('entries.iconCount', doc.querySelectorAll('.card--entries .row__icon').length, 5)
        chkList('entries.iconTops', rects('.card--entries .row__icon').map(function (r) { return r.top }), [364, 421, 478, 535, 591], 1)
        chkList('entries.iconX', rects('.card--entries .row__icon').map(function (r) { return r.x }), [36, 36, 36, 36, 36], 1)
        chkList('entries.iconW', rects('.card--entries .row__icon').map(function (r) { return r.w }), [32, 32, 32, 32, 32], 1)
        chkList('entries.iconH', rects('.card--entries .row__icon').map(function (r) { return r.h }), [32, 32, 32, 32, 32], 1)
        chkC('entries.icon.radius', '.card--entries .row__icon', 'borderRadius', '10px')
        chkStrs('entries.iconBgs', colors('.card--entries .row__icon'),
          ['rgb(239, 246, 255)', 'rgb(236, 253, 245)', 'rgb(255, 247, 237)', 'rgb(250, 245, 255)', 'rgba(255, 149, 0, 0.03)'])
        /* 图标字形盒 = 设计图层声明宽 20 × fs18 行盒 27（PNG 图标盒 36..68 / 字形墨迹 43..59 × 373..388） */
        chkList('entries.glyphBoxX', rects('.card--entries .row__glyph').map(function (r) { return r.x }), [42, 42, 42, 42, 42], 1)
        chkList('entries.glyphBoxW', rects('.card--entries .row__glyph').map(function (r) { return r.w }), [20, 20, 20, 20, 20], 1)
        chkList('entries.glyphBoxH', rects('.card--entries .row__glyph').map(function (r) { return r.h }), [27, 27, 27, 27, 27], 1)
        chkList('entries.glyphBoxTops', rects('.card--entries .row__glyph').map(function (r) { return r.top }), [366, 423, 480, 537, 593], 1)
        /* D5：占位形状在 ::before 上 → 颜色读伪元素（读元素 color 会得 rgb(0,0,0)） */
        chkStrs('entries.glyphColors', resolveAll('.card--entries .row__glyph').map(function (e) { return normColor(win.getComputedStyle(e, '::before').backgroundColor) }),
          ['rgb(37, 99, 235)', 'rgb(22, 163, 74)', 'rgb(217, 119, 6)', 'rgb(124, 58, 237)', 'rgb(255, 149, 0)'])
        chkStrs('entries.labels', texts('.card--entries .row__label'), ['我的报价单', '检测报告', '我的合同', '用量与对账', '我的消息'])
        chkList('entries.labelX', rects('.card--entries .row__label').map(function (r) { return r.x }), [78, 78, 78, 78, 78], 1) /* 36+32+10（PNG 标签墨迹左界 78） */
        chkC('entries.label.fs', '.card--entries .row__label', 'fontSize', 13) /* efe090dd fs13 Medium */
        chkC('entries.label.fw', '.card--entries .row__label', 'fontWeight', 500)
        chkC('entries.label.lh', '.card--entries .row__label', 'lineHeight', 15.6, 0.2) /* 无显式 height → 设计 1.2 × 13 */
        chkC('entries.label.color', '.card--entries .row__label', 'color', 'rgb(15, 23, 42)')
        chkStrs('entries.values', texts('.card--entries .row__value'), ['3 个', '2 份', '待签署 1', '待阅读 3']) /* 行4 无值（设计 kids 只有 chevron） */
        chkList('entries.valueRights', rects('.card--entries .row__value').map(function (r) { return r.right }), [368, 368, 368, 368], 2)
        chkC('entries.value.fs', '.card--entries .row__value', 'fontSize', 12)
        chkC('entries.value.fw', '.card--entries .row__value', 'fontWeight', 400)
        chkC('entries.value.lh', '.card--entries .row__value', 'lineHeight', 14.4, 0.2)
        chkStrs('entries.valueColors', textColors('.card--entries .row__value'),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(217, 119, 6)', 'rgb(0, 0, 0)']) /* 「待阅读 3」设计字色 rgba(0,0,0,1) */
        chk('entries.chevCount', doc.querySelectorAll('.card--entries .chevron').length, 5)
        chkList('entries.chevRights', rects('.card--entries .chevron').map(function (r) { return r.right }), [394, 394, 394, 394, 394], 1)
        chkList('entries.chevW', rects('.card--entries .chevron').map(function (r) { return r.w }), [26, 26, 26, 26, 26], 1) /* 容器 padding-left 4 + 盒 22 */
        chkList('entries.chevH', rects('.card--entries .chevron').map(function (r) { return r.h }), [30, 30, 30, 30, 30], 1)

        /* ===================== 主体与证照卡（design cd8b4c81 padding 8/20 · 4 行 ×54 + 3×1） ===================== */
        chkR('records.x', '.card--records', 16, 1)
        chkR('records.top', '.card--records', 655, 1) /* PNG 描边行 654/655 */
        chkR('records.w', '.card--records', 398, 1)
        chkR('records.h', '.card--records', 235, 1) /* 8 + 4×54 + 3×1 + 8（PNG 655..890） */
        chkC('records.pad', '.card--records', 'padding', '8px 20px')
        chkC('records.radius', '.card--records', 'borderRadius', '18px')
        chkC('records.ring', '.card--records', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('records.borderDeclared', '.card--records', 'border', null)
        chk('records.rowCount', doc.querySelectorAll('.card--records .row').length, 4)
        chkList('records.rowTops', rects('.card--records .row').map(function (r) { return r.top }), [663, 718, 773, 828], 1)
        chkList('records.rowH', rects('.card--records .row').map(function (r) { return r.h }), [54, 54, 54, 54], 1)
        chkList('records.rowX', rects('.card--records .row').map(function (r) { return r.x }), [36, 36, 36, 36], 1)
        chk('records.sepCount', doc.querySelectorAll('.card--records .row__sep').length, 3)
        chkList('records.sepTops', rects('.card--records .row__sep').map(function (r) { return r.top }), [717, 772, 827], 1)
        chkStrs('records.glyphColors', resolveAll('.card--records .row__glyph').map(function (e) { return normColor(win.getComputedStyle(e, '::before').backgroundColor) }),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)'])
        chkList('records.glyphBoxX', rects('.card--records .row__glyph').map(function (r) { return r.x }), [36, 36, 36, 36], 1)
        chkList('records.glyphBoxW', rects('.card--records .row__glyph').map(function (r) { return r.w }), [20, 20, 20, 20], 1)
        chkList('records.glyphBoxH', rects('.card--records .row__glyph').map(function (r) { return r.h }), [27, 27, 27, 27], 1)
        chkStrs('records.labels', texts('.card--records .row__label'), ['主体档案', '接入凭证', '结算账户', '账号与设置'])
        chkList('records.labelX', rects('.card--records .row__label').map(function (r) { return r.x }), [66, 66, 66, 66], 1) /* 36+20+10（PNG 标签墨迹左界 66） */
        chkC('records.label.fs', '.card--records .row__label', 'fontSize', 13)
        chkC('records.label.lh', '.card--records .row__label', 'lineHeight', 15.6, 0.2)
        chk('records.pillCount', doc.querySelectorAll('.card--records .row__pill').length, 1) /* 只有 主体档案=100% 是胶囊 */
        chkR('records.pill.x', '.card--records .row__pill', 324, 2) /* b059278f h20 r10 padding[0,8] + 文案 28 → 44 宽 */
        chkR('records.pill.right', '.card--records .row__pill', 368, 2)
        chkR('records.pill.h', '.card--records .row__pill', 20, 1)
        chkC('records.pill.pad', '.card--records .row__pill', 'padding', '0px 8px')
        chkC('records.pill.radius', '.card--records .row__pill', 'borderRadius', '10px')
        chkC('records.pill.bg', '.card--records .row__pill', 'backgroundColor', 'rgb(236, 253, 245)') /* rgba(236,253,245,1) */
        chkC('records.pillText.fs', '.card--records .row__pill-text', 'fontSize', 10) /* 36fd8a4c fs10 Medium rgba(21,128,61,1) */
        chkC('records.pillText.fw', '.card--records .row__pill-text', 'fontWeight', 500)
        chkC('records.pillText.lh', '.card--records .row__pill-text', 'lineHeight', 12, 0.2) /* 无显式 height → 设计 1.2 × 10 */
        chkC('records.pillText.color', '.card--records .row__pill-text', 'color', 'rgb(21, 128, 61)')
        chkStrs('records.pillText.text', [textOf('.card--records .row__pill')], ['100%'])
        chkStrs('records.values', texts('.card--records .row__value'), ['3 条', '已绑定']) /* 行4 账号与设置无值 */
        chkList('records.valueRights', rects('.card--records .row__value').map(function (r) { return r.right }), [368, 368], 2)
        chkC('records.value.lh', '.card--records .row__value', 'lineHeight', 14.4, 0.2)
        chkStrs('records.valueColors', textColors('.card--records .row__value'), ['rgb(148, 163, 184)', 'rgb(148, 163, 184)'])
        chk('records.chevCount', doc.querySelectorAll('.card--records .chevron').length, 4)
        chkList('records.chevRights', rects('.card--records .chevron').map(function (r) { return r.right }), [394, 394, 394, 394], 1)

        /* ===================== 底部 TabBar（共享组件 AppTabBar · design 9385b03b） ===================== */
        chkR('tabbar.top', '.tabbar', 906, 1) /* PNG 906..990 */
        chkR('tabbar.h', '.tabbar', 84, 1) /* 8 + 33 + 3 + 16 + 24 */
        chkC('tabbar.pos', '.tabbar', 'position', 'fixed')
        chkC('tabbar.pad', '.tabbar', 'padding', '8px 0px 24px')
        chkC('tabbar.bg', '.tabbar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('tabbar.justify', '.tabbar', 'justifyContent', 'space-between')
        chk('tabbar.count', doc.querySelectorAll('.tabbar').length, 1)
        chk('tabbar.itemCount', doc.querySelectorAll('.tabbar__item').length, 4)
        chkList('tabbar.itemW', rects('.tabbar__item').map(function (r) { return r.w }), [104, 104, 104, 104], 1)
        chkList('tabbar.itemX', rects('.tabbar__item').map(function (r) { return r.x }), [0, 109, 217, 326], 1) /* space_between：430 − 4×104 = 14 → 3 隙 4.67 */
        chkList('tabbar.iconH', rects('.tabbar__icon').map(function (r) { return r.h }), [33, 33, 33, 33], 1) /* 字形层 height=33（显式） */
        chk('tabbar.gap.h', css('.tabbar__gap', 'height'), 3)
        chkStrs('tabbar.glyphBg', colors('.tabbar__glyph'),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(37, 99, 235)']) /* page-21-2 高亮 = #2563EB */
        chkStrs('tabbar.labels', texts('.tabbar__label'), ['工作台', '报告', '报价', '我的'])
        chkC('tabbar.label.fs', '.tabbar__label', 'fontSize', 11)
        chkC('tabbar.label.lh', '.tabbar__label', 'lineHeight', 16)
        chkStrs('tabbar.labelColors', textColors('.tabbar__label'),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(37, 99, 235)'])
        chkStrs('tabbar.labelWeights', ['@@0', '@@1', '@@2', '@@3'].map(function (s) { return css('.tabbar__label' + s, 'fontWeight') }),
          [400, 400, 400, 600]) /* page-21-2 高亮项是 SourceHanSans-SemiBold（与 page-20-2 的 Regular 逐帧不同） */
        chk('tabbar.activeLabel', textOf('.tabbar__label--active'), '我的')

        /* 设计帧字面量登记（不照抄/派生项，逐条说明） */
        var designLiteralDiff = [
          '设计帧第 5 行「我的消息」的值「待阅读 3」与 chevron 被推出卡片右边界（导出图墨迹 372..429，卡右界 414）→ 实现按零溢出右对齐（值右 368 / chevron 右 394），越界已登记（台账序号 21 备注⑩）',
          '「待阅读 3」设计字色 rgba(0,0,0,1)（同卡其它值 #94A3B8）→ 实现照设计用 #000000（不擅自统一）',
          '三金额文案由 GET /payments 的 available_balance/pending_settlement/total_settled 派生（18-API 无钱包汇总 schema，字段名为推断 → 台账序号 21 备注②）',
          '各入口计数由各模块列表接口 pageSize=1 的 total 派生（无汇总接口）；缺字段渲染「—」',
          '「已认证」由 GET /provider/profile 的 verified 布尔派生（PRD 零命中 → 台账备注⑤）',
          '图标字形为 CSS 占位形状（D5）：形状 17×16 贴近设计 remixicon 墨迹 17×16；笔画细节非真实图标',
          '卡片描边用 ring（盒外 1px）→ 可见描边行比设计帧外移 1px（卡内容盒 140/192、344/299、655/235 与设计逐值相等）',
          '「提现」按钮按设计保留 → 点击只做占位提示（18-API 无提现端点，02-PRD 写线下结算 → missing-prd）',
          'toast 文案（提现功能暂未开放 / 数据加载失败，请稍后重试）设计帧无稿 → 占位（missing-prd）'
        ]

        return {
          checkCount: checks,
          checkFailCount: fails.length,
          checkFails: fails.slice(0, 400),
          overflowingCount: over.length,
          overflowing: over.slice(0, 10),
          missingTexts: missing,
          designLiteralDiff: designLiteralDiff,
          docScrollWidth: doc.documentElement.scrollWidth,
          docScrollHeight: docH,
          innerWidth: win.innerWidth,
          head: rect('.head'),
          avatar: rect('.head__avatar'),
          avatarGlyph: rect('.head__avatar-glyph'),
          company: rect('.head__company'),
          typePill: rect('.head__type'),
          verifiedPill: rect('.head__verified'),
          dot: rect('.head__dot'),
          wallet: rect('.card--wallet'),
          walletTitleRow: rect('.wallet__title-row'),
          walletTitle: rect('.wallet__title'),
          walletChev: rect('.wallet__title-row .chevron'),
          balanceRow: rect('.wallet__balance-row'),
          balanceBlock: rect('.wallet__balance'),
          amount: rect('.wallet__amount'),
          withdraw: rect('.withdraw'),
          detailRow: rect('.wallet__detail-row'),
          dividers: rects('.wallet__divider'),
          subs: rects('.wallet__sub-amount'),
          entries: rect('.card--entries'),
          entryRows: rects('.card--entries .row'),
          entryIcons: rects('.card--entries .row__icon'),
          entryGlyphs: rects('.card--entries .row__glyph'),
          entryValues: rects('.card--entries .row__value'),
          entryChevs: rects('.card--entries .chevron'),
          records: rect('.card--records'),
          recordRows: rects('.card--records .row'),
          recordGlyphs: rects('.card--records .row__glyph'),
          recordValues: rects('.card--records .row__value'),
          pill: rect('.card--records .row__pill'),
          tabbar: rect('.tabbar'),
          tabItems: rects('.tabbar__item'),
          texts: {
            company: textOf('.head__company'),
            type: textOf('.head__type'),
            verified: textOf('.head__verified'),
            walletTitle: textOf('.wallet__title'),
            labels: texts('.wallet__label'),
            amount: textOf('.wallet__amount'),
            subs: texts('.wallet__sub-amount'),
            withdraw: textOf('.withdraw'),
            entryLabels: texts('.card--entries .row__label'),
            entryValues: texts('.card--entries .row__value'),
            recordLabels: texts('.card--records .row__label'),
            recordValues: texts('.card--records .row__value'),
            pillText: textOf('.card--records .row__pill'),
            tabs: texts('.tabbar__label')
          },
          counts: {
            cards: doc.querySelectorAll(CARDS).length,
            entryRows: doc.querySelectorAll('.card--entries .row').length,
            recordRows: doc.querySelectorAll('.card--records .row').length,
            pills: doc.querySelectorAll('.card--records .row__pill').length,
            inputs: doc.querySelectorAll('input,textarea').length
          },
          userAgent: win.navigator.userAgent
        }
      }

"""

MAIN = r"""      async function main() {
        try {
          await waitFor('[data-testid="row-quotes"]')
          await sleep(1600)
          phase(1)
          if (NO_ACTION || !SCENARIO || SHOT_ONLY) return

          /* ?scenario=withdraw：设计稿「提现」按钮 = missing-prd（18-API 无提现端点）→ 只做占位提示。
             硬证据 = toast 文案 + hash 不变 + serve 实收零写请求。 */
          if (SCENARIO === 'withdraw') {
            var cW = clickIn('[data-testid="wallet-withdraw"]')
            await sleep(1200)
            sink(2, {
              scenario: SCENARIO, clicked: cW,
              toast: toastText(f.contentDocument),
              withdrawBg: bgsIn('[data-testid="wallet-withdraw"]')[0],
              hash: hashNow(),
              rowCount: countIn('.card--entries .row')
            })
            return
          }

          /* ?scenario=rows-quotes：我的报价单 → /pages/quotes/index（列表页取数） */
          if (SCENARIO === 'rows-quotes') {
            var cQ = clickIn('[data-testid="row-quotes"]')
            await sleep(2200)
            sink(2, {
              scenario: SCENARIO, clicked: cQ,
              hash: hashNow(),
              landingText: textIn('.quotes__title') || textIn('.quotes')
            })
            return
          }

          /* ?scenario=usage：用量与对账 → /pages/usage/index（序号 22 已实现 —— 旧台账「未实现 → 降级」口径已作废） */
          if (SCENARIO === 'usage') {
            var cU = clickIn('[data-testid="row-usage"]')
            await sleep(2200)
            sink(2, {
              scenario: SCENARIO, clicked: cU,
              hash: hashNow(),
              landingText: textIn('.usage .nav__title') || textIn('.usage')
            })
            return
          }

          /* ?scenario=settings：账号与设置 → /pages/settings/index（序号 23 已实现） */
          if (SCENARIO === 'settings') {
            var cS = clickIn('[data-testid="row-settings"]')
            await sleep(2200)
            sink(2, {
              scenario: SCENARIO, clicked: cS,
              hash: hashNow(),
              landingText: textIn('.settings .nav__title') || textIn('.settings')
            })
            return
          }

          /* ?scenario=tab-workbench：TabBar「工作台」→ /pages/workbench/index */
          if (SCENARIO === 'tab-workbench') {
            var cT = clickIn('[data-testid="tab-工作台"]')
            await sleep(2200)
            sink(2, {
              scenario: SCENARIO, clicked: cT,
              hash: hashNow(),
              landingText: textIn('.workbench')
            })
            return
          }

          /* ?scenario=tab-mine：TabBar「我的」= 当前模块 → 不跳转（hash 不变、无新请求） */
          if (SCENARIO === 'tab-mine') {
            var cM = clickIn('[data-testid="tab-我的"]')
            await sleep(1500)
            sink(2, {
              scenario: SCENARIO, clicked: cM,
              hash: hashNow(),
              rowCount: countIn('.card--entries .row')
            })
            return
          }
        } catch (e) {
          sink('error', { message: String(e && e.message), stack: String((e && e.stack) || '').slice(0, 600) })
        }
      }

      main()
    </script>
  </body>
</html>
"""

out = HEAD + top + "\n" + preamble + PRELUDE + overflow + CHECKS + tail + MAIN
with io.open(DST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(out)
print("wrote", DST, len(out), "chars,", out.count("\n") + 1, "lines")
