"""Build __measure-settings.html (序号 23 · page-23-2「【工作台与我的】我的设置 2」) as a
430-wide iframe probe with design-expectation checks (chk/chkR/chkC/chkD/chkP/chkList/chkStrs).

做法与 build-probe-10/11/12/12v2/12v3/15/20/21/22 同：从 __measure-usage.html（同族载体页，含
`resolveAll` / `declared` / `normShadow` / `pseudoStyle` 等全套 helpers）切四段「与帧无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计 / sink+phase+点击工具）逐字节复用，
本文件只写 page-23-2 自己的 checks / return / main。

want 两类来源（先量再写，不凭截图目测）：
  (a) 声明值 .calicat/raw/pages/page-23-2/{design.json,design.tree.json}
      python .agents/state/dump-layout.py page-23-2      # 全字段（padding/gap/lineHeight/stroke/effects/圆角）
      python .agents/state/text-fields.py page-23-2      # 文本叶子 fontSize/字重/字色/宽高/文案
  (b) 设计截图 PNG 实测（430×797；本轮重抓 design.json sha256 6b099f48… **逐字节相同**、
      设计 PNG 重下载 sha256 bdef9d47…（430×797）→ 无漂移）
      python .agents/state/text-rows.py design-shots/page-23-2.png 20 410
      python .agents/state/probe-23-png.py   # 卡1 投影带 / 文本墨迹色 / 水平墨迹 runs

设计骨架（逐条与 PNG 墨迹对过）：
  顶部导航 0..96（白底 padding 48/16/12/16 · 返回字形盒 26×36 @x16 · 标题盒 x54 fs17 Bold lh20.4）
  账号信息卡 108..331（223 = 20 + 标题行 27 + 16 + 30 + (12+1) + (12+30) + (12+1) + (12+30) + 20
            · padding 20 · r18 · **无描边、有 effects(0,6,20,.06)**）· 行 x36 标签列宽 87、值列 x123
            PNG 锚点：行墨迹 180..191 / 235..246 / 290..301 · 分隔线 y213 / y268 · 胶囊 123..190 · chevron 墨迹 381..384
  通知设置卡 343..519（176 = 20 + 27 + 16 + 34 + (12+1) + (12+34) + 20 · ring #EEF2F7 · 无 effects）
            行 406..440 / 465..499 · 分隔 y452 · 开关 348..394 h26（钮 368..390）· 徽标 326..394
  功能入口卡 531..717（186 = 8 + 3×56 + 2×1 + 8 · padding 8/20 · ring）行 539/596/653
            图标盒 32×32 @x36 → 标签 x78 · chevron 盒 372..394
  底部说明 717..797（80 = 24+16+16+24 · padding 24/0 居中 · 两行 11px h16）

本页定标（与 §5.12~§5.15 一致）：
  · 图标字形盒 = 设计声明宽 × 字号×1.5（返回 fs24 声明 w26 → 26×36 · 卡标题 fs18 声明 w20 → 20×27 ·
    chevron fs20 声明 w22 → 22×30 · 胶囊内对勾 fs12 声明 w14 → 14×18 · 入口图标 fs18 声明 w20 → 20×27）。
  · 文本行盒 **设计显式 height 优先**（通知卡标题 18 / 副文案 16 / 底部两行 16），无显式 height 走
    设计 `lineHeight 1.2`（13 → 15.6 · 11 → 13.2 · 17 → 20.4）；卡片标题 14 → 16.8。
  · stroke{align:center,thickness:1} → box-shadow: 0 0 0 1px（border 会占布局）· 账号信息卡只有 effects。
"""

import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-usage.html")
DST = os.path.join(HM, "__measure-settings.html")

