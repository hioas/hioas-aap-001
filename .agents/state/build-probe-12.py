"""Build __measure-quote-preview.html (序号 12 · page-12-2) as a 430-wide iframe probe with
design-expectation checks (chk/chkR/chkC/chkList/chkStrs).

做法与 build-probe-11.py 同：从 __measure-model-pricing.html 切出三段「与页面无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计），逐字节复用，保证全仓库只有一个实现；
本文件只写 page-12-2 自己的 checks / return / phases。

want 两类来源：
  (a) 声明值 .calicat/raw/pages/page-12-2/{design.json,design.tree.json}
      python .agents/state/tree-view.py page-12-2 --types all      # 几何/内边距/圆角/stroke/effects
      python .agents/state/text-lineheight.py page-12-2            # 文本叶子 fontSize/lineHeight/宽高/字色
  (b) 设计截图 PNG 实测（430×1027）：.agents/state/design-shots/page-12-2-design.png
      python .agents/state/stroke-rows.py <png> eef2f7 6 150      # 卡片上下描边所在行（卡边界）
      python .agents/state/png-colorat.py <png> v 100 f8fafc 3 2  # 规则行 / 页面底（#F8FAFC）色带
      python .agents/state/png-colorat.py <png> h 880 fffbeb 4 2  # 提示条横向边界
      python .agents/state/png-textbands.py <png> 46 217 384 261  # 盒内文字带（行数/行位）
      python .agents/state/png-xruns.py <png> <y> 36 394          # 某行墨迹 x 区间
      python .agents/state/png-profile.py <png> 70 217 394 261    # 逐行墨迹（判文字行数）

设计骨架（PNG 实测 · 设计帧高 1027）：
  顶部导航 0..96 · 内容区 padding-top 12 → 卡1 108..380(273) · 卡2 392..612(221) · 卡3 624..788(165) ·
  确认卡 800..926(127) · 底栏容器 padding-top 16 → 操作条 943..1027(84)
  卡内模型（与 design.json 声明自洽）：
    · 头行 26（标签胶囊 h20 居中 → 128..154）· 头行图标盒 20 宽
    · 基础价行 = 标签 16 + 值 22 = 38（设计显式 height 16/22）· wrapper padding-top 12
    · 规则行 = padding 10 + 内容 + 10；「峰谷行/阶梯行」内容 24（图标 18×24）→ 44；
      「请求规则行」内容 20（该图标图层 width=fit_content）→ **40**（PNG 实测 321..360 / 553..592 / 729..768）
    · 首个规则块 wrapper padding-top 12、其后 8（卡3 只有 1 条 → 8）
    · 确认行 19（= fs12 文本行框 19.2 取整）· 提示条 56 = 10 + 2×18 + 10（文本 11px 两行）
  卡片投影/描边（design 声明逐卡不同，不静默统一）：
    · 卡1 effects drop_shadow(0,6,20,rgba(15,23,42,0.06)) → box-shadow，**无描边**
    · 卡2/卡3/确认卡 stroke{align:center,thickness:1,#EEF2F7} → box-shadow 0 0 0 1px，**无投影**
      （PNG 佐证：卡1 下方 381..391 有投影染色、卡2/卡3/确认卡下方是纯页面底色；x=16 处
        卡1 行内无描边像素、卡2/3/确认卡有）
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-model-pricing.html")
DST = os.path.join(HM, "__measure-quote-preview.html")

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
i_checks = find("/* ===================== 整页 ===================== */")

top = "\n".join(src[i_var:i_collect])
top = top.replace("if (SHOT_ONLY) f.style.height = '1541px'", "if (SHOT_ONLY) f.style.height = '1027px'")
preamble = "\n".join(src[i_collect:i_over])          # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])           # over / missing 统计（引用 NEED_TEXT）

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-quote-preview</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      iframe { width: 430px; height: 900px; border: 0; }
      /* 取数用 <pre> 包在 0 尺寸 overflow:hidden 容器：textContent 可读，但不参与渲染、也不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜
         序号 12：/pages/quote-preview/index?quoteId=q7（【报价管理】报价预览与提交 2，page-12-2 ·
         帧名「12. 报价端·小程序 ｜ 【报价管理】报价预览与提交 2」· layer_id 55b40659-f198-4a04-b36b-ce699c55c75d）
         设计帧重抓 2026-09-16 13:3x：design.json sha256 20f0f362…，与实现所依据的一份**逐字节相同**
           （cmp 报 BYTE-IDENTICAL）（无漂移）
         phase1（首屏：GET /api/v1/quotes/q7）→ **设计期望值 checks 全量**
         ?scenario=actions → phase2（「返回编辑」= navigateBack hash 不变 + 取消勾选后「提交报价」被门禁拦住、
           零写请求）· phase3（重新勾选 → 「提交报价」→ 真实 POST /api/v1/quotes/q7/submit → toast + 跳报价单列表）
         无 scenario/?noaction=1 → 只跑 phase1（纯测量轮，serve 实收只有只读 GET）· ?shot=1 iframe 高 = 设计帧高 1027 -->
    <iframe id="f" src="/index.html#/pages/quote-preview/index?quoteId=q7"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

BODY = r"""
        var CARDS = '.card'
        /* 本页要断言文本字色（前导 helpers 里只有 backgroundColor 版 colors）——与 __measure-profile.html 同实现 */
        function textColors(sel) {
          return resolveAll(sel).map(function (e) { return normColor(win.getComputedStyle(e).color) })
        }
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 design.tree.json） */
        var NEED_TEXT = [
          '报价预览',
          'gpt-4o-mini', '时段价 + 阶梯价', '输入', '¥1.2', '输出', '¥3.6', '缓存读', '¥0.6',
          '高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍',
          '3 档阶梯：0–100万 / 100–500万 / 500万以上',
          '请求规则计费：命中条件时按倍率计费，多条命中相乘',
          'claude-3-5-sonnet', '阶梯价', '¥2.0', '¥8.0', '¥0.2',
          '3 档阶梯已启用，末档覆盖至不限量',
          'gpt-4o', '仅基础价', '¥4.0', '¥12.0', '缓存写', '¥5.0',
          '我确认以上价格真实有效，并同意《报价服务条款》',
          '提交后进入运营审核，审核通过将自动编译计费表达式并同步渠道。',
          '返回编辑', '提交报价'
        ]
