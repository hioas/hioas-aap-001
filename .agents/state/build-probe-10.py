"""Build __measure-profile-edit.html (序号 10 · page-10-2) from the 序号 9 probe idiom.

head/helpers/tail are lifted verbatim from __measure-quote-setup.html so the two probes
share exactly one implementation of chk()/rect()/declared()/splitSel().
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-quote-setup.html")
DST = os.path.join(HM, "__measure-profile-edit.html")

with io.open(SRC, encoding="utf-8") as fh:
    src = fh.read().split("\n")


def find(needle, start=0):
    for i in range(start, len(src)):
        if needle in src[i]:
            return i
    raise SystemExit("not found: " + needle)


i_var = find("var f = document.getElementById('f')")
i_helpers_end = find("var CARDS = '.card'")
i_tail_start = find("function sink(n, payload)")
i_load = find("f.addEventListener('load'")
i_end = find("</script>")

helpers = "\n".join(src[i_var:i_helpers_end])
helpers = helpers.replace("f.style.height = '1211px'", "f.style.height = '1409px'")  # 本页设计帧高 1409
tail = "\n".join(src[i_tail_start:i_load])
# 本页 checks 跑在 phase1（设计稿态），不是 phase2
tail = tail.replace("n === 2)", "n === 1)")

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-profile-edit</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      iframe { width: 430px; height: 900px; border: 0; }
      /* 取数用 <pre> 包在 0 尺寸 overflow:hidden 容器：textContent 可读，但不参与渲染、也不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜
         序号 10：/pages/profile-edit/index（【档案与凭证】供应商档案编辑 2，page-10-2 · 帧 layer_id 45f4d7f9-17d7-4f24-b0d0-af81807d0f18）
         设计帧重抓 2026-09-16 12:3x：design.json sha256 46e9cfee… 与实现所依据的一份**逐字节相同**（无漂移）
         phase1（首次加载：GET profile + GET qualifications = 设计稿态 → 设计期望值 checks）
         phase2（类型 chip 原厂→渠道商 切换 + 简介输入 = 真实 DOM 事件；见 ?scenario=actions）
         phase3（清空企业名称 → 点保存被校验拦截 → 点保存草稿写本地草稿）
         phase4（恢复企业名称 → 点保存真实 PUT → 删资质行 uni-modal 二次确认 → DELETE → 重拉列表）
         ?scenario=guard → 只跑 phase3（校验门：serve 实收必须 0 行写请求）
         ?shot=1 → iframe 高度 = 设计帧高 1409（截图用）
         设计期望值（want）两类来源：
           (a) 声明值：.calicat/raw/pages/page-10-2/design.json（+ design.tree.json）
               python .agents/state/tree-view.py page-10-2                    几何/内边距/圆角/stroke/effects
               python .agents/state/text-fields.py page-10-2                  全部文本叶子的 fontSize/字重/fontFill/宽高
               python .agents/state/show-node-json.py .calicat/raw/pages/page-10-2/design.json <节点名>
           (b) 盒子的真实边界/行框：设计截图 PNG 实测（430×1409）
               PNG: https://prototype-prod-1254106194.cos.ap-beijing.myqcloud.com/calicat/file/2099929070227210240/canvas/image/2099929070227210240.png
               （已存在 .agents/state/design-shots/page-10-2.png）复现命令（仓库根）：
                 python .agents/state/png-rowclass.py .agents/state/design-shots/page-10-2.png --x0 16 --x1 414
                 python .agents/state/png-textbands.py .agents/state/design-shots/page-10-2.png 20 108 410 700 --minink 3
                 python .agents/state/png-xruns.py .agents/state/design-shots/page-10-2.png 388 30 300
               实测骨架（设计帧高 1409 = 顶部导航 96 + 卡1 579 + 12 + 卡2 345 + 12 + 卡3 253 + 16 间隔 + 底栏 84）：
                 顶部导航 0..95（内容行 48..84：返回图标 26×36 @16 · 标题 编辑主体档案 @54 · 完整度胶囊 40×24 @374）
                 卡1 主体信息 108..686(579)：头部行 27（图标 20×27 @36 + 6 + 标题 14/600 @62）
                   字段 6 组：标签 18 @171/257/343/429/515/601 · 框 44 @197/283/369(类型行 40)/455/541/627
                 卡2 联系信息 699..1043(345)：头部行 27 · 两列行（列宽 172.5 gap 13）· 简介行（标签 18 + 框 64）
                 卡3 资质文件 1056..1308(253)：头部行 27（含右对齐说明 148 宽）· 资质行 46 @1119/1181/1243（行间距 16）
                 底栏 1325..1408(84)：padding 12/16/24/16 · 草稿 156×48 @16 · 保存 230×48 @184
               关键模型（本页定标）：
                 · remixicon 字形行框 = fontSize × 1.5（24→36 顶部栏 · 18→27 卡头 · 11→16.5 已上传勾）
                 · 文本行框：设计显式 height 优先（标签 18 · 文件名/提示 16 · 简介文本 40）；否则按渲染居中，不单独断言
                 · Figma center 描边 → box-shadow 0 0 0 1px（border 会占布局：框内容左界会从 12 变 13）
                 · 设计「简介 48/200」与设计自身简介文案（40 字）矛盾 → 设计稿静态假数据，实现按真实字数（40/200），
                   探针断言「格式 + 与输入长度一致」，设计字面量登记为 designLiteralDiff -->
    <iframe id="f" src="/index.html#/pages/profile-edit/index"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
      /* quote-setup 的帮手块里没有顶层 all()（它内部用 doc.querySelectorAll + map.call）→ 本页补齐 */
      function all(doc, sel) { return Array.prototype.slice.call(doc.querySelectorAll(sel)) }
"""

