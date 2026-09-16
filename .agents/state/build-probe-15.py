"""Build __measure-contract.html (序号 15 · page-15-2「【合同与通知】合同签署 2」) as a
430-wide iframe probe with design-expectation checks (chk/chkR/chkC/chkD/chkList/chkStrs/chkP).

做法与 build-probe-10/11/12/12v2/12v3 同：从 __measure-quote-success.html（同族载体页，含
`resolveAll` / `declared` / `normShadow` 等全套 helpers）切四段「与帧无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计 / sink+phase+点击工具）逐字节复用，
本文件只写 page-15-2 自己的 checks / return / main。

want 两类来源（先量再写，不凭截图目测）：
  (a) 声明值 .calicat/raw/pages/page-15-2/{design.json,design.tree.json}
      python .agents/state/dump-layout.py page-15-2      # 全字段（gap/lineHeight/effects/stroke/cornerRadius）
      python .agents/state/text-fields.py page-15-2      # 文本叶子 fontSize/字重/字色/宽高/文案
  (b) 设计截图 PNG 实测（430×1231）
      python .agents/state/png-rowclass.py <png> --x0 20 --x1 410
      python .agents/state/png-textbands.py <png> x0 y0 x1 y1 --minink 3

设计骨架（逐条与 PNG 墨迹对过）：
  顶栏 0..96（padding 48/16/12/16 + 返回图标字形行盒 fs24×1.5 = 36）· 内容区 padding[12,16,0,16]
  卡1 合同状态卡 108..194(86 = 20+46+20) · 卡2 电子签提示卡 206..257(51 = 12+27+12)
  卡3 合同基本信息 269..453(184) · 卡4 费用与分成 465..619(154) · 卡5 关键条款 631..797(166)
  卡6 签署信息 809..963(154) · 卡7 签署记录 975..1131(156) · 底栏 1147..1231(84 = 12+48+24)
  卡内锚点（PNG 墨迹）：状态标题行 130..152(row 22) · 期限行 156..172
    字段卡 title 289..309(h20) · 行 325/355/385/415(pitch 30 = 18 + 12；首行与 title 距 16)
    费用卡 title 485..505 · 行 521/551/581 · 条款卡 title 651..671 · 条款 679/705/731/757(行 20 + 6)
    记录卡 title 995..1015 · 记录1 1031(title18 + time16 = 34) · 记录2 1077

本页定标：
  · 图标字形行盒 = 字号 × 1.5（fs24 → 26×36 · fs18 → 20×27）；D5 占位形状画在盒子内部，
    字形色就读「盒子内那个形状元素」的 border 色（本页 5 个字形均非 ::before 实现 → 用 chkC）。
  · 文本行盒一律取 PNG 实测（18 / 16 / 20 / 22 / 34 …），不用 lineHeight 1.2 反推
    —— 设计树里 fit_content 文本的 lineHeight 字段是 1.2，而 PNG 行盒是 1.5 倍系（同前几页）。
  · stroke{align:center,thickness:1} → box-shadow: 0 0 0 1px（border 会占布局）
    effects.drop_shadow → box-shadow。
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-quote-success.html")
DST = os.path.join(HM, "__measure-contract.html")

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
    "if (SHOT_ONLY) f.style.height = '1018px' /* = 设计帧高 */",
    "if (SHOT_ONLY) f.style.height = '1231px' /* = 设计帧高 */",
)
assert "'1231px'" in top, "SHOT 高度替换失败（顶部作用域切片变了？）"
preamble = "\n".join(src[i_collect:i_over])   # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])    # over / missing 统计（引用 NEED_TEXT / CARDS）
tail = "\n".join(src[i_sink:i_main])          # sink / phase / clickIn / toastText / hashNow / waitFor / sleep / textIn / countIn / bgsIn

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-contract</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      iframe { width: 430px; height: 900px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜（uni-app 技能 §5 口径）
         页面 15：/pages/contract/index（【合同与通知】合同签署 2，page-15-2 · layer_id 14d79713-8314-41a4-a8df-b4aff9ecd7b8）
         设计真源：.calicat/raw/pages/page-15-2/design.tree.json（本轮重抓 sha256 ca94e93e… 逐字节相同）
         设计骨架（声明值 + 设计 PNG 430x1231 实测）：
           顶栏 0..96（padding 48/16/12/16 · 返回字形盒 26×36）· 内容区 padding 12/16/0/16
           卡1 108..194(86) · 卡2 206..257(51) · 卡3 269..453(184) · 卡4 465..619(154)
           卡5 631..797(166) · 卡6 809..963(154) · 卡7 975..1131(156) · 底栏 1147..1231(84)
           卡内锚点：状态标题行 130..152 · 期限行 156..172 · 字段行 325/355/385/415
                     费用行 521/551/581 · 条款 679/705/731/757 · 记录1 1031 / 记录2 1077
                     PDF 按钮 x16..142 h48 · 去签署 x154..414 h48
         ?scenario=pdf|sign|back 逐个回放出口；不带 scenario（或 noaction）只取 phase1 设计期望值相 -->
    <iframe id="f" src="/index.html#/pages/contract/index?contractId=c1"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

PRELUDE = r"""
        var CARDS = '.card'
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-15-2 design.tree.json；
           图标字形层 content 为空不进清单。示例值「CT-2024-0613-008」「云智科技有限公司」「8%」等
           来自本页 mock（api-15/v1/contracts/c1），不是页面硬编码 → 进清单） */
        var NEED_TEXT = [
          '合同签署', '编号 CT-2024-0613-008',
          'API 接入服务合同', '待签署', '请在 2024-06-20 前完成签署，逾期将自动作废',
          '本合同采用电子签章，签署后即时生效并具备法律效力。',
          '合同基本信息', '供应商', '云智科技有限公司', '合作模式', 'API 转售（非独家）',
          '生效期', '2024-07-01 至 2025-06-30', '结算账期', '月结 · 次月 15 日',
          '费用与分成', '平台服务费率', '8%', '结算币种', 'CNY', '最低结算额', '¥1,000.00',
          '关键条款', '1. 供应商须保证上游接口的合法来源与稳定可用。',
          '2. 平台按实际用量结算，价格以审核通过的报价单为准。',
          '3. 若月度可用率低于 99%，平台有权下调报价或终止合作。',
          '4. 合同期内价格调整需双方确认后生效。',
          '签署信息', '签署人', '李明（商务负责人）', '手机号', '138 **** 6621', '签署方式', '短信验证码签署',
          '签署记录', '平台方已盖章', '2024-06-13 09:12', '等待供应商签署', '请尽快完成，逾期作废',
          'PDF', '去签署'
        ]
