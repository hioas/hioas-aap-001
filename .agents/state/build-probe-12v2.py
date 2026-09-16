"""Build __measure-quote-apikey.html (序号 12-v2 · page-apikey) as a 430-wide iframe probe with
design-expectation checks (chk/chkR/chkC/chkD/chkList/chkStrs).

做法与 build-probe-11/12 同：从 __measure-quote-form.html（12-v1 的载体页，**同一页/同一共用组件**）
切出三段「与帧无关的骨架」（顶部作用域 / collect() helpers / 溢出统计）逐字节复用，
本文件只写 page-apikey 自己的 checks / return / phases。

want 两类来源：
  (a) 声明值 .calicat/raw/pages/page-apikey/{design.json,design.tree.json}
      python .agents/state/tree-view.py page-apikey --types all
      python .agents/state/node-probe.py page-apikey          # 全树几何/内外边距/文案
      python .agents/state/text-lineheight.py page-apikey     # 每个文本叶子 fontSize/lineHeight/宽高/字色
      python .agents/state/raw-node.py page-apikey <id前缀>   # 单节点完整 JSON（stroke/effects/cornerRadius/gap）
  (b) 设计截图 PNG 实测（430×1129，LOCALAPPDATA/Temp/design-page-apikey.png）
      python .agents/state/png-rows.py <png> v <x> <from> <to>   # 单列同色带（盒边界；可打印长度 1）
      python .agents/state/png-textbands.py <png> <x0> <y0> <x1> <y1>
      python .agents/state/stroke-rows.py <png> <rrggbb> ...

设计骨架（PNG 实测 + 设计树算术，逐条对上）：
  顶部导航 0..102（= 48 + 标题块42 + 12）· 内容区 padding[16,16,20,16] gap16
  卡1（基本信息卡）118..748（630）· 卡2（模型列表卡）764..990（226）· 底栏 1010.5..1128（117.5）
  卡1 内部锚点（链路自洽，PNG 逐点命中）：
    卡头 134..154（h20） → 容器 pt16 → 名称标签行 170..187（h17）
    → 容器 pt8 → 名称输入框 195..243（h48，PNG x=390：196 AA / 197 描边 / 198+ 底 #F8FAFC）
    → 容器 pt6 → 字数提示 249..265.5（fs11 行盒 16.5，12-v1 同口径）
    → 容器 pt16 → 分隔线1 281.5（PNG 281/282） → 容器 pt16 → 单号标签行 298.5..316.5（h18 = 标）
    → 容器 pt8 → 单号只读框 324.5..372.5（PNG 325..371 #F1F5F9）
    → 容器 pt16 → 分隔线2 388.5（PNG 388/389，x=390 同一读数法）
    → 容器 pt16 → 凭证标签行 405.5..422.5 → 容器 pt8 → 凭证选择框 430.5..478.5（PNG 431/432 蓝描边）
    → 下拉面板紧贴 478.5..704（225.5；PNG x=90：478 描边 / 480..484 面板 padding6）
        选项行三行：行1 484.5..540.5（56）· 行2 540.5..595.5（55）· 行3 595.5..650.5（55）
          （PNG x=60 图标盒：行2 550.5..584.5 · 行3 605.5..639.5；x=90 行1 选中底 #EFF6FF 486..539）
        分隔线 654.5（wrapper pt4）· 面板底描边 703/704
    → 凭证说明（wrapper pt10 + 行18 = 28）704..732 → 卡1 padding-bottom 16 → 748
  卡2 内部：卡头 780..800（h20）→ 容器 pt16 → 模型空态 815.5..974.5（158.4 = 28+56+12+20+14.4+28）
    空态标题带 916..929 · 空态说明带 933..944（12px 墨迹）→ 卡2 padding-bottom 16 → 990
  底栏：保存说明行 1022.4..1041.9（图标字形行盒 fs13×1.5 = 19.5）→ 按钮行 pt10 → 按钮 48 → padding-bottom 28

卡片效果（design 声明逐卡）：
  · 基本信息卡 519ebc84 effects drop_shadow(0,4,16,rgba(15,23,42,0.06)) → box-shadow，**无描边**
  · 模型列表卡 2491fafe 同上 effects；下拉面板 566c12d1 stroke 0.8 #2563EB + effects(0,12,24,rgba(15,23,42,0.1))
  · 底栏 600c4fc6 effects drop_shadow(0,-4,16,rgba(15,23,42,0.05)) → box-shadow

本帧与 page-26（12-v1）的差异（variantFlags，不静默统一）：
  无步骤卡 / 无「为必填项」/ 无单号说明行 / 无空态提示卡 / 无填写须知卡 /
  空态说明文案「选择凭证后将自动带出可用模型」且包裹层 pt0 / 凭证说明包裹层 pt10 / 面板展开态。
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-quote-form.html")
DST = os.path.join(HM, "__measure-quote-apikey.html")

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
i_checks = find("/* ===================== 整页")

top = "\n".join(src[i_var:i_collect])
top = top.replace("if (SHOT_ONLY) f.style.height = '1238px'", "if (SHOT_ONLY) f.style.height = '1129px'")
preamble = "\n".join(src[i_collect:i_over])          # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])           # over / missing 统计（引用 NEED_TEXT）

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-quote-apikey</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      iframe { width: 430px; height: 900px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜
         序号 12-v2：/pages/quote-form/apikey（【报价管理】新增报价单-APIKey 下拉展开，page-apikey ·
         layer_id c861ae72-865c-42b6-b314-bef4da1b2277）
         设计帧重抓 2026-09-16 14:2x：design.json sha256 29a2c80f… 与实现所依据的一份**逐字节相同**（cmp 报 BYTE-IDENTICAL，无漂移）
         phase1（首屏：面板已展开 + GET /api/v1/credentials 三选项）→ **设计期望值 checks 全量**
         ?scenario=actions → phase2（选 c2 → GET /api/v1/credentials/c2 带出 2 行模型 / 面板收起 / chip「已选 1 / 2」）
           · phase3（重开面板 → 选中行高亮 + 对勾，其余行仍显环境标）· phase3b（再点收起，回到设计帧的收起态）
           · phase4（填名称 → 保存并继续 → 真实 POST /api/v1/quotes + /quotes/q9/items → toast + 跳模型定价页）
         ?scenario=settings → phase2（点「前往「我的设置」新建凭证」→ /pages/settings/index 落地页渲染 + toast 清空）
         无 scenario/?noaction=1 → 只跑 phase1（纯测量轮）· ?shot=1 → iframe 高 = 设计帧高 1129（截图用，不跳页） -->
    <iframe id="f" src="/index.html#/pages/quote-form/apikey"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

BODY = r"""
        var CARDS = '.card'
        /* D5：图标是 CSS 绘制的占位形状 → 设计声明的「字形颜色」落在形状（多在 ::before）上；
           读元素自身的 color 只会得到 rgb(0,0,0)（那是探针口径 bug，会记到页面账上）。
           pseudo… / chkP 专门读 ::before 的声明值。 */
        function pseudoStyle(sel, prop) {
          var e = el(sel)
          if (!e) return null
          var v = win.getComputedStyle(e, '::before')[prop]
          return prop.toLowerCase().indexOf('color') >= 0 ? normColor(v) : norm(v)
        }
        function chkP(key, sel, prop, want, tol) { return chk(key, pseudoStyle(sel, prop), want, tol) }
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-apikey design.tree.json；
           图标字形层 content 为空不进清单。「2024Q3 主线路报价」「13/30」是设计帧的示例填写态，
           本实现不预填（无数据来源）→ 不进清单，登记在 designLiteralDiff） */
        var NEED_TEXT = [
          '新增报价单', '填写基本信息并设置模型报价',
          '基本信息', '报价单名称', '*',
          '请输入报价单名称，如：2024Q3 主线路报价',
          '报价单号', '系统生成', '保存后自动生成', 'QT-XXXXXXXX-XXXX',
          '凭证名称', '请选择凭证',
          '选择凭证后，系统将自动带出该凭证下可用的模型列表',
          '生产环境密钥', '常用', 'sk-prod-••••••••2f9a · 12 个模型',
          '测试环境密钥', '沙箱', 'sk-test-••••••••7b31 · 8 个模型',
          '数据标注专用', '专用', 'sk-label-••••••••a4c8 · 5 个模型',
          '前往「我的设置」新建凭证',
          '模型列表', '待带出', '尚未加载模型', '选择凭证后将自动带出可用模型',
          '保存成功后系统将自动生成报价单号', '存为草稿', '保存并继续'
        ]
