"""Build __measure-usage.html (序号 22 · page-22-2「【工作台与我的】我的与用量概览 2」) as a
430-wide iframe probe with design-expectation checks (chk/chkR/chkC/chkD/chkP/chkList/chkStrs).

做法与 build-probe-10/11/12/12v2/12v3/15/20/21 同：从 __measure-mine.html（同族载体页，含
`resolveAll` / `declared` / `normShadow` / `pseudoStyle` 等全套 helpers）切四段「与帧无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计 / sink+phase+点击工具）逐字节复用，
本文件只写 page-22-2 自己的 checks / return / main。

want 两类来源（先量再写，不凭截图目测）：
  (a) 声明值 .calicat/raw/pages/page-22-2/{design.json,design.tree.json}
      python .agents/state/dump-layout.py page-22-2      # 全字段（padding/gap/lineHeight/stroke/effects/圆角）
      python .agents/state/text-fields.py page-22-2      # 文本叶子 fontSize/字重/字色/宽高/文案
      python .agents/state/raw-node.py page-22-2 <id>    # 单节点原始 JSON（fontFill / 显式 height）
  (b) 设计截图 PNG 实测（430×1138；本轮重抓 design.json sha256 63d7ce0c… 逐字节相同、
      设计 PNG 重下载 sha256 ce50a955… 相同 → 无漂移）
      python .agents/state/stroke-rows.py design-shots/page-22-2.png eef2f7 6 150 20 410 100 1138
      python .agents/state/scan-col.py design-shots/page-22-2.png 100 96 360 6
      python .agents/state/text-rows.py design-shots/page-22-2.png 20 410
      python .agents/state/ink-bbox.py design-shots/page-22-2.png 300,45,335,90
      python .agents/state/png-profile.py design-shots/page-22-2.png 20 1057 410 1138
      python .agents/state/scan-row.py design-shots/page-22-2.png 66 280 430 3

设计骨架（逐条与 PNG 墨迹对过）：
  顶部导航 0..96（白底 padding 48/16/12/16 · 返回字形盒 26×36 @x16 → 标题盒 x54 · 月份胶囊 299..414
            h30 r10 #F1F5F9 padding 0/12 · 日历字形盒 17×22.5 · 月份文字 fs12 #475569 · 下箭头字形盒 18×24）
  本月汇总卡 108..336（228 = 20 + 标题 h20 + 16 + 72 + 8 + 72 + 20 · r18 · **无描边、有 effects(0,6,20,.06)**）
            四宫格 164..236 / 244..316（各 178.5 宽 · gap 9 · 值 h26 fs17 Bold · 标签 h16 fs10）
  近 7 日趋势卡 348..570（222 = 20 + 标题行 20 + 12 + 图 150 + 20 · r18 ring #EEF2F7）
            标题行 368..388 · 图 400..550 · 横轴标签盒 20.12×11.3 @top 122.95（图内坐标）
  模型用量分布卡 582..766（184 = 20 + 20 + 16 + 4×18 + 3×12 + 20 · ring）行内容 638/668/698/728
  成本构成卡 778..985（207 = 20 + 20 + 16 + 3×18 + 3×12 + 41 + 20 · ring）合计行 924..965(padding 10 r10 #F8FAFC)
  明细入口卡 997..1057（60 = 16 + 28 + 16 · ring · 图标盒 20×27 @x36 · 文字 fs13 @x64 · chevron 盒 22×28）
  底部说明 1057..1138（padding 24/0/24/0 · 两行 11px h16：墨迹 1084..1095 / 1100..1110）

本页定标（与 §5.12/§5.13/§5.14 一致）：
  · 图标字形盒 = 设计声明宽 × 字号×1.5（返回 fs24 声明 w26 → 26×36 · 日历 fs15 → 17×22.5 ·
    下箭头 fs16 → 18×24 · 明细列表 fs18 → 20×27；chevron-right fs20 实测 22×28，非 ×1.5）。
  · 文本行盒 **设计显式 height 优先**（标题 20 · 图例行 20 · 值 26 · 标签 16 · 合计值 21 · 底部 16 · 横轴 11.3×1.31）；
    无显式 height 走设计 `lineHeight 1.2`（fs12 → 14.4）或 fit_content 实测（模型/成本行 18）。
  · stroke{align:center,thickness:1} → box-shadow: 0 0 0 1px（border 会占布局）· 汇总卡只有 effects。
  · 占比条填充 = 百分比 × **轨道宽**（设计声明 = 百分比 × 卡外层宽 398 → 设计自身不自洽，台账序号 22 备注①）。
"""

import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-mine.html")
DST = os.path.join(HM, "__measure-usage.html")