"""

CHECKS = r"""
        /* ===================== 整页（设计帧 430×1231） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 1231, 2)
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.ct', 'backgroundColor', 'rgb(248, 250, 252)') /* 合同签署页 c77e82e3 fills rgba(248,250,252,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 7)
        chk('page.tabbarAbsent', !!doc.querySelector('.tabbar'), false)
        chk('page.inputCount', doc.querySelectorAll('input,textarea').length, 0)
        /* PNG 实测卡边界：108..194 / 206..257 / 269..453 / 465..619 / 631..797 / 809..963 / 975..1131 */
        chkList('page.cardTops', rects(CARDS).map(function (r) { return r.top }), [108, 206, 269, 465, 631, 809, 975], 2)
        chkList('page.cardHeights', rects(CARDS).map(function (r) { return r.h }), [86, 51, 184, 154, 166, 154, 156], 2)
        chkList('page.cardX', rects(CARDS).map(function (r) { return r.x }), [16, 16, 16, 16, 16, 16, 16], 1)
        chkList('page.cardW', rects(CARDS).map(function (r) { return r.w }), [398, 398, 398, 398, 398, 398, 398], 1)
        chkStrs('page.cardBg', colors(CARDS),
          ['rgb(255, 255, 255)', 'rgb(255, 255, 255)', 'rgb(255, 255, 255)', 'rgb(255, 255, 255)',
           'rgb(255, 255, 255)', 'rgb(255, 255, 255)', 'rgb(255, 255, 255)'])
        chkStrs('page.cardRadius', ['@@0', '@@1', '@@2', '@@3', '@@4', '@@5', '@@6'].map(function (s) { return css(CARDS + s, 'borderRadius') }),
          [16, 16, 16, 16, 16, 16, 16]) /* 探针 norm() 把 '16px' 归一成 16 → want 写数值（chkStrs 内部 String() 比较） */
        /* 卡距 12（设计每个后续卡片外包裹层 padding-top 12）· 内容区 padding-bottom 0 + 底栏外包裹 padding-top 16 */
        chkList('page.cardGaps', [0, 1, 2, 3, 4, 5].map(function (i) {
          return rect(CARDS + '@@' + (i + 1)).top - rect(CARDS + '@@' + i).bottom
        }), [12, 12, 12, 12, 12, 12], 1)
        chk('page.gapToBar', rect('.ct__bar').top - rect(CARDS + '@@6').bottom, 16, 1)
        /* 卡1 设计 effects = drop_shadow(0,6,20,rgba(15,23,42,0.06))；其余卡是 stroke（无 effects） */
        chkC('page.card1Shadow', '.card@@0', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 6px 20px 0px')
        chkD('page.card1BorderDeclared', '.card@@0', 'border', null) /* 反向断言：设计只有投影，没有描边 */
        chkStrs('page.cardRings', ['@@1', '@@2', '@@3', '@@4', '@@5', '@@6'].map(function (s) { return css(CARDS + s, 'boxShadow') }),
          ['rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px',
           'rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px'])
        chkD('page.cardRingBorderDeclared', '.card@@1', 'border', null) /* stroke{align:center} → 只能 ring 表达 */

        /* ===================== 顶部导航（design c6e9ba1f padding[48,16,12,16]） ===================== */
        chkR('nav.h', '.ct__nav', 96, 1) /* 48 + 图标字形行盒 36 + 12 */
        chkC('nav.pad', '.ct__nav', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.ct__nav', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('nav.align', '.ct__nav', 'alignItems', 'center')
        chkR('nav.back.x', '[data-testid="back"]', 16, 1)
        chkR('nav.back.w', '[data-testid="back"]', 26, 1) /* 返回字形 图层 fs24 w26 */
        chkR('nav.back.h', '[data-testid="back"]', 36, 1)
        chkR('nav.backIcon.w', '.ct__nav .icon-line--24', 26, 1)
        chkR('nav.backIcon.h', '.ct__nav .icon-line--24', 36, 1) /* 字形行盒 = 字号 × 1.5 */
        chkC('nav.backIcon.color', '.ic-back', 'borderBottomColor', 'rgb(51, 65, 85)') /* 图层 fills rgba(51,65,85,1) */
        chk('nav.title.inkX', rect('[data-testid="nav-title"]').x + Number(css('.nav__title', 'paddingLeft')), 54, 1) /* 16+26+12 */
        chkC('nav.title.fs', '.nav__title', 'fontSize', 17) /* cfce7649 fs17 Bold */
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700)
        chkC('nav.title.lh', '.nav__title', 'lineHeight', 20.4, 0.2) /* 设计 lineHeight 1.2 × 17 */
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('[data-testid="nav-title"]')], ['合同签署'])
        chk('nav.spacerGrow', css('.nav__spacer', 'flexGrow'), 1) /* 设计 spacer fill_container */
        chkR('nav.no.right', '[data-testid="nav-no"]', 414, 1)
        chkC('nav.no.fs', '.nav__no', 'fontSize', 11) /* 106ed810 fs11 Regular #94A3B8 w117 */
        chkC('nav.no.fw', '.nav__no', 'fontWeight', 400)
        chkC('nav.no.lh', '.nav__no', 'lineHeight', 13.2, 0.2)
        chkC('nav.no.color', '.nav__no', 'color', 'rgb(148, 163, 184)')
        chkStrs('nav.no.text', [textOf('[data-testid="nav-no"]')], ['编号 CT-2024-0613-008']) /* 设计是单个文本图层（含「编号 」前缀） */

        /* ===================== 合同状态卡（design a05669ed padding20 r16 · horizontal align center） ===================== */
        chkR('status.top', '[data-testid="card-status"]', 108, 2)
        chkR('status.h', '[data-testid="card-status"]', 86, 2) /* 20 + max(46, 42) + 20 */
        chkC('status.pad', '.card--status', 'padding', '20px')
        chkC('status.radius', '.card--status', 'borderRadius', '16px')
        chkC('status.bg', '.card--status', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('status.align', '.card--status', 'alignItems', 'center')
        chkR('status.icon.x', '.status__icon', 36, 1) /* 16 + 20 */
        chkR('status.icon.w', '.status__icon', 46, 1) /* 状态图标 87c09b04 46×46 r14 */
        chkR('status.icon.h', '.status__icon', 46, 1)
        chkC('status.icon.radius', '.status__icon', 'borderRadius', '14px')
        chkC('status.icon.bg', '.status__icon', 'backgroundColor', 'rgb(255, 251, 235)')
        chkR('status.iconGlyph.w', '.status__icon .icon-line--24', 26, 1) /* 字形 864f86d5 fs24 w26 → 盒 26×36 */
        chkR('status.iconGlyph.h', '.status__icon .icon-line--24', 36, 1)
        chkC('status.iconGlyph.color', '.ic-contract', 'borderTopColor', 'rgb(217, 119, 6)') /* 字形 fills rgba(217,119,6,1) */
        chk('status.content.inkX', rect('.status__content').x + Number(css('.status__content', 'paddingLeft')), 94, 1) /* 82 + 12（容器 padding-left 12） */
        chkR('status.row.h', '.status__row', 22, 1) /* 状态标题行 = max(标签行, 待签署标 22) */
        chkC('status.title.fs', '.status__title', 'fontSize', 15) /* 121da433 fs15 SemiBold */
        chkC('status.title.fw', '.status__title', 'fontWeight', 600)
        chkC('status.title.lh', '.status__title', 'lineHeight', 18)
        chkC('status.title.color', '.status__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('status.title.text', [textOf('[data-testid="status-title"]')], ['API 接入服务合同'])
        chkR('status.chip.h', '.status-chip', 22, 1) /* 待签署标 01af6609 h22 padding[0,8] r11 #FFFBEB */
        chkC('status.chip.pad', '.status-chip', 'padding', '0px 8px')
        chkC('status.chip.radius', '.status-chip', 'borderRadius', '11px')
        chkC('status.chip.bg', '.status-chip', 'backgroundColor', 'rgb(255, 251, 235)')
        chk('status.chip.gap', rect('.status-chip').x - rect('[data-testid="status-title"]').right, 8, 1) /* 标题块容器 padding-left 8 */
        chkC('status.chip.text.fs', '.status-chip__text', 'fontSize', 11) /* 4c410aee fs11 Medium #B45309 */
        chkC('status.chip.text.fw', '.status-chip__text', 'fontWeight', 500)
        chkC('status.chip.text.lh', '.status-chip__text', 'lineHeight', 13.2, 0.2)
        chkC('status.chip.text.color', '.status-chip__text', 'color', 'rgb(180, 83, 9)')
        chkStrs('status.chip.text', [textOf('[data-testid="status-chip"]')], ['待签署'])
        chkR('status.deadline.h', '[data-testid="deadline"]', 20, 1) /* content-box：padding-top 4 + 行盒 16 */
        chkC('status.deadline.padTop', '.status__deadline', 'paddingTop', 4)
        chkC('status.deadline.fs', '.status__deadline', 'fontSize', 11) /* 9002dd75 fs11 h16 #94A3B8 */
        chkC('status.deadline.fw', '.status__deadline', 'fontWeight', 400)
        chkC('status.deadline.lh', '.status__deadline', 'lineHeight', 16)
        chkC('status.deadline.color', '.status__deadline', 'color', 'rgb(148, 163, 184)')
        chkStrs('status.deadline.text', [textOf('[data-testid="deadline"]')], ['请在 2024-06-20 前完成签署，逾期将自动作废'])
        chk('status.deadline.toCardBottom', rect('[data-testid="card-status"]').bottom - rect('[data-testid="deadline"]').bottom, 22, 1) /* 卡 padding-bottom 20 + 内容列(42) 在 46 高盒里的居中余量 2 */

        /* ===================== 电子签提示卡（design a5af23f5 padding[12,20,12,20] r16 stroke1 #EEF2F7） ===================== */
        chkR('tip.top', '[data-testid="tip-card"]', 206, 2)
        chkR('tip.h', '[data-testid="tip-card"]', 51, 2) /* 12 + 字形行盒 27 + 12 */
        chkC('tip.pad', '.card--tip', 'padding', '12px 20px')
        chkC('tip.radius', '.card--tip', 'borderRadius', '16px')
        chkC('tip.ring', '.card--tip', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkC('tip.align', '.card--tip', 'alignItems', 'flex-start')
        chkR('tip.icon.w', '.card--tip .icon-line--18', 20, 1) /* 字形 b5a1d335 fs18 w20 → 盒 20×27 */
        chkR('tip.icon.h', '.card--tip .icon-line--18', 27, 1)
        chkC('tip.icon.color', '.ic-shield', 'borderTopColor', 'rgb(37, 99, 235)') /* 字形 fills rgba(37,99,235,1) */
        chk('tip.text.inkX', rect('[data-testid="tip"]').x + Number(css('.tip__text', 'paddingLeft')), 64, 1) /* 16+20+20+8 */
        chkC('tip.text.w', '.tip__text', 'width', 276) /* 4c87113e w276（该元素 padding-left 8 → 盒子 284） */
        chkC('tip.text.fs', '.tip__text', 'fontSize', 11)
        chkC('tip.text.fw', '.tip__text', 'fontWeight', 400)
        chkC('tip.text.lh', '.tip__text', 'lineHeight', 16, 0.2) /* PNG 派生：设计文案墨迹 221..232 → 行盒 16（设计树 lineHeight 1.2=13.2 是陈旧值，同 11px 显式 h16 的期限/记录时间节点） */
        chkC('tip.text.color', '.tip__text', 'color', 'rgb(100, 116, 139)')
        chk('tip.textLines', Math.round(rect('[data-testid="tip"]').h / css('.tip__text', 'lineHeight')), 1) /* PNG 墨迹 221..231 单行 */
        chkStrs('tip.text.text', [textOf('[data-testid="tip"]')], ['本合同采用电子签章，签署后即时生效并具备法律效力。'])

        /* ===================== 合同基本信息卡（design 6d9b8d54 padding20 r16 stroke1） ===================== */
        chkR('basic.top', '[data-testid="card-basic"]', 269, 2)
        chkR('basic.h', '[data-testid="card-basic"]', 184, 2) /* 20+20+16+4×18+3×12+20 */
        chkC('basic.pad', '.card--basic', 'padding', '20px')
        chkC('basic.radius', '.card--basic', 'borderRadius', '16px')
        chkC('basic.ring', '.card--basic', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkR('basic.title.h', '[data-testid="card-basic-title"]', 20, 1) /* 14211c82 h20 fs14 SemiBold */
        chkC('basic.title.fs', '.card--basic .card__title', 'fontSize', 14)
        chkC('basic.title.fw', '.card--basic .card__title', 'fontWeight', 600)
        chkC('basic.title.lh', '.card--basic .card__title', 'lineHeight', 20)
        chkC('basic.title.color', '.card--basic .card__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('basic.title.text', [textOf('[data-testid="card-basic-title"]')], ['合同基本信息'])
        chk('basic.rowsGap1', rects('.card--basic .crow')[0].top - rect('[data-testid="card-basic-title"]').bottom, 16, 1)
        chkList('basic.rowTops', rects('.card--basic .crow').map(function (r) { return r.top }), [325, 355, 385, 415], 2)
        chkList('basic.rowH', rects('.card--basic .crow').map(function (r) { return r.h }), [18, 18, 18, 18], 1)
        chkList('basic.rowGaps', [1, 2, 3].map(function (i) {
          var rs = rects('.card--basic .crow'); return rs[i].top - rs[i - 1].bottom
        }), [12, 12, 12], 1)
        chkStrs('basic.labels', texts('.card--basic .crow__label'), ['供应商', '合作模式', '生效期', '结算账期'])
        chkStrs('basic.values', texts('.card--basic .crow__value'), ['云智科技有限公司', 'API 转售（非独家）', '2024-07-01 至 2025-06-30', '月结 · 次月 15 日'])
        chkC('basic.label.w', '.card--basic .crow__label', 'width', 87) /* 8dd9e0a3 w87 */
        chkC('basic.label.fs', '.card--basic .crow__label', 'fontSize', 12)
        chkC('basic.label.fw', '.card--basic .crow__label', 'fontWeight', 400)
        chkC('basic.label.lh', '.card--basic .crow__label', 'lineHeight', 18)
        chkC('basic.label.color', '.card--basic .crow__label', 'color', 'rgb(148, 163, 184)')
        chkC('basic.value.fs', '.card--basic .crow__value', 'fontSize', 13) /* 1e58a3b7 fs13 SemiBold */
        chkC('basic.value.fw', '.card--basic .crow__value', 'fontWeight', 600)
        chkC('basic.value.lh', '.card--basic .crow__value', 'lineHeight', 18)
        chkC('basic.value.color', '.card--basic .crow__value', 'color', 'rgb(15, 23, 42)')
        chk('basic.value.left', rects('.card--basic .crow__value')[0].x - rects('.card--basic .crow__label')[0].right, 0, 1)

        /* ===================== 费用与分成卡（design 05b6072f · 值右对齐 Bold） ===================== */
        chkR('fee.top', '[data-testid="card-fee"]', 465, 2)
        chkR('fee.h', '[data-testid="card-fee"]', 154, 2) /* 20+20+16+3×18+2×12+20 */
        chkC('fee.pad', '.card--fee', 'padding', '20px')
        chkC('fee.ring', '.card--fee', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkR('fee.title.h', '[data-testid="card-fee-title"]', 20, 1)
        chkStrs('fee.title.text', [textOf('[data-testid="card-fee-title"]')], ['费用与分成'])
        chk('fee.rowsGap1', rects('.card--fee .crow')[0].top - rect('[data-testid="card-fee-title"]').bottom, 16, 1)
        chkList('fee.rowTops', rects('.card--fee .crow').map(function (r) { return r.top }), [521, 551, 581], 2)
        chkList('fee.rowH', rects('.card--fee .crow').map(function (r) { return r.h }), [18, 18, 18], 1)
        chkStrs('fee.labels', texts('.card--fee .crow__label'), ['平台服务费率', '结算币种', '最低结算额'])
        chkStrs('fee.values', texts('.card--fee .crow__value'), ['8%', 'CNY', '¥1,000.00'])
        chkC('fee.label.fs', '.card--fee .crow__label', 'fontSize', 12) /* f61c35f4 fs12 #64748B */
        chkC('fee.label.fw', '.card--fee .crow__label', 'fontWeight', 400)
        chkC('fee.label.color', '.card--fee .crow__label', 'color', 'rgb(100, 116, 139)')
        chkC('fee.value.fs', '.card--fee .crow__value', 'fontSize', 13) /* 5e9df7d8 fs13 Bold */
        chkC('fee.value.fw', '.card--fee .crow__value', 'fontWeight', 700)
        chkC('fee.value.color', '.card--fee .crow__value', 'color', 'rgb(15, 23, 42)')
        chkList('fee.valueRight', rects('.card--fee .crow__value').map(function (r) { return r.right }), [394, 394, 394], 1)

        /* ===================== 关键条款卡（design 02f96094 · 首条 pt8 其后 pt6 · 行 20） ===================== */
        chkR('terms.top', '[data-testid="card-terms"]', 631, 2)
        chkR('terms.h', '[data-testid="card-terms"]', 166, 2) /* 20+20+8+20+3×(6+20)+20 */
        chkC('terms.pad', '.card--terms', 'padding', '20px')
        chkC('terms.ring', '.card--terms', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkR('terms.title.h', '[data-testid="card-terms-title"]', 20, 1)
        chkStrs('terms.title.text', [textOf('[data-testid="card-terms-title"]')], ['关键条款'])
        chk('terms.clauseGap1', rects('.clause')[0].top - rect('[data-testid="card-terms-title"]').bottom, 8, 1)
        chkList('terms.clauseTops', rects('.clause').map(function (r) { return r.top }), [679, 705, 731, 757], 2)
        chkList('terms.clauseH', rects('.clause').map(function (r) { return r.h }), [20, 20, 20, 20], 1)
        chkList('terms.clauseGaps', [1, 2, 3].map(function (i) {
          var cs = rects('.clause'); return cs[i].top - cs[i - 1].bottom
        }), [6, 6, 6], 1)
        chkStrs('terms.clauseTexts', texts('.clause__text'), [
          '1. 供应商须保证上游接口的合法来源与稳定可用。',
          '2. 平台按实际用量结算，价格以审核通过的报价单为准。',
          '3. 若月度可用率低于 99%，平台有权下调报价或终止合作。',
          '4. 合同期内价格调整需双方确认后生效。'])
        chkC('terms.clause.fs', '.clause__text', 'fontSize', 12) /* 2bf9caaf fs12 h20 #64748B */
        chkC('terms.clause.fw', '.clause__text', 'fontWeight', 400)
        chkC('terms.clause.lh', '.clause__text', 'lineHeight', 20)
        chkC('terms.clause.color', '.clause__text', 'color', 'rgb(100, 116, 139)')

        /* ===================== 签署信息卡（design 62c0922c padding20 r16） ===================== */
        chkR('sign.top', '[data-testid="card-sign"]', 809, 2)
        chkR('sign.h', '[data-testid="card-sign"]', 154, 2)
        chkC('sign.pad', '.card--sign', 'padding', '20px')
        chkC('sign.ring', '.card--sign', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkR('sign.title.h', '[data-testid="card-sign-title"]', 20, 1)
        chkStrs('sign.title.text', [textOf('[data-testid="card-sign-title"]')], ['签署信息'])
        chk('sign.rowsGap1', rects('.card--sign .crow')[0].top - rect('[data-testid="card-sign-title"]').bottom, 16, 1)
        chkList('sign.rowTops', rects('.card--sign .crow').map(function (r) { return r.top }), [865, 895, 925], 2)
        chkStrs('sign.labels', texts('.card--sign .crow__label'), ['签署人', '手机号', '签署方式'])
        chkStrs('sign.values', texts('.card--sign .crow__value'), ['李明（商务负责人）', '138 **** 6621', '短信验证码签署'])
        chkC('sign.label.color', '.card--sign .crow__label', 'color', 'rgb(148, 163, 184)')
        chkC('sign.value.fw', '.card--sign .crow__value', 'fontWeight', 600)
        chkC('sign.value.color', '.card--sign .crow__value', 'color', 'rgb(15, 23, 42)')

        /* ===================== 签署记录卡（design bedc9151 · 记录 34 = 18 + 16 · 首条 pt16 其后 pt12） ===================== */
        chkR('rec.top', '[data-testid="card-records"]', 975, 2)
        chkR('rec.h', '[data-testid="card-records"]', 156, 2) /* 20+20+16+34+12+34+20 */
        chkC('rec.pad', '.card--records', 'padding', '20px')
        chkC('rec.ring', '.card--records', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkR('rec.title.h', '[data-testid="card-records-title"]', 20, 1)
        chkStrs('rec.title.text', [textOf('[data-testid="card-records-title"]')], ['签署记录'])
        chk('rec.gap1', rects('.record')[0].top - rect('[data-testid="card-records-title"]').bottom, 16, 1)
        chkList('rec.recordTops', rects('.record').map(function (r) { return r.top }), [1031, 1077], 2)
        chkList('rec.recordH', rects('.record').map(function (r) { return r.h }), [34, 34], 1)
        chk('rec.gap2', rects('.record')[1].top - rects('.record')[0].bottom, 12, 1)
        chkList('rec.dotW', rects('.record__dot').map(function (r) { return r.w }), [11, 11], 1) /* 记录点 11×10 r5 */
        chkList('rec.dotH', rects('.record__dot').map(function (r) { return r.h }), [10, 10], 1)
        chkC('rec.dot.radius', '.record__dot', 'borderRadius', '5px')
        chkStrs('rec.dotBg', colors('.record__dot'), ['rgb(22, 163, 74)', 'rgb(245, 158, 11)']) /* #16A34A / #F59E0B */
        chkStrs('rec.dotTone', resolveAll('.record__dot').map(function (e) { return e.getAttribute('data-tone') }), ['success', 'pending'])
        chk('rec.body.inkX', rect('.record__body').x + Number(css('.record__body', 'paddingLeft')), 59, 1) /* 47 + 12（容器 padding-left 12） */
        chkR('rec.titleBox.h', '.record__title', 18, 1) /* f75ced53 h18 fs12 SemiBold */
        chkC('rec.titleBox.fs', '.record__title', 'fontSize', 12)
        chkC('rec.titleBox.fw', '.record__title', 'fontWeight', 600)
        chkC('rec.titleBox.lh', '.record__title', 'lineHeight', 18)
        chkC('rec.titleBox.color', '.record__title', 'color', 'rgb(15, 23, 42)')
        chkR('rec.timeBox.h', '.record__time', 16, 1) /* 70c92bdc h16 fs11 */
        chkC('rec.timeBox.fs', '.record__time', 'fontSize', 11)
        chkC('rec.timeBox.fw', '.record__time', 'fontWeight', 400)
        chkC('rec.timeBox.lh', '.record__time', 'lineHeight', 16)
        chkC('rec.timeBox.color', '.record__time', 'color', 'rgb(148, 163, 184)')
        chkStrs('rec.titles', texts('.record__title'), ['平台方已盖章', '等待供应商签署'])
        chkStrs('rec.times', texts('.record__time'), ['2024-06-13 09:12', '请尽快完成，逾期作废'])

        /* ===================== 底部操作条（design 06df97bf padding[12,16,24,16]） ===================== */
        chkR('bar.wrap.h', '.ct__bar-wrap', 100, 2) /* padding-top 16 + 栏 84 */
        chkR('bar.top', '.ct__bar', 1147, 2)
        chkR('bar.h', '.ct__bar', 84, 2) /* 12 + 48 + 24 */
        chkC('bar.pad', '.ct__bar', 'padding', '12px 16px 24px')
        chkC('bar.bg', '.ct__bar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('bar.align', '.ct__bar', 'alignItems', 'center')
        chk('bar.btn.top', rect('[data-testid="btn-pdf"]').top - rect('.ct__bar').top, 12, 1)
        chkR('bar.pdf.x', '[data-testid="btn-pdf"]', 16, 1)
        chkR('bar.pdf.w', '[data-testid="btn-pdf"]', 126, 1) /* 8bbcfb54 w126 h48 r12 */
        chkR('bar.pdf.h', '[data-testid="btn-pdf"]', 48, 1)
        chkC('bar.pdf.radius', '[data-testid="btn-pdf"]', 'borderRadius', '12px')
        chkC('bar.pdf.bg', '[data-testid="btn-pdf"]', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('bar.pdf.ring', '[data-testid="btn-pdf"]', 'boxShadow', 'rgb(203, 213, 225) 0px 0px 0px 1px') /* stroke thickness 1 */
        chkD('bar.pdf.borderDeclared', '[data-testid="btn-pdf"]', 'border', null)
        chkR('bar.pdfIcon.w', '[data-testid="btn-pdf"] .icon-line--18', 20, 1) /* 字形 1e5a64dd fs18 w20 → 盒 20×27 */
        chkR('bar.pdfIcon.h', '[data-testid="btn-pdf"] .icon-line--18', 27, 1)
        chkC('bar.pdfIcon.color', '.ic-download', 'borderBottomColor', 'rgb(71, 85, 105)') /* 字形 fills rgba(71,85,105,1) */
        chk('bar.pdfText.pad', css('[data-testid="btn-pdf"] .btn__text', 'paddingLeft'), 5) /* 容器 padding-left 5 */
        chkC('bar.pdfText.fs', '[data-testid="btn-pdf"] .btn__text', 'fontSize', 13) /* dde0782c fs13 Medium */
        chkC('bar.pdfText.fw', '[data-testid="btn-pdf"] .btn__text', 'fontWeight', 500)
        chkC('bar.pdfText.lh', '[data-testid="btn-pdf"] .btn__text', 'lineHeight', 18)
        chkC('bar.pdfText.color', '[data-testid="btn-pdf"] .btn__text', 'color', 'rgb(71, 85, 105)')
        chkStrs('bar.pdfText.text', [textOf('[data-testid="btn-pdf"]')], ['PDF'])
        chk('bar.btnGap', rect('[data-testid="btn-sign"]').x - rect('[data-testid="btn-pdf"]').right, 12, 1) /* 容器 padding-left 12 */
        chkR('bar.sign.x', '[data-testid="btn-sign"]', 154, 1)
        chkR('bar.sign.right', '[data-testid="btn-sign"]', 414, 1) /* fill_container */
        chkR('bar.sign.h', '[data-testid="btn-sign"]', 48, 1)
        chkC('bar.sign.radius', '[data-testid="btn-sign"]', 'borderRadius', '12px')
        chkC('bar.sign.bg', '[data-testid="btn-sign"]', 'backgroundColor', 'rgb(37, 99, 235)')
        chkR('bar.signIcon.w', '[data-testid="btn-sign"] .icon-line--18', 20, 1) /* 字形 1ec3dab0 fs18 w20 */
        chkR('bar.signIcon.h', '[data-testid="btn-sign"] .icon-line--18', 27, 1)
        chkC('bar.signIcon.color', '.ic-send', 'borderLeftColor', 'rgb(255, 255, 255)')
        chk('bar.signText.pad', css('[data-testid="btn-sign"] .btn__text', 'paddingLeft'), 6) /* 容器 padding-left 6 */
        chkC('bar.signText.fs', '[data-testid="btn-sign"] .btn__text', 'fontSize', 15) /* 2f4816da fs15 SemiBold #FFFFFF */
        chkC('bar.signText.fw', '[data-testid="btn-sign"] .btn__text', 'fontWeight', 600)
        chkC('bar.signText.lh', '[data-testid="btn-sign"] .btn__text', 'lineHeight', 18, 0.5)
        chkC('bar.signText.color', '[data-testid="btn-sign"] .btn__text', 'color', 'rgb(255, 255, 255)')
        chkStrs('bar.signText.text', [textOf('[data-testid="btn-sign"]')], ['去签署'])

        /* 设计帧字面量登记（不照抄的项，逐条说明；同 D3 图例百分比口径） */
        var designLiteralDiff = [
          '合同编号「CT-2024-0613-008」与各字段值均来自服务端（本页 mock api-15/v1/contracts/c1 = 设计帧同值）→ 页面不硬编码',
          '状态胶囊「待签署」是 10-PRD §4.2 状态机（PENDING_SIGN）的中文派生标签（全 PRD 无中文标签）→ 由状态映射得到，不写死',
          'toast / 二次确认弹窗文案（「确认签署」「确认对当前合同发起签署？」「签署申请已提交」等）设计帧无稿 → 占位（missing-prd）',
          '签署记录 2 条的 tone(success/pending) 字段未定义 → 服务端优先、缺省 pending；点色 #16A34A / #F59E0B 由 tone 派生'
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
          nav: rect('.ct__nav'),
          navBack: rect('[data-testid="back"]'),
          navTitle: rect('[data-testid="nav-title"]'),
          navNo: rect('[data-testid="nav-no"]'),
          cards: rects(CARDS),
          statusCard: rect('[data-testid="card-status"]'),
          statusIcon: rect('.status__icon'),
          statusRow: rect('.status__row'),
          statusChip: rect('.status-chip'),
          statusTitle: rect('[data-testid="status-title"]'),
          deadline: rect('[data-testid="deadline"]'),
          tipCard: rect('[data-testid="tip-card"]'),
          tipText: rect('[data-testid="tip"]'),
          basicRows: rects('.card--basic .crow'),
          feeRows: rects('.card--fee .crow'),
          feeValueRight: rects('.card--fee .crow__value').map(function (r) { return r.right }),
          clauses: rects('.clause'),
          signRows: rects('.card--sign .crow'),
          records: rects('.record'),
          dots: rects('.record__dot'),
          barWrap: rect('.ct__bar-wrap'),
          bar: rect('.ct__bar'),
          pdfBtn: rect('[data-testid="btn-pdf"]'),
          signBtn: rect('[data-testid="btn-sign"]'),
          iconBoxes: {
            back: rect('.ct__nav .icon-line--24'),
            statusGlyph: rect('.status__icon .icon-line--24'),
            tip: rect('.card--tip .icon-line--18'),
            pdf: rect('[data-testid="btn-pdf"] .icon-line--18'),
            sign: rect('[data-testid="btn-sign"] .icon-line--18')
          },
          texts: {
            navTitle: textOf('[data-testid="nav-title"]'),
            navNo: textOf('[data-testid="nav-no"]'),
            statusTitle: textOf('[data-testid="status-title"]'),
            statusChip: textOf('[data-testid="status-chip"]'),
            deadline: textOf('[data-testid="deadline"]'),
            tip: textOf('[data-testid="tip"]'),
            basicLabels: texts('.card--basic .crow__label'),
            basicValues: texts('.card--basic .crow__value'),
            feeLabels: texts('.card--fee .crow__label'),
            feeValues: texts('.card--fee .crow__value'),
            clauseTexts: texts('.clause__text'),
            signLabels: texts('.card--sign .crow__label'),
            signValues: texts('.card--sign .crow__value'),
            recTitles: texts('.record__title'),
            recTimes: texts('.record__time'),
            pdf: textOf('[data-testid="btn-pdf"]'),
            sign: textOf('[data-testid="btn-sign"]')
          },
          counts: {
            cards: doc.querySelectorAll(CARDS).length,
            clauses: doc.querySelectorAll('.clause').length,
            records: doc.querySelectorAll('.record').length,
            inputs: doc.querySelectorAll('input,textarea').length
          },
          userAgent: win.navigator.userAgent
        }
      }

"""

MAIN = r"""      async function main() {
        try {
          await waitFor('[data-testid="card-records"]')
          await sleep(1400)
          phase(1)
          if (NO_ACTION || !SCENARIO) return

          /* ?scenario=pdf：下载 PDF —— 页面先 GET /contracts/{id}/file 取地址，再走 uni.downloadFile
             （uni-app H5 把 uni API 以模块绑定内联 → 打桩 window.uni 无效，只能让 mock 返回可达 URL，
             用 serve 访问日志作「真的下载了」的硬证据；同序号 15 建页轮口径）。 */
          if (SCENARIO === 'pdf') {
            var w = f.contentWindow
            var apiProbe = {
              windowUniDownloadFile: typeof (w.uni && w.uni.downloadFile),
              windowUniOpenDocument: typeof (w.uni && w.uni.openDocument)
            }
            var cPdf = clickIn('[data-testid="btn-pdf"]')
            await sleep(2500)
            sink(2, {
              scenario: SCENARIO, clicked: cPdf, apiProbe: apiProbe,
              toast: toastText(f.contentDocument), hash: hashNow()
            })
            return
          }

          /* ?scenario=sign：去签署 → uni-modal 二次确认 → POST /contracts/{id}/sign → toast → 重新取数 */
          if (SCENARIO === 'sign') {
            var cSign = clickIn('[data-testid="btn-sign"]')
            await sleep(600)
            var docS = f.contentDocument
            var modal = docS.querySelector('uni-modal, .uni-modal')
            var modalText = modal ? modal.textContent.replace(/\s+/g, ' ').trim() : ''
            var confirmBtn = docS.querySelector('.uni-modal__btn_primary, .uni-modal__btn:last-child')
            var confirmed = 'NO_CONFIRM_BTN'
            if (confirmBtn) {
              var ev2 = docS.createEvent('MouseEvents')
              ev2.initMouseEvent('click', true, true, f.contentWindow, 0, 0, 0, 0, 0, false, false, false, false, 0, null)
              confirmBtn.dispatchEvent(ev2)
              confirmed = 'CONFIRMED'
            }
            await sleep(700)
            var toastAfter = toastText(docS)
            await sleep(1200)
            sink(2, {
              scenario: SCENARIO, clicked: cSign, confirmed: confirmed, modalText: modalText,
              toast: toastAfter, hash: hashNow(),
              statusChip: textIn('[data-testid="status-chip"]')
            })
            return
          }

          /* ?scenario=back：返回 = navigateBack（本页是栈内页面，落地页由栈决定 → 断言 hash 不变 + 无请求） */
          if (SCENARIO === 'back') {
            var cBack = clickIn('[data-testid="back"]')
            await sleep(1200)
            sink(2, { scenario: SCENARIO, clicked: cBack, hash: hashNow() })
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