CHECKS = r"""        /* ===================== 整页（设计帧 430×1409） ===================== */
        chk('page.docHeight', Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight), 1409, 2)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chkC('page.bg', '.profile-edit', 'backgroundColor', 'rgb(248, 250, 252)')
        chk('page.cardCount', doc.querySelectorAll('.card').length, 3)
        chk('page.tabbarAbsent', !!doc.querySelector('.tabbar'), false)
        /* 设计帧 PNG 实测（x 16..414 逐行主色）：卡1 108..686 · 卡2 699..1043 · 卡3 1056..1308 */
        chkList('page.cardTops', rects('.card').map(function (r) { return r.top }), [108, 699, 1056], 2)
        chkList('page.cardHeights', rects('.card').map(function (r) { return r.h }), [579, 345, 253], 2)
        chkList('page.cardX', rects('.card').map(function (r) { return r.x }), [16, 16, 16], 1)
        chkList('page.cardW', rects('.card').map(function (r) { return r.w }), [398, 398, 398], 1)
        chkC('page.cardPadTop', '.card', 'paddingTop', 20)
        chkC('page.cardPadLeft', '.card', 'paddingLeft', 20)
        chkC('page.cardRadius', '.card', 'borderRadius', 18)
        chkC('page.cardBg', '.card', 'backgroundColor', 'rgb(255, 255, 255)')
        /* design c2a309c7 stroke{align:center,thickness:1,rgba(238,242,247,1)} → 中心描边不占布局 → ring */
        chk('page.cardRing', css('.card', 'boxShadow'), 'rgb(238, 242, 247) 0px 0px 0px 1px')

        /* ===================== 顶部导航（design 553188bc padding[48,16,12,16]） ===================== */
        chkR('nav.h', '.topbar', 96, 1)
        chkC('nav.padTop', '.topbar', 'paddingTop', 48)
        chkC('nav.padRight', '.topbar', 'paddingRight', 16)
        chkC('nav.padBottom', '.topbar', 'paddingBottom', 12)
        chkC('nav.padLeft', '.topbar', 'paddingLeft', 16)
        chkC('nav.bg', '.topbar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkR('nav.row.h', '.topbar__row', 36, 1) /* 内容行 = 图标字形行框 24×1.5 */
        /* 返回图标（design 32e4345c：remixicon fs=24 w=26 → 26×36） */
        chkR('nav.back.x', '.icon-btn', 16, 1)
        chkR('nav.back.w', '.icon-btn', 26, 1)
        chkR('nav.back.h', '.icon-btn', 36, 1)
        chkR('nav.back.top', '.icon-btn', 48, 1)
        /* 标题块（design 373699bc padding-left 12；标题 2b414252 fs17 Bold fill rgba(15,23,42,1)，声明宽 120） */
        chkR('nav.titleWrap.x', '.topbar__title-wrap', 42, 1)
        chkC('nav.titleWrap.padLeft', '.topbar__title-wrap', 'paddingLeft', 12)
        chkR('nav.title.x', '.topbar__title', 54, 1)
        chkC('nav.title.fs', '.topbar__title', 'fontSize', 17)
        chkC('nav.title.fw', '.topbar__title', 'fontWeight', 700) /* SourceHanSans-Bold */
        chkC('nav.title.color', '.topbar__title', 'color', 'rgb(15, 23, 42)')
        chk('nav.titleText', textOf('.topbar__title'), '编辑主体档案')
        /* 完整度胶囊（design 80d78cb9：h24 r12 padding 0/8 fills #EFF6FF；文字 fs11 Medium #2563EB） */
        chkR('nav.chip.x', '.completeness', 374, 1)
        chkR('nav.chip.w', '.completeness', 40, 1)
        chkR('nav.chip.h', '.completeness', 24, 1)
        chkR('nav.chip.top', '.completeness', 54, 1)
        chkC('nav.chip.radius', '.completeness', 'borderRadius', 12)
        chkC('nav.chip.bg', '.completeness', 'backgroundColor', 'rgb(239, 246, 255)')
        chkC('nav.chip.padLeft', '.completeness', 'paddingLeft', 8)
        chkC('nav.chipText.fs', '.completeness__text', 'fontSize', 11)
        chkC('nav.chipText.fw', '.completeness__text', 'fontWeight', 500)
        chkC('nav.chipText.color', '.completeness__text', 'color', 'rgb(37, 99, 235)')
        chk('nav.chipText', textOf('.completeness'), '72%') /* mock completeness=72 */
        chk('nav.padTopCalc', css('.topbar', 'paddingTop') - rect('.icon-btn').top, 0, 1) /* H5 无状态栏 → 纯 48 */

        /* ===================== 卡头（design 2ea26a8a：图标 20×27 + container padding-left 6 + 标题） ===== */
        chkR('c1.head.h', '.card@@0 .card__head', 27, 1)
        chkR('c1.headIcon.x', '.card@@0 .glyph--basic', 36, 1)
        chkR('c1.headIcon.w', '.card@@0 .glyph--basic', 20, 1) /* design dd2e0031 fs=18 → 行框 27 */
        chkR('c1.headIcon.h', '.card@@0 .glyph--basic', 27, 1)
        chkR('c1.title.x', '.card@@0 .card__title', 62, 1)
        chkC('c1.title.fs', '.card@@0 .card__title', 'fontSize', 14)
        chkC('c1.title.fw', '.card@@0 .card__title', 'fontWeight', 600)
        chkC('c1.title.color', '.card@@0 .card__title', 'color', 'rgb(15, 23, 42)')
        chk('c1.titleText', textOf('.card@@0 .card__title'), '主体信息')

        /* ===================== 卡1 字段（design：标签 18 · 间距 8 · 框 44 → 字段间 16） ===================== */
        var C1BOX = ['.field@@0 .field__box', '.field@@1 .field__box', '.field@@2 .type-row',
                     '.field@@3 .field__box--half', '.field@@4 .field__box', '.field@@5 .field__box']
        var C1LBL = ['.field@@0 .field__label', '.field@@1 .field__label', '.field@@2 .field__label',
                     '.field@@3 .field__label', '.field@@4 .field__label', '.field@@5 .field__label']
        var RB = ['.field__box--half@@0', '.field__box--half@@1'] /* splitSel 只认第一个 @@ → 用全局序（本页只有地区这两个半栏框） */
        var C1TXT = ['.field@@0 .field__input', '.field@@1 .field__input', '.field@@4 .field__input', '.field@@5 .field__input']
        var RTXT = ['[data-testid="province-value"]', '[data-testid="city-value"]']
        chkList('c1.labelTops', selTop(C1LBL), [171, 257, 343, 425, 511, 597], 2)
        chkList('c1.labelHeights', selH(C1LBL), [18, 18, 18, 18, 18, 18], 1)
        chkList('c1.labelX', selX(C1LBL), [36, 36, 36, 36, 36, 36], 1)
        chkList('c1.labelFontSize', selCss(C1LBL, 'fontSize'), ['13px', '13px', '13px', '13px', '13px', '13px'])
        chkList('c1.labelFontWeight', selCss(C1LBL, 'fontWeight'), ['500', '500', '500', '500', '500', '500'])
        chkList('c1.labelColor', selCss(C1LBL, 'color'), ['rgb(51, 65, 85)', 'rgb(51, 65, 85)', 'rgb(51, 65, 85)', 'rgb(51, 65, 85)', 'rgb(51, 65, 85)', 'rgb(51, 65, 85)'])
        chkList('c1.labelTexts', selText(C1LBL), ['企业名称 *', '统一社会信用代码 *', '供应商类型 *', '所在地区 *', '详细地址 *', '官网'])
        /* 框位：设计 PNG 实测 196/282/368/450/536/622（框 ink 起于 1px 描边外沿 → 布局位 +0.5）
           批次 3 的类型行只有 40 高（不是 44）→ 该组步进 82，其后恢复 86 */
        chkList('c1.boxTops', selTop(C1BOX), [197, 283, 369, 451, 537, 623], 2)
        chkList('c1.boxX', selX(C1BOX), [36, 36, 36, 36, 36, 36], 1)
        chk('c1.box0.w', rect(C1BOX[0]).w, 358, 1)
        chk('c1.box0.inputW', rect(C1TXT[0]).w, 334, 1) /* 358 − padding 12×2（描边不占布局） */
        chkList('c1.boxHeights', selH(C1BOX), [44, 44, 40, 44, 44, 44], 1)
        chkList('c1.boxRadius', selCss(C1BOX, 'borderRadius'), ['12px', '12px', '12px', '12px', '12px', '12px'])
        chkList('c1.boxBg', selCss(C1BOX, 'backgroundColor'), ['rgb(248, 250, 252)', 'rgb(248, 250, 252)', 'rgba(0, 0, 0, 0)', 'rgb(248, 250, 252)', 'rgb(248, 250, 252)', 'rgb(248, 250, 252)'])
        /* 描边：design {align:center, thickness:1, #E2E8F0} → ring（border 占布局） */
        chkList('c1.boxRing', selCss(C1BOX, 'boxShadow'), [
          'rgb(226, 232, 240) 0px 0px 0px 1px', 'rgb(226, 232, 240) 0px 0px 0px 1px', 'none',
          'rgb(226, 232, 240) 0px 0px 0px 1px', 'rgb(226, 232, 240) 0px 0px 0px 1px', 'rgb(226, 232, 240) 0px 0px 0px 1px'])
        /* 框内内容左界 = 设计声明 padding 12（Figma 中心描边不占布局 → 容差 0） */
        chk('c1.box0.contentLeft', contentLeft(C1BOX[0], C1TXT[0]), 12, 0)
        chk('c1.box3.contentLeft', contentLeft(RB[0], '[data-testid="province-value"]'), 12, 0)
        /* 输入文字（design 5def1ebc 等：fs14 Medium fill rgba(51,65,85,1)） */
        var C1IN = C1TXT
        chkList('c1.inputFontSize', selCss(C1IN, 'fontSize'), ['14px', '14px', '14px', '14px'])
        chkList('c1.inputFontWeight', selCss(C1IN, 'fontWeight'), ['500', '500', '500', '500'])
        chkList('c1.inputColor', selCss(C1IN, 'color'), ['rgb(51, 65, 85)', 'rgb(51, 65, 85)', 'rgb(51, 65, 85)', 'rgb(51, 65, 85)'])
        chk('c1.usccOkBox', !!rect('[data-testid="uscc-ok"]'), true) /* 18 位 → 设计稿绿勾 */
        chk('c1.usccOk.w', rect('[data-testid="uscc-ok"]').w, 20, 1) /* 设计 9b1ba6ce：w=20 fs=18 → 20×27 */
        chk('c1.usccOk.h', rect('[data-testid="uscc-ok"]').h, 27, 1)
        chk('c1.usccOkColor', css('[data-testid="uscc-ok"]', 'color'), 'rgb(22, 163, 74)') /* 形状在 ::before，用 currentColor 承载 */
        chk('c1.headIcon.color', css('.glyph--basic', 'color'), 'rgb(37, 99, 235)')

        /* ===================== 供应商类型 chip（design 3ad6f172/b6855e24/97569b10） ===================== */
        var CHIP = '[data-testid="industry-chip"]@@0'
        var CHIPS = ['[data-testid="industry-chip"]@@0', '[data-testid="industry-chip"]@@1', '[data-testid="industry-chip"]@@2']
        chkList('chip.x', selX(CHIPS), [36, 104, 185], 2) /* PNG y=388 实测：36 / 104 / 185（间距 9） */
        chkList('chip.w', selW(CHIPS), [59, 72, 72], 2) /* 文字 27/40/40 + padding 16×2 */
        chkList('chip.h', selH(CHIPS), [40, 40, 40], 1)
        chkList('chip.radius', selCss(CHIPS, 'borderRadius'), ['12px', '12px', '12px'])
        chkList('chip.bg', selCss(CHIPS, 'backgroundColor'), ['rgb(255, 255, 255)', 'rgb(37, 99, 235)', 'rgb(255, 255, 255)'])
        chkList('chip.ring', selCss(CHIPS, 'boxShadow'), ['rgb(203, 213, 225) 0px 0px 0px 1px', 'rgb(37, 99, 235) 0px 0px 0px 1px', 'rgb(203, 213, 225) 0px 0px 0px 1px'])
        chkList('chip.texts', selText(CHIPS), ['原厂', '渠道商', '中转商'])
        var CHIPTXT = CHIPS.map(function (s) { return s + ' .type-chip__text' })
        chkList('chip.textFontSize', selCss(CHIPTXT, 'fontSize'), ['13px', '13px', '13px'])
        chkList('chip.textFontWeight', selCss(CHIPTXT, 'fontWeight'), ['500', '500', '500'])
        chkList('chip.textColor', selCss(CHIPTXT, 'color'), ['rgb(71, 85, 105)', 'rgb(255, 255, 255)', 'rgb(71, 85, 105)'])
        chkList('chip.checked', ['0', '1', '2'].map(function (i) { return all(doc, '[data-testid="industry-chip"]')[i].getAttribute('data-checked') }), ['false', 'true', 'false'])

        /* ===================== 所在地区（design 地区行：两个 fill_container 框 + 间距 13） ===================== */
        /* RB 已在「卡1 字段」段定义 */
        chkList('region.boxX', selX(RB), [36, 222], 2)
        chkList('region.boxW', selW(RB), [172, 172], 2)
        chkList('region.boxH', selH(RB), [44, 44], 1)
        chk('region.gap', hgap(RB[0], RB[1]), 13, 1)
        chkList('region.texts', selText(RB), ['浙江省', '杭州市'])
        chkList('region.textFontSize', selCss(RTXT, 'fontSize'), ['14px', '14px'])
        chkList('region.textFontWeight', selCss(RTXT, 'fontWeight'), ['500', '500'])
        chkList('region.textColor', selCss(RTXT, 'color'), ['rgb(51, 65, 85)', 'rgb(51, 65, 85)'])
        chkList('region.textX', selX(RTXT), [48, 234], 1) /* 框内 padding 12 */
        /* 地区框尾部 chevron（design fbc191db/1556519d：fs18 → 盒 20×27，右贴框内边） */
        chkList('region.chevronW', selW(RB.map(function (s) { return s + ' .glyph--chevron' })), [20, 20], 1)
        chkList('region.chevronH', selH(RB.map(function (s) { return s + ' .glyph--chevron' })), [27, 27], 1)
        chkList('region.chevronX', selX(RB.map(function (s) { return s + ' .glyph--chevron' })), [176, 362], 1)

        /* ===================== 卡2 联系信息（design 67023af5） ===================== */
        chkR('c2.head.h', '.card@@1 .card__head', 27, 1)
        chkR('c2.headIcon.w', '.card@@1 .glyph--contact', 20, 1)
        chkR('c2.headIcon.h', '.card@@1 .glyph--contact', 27, 1)
        chkR('c2.title.x', '.card@@1 .card__title', 62, 1)
        chk('c2.titleText', textOf('.card@@1 .card__title'), '联系信息')
        var C2LBL = ['.field@@6 .field__label', '.field@@7 .field__label', '.field@@8 .field__label', '.field@@9 .field__label', '.field@@10 .field__label']
        var C2BOX = ['.field@@6 .field__box', '.field@@7 .field__box', '.field@@8 .field__box', '.field@@9 .field__box', '.field@@10 .intro-box']
        chkList('c2.labelTops', selTop(C2LBL), [762, 762, 848, 848, 934], 2)
        chkList('c2.labelTexts', selText(C2LBL), ['联系人 *', '职务', '手机号 *', '邮箱', '公司简介'])
        chkList('c2.labelHeights', selH(C2LBL), [18, 18, 18, 18, 18], 1)
        chkList('c2.boxTops', selTop(C2BOX), [788, 788, 874, 874, 960], 2)
        chkList('c2.boxHeights', selH(C2BOX), [44, 44, 44, 44, 64], 1)
        chkList('c2.boxX', selX(C2BOX), [36, 222, 36, 222, 36], 2)
        chkList('c2.boxW', selW(C2BOX), [172, 172, 172, 172, 358], 2)
        chk('c2.colGap', hgap(C2BOX[0], C2BOX[1]), 13, 1)
        chk('c2.intro.pad', css('.intro-box', 'paddingTop'), 12)
        chk('c2.intro.radius', css('.intro-box', 'borderRadius'), '12px')
        chk('c2.intro.ring', css('.intro-box', 'boxShadow'), 'rgb(226, 232, 240) 0px 0px 0px 1px')
        chk('c2.introText.h', rect('.intro-box__textarea').h, 40, 1) /* design 740eca60 显式 height 40 */
        chk('c2.introText.fs', css('.intro-box__textarea', 'fontSize'), '13px')
        chk('c2.introText.color', css('.intro-box__textarea', 'color'), 'rgb(71, 85, 105)')
        /* 简介计数（design 4b1f129a 公司简介 fs13 Medium + 2b52ecde 计数 fs11 fill rgba(148,163,184,1)）
           ⚠️ 设计字面量「48/200」与同帧简介文案 40 字矛盾（designLiteralDiff）→ 断「格式 + 与输入长度一致」 */
        chk('c2.counter.fontSize', css('.field__counter', 'fontSize'), '11px')
        chk('c2.counter.color', css('.field__counter', 'color'), 'rgb(148, 163, 184)')
        chk('c2.counter.matchesInput', textOf('.field__counter'), String(String(inputValue('intro-input') || '').length) + '/200')
        chk('c2.counter.is40', textOf('.field__counter'), '40/200')
        chk('c2.labelRow.h', rect('.field__label-row').h, 18, 1)

        /* ===================== 卡3 资质文件（design 85da8ac1） ===================== */
        chkR('c3.head.h', '.card@@2 .card__head', 27, 1)
        chkR('c3.headIcon.w', '.card@@2 .glyph--files', 20, 1)
        chkR('c3.headIcon.h', '.card@@2 .glyph--files', 27, 1)
        chkR('c3.title.x', '.card@@2 .card__title', 62, 1)
        chk('c3.titleText', textOf('.card@@2 .card__title'), '资质文件')
        /* 说明文案（design 555a4423 fs11 Regular fill rgba(148,163,184,1)，w=148 → 右对齐到 394） */
        chk('c3.tip.text', textOf('.card__tip'), '支持 JPG/PNG/PDF，≤10MB')
        chk('c3.tip.fontSize', css('.card__tip', 'fontSize'), '11px')
        chk('c3.tip.fontWeight', css('.card__tip', 'fontWeight'), 400)
        chk('c3.tip.color', css('.card__tip', 'color'), 'rgb(148, 163, 184)')
        chkR('c3.tip.right', '.card__tip', 394, 1)
        var ROWS = ['[data-testid="qual-row"]@@0', '[data-testid="qual-row"]@@1', '[data-testid="qual-row"]@@2']
        chkList('c3.rowTops', selTop(ROWS), [1119, 1181, 1243], 2) /* 行高 46 + 行间距 16 */
        chkList('c3.rowHeights', selH(ROWS), [46, 46, 46], 1)
        chkList('c3.rowGaps', [gapBetween(ROWS[0], ROWS[1]), gapBetween(ROWS[1], ROWS[2])], [16, 16], 1)
        chkList('c3.thumbX', selX(ROWS.map(function (s) { return s + ' .qual-row__thumb' })), [36, 36, 36], 1)
        chkList('c3.thumbTop', selTop(ROWS.map(function (s) { return s + ' .qual-row__thumb' })), [1119, 1181, 1243], 1)
        chkList('c3.thumbW', selW(ROWS.map(function (s) { return s + ' .qual-row__thumb' })), [47, 46, 46], 1)
        chkList('c3.thumbH', selH(ROWS.map(function (s) { return s + ' .qual-row__thumb' })), [46, 46, 46], 1)
        chkList('c3.thumbRadius', selCss(ROWS.map(function (s) { return s + ' .qual-row__thumb' }), 'borderRadius'), ['10px', '10px', '10px'])
        chk('c3.thumb0.bg', css(ROWS[0] + ' .qual-row__thumb', 'backgroundColor'), 'rgb(239, 246, 255)') /* 90a08674 #EFF6FF */
        chkList('c3.thumbEmpty.bg', [css(ROWS[1] + ' .qual-row__thumb', 'backgroundColor'), css(ROWS[2] + ' .qual-row__thumb', 'backgroundColor')], ['rgb(248, 250, 252)', 'rgb(248, 250, 252)'])
        chkList('c3.thumbEmpty.ring', [css('.qual-row__thumb--empty', 'boxShadow'), css('.qual-row__thumb--empty@@1', 'boxShadow')], ['rgb(203, 213, 225) 0px 0px 0px 1px', 'rgb(203, 213, 225) 0px 0px 0px 1px'])
        chkList('c3.nameTexts', selText(ROWS.map(function (s) { return s + ' .qual-row__name' })), ['营业执照', '上游授权书', '其他选传资质'])
        chkList('c3.nameFontSize', selCss(ROWS.map(function (s) { return s + ' .qual-row__name' }), 'fontSize'), ['13px', '13px', '13px'])
        chkList('c3.nameFontWeight', selCss(ROWS.map(function (s) { return s + ' .qual-row__name' }), 'fontWeight'), ['600', '600', '600'])
        chkList('c3.nameColor', selCss(ROWS.map(function (s) { return s + ' .qual-row__name' }), 'color'), ['rgb(15, 23, 42)', 'rgb(15, 23, 42)', 'rgb(15, 23, 42)'])
        chkList('c3.nameRowH', selH(ROWS.map(function (s) { return s + ' .qual-row__name-row' })), [18, 18, 18], 1)
        /* 角标：design 必传标(37=8+21+8) · 已上传标(62=8+勾13+2+文31+8) · 条件必传标(57=8+41+8)，h18 r9 */
        var D2F = 'borderBottomColor'
        chk('c3.badgeRequired.w', rect(ROWS[0] + ' .qual-row__badge--required').w, 37, 3)
        chk('c3.badgeRequired.right', rect(ROWS[0] + ' .qual-row__badge--required').right, 193, 3)
        chk('c3.badgeRequired.h', rect(ROWS[0] + ' .qual-row__badge--required').h, 18, 1)
        chk('c3.badgeRequired.radius', css(ROWS[0] + ' .qual-row__badge--required', 'borderRadius'), '9px')
        chk('c3.badgeRequired.bg', css(ROWS[0] + ' .qual-row__badge--required', 'backgroundColor'), 'rgb(254, 242, 242)')
        chk('c3.badgeRequired.color', css(ROWS[0] + ' .qual-row__badge--required .qual-row__badge-text', 'color'), 'rgb(185, 28, 28)')
        chk('c3.badgeUploaded.w', rect('.qual-row__badge--uploaded').w, 62, 3)
        chk('c3.badgeUploaded.right', rect('.qual-row__badge--uploaded').right, 263, 3)
        chk('c3.badgeUploaded.h', rect('.qual-row__badge--uploaded').h, 18, 1)
        chk('c3.badgeUploaded.bg', css('.qual-row__badge--uploaded', 'backgroundColor'), 'rgb(236, 253, 245)')
        chk('c3.badgeUploaded.color', css('.qual-row__badge--uploaded .qual-row__badge-text', 'color'), 'rgb(21, 128, 61)')
        chk('c3.badgeUploadedGlyph.w', rect('.qual-row__badge--uploaded .glyph--check-sm').w, 13, 1) /* design acdea136 w=13 fs=11 → 行框 16 */
        chk('c3.badgeUploadedGlyph.h', rect('.qual-row__badge--uploaded .glyph--check-sm').h, 16, 1)
        chk('c3.badgeUploadedGlyph.color', css('.qual-row__badge--uploaded .glyph--check-sm', 'color'), 'rgb(22, 163, 74)')
        chk('region.chevronColor', css('.field__box--half@@0 .glyph--chevron', 'color'), 'rgb(148, 163, 184)') /* design fbc191db */
        chk('c3.badgeConditional.w', rect(ROWS[1] + ' .qual-row__badge').w, 57, 3)
        chk('c3.badgeConditional.h', rect(ROWS[1] + ' .qual-row__badge').h, 18, 1)
        chk('c3.badgeConditional.bg', css(ROWS[1] + ' .qual-row__badge', 'backgroundColor'), 'rgb(255, 247, 237)')
        chk('c3.badgeConditional.color', css(ROWS[1] + ' .qual-row__badge .qual-row__badge-text', 'color'), 'rgb(180, 83, 9)')
        chkList('c3.badgeTextFontSize', selCss(['[data-testid="qual-badge"]@@0', '[data-testid="qual-badge"]@@1', '[data-testid="qual-badge"]@@2'], 'fontSize'), ['10px', '10px', '10px'])
        chkList('c3.badgeTextFontWeight', selCss(['[data-testid="qual-badge"]@@0 .qual-row__badge-text', '[data-testid="qual-badge"]@@1 .qual-row__badge-text', '[data-testid="qual-badge"]@@2 .qual-row__badge-text'], 'fontWeight'), ['500', '500', '500'])
        chkList('c3.badgeTexts', texts('[data-testid="qual-badge"]'), ['必传', '已上传', '条件必传'])
        chk('c3.file.text', textOf('[data-testid="qual-file"]'), '营业执照-云智科技.jpg')
        chk('c3.file.h', rect('[data-testid="qual-file"]').h, 16, 1) /* design ce781949 显式 height 16 */
        chk('c3.file.fontSize', css('[data-testid="qual-file"]', 'fontSize'), '11px')
        chk('c3.file.color', css('[data-testid="qual-file"]', 'color'), 'rgb(148, 163, 184)')
        chkList('c3.hintTexts', texts('[data-testid="qual-hint"], [data-testid="qual-desc"]'), ['点击上传，仅支持单个文件', '增值电信业务许可证、等保备案等'])
        chkList('c3.hint.h', [rect('[data-testid="qual-hint"]').h, rect('[data-testid="qual-desc"]').h], [16, 16], 1)
        chk('c3.info.padLeft', css(ROWS[0] + ' .qual-row__info', 'paddingLeft'), '12px') /* design 623e8cdd padding-left 12 */
        chk('c3.nameRow.x', rect(ROWS[0] + ' .qual-row__name-row').x, 95, 1) /* 36 + 47 + 12 */
        chk('c3.rowsAbsent', all(doc, '[data-testid="qual-row"]').length, 3)
        /* 行内尾部图标：design 资质-营业执照 = [缩略图 47][信息 fill][删除盒 20][container padding-left 8 → 查看盒 20]
           → PNG y=1136/1142 实测：删除 ink 347..363（盒 346..366）· 查看 ink 380..386（盒 374..394）
           其余两行（授权书 / 选传）设计里**没有**尾部图标（PNG y=1198/1260 该区间无 ink） */
        chk('c3.row1.trashX', rect('.icon-tap@@0').x, 346, 1)
        chk('c3.row1.chevonX', rect('.icon-tap@@1').x, 374, 1)
        chk('c3.row1.iconW', rect('.icon-tap@@0').w, 20, 1)
        chk('c3.row1.iconGap', hgap('.icon-tap@@0', '.icon-tap@@1'), 8, 1)
        chk('c3.row2.iconAbsent', all(doc, '[data-testid="qual-row"]')[1].querySelectorAll('.icon-tap').length, 0)
        chk('c3.row3.iconAbsent', all(doc, '[data-testid="qual-row"]')[2].querySelectorAll('.icon-tap').length, 0)

        /* ===================== 底栏（design 1648cc81 padding[12,16,24,16]） ===================== */
        chkR('bar.top', '.bar', 1325, 2)
        chkR('bar.h', '.bar', 84, 1)
        chkC('bar.padTop', '.bar', 'paddingTop', 12)
        chkC('bar.padRight', '.bar', 'paddingRight', 16)
        chkC('bar.padBottom', '.bar', 'paddingBottom', 24)
        chkC('bar.padLeft', '.bar', 'paddingLeft', 16)
        chkC('bar.bg', '.bar', 'backgroundColor', 'rgb(255, 255, 255)')
        chk('bar.wrapPadTop', css('.bar-wrap', 'paddingTop'), '16px') /* design adc93132 padding-top 16 */
        chkR('bar.draft.x', '[data-testid="btn-draft"]', 16, 1)
        chkR('bar.draft.w', '[data-testid="btn-draft"]', 156, 1)
        chkR('bar.draft.h', '[data-testid="btn-draft"]', 48, 1)
        chkR('bar.draft.top', '[data-testid="btn-draft"]', 1337, 1)
        chk('bar.gap', hgap('[data-testid="btn-draft"]', '[data-testid="btn-save"]'), 12, 1)
        chk('bar.draft.radius', css('[data-testid="btn-draft"]', 'borderRadius'), '12px')
        chk('bar.draft.bg', css('[data-testid="btn-draft"]', 'backgroundColor'), 'rgb(255, 255, 255)')
        chk('bar.draft.ring', css('[data-testid="btn-draft"]', 'boxShadow'), 'rgb(203, 213, 225) 0px 0px 0px 1px')
        chk('bar.draft.color', css('[data-testid="btn-draft"]', 'color'), 'rgb(71, 85, 105)')
        chk('bar.draft.fontSize', css('[data-testid="btn-draft"]', 'fontSize'), '14px')
        chk('bar.draft.fontWeight', css('[data-testid="btn-draft"]', 'fontWeight'), 500)
        chk('bar.draft.text', textOf('[data-testid="btn-draft"]'), '保存草稿')
        chkR('bar.save.x', '[data-testid="btn-save"]', 184, 1)
        chkR('bar.save.w', '[data-testid="btn-save"]', 230, 1)
        chkR('bar.save.h', '[data-testid="btn-save"]', 48, 1)
        chk('bar.save.radius', css('[data-testid="btn-save"]', 'borderRadius'), '12px')
        chk('bar.save.bg', css('[data-testid="btn-save"]', 'backgroundColor'), 'rgb(37, 99, 235)')
        chk('bar.save.text', textOf('.btn__text'), '保存')
        chk('bar.save.textFontSize', css('.btn__text', 'fontSize'), '15px')
        chk('bar.save.textFontWeight', css('.btn__text', 'fontWeight'), 600)
        chk('bar.save.textColor', css('.btn__text', 'color'), 'rgb(255, 255, 255)')
        /* design 下一步按钮 子节点：文本声明宽 91（左对齐）+ container padding-left 4 + 箭头 22 → 组合 117 居中
           → 文本 ink 起于 240（PNG 实测 240..270）· 箭头盒 335.5..357.5（PNG 实测 ink 345..352） */
        chk('bar.save.textBoxW', rect('.btn__text').w, 91, 2)
        chk('bar.save.text.align', css('.btn__text', 'textAlign'), 'left')
        chk('bar.save.textX', rect('.btn__text').x, 240, 2)
        chk('bar.save.arrowW', rect('.glyph--arrow-white').w, 22, 2)
        chk('bar.save.arrowH', rect('.glyph--arrow-white').h, 30, 2) /* remixicon fs=20 → 行框 30 */
        chk('bar.save.arrowX', rect('.glyph--arrow-white').x, 335, 2)

        /* ===================== 文案齐备 / 取值齐全 / 溢出 ===================== */
        var needText = ['编辑主体档案', '72%', '主体信息', '企业名称 *', '统一社会信用代码 *', '供应商类型 *',
          '所在地区 *', '详细地址 *', '官网', '原厂', '渠道商', '中转商', '浙江省', '杭州市',
          '联系信息', '联系人 *', '职务', '手机号 *', '邮箱', '公司简介', '资质文件',
          '支持 JPG/PNG/PDF，≤10MB', '营业执照', '必传', '已上传', '营业执照-云智科技.jpg',
          '上游授权书', '条件必传', '点击上传，仅支持单个文件', '其他选传资质', '增值电信业务许可证、等保备案等',
          '保存草稿', '保存']
        var pageText = String(doc.body.innerText || '')
        var missing = needText.filter(function (t) { return pageText.indexOf(t) === -1 })
        chk('text.missingCount', missing.length, 0)
        /* 输入框/文本域的值不进 innerText（既知假象）→ 单独按 input.value 核对 */
        var needValues = ['云智科技有限公司', '91330106MA2XXXXX8B', '西湖区文三路 199 号 A 座 18F',
          '李明', '商务负责人', '13800006621', 'liming@yunzhi.com',
          '专注大模型 API 分销与聚合，覆盖华东区域客户，具备 3 年上游资源整合经验。']
        var gotValues = ['company-input', 'uscc-input', 'address-input', 'contact-input', 'title-input', 'phone-input', 'email-input', 'intro-input'].map(function (t) { return inputValue(t) })
        var missingValues = needValues.filter(function (v) { return gotValues.indexOf(v) === -1 })
        chk('values.missingCount', missingValues.length, 0)
        /* 官网为空 → 设计渲染的是占位文案（uni-app H5 会渲染 .uni-input-placeholder 文本节点） */
        var phAttr = (function () {
          var host = doc.querySelector('[data-testid="website-input"]')
          var el = host ? (host.tagName === 'INPUT' ? host : host.querySelector('input')) : null
          return el ? el.getAttribute('placeholder') : null
        })()
        var phInText = pageText.indexOf('请输入企业官网地址') !== -1
        chk('values.websitePlaceholder', phAttr === '请输入企业官网地址' || phInText, true)
        chkList('values.website', [inputValue('website-input')], [''], 0)

        /* 溢出：uni-app 内部测量元素（uni-resize-sensor / picker 空壳）不计入 */
        var over = []
        all(doc, '*').forEach(function (e) {
          if (e.closest && e.closest('uni-resize-sensor')) return
          var r = e.getBoundingClientRect()
          if (r.width > 0 && r.right > win.innerWidth + 0.5) {
            over.push({ tag: e.tagName, cls: String(e.className || '').slice(0, 60), right: Math.round(r.right) })
          }
        })
        chk('overflow.count', over.length, 0)

        return {
          innerWidth: win.innerWidth,
          docScrollWidth: doc.documentElement.scrollWidth,
          docScrollHeight: Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight),
          checkCount: checks,
          checkFailCount: fails.length,
          checkFails: fails,
          overflowing: over.slice(0, 10),
          /* 设计稿静态假数据差异留痕（不是页面缺陷）：设计计数 48/200，而同帧简介文案只有 40 字 */
          designLiteralDiff: { 'bio-count': '设计 48/200 vs 按真实字数 40/200' },
          cardRects: rects('.card'),
          topbar: rect('.topbar'),
          chip: rect('.completeness'),
          fieldBoxes: rects('.field__box'),
          chips: rects('[data-testid="industry-chip"]'),
          qualRows: rects('[data-testid="qual-row"]'),
          badges: rects('[data-testid="qual-badge"]'),
          bar: rect('.bar'),
          draftBtn: rect('[data-testid="btn-draft"]'),
          saveBtn: rect('[data-testid="btn-save"]'),
          title: textOf('.topbar__title'),
          chipText: textOf('.completeness'),
          counter: textOf('.field__counter'),
          labels: texts('.field__label'),
          cardTitles: texts('.card__title'),
          badgeTexts: texts('[data-testid="qual-badge"]'),
          missingTexts: missing,
          missingValues: missingValues,
          values: gotValues,
          userAgent: win.navigator.userAgent
        }
      }
"""