FRAME_H = "1138px"

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
    "if (SHOT_ONLY) f.style.height = '990px' /* = 设计帧高 */",
    "if (SHOT_ONLY) f.style.height = '%s' /* = 设计帧高 */" % FRAME_H,
)
assert "'%s'" % FRAME_H in top, "SHOT 高度替换失败（顶部作用域切片变了？）"
preamble = "\n".join(src[i_collect:i_over])   # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])    # over / missing 统计（引用 NEED_TEXT / CARDS）
tail = "\n".join(src[i_sink:i_main])          # sink / phase / clickIn / toastText / hashNow / waitFor / sleep / textIn / countIn / bgsIn
assert "f.style.height = '990px'" in tail, "phase() 取数高度锚变了（应把 990 改成 1138）"
tail = tail.replace("f.style.height = '990px'", "f.style.height = '%s'" % FRAME_H)
# ⚠️ 切片坑（与 build-probe-20 §5.13 同族）：__measure-mine.html 里 `function bgsIn` 的收尾 `}` 与
# `async function main() {` 落在同一行，按行切到 main 之前会把它切掉（大括号净值 +1，
# node --check 只报「Unexpected end of input」不给行号）→ 这里显式补回，并用 js-depth-lines.py 复验净值 0。
assert "      }      async function main() {" in src[i_main], "bgsIn 收尾与 main 同行这一前提变了，请重新核对切片"
# ⚠️ pickerProbe / clickOverlayConfirm 不在共享骨架里（它们原本只写在旧版 __measure-usage.html 自己的脚本中，
# 骨架切不来）→ 本页必须在主脚本里自带（本轮踩到：month 相报 ReferenceError: pickerProbe is not defined）。
PICKER_TOOLS = r"""
      /** uni H5 的 picker 覆盖层（点开后再点「确定」）——类名探针，找不到就回 NO_PICKER_OVERLAY */
      function pickerProbe(doc) {
        var containers = Array.prototype.slice.call(doc.querySelectorAll('[class*="picker"]'))
        return containers.slice(0, 8).map(function (e) { return { tag: e.tagName, cls: String(e.className) } })
      }
      function clickOverlayConfirm(doc) {
        var cands = Array.prototype.slice.call(doc.querySelectorAll('[class*="confirm"], [class*="ok"]'))
        for (var i = 0; i < cands.length; i++) {
          var el = cands[i]
          if (el.getBoundingClientRect().width > 0) {
            var ev = doc.createEvent('MouseEvents')
            ev.initMouseEvent('click', true, true, f.contentWindow, 0, 0, 0, 0, 0, false, false, false, false, 0, null)
            el.dispatchEvent(ev)
            return 'CONFIRMED:' + String(el.className)
          }
        }
        return 'NO_CONFIRM'
      }
"""
tail = tail + "\n      }" + PICKER_TOOLS

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-usage</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      /* iframe 取数高度 = 设计帧高 1138：页面 min-height:100vh 会把测量高度顶到 iframe 高，
         1138 时 docScrollHeight 恰好等于设计帧高（内容自算 1137 + 设计导出末行）。 */
      iframe { width: 430px; height: 1138px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜（uni-app 技能 §5 口径）
         页面 22：/pages/usage/index（【工作台与我的】我的与用量概览 2，page-22-2 · layer_id 8bc59233-3854-4725-b85b-bfaf4518e934）
         设计真源：.calicat/raw/pages/page-22-2/design.tree.json（本轮重抓 design.json sha256 63d7ce0c… 逐字节相同；
                  设计 PNG 重下载 sha256 ce50a955… 相同 → 无漂移）
         设计骨架（声明值 + 设计 PNG 430x1138 实测）：
           顶部导航 0..96（白底 padding 48/16/12/16 · 返回字形盒 26×36 @x16 · 月份胶囊 299..414 h30 r10 #F1F5F9）
           本月汇总卡 108..336（228 · r18 · 无描边有 effects(0,6,20,.06)）· 四宫格 164..236 / 244..316（gap 9）
           近 7 日趋势卡 348..570（222 · ring）· 标题行 368..388 · 图 400..550（横轴标签盒 20.12×11.3 @122.95）
           模型用量分布卡 582..766（184 · ring）行内容 638/668/698/728 · 轨道 x167 w192 h10
           成本构成卡 778..985（207 · ring）合计行 924..965（padding 10 r10 #F8FAFC）
           明细入口卡 997..1057（60 · ring）· 底部说明 1057..1138（两行 11px 墨迹 1084..1095 / 1100..1110）
         ?scenario=back|month|detail 逐个回放出口；不带 scenario（或 noaction / shot=1）只取 phase1 设计期望值相 -->
    <iframe id="f" src="/index.html#/pages/usage/index"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

PRELUDE = r"""
        var CARDS = '.card'
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-22-2 design.tree.json 的
           fontSize/fontFamily/content；remixicon 字形层 content 是私有码位/空 → 不进清单）。
           值文案与 mock（api-22/v1/usage/summary）一致：1.24M / 3.86B / ¥12,860 / ¥2,140 / 42% …
           设计帧「平台服务费（8%）」的费率来自数据（cost.platform_fee_rate=8）→ 文案随费率走。 */
        var NEED_TEXT = [
          '用量概览', '2024-06',
          '本月汇总', '1.24M', '请求数', '3.86B', 'Token', '¥12,860', '费用', '¥2,140', '较上月节省',
          '近 7 日用量趋势', 'Token（亿）',
          '6-08', '6-09', '6-10', '6-11', '6-12', '6-13', '6-14',
          '模型用量分布', 'gpt-4o-mini', '42%', 'claude-3-5-sonnet', '31%', 'gpt-4o', '21%', '其他', '6%',
          '成本构成', '输入 Token 成本', '¥4,120', '输出 Token 成本', '¥8,240', '平台服务费（8%）', '¥500', '合计', '¥12,860',
          '查看逐日 / 逐模型明细',
          '数据每小时更新一次，最终以结算账单为准', '更新时间：2024-06-14 16:20'
        ]
"""

CHECKS = r"""
        /* ===================== 整页（设计帧 430×1138） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 1138, 2) /* 96 + 5×12 + 228+222+184+207+60 + 底部说明 81 */
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.usage', 'backgroundColor', 'rgb(248, 250, 252)') /* 用量概览页 fdfd1d4a fills rgba(248,250,252,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 5)
        chk('page.inputCount', doc.querySelectorAll('input,textarea').length, 0)
        chk('page.tabbarCount', doc.querySelectorAll('.tabbar').length, 0) /* 本页设计无 TabBar（由「我的 → 用量与对账」navigateTo 进入） */

        /* ===================== 顶部导航（design 30e7ff99 padding[48,16,12,16] · 白底） ===================== */
        chkR('nav.top', '.nav', 0, 1)
        chkR('nav.h', '.nav', 96, 1) /* 48 + 字形行盒 36 + 12（PNG 白底 0..95） */
        chkR('nav.w', '.nav', 430, 1)
        chkC('nav.pad', '.nav', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.nav', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('nav.align', '.nav', 'alignItems', 'center')
        /* 返回字形层 d8f8de49 fs24 声明 w26 → 盒 26×36（PNG 墨迹 x20..36 y59..74） */
        chkR('nav.back.x', '.nav__back', 16, 1)
        chkR('nav.back.top', '.nav__back', 48, 1)
        chkR('nav.back.w', '.nav__back', 26, 1)
        chkR('nav.back.h', '.nav__back', 36, 1)
        chkR('nav.backGlyph.w', '.nav__back .glyph', 16, 1) /* 形状 16×16 贴设计墨迹 17×16（D5 占位） */
        chkR('nav.backGlyph.h', '.nav__back .glyph', 16, 1)
        chk('nav.titleWrap.padLeft', css('.nav__title-wrap', 'paddingLeft'), 12) /* container f293d85d padding-left 12 */
        chkR('nav.title.x', '.nav__title', 54, 1) /* 16 + 26 + 12（PNG 标题墨迹 55..121） */
        chkC('nav.title.fs', '.nav__title', 'fontSize', 17) /* 0b262a42 fs17 Bold #0F172A */
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700)
        chkC('nav.title.lh', '.nav__title', 'lineHeight', 25.5, 0.2)
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('.nav__title')], ['用量概览'])
        /* 月份胶囊 6073d689：h30 r10 padding[0,12] #F1F5F9 · 右边界 = 430 − 16 */
        chkR('month.right', '.month', 414, 1)
        chkR('month.top', '.month', 51, 1) /* 48 + (36−30)/2（PNG 胶囊 51..81，x=302 处因 r10 圆角收窄可见 53.5..77.5） */
        chkR('month.h', '.month', 30, 1)
        chkR('month.w', '.month', 115, 2) /* 12+17+5+47+4+18+12（CJK/数字度量 → 实测 113，链算值登记） */
        chkC('month.pad', '.month', 'padding', '0px 12px')
        chkC('month.radius', '.month', 'borderRadius', '10px')
        chkC('month.bg', '.month', 'backgroundColor', 'rgb(241, 245, 249)')
        chkR('month.cal.w', '.glyph--calendar', 17, 1) /* 687c0ef8 fs15 声明 w17 → 盒 17×22.5 */
        chkR('month.cal.h', '.glyph--calendar', 22.5, 0.6)
        chk('month.textWrap.padLeft', css('.month__text-wrap', 'paddingLeft'), 5) /* container 89b36cb0 padding-left 5 */
        chkC('month.value.fs', '.month__value', 'fontSize', 12) /* f1090524 fs12 Medium #475569 */
        chkC('month.value.fw', '.month__value', 'fontWeight', 500)
        chkC('month.value.lh', '.month__value', 'lineHeight', 14.4, 0.2) /* 无显式 height → 设计 1.2 × 12 */
        chkC('month.value.color', '.month__value', 'color', 'rgb(71, 85, 105)')
        chkStrs('month.value.text', [textOf('.month__value')], ['2024-06'])
        chk('month.chevWrap.padLeft', css('.month__chevron-wrap', 'paddingLeft'), 4) /* container 9f6f1e9b padding-left 4 */
        chkR('month.chev.w', '.glyph--chevron-down', 18, 1) /* 6b54127b fs16 声明 w18 → 盒 18×24 */
        chkR('month.chev.h', '.glyph--chevron-down', 24, 0.6)

        /* ===================== 本月汇总卡（design 811a53eb padding 20/16 r18 · 仅 effects） ===================== */
        chkR('summary.x', '.card--summary', 16, 1)
        chkR('summary.top', '.card--summary', 108, 1) /* PNG 卡 108..336 */
        chkR('summary.w', '.card--summary', 398, 1)
        chkR('summary.h', '.card--summary', 228, 1) /* 20 + 20 + 16 + 72 + 8 + 72 + 20 */
        chkC('summary.pad', '.card--summary', 'padding', '20px 16px')
        chkC('summary.radius', '.card--summary', 'borderRadius', '18px')
        chkC('summary.bg', '.card--summary', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('summary.shadow', '.card--summary', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 6px 20px 0px') /* effects drop_shadow(0,6,20)；Chrome 会补尾随 spread 0px（同序号 12/15 口径） */
        chkD('summary.borderDeclared', '.card--summary', 'border', null) /* 反向断言：本卡设计无 stroke，不许补描边 */
        chkR('summary.title.x', '.card--summary .card__title', 32, 1) /* 卡 padding 16（PNG 标题墨迹 32..87） */
        chkR('summary.title.top', '.card--summary .card__title', 128, 1) /* 108 + 20 */
        chkR('summary.title.h', '.card--summary .card__title', 20, 1) /* 0283c332 fs14 显式 h20 */
        chkC('summary.title.fs', '.card--summary .card__title', 'fontSize', 14)
        chkC('summary.title.fw', '.card--summary .card__title', 'fontWeight', 600)
        chkC('summary.title.lh', '.card--summary .card__title', 'lineHeight', 20)
        chkC('summary.title.color', '.card--summary .card__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('summary.title.text', [textOf('.card--summary .card__title')], ['本月汇总'])
        chk('summary.tiles1.padTop', css('.tiles--first', 'paddingTop'), 16) /* container 5791f18b padding-top 16 */
        chk('summary.tiles2.padTop', css('.tiles--second', 'paddingTop'), 8) /* container 09bcbf67 padding-top 8 */
        chkR('summary.tiles1.top', '.tiles--first', 148, 1) /* 容器 5791f18b（含 padding-top 16）→ 宫格行 164..236 */
        chkR('summary.tiles1.h', '.tiles--first', 88, 1) /* 16 + 72 */
        chkR('summary.tiles2.top', '.tiles--second', 236, 1) /* 容器 09bcbf67（含 padding-top 8）→ 宫格行 244..316 */
        chkR('summary.tiles2.h', '.tiles--second', 80, 1) /* 8 + 72 */
        chk('summary.tileCount', doc.querySelectorAll('.card--summary .tile').length, 4)
        chkList('summary.tileTops', rects('.card--summary .tile').map(function (r) { return r.top }), [164, 164, 244, 244], 1)
        chkList('summary.tileX', rects('.card--summary .tile').map(function (r) { return r.x }), [32, 220, 32, 220], 1)
        chkList('summary.tileW', rects('.card--summary .tile').map(function (r) { return r.w }), [178, 178, 178, 178], 1)
        chkList('summary.tileH', rects('.card--summary .tile').map(function (r) { return r.h }), [72, 72, 72, 72], 1)
        chk('summary.tileGap', rect('.card--summary .tile@@1').x - rect('.card--summary .tile@@0').right, 9, 1) /* spacer w9 */
        chkC('summary.tile.radius', '.card--summary .tile', 'borderRadius', '12px')
        chkStrs('summary.tileBgs', colors('.card--summary .tile'),
          ['rgb(239, 246, 255)', 'rgb(236, 253, 245)', 'rgb(255, 247, 237)', 'rgb(250, 245, 255)'])
        chkStrs('summary.values', texts('.card--summary .tile__value'), ['1.24M', '3.86B', '¥12,860', '¥2,140'])
        chkR('summary.value.h', '.card--summary .tile__value', 26, 1) /* f6e970f6 fs17 显式 h26 */
        chkC('summary.value.fs', '.card--summary .tile__value', 'fontSize', 17)
        chkC('summary.value.fw', '.card--summary .tile__value', 'fontWeight', 700)
        chkC('summary.value.lh', '.card--summary .tile__value', 'lineHeight', 26)
        chkStrs('summary.valueColors', textColors('.card--summary .tile__value'),
          ['rgb(29, 78, 216)', 'rgb(21, 128, 61)', 'rgb(180, 83, 9)', 'rgb(124, 58, 237)'])
        chkStrs('summary.labels', texts('.card--summary .tile__label'), ['请求数', 'Token', '费用', '较上月节省'])
        chkR('summary.label.h', '.card--summary .tile__label', 16, 1) /* 85174969 fs10 显式 h16 */
        chkC('summary.label.fs', '.card--summary .tile__label', 'fontSize', 10)
        chkC('summary.label.fw', '.card--summary .tile__label', 'fontWeight', 400)
        chkC('summary.label.lh', '.card--summary .tile__label', 'lineHeight', 16)
        chkC('summary.label.color', '.card--summary .tile__label', 'color', 'rgb(100, 116, 139)')

        /* ===================== 近 7 日用量趋势卡（design 0baed36c padding 20 r18 · stroke 1px #EEF2F7） ===================== */
        chkR('trend.x', '.card--trend', 16, 1)
        chkR('trend.top', '.card--trend', 348, 1) /* PNG 描边行 348/570 */
        chkR('trend.w', '.card--trend', 398, 1)
        chkR('trend.h', '.card--trend', 222, 1) /* 20 + 标题行 20 + 12 + 图 150 + 20 */
        chkC('trend.pad', '.card--trend', 'padding', '20px')
        chkC('trend.radius', '.card--trend', 'borderRadius', '18px')
        chkC('trend.bg', '.card--trend', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('trend.ring', '.card--trend', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('trend.borderDeclared', '.card--trend', 'border', null)
        chkR('trend.head.top', '.card--trend .card__head', 368, 1) /* 348 + 20 */
        chkR('trend.head.h', '.card--trend .card__head', 20, 1)
        chkC('trend.title.fs', '.card--trend .card__title', 'fontSize', 14) /* 27e04c6d fs14 SemiBold #0F172A */
        chkC('trend.title.fw', '.card--trend .card__title', 'fontWeight', 600)
        chkC('trend.title.lh', '.card--trend .card__title', 'lineHeight', 20)
        chkC('trend.title.color', '.card--trend .card__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('trend.title.text', [textOf('.card--trend .card__title')], ['近 7 日用量趋势'])
        chkR('trend.dot.w', '.legend__dot', 9, 1) /* bf03fb26 9×8 r4 rgba(37,99,235,1) */
        chkR('trend.dot.h', '.legend__dot', 8, 1)
        chkC('trend.dot.radius', '.legend__dot', 'borderRadius', '4px')
        chkC('trend.dot.bg', '.legend__dot', 'backgroundColor', 'rgb(37, 99, 235)')
        chk('trend.legend.padLeft', css('.legend__text-wrap', 'paddingLeft'), 4) /* container abcc3cd3 padding-left 4 */
        chkR('trend.legendText.right', '.legend__text', 394, 2) /* 右对齐卡内容右界（PNG 图例文字墨迹 334..386） */
        chkC('trend.legendText.fs', '.legend__text', 'fontSize', 10) /* 2f762dbc fs10 Regular #94A3B8 */
        chkC('trend.legendText.color', '.legend__text', 'color', 'rgb(148, 163, 184)')
        chkStrs('trend.legendText.text', [textOf('.legend__text')], ['Token（亿）'])
        chkR('trend.chart.top', '.trend', 400, 1) /* 368 + 20 + 12（PNG 图区 400..550） */
        chkR('trend.chart.h', '.trend', 150, 1) /* container 13d9631c padding-top 12 + 趋势图 h150 */
        chkR('trend.img.w', '.trend__img', 358, 1)
        chkR('trend.img.h', '.trend__img', 150, 1)
        /* 趋势图：uni-image 在 H5 下把 src 放进内部 <img>/背景图 → 从 innerHTML 取 data-URI 并解码回 SVG 校验 */
        var trendHost = el('.trend__img')
        var trendHtml = trendHost ? String(trendHost.innerHTML) : ''
        var trendMatch = trendHtml.match(/data:image\/svg\+xml;base64,([A-Za-z0-9+/=]+)/)
        var trendSvg = ''
        try { trendSvg = trendMatch ? atob(trendMatch[1]) : '' } catch (e) { trendSvg = '' }
        chk('trend.img.src', !!trendMatch, true)
        chk('trend.img.viewBox', trendSvg.indexOf('viewBox="0 0 358 150"') >= 0, true)
        chk('trend.img.gridCount', (trendSvg.match(/<line /g) || []).length, 4) /* design 4 条网格线（3×#F1F5F9 + 1×#E2E8F0） */
        chk('trend.img.dotCount', (trendSvg.match(/<circle /g) || []).length, 7) /* design 7 个数据点 */
        chk('trend.img.lineColor', trendSvg.indexOf('#2563EB') >= 0, true) /* design 折线 #2563EB 3px */
        chk('trend.img.areaFill', trendSvg.indexOf('rgba(191,219,254,0.35)') >= 0, true) /* design 面积填充 */
        chk('trend.labelCount', doc.querySelectorAll('.trend__label').length, 7)
        chkStrs('trend.labelTexts', texts('.trend__label'), ['6-08', '6-09', '6-10', '6-11', '6-12', '6-13', '6-14'])
        chkList('trend.labelX', rects('.trend__label').map(function (r) { return r.x }), [56, 107, 159, 210, 261, 313, 364], 1) /* 36 + (30 + 51.33i) − 10.06 */
        chkList('trend.labelW', rects('.trend__label').map(function (r) { return r.w }), [20, 20, 20, 20, 20, 20, 20], 1) /* 20.12 */
        chkList('trend.labelTop', rects('.trend__label').map(function (r) { return r.top }), [523, 523, 523, 523, 523, 523, 523], 1) /* 图顶 400 + 122.95 */
        chkC('trend.label.fs', '.trend__label', 'fontSize', 10) /* dd03924e fs10 fills #94A3B8 lineHeight 1.31 */
        chkC('trend.label.lh', '.trend__label', 'lineHeight', 13.1, 0.3)
        chkC('trend.label.color', '.trend__label', 'color', 'rgb(148, 163, 184)')
        chk('trend.emptyCount', doc.querySelectorAll('.trend__empty').length, 0) /* 有数据 → 不渲染占位 */
        chk('trend.labelTopCss', css('.trend__label', 'top'), 122.95, 0.5) /* 设计帧 y=122.95（图内坐标） */

        /* ===================== 模型用量分布卡（design 4a6aa3b5 padding 20 r18 · stroke 1px） ===================== */
        chkR('models.x', '.card--models', 16, 1)
        chkR('models.top', '.card--models', 582, 1) /* PNG 描边行 582/766 */
        chkR('models.w', '.card--models', 398, 1)
        chkR('models.h', '.card--models', 184, 1) /* 20 + 20 + 16 + 4×18 + 3×12 + 20 */
        chkC('models.pad', '.card--models', 'padding', '20px')
        chkC('models.radius', '.card--models', 'borderRadius', '18px')
        chkC('models.ring', '.card--models', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('models.borderDeclared', '.card--models', 'border', null)
        chkR('models.title.top', '.card--models .card__title', 602, 1) /* 582 + 20 */
        chkR('models.title.h', '.card--models .card__title', 20, 1) /* f3361737 fs14 显式 h20 */
        chkC('models.title.fs', '.card--models .card__title', 'fontSize', 14)
        chkC('models.title.fw', '.card--models .card__title', 'fontWeight', 600)
        chkC('models.title.color', '.card--models .card__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('models.title.text', [textOf('.card--models .card__title')], ['模型用量分布'])
        chk('models.rowCount', doc.querySelectorAll('.card--models .mrow').length, 4)
        chk('models.row1.padTop', css('.card--models .mrow--first', 'paddingTop'), 16) /* container ca975301 padding-top 16 */
        chk('models.row.padTop', css('.card--models .mrow@@1', 'paddingTop'), 12) /* container ca07073f padding-top 12 */
        chkList('models.rowTops', rects('.card--models .mrow').map(function (r) { return r.top }), [622, 656, 686, 716], 1)
        chkList('models.rowH', rects('.card--models .mrow').map(function (r) { return r.h }), [34, 30, 30, 30], 1)
        chkStrs('models.names', texts('.card--models .mrow__name'), ['gpt-4o-mini', 'claude-3-5-sonnet', 'gpt-4o', '其他'])
        chkList('models.nameTops', rects('.card--models .mrow__name').map(function (r) { return r.top }), [638, 668, 698, 728], 1) /* PNG 名称墨迹 642/672/702/732 */
        chkC('models.name.w', '.card--models .mrow__name', 'width', 131)
        chkC('models.name.fs', '.card--models .mrow__name', 'fontSize', 12) /* 0cadecd5 fs12 Regular #475569 */
        chkC('models.name.fw', '.card--models .mrow__name', 'fontWeight', 400)
        chkC('models.name.lh', '.card--models .mrow__name', 'lineHeight', 18)
        chkC('models.name.color', '.card--models .mrow__name', 'color', 'rgb(71, 85, 105)')
        chkList('models.trackTops', rects('.card--models .mrow__track').map(function (r) { return r.top }), [642, 672, 702, 732], 1)
        chkList('models.trackX', rects('.card--models .mrow__track').map(function (r) { return r.x }), [167, 167, 167, 167], 1)
        chkList('models.trackW', rects('.card--models .mrow__track').map(function (r) { return r.w }), [192, 192, 192, 199], 1) /* 轨道 = 358 − 131 − 8 − 百分比盒宽（row4「6%」盒窄 7 → 199；PNG 实测 167..358.5 / 167..365.5） */
        chkList('models.trackH', rects('.card--models .mrow__track').map(function (r) { return r.h }), [10, 10, 10, 10], 1)
        chkC('models.track.radius', '.card--models .mrow__track', 'borderRadius', '5px')
        chkC('models.track.bg', '.card--models .mrow__track', 'backgroundColor', 'rgb(241, 245, 249)')
        chkList('models.fillW', rects('.card--models .mrow__fill').map(function (r) { return r.w }), [81, 60, 41, 12], 1) /* 百分比 × 轨道宽 192（设计声明 × 398 → 台账备注①） */
        chkList('models.fillH', rects('.card--models .mrow__fill').map(function (r) { return r.h }), [10, 10, 10, 10], 1)
        chkStrs('models.fillColors', colors('.card--models .mrow__fill'),
          ['rgb(37, 99, 235)', 'rgb(34, 197, 94)', 'rgb(245, 158, 11)', 'rgb(148, 163, 184)'])
        chkStrs('models.pcts', texts('.card--models .mrow__pct'), ['42%', '31%', '21%', '6%'])
        chkC('models.pct.fs', '.card--models .mrow__pct', 'fontSize', 12) /* 7af87f8b fs12 SemiBold #0F172A */
        chkC('models.pct.fw', '.card--models .mrow__pct', 'fontWeight', 600)
        chkC('models.pct.lh', '.card--models .mrow__pct', 'lineHeight', 18)
        chkC('models.pct.color', '.card--models .mrow__pct', 'color', 'rgb(15, 23, 42)')
        chk('models.pctWrap.padLeft', css('.card--models .mrow__pct-wrap', 'paddingLeft'), 8) /* container 3b617c7a padding-left 8 */
        chkList('models.pctRights', rects('.card--models .mrow__pct').map(function (r) { return r.right }), [394, 394, 394, 394], 2)

        /* ===================== 成本构成卡（design a9b6fb23 padding 20 r18 · stroke 1px） ===================== */
        chkR('cost.x', '.card--cost', 16, 1)
        chkR('cost.top', '.card--cost', 778, 1) /* PNG 描边行 778/985 */
        chkR('cost.w', '.card--cost', 398, 1)
        chkR('cost.h', '.card--cost', 207, 1) /* 20 + 20 + 16 + 3×18 + 3×12 + 41 + 20 */
        chkC('cost.pad', '.card--cost', 'padding', '20px')
        chkC('cost.radius', '.card--cost', 'borderRadius', '18px')
        chkC('cost.ring', '.card--cost', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('cost.borderDeclared', '.card--cost', 'border', null)
        chkR('cost.title.top', '.card--cost .card__title', 798, 1) /* 778 + 20 */
        chkR('cost.title.h', '.card--cost .card__title', 20, 1) /* 769170f3 fs14 显式 h20 */
        chkC('cost.title.fs', '.card--cost .card__title', 'fontSize', 14)
        chkC('cost.title.fw', '.card--cost .card__title', 'fontWeight', 600)
        chkC('cost.title.color', '.card--cost .card__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('cost.title.text', [textOf('.card--cost .card__title')], ['成本构成'])
        chk('cost.rowCount', doc.querySelectorAll('.card--cost .crow').length, 3)
        chk('cost.row1.padTop', css('.card--cost .crow--first', 'paddingTop'), 16)
        chk('cost.row.padTop', css('.card--cost .crow@@1', 'paddingTop'), 12)
        chkList('cost.rowTops', rects('.card--cost .crow').map(function (r) { return r.top }), [818, 852, 882], 1)
        chkList('cost.rowH', rects('.card--cost .crow').map(function (r) { return r.h }), [34, 30, 30], 1)
        chkStrs('cost.labels', texts('.card--cost .crow__label'), ['输入 Token 成本', '输出 Token 成本', '平台服务费（8%）'])
        chkList('cost.labelTops', rects('.card--cost .crow__label').map(function (r) { return r.top }), [834, 864, 894], 1) /* PNG 标签墨迹 838/868/898 */
        chkC('cost.label.w', '.card--cost .crow__label', 'width', 131)
        chkC('cost.label.fs', '.card--cost .crow__label', 'fontSize', 12) /* 31939c6c fs12 Regular #475569 */
        chkC('cost.label.lh', '.card--cost .crow__label', 'lineHeight', 18)
        chkC('cost.label.color', '.card--cost .crow__label', 'color', 'rgb(71, 85, 105)')
        chkStrs('cost.values', texts('.card--cost .crow__value'), ['¥4,120', '¥8,240', '¥500'])
        chkC('cost.value.fs', '.card--cost .crow__value', 'fontSize', 12) /* 48b5b0b4 fs12 SemiBold #0F172A */
        chkC('cost.value.fw', '.card--cost .crow__value', 'fontWeight', 600)
        chkC('cost.value.lh', '.card--cost .crow__value', 'lineHeight', 18)
        chkC('cost.value.color', '.card--cost .crow__value', 'color', 'rgb(15, 23, 42)')
        chkList('cost.valueRights', rects('.card--cost .crow__value').map(function (r) { return r.right }), [394, 394, 394], 2)
        chkR('cost.total.top', '.card--cost .cost-total', 924, 1) /* container eb942cdd padding-top 12（PNG 合计行 924..965） */
        chkR('cost.total.h', '.card--cost .cost-total', 41, 1) /* 10 + 21 + 10 */
        chkR('cost.total.x', '.card--cost .cost-total', 36, 1)
        chkR('cost.total.w', '.card--cost .cost-total', 358, 1)
        chkC('cost.total.pad', '.card--cost .cost-total', 'padding', '10px')
        chkC('cost.total.radius', '.card--cost .cost-total', 'borderRadius', '10px')
        chkC('cost.total.bg', '.card--cost .cost-total', 'backgroundColor', 'rgb(248, 250, 252)') /* rgba(248,250,252,1) */
        chkC('cost.totalLabel.fs', '.card--cost .cost-total__label', 'fontSize', 12) /* 9eae8c0c fs12 SemiBold #334155 */
        chkC('cost.totalLabel.fw', '.card--cost .cost-total__label', 'fontWeight', 600)
        chkC('cost.totalLabel.lh', '.card--cost .cost-total__label', 'lineHeight', 18)
        chkC('cost.totalLabel.color', '.card--cost .cost-total__label', 'color', 'rgb(51, 65, 85)')
        chkStrs('cost.totalLabel.text', [textOf('.card--cost .cost-total__label')], ['合计'])
        chkR('cost.totalValue.h', '.card--cost .cost-total__value', 21, 1) /* b32f838e fs14 ExtraBold（行盒 14×1.5） */
        chkC('cost.totalValue.fs', '.card--cost .cost-total__value', 'fontSize', 14)
        chkC('cost.totalValue.fw', '.card--cost .cost-total__value', 'fontWeight', 800)
        chkC('cost.totalValue.lh', '.card--cost .cost-total__value', 'lineHeight', 21)
        chkC('cost.totalValue.color', '.card--cost .cost-total__value', 'color', 'rgb(29, 78, 216)')
        chkStrs('cost.totalValue.text', [textOf('.card--cost .cost-total__value')], ['¥12,860'])
        chkR('cost.totalValue.right', '.card--cost .cost-total__value', 384, 2)

        /* ===================== 明细入口卡（design 88ce181b padding 16/20 r18 · stroke 1px） ===================== */
        chkR('detail.x', '.card--detail', 16, 1)
        chkR('detail.top', '.card--detail', 997, 1) /* PNG 描边行 997/1057 */
        chkR('detail.w', '.card--detail', 398, 1)
        chkR('detail.h', '.card--detail', 60, 1) /* 16 + 28 + 16 */
        chkC('detail.pad', '.card--detail', 'padding', '16px 20px')
        chkC('detail.radius', '.card--detail', 'borderRadius', '18px')
        chkC('detail.align', '.card--detail', 'alignItems', 'center')
        chkC('detail.ring', '.card--detail', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkD('detail.borderDeclared', '.card--detail', 'border', null)
        chkR('detail.icon.x', '.detail__icon-wrap', 36, 1) /* 卡 padding-left 20 */
        chkR('detail.icon.w', '.detail__icon-wrap', 20, 1) /* 96786af1 fs18 声明 w20 → 盒 20×27 */
        chkR('detail.icon.h', '.detail__icon-wrap', 27, 1)
        chkR('detail.iconShape.w', '.glyph--list', 16, 1) /* 形状 16×16 贴设计墨迹 x37..52 */
        chkR('detail.iconShape.h', '.glyph--list', 16, 1)
        chk('detail.textWrap.padLeft', css('.detail__text-wrap', 'paddingLeft'), 8) /* container 41c73779 padding-left 8 */
        chkR('detail.text.x', '.detail__text', 64, 1) /* 36 + 20 + 8（PNG 文字墨迹左界 64） */
        chkC('detail.text.fs', '.detail__text', 'fontSize', 13) /* 15549997 fs13 Medium #0F172A */
        chkC('detail.text.fw', '.detail__text', 'fontWeight', 500)
        chkC('detail.text.lh', '.detail__text', 'lineHeight', 19.5, 0.3)
        chkC('detail.text.color', '.detail__text', 'color', 'rgb(15, 23, 42)')
        chkStrs('detail.text.text', [textOf('.detail__text')], ['查看逐日 / 逐模型明细'])
        chkR('detail.chev.x', '.detail__chevron-wrap', 372, 1) /* dd84a7ca fs20 声明 w22 → 盒 22×28 */
        chkR('detail.chev.right', '.detail__chevron-wrap', 394, 1)
        chkR('detail.chev.w', '.detail__chevron-wrap', 22, 1)
        chkR('detail.chev.h', '.detail__chevron-wrap', 28, 1)

        /* ===================== 底部说明（design 5fe4c752 padding[24,0,24,0] 居中 · 两行 11px h16） ===================== */
        chkR('footer.top', '.footer', 1057, 1.5) /* PNG 底部区 1057..1138 */
        chkR('footer.h', '.footer', 80, 2)
        chkC('footer.pad', '.footer', 'padding', '24px 0px')
        chkC('footer.align', '.footer', 'alignItems', 'center')
        chkR('footer.note.h', '.footer__note', 16, 1) /* 9e95e025 fs11 显式 h16 */
        chkR('footer.note.top', '.footer__note', 1081, 2) /* PNG 第一行墨迹 1084..1095 */
        chkC('footer.note.fs', '.footer__note', 'fontSize', 11)
        chkC('footer.note.fw', '.footer__note', 'fontWeight', 400)
        chkC('footer.note.lh', '.footer__note', 'lineHeight', 16)
        chkC('footer.note.color', '.footer__note', 'color', 'rgb(148, 163, 184)')
        chkStrs('footer.note.text', [textOf('.footer__note')], ['数据每小时更新一次，最终以结算账单为准'])
        chkR('footer.updated.top', '.footer__updated', 1097, 2) /* PNG 第二行墨迹 1100..1110 */
        chkC('footer.updated.fs', '.footer__updated', 'fontSize', 11) /* b9444b31 fs11 h16 rgba(203,213,225,1) */
        chkC('footer.updated.lh', '.footer__updated', 'lineHeight', 16)
        chkC('footer.updated.color', '.footer__updated', 'color', 'rgb(203, 213, 225)')
        chkStrs('footer.updated.text', [textOf('.footer__updated')], ['更新时间：2024-06-14 16:20'])

        /* 设计帧字面量登记（不照抄/派生项，逐条说明） */
        var designLiteralDiff = [
          '占比条填充宽 = 百分比 × 轨道宽（本页 42%→81px）：设计声明填充 167/125/86/25 = 百分比 × 卡外层宽 398（轨道实际 192）→ 设计自身不自洽，按语义取轨道宽（与序号 6「分项条宽按分值%」同口径，台账序号 22 备注①）',
          '横轴末位日期标签：设计帧自行左移 8px 以免出血（导出墨迹止于 ~356），实现按数据点 x 居中（末标签盒 363.94..384.06）→ 登记（台账备注⑧）',
          '趋势图：设计为内联矢量（4 网格线 + 折线 #2563EB 3px + 面积 rgba(191,219,254,.35) + 7 数据点）；实现编码为 data-URI <image>（mp-weixin 不支持内联 svg，同序号 6 雷达图）+ 横轴标签作 DOM 文本（绝对定位按数据点 x 居中）',
          '图标为 CSS 绘制占位形状（决策 D5：不引入图标字体库，R-26 禁 emoji）→ 返回箭头墨迹 16 宽 vs 设计 17 宽、日历 12×12 vs 设计墨迹 14×13，形状近似非真实图标',
          '「查看逐日 / 逐模型明细」画布 30 页无明细页（18-API 只有 /usage/hourly 数据接口而无页面）→ 点击 no-op（不跳转、不弹占位 toast、不臆造路由，台账待拍板）',
          '月份选择为原生 uni-picker（mode=date fields=month）→ client-only + 重新取数；H5 下 uni-picker 会挂一个空内部 div（父级 overflow:hidden）→ 页面自身溢出为 0',
          '卡片描边用 ring（盒外 1px）→ 可见描边行比设计中心描边（跨边各半）外移 0.5px（卡内容盒与设计逐值相等）',
          '汇总卡只有 effects drop_shadow(0,6,20,rgba(15,23,42,.06))、无 stroke；其余四卡只有 stroke、无 effects → 逐卡断言，不统一',
          '页面数据全部来自 GET /api/v1/usage/summary（mock api-22/v1/usage/summary）；响应字段级 schema 18-API 未定义 → 逐日/占比/成本字段名为推断、缺字段渲染「—」（台账备注②③）',
          '「较上月节省」「平台服务费（8%）」在 22 份 PRD 零命中 → 服务端优先；费率取 cost.platform_fee_rate，缺省用设计帧常量 8%（文案随费率走）（台账备注④⑤）'
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
          nav: rect('.nav'),
          navBack: rect('.nav__back'),
          navTitle: rect('.nav__title'),
          month: rect('.month'),
          monthCal: rect('.glyph--calendar'),
          monthChev: rect('.glyph--chevron-down'),
          summary: rect('.card--summary'),
          summaryTitle: rect('.card--summary .card__title'),
          tiles: rects('.card--summary .tile'),
          tilesFirst: rect('.tiles--first'),
          tilesSecond: rect('.tiles--second'),
          trend: rect('.card--trend'),
          trendHead: rect('.card--trend .card__head'),
          legendDot: rect('.legend__dot'),
          legendText: rect('.legend__text'),
          chart: rect('.trend'),
          chartImg: rect('.trend__img'),
          trendLabels: rects('.trend__label'),
          models: rect('.card--models'),
          modelRows: rects('.card--models .mrow'),
          modelNames: rects('.card--models .mrow__name'),
          modelTracks: rects('.card--models .mrow__track'),
          modelFills: rects('.card--models .mrow__fill'),
          modelPcts: rects('.card--models .mrow__pct'),
          cost: rect('.card--cost'),
          costRows: rects('.card--cost .crow'),
          costLabels: rects('.card--cost .crow__label'),
          costValues: rects('.card--cost .crow__value'),
          costTotal: rect('.card--cost .cost-total'),
          costTotalValue: rect('.card--cost .cost-total__value'),
          detail: rect('.card--detail'),
          detailIcon: rect('.detail__icon-wrap'),
          detailIconShape: rect('.glyph--list'),
          detailText: rect('.detail__text'),
          detailChev: rect('.detail__chevron-wrap'),
          footer: rect('.footer'),
          footerNote: rect('.footer__note'),
          footerUpdated: rect('.footer__updated'),
          texts: {
            navTitle: textOf('.nav__title'),
            month: textOf('.month__value'),
            summaryTitle: textOf('.card--summary .card__title'),
            tileValues: texts('.card--summary .tile__value'),
            tileLabels: texts('.card--summary .tile__label'),
            trendTitle: textOf('.card--trend .card__title'),
            legend: textOf('.legend__text'),
            trendLabels: texts('.trend__label'),
            modelTitle: textOf('.card--models .card__title'),
            modelNames: texts('.card--models .mrow__name'),
            modelPcts: texts('.card--models .mrow__pct'),
            costTitle: textOf('.card--cost .card__title'),
            costLabels: texts('.card--cost .crow__label'),
            costValues: texts('.card--cost .crow__value'),
            costTotal: textOf('.card--cost .cost-total__value'),
            detailText: textOf('.detail__text'),
            footerNote: textOf('.footer__note'),
            footerUpdated: textOf('.footer__updated')
          },
          counts: {
            cards: doc.querySelectorAll(CARDS).length,
            tiles: doc.querySelectorAll('.card--summary .tile').length,
            modelRows: doc.querySelectorAll('.card--models .mrow').length,
            costRows: doc.querySelectorAll('.card--cost .crow').length,
            trendLabels: doc.querySelectorAll('.trend__label').length,
            tabbar: doc.querySelectorAll('.tabbar').length,
            inputs: doc.querySelectorAll('input,textarea').length
          },
          userAgent: win.navigator.userAgent
        }
      }

"""

MAIN = r"""      async function main() {
        try {
          await waitFor('[data-testid="month-value"]')
          await sleep(1600)
          phase(1)
          if (NO_ACTION || !SCENARIO || SHOT_ONLY) return

          /* ?scenario=back：返回 = navigation（navigateBack；H5 直接进入本页时栈内无上一页）
             硬证据 = hash 不变 + 无 toast + 零写请求；windowMark 用来区分「uni 降级为整页重载」与「重复取数」 */
          if (SCENARIO === 'back') {
            var pageWin = f.contentWindow
            try { pageWin.__usageMark = 'kept' } catch (e) {}
            var cB = clickIn('[data-testid="usage-back"]')
            await sleep(1500)
            var markAfter = null
            try { markAfter = pageWin.__usageMark || null } catch (e) { markAfter = 'ERR' }
            sink(2, {
              scenario: SCENARIO, clicked: cB,
              hash: hashNow(),
              toast: toastText(f.contentDocument),
              cardCount: countIn('.card'),
              windowMark: markAfter
            })
            return
          }

          /* ?scenario=month：原生月份 picker（client-only）→ 确认后按新月份重新取数
             硬证据 = serve 实收第二次 GET /api/v1/usage/summary?month=… */
          if (SCENARIO === 'month') {
            var cM = clickIn('[data-testid="month-picker"]')
            await sleep(1500)
            var overlay = pickerProbe(f.contentDocument)
            var confirm = clickOverlayConfirm(f.contentDocument)
            await sleep(2200)
            var after = collect(f.contentDocument, f.contentWindow, false)
            sink(2, {
              scenario: SCENARIO,
              clickedHost: cM,
              overlay: overlay.slice(0, 6),
              confirm: confirm,
              monthAfter: after.texts.month,
              monthRect: after.month,
              tileAfter: after.texts.tileValues,
              hash: hashNow()
            })
            return
          }

          /* ?scenario=detail：「查看逐日 / 逐模型明细」无落点（画布无明细页）→ no-op：不跳转、不弹 toast、无新请求 */
          if (SCENARIO === 'detail') {
            var cD = clickIn('[data-testid="detail-entry"]')
            await sleep(1500)
            sink(2, {
              scenario: SCENARIO, clicked: cD,
              hash: hashNow(),
              toast: toastText(f.contentDocument),
              detailText: textIn('.detail__text')
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