__OVERFLOW__

        /* ===================== 整页（设计帧 430×1129） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 1128, 4) /* 设计帧 PNG 1129 行（0..1128）= 底栏底 1127.9 取整 */
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.qf', 'backgroundColor', 'rgb(245, 247, 251)') /* design 页面容器 c3736eb4 fills rgba(245,247,251,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 2)
        chk('page.stepCardCount', doc.querySelectorAll('.step-card').length, 0) /* 本帧无步骤卡（与 12-v1 的帧级差异） */
        chk('page.tabbarAbsent', !!doc.querySelector('.tabbar'), false)
        chk('page.noticeCardAbsent', !!doc.querySelector('[data-testid="card-notice"]'), false)
        chk('page.tipAbsent', !!doc.querySelector('[data-testid="model-empty-tip"]'), false)
        chk('page.requiredAbsent', !!doc.querySelector('[data-testid="chip-required"]'), false)
        chk('page.quoteNoHintAbsent', !!doc.querySelector('[data-testid="quote-no-hint"]'), false)
        /* PNG 实测：卡1 118..748（630）· 卡2 764..990（226.4 = 16+20+16+158.4+16） */
        chkList('page.cardTops', rects(CARDS).map(function (r) { return r.top }), [118, 764], 2)
        chkList('page.cardHeights', rects(CARDS).map(function (r) { return r.h }), [630, 226], 3)
        chk('page.gap12', rect(CARDS + '@@1').top - rect(CARDS + '@@0').bottom, 16, 1)
        chkList('page.cardX', rects(CARDS).map(function (r) { return r.x }), [16, 16], 1)
        chkList('page.cardW', rects(CARDS).map(function (r) { return r.w }), [398, 398], 1)
        chkC('page.cardPad', '.card@@0', 'padding', '16px')
        chkC('page.cardRadius', '.card@@0', 'borderRadius', '16px')
        chkC('page.cardBg', '.card@@0', 'backgroundColor', 'rgb(255, 255, 255)')
        /* design effects：基本信息卡 519ebc84 / 模型列表卡 2491fafe 均 drop_shadow(0,4,16,rgba(15,23,42,0.06))，
           两卡都**没有** stroke → 不得用 ring 顶替 */
        chkC('page.card1Shadow', '.card@@0', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkC('page.card2Shadow', '.card@@1', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkR('page.card1Head.h', '.card@@0 .card__head', 20, 1)
        chkR('page.card2Head.h', '.card@@1 .card__head', 20, 1)
        chkC('page.cardHead.gap', '.card__head@@0', 'columnGap', 8)

        /* ===================== 顶部导航（design 885c593c padding[48,16,12,16]） ===================== */
        chkR('nav.h', '.qf__nav', 102, 1) /* 48 + 标题块(24+18=42) + 12 */
        chkC('nav.pad', '.qf__nav', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.qf__nav', 'backgroundColor', 'rgb(255, 255, 255)')
        /* 顶部左侧 55f31ada gap12：组件把返回按钮与标题块并排（标题块不是左侧组的容器）→
           断「两者间距」而不是断某个容器的 columnGap（容器名口径会误伤） */
        chk('nav.left.gap', rect('.nav__title').x - rect('.nav__back').right, 12, 1)
        chkR('nav.back.x', '.nav__back', 16, 1)
        chkR('nav.back.w', '.nav__back', 36, 1)
        chkR('nav.back.h', '.nav__back', 36, 1)
        chkC('nav.back.radius', '.nav__back', 'borderRadius', '18px')
        chkC('nav.back.bg', '.nav__back', 'backgroundColor', 'rgb(241, 245, 249)')
        /* 返回字形 5854407a fs18 w20 → 盒 20×27（图标字形行盒 = 字号×1.5） */
        chkR('nav.backIcon.w', '.ic-back', 20, 1)
        chkR('nav.backIcon.h', '.ic-back', 27, 1)
        chkR('nav.title.x', '.nav__title', 64, 1) /* 16 + 36 + 12 */
        chkC('nav.title.fs', '.nav__title', 'fontSize', 18) /* d8d8d171 fs18 Bold h24 */
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700)
        chkC('nav.title.lh', '.nav__title', 'lineHeight', 24)
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('.nav__title')], ['新增报价单'])
        chkC('nav.sub.fs', '.nav__subtitle', 'fontSize', 12) /* 8862f35e fs12 #94A3B8 h18 */
        chkC('nav.sub.fw', '.nav__subtitle', 'fontWeight', 400)
        chkC('nav.sub.lh', '.nav__subtitle', 'lineHeight', 18)
        chkC('nav.sub.color', '.nav__subtitle', 'color', 'rgb(148, 163, 184)')
        chkStrs('nav.sub.text', [textOf('.nav__subtitle')], ['填写基本信息并设置模型报价'])
        chkR('nav.help.right', '.nav__help', 414, 1)
        chkR('nav.help.w', '.nav__help', 36, 1)
        chkR('nav.help.h', '.nav__help', 36, 1)
        chkC('nav.help.radius', '.nav__help', 'borderRadius', '18px')
        chkC('nav.help.bg', '.nav__help', 'backgroundColor', 'rgb(241, 245, 249)')
        chkR('nav.helpIcon.w', '.ic-help', 20, 1) /* 20286764 fs18 w20 */
        chkR('nav.helpIcon.h', '.ic-help', 27, 1)

        /* ===================== 基本信息卡 · 标题行（design 178d3faf） ===================== */
        chkR('basic.bar.w', '.card__bar', 5, 1) /* 标题竖条 030f12a2 w5 h16 r2 #2563EB */
        chkR('basic.bar.h', '.card__bar', 16, 1)
        chkC('basic.bar.radius', '.card__bar', 'borderRadius', '2px')
        chkC('basic.bar.bg', '.card__bar', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('basic.title.fs', '.card__title@@0', 'fontSize', 15) /* 63d02fa4 fs15 Bold #0F172A */
        chkC('basic.title.fw', '.card__title@@0', 'fontWeight', 700)
        chkC('basic.title.color', '.card__title@@0', 'color', 'rgb(15, 23, 42)')
        chkStrs('basic.title', [textOf('.card__title@@0')], ['基本信息'])

        /* ===================== 字段「报价单名称」 ===================== */
        chkStrs('label.texts', texts('.label__text'), ['报价单名称', '报价单号', '凭证名称'])
        chkC('label.fs', '.label__text@@0', 'fontSize', 13) /* 2a1697de fs13 SemiBold #334155 */
        chkC('label.fw', '.label__text@@0', 'fontWeight', 600)
        chkC('label.color', '.label__text@@0', 'color', 'rgb(51, 65, 85)')
        chkC('label.star.color', '.label__star@@0', 'color', 'rgb(239, 68, 68)') /* 5b8344d7 #EF4444 */
        chkC('label.star.fs', '.label__star@@0', 'fontSize', 13)
        chkList('label.rowH', rects('.label').map(function (r) { return r.h }), [17, 18, 17], 1) /* 13px 文本行盒 17；单号标签行被 18 高的「系统生成」标撑到 18 */
        chkR('name.box.top', '.input-box', 195, 2) /* PNG x=390：196 AA / 197 描边 → 盒顶 195 */
        chkR('name.box.h', '.input-box', 48, 1)
        chkR('name.box.w', '.input-box', 366, 1)
        chkC('name.box.radius', '.input-box', 'borderRadius', '12px')
        chkC('name.box.bg', '.input-box', 'backgroundColor', 'rgb(248, 250, 252)') /* 8c6c3f90 #F8FAFC */
        chkC('name.box.pad', '.input-box', 'padding', '0px 14px')
        chkC('name.box.ring', '.input-box', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px') /* stroke 0.8 center → ring */
        chk('name.box.noBorder', declared('.input-box', 'border'), null)
        chkR('name.placeholder.x', '.input-box__placeholder', 46, 1) /* 32 + 14 */
        chkC('name.placeholder.fs', '.input-box__placeholder', 'fontSize', 14)
        chkStrs('name.placeholder.text', [textOf('.input-box__placeholder')], ['请输入报价单名称，如：2024Q3 主线路报价'])
        /* 字数提示 1c5ce68d fs11 #94A3B8：页内同款 11px 行盒 16.5（12-v1 PNG 反证），右对齐到内容右界 398 */
        chkR('name.counter.h', '.counter__text', 16.5, 1)
        chkC('name.counter.fs', '.counter__text', 'fontSize', 11)
        chkC('name.counter.lh', '.counter__text', 'lineHeight', 16.5)
        chkC('name.counter.color', '.counter__text', 'color', 'rgb(148, 163, 184)')
        chkR('name.counter.right', '.counter__text', 398, 1)
        chkStrs('name.counter.text', [textOf('.counter__text')], ['0/30']) /* 不预填设计示例值「13/30」（designLiteralDiff） */
        chk('name.clearIconAbsent', !!byTestId('name-clear'), false)

        /* ===================== 分隔线（design 772431e7 / a2e78091 pad-top 16 + 1px） ===================== */
        chkList('divider.tops', rects('.divider').map(function (r) { return r.top }), [282, 389], 2) /* PNG 281/282 与 388/389 */
        chkList('divider.h', rects('.divider').map(function (r) { return r.h }), [1, 1], 0)
        chkC('divider.bg', '.divider@@0', 'backgroundColor', 'rgb(241, 245, 249)')

        /* ===================== 字段「报价单号」 ===================== */
        chkR('qno.tag.h', '.tag--blue', 18, 1) /* 系统生成标 7c9cfb60 h18 r9 #EFF6FF */
        chkC('qno.tag.radius', '.tag--blue', 'borderRadius', '9px')
        chkC('qno.tag.bg', '.tag--blue', 'backgroundColor', 'rgb(239, 246, 255)')
        chkC('qno.tag.text.fs', '.tag--blue .tag__text', 'fontSize', 10) /* d829e70b fs10 SemiBold #2563EB */
        chkC('qno.tag.text.fw', '.tag--blue .tag__text', 'fontWeight', 600)
        chkC('qno.tag.text.color', '.tag--blue .tag__text', 'color', 'rgb(37, 99, 235)')
        chkStrs('qno.tag.text', [textOf('.tag--blue .tag__text')], ['系统生成'])
        chkR('qno.box.top', '.readonly-box', 325, 2) /* PNG x=390：325..371 底 #F1F5F9 */
        chkR('qno.box.h', '.readonly-box', 48, 1)
        chkC('qno.box.radius', '.readonly-box', 'borderRadius', '12px')
        chkC('qno.box.bg', '.readonly-box', 'backgroundColor', 'rgb(241, 245, 249)') /* 02b762b6 #F1F5F9 */
        chkC('qno.box.ring', '.readonly-box', 'boxShadow', 'rgb(203, 213, 225) 0px 0px 0px 0.8px') /* stroke 0.8 #CBD5E1 */
        chkR('qno.icon.w', '.ic-doc', 18, 1) /* 4093d255 fs16 w18 → 18×24 */
        chkR('qno.icon.h', '.ic-doc', 24, 1)
        chkC('qno.iconWrap.gap', '.readonly-box__left', 'columnGap', 8) /* 单号占位 8fae17d2 gap8 */
        chkC('qno.text.fs', '.readonly-box__text', 'fontSize', 14) /* a03d8a1b fs14 Medium #94A3B8 */
        chkC('qno.text.fw', '.readonly-box__text', 'fontWeight', 500)
        chkC('qno.text.color', '.readonly-box__text', 'color', 'rgb(148, 163, 184)')
        chkStrs('qno.text', [textOf('.readonly-box__text')], ['保存后自动生成'])
        chkR('qno.pill.h', '.sample-pill', 20, 1) /* 单号示例标 96db9ba6 h20 r10 #FFFFFF */
        chkC('qno.pill.radius', '.sample-pill', 'borderRadius', '10px')
        chkC('qno.pill.bg', '.sample-pill', 'backgroundColor', 'rgb(255, 255, 255)')
        chkR('qno.pill.right', '.sample-pill', 384, 1) /* 398 − 14（设计 stroke 不占布局） */
        chkC('qno.pillText.fs', '.sample-pill__text', 'fontSize', 10) /* 106d1228 fs10 Medium #94A3B8 */
        chkC('qno.pillText.fw', '.sample-pill__text', 'fontWeight', 500)
        chkC('qno.pillText.color', '.sample-pill__text', 'color', 'rgb(148, 163, 184)')
        chkStrs('qno.pillText', [textOf('.sample-pill__text')], ['QT-XXXXXXXX-XXXX'])
        chk('qno.hintAbsent', !!byTestId('quote-no-hint'), false) /* 本帧无单号说明行 */

        /* ===================== 字段「凭证名称」· 选择框（design 2eb45208 展开态） ===================== */
        chkR('cred.select.top', '.select', 431, 2) /* PNG x=90：478 描边下沿 → 盒 430.5..478.5 */
        chkR('cred.select.h', '.select', 48, 1)
        chkC('cred.select.radius', '.select', 'borderTopLeftRadius', '12px')
        chkC('cred.select.radiusBL', '.select', 'borderBottomLeftRadius', '0px') /* cornerRadius [12,12,0,0] */
        chkC('cred.select.bg', '.select', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('cred.select.ring', '.select', 'boxShadow', 'rgb(37, 99, 235) 0px 0px 0px 0.8px') /* 展开态描边改蓝 #2563EB */
        chkR('cred.keybox.w', '.select__keybox', 28, 1) /* 钥匙图标底 47a7cae8 28×28 r8 #EFF6FF */
        chkR('cred.keybox.h', '.select__keybox', 28, 1)
        chkC('cred.keybox.radius', '.select__keybox', 'borderRadius', '8px')
        chkC('cred.keybox.bg', '.select__keybox', 'backgroundColor', 'rgb(239, 246, 255)')
        chkR('cred.keyIcon.w', '.ic-key', 17, 1) /* fd2848b0 fs15 w17 → 17×22.5 */
        chkR('cred.keyIcon.h', '.ic-key', 22.5, 1)
        chkC('cred.left.gap', '.select__left', 'columnGap', 8) /* 5fe515c3 gap8 */
        chkC('cred.value.fs', '.select__value', 'fontSize', 14) /* 324d1612 fs14 #94A3B8（展开态比 page-26 深一档） */
        chkC('cred.value.color', '.select__value', 'color', 'rgb(148, 163, 184)')
        chkStrs('cred.value', [textOf('.select__value')], ['请选择凭证'])
        chkR('cred.chevron.w', '.ic-chevron', 22, 1) /* cf6b6593 fs20 w22 → 22×30 */
        chkR('cred.chevron.h', '.ic-chevron', 30, 1)
        chkP('cred.chevron.shape', '.ic-chevron--up', 'borderBottomColor', 'rgb(37, 99, 235)') /* 展开态字形 #2563EB（D5 占位形状画在 ::before 的 border-color 上） */

        /* ===================== 下拉选项面板（design 566c12d1） ===================== */
        chkR('panel.top', '.panel', 479, 2) /* 紧贴选择框下沿 478.5，无间距 */
        chkR('panel.h', '.panel', 226, 2) /* PNG：478.5..704 = 225.5；取 225 时把 10+34+10=54 的行高写死（设计 55）→ 该检查会红 */
        chkC('panel.pad', '.panel', 'padding', '6px')
        chkC('panel.radiusTL', '.panel', 'borderTopLeftRadius', '0px') /* cornerRadius [0,0,12,12] */
        chkC('panel.radiusBL', '.panel', 'borderBottomLeftRadius', '12px')
        chkC('panel.bg', '.panel', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('panel.ring', '.panel', 'boxShadow', 'rgb(37, 99, 235) 0px 0px 0px 0.8px, rgba(15, 23, 42, 0.1) 0px 12px 24px 0px')
        chkList('row.h', rects('.panel__row').map(function (r) { return r.h }), [55, 55, 55], 1) /* 10 + max(图标盒34, 名称行19 + 副行16) + 10 */
        chkList('row.w', rects('.panel__row').map(function (r) { return r.w }), [354, 354, 354], 1) /* 面板内容宽 = 366 − 2×6（设计 stroke 不占布局） */
        chkList('row.x', rects('.panel__row').map(function (r) { return r.x }), [38, 38, 38], 1) /* 32 + 6 */
        chkList('row.pads', [css('.panel__row@@0', 'paddingTop'), css('.panel__row@@0', 'paddingLeft')], [10, 12], 0)
        chkList('row.radius', resolveAll('.panel__row').map(function (e) { return win.getComputedStyle(e).borderRadius }), ['10px', '10px', '10px'], 0)
        chkList('row.bgs', colors('.panel__row'), ['rgb(255, 255, 255)', 'rgb(255, 255, 255)', 'rgb(255, 255, 255)']) /* 未选凭证 → 三行都不高亮（设计帧把首行画成选中态，属帧内矛盾，不照抄） */
        chkList('row.iconBox.w', rects('.panel__icon').map(function (r) { return r.w }), [34, 34, 34], 1)
        chkList('row.iconBox.h', rects('.panel__icon').map(function (r) { return r.h }), [34, 34, 34], 1)
        chkC('row.iconBox.radius', '.panel__icon@@0', 'borderRadius', '10px')
        chkList('row.iconBox.bgs', colors('.panel__icon'), ['rgb(241, 245, 249)', 'rgb(241, 245, 249)', 'rgb(241, 245, 249)'])
        chkList('row.iconGlyph.bgs', colors('.ic-key-sm'), ['rgb(100, 116, 139)', 'rgb(100, 116, 139)', 'rgb(100, 116, 139)']) /* 字形 #64748B（选中行为白） */
        chkC('row.left.gap', '.panel__left@@0', 'columnGap', 12) /* c3ea0a69 gap12 */
        chkC('row.title.fs', '.panel__title@@0', 'fontSize', 14) /* ecfecae1 fs14 SemiBold #0F172A */
        chkC('row.title.fw', '.panel__title@@0', 'fontWeight', 600)
        chkC('row.title.color', '.panel__title@@0', 'color', 'rgb(15, 23, 42)')
        chkStrs('row.titles', texts('.panel__title'), ['生产环境密钥', '测试环境密钥', '数据标注专用'])
        chkR('row.recTag.h', '.rec-tag', 16, 1) /* 推荐标 797105ee h16 pad[0,6] r8 #2563EB */
        chkC('row.recTag.pad', '.rec-tag', 'padding', '0px 6px')
        chkC('row.recTag.radius', '.rec-tag', 'borderRadius', '8px')
        chkC('row.recTag.bg', '.rec-tag', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('row.recTagText.fs', '.rec-tag__text', 'fontSize', 9) /* 73297a26 fs9 SemiBold #FFFFFF */
        chkC('row.recTagText.fw', '.rec-tag__text', 'fontWeight', 600)
        chkC('row.recTagText.color', '.rec-tag__text', 'color', 'rgb(255, 255, 255)')
        chkStrs('row.recTags', texts('.rec-tag__text'), ['常用'])
        chkC('row.sub.fs', '.panel__sub@@0', 'fontSize', 11) /* 7a442214 fs11 #94A3B8 h16 */
        chkC('row.sub.color', '.panel__sub@@0', 'color', 'rgb(148, 163, 184)')
        chkStrs('row.subs', texts('.panel__sub'), [
          'sk-prod-••••••••2f9a · 12 个模型', 'sk-test-••••••••7b31 · 8 个模型', 'sk-label-••••••••a4c8 · 5 个模型'
        ])
        chkList('row.envTag.h', rects('.env-tag').map(function (r) { return r.h }), [20, 20], 1) /* 环境标 h20 pad[0,8] r10 #F1F5F9（首行是推荐标而非环境标 → 只有 2 个） */
        chkC('row.envTag.pad', '.env-tag@@0', 'padding', '0px 8px')
        chkC('row.envTag.radius', '.env-tag@@0', 'borderRadius', '10px')
        chkC('row.envTag.bg', '.env-tag@@0', 'backgroundColor', 'rgb(241, 245, 249)')
        chkC('row.envTagText.fs', '.env-tag__text@@0', 'fontSize', 10) /* 3291a0b7 fs10 Medium #64748B */
        chkC('row.envTagText.fw', '.env-tag__text@@0', 'fontWeight', 500)
        chkC('row.envTagText.color', '.env-tag__text@@0', 'color', 'rgb(100, 116, 139)')
        chkStrs('row.envTags', texts('.env-tag__text'), ['沙箱', '专用'])
        chk('row.pickedAbsent', doc.querySelectorAll('.ic-picked').length, 0) /* 未选凭证 → 无对勾（设计帧画了，属帧内矛盾） */
        chkC('panel.dividerWrap.padTop', '.panel__divider-wrap', 'paddingTop', 4)
        chkR('panel.divider.h', '.panel__divider', 1, 0)
        chkC('panel.divider.bg', '.panel__divider', 'backgroundColor', 'rgb(241, 245, 249)')
        chkC('panel.actionWrap.padTop', '.panel__action-wrap', 'paddingTop', 4)
        chkC('panel.action.pad', '.panel__action', 'padding', '8px 12px')
        chkC('panel.action.gap', '.panel__action', 'columnGap', 8)
        chkR('panel.actionIcon.w', '.ic-plus', 17, 1) /* 416214ef fs15 w17 → 17×22.5 */
        chkR('panel.actionIcon.h', '.ic-plus', 22.5, 1)
        chkC('panel.actionText.fs', '.panel__action-text', 'fontSize', 12) /* 76ff03a5 fs12 Medium #2563EB */
        chkC('panel.actionText.fw', '.panel__action-text', 'fontWeight', 500)
        chkC('panel.actionText.color', '.panel__action-text', 'color', 'rgb(37, 99, 235)')
        chkStrs('panel.actionText', [textOf('.panel__action-text')], ['前往「我的设置」新建凭证'])

        /* ===================== 凭证说明（design 5d97b44c padding-top 10） ===================== */
        chk('credHint.count', doc.querySelectorAll('.hint').length, 1) /* 本帧无单号说明行 → 全页只有 1 个 .hint */
        chkR('credHint.h', '.hint@@0', 28, 1) /* wrapper pt10 + 行 18 */
        chkR('credHint.icon.w', '.ic-info-blue', 14, 1) /* a5ee1ff1 fs12 w14 */
        chkR('credHint.icon.h', '.ic-info-blue', 18, 1)
        chkC('credHint.text.fs', '.hint__text@@0', 'fontSize', 11) /* a046a0e9 fs11 #64748B */
        chkC('credHint.text.lh', '.hint__text@@0', 'lineHeight', 16.5)
        chkC('credHint.text.color', '.hint__text@@0', 'color', 'rgb(100, 116, 139)')
        chkStrs('credHint.text', [textOf('.hint__text@@0')], ['选择凭证后，系统将自动带出该凭证下可用的模型列表'])

        /* ===================== 模型列表卡（design 2491fafe） ===================== */
        chkC('models.title.fs', '.card__title@@1', 'fontSize', 15) /* c3059e08 fs15 Bold #0F172A */
        chkC('models.title.fw', '.card__title@@1', 'fontWeight', 700)
        chkStrs('models.title', [textOf('.card__title@@1')], ['模型列表'])
        chkR('models.chip.h', '[data-testid="chip-model"]', 20, 1) /* 待带出标 dc7f75ad h20 r10 #F1F5F9 */
        chkC('models.chip.bg', '[data-testid="chip-model"]', 'backgroundColor', 'rgb(241, 245, 249)')
        chkC('models.chip.radius', '[data-testid="chip-model"]', 'borderRadius', '10px')
        chkR('models.chip.right', '[data-testid="chip-model"]', 398, 1)
        chkC('models.chipText.fs', '[data-testid="chip-model"] .tag__text', 'fontSize', 11) /* 1867a0bc fs11 Medium #94A3B8 */
        chkC('models.chipText.fw', '[data-testid="chip-model"] .tag__text', 'fontWeight', 500)
        chkC('models.chipText.color', '[data-testid="chip-model"] .tag__text', 'color', 'rgb(148, 163, 184)')
        chkStrs('models.chipText', [textOf('[data-testid="chip-model"] .tag__text')], ['待带出'])
        /* 模型空态 ab9d3251：padding[28,16,28,16] r12 bg#FAFCFF stroke0.8 #E2E8F0（PNG 815.5..974.5 = 159 ≈ 158.4） */
        chkR('empty.top', '[data-testid="model-empty"]', 816, 2)
        chkR('empty.h', '[data-testid="model-empty"]', 158, 2)
        chkC('empty.pad', '[data-testid="model-empty"]', 'padding', '28px 16px')
        chkC('empty.radius', '[data-testid="model-empty"]', 'borderRadius', '12px')
        chkC('empty.bg', '[data-testid="model-empty"]', 'backgroundColor', 'rgb(250, 252, 255)')
        chkC('empty.ring', '[data-testid="model-empty"]', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px')
        chkR('empty.icon.w', '.empty__icon', 56, 1) /* 9aa105e9 56×56 r28 #EFF6FF */
        chkR('empty.icon.h', '.empty__icon', 56, 1)
        chkC('empty.icon.radius', '.empty__icon', 'borderRadius', '28px')
        chkC('empty.icon.bg', '.empty__icon', 'backgroundColor', 'rgb(239, 246, 255)')
        chkR('empty.glyph.w', '.ic-empty', 29, 1) /* 5401c373 fs26 w29 → 29×39 */
        chkR('empty.glyph.h', '.ic-empty', 39, 1)
        chkP('empty.glyph.fill', '.ic-empty', 'backgroundColor', 'rgb(147, 197, 253)') /* 字形 #93C5FD（D5 占位形状） */
        chkR('empty.title.h', '.empty__title', 20, 1) /* 5722fab4 fs14 SemiBold #334155 h20 */
        chkC('empty.title.fs', '.empty__title', 'fontSize', 14)
        chkC('empty.title.fw', '.empty__title', 'fontWeight', 600)
        chkC('empty.title.color', '.empty__title', 'color', 'rgb(51, 65, 85)')
        chkStrs('empty.title', [textOf('.empty__title')], ['尚未加载模型'])
        chkC('empty.descWrap.padTop', '.empty__desc-wrap', 'paddingTop', 0) /* 本帧 pt0（page-26 为 pt6） */
        chkR('empty.desc.h', '.empty__desc', 14.4, 1) /* 7cab63b5 fs12 lh1.2 */
        chkC('empty.desc.fs', '.empty__desc', 'fontSize', 12)
        chkC('empty.desc.lh', '.empty__desc', 'lineHeight', 14.4)
        chkC('empty.desc.color', '.empty__desc', 'color', 'rgb(148, 163, 184)')
        chkC('empty.desc.align', '.empty__desc', 'textAlign', 'center')
        chkStrs('empty.desc', [textOf('.empty__desc')], ['选择凭证后将自动带出可用模型'])

        /* ===================== 底部操作条（design 600c4fc6 padding[12,16,28,16]） ===================== */
        chkR('bar.top', '.qf__bar', 1010, 4) /* PNG：1010.4..1128，白起 1011 */
        chkR('bar.h', '.qf__bar', 118, 2)
        chkC('bar.pad', '.qf__bar', 'padding', '12px 16px 28px')
        chkC('bar.bg', '.qf__bar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('bar.shadow', '.qf__bar', 'boxShadow', 'rgba(15, 23, 42, 0.05) 0px -4px 16px 0px')
        chkR('bar.hintIcon.w', '.ic-save-info', 15, 1) /* f0ac1b81 fs13 w15 → 15×19.5 */
        chkR('bar.hintIcon.h', '.ic-save-info', 19.5, 1)
        chkC('bar.hintText.fs', '.bar__hint-text', 'fontSize', 11) /* 759e401b fs11 #94A3B8 */
        chkC('bar.hintText.color', '.bar__hint-text', 'color', 'rgb(148, 163, 184)')
        chkStrs('bar.hintText', [textOf('.bar__hint-text')], ['保存成功后系统将自动生成报价单号'])
        chkC('bar.row.padTop', '.bar__row', 'paddingTop', 10) /* container 592c46c7 pad-top 10 */
        chkC('bar.row.gap', '.bar__row', 'columnGap', 12) /* 按钮行 618f084b gap12 */
        chkR('bar.draft.x', '.btn--ghost', 16, 1)
        chkR('bar.draft.w', '.btn--ghost', 128, 1) /* 存草稿按钮 cad1adf6 128×48 r12 stroke0.8 #E2E8F0 */
        chkR('bar.draft.h', '.btn--ghost', 48, 1)
        chkC('bar.draft.radius', '.btn--ghost', 'borderRadius', '12px')
        chkC('bar.draft.bg', '.btn--ghost', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('bar.draft.ring', '.btn--ghost', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px')
        chkC('bar.draft.fs', '.btn--ghost', 'fontSize', 14) /* d8331c53 fs14 SemiBold #64748B */
        chkC('bar.draft.fw', '.btn--ghost', 'fontWeight', 600)
        chkC('bar.draft.color', '.btn--ghost', 'color', 'rgb(100, 116, 139)')
        chkStrs('bar.draftText', [textOf('.btn--ghost')], ['存为草稿'])
        chkR('bar.save.x', '.btn--primary', 156, 1) /* 16 + 128 + 12 */
        chkR('bar.save.w', '.btn--primary', 258, 1)
        chkR('bar.save.h', '.btn--primary', 48, 1)
        chkC('bar.save.radius', '.btn--primary', 'borderRadius', '12px')
        chkC('bar.save.bg', '.btn--primary', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('bar.save.shadow', '.btn--primary', 'boxShadow', 'rgba(37, 99, 235, 0.28) 0px 6px 16px 0px') /* daa9ecd3 effects */
        chkC('bar.save.gap', '.btn--primary', 'columnGap', 8)
        chkR('bar.saveIcon.w', '.ic-save', 20, 1) /* 006a8adb fs18 w20 → 20×27 */
        chkR('bar.saveIcon.h', '.ic-save', 27, 1)
        chkC('bar.saveText.fs', '.btn__text', 'fontSize', 15) /* b4a413fd fs15 SemiBold #FFFFFF */
        chkC('bar.saveText.fw', '.btn__text', 'fontWeight', 600)
        chkC('bar.saveText.color', '.btn__text', 'color', 'rgb(255, 255, 255)')
        chkStrs('bar.saveText', [textOf('.btn__text')], ['保存并继续'])

        /* 设计帧字面量登记（不照抄的项，逐条说明；同 D3 图例百分比口径） */
        var designLiteralDiff = [
          '名称框：设计帧为示例填写态「2024Q3 主线路报价」+ 字数「13/30」（实际 12 字，设计自身不自洽）→ 不预填，字数按真实长度 0/30',
          '下拉首行：设计帧把首选项画成选中态（底 #EFF6FF + 对勾），选择框却显示占位「请选择凭证」→ 按真实选择驱动高亮/对勾',
          '「沙箱」「专用」「常用」在 22 份 PRD 零命中 → 消费服务端 env_tag / is_primary，缺字段不渲染'
        ]

        return {
          checks: checks,
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
          nav: rect('.qf__nav'),
          cards: rects(CARDS),
          cardHeads: rects('.card__head'),
          cardStyles: [css('.card@@0', 'boxShadow'), css('.card@@1', 'boxShadow')],
          nameBox: rect('.input-box'),
          counter: rect('.counter__text'),
          dividers: rects('.divider'),
          quoteNoBox: rect('.readonly-box'),
          select: rect('.select'),
          panel: rect('.panel'),
          panelRows: rects('.panel__row'),
          panelIcons: rects('.panel__icon'),
          panelDivider: rect('.panel__divider'),
          panelAction: rect('.panel__action'),
          credHint: rect('.hint@@0'),
          empty: rect('[data-testid="model-empty"]'),
          emptyIcon: rect('.empty__icon'),
          emptyTitle: rect('.empty__title'),
          emptyDesc: rect('.empty__desc'),
          bar: rect('.qf__bar'),
          draft: rect('.btn--ghost'),
          save: rect('.btn--primary'),
          iconBoxes: {
            back: rect('.ic-back'), help: rect('.ic-help'), doc: rect('.ic-doc'),
            infoBlue: rect('.ic-info-blue'), key: rect('.ic-key'), chevron: rect('.ic-chevron'),
            keySm: rect('.ic-key-sm'), picked: rect('.ic-picked'), plus: rect('.ic-plus'),
            empty: rect('.ic-empty'), saveInfo: rect('.ic-save-info'), save: rect('.ic-save')
          },
          texts: {
            navTitle: textOf('.nav__title'), navSub: textOf('.nav__subtitle'),
            cardTitles: texts('.card__title'), labels: texts('.label__text'),
            placeholder: textOf('.input-box__placeholder'), counter: textOf('.counter__text'),
            quoteNo: textOf('.readonly-box__text'), sample: textOf('.sample-pill__text'),
            credValue: textOf('.select__value'), credHint: textOf('.hint__text@@0'),
            chip: textOf('[data-testid="chip-model"] .tag__text'),
            emptyTitle: textOf('.empty__title'), emptyDesc: textOf('.empty__desc'),
            rowTitles: texts('.panel__title'), rowSubs: texts('.panel__sub'),
            recTags: texts('.rec-tag__text'), envTags: texts('.env-tag__text'),
            action: textOf('.panel__action-text'),
            barHint: textOf('.bar__hint-text'), draft: textOf('.btn--ghost'), save: textOf('.btn__text')
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
      function textIn(sel) {
        try { var e = f.contentDocument.querySelector(sel); return e ? e.textContent.trim() : null } catch (err) { return 'ERR:' + err.message }
      }
      function countIn(sel) {
        try { return f.contentDocument.querySelectorAll(sel).length } catch (err) { return -1 }
      }
      function bgsIn(sel) {
        try {
          var win = f.contentWindow
          return Array.prototype.slice.call(f.contentDocument.querySelectorAll(sel)).map(function (e) { return win.getComputedStyle(e).backgroundColor })
        } catch (err) { return ['ERR:' + err.message] }
      }

      /** uni-app H5 的 <input> 渲染成 <uni-input> 宿主 → 必须写内层原生 input 才触发 v-model */
      function typeName(value) {
        var host = f.contentDocument.querySelector('[data-testid="name-input"]')
        if (!host) return 'NOT_FOUND'
        var el = host.tagName === 'INPUT' ? host : host.querySelector('input')
        if (!el) return 'NO_NATIVE_INPUT'
        el.focus()
        el.value = value
        el.dispatchEvent(new Event('input', { bubbles: true }))
        return 'TYPED'
      }

      async function main() {
        try {
          await waitFor('[data-testid="cred-panel"]')
          await sleep(1400)
          phase(1)
          if (NO_ACTION || (SCENARIO !== 'actions' && SCENARIO !== 'settings')) return

          /* ?scenario=settings：面板底部操作「前往「我的设置」新建凭证」→ /pages/settings/index
             （台账序号 23「我的设置」**已实现**并注册在 pages.json —— 旧台账里「未实现 → hash 不变」是过期口径，本轮改正） */
          if (SCENARIO === 'settings') {
            var hashBeforeCreate = hashNow()
            var createClicked = clickIn('[data-testid="cred-create"]')
            await waitFor('[data-testid="settings-title"]')
            await sleep(900)
            sink(2, {
              clickedCreate: createClicked,
              hashBeforeCreate: hashBeforeCreate,
              hashAfterCreate: hashNow(),
              settingsTitle: textIn('[data-testid="settings-title"]'),
              settingsTitleCount: countIn('[data-testid="settings-title"]'),
              toastOnLanding: toastText(f.contentDocument)
            })
            return
          }

          /* phase2：选 c2（真实 GET /api/v1/credentials/c2）→ 面板收起 → chip「已选 1 / 2」 */
          var pick = clickIn('[data-testid="cred-option-c2"]')
          await waitFor('[data-testid="model-row-gpt-4o"]')
          await sleep(900)
          sink(2, {
            clickedOption: pick,
            panelAfterPick: countIn('[data-testid="cred-panel"]'),
            credValue: textIn('[data-testid="cred-value"]'),
            chipAfterPick: textIn('[data-testid="chip-model"] .tag__text'),
            modelRowCount: countIn('[data-testid^="model-row-"]'),
            modelRows: (function () {
              try {
                return Array.prototype.slice.call(f.contentDocument.querySelectorAll('[data-testid^="model-row-"] .model__name')).map(function (e) { return e.textContent.trim() })
              } catch (err) { return ['ERR:' + err.message] }
            })(),
            emptyStillThere: countIn('[data-testid="model-empty"]'),
            selectRing: (function () {
              try { return f.contentWindow.getComputedStyle(f.contentDocument.querySelector('.select')).boxShadow } catch (err) { return 'ERR' }
            })(),
            hash: hashNow()
          })

          /* phase3：重开面板 → 选中行高亮 + 对勾；其余行仍显环境标 */
          clickIn('[data-testid="cred-select"]')
          await waitFor('[data-testid="cred-option-c2"]')
          await sleep(700)
          sink(3, {
            panelReopened: countIn('[data-testid="cred-panel"]'),
            rowBgs: bgsIn('.panel__row'),
            iconBgs: bgsIn('.panel__icon'),
            pickedCount: countIn('.ic-picked'),
            pickedTestIds: (function () {
              try {
                return Array.prototype.slice.call(f.contentDocument.querySelectorAll('.ic-picked')).map(function (e) { return e.getAttribute('data-testid') })
              } catch (err) { return ['ERR:' + err.message] }
            })(),
            envTags: (function () {
              try {
                return Array.prototype.slice.call(f.contentDocument.querySelectorAll('.env-tag__text')).map(function (e) { return e.textContent.trim() })
              } catch (err) { return ['ERR:' + err.message] }
            })(),
            recTags: (function () {
              try {
                return Array.prototype.slice.call(f.contentDocument.querySelectorAll('.rec-tag__text')).map(function (e) { return e.textContent.trim() })
              } catch (err) { return ['ERR:' + err.message] }
            })(),
            panel: (function () {
              try {
                var r = f.contentDocument.querySelector('[data-testid="cred-panel"]').getBoundingClientRect()
                return { top: Math.round(r.top), h: Math.round(r.height) }
              } catch (err) { return null }
            })()
          })

          /* phase3 收尾：再点一次选择框收起面板，回到设计帧的「收起态」再走保存流程 */
          var closedPanel = clickIn('[data-testid="cred-select"]')
          await sleep(500)
          sink('3b', {
            clickedSelectToClose: closedPanel,
            panelAfterClose: countIn('[data-testid="cred-panel"]'),
            selectRingAfterClose: (function () {
              try { return f.contentWindow.getComputedStyle(f.contentDocument.querySelector('.select')).boxShadow } catch (err) { return 'ERR' }
            })()
          })

          /* phase4：填名称 → 保存并继续 → 真实 POST /quotes[+/q9/items] → toast + 跳模型定价页
             toast 必须在跳转前采样（1.5s 后会被 uni 收起；落地页自己的取数 toast 也会覆盖它） */
          var typed = typeName('2024Q3 主线路报价')
          await sleep(1200)
          var countText = textIn('[data-testid="name-count"]')
          var saveClick = clickIn('[data-testid="btn-save"]')
          await sleep(900)
          var toastAfterSave = toastText(f.contentDocument)
          await sleep(1500)
          sink(4, {
            typed: typed,
            countAfterType: countText,
            clickedSave: saveClick,
            toastAfterSave: toastAfterSave,
            hashAfterSave: hashNow(),
            pricingRendered: countIn('[data-testid="pricing-title"], .pricing, .mp')
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
