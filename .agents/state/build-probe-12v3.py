"""Build __measure-quote-success.html (序号 12-v3 · page-29「新增报价单-保存成功」) as a
430-wide iframe probe with design-expectation checks (chk/chkR/chkC/chkD/chkList/chkStrs/chkP).

做法与 build-probe-10/11/12/12v2 同：从 __measure-quote-apikey.html（同族载体页，含
`resolveAll` / `chkP` / `pseudoStyle` / `declared` 等全套 helpers）切三段「与帧无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计 / sink+phase+点击工具）逐字节复用，
本文件只写 page-29 自己的 checks / return / phases。

want 两类来源：
  (a) 声明值 .calicat/raw/pages/page-29/{design.json,design.tree.json}
      python .agents/state/dump-layout.py page-29      # 全字段（gap/lineHeight/effects/stroke/cornerRadius）
      python .agents/state/text-fields.py page-29      # 文本叶子 fontSize/字重/字色/宽高/文案
      python .agents/state/raw-node.py page-29 <id前缀> # 单节点完整 JSON
  (b) 设计截图 PNG 实测（430×1018）
      python .agents/state/png-rowclass.py <png> --x0 20 --x1 410   # 卡片/间隙
      python .agents/state/scan-col.py <png> 28 0 1018              # 单列色带（卡边界/底栏）
      python .agents/state/png-textbands.py <png> 32 390 412 640    # 盒内文字带（行位）

设计骨架（声明值 + PNG 实测逐条对上）：
  顶部导航 0..102（= 48 + 标题块 42 + 12）
  内容区 padding[16,16,20,16] gap16
  卡1 成功头部卡 118..374（256 = 28+64+14+24+18+18+62+28）
  卡2 结果摘要卡 390..639.5（249.5 = 16+20+14+38×3+39.5+30+16）
  卡3 带出模型卡 655.5..787.5（132 = 16+24+12+28+8+28+16）
  提示卡 803.5..851.5（48 = 12+24+12；PNG 文案墨迹 819..830 = 单行）
  底栏 871.5..1017.5（146 = 12+48+10+48+28）· 页高 1018
  卡内锚点（PNG）：成功图标 146..210 · 标题 224..248 · 说明 248..266 · 单号条 284..346(x32..398, 复制按钮 x315..384)
                  摘要标题行 406..426 · 5 行 440/478/516/554/593.5 · 环境小标 488..506 · 模型数标 526..544 · 状态标 604..623.5
                  标签行 708..735 / 743..772 · 主按钮 884..931.5 · 次按钮 941.5..989.5

本页定标（与其它页的差异，不静默统一）：
  · 图标字形行盒 = 字号 × 1.5（三条交叉验证：单号行 fs13→19.5 使卡2 恰 249.5 · 卡3 标题行 fs16→24 使卡3 恰 132
    · 提示卡 fs16→24 使提示卡恰 48）；字形颜色落在占位形状上（D5）→ 用 chkP 读 ::before。
  · 文本行盒：13px→18（PNG 五行算术自洽）· 15px 标题→20（PNG 卡2 高 249.5 反推）· 11px→无显式声明处走 13.2（提示卡文案）
    或显式 height（单号标签 15）。
  · stroke{align:center,thickness:0.8} → box-shadow: 0 0 0 0.8px（border 会占布局）· effects.drop_shadow → box-shadow。
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-quote-apikey.html")
DST = os.path.join(HM, "__measure-quote-success.html")

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
i_type = find("/** uni-app H5 的 <input>")

top = "\n".join(src[i_var:i_collect])
top = top.replace(
    "if (SHOT_ONLY) f.style.height = '1129px' /* = 设计帧高 */",
    "if (SHOT_ONLY) f.style.height = '1018px' /* = 设计帧高 */",
)
assert "'1018px'" in top, "SHOT 高度替换失败（顶部作用域切片变了？）"
preamble = "\n".join(src[i_collect:i_over])   # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])    # over / missing 统计（引用 NEED_TEXT / CARDS）
tail = "\n".join(src[i_sink:i_type])          # sink / phase / clickIn / toastText / hashNow / waitFor / sleep / textIn / countIn / bgsIn

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-quote-success</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      iframe { width: 430px; height: 900px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜（uni-app 技能 §5 口径）
         页面 12-v3：/pages/quote-form/success（【报价管理】新增报价单-保存成功，page-29 · layer_id 49d2fa52-959d-4415-9fda-edf38415d6bd）
         设计真源：.calicat/raw/pages/page-29/design.tree.json（重抓 sha256 cdd34a51… 逐字节相同）
         设计骨架（声明值 + 设计 PNG 430x1018 实测）：
           顶栏 0..102（padding 48/16/12/16 · 标题块 42）· 内容区 padding 16/16/20/16 gap 16
           卡1 118..374(256) · 卡2 390..639.5(249.5) · 卡3 655.5..787.5(132) · 提示卡 803.5..851.5(48) · 底栏 871.5..1017.5(146)
           卡内锚点：成功图标 146..210(64) · 标题 224..248 · 说明 248..266 · 单号条 284..346(62, x32..398 · 复制按钮 x315..384)
                     摘要标题行 406..426(20) · 五行 440/478/516/554/593.5（38/38/38/39.5/30）
                     环境小标 488..506 · 模型数标 526..544 · 状态标 604..623.5 · 标签行 708..735 / 743..772
                     主按钮 884..931.5 · 次按钮 941.5..989.5
         ?scenario=copy|primary|secondary|close 逐个回放出口；不带 scenario（或 noaction）只取 phase1 设计期望值相 -->
    <iframe id="f" src="/index.html#/pages/quote-form/success?quoteId=q9"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

PRELUDE = r"""
        var CARDS = '.card'
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-29 design.tree.json；
           图标字形层 content 为空不进清单。示例值「QT-20240615-0007」「2024Q3 主线路报价」「共 5 个 / 勾选 3 个」
           来自本页 mock（api-12-v3），不是页面硬编码 → 进清单） */
        var NEED_TEXT = [
          '报价单已创建', '报价单号已自动生成',
          '报价单创建成功', '已保存基本信息并带出模型清单',
          '报价单号', 'QT-20240615-0007', '复制',
          '结果摘要', '报价单名称', '2024Q3 主线路报价', '凭证名称', '生产环境', 'sk-prod-••2f9a',
          '参与报价模型', '已勾选 3 个', '当前状态', '草稿',
          '已带出模型', '共 5 个 / 勾选 3 个',
          'gpt-4o', 'gpt-4o-mini', 'claude-3-5', 'gemini-1.5-pro', 'deepseek-chat',
          '下一步可为勾选模型设置输入/输出单价，设置完成即可提交审核。',
          '继续设置模型报价', '返回报价单列表'
        ]