LOAD = r"""      function clickAll(sel, index) {
        var doc = f.contentDocument
        var el = all(doc, sel)[index]
        if (!el) return 'NOT_FOUND'
        var ev = doc.createEvent('MouseEvents')
        ev.initMouseEvent('click', true, true, f.contentWindow, 0, 0, 0, 0, 0, false, false, false, false, 0, null)
        el.dispatchEvent(ev)
        return 'CLICKED'
      }

      function valueOf(testid) {
        var host = f.contentDocument.querySelector('[data-testid="' + testid + '"]')
        if (!host) return null
        if (host.tagName === 'INPUT' || host.tagName === 'TEXTAREA') return host.value
        var inner = host.querySelector('input,textarea')
        return inner ? inner.value : null
      }

      /* collect() 内部的 textOf(sel) 用闭包里的 doc → 外层回调不能借用，这里另给一个 */
      function textIn(sel) {
        var e = f.contentDocument.querySelector(sel)
        return e ? e.textContent.trim() : null
      }

      function checkedStates() {
        return all(f.contentDocument, '[data-testid="industry-chip"]').map(function (e) { return e.getAttribute('data-checked') })
      }

      function fillField(testid, value) {
        /* ⚠️ 必须写内层原生控件：data-testid 落在 <uni-input>/<uni-textarea> 宿主上，
           给宿主设 .value + 派发 input 不触发 v-model（序号 9 实测） */
        var host = f.contentDocument.querySelector('[data-testid="' + testid + '"]')
        var el = host ? (host.tagName === 'INPUT' || host.tagName === 'TEXTAREA' ? host : host.querySelector('input,textarea')) : null
        if (!el) return 'NOT_FOUND'
        el.focus()
        el.value = value
        el.dispatchEvent(new Event('input', { bubbles: true }))
        return 'FILLED'
      }

      f.addEventListener('load', function () {
        var SC = SCENARIO
        setTimeout(function () { phase(1) }, 2400)

        if (SC === 'guard') {
          /* 校验门：只清空必填项后点保存 —— serve 实收必须 0 行写请求 */
          setTimeout(function () {
            fillField('company-input', '')
            setTimeout(function () {
              var clicked = clickIn('[data-testid="btn-save"]')
              setTimeout(function () {
                sink(2, {
                  scenario: 'guard',
                  clickedSave: clicked,
                  validateToast: toastText(f.contentDocument),
                  hash: String(f.contentWindow.location.hash),
                  saved: false
                })
              }, 1600)
            }, 900)
          }, 3200)
          return
        }

        if (SC !== 'actions') return

        /* phase2：类型 chip 切换（原厂 → 渠道商）+ 简介输入 */
        setTimeout(function () {
          var clickedOrigin = clickAll('[data-testid="industry-chip"]', 0)
          setTimeout(function () {
            var afterOrigin = checkedStates()
            clickAll('[data-testid="industry-chip"]', 1)
            setTimeout(function () {
              var afterBack = checkedStates()
              fillField('intro-input', '专注大模型')
              setTimeout(function () {
                sink(2, {
                  scenario: 'actions',
                  clickedOrigin: clickedOrigin,
                  checkedAfterOrigin: afterOrigin,
                  checkedAfterBack: afterBack,
                  introCounter: textIn('[data-testid="intro-counter"]'),
                  introValue: valueOf('intro-input'),
                  province: textIn('[data-testid="province-value"]'),
                  hash: String(f.contentWindow.location.hash)
                })
              }, 1200)
            }, 400)
          }, 400)
        }, 3400)

        /* phase3：清空企业名称 → 点保存（校验拦截）→ 点保存草稿（本地草稿 storage） */
        setTimeout(function () {
          fillField('company-input', '')
          setTimeout(function () {
            var clicked = clickIn('[data-testid="btn-save"]')
            setTimeout(function () {
              var validateToast = toastText(f.contentDocument)
              clickIn('[data-testid="btn-draft"]')
              setTimeout(function () {
                var raw = ''
                try { raw = f.contentWindow.localStorage.getItem('aap_provider_profile_draft') || '' } catch (e) { raw = 'ERR:' + e.message }
                sink(3, {
                  scenario: 'actions',
                  clickedSave: clicked,
                  validateToast: validateToast,
                  draftToast: toastText(f.contentDocument),
                  draftRaw: raw.slice(0, 300),
                  hash: String(f.contentWindow.location.hash)
                })
              }, 1500)
            }, 1500)
          }, 900)
        }, 5800)

        /* phase4：恢复企业名称 → 点保存（真实 PUT）→ 删资质行（uni-modal 二次确认 → DELETE） */
        setTimeout(function () {
          fillField('company-input', '云智科技有限公司')
          setTimeout(function () {
            clickIn('[data-testid="btn-save"]')
            setTimeout(function () {
              var saveToast = toastText(f.contentDocument)
              var chipAfter = textIn('[data-testid="completeness-chip"]')
              clickIn('[data-testid="qual-del-0"]')
              setTimeout(function () {
                var doc = f.contentDocument
                var modal = doc.querySelector('.uni-modal')
                var modalText = modal ? modal.textContent.replace(/\s+/g, ' ').trim() : ''
                var btns = all(doc, '.uni-modal__btn').map(function (b) { return b.textContent.trim() })
                var confirmed = clickIn('.uni-modal__btn_primary')
                setTimeout(function () {
                  sink(4, {
                    scenario: 'actions',
                    saveToast: saveToast,
                    chipAfterSave: chipAfter,
                    modalExists: !!modal,
                    modalText: modalText,
                    modalButtons: btns,
                    confirmClicked: confirmed,
                    toastAfterDelete: toastText(f.contentDocument),
                    qualRowsAfterDelete: all(f.contentDocument, '[data-testid="qual-row"]').length,
                    hash: String(f.contentWindow.location.hash)
                  })
                }, 1800)
              }, 900)
            }, 2000)
          }, 1000)
        }, 9000)
      })
    </script>
  </body>
</html>
"""