__OVERFLOW__

        /* ===================== 整页（设计帧 430×1027） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.docHeight', docH, 1027, 2)
        chkC('page.bg', '.preview', 'backgroundColor', 'rgb(248, 250, 252)') /* design 440d67a6 fills rgba(248,250,252,1) */
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 4)
        /* PNG 实测：卡1 108..380 · 卡2 392..612（描边行）· 卡3 624..788 · 确认卡 800..926 */
        chkList('page.cardTops', rects(CARDS).map(function (r) { return r.top }), [108, 392, 624, 800], 2)
        chkList('page.cardHeights', rects(CARDS).map(function (r) { return r.h }), [273, 221, 165, 127], 2)
        chkList('page.cardX', rects(CARDS).map(function (r) { return r.x }), [16, 16, 16, 16], 1)
        chkList('page.cardW', rects(CARDS).map(function (r) { return r.w }), [398, 398, 398, 398], 1)
        chkC('page.cardRadius', '.card@@0', 'borderRadius', '16px')
        chkC('page.cardBg', '.card@@0', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('page.cardPad', '.card@@0', 'padding', '20px')
        /* 卡1 只有 effects 投影（设计 39fed800，未声明 stroke）；卡2/3/确认卡只有 1px 中心描边 */
        chkC('page.card1.shadow', '.card@@0', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 6px 20px 0px')
        chkC('page.card2.shadow', '.card@@1', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkC('page.card3.shadow', '.card@@2', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkC('page.card4.shadow', '.card@@3', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')

        /* ===================== 顶部导航（design d02dab76 padding[48,16,12,16]） ===================== */
        chkR('nav.h', '.preview__nav', 96, 1) /* 48 + 36（图标字形行框 24×1.5）+ 12 */
        chkC('nav.pad', '.preview__nav', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.preview__nav', 'backgroundColor', 'rgb(255, 255, 255)')
        /* 返回图标 图层 c8e47792 w=26 fs=24 → 盒 26×36 */
        chkR('nav.back.x', '.nav__back', 16, 1)
        chkR('nav.back.top', '.nav__back', 48, 1)
        chkR('nav.back.w', '.nav__back', 26, 1)
        chkR('nav.back.h', '.nav__back', 36, 1)
        /* 标题块 container 9d190551 padding-left 12；标题 图层 0b28f444 fs=17 Bold */
        chkC('nav.titles.padLeft', '.nav__title-wrap', 'paddingLeft', 12)
        chkR('nav.title.x', '.nav__title', 54, 1) /* 16 + 26 + 12 */
        chkC('nav.title.fs', '.nav__title', 'fontSize', 17)
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700)
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('.nav__title')], ['报价预览'])

        /* ===================== 模型头行（design 73e3529b / 858f859f / 58268dc8） ===================== */
        chkList('head.h', rects('.card__head').map(function (r) { return r.h }), [26, 26, 26], 1)
        chkR('head.icon.w', '.ic-model@@0', 20, 1) /* 头行图标 图层 9e9b1167 w=20 fs=18 */
        chkR('head.icon.h', '.ic-model@@0', 26, 1)
        chkC('head.nameWrap.padLeft', '.head__name-wrap@@0', 'paddingLeft', 6)
        chkC('head.name.fs', '.head__name@@0', 'fontSize', 14)
        chkC('head.name.fw', '.head__name@@0', 'fontWeight', 600)
        chkC('head.name.color', '.head__name@@0', 'color', 'rgb(15, 23, 42)')
        chkStrs('head.names', texts('.head__name'), ['gpt-4o-mini', 'claude-3-5-sonnet', 'gpt-4o'])
        /* 标签胶囊（design h=20 padding[0,8,0,8] r=10） */
        chkList('tag.h', rects('.tag').map(function (r) { return r.h }), [20, 20, 20], 1)
        chkList('tag.right', rects('.tag').map(function (r) { return r.right }), [394, 394, 394], 1)
        chkC('tag.pad', '.tag@@0', 'padding', '0px 8px')
        chkC('tag.radius', '.tag@@0', 'borderRadius', '10px')
        chkList('tag.bgs', colors('.tag'), ['rgb(239, 246, 255)', 'rgb(236, 253, 245)', 'rgb(241, 245, 249)'])
        chkStrs('tag.texts', texts('.tag'), ['时段价 + 阶梯价', '阶梯价', '仅基础价'])
        chkC('tag.text.fs', '.tag__text@@0', 'fontSize', 10)
        chkC('tag.text.fw', '.tag__text@@0', 'fontWeight', 500)
        chkList('tag.text.colors', textColors('.tag__text'), ['rgb(37, 99, 235)', 'rgb(21, 128, 61)', 'rgb(100, 116, 139)'])

        /* ===================== 基础价行（design 1f36434b padding-top 12 + 基础行） ===================== */
        chkC('price.block.padTop', '.card__block--first@@0', 'paddingTop', 12)
        chkList('price.row.h', rects('.prices').map(function (r) { return r.h }), [38, 38, 38], 1) /* 标签 16 + 值 22 */
        chkList('price.label.h', rects('.prices__label').map(function (r) { return r.h }), [16, 16, 16, 16, 16, 16, 16, 16, 16], 1)
        chkC('price.label.fs', '.prices__label@@0', 'fontSize', 10)
        chkC('price.label.fw', '.prices__label@@0', 'fontWeight', 400)
        chkC('price.label.color', '.prices__label@@0', 'color', 'rgb(148, 163, 184)')
        chkC('price.label.lh', '.prices__label@@0', 'lineHeight', 16)
        chkList('price.value.h', rects('.prices__value').map(function (r) { return r.h }), [22, 22, 22, 22, 22, 22, 22, 22, 22], 1)
        chkC('price.value.fs', '.prices__value@@0', 'fontSize', 14)
        chkC('price.value.fw', '.prices__value@@0', 'fontWeight', 700)
        chkC('price.value.color', '.prices__value@@0', 'color', 'rgb(15, 23, 42)')
        chkC('price.value.lh', '.prices__value@@0', 'lineHeight', 22)
        chkStrs('price.labels', texts('.prices__label'),
          ['输入', '输出', '缓存读', '输入', '输出', '缓存读', '输入', '输出', '缓存写'])
        chkStrs('price.values', texts('.prices__value'),
          ['¥1.2', '¥3.6', '¥0.6', '¥2.0', '¥8.0', '¥0.2', '¥4.0', '¥12.0', '¥5.0'])
        chkR('price.spacer.w', '.prices__spacer@@0', 9, 1) /* design spacer w=9 */

        /* ===================== 规则行（design 峰谷行/阶梯行 h=44 · 请求规则行 h=40） ===================== */
        chkList('rule.h', rects('.rule').map(function (r) { return r.h }), [44, 44, 40, 44, 40, 40], 1)
        chkC('rule.pad', '.rule@@0', 'padding', '10px')
        chkC('rule.radius', '.rule@@0', 'borderRadius', '10px')
        chkC('rule.bg', '.rule@@0', 'backgroundColor', 'rgb(248, 250, 252)')
        chkList('rule.icon.h', rects('.rule .ic').map(function (r) { return r.h }), [24, 24, 20, 24, 20, 20], 1)
        chkList('rule.icon.w', rects('.rule .ic').map(function (r) { return r.w }), [18, 18, 18, 18, 18, 18], 1)
        chkList('rule.text.x', rects('.rule__text').map(function (r) { return r.x }), [70, 70, 70, 70, 70, 70], 1) /* 36+10+18+6 */
        chkC('rule.text.fs', '.rule__text@@0', 'fontSize', 11)
        chkC('rule.text.fw', '.rule__text@@0', 'fontWeight', 400)
        chkC('rule.text.color', '.rule__text@@0', 'color', 'rgb(71, 85, 105)')
        chkC('rule.text.lh', '.rule__text@@0', 'lineHeight', 18) /* 峰谷/阶梯行：设计文字带位于行顶 +13 → 行框 18 */
        chkC('rule.text.compactLh', '.rule--compact .rule__text@@0', 'lineHeight', 13.2) /* 请求规则行：设计文字带 +11 → 行框 13.2（声明 lineHeight 1.2） */
        chkStrs('rule.texts', texts('.rule__text'), [
          '高峰 09:00–12:00 / 18:00–22:00 上浮 1.2 倍，其余时段 0.85 倍',
          '3 档阶梯：0–100万 / 100–500万 / 500万以上',
          '请求规则计费：命中条件时按倍率计费，多条命中相乘',
          '3 档阶梯已启用，末档覆盖至不限量',
          '请求规则计费：命中条件时按倍率计费，多条命中相乘',
          '请求规则计费：命中条件时按倍率计费，多条命中相乘'
        ])
        /* 规则块 padding-top：首个规则块 12、其后 8（design 逐卡如此，卡3 只有 1 条 → 8） */
        chkList('rule.block.padTops', [css('.card__block--first@@0', 'paddingTop'), css('.card__block--tight@@0', 'paddingTop')], [12, 8], 0)

        /* ===================== 确认提交卡（design 确认行 76d8affa + 提交后端提示 1053a012） ===================== */
        chkR('confirm.row.h', '.confirm', 19, 1) /* = fs12 文本行框 19.2（PNG 实测确认行 820..838） */
        chkR('confirm.check.x', '.check', 36, 1)
        chkR('confirm.check.w', '.check', 18, 1)
        chkR('confirm.check.h', '.check', 18, 1)
        chkC('confirm.check.radius', '.check', 'borderRadius', '6px')
        chkC('confirm.check.bg', '.check', 'backgroundColor', 'rgb(37, 99, 235)') /* 设计勾选框为蓝底白勾（默认已勾选）*/
        chk('confirm.tick.absent', !!byTestId('confirm-tick'), false) /* 占位：勾用 CSS 形状，不加设计外节点 */
        chkR('confirm.text.x', '.confirm__text', 62, 1) /* 36 + 18 + 8（container padding-left 8） */
        chkC('confirm.text.fs', '.confirm__text', 'fontSize', 12)
        chkC('confirm.text.fw', '.confirm__text', 'fontWeight', 400)
        chkC('confirm.text.color', '.confirm__text', 'color', 'rgb(71, 85, 105)')
        chkStrs('confirm.text', [textOf('.confirm__text')], ['我确认以上价格真实有效，并同意《报价服务条款》'])
        /* 提示条 56 = padding 10 + 2×18 + 10（design 1053a012 padding=10 r=10 fills#FFFBEB） */
        chkR('hint.x', '.hint', 36, 1)
        chkR('hint.w', '.hint', 358, 1)
        chkR('hint.h', '.hint', 56, 1)
        chkC('hint.pad', '.hint', 'padding', '10px')
        chkC('hint.radius', '.hint', 'borderRadius', '10px')
        chkC('hint.bg', '.hint', 'backgroundColor', 'rgb(255, 251, 235)')
        chkR('hint.icon.w', '.ic-hint', 17, 1) /* design c9d42967 w=17 fs=15 */
        chkR('hint.text.x', '.hint__text', 69, 1) /* 36 + 10 + 17 + 6 */
        chkC('hint.text.fs', '.hint__text', 'fontSize', 11)
        chkC('hint.text.color', '.hint__text', 'color', 'rgb(146, 64, 14)')
        chkC('hint.text.lh', '.hint__text', 'lineHeight', 18)
        chk('hint.textLines', Math.round(rect('.hint__text').h / 18), 2) /* 设计为两行（PNG 866..877 + 880..890） */
        chkStrs('hint.text', [textOf('.hint__text')], ['提交后进入运营审核，审核通过将自动编译计费表达式并同步渠道。'])

        /* ===================== 底部操作条（design 8e160a88 padding-top 16 + d7b75749） ===================== */
        chkC('bar.wrap.padTop', '.preview__bar-wrap', 'paddingTop', 16)
        chkR('bar.top', '.preview__bar', 943, 2) /* PNG 实测 943..1027 */
        chkR('bar.h', '.preview__bar', 84, 1)
        chkC('bar.pad', '.preview__bar', 'padding', '12px 16px 24px')
        chkC('bar.bg', '.preview__bar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkR('bar.ghost.x', '.bar__ghost', 16, 1)
        chkR('bar.ghost.w', '.bar__ghost', 156, 1) /* design 81fe5e38 w=156 h=48 */
        chkR('bar.ghost.h', '.bar__ghost', 48, 1)
        chkC('bar.ghost.radius', '.bar__ghost', 'borderRadius', '12px')
        chkC('bar.ghost.fs', '.bar__ghost', 'fontSize', 14)
        chkC('bar.ghost.fw', '.bar__ghost', 'fontWeight', 500)
        chkC('bar.ghost.color', '.bar__ghost', 'color', 'rgb(71, 85, 105)')
        chkStrs('bar.texts', [textOf('.bar__ghost'), textOf('.bar__main-text')], ['返回编辑', '提交报价'])
        chkR('bar.main.x', '.bar__main', 184, 1) /* 16 + 156 + 12 */
        chkR('bar.main.w', '.bar__main', 230, 1)
        chkR('bar.main.h', '.bar__main', 48, 1)
        chkC('bar.main.radius', '.bar__main', 'borderRadius', '12px')
        chkC('bar.main.bg', '.bar__main', 'backgroundColor', 'rgb(37, 99, 235)')
        chkR('bar.mainIcon.w', '.ic-send', 20, 1) /* design 8b1d07f9 w=20 fs=18 */
        chkC('bar.mainText.fs', '.bar__main-text', 'fontSize', 15)
        chkC('bar.mainText.fw', '.bar__main-text', 'fontWeight', 600)
        chkC('bar.mainText.color', '.bar__main-text', 'color', 'rgb(255, 255, 255)')
        chk('bar.tabbarAbsent', !!doc.querySelector('.tabbar'), false)
        chk('page.inputCount', doc.querySelectorAll('input,textarea').length, 0)

        function styles(sel) {
          var e = el(sel)
          if (!e) return null
          var cs = win.getComputedStyle(e)
          return {
            boxShadow: normShadow(cs.boxShadow),
            backgroundColor: normColor(cs.backgroundColor),
            padding: cs.padding
          }
        }

        return {
          checks: checks,
          checkCount: checks,
          checkFailCount: fails.length,
          checkFails: fails.slice(0, 400),
          overflowingCount: over.length,
          overflowing: over.slice(0, 10),
          missingTexts: missing,
          docScrollWidth: doc.documentElement.scrollWidth,
          docScrollHeight: docH,
          innerWidth: win.innerWidth,
          nav: rect('.preview__nav'),
          cards: rects(CARDS),
          cardStyles: [styles('.card@@0'), styles('.card@@1'), styles('.card@@2'), styles('.card@@3')],
          heads: rects('.card__head'),
          priceRows: rects('.prices'),
          rules: rects('.rule'),
          ruleIcons: rects('.rule .ic'),
          confirmRow: rect('.confirm'),
          check: rect('.check'),
          hint: rect('.hint'),
          bar: rect('.preview__bar'),
          ghost: rect('.bar__ghost'),
          main: rect('.bar__main'),
          texts: {
            navTitle: textOf('.nav__title'),
            names: texts('.head__name'),
            tags: texts('.tag'),
            labels: texts('.prices__label'),
            values: texts('.prices__value'),
            rules: texts('.rule__text'),
            confirm: textOf('.confirm__text'),
            hint: textOf('.hint__text'),
            ghost: textOf('.bar__ghost'),
            main: textOf('.bar__main-text')
          },
          userAgent: win.navigator.userAgent
        }
      }

      function sink(n, payload) {
        acc['phase' + n] = payload
        document.getElementById('m').textContent = 'MEASURE_JSON:' + JSON.stringify(acc)
      }

      function phase(n) {
        try {
          var payload = collect(f.contentDocument, f.contentWindow, n === 1)
          if (n === 1 && !SHOT_ONLY) {
            f.style.height = '900px' /* 保持取数高度：min-height:100vh 会把测量高度顶到 iframe 高 */
            acc.iframeHeightForShot = payload.docScrollHeight
          }
          sink(n, payload)
        } catch (e) {
          sink(n, { error: String(e && e.message) })
        }
      }

      function clickIn(sel) {
        var doc = f.contentDocument
        var el = doc.querySelector(sel)
        if (!el) return 'NOT_FOUND'
        var ev = doc.createEvent('MouseEvents')
        ev.initMouseEvent('click', true, true, f.contentWindow, 0, 0, 0, 0, 0, false, false, false, false, 0, null)
        el.dispatchEvent(ev)
        return 'CLICKED'
      }

      function toastText(doc) {
        var el = doc.querySelector('uni-toast .uni-toast__content, .uni-toast__content, uni-toast')
        return el ? el.textContent.trim() : ''
      }

      function hashNow() {
        try { return String(f.contentWindow.location.hash) } catch (e) { return 'ERR:' + e.message }
      }

      function checkAttr() {
        try {
          var e = f.contentDocument.querySelector('[data-testid="confirm-check"]')
          return e ? e.getAttribute('data-checked') : null
        } catch (err) { return 'ERR:' + err.message }
      }

      function waitFor(sel, maxTries) {
        return new Promise(function (resolve) {
          var n = 0
          function tick() {
            n++
            var ok = false
            try { ok = !!f.contentDocument.querySelector(sel) } catch (e) { ok = false }
            if (ok) return resolve('READY(tries=' + n + ')')
            if (n >= (maxTries || 40)) return resolve('TIMEOUT(tries=' + n + ')')
            setTimeout(tick, 200)
          }
          tick()
        })
      }

      function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms) }) }

      async function main() {
        try {
          await waitFor('[data-testid="model-name"]')
          await sleep(1400)
          phase(1)
          if (NO_ACTION || SCENARIO !== 'actions') return

          /* phase2：「返回编辑」（navigateBack 无栈 → hash 不变）+ 取消勾选后提交被门禁拦住（零写请求） */
          var backClick = clickIn('[data-testid="btn-back-edit"]')
          await sleep(700)
          var hashAfterBack = hashNow()
          var toggled = clickIn('[data-testid="confirm-check"]')
          await sleep(400)
          var attrAfterToggle = checkAttr()
          var submitBlocked = clickIn('[data-testid="btn-submit"]')
          await sleep(1400)
          sink(2, {
            clickedBack: backClick,
            hashAfterBack: hashAfterBack,
            clickedCheck: toggled,
            checkAttrAfterToggle: attrAfterToggle,
            clickedSubmit: submitBlocked,
            toastAfterBlockedSubmit: toastText(f.contentDocument),
            hashAfterBlockedSubmit: hashNow()
          })

          /* phase3：重新勾选 → 提交 → 真实 POST /api/v1/quotes/q7/submit → toast + 跳报价单列表
             toast 必须在跳转前采样（1.5s 后会被 uni 自动收起；列表页自己的取数也会 toast） */
          clickIn('[data-testid="confirm-check"]')
          await sleep(400)
          var attrBeforeSubmit = checkAttr()
          var submitClick = clickIn('[data-testid="btn-submit"]')
          await sleep(900)
          var toastAfterSubmit = toastText(f.contentDocument)
          await sleep(1300)
          sink(3, {
            checkAttrBeforeSubmit: attrBeforeSubmit,
            clickedSubmit: submitClick,
            toastAfterSubmit: toastAfterSubmit,
            hashAfterSubmit: hashNow(),
            listRendered: !!f.contentDocument.querySelector('[data-testid="new-quote"]')
          })
        } catch (e) {
          sink('error', { message: String(e && e.message), stack: String((e && e.stack) || '').slice(0, 600) })
        }
      }

      main()
"""

TAIL = """    </script>
  </body>
</html>
"""

body = BODY.replace("__OVERFLOW__", overflow)

with io.open(DST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(HEAD + top + preamble + body + TAIL)
print("wrote", DST)
print("top lines:", len(top.split("\n")), "preamble lines:", len(preamble.split("\n")), "overflow lines:", len(overflow.split("\n")))