"""

CHECKS = r"""
        /* ===================== 整页（设计帧 430×1018） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 1018, 3) /* 设计帧 PNG 1018 行（底栏底 1017.5 取整） */
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.qs', 'backgroundColor', 'rgb(245, 247, 251)') /* 页面容器 08f6714a fills rgba(245,247,251,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 3)
        chk('page.tabbarAbsent', !!doc.querySelector('.tabbar'), false)
        chk('page.succCardCount', doc.querySelectorAll('[data-testid="success-card"]').length, 1)
        /* PNG 实测卡边界：118..374(256) · 390..639.5(249.5) · 655.5..787.5(132) → 取整 118/390/656 */
        chkList('page.cardTops', rects(CARDS).map(function (r) { return r.top }), [118, 390, 656], 1)
        chkList('page.cardHeights', rects(CARDS).map(function (r) { return r.h }), [256, 250, 132], 1)
        chkList('page.cardX', rects(CARDS).map(function (r) { return r.x }), [16, 16, 16], 1)
        chkList('page.cardW', rects(CARDS).map(function (r) { return r.w }), [398, 398, 398], 1)
        chkStrs('page.cardBg', colors(CARDS), ['rgb(255, 255, 255)', 'rgb(255, 255, 255)', 'rgb(255, 255, 255)'])
        chkC('page.card1Radius', '.card@@0', 'borderRadius', '16px')
        chkC('page.card2Radius', '.card@@1', 'borderRadius', '16px')
        chkC('page.card3Radius', '.card@@2', 'borderRadius', '16px')
        /* design effects：三张卡逐卡 drop_shadow(0,4,16,rgba(15,23,42,0.06))；三卡均无 stroke → 不得用 ring 顶替 */
        chkC('page.card1Shadow', '.card@@0', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkC('page.card2Shadow', '.card@@1', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkC('page.card3Shadow', '.card@@2', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chk('page.card2BorderDeclared', declared('.card@@1', 'border'), null) /* 反向断言：设计只有投影，没有描边 */
        chk('page.gap12', rect(CARDS + '@@1').top - rect(CARDS + '@@0').bottom, 16, 1)
        chk('page.gap23', rect(CARDS + '@@2').top - rect(CARDS + '@@1').bottom, 16, 1)
        chk('page.gapToTip', rect('[data-testid="tip-card"]').top - rect(CARDS + '@@2').bottom, 16, 1)
        chk('page.gapToBar', rect('.qs__bar').top - rect('[data-testid="tip-card"]').bottom, 20, 1) /* 内容区 padding-bottom 20 */

        /* ===================== 顶部导航（design 86e36607 padding[48,16,12,16]） ===================== */
        chkR('nav.h', '.qs__nav', 102, 1) /* 48 + 标题块(24+18=42) + 12 */
        chkC('nav.pad', '.qs__nav', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.qs__nav', 'backgroundColor', 'rgb(255, 255, 255)')
        chkR('nav.back.x', '[data-testid="back"]', 16, 1)
        chkR('nav.back.w', '[data-testid="back"]', 36, 1) /* 357a3d7f 36×36 r18 #F1F5F9 */
        chkR('nav.back.h', '[data-testid="back"]', 36, 1)
        chkC('nav.back.radius', '[data-testid="back"]', 'borderRadius', '18px')
        chkC('nav.back.bg', '[data-testid="back"]', 'backgroundColor', 'rgb(241, 245, 249)')
        /* 返回字形 581eaf07 fs18 w20 #334155 → 盒 20×27（图标字形行盒 = 字号×1.5），形状入 ::before（D5） */
        chkR('nav.backIcon.w', '.ic-back', 20, 1)
        chkR('nav.backIcon.h', '.ic-back', 27, 1)
        chkP('nav.backIcon.color', '.ic-back', 'borderLeftColor', 'rgb(51, 65, 85)')
        chk('nav.left.gap', rect('[data-testid="nav-title"]').x - rect('[data-testid="back"]').right, 12, 1) /* 顶部左侧 6a60cbdb gap=12 */
        chkR('nav.title.x', '[data-testid="nav-title"]', 64, 1) /* 16 + 36 + 12 */
        chkR('nav.title.h', '[data-testid="nav-title"]', 24, 1) /* edddf3fc height 24 */
        chkC('nav.title.fs', '.nav__title', 'fontSize', 18)
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700)
        chkC('nav.title.lh', '.nav__title', 'lineHeight', 24)
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('[data-testid="nav-title"]')], ['报价单已创建'])
        chkC('nav.sub.fs', '.nav__subtitle', 'fontSize', 12) /* 63fbec31 height 18 fs12 #94A3B8 */
        chkC('nav.sub.fw', '.nav__subtitle', 'fontWeight', 400)
        chkC('nav.sub.lh', '.nav__subtitle', 'lineHeight', 18)
        chkC('nav.sub.color', '.nav__subtitle', 'color', 'rgb(148, 163, 184)')
        chkStrs('nav.sub.text', [textOf('[data-testid="nav-subtitle"]')], ['报价单号已自动生成'])
        chkR('nav.titles.w', '.nav__titles', 108, 4) /* 59059973 标题块 w108（CJK 字体度量允许 ±4） */
        chkR('nav.close.right', '[data-testid="close"]', 414, 1)
        chkR('nav.close.w', '[data-testid="close"]', 36, 1) /* 000f0870 36×36 r18 #F1F5F9 */
        chkR('nav.close.h', '[data-testid="close"]', 36, 1)
        chkC('nav.close.radius', '[data-testid="close"]', 'borderRadius', '18px')
        chkC('nav.close.bg', '[data-testid="close"]', 'backgroundColor', 'rgb(241, 245, 249)')
        chkR('nav.closeIcon.w', '.ic-close', 20, 1) /* 4edd7cd1 fs18 w20 #64748B */
        chkR('nav.closeIcon.h', '.ic-close', 27, 1)
        chkP('nav.closeIcon.color', '.ic-close', 'backgroundColor', 'rgb(100, 116, 139)')

        /* ===================== 成功头部卡（design f5d8ac7d padding[28,16,28,16] r16） ===================== */
        chkC('succ.pad', '[data-testid="success-card"]', 'padding', '28px 16px')
        chkR('succ.icon.top', '.succ__icon', 146, 1) /* PNG 图标 146..209 */
        chkR('succ.icon.w', '.succ__icon', 64, 1) /* c98d69ea 64×64 r32 #ECFDF5 */
        chkR('succ.icon.h', '.succ__icon', 64, 1)
        chkC('succ.icon.radius', '.succ__icon', 'borderRadius', '32px')
        chkC('succ.icon.bg', '.succ__icon', 'backgroundColor', 'rgb(236, 253, 245)')
        chkR('succ.iconGlyph.w', '.ic-check-big', 41, 1) /* 9bc128ea fs38 w41 #16A34A */
        chkR('succ.iconGlyph.h', '.ic-check-big', 57, 2)
        chkP('succ.iconGlyph.color', '.ic-check-big', 'borderLeftColor', 'rgb(22, 163, 74)')
        chkR('succ.titleWrap.h', '.succ__title-wrap', 38, 1) /* padding-top 14 + 行盒 24 */
        chkR('succ.title.h', '[data-testid="success-title"]', 24, 1) /* 1961a349 height 24 */
        chkC('succ.title.fs', '.succ__title', 'fontSize', 18)
        chkC('succ.title.fw', '.succ__title', 'fontWeight', 700)
        chkC('succ.title.lh', '.succ__title', 'lineHeight', 24)
        chkC('succ.title.color', '.succ__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('succ.title.text', [textOf('[data-testid="success-title"]')], ['报价单创建成功'])
        chkC('succ.desc.fs', '.succ__desc', 'fontSize', 12) /* 5ae9adf1 height 18 fs12 #94A3B8 */
        chkC('succ.desc.lh', '.succ__desc', 'lineHeight', 18)
        chkC('succ.desc.color', '.succ__desc', 'color', 'rgb(148, 163, 184)')
        chkStrs('succ.desc.text', [textOf('[data-testid="success-desc"]')], ['已保存基本信息并带出模型清单'])
        chkR('succ.barWrap.h', '.succ__bar-wrap', 80, 1) /* padding-top 18 + 单号条 62 */

        /* ===================== 单号展示条（design 22395006 padding[12,14,12,14] r12 stroke .8 #BFDBFE） ===================== */
        chkR('noBar.x', '[data-testid="quote-no-bar"]', 32, 1)
        chkR('noBar.w', '[data-testid="quote-no-bar"]', 366, 1)
        chkR('noBar.top', '[data-testid="quote-no-bar"]', 284, 1) /* PNG 单号条 284..346 */
        chkR('noBar.h', '[data-testid="quote-no-bar"]', 62, 1)
        chkC('noBar.pad', '.no-bar', 'padding', '12px 14px')
        chkC('noBar.radius', '.no-bar', 'borderRadius', '12px')
        chkC('noBar.bg', '.no-bar', 'backgroundColor', 'rgb(248, 250, 252)')
        chkC('noBar.ring', '.no-bar', 'boxShadow', 'rgb(191, 219, 254) 0px 0px 0px 0.8px')
        chk('noBar.borderDeclared', declared('.no-bar', 'border'), null) /* 反向：中心描边只能 ring 表达 */
        chkR('noBar.info.w', '.no-bar__info', 155, 1) /* 60931401 w155 */
        chkC('noBar.label.fs', '.no-bar__label', 'fontSize', 11) /* f7d70ca1 height 15 fs11 Medium #94A3B8 */
        chkC('noBar.label.fw', '.no-bar__label', 'fontWeight', 500)
        chkC('noBar.label.lh', '.no-bar__label', 'lineHeight', 15)
        chkC('noBar.label.color', '.no-bar__label', 'color', 'rgb(148, 163, 184)')
        chkStrs('noBar.label.text', [textOf('[data-testid="quote-no-label"]')], ['报价单号'])
        chkC('noBar.value.fs', '.no-bar__value', 'fontSize', 17) /* 7a53816e height 23 fs17 Bold #2563EB */
        chkC('noBar.value.fw', '.no-bar__value', 'fontWeight', 700)
        chkC('noBar.value.lh', '.no-bar__value', 'lineHeight', 23)
        chkC('noBar.value.color', '.no-bar__value', 'color', 'rgb(37, 99, 235)')
        chkStrs('noBar.value.text', [textOf('[data-testid="quote-no-value"]')], ['QT-20240615-0007'])
        chkR('noBar.copy.right', '[data-testid="copy"]', 384, 1) /* PNG 复制按钮 315..384 */
        chkR('noBar.copy.w', '[data-testid="copy"]', 69, 5) /* 6bb5859a = 12+16+4+25+12（文案宽度随字体 ±） */
        chkR('noBar.copy.h', '[data-testid="copy"]', 32, 1)
        chkC('noBar.copy.pad', '.no-bar__copy', 'padding', '0px 12px')
        chkC('noBar.copy.radius', '.no-bar__copy', 'borderRadius', '10px')
        chkC('noBar.copy.bg', '.no-bar__copy', 'backgroundColor', 'rgb(239, 246, 255)')
        chkC('noBar.copy.gap', '.no-bar__copy', 'columnGap', 4)
        chkR('noBar.copyIcon.w', '.ic-copy', 16, 1) /* bd63a0f4 fs14 w16 #2563EB */
        chkR('noBar.copyIcon.h', '.ic-copy', 21, 1)
        chkP('noBar.copyIcon.color', '.ic-copy', 'borderLeftColor', 'rgb(37, 99, 235)')
        chkC('noBar.copyText.fs', '.no-bar__copy-text', 'fontSize', 12) /* 2a52645d fs12 SemiBold #2563EB */
        chkC('noBar.copyText.fw', '.no-bar__copy-text', 'fontWeight', 600)
        chkC('noBar.copyText.color', '.no-bar__copy-text', 'color', 'rgb(37, 99, 235)')
        chkStrs('noBar.copyText.text', [textOf('.no-bar__copy-text')], ['复制'])

        /* ===================== 结果摘要卡：标题行（design c0b98aa4 gap8） ===================== */
        chkR('sum.head.h', '.card@@1 .card__head', 20, 1) /* PNG 摘要标题行 406..426 */
        chkC('sum.head.gap', '.card@@1 .card__head', 'columnGap', 8)
        chkR('sum.bar.w', '.card@@1 .head__bar', 5, 1) /* 52d37f40 5×16 r2 #2563EB */
        chkR('sum.bar.h', '.card@@1 .head__bar', 16, 1)
        chkC('sum.bar.radius', '.card@@1 .head__bar', 'borderRadius', '2px')
        chkC('sum.bar.bg', '.card@@1 .head__bar', 'backgroundColor', 'rgb(37, 99, 235)')
        chkR('sum.title.x', '[data-testid="summary-title"]', 45, 1) /* 32 + 5 + 8 */
        chkC('sum.title.fs', '[data-testid="summary-title"]', 'fontSize', 15) /* 8f374f84 fs15 Bold #0F172A */
        chkC('sum.title.fw', '[data-testid="summary-title"]', 'fontWeight', 700)
        chkC('sum.title.color', '[data-testid="summary-title"]', 'color', 'rgb(15, 23, 42)')
        chkStrs('sum.title.text', [textOf('[data-testid="summary-title"]')], ['结果摘要'])
        chk('sum.rowsOffset', rects('.srow')[0].top - rect('.card@@1 .card__head').bottom, 14, 1) /* 容器 a0be0ffb padding-top 14 */
        /* PNG 五行：440/478/516/554/593.5 起，高 38/38/38/39.5/30 */
        chkList('sum.rowTops', rects('.srow').map(function (r) { return r.top }), [440, 478, 516, 554, 594], 1)
        chkList('sum.rowHeights', rects('.srow').map(function (r) { return r.h }), [38, 38, 38, 40, 30], 1)
        chkStrs('sum.label.texts', texts('.srow__label'), ['报价单名称', '凭证名称', '参与报价模型', '报价单号', '当前状态'])
        chkC('sum.label.fs', '.srow__label@@0', 'fontSize', 13) /* 4bb8ac13 fs13 #94A3B8 */
        chkC('sum.label.fw', '.srow__label@@0', 'fontWeight', 400)
        chkC('sum.label.lh', '.srow__label@@0', 'lineHeight', 18)
        chkC('sum.label.color', '.srow__label@@0', 'color', 'rgb(148, 163, 184)')
        chkC('sum.nameValue.fs', '.srow__value@@0', 'fontSize', 13) /* 2c1fc5b0 fs13 SemiBold #0F172A */
        chkC('sum.nameValue.fw', '.srow__value@@0', 'fontWeight', 600)
        chkC('sum.nameValue.color', '.srow__value@@0', 'color', 'rgb(15, 23, 42)')
        chkStrs('sum.nameValue.text', [textOf('.srow__value@@0')], ['2024Q3 主线路报价'])
        /* 密钥行：环境小标 h18 r9 #EFF6FF + 脱敏 key */
        chkR('sum.envChip.h', '.env-chip', 18, 1) /* 2a6f28d0 h18 padding[0,8] r9 #EFF6FF */
        chkR('sum.envChip.w', '.env-chip', 57, 6) /* = 41 + 16（文案宽度随字体 ±） */
        chkC('sum.envChip.pad', '.env-chip', 'padding', '0px 8px')
        chkC('sum.envChip.radius', '.env-chip', 'borderRadius', '9px')
        chkC('sum.envChip.bg', '.env-chip', 'backgroundColor', 'rgb(239, 246, 255)')
        chkC('sum.envChip.fs', '.env-chip__text', 'fontSize', 10) /* 2fa8f443 fs10 SemiBold #2563EB */
        chkC('sum.envChip.fw', '.env-chip__text', 'fontWeight', 600)
        chkC('sum.envChip.color', '.env-chip__text', 'color', 'rgb(37, 99, 235)')
        chkStrs('sum.envChip.text', [textOf('[data-testid="cred-env-tag"]')], ['生产环境'])
        chkC('sum.credGap', '.srow__value-group@@0', 'columnGap', 8) /* 密钥信息 e86268ab gap8 */
        chkC('sum.mask.fs', '[data-testid="cred-mask"]', 'fontSize', 13) /* 77b3615b fs13 SemiBold #0F172A */
        chkC('sum.mask.color', '[data-testid="cred-mask"]', 'color', 'rgb(15, 23, 42)')
        chkStrs('sum.mask.text', [textOf('[data-testid="cred-mask"]')], ['sk-prod-••2f9a'])
        /* 模型数行：模型数标 h18 r9 #ECFDF5 */
        chkR('sum.countChip.h', '.count-chip', 18, 1) /* 22acf5bc h18 padding[0,8] r9 #ECFDF5 */
        chkR('sum.countChip.w', '.count-chip', 68, 8) /* = 52 + 16 */
        chkC('sum.countChip.pad', '.count-chip', 'padding', '0px 8px')
        chkC('sum.countChip.radius', '.count-chip', 'borderRadius', '9px')
        chkC('sum.countChip.bg', '.count-chip', 'backgroundColor', 'rgb(236, 253, 245)')
        chkC('sum.countChip.fs', '.count-chip__text', 'fontSize', 10) /* 40a814ab fs10 SemiBold #16A34A */
        chkC('sum.countChip.fw', '.count-chip__text', 'fontWeight', 600)
        chkC('sum.countChip.color', '.count-chip__text', 'color', 'rgb(22, 163, 74)')
        chkStrs('sum.countChip.text', [textOf('.count-chip__text')], ['已勾选 3 个'])
        /* 单号行：绿勾字形 fs13（盒 15×19.5）+ 蓝单号 */
        chkR('sum.checkIcon.w', '.ic-check-sm', 15, 1) /* b008562c fs13 w15 #16A34A */
        chkR('sum.checkIcon.h', '.ic-check-sm', 19.5, 1)
        chkP('sum.checkIcon.color', '.ic-check-sm', 'borderLeftColor', 'rgb(22, 163, 74)')
        chk('sum.checkGap', rect('.srow__value--primary').x - rect('.ic-check-sm').right, 4, 1) /* 单号值行 55b312e3 gap4 */
        chkC('sum.noGroup.gap', '.srow__value-group@@1', 'columnGap', 4) /* 单号行右侧组 gap4（≠ 密钥行的 8） */
        chkC('sum.noValue.fs', '.srow__value--primary', 'fontSize', 13) /* 056d35c2 fs13 SemiBold #2563EB */
        chkC('sum.noValue.fw', '.srow__value--primary', 'fontWeight', 600)
        chkC('sum.noValue.color', '.srow__value--primary', 'color', 'rgb(37, 99, 235)')
        chkStrs('sum.noValue.text', [textOf('.srow__value--primary')], ['QT-20240615-0007'])
        /* 状态行：状态标 c9fda041 h20 padding[0,8] r10 #F1F5F9 gap4（点 7×6 r3 #94A3B8 + 文案 11px SemiBold #64748B） */
        chkR('sum.status.right', '.status-chip', 398, 1)
        chkR('sum.status.h', '.status-chip', 20, 1)
        chkC('sum.status.pad', '.status-chip', 'padding', '0px 8px')
        chkC('sum.status.radius', '.status-chip', 'borderRadius', '10px')
        chkC('sum.status.gap', '.status-chip', 'columnGap', 4)
        chkC('sum.status.bg', '.status-chip', 'backgroundColor', 'rgb(241, 245, 249)')
        chkR('sum.dot.w', '.status-chip__dot', 7, 1)
        chkR('sum.dot.h', '.status-chip__dot', 6, 1)
        chkC('sum.dot.radius', '.status-chip__dot', 'borderRadius', '3px')
        chkC('sum.dot.bg', '.status-chip__dot', 'backgroundColor', 'rgb(148, 163, 184)')
        chkC('sum.status.fs', '.status-chip__text', 'fontSize', 11) /* 7df23b37 fs11 SemiBold #64748B */
        chkC('sum.status.fw', '.status-chip__text', 'fontWeight', 600)
        chkC('sum.status.color', '.status-chip__text', 'color', 'rgb(100, 116, 139)')
        chkStrs('sum.status.text', [textOf('[data-testid="status-chip"]')], ['草稿'])

        /* ===================== 带出模型卡（design cec63018 padding16 r16） ===================== */
        chkR('models.head.h', '.card@@2 .card__head', 24, 1) /* 标题行 = 图标字形行盒 fs16×1.5 = 24（PNG 卡3 高 132 反推） */
        chkC('models.head.gap', '.card@@2 .card__head', 'columnGap', 8)
        chkR('models.iconGlyph.w', '.card@@2 .ic-models', 18, 1) /* f6b7fbbd fs16 w18 #2563EB */
        chkR('models.iconGlyph.h', '.card@@2 .ic-models', 24, 1)
        chkP('models.iconGlyph.color', '.card@@2 .ic-models', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('models.title.fs', '[data-testid="model-card-title"]', 'fontSize', 14) /* 78988284 fs14 SemiBold #0F172A */
        chkC('models.title.fw', '[data-testid="model-card-title"]', 'fontWeight', 600)
        chkC('models.title.color', '[data-testid="model-card-title"]', 'color', 'rgb(15, 23, 42)')
        chkStrs('models.title.text', [textOf('[data-testid="model-card-title"]')], ['已带出模型'])
        chkC('models.count.fs', '.head__count', 'fontSize', 11) /* 81bd48f2 fs11 #94A3B8 */
        chkC('models.count.fw', '.head__count', 'fontWeight', 400)
        chkC('models.count.color', '.head__count', 'color', 'rgb(148, 163, 184)')
        chkR('models.count.right', '[data-testid="model-count"]', 398, 1)
        chkStrs('models.count.text', [textOf('[data-testid="model-count"]')], ['共 5 个 / 勾选 3 个'])
        /* 标签组（PNG：组1 708..735 · 组2 743..772；容器 pt12 / pt8，组内 gap8，标签 h28 r14） */
        chk('models.tagsGap1', rects('.tags')[0].top - rect('.card@@2 .card__head').bottom, 12, 1)
        chk('models.tagsGap2', rects('.tags')[1].top - rects('.tags')[0].bottom, 8, 1)
        chkList('models.tagTops', rects('.tag').map(function (r) { return r.top }), [708, 708, 708, 744, 744], 1)
        chkList('models.tagHeights', rects('.tag').map(function (r) { return r.h }), [28, 28, 28, 28, 28], 1)
        chkStrs('models.tagTexts', texts('.tag__text'),
          ['gpt-4o', 'gpt-4o-mini', 'claude-3-5', 'gemini-1.5-pro', 'deepseek-chat'])
        chkStrs('models.tagSelected',
          Array.prototype.slice.call(doc.querySelectorAll('.tag')).map(function (e) { return e.getAttribute('data-selected') }),
          ['true', 'true', 'true', 'false', 'false'])
        chkR('models.tag1.x', '.tag--on@@0', 32, 1)
        chkC('models.tag.radius', '.tag--on@@0', 'borderRadius', '14px')
        chkC('models.tag.pad', '.tag--on@@0', 'padding', '0px 12px')
        chkC('models.tagOn.bg', '.tag--on@@0', 'backgroundColor', 'rgb(239, 246, 255)') /* 64ec1411 #EFF6FF */
        chkC('models.tagOn.fs', '.tag--on@@0 .tag__text', 'fontSize', 12) /* 95825493 fs12 SemiBold #2563EB */
        chkC('models.tagOn.fw', '.tag--on@@0 .tag__text', 'fontWeight', 600)
        chkC('models.tagOn.color', '.tag--on@@0 .tag__text', 'color', 'rgb(37, 99, 235)')
        chkC('models.tagOff.bg', '.tag--off@@0', 'backgroundColor', 'rgb(248, 250, 252)') /* 1f778b64 #F8FAFC */
        chkC('models.tagOff.ring', '.tag--off@@0', 'boxShadow', 'rgb(241, 245, 249) 0px 0px 0px 0.8px')
        chkC('models.tagOff.fs', '.tag--off@@0 .tag__text', 'fontSize', 12) /* 5b74c3e9 fs12 Medium #94A3B8 */
        chkC('models.tagOff.fw', '.tag--off@@0 .tag__text', 'fontWeight', 500)
        chkC('models.tagOff.color', '.tag--off@@0 .tag__text', 'color', 'rgb(148, 163, 184)')
        chk('models.tagGapOn', rects('.tag--on')[1].x - rects('.tag--on')[0].right, 8, 2)
        chk('models.tagGapOff', rects('.tag--off')[1].x - rects('.tag--off')[0].right, 8, 2)

        /* ===================== 下一步提示卡（design 0282549e padding[12,14,12,14] gap8 r14） ===================== */
        chkR('tip.top', '[data-testid="tip-card"]', 804, 1) /* PNG 提示卡 803.5..851.5 */
        chkR('tip.h', '[data-testid="tip-card"]', 48, 1) /* 12 + 图标字形行盒 24 + 12 */
        chkC('tip.pad', '.tip', 'padding', '12px 14px')
        chkC('tip.radius', '.tip', 'borderRadius', '14px')
        chkC('tip.bg', '.tip', 'backgroundColor', 'rgb(239, 246, 255)')
        chkC('tip.gap', '.tip', 'columnGap', 8)
        chkC('tip.align', '.tip', 'alignItems', 'flex-start')
        chkR('tip.iconGlyph.w', '.tip .ic-info', 18, 1) /* f986592e fs16 w18 #2563EB */
        chkR('tip.iconGlyph.h', '.tip .ic-info', 24, 1)
        chkP('tip.iconGlyph.color', '.tip .ic-info', 'borderLeftColor', 'rgb(37, 99, 235)')
        chkR('tip.text.x', '[data-testid="tip"]', 56, 1) /* 16 + 14 + 18 + 8 */
        chkC('tip.text.fs', '.tip__text', 'fontSize', 11) /* 64c00211 fs11 #1D4ED8 */
        chkC('tip.text.color', '.tip__text', 'color', 'rgb(29, 78, 216)')
        chkC('tip.text.lh', '.tip__text', 'lineHeight', 13.2, 0.2)
        chkR('tip.text.h', '[data-testid="tip"]', 14, 1) /* 设计帧该文案一行（PNG 墨迹 819..830 单带） */
        chkStrs('tip.text.text', [textOf('[data-testid="tip"]')],
          ['下一步可为勾选模型设置输入/输出单价，设置完成即可提交审核。'])

        /* ===================== 底部操作条（design a17976f7 padding[12,16,28,16]） ===================== */
        chkR('bar.top', '.qs__bar', 872, 1) /* PNG 底栏 871.5..1017.5 */
        chkR('bar.h', '.qs__bar', 146, 1)
        chkC('bar.pad', '.qs__bar', 'padding', '12px 16px 28px')
        chkC('bar.bg', '.qs__bar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('bar.shadow', '.qs__bar', 'boxShadow', 'rgba(15, 23, 42, 0.05) 0px -4px 16px 0px') /* effects(0,-4,16,.05) */
        chkR('bar.primary.top', '[data-testid="btn-primary"]', 884, 1) /* PNG 主按钮 884..931 */
        chkR('bar.primary.h', '[data-testid="btn-primary"]', 48, 1)
        chkR('bar.primary.w', '[data-testid="btn-primary"]', 398, 1)
        chkC('bar.primary.radius', '[data-testid="btn-primary"]', 'borderRadius', '12px')
        chkC('bar.primary.bg', '[data-testid="btn-primary"]', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('bar.primary.shadow', '[data-testid="btn-primary"]', 'boxShadow', 'rgba(37, 99, 235, 0.28) 0px 6px 16px 0px')
        chkC('bar.primary.gap', '[data-testid="btn-primary"]', 'columnGap', 8)
        chkR('bar.primaryIcon.w', '.ic-shield', 20, 1) /* 21d896a0 fs18 w20 #FFFFFF */
        chkR('bar.primaryIcon.h', '.ic-shield', 27, 1)
        chkP('bar.primaryIcon.color', '.ic-shield', 'borderLeftColor', 'rgb(255, 255, 255)')
        chkC('bar.primaryText.fs', '.btn__text--light', 'fontSize', 15) /* a485f238 fs15 SemiBold #FFFFFF */
        chkC('bar.primaryText.fw', '.btn__text--light', 'fontWeight', 600)
        chkC('bar.primaryText.color', '.btn__text--light', 'color', 'rgb(255, 255, 255)')
        chkStrs('bar.primaryText.text', [textOf('[data-testid="btn-primary"]')], ['继续设置模型报价'])
        chk('bar.secondaryGap', rect('[data-testid="btn-secondary"]').top - rect('[data-testid="btn-primary"]').bottom, 10, 1) /* 容器 2730bde2 padding-top 10 */
        chkR('bar.secondary.h', '[data-testid="btn-secondary"]', 48, 1)
        chkC('bar.secondary.radius', '[data-testid="btn-secondary"]', 'borderRadius', '12px')
        chkC('bar.secondary.bg', '[data-testid="btn-secondary"]', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('bar.secondary.ring', '[data-testid="btn-secondary"]', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px')
        chkC('bar.secondaryText.fs', '.btn--ghost .btn__text', 'fontSize', 14) /* 20db89c2 fs14 SemiBold #64748B */
        chkC('bar.secondaryText.fw', '.btn--ghost .btn__text', 'fontWeight', 600)
        chkC('bar.secondaryText.color', '.btn--ghost .btn__text', 'color', 'rgb(100, 116, 139)')
        chkStrs('bar.secondaryText.text', [textOf('[data-testid="btn-secondary"]')], ['返回报价单列表'])

        /* 设计帧字面量登记（不照抄的项，逐条说明；同 D3 图例百分比口径） */
        var designLiteralDiff = [
          '单号展示条：设计「单号信息」声明 155 宽 + 单号 17px Bold → PNG 该行墨迹 46..191 为单行（设计把文本节点 height 固定 23）→ 实现按单行渲染（white-space: nowrap）',
          '「已勾选 3 个」「共 5 个 / 勾选 3 个」的数字是设计帧的示例选择态 → 实现按 mock/服务端数据计算（本页 api-12-v3 恰为 3/5），不照抄字面量',
          '复制成功 toast 文案：设计稿与 22 份 PRD 均无稿 → 占位「报价单号已复制」（missing-prd 6）'
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
          nav: rect('.qs__nav'),
          cards: rects(CARDS),
          cardShadows: [css('.card@@0', 'boxShadow'), css('.card@@1', 'boxShadow'), css('.card@@2', 'boxShadow')],
          succIcon: rect('.succ__icon'),
          noBar: rect('.no-bar'),
          noBarCopy: rect('.no-bar__copy'),
          rows: rects('.srow'),
          envChip: rect('.env-chip'),
          countChip: rect('.count-chip'),
          statusChip: rect('.status-chip'),
          statusDot: rect('.status-chip__dot'),
          tagRows: rects('.tags'),
          tags: rects('.tag'),
          tip: rect('.tip'),
          tipText: rect('.tip__text'),
          bar: rect('.qs__bar'),
          primary: rect('[data-testid="btn-primary"]'),
          secondary: rect('[data-testid="btn-secondary"]'),
          iconBoxes: {
            back: rect('.ic-back'), close: rect('.ic-close'), succCheck: rect('.ic-check-big'),
            copy: rect('.ic-copy'), checkSm: rect('.ic-check-sm'), models: rect('.ic-models'),
            info: rect('.tip .ic-info'), shield: rect('.ic-shield')
          },
          texts: {
            navTitle: textOf('[data-testid="nav-title"]'),
            navSub: textOf('[data-testid="nav-subtitle"]'),
            succTitle: textOf('[data-testid="success-title"]'),
            succDesc: textOf('[data-testid="success-desc"]'),
            quoteNo: textOf('[data-testid="quote-no-value"]'),
            copyText: textOf('.no-bar__copy-text'),
            sumTitle: textOf('[data-testid="summary-title"]'),
            labels: texts('.srow__label'),
            quoteName: textOf('.srow__value@@0'),
            envTag: textOf('[data-testid="cred-env-tag"]'),
            mask: textOf('[data-testid="cred-mask"]'),
            countChip: textOf('.count-chip__text'),
            status: textOf('[data-testid="status-chip"]'),
            modelTitle: textOf('[data-testid="model-card-title"]'),
            modelCount: textOf('[data-testid="model-count"]'),
            tagTexts: texts('.tag__text'),
            tip: textOf('[data-testid="tip"]'),
            primary: textOf('[data-testid="btn-primary"]'),
            secondary: textOf('[data-testid="btn-secondary"]')
          },
          counts: {
            cards: doc.querySelectorAll(CARDS).length,
            tags: doc.querySelectorAll('.tag').length,
            rows: doc.querySelectorAll('.srow').length,
            inputs: doc.querySelectorAll('input,textarea').length
          },
          userAgent: win.navigator.userAgent
        }
      }

"""

MAIN = r"""      async function main() {
        try {
          await waitFor('[data-testid="success-card"]')
          await sleep(1400)
          phase(1)
          if (NO_ACTION || !SCENARIO) return

          /* ?scenario=copy：复制报价单号（client-only）。
             无头 Chrome 里 navigator.clipboard 受权限限制且 click 非可信事件 → 在 iframe 内换成记录器
             （uni H5 只走 navigator.clipboard.writeText / execCommand('copy') 两条路），仍是真实页面调用链。 */
          if (SCENARIO === 'copy') {
            var w = f.contentWindow
            var rec = ''
            var execRec = ''
            try {
              Object.defineProperty(w.navigator, 'clipboard', {
                configurable: true,
                value: { writeText: function (t) { rec = String(t); return Promise.resolve() } }
              })
            } catch (e) { rec = 'PATCH_ERR:' + (e && e.message) }
            try {
              var origExec = w.document.execCommand.bind(w.document)
              w.document.execCommand = function (cmd) { execRec += cmd + ';'; return origExec(cmd) }
            } catch (e) { execRec = 'EXEC_PATCH_ERR' }
            var clickedCopy = clickIn('[data-testid="copy"]')
            await sleep(900)
            var toastCopy = toastText(f.contentDocument)
            await sleep(700)
            sink(2, {
              scenario: SCENARIO, clicked: clickedCopy, clipboardWrite: rec, execCommand: execRec,
              toast: toastCopy, hash: hashNow()
            })
            return
          }

          /* ?scenario=primary：「继续设置模型报价」→ /pages/model-pricing/index?quoteId=q9（设计：下一步为勾选模型设置单价） */
          if (SCENARIO === 'primary') {
            var hashBefore = hashNow()
            var cPri = clickIn('[data-testid="btn-primary"]')
            await waitFor('.pricing', 30)
            await sleep(1400)
            sink(2, {
              scenario: SCENARIO, clicked: cPri, hashBefore: hashBefore, hash: hashNow(),
              pricingRendered: countIn('.pricing'),
              pricingTitle: textIn('[data-testid="nav-subtitle"]'),
              toast: toastText(f.contentDocument)
            })
            return
          }

          /* ?scenario=secondary / close：两个出口同落 /pages/quotes/index（reLaunch 清栈） */
          if (SCENARIO === 'secondary' || SCENARIO === 'close') {
            var sel = SCENARIO === 'close' ? '[data-testid="close"]' : '[data-testid="btn-secondary"]'
            var hashBefore2 = hashNow()
            var cExit = clickIn(sel)
            await waitFor('.quotes', 30)
            await sleep(1400)
            sink(2, {
              scenario: SCENARIO, clicked: cExit, hashBefore: hashBefore2, hash: hashNow(),
              quotesRendered: countIn('.quotes'),
              quoteCards: countIn('[data-testid="quote-card"]'),
              toast: toastText(f.contentDocument)
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