EXTRA_HELPERS = r"""        function selTop(sels) { return sels.map(function (s) { var r = rect(s); return r ? r.top : null }) }
        function selX(sels) { return sels.map(function (s) { var r = rect(s); return r ? r.x : null }) }
        function selW(sels) { return sels.map(function (s) { var r = rect(s); return r ? r.w : null }) }
        function selH(sels) { return sels.map(function (s) { var r = rect(s); return r ? r.h : null }) }
        function selCss(sels, prop) { return sels.map(function (s) { return css(s, prop) }) }
        function selText(sels) { return sels.map(function (s) { return textOf(s) }) }
        /* 横向间距：b 的左界 − a 的右界（gapBetween 是纵向的，横排元素上会得负数） */
        function hgap(aSel, bSel) {
          var a = rect(aSel), b = rect(bSel)
          return a && b ? b.x - a.right : null
        }
        /* 字符串数组逐项比较（chkList 只做数值比较，字符串会被 Math.abs(NaN) 静默放过） */
        function chkStrs(key, got, want) {
          if (!withChecks) return got
          checks++
          var ok = got.length === want.length
          if (ok) {
            for (var i = 0; i < got.length; i++) { if (norm(got[i]) !== norm(want[i])) { ok = false; break } }
          }
          if (!ok) fails.push({ k: key, got: got.join(' | '), want: want.join(' | ') })
          return got
        }
"""

out = HEAD + helpers + "\n" + EXTRA_HELPERS + "\n" + CHECKS + "\n" + tail + "\n" + LOAD

# quote-setup tail defines clickIn/clickAll/toastText; drop our duplicates if the tail
# already provides them (checked by grep below).
with io.open(DST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(out)
print("wrote", DST, len(out), "bytes")
for name in ["function clickIn", "function clickAll", "function toastText", "function fillField", "function sink", "function phase", "function chk(", "function declared("]:
    print(name, out.count("function " + name.replace("function ", "")))