FRAME_H = "797px"

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
    "if (SHOT_ONLY) f.style.height = '1138px' /* = 设计帧高 */",
    "if (SHOT_ONLY) f.style.height = '%s' /* = 设计帧高 */" % FRAME_H,
)
assert "'%s'" % FRAME_H in top, "SHOT 高度替换失败（顶部作用域切片变了？）"
preamble = "\n".join(src[i_collect:i_over])   # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])    # over / missing 统计（引用 NEED_TEXT / CARDS）
tail = "\n".join(src[i_sink:i_main])          # sink / phase / clickIn / toastText / hashNow / waitFor / sleep / pickers
assert "f.style.height = '1138px'" in tail, "phase() 取数高度锚变了（应把 1138 改成 797）"
tail = tail.replace("f.style.height = '1138px'", "f.style.height = '%s'" % FRAME_H)
# ⚠️ 切片坑（§5.13 同族）：若 `function bgsIn` 的收尾 `}` 与 `async function main()` 同行会丢一档；
# 本骨架里 bgsIn 收尾 `}` 单独成行（后接 pickerProbe/clickOverlayConfirm），故无需补 `}` —— 仍要复核净值 0。
assert "async function main() {" in src[i_main], "main 锚变了"
# ⚠️ modalProbe / clickAllIn 不在共享骨架里（旧版 __measure-settings.html 自带）→ 本页必须在主脚本里自带。
TOOLS = r"""
      /** uni.showModal 的 H5 覆盖层探针（退出登录二次确认） */
      function modalProbe(doc) {
        var host = doc.querySelector('uni-modal, .uni-modal, [class*="uni-modal"]')
        if (!host) return { exists: false }
        return {
          exists: true,
          text: host.textContent.replace(/\s+/g, ' ').trim().slice(0, 120),
          buttons: Array.prototype.slice.call(host.querySelectorAll('.uni-modal__btn, [class*="modal__btn"]')).map(function (e) { return e.textContent.trim() })
        }
      }
      /** 点弹窗按钮：sel 里 first/last 由调用方给（本页用 :first-child / :last-child 组合选择器） */
      function clickAllIn(sel) {
        var doc = f.contentDocument
        var els = Array.prototype.slice.call(doc.querySelectorAll(sel))
        for (var i = 0; i < els.length; i++) {
          if (els[i].getBoundingClientRect().width > 0) {
            var ev = doc.createEvent('MouseEvents')
            ev.initMouseEvent('click', true, true, f.contentWindow, 0, 0, 0, 0, 0, false, false, false, false, 0, null)
            els[i].dispatchEvent(ev)
            return 'CLICKED:' + String(els[i].className).slice(0, 60)
          }
        }
        return 'NOT_FOUND'
      }
"""

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-settings</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      /* iframe 取数高度 = 设计帧高 797：页面 min-height:100vh 会把测量高度顶到 iframe 高，
         797 时 docScrollHeight 恰好等于设计帧高（96+12+223+12+176+12+186+80 = 797）。 */
      iframe { width: 430px; height: 797px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜（uni-app 技能 §5 口径）
         页面 23：/pages/settings/index（【工作台与我的】我的设置 2，page-23-2 · layer_id 44006a8c-895d-4e5f-b507-f4559b644e06）
         设计真源：.calicat/raw/pages/page-23-2/design.tree.json（本轮重抓 design.json sha256 6b099f48… 逐字节相同；
                  设计 PNG 重下载 sha256 bdef9d47…（430×797）→ 无漂移）
         设计骨架（声明值 + 设计 PNG 430x797 实测）：
           顶部导航 0..96（白底 padding 48/16/12/16 · 返回字形盒 26×36 @x16 · 标题盒 x54 fs17 Bold）
           账号信息卡 108..331（223 · padding 20 · r18 · 无描边 + effects(0,6,20,.06)）
                       行 171/226/281(h30) · 分隔 213/268 · 胶囊 123..190 · chevron 盒 372..394
           通知设置卡 343..519（176 · padding 20 · r18 · ring #EEF2F7）
                       行 406/465(h34) · 分隔 452 · 开关 348..394(h26) · 徽标 326..394
           功能入口卡 531..717（186 · padding 8/20 · ring）行 539/596/653(h56) · 图标盒 32×32 @x36 · 标签 x78
           底部说明 717..797（80 · padding 24/0 居中 · 两行 11px h16）
         ?scenario=back|identity|legal|account|toggle|logout|logout-cancel 逐个回放出口；
         不带 scenario（或 noaction / shot=1）只取 phase1 设计期望值相 -->
    <iframe id="f" src="/index.html#/pages/settings/index"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

PRELUDE = r"""
        var CARDS = '.card'
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-23-2 design.tree.json 的
           fontSize/fontFamily/content；remixicon 字形层 content 是私有码位/空 → 不进清单）。
           值文案与 mock（api-23/v1/auth/me：phone 13812346621 / wechat_bound / sms_two_factor /
           wechat_subscribed 全 true）一致：「138 **** 6621」「已绑定」「已开启短信二次校验」「已授权」。 */
        var NEED_TEXT = [
          '账号与设置',
          '账号信息', '手机号', '138 **** 6621', '微信绑定', '已绑定', '登录安全', '已开启短信二次校验',
          '通知设置', '短信通知', '审核结果、账单与合同提醒', '微信订阅消息', '检测进度与用量周报', '已授权',
          '实名与主体信息', '服务协议与隐私政策', '退出登录',
          '云算接入平台 v1.4.2', '© 2024 保留所有权利'
        ]
"""

CHECKS = r"""
        /* ===================== 整页（设计帧 430×797） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 797, 2) /* 96 + 12 + 223 + 12 + 176 + 12 + 186 + 80 */
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.settings', 'backgroundColor', 'rgb(248, 250, 252)') /* 我的设置页 8f6ee14f fills rgba(248,250,252,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 3)
        chk('page.inputCount', doc.querySelectorAll('input,textarea').length, 0)
        chk('page.tabbarCount', doc.querySelectorAll('.tabbar').length, 0) /* 本页设计无 TabBar（由「我的 → 账号与设置」navigateTo 进入） */
        chkList('page.cardRights', rects(CARDS).map(function (r) { return r.right }), [414, 414, 414], 1)

        /* ===================== 顶部导航（design 5f81549a padding[48,16,12,16] · 白底） ===================== */
        chkR('nav.top', '.nav', 0, 1)
        chkR('nav.h', '.nav', 96, 1) /* 48 + 字形行盒 36 + 12（PNG 白底 0..95） */
        chkR('nav.w', '.nav', 430, 1)
        chkC('nav.pad', '.nav', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.nav', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('nav.align', '.nav', 'alignItems', 'center')
        chkD('nav.shadowDeclared', '.nav', 'boxShadow', null) /* 反向断言：设计顶部导航无 effects，不许补投影 */
        /* 返回字形层 a3b1c59a fs24 声明 w26 → 盒 26×36（PNG 墨迹 y 约 59..74） */
        chkR('nav.back.x', '.nav__back', 16, 1)
        chkR('nav.back.top', '.nav__back', 48, 1)
        chkR('nav.back.w', '.nav__back', 26, 1)
        chkR('nav.back.h', '.nav__back', 36, 1)
        chkR('nav.backGlyph.w', '.nav__back .glyph', 16, 1) /* 形状 16×16（D5 占位） */
        chkR('nav.backGlyph.h', '.nav__back .glyph', 16, 1)
        chkP('nav.backShape.color', '.glyph--back', 'borderLeftColor', 'rgb(51, 65, 85)') /* a3b1c59a fills rgba(51,65,85,1) */
        chk('nav.titleWrap.padLeft', css('.nav__title-wrap', 'paddingLeft'), 12) /* container 869c6ea6 padding-left 12 */
        chkR('nav.title.x', '.nav__title', 54, 1) /* 16 + 26 + 12（PNG 标题墨迹 58..73） */
        chkR('nav.title.h', '.nav__title', 20.4, 2)
        chkC('nav.title.fs', '.nav__title', 'fontSize', 17) /* ee84ab2b fs17 Bold #0F172A */
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700)
        chkC('nav.title.lh', '.nav__title', 'lineHeight', 20.4, 0.2)
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('.nav__title')], ['账号与设置'])

        /* ===================== 账号信息卡（design a2608b12 padding 20 r18 · 仅 effects，无 stroke） ===================== */
        chkR('account.x', '.card--account', 16, 1)
        chkR('account.top', '.card--account', 108, 1) /* 96 + 12（PNG 卡 108..331） */
        chkR('account.w', '.card--account', 398, 1)
        chkR('account.h', '.card--account', 223, 1) /* 20 + 27 + 16 + 30 + 13 + 12 + 30 + 13 + 12 + 30 + 20 */
        chkC('account.pad', '.card--account', 'padding', '20px')
        chkC('account.radius', '.card--account', 'borderRadius', '18px')
        chkC('account.bg', '.card--account', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('account.shadow', '.card--account', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 6px 20px 0px') /* effects drop_shadow(0,6,20)；Chrome 会补尾随 spread 0px（同序号 12/15/22 口径） */
        chkD('account.borderDeclared', '.card--account', 'border', null) /* 反向断言：本卡设计无 stroke，不许补描边 */
        chkR('account.head.top', '.card--account .card__head', 128, 1) /* 108 + 20 */
        chkR('account.head.h', '.card--account .card__head', 27, 1) /* 图标字形层 84543b9d fs18 声明 w20 → 盒 20×27 */
        chkR('account.icon.x', '.card--account .card__icon-wrap', 36, 1)
        chkR('account.icon.w', '.card--account .card__icon-wrap', 20, 1)
        chkR('account.icon.h', '.card--account .card__icon-wrap', 27, 1)
        chkC('account.icon.color', '.card--account .card__icon-wrap', 'color', 'rgb(37, 99, 235)') /* 84543b9d fills rgba(37,99,235,1) */
        chkP('account.icon.shapeColor', '.glyph--user', 'borderTopColor', 'rgb(37, 99, 235)') /* 形状用 currentColor（D5 占位） */
        chk('account.titleWrap.padLeft', css('.card--account .card__title-wrap', 'paddingLeft'), 6) /* container be48b0fb padding-left 6 */
        chkR('account.title.x', '.card--account .card__title', 62, 1) /* 36 + 20 + 6（PNG 标题墨迹 134..148） */
        chkR('account.title.h', '.card--account .card__title', 16.8, 2)
        chkC('account.title.fs', '.card--account .card__title', 'fontSize', 14) /* 02ab387b fs14 SemiBold */
        chkC('account.title.fw', '.card--account .card__title', 'fontWeight', 600)
        chkC('account.title.lh', '.card--account .card__title', 'lineHeight', 16.8, 0.2)
        chkC('account.title.color', '.card--account .card__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('account.title.text', [textOf('.card--account .card__title')], ['账号信息'])
        chk('account.rows.padTop', css('.card--account .rows', 'paddingTop'), 16) /* container d1bca590 padding-top 16 */
        chkList('account.rowTops', rects('.card--account .row').map(function (r) { return r.top }), [171, 226, 281], 1) /* 155 + 16 / 分隔 12+1+12 */
        chkList('account.rowHs', rects('.card--account .row').map(function (r) { return r.h }), [30, 30, 30], 1) /* chevron 字形盒 22×30 定行高 */
        chkList('account.labelX', rects('.card--account .row__label').map(function (r) { return r.x }), [36, 36, 36], 1)
        chkList('account.labelW', rects('.card--account .row__label').map(function (r) { return r.w }), [87, 87, 87], 1) /* 设计三行标签均声明 width 87 */
        chkList('account.labelH', rects('.card--account .row__label').map(function (r) { return r.h }), [15.6, 15.6, 15.6], 1)
        chkC('account.label.fs', '.card--account .row__label', 'fontSize', 13) /* bd6a1cb6 fs13 Regular */
        chkC('account.label.fw', '.card--account .row__label', 'fontWeight', 400)
        chkC('account.label.lh', '.card--account .row__label', 'lineHeight', 15.6, 0.2)
        chkC('account.label.color', '.card--account .row__label', 'color', 'rgb(100, 116, 139)') /* rgba(100,116,139,1) */
        chkStrs('account.labels', texts('.card--account .row__label'), ['手机号', '微信绑定', '登录安全'])
        chkR('account.value.x', '.card--account .row__value', 123, 1) /* 36 + 87（PNG 值墨迹起 126） */
        chkC('account.value.fs', '.card--account .row__value', 'fontSize', 13) /* a5075cf1 fs13 SemiBold */
        chkC('account.value.fw', '.card--account .row__value', 'fontWeight', 600)
        chkC('account.value.lh', '.card--account .row__value', 'lineHeight', 15.6, 0.2)
        chkC('account.value.color', '.card--account .row__value', 'color', 'rgb(15, 23, 42)')
        chkStrs('account.value.text', [textOf('.card--account .row__value')], ['138 **** 6621'])
        chkList('account.sepTops', rects('.card--account .row__sep').map(function (r) { return r.top }), [213, 268], 1) /* PNG 分隔线 y213 / y268 */
        chkList('account.sepHs', rects('.card--account .row__sep').map(function (r) { return r.h }), [1, 1], 0)
        chkC('account.sep.bg', '.card--account .row__sep', 'backgroundColor', 'rgb(241, 245, 249)') /* 横分隔1/2 fills rgba(241,245,249,1) */
        chk('account.sep.margin', css('.card--account .row__sep', 'marginTop'), 12) /* container padding-top 12 上下各一次 */
        chkR('account.pill.x', '.card--account .row__pill', 123, 1) /* 标签列 87 之后（PNG 胶囊 123..190） */
        chkR('account.pill.w', '.card--account .row__pill', 68, 2) /* 8 + 14 + 4 + 34 + 8（CJK 度量 → 实测 67，链算值登记） */
        chkR('account.pill.h', '.card--account .row__pill', 22, 1) /* ba0f1119 height=22 */
        chkC('account.pill.pad', '.card--account .row__pill', 'padding', '0px 8px')
        chkC('account.pill.radius', '.card--account .row__pill', 'borderRadius', '11px')
        chkC('account.pill.bg', '.card--account .row__pill', 'backgroundColor', 'rgb(236, 253, 245)') /* fills rgba(236,253,245,1) */
        chkR('account.pillIcon.w', '.card--account .row__pill-icon', 14, 1) /* b367c4b1 fs12 声明 w14 → 盒 14×18 */
        chkR('account.pillIcon.h', '.card--account .row__pill-icon', 18, 0.6)
        chk('account.pillTextWrap.padLeft', css('.card--account .row__pill-text-wrap', 'paddingLeft'), 4) /* container 1c811385 padding-left 4 */
        chkC('account.pillText.fs', '.card--account .row__pill-text', 'fontSize', 11) /* ed7794d4 fs11 Medium */
        chkC('account.pillText.fw', '.card--account .row__pill-text', 'fontWeight', 500)
        chkC('account.pillText.lh', '.card--account .row__pill-text', 'lineHeight', 13.2, 0.2)
        chkC('account.pillText.color', '.card--account .row__pill-text', 'color', 'rgb(21, 128, 61)') /* rgba(21,128,61,1) */
        chkStrs('account.pillText.text', [textOf('.card--account .row__pill-text')], ['已绑定'])
        chkC('account.pillIcon.shapeColor', '.card--account .glyph--check', 'borderLeftColor', 'rgb(22, 163, 74)') /* b367c4b1 fills rgba(22,163,74,1)；⚠️ 对勾颜色直接落在元素自身的 border 上（不是 ::before）→ 用 chkC 而非 chkP（探针口径，本轮踩到） */
        chkList('account.chevX', rects('.card--account .chevron-wrap').map(function (r) { return r.x }), [372, 372, 372], 1) /* PNG chevron 墨迹 381..384 */
        chkList('account.chevR', rects('.card--account .chevron-wrap').map(function (r) { return r.right }), [394, 394, 394], 1)
        chkList('account.chevH', rects('.card--account .chevron-wrap').map(function (r) { return r.h }), [30, 30, 30], 1)
        chkC('account.chev.color', '.card--account .glyph--chevron-right', 'borderTopColor', 'rgb(203, 213, 225)') /* 480ba848 fills rgba(203,213,225,1)；同前：形状颜色在元素自身（chkC） */

        /* ===================== 通知设置卡（design 63885808 padding 20 r18 · stroke 1px #EEF2F7） ===================== */
        chkR('notify.x', '.card--notify', 16, 1)
        chkR('notify.top', '.card--notify', 343, 1) /* 331 + 12（PNG 卡 343..519） */
        chkR('notify.w', '.card--notify', 398, 1)
        chkR('notify.h', '.card--notify', 176, 1) /* 20 + 27 + 16 + 34 + 13 + 12 + 34 + 20 */
        chkC('notify.pad', '.card--notify', 'padding', '20px')
        chkC('notify.radius', '.card--notify', 'borderRadius', '18px')
        chkC('notify.bg', '.card--notify', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('notify.ring', '.card--notify', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px') /* stroke{align:center,thickness:1} → ring（border 会占布局） */
        chkD('notify.borderDeclared', '.card--notify', 'border', null) /* 反向断言：ring 而非 border */
        chkR('notify.head.top', '.card--notify .card__head', 363, 1)
        chkR('notify.head.h', '.card--notify .card__head', 27, 1)
        chkR('notify.icon.w', '.card--notify .card__icon-wrap', 20, 1)
        chkR('notify.icon.h', '.card--notify .card__icon-wrap', 27, 1)
        chkC('notify.icon.color', '.card--notify .card__icon-wrap', 'color', 'rgb(37, 99, 235)') /* 70741131 fills rgba(37,99,235,1) */
        chkR('notify.title.x', '.card--notify .card__title', 62, 1)
        chkC('notify.title.fs', '.card--notify .card__title', 'fontSize', 14) /* fffd0153 fs14 SemiBold */
        chkC('notify.title.fw', '.card--notify .card__title', 'fontWeight', 600)
        chkC('notify.title.lh', '.card--notify .card__title', 'lineHeight', 16.8, 0.2)
        chkStrs('notify.title.text', [textOf('.card--notify .card__title')], ['通知设置'])
        chk('notify.rows.padTop', css('.card--notify .rows', 'paddingTop'), 16) /* container b698a40c padding-top 16 */
        chkList('notify.rowTops', rects('.card--notify .nrow').map(function (r) { return r.top }), [406, 465], 1) /* 390 + 16 / 分隔 12+1+12 */
        chkList('notify.rowHs', rects('.card--notify .nrow').map(function (r) { return r.h }), [34, 34], 1) /* 标题行盒 18 + 副文案行盒 16 */
        chkList('notify.titleHs', rects('.card--notify .nrow__title').map(function (r) { return r.h }), [18, 18], 1) /* 设计显式 height=18 */
        chkList('notify.descHs', rects('.card--notify .nrow__desc').map(function (r) { return r.h }), [16, 16], 1) /* 设计显式 height=16（单行） */
        chkC('notify.rowTitle.fs', '.card--notify .nrow__title', 'fontSize', 13) /* 7fb542b0 fs13 Medium */
        chkC('notify.rowTitle.fw', '.card--notify .nrow__title', 'fontWeight', 500)
        chkC('notify.rowTitle.lh', '.card--notify .nrow__title', 'lineHeight', 18)
        chkC('notify.rowTitle.color', '.card--notify .nrow__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('notify.rowTitles', texts('.card--notify .nrow__title'), ['短信通知', '微信订阅消息'])
        chkC('notify.rowDesc.fs', '.card--notify .nrow__desc', 'fontSize', 11) /* 53711655 fs11 Regular */
        chkC('notify.rowDesc.fw', '.card--notify .nrow__desc', 'fontWeight', 400)
        chkC('notify.rowDesc.lh', '.card--notify .nrow__desc', 'lineHeight', 16)
        chkC('notify.rowDesc.color', '.card--notify .nrow__desc', 'color', 'rgb(148, 163, 184)') /* rgba(148,163,184,1) */
        chkStrs('notify.rowDescs', texts('.card--notify .nrow__desc'), ['审核结果、账单与合同提醒', '检测进度与用量周报'])
        chkList('notify.sepTops', rects('.card--notify .row__sep').map(function (r) { return r.top }), [452], 1) /* PNG 分隔 y452 */
        /* 短信开关 28d7d283：46×26 r13 padding[0,4] fills rgba(37,99,235,1) · 钮 5a8b3052 22×20 r10 白 */
        var swEl = doc.querySelector('[data-testid="sms-switch"]')
        var dataOn = swEl ? swEl.getAttribute('data-on') : 'NO_SWITCH'
        chkR('switch.x', '.switch', 348, 1) /* 卡右界 414 − padding 20 − 46（PNG 开关 348..393） */
        chkR('switch.top', '.switch', 410, 1) /* 406 + (34−26)/2 */
        chkR('switch.w', '.switch', 46, 1)
        chkR('switch.h', '.switch', 26, 1)
        chkC('switch.pad', '.switch', 'padding', '0px 4px')
        chkC('switch.radius', '.switch', 'borderRadius', '13px')
        chkC('switch.bg', '.switch', 'backgroundColor', 'rgb(37, 99, 235)') /* 开态（设计帧唯一态） */
        chk('switch.dataOn', dataOn, 'true')
        chkR('switchKnob.x', '.switch__knob', 368, 1) /* 348 + 4 + (46−8−22)（PNG 钮 368..390） */
        chkR('switchKnob.w', '.switch__knob', 22, 1)
        chkR('switchKnob.h', '.switch__knob', 20, 1)
        chkC('switchKnob.radius', '.switch__knob', 'borderRadius', '10px')
        chkC('switchKnob.bg', '.switch__knob', 'backgroundColor', 'rgb(255, 255, 255)')
        /* 订阅已授权标 78f1418a（同胶囊组件）· 本行设计无 chevron */
        chkR('badge.x', '.card--notify .row__pill', 326, 2) /* PNG 徽标 326..394 */
        chkR('badge.right', '.card--notify .row__pill', 394, 1)
        chkR('badge.h', '.card--notify .row__pill', 22, 1)
        chkC('badge.bg', '.card--notify .row__pill', 'backgroundColor', 'rgb(236, 253, 245)')
        chkC('badge.text.fs', '.card--notify .row__pill-text', 'fontSize', 11) /* 9dabc505 fs11 Medium */
        chkR('badge.pillIcon.w', '.card--notify .row__pill-icon', 14, 1) /* 46f0a067 fs12 声明 w14 → 盒 14×18 */
        chkR('badge.pillIcon.h', '.card--notify .row__pill-icon', 18, 0.6)
        chkC('badge.text.color', '.card--notify .row__pill-text', 'color', 'rgb(21, 128, 61)')
        chkStrs('badge.text', [textOf('.card--notify .row__pill-text')], ['已授权'])
        chk('notify.chevCount', doc.querySelectorAll('.card--notify .chevron-wrap').length, 0) /* 本行设计为只读徽标，无 chevron */

        /* ===================== 功能入口卡（design befb43af padding 8/20 r18 · stroke 1px） ===================== */
        chkR('entries.x', '.card--entries', 16, 1)
        chkR('entries.top', '.card--entries', 531, 1) /* 519 + 12（PNG 卡 531..717） */
        chkR('entries.w', '.card--entries', 398, 1)
        chkR('entries.h', '.card--entries', 186, 1) /* 8 + 56 + 1 + 56 + 1 + 56 + 8 */
        chkC('entries.pad', '.card--entries', 'padding', '8px 20px') /* 设计 padding=[8,20,8,20] */
        chkC('entries.radius', '.card--entries', 'borderRadius', '18px')
        chkC('entries.bg', '.card--entries', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('entries.ring', '.card--entries', 'boxShadow', 'rgb(238, 242, 247) 0px 0px 0px 1px')
        chkList('entries.rowTops', rects('.card--entries .erow').map(function (r) { return r.top }), [539, 596, 653], 1) /* PNG 行 539/596/653 */
        chkList('entries.rowHs', rects('.card--entries .erow').map(function (r) { return r.h }), [56, 56, 56], 1) /* 12 + 图标盒 32 + 12 */
        chk('entries.rowPadTop', css('.card--entries .erow', 'paddingTop'), 12) /* 入口1 padding=[12,0,12,0] */
        chkList('entries.iconX', rects('.card--entries .erow__icon').map(function (r) { return r.x }), [36, 36, 36], 1) /* PNG 图标盒 36..67 */
        chkList('entries.iconW', rects('.card--entries .erow__icon').map(function (r) { return r.w }), [32, 32, 32], 1)
        chkList('entries.iconH', rects('.card--entries .erow__icon').map(function (r) { return r.h }), [32, 32, 32], 1)
        chkC('entries.icon.radius', '.card--entries .erow__icon', 'borderRadius', '10px') /* 入口图标 cornerRadius=10 */
        chkStrs('entries.iconBgs', colors('.card--entries .erow__icon'), ['rgb(239, 246, 255)', 'rgb(241, 245, 249)', 'rgb(254, 242, 242)'])
        chkStrs('entries.iconColors', textColors('.card--entries .erow__icon'), ['rgb(37, 99, 235)', 'rgb(100, 116, 139)', 'rgb(220, 38, 38)'])
        chkList('entries.glyphW', rects('.card--entries .glyph-wrap').map(function (r) { return r.w }), [20, 20, 20], 1) /* 字形层 fs18 声明 w20 → 盒 20×27 */
        chkList('entries.glyphH', rects('.card--entries .glyph-wrap').map(function (r) { return r.h }), [27, 27, 27], 1)
        chk('entries.textWrap.padLeft', css('.card--entries .erow__text-wrap', 'paddingLeft'), 10) /* container 04a750c4 padding-left 10 */
        chkList('entries.labelX', rects('.card--entries .erow__label').map(function (r) { return r.x }), [78, 78, 78], 1) /* 36 + 32 + 10（PNG 标签墨迹起 79） */
        chkList('entries.labelTops', rects('.card--entries .erow__label').map(function (r) { return r.top }), [559, 617, 674], 2) /* PNG 墨迹 559..574 / 617..631 / 674..688 */
        chkList('entries.labelHs', rects('.card--entries .erow__label').map(function (r) { return r.h }), [15.6, 15.6, 15.6], 1)
        chkC('entries.label.fs', '.card--entries .erow__label', 'fontSize', 13) /* 4af4f5ab fs13 Medium */
        chkC('entries.label.fw', '.card--entries .erow__label', 'fontWeight', 500)
        chkC('entries.label.lh', '.card--entries .erow__label', 'lineHeight', 15.6, 0.2)
        chkStrs('entries.labels', texts('.card--entries .erow__label'), ['实名与主体信息', '服务协议与隐私政策', '退出登录'])
        chkStrs('entries.labelColors', textColors('.card--entries .erow__label'), ['rgb(15, 23, 42)', 'rgb(15, 23, 42)', 'rgb(220, 38, 38)']) /* 入口3 d44c88e2 rgba(220,38,38,1) */
        chkStrs('entries.tones', resolveAll('.card--entries .erow').map(function (e) { return e.getAttribute('data-tone') }), ['primary', 'neutral', 'danger'])
        chkList('entries.sepTops', rects('.card--entries .entry__sep').map(function (r) { return r.top }), [595, 652], 1) /* 539+56 / 653−1 */
        chkList('entries.sepHs', rects('.card--entries .entry__sep').map(function (r) { return r.h }), [1, 1], 0)
        chkC('entries.sep.bg', '.card--entries .entry__sep', 'backgroundColor', 'rgb(241, 245, 249)') /* 横分隔4/5 fills rgba(241,245,249,1) */
        chkList('entries.chevX', rects('.card--entries .chevron-wrap').map(function (r) { return r.x }), [372, 372, 372], 1)
        chkList('entries.chevR', rects('.card--entries .chevron-wrap').map(function (r) { return r.right }), [394, 394, 394], 1)
        chk('entries.chevCount', doc.querySelectorAll('.card--entries .chevron-wrap').length, 3) /* 入口三行均有 chevron（与通知卡徽标行不同） */

        /* ===================== 底部说明（design 6c196387 padding[24,0,24,0] 居中 · 两行 11px h16） ===================== */
        chkR('footer.top', '.footer', 717, 1) /* PNG 底部区 717..797 */
        chkR('footer.h', '.footer', 80, 2)
        chkC('footer.pad', '.footer', 'padding', '24px 0px')
        chkC('footer.align', '.footer', 'alignItems', 'center')
        chkC('footer.direction', '.footer', 'flexDirection', 'column')
        chkR('footer.version.top', '.footer__version', 741, 1) /* PNG 第一行墨迹 744..753 */
        chkR('footer.version.h', '.footer__version', 16, 1) /* 673ad504 fs11 显式 h16 */
        chkC('footer.version.fs', '.footer__version', 'fontSize', 11)
        chkC('footer.version.fw', '.footer__version', 'fontWeight', 400)
        chkC('footer.version.lh', '.footer__version', 'lineHeight', 16)
        chkC('footer.version.color', '.footer__version', 'color', 'rgb(148, 163, 184)') /* rgba(148,163,184,1) */
        chkStrs('footer.version.text', [textOf('.footer__version')], ['云算接入平台 v1.4.2'])
        chkR('footer.copyright.top', '.footer__copyright', 757, 1)
        chkR('footer.copyright.h', '.footer__copyright', 16, 1) /* f3df102e fs11 显式 h16 */
        chkC('footer.copyright.fs', '.footer__copyright', 'fontSize', 11) /* fs11 rgba(203,213,225,1) */
        chkC('footer.copyright.lh', '.footer__copyright', 'lineHeight', 16)
        chkC('footer.copyright.color', '.footer__copyright', 'color', 'rgb(203, 213, 225)')
        chkStrs('footer.copyright.text', [textOf('.footer__copyright')], ['© 2024 保留所有权利'])

        /* 设计帧字面量登记（不照抄/派生项，逐条说明） */
        var designLiteralDiff = [
          '账号信息卡只有 effects drop_shadow(0,6,20,rgba(15,23,42,.06))、无 stroke；通知设置卡 / 功能入口卡只有 stroke(#EEF2F7)、无 effects → 逐卡断言，不统一（PNG 实测：卡1 下方 12px 间隙最暗 241 有投影带，卡2 下方间隙 = 页面底色 248,250,252）',
          '卡片描边用 ring（盒外 1px）→ 可见描边行比设计中心描边（跨边各半）外移 0.5px（卡内容盒与设计逐值相等）',
          '短信通知开关：设计帧只给「开」态（#2563EB），关态色设计未给 → 用中性 #CBD5E1 占位（台账备注④，client-only 无接口依据 missing-prd）',
          '「审核结果、账单与合同提醒」设计声明容器宽 132（11px × 13 字 = 143）→ 实现按 flex:none 单行渲染（设计帧该行同样是单行，行高 34 自洽）；未写死 132',
          '图标为 CSS 绘制占位形状（决策 D5：不引入图标字体库，R-26 禁 emoji）→ 返回箭头墨迹 16 宽、卡片人像/铃铛/盾牌/文档/门 16×16，形状近似非真实 remixicon 字形',
          '账号信息三行（手机号 / 微信绑定 / 登录安全）设计帧有 chevron，但画布 30 页无对应页 → 点击 no-op（不跳转、不弹占位 toast、不臆造路由，台账待拍板）',
          '「服务协议与隐私政策」同样无画布页且 PRD 无外链地址 → 无落点（不臆造 URL，台账待拍板）',
          '退出登录二次确认弹窗文案（「退出登录 / 确认退出当前账号？退出后需重新登录。」）设计帧无弹窗稿 → 占位（同序号 8「删除」口径）',
          '页面数据来自 GET /api/v1/auth/me（mock api-23）；响应字段级 schema 18-API 未定义 → 手机号/微信绑定/登录安全/订阅授权逐字段容错读取，缺字段渲染「—」不冒充状态（台账备注②③）'
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
          account: rect('.card--account'),
          accountHead: rect('.card--account .card__head'),
          accountRows: rects('.card--account .row'),
          accountLabels: rects('.card--account .row__label'),
          accountSeps: rects('.card--account .row__sep'),
          accountPill: rect('.card--account .row__pill'),
          accountChevrons: rects('.card--account .chevron-wrap'),
          notify: rect('.card--notify'),
          notifyRows: rects('.card--notify .nrow'),
          notifySeps: rects('.card--notify .row__sep'),
          switch: rect('.switch'),
          switchKnob: rect('.switch__knob'),
          badge: rect('.card--notify .row__pill'),
          entries: rect('.card--entries'),
          entryRows: rects('.card--entries .erow'),
          entryIcons: rects('.card--entries .erow__icon'),
          entryLabels: rects('.card--entries .erow__label'),
          entrySeps: rects('.card--entries .entry__sep'),
          entryChevrons: rects('.card--entries .chevron-wrap'),
          footer: rect('.footer'),
          footerVersion: rect('.footer__version'),
          footerCopyright: rect('.footer__copyright'),
          texts: {
            navTitle: textOf('.nav__title'),
            accountTitle: textOf('.card--account .card__title'),
            accountLabels: texts('.card--account .row__label'),
            accountValue: textOf('.card--account .row__value'),
            accountPillText: textOf('.card--account .row__pill-text'),
            notifyTitle: textOf('.card--notify .card__title'),
            notifyTitles: texts('.card--notify .nrow__title'),
            notifyDescs: texts('.card--notify .nrow__desc'),
            badgeText: textOf('.card--notify .row__pill-text'),
            entryLabels: texts('.card--entries .erow__label'),
            footerVersion: textOf('.footer__version'),
            footerCopyright: textOf('.footer__copyright')
          },
          state: {
            /* 开关本地态（client-only，无接口）：toggle 相 before/after 对比用 */
            switchDataOn: (doc.querySelector('[data-testid="sms-switch"]') || { getAttribute: function () { return null } }).getAttribute('data-on'),
            switchBg: css('.switch', 'backgroundColor'),
            hash: String(win.location.hash)
          },
          counts: {
            cards: doc.querySelectorAll(CARDS).length,
            accountRows: doc.querySelectorAll('.card--account .row').length,
            accountChevrons: doc.querySelectorAll('.card--account .chevron-wrap').length,
            notifyRows: doc.querySelectorAll('.card--notify .nrow').length,
            notifyChevrons: doc.querySelectorAll('.card--notify .chevron-wrap').length,
            switches: doc.querySelectorAll('.switch').length,
            entryRows: doc.querySelectorAll('.card--entries .erow').length,
            entryChevrons: doc.querySelectorAll('.card--entries .chevron-wrap').length,
            tabbar: doc.querySelectorAll('.tabbar').length,
            inputs: doc.querySelectorAll('input,textarea').length
          },
          userAgent: win.navigator.userAgent
        }
      }
"""

MAIN = r"""
      async function main() {
        try {
          await waitFor('[data-testid="account-title"]')
          await sleep(1600)
          phase(1)
          if (NO_ACTION || !SCENARIO || SHOT_ONLY) return

          /* ?scenario=back：返回 = navigation（navigateBack；H5 直接进入本页时栈内无上一页）→ hash 不变 + 无 toast + 零写请求 */
          if (SCENARIO === 'back') {
            var cB = clickIn('[data-testid="settings-back"]')
            await sleep(1500)
            sink(2, {
              scenario: SCENARIO, clicked: cB,
              hash: hashNow(),
              toast: toastText(f.contentDocument),
              cardCount: countIn('.card')
            })
            return
          }

          /* ?scenario=identity：功能入口「实名与主体信息」→ navigation /pages/profile/index（序号 10.1 已实现） */
          if (SCENARIO === 'identity') {
            var cI = clickIn('[data-testid="row-identity"]')
            await sleep(1800)
            sink(2, {
              scenario: SCENARIO, clicked: cI,
              hash: hashNow(),
              landedTitle: textIn('.profile__title') || textIn('.nav__title'),
              toast: toastText(f.contentDocument)
            })
            return
          }

          /* ?scenario=legal：功能入口「服务协议与隐私政策」无画布页 / PRD 无外链 → 无落点（no-op） */
          if (SCENARIO === 'legal') {
            var cL = clickIn('[data-testid="row-legal"]')
            await sleep(1500)
            sink(2, { scenario: SCENARIO, clicked: cL, hash: hashNow(), toast: toastText(f.contentDocument) })
            return
          }

          /* ?scenario=account：账号信息行有 chevron 但画布无对应页 → 无落点（no-op：不跳转、不弹 toast） */
          if (SCENARIO === 'account') {
            var cA = clickIn('[data-testid="account-row"]')
            await sleep(1500)
            sink(2, { scenario: SCENARIO, clicked: cA, hash: hashNow(), toast: toastText(f.contentDocument) })
            return
          }

          /* ?scenario=toggle：短信通知开关 = client-only（只改本地态，18-API 无 /settings 端点 → 不发请求） */
          if (SCENARIO === 'toggle') {
            var before = collect(f.contentDocument, f.contentWindow, false)
            var cT = clickIn('[data-testid="sms-switch"]')
            await sleep(1200)
            var after = collect(f.contentDocument, f.contentWindow, false)
            sink(2, {
              scenario: SCENARIO, clicked: cT,
              before: before.state.switchDataOn,
              after: after.state.switchDataOn,
              beforeBg: before.state.switchBg,
              afterBg: after.state.switchBg,
              hash: hashNow()
            })
            return
          }

          /* ?scenario=logout / logout-cancel：功能入口「退出登录」→ uni-modal 二次确认 → api POST /auth/logout → reLaunch 登录页 */
          if (SCENARIO === 'logout' || SCENARIO === 'logout-cancel') {
            var cO = clickIn('[data-testid="row-logout"]')
            await sleep(1200)
            var modal = modalProbe(f.contentDocument)
            var answer = SCENARIO === 'logout'
              ? clickAllIn('.uni-modal__btn:last-child, [class*="modal__btn"]:last-child')
              : clickAllIn('.uni-modal__btn:first-child, [class*="modal__btn"]:first-child')
            await sleep(2200)
            sink(2, {
              scenario: SCENARIO, clicked: cO,
              modal: modal, answered: answer,
              hash: hashNow(),
              toast: toastText(f.contentDocument),
              hashBefore: null
            })
            return
          }
        } catch (e) {
          sink('error', { message: String(e && e.message), stack: String((e && e.stack) || '').slice(0, 600) })
        }
      }

      main()
"""

out = HEAD + top + "\n" + preamble + PRELUDE + overflow + CHECKS + tail + TOOLS + MAIN + "\n    </script>\n  </body>\n</html>\n"
with io.open(DST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(out)
print("wrote", DST, len(out), "chars,", out.count("\n") + 1, "lines")
