"""Build __measure-model-pricing.html (序号 11 · page-11) as a 430-wide iframe probe with
design-expectation checks (chk/chkR/chkC/chkList).

The helpers (splitSel / norm / normColor / normShadow / declared / el / rect / rects / css /
chk / rectField / chkR / chkC / chkList / texts / colors / textOf / groupOf / grpRss / textColors)
are lifted VERBATIM from __measure-profile.html so every probe shares exactly one implementation.
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-profile.html")
DST = os.path.join(HM, "__measure-model-pricing.html")

with io.open(SRC, encoding="utf-8") as fh:
    src = fh.read().split("\n")


def find(needle, start=0):
    for i in range(start, len(src)):
        if needle in src[i]:
            return i
    raise SystemExit("not found: " + needle)


i_var = find("var f = document.getElementById('f')")
# 只取顶部作用域（var f / acc / SCENARIO / SHOT_ONLY / NO_ACTION / splitSel），
# collect() 由本页自己定义（否则会把上一页的 collect 打开却不闭合）
i_helpers_end = find("function collect(doc, win, withChecks) {")
helpers = "\n".join(src[i_var:i_helpers_end])
helpers = helpers.replace("f.style.height = '1414px'", "f.style.height = '1541px'")

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-model-pricing</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      iframe { width: 430px; height: 900px; border: 0; }
      /* 取数用 <pre> 包在 0 尺寸 overflow:hidden 容器：textContent 可读，但不参与渲染、也不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜
         序号 11：/pages/model-pricing/index（【报价管理】模型定价-详情，page-11 ·
         帧名「11. 报价端·小程序 ｜ 【报价管理】模型定价-详情」· layer_id 46c3747b-3aca-419f-a302-22cf9de8cff8）
         设计帧重抓 2026-09-16 13:1x：design.json sha256 fcec83536a0a9c6d981f920721b93d13c1f50a37703da7c6402834ba6d1d955b
           与实现所依据的一份**逐字节相同**（cmp 报 BYTE-IDENTICAL）（无漂移）
         phase1（首屏：GET /api/v1/quotes/items/qi1）→ **设计期望值 checks 全量**
         phase2（点顶栏「保存」→ 真实 PUT /api/v1/quotes/items/qi1 → toast；请求见 serve 实收 requests-序号11-*.txt）
         phase3（勾选「缓存读取价格」→ 点底部「保存价格」→ 真实 PUT（body 含 cache_read_price））
         phase4（折叠请求规则 → 折叠提示出现；展开；新增规则组 → #2 出现；返回 → navigateBack）
         ?noaction=1 只跑 phase1（截图用）· ?shot=1 iframe 高 = 设计帧高 1541

         设计期望值（want）两类来源：
           (a) 声明值：.calicat/raw/pages/page-11/design.json（+ design.tree.json）
               python .agents/state/tree-view.py page-11          # 几何/内边距/圆角/stroke/effects/gap
               python .agents/state/text-fields.py page-11         # 全部文本叶子的 fontSize/字重/fontFill/宽高
               python .agents/state/node-probe.py page-11          # 逐节点 gap/padding/字号/文案（page-11-nodes.txt）
               python .agents/state/dump-node-fields.py page-11 <名字>   # 单节点全字段
           (b) 盒的真实边界：设计截图 PNG 实测（430×1541 =
               https://prototype-prod-1254106194.cos.ap-beijing.myqcloud.com/calicat/file/2099939149044117504/canvas/image/2099939149044117504.png；
               已存在 .agents/state/design-shots/page-11.png）复现命令（仓库根）：
                 python .agents/state/png-rowmodal.py .agents/state/design-shots/page-11.png --x0 30 --x1 400 --runs
                 python .agents/state/text-rows.py   .agents/state/design-shots/page-11.png 20 410 190 3 0 1541
                 python .agents/state/scan-col.py    .agents/state/design-shots/page-11.png 35 995 1445
                 python .agents/state/scan-col.py    .agents/state/design-shots/page-11.png 25 960 1541
           实测骨架（设计帧高 1541）：顶部导航 0..97(98) · 卡1 114..196(82) · 卡2 210..363(153) ·
             卡3 378..975(597) · 卡4 989..1447(459) · 底栏 1464..1540(76) ；卡 x16 w398 · 卡内 padding 14/16 r16
           关键模型（本页定标，与 design.json 自洽）：
             · 本页 remixicon/字形行框 ≈ fontSize × 1.1（16→17.6=媒体排版头 18 / 14→15.4=条件操作行 16 /
               24→26.4=返回图标盒 26 / 12→13.2=勾选内勾），**不是** ×1.5（×1.5 会把卡1 顶成 83、卡3 顶成 603）
             · 文本行框优先取设计**显式 height**（导航标题 24 / 副标题 14.4 / 档位标签 18 / 卡1 摘要 18 /
               单位标签行 18 / 媒体标题 15.6 / 媒体标签 14.4）
             · `effects.drop_shadow(0,4,16,rgba(15,23,42,.06))` → 卡 `box-shadow`；
               保存按钮 `drop_shadow(0,6,16,rgba(37,99,235,.28))`
             · `stroke{align:center,thickness:0.8}` → `box-shadow: 0 0 0 .8px`（border 占布局）；
               媒体勾选框的设计 stroke thickness=1 → `0 0 0 1px`
             · 分隔线 1px #F1F5F9 · 规则组 bg #F8FAFC r12 padding12 gap12
         ⚠️ 残差留痕（均 ≤1px，Figma 小数坐标链取整所致，非页面缺陷）：卡顶 114/210/377/990 vs 设计
           114.4/211.4/378.4/989；卡3 高 598 vs 597；docH 1540 vs 设计框高 1539.4（PNG 1541，含底投影 AA） -->
    <iframe id="f" src="/index.html#/pages/model-pricing/index?itemId=qi1"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

BODY = r"""
      var CARD = '.card'
      var NEED_TEXT = [
        '模型定价', '保存',
        '1', 'gpt-4o', '始终匹配（默认档位）· 输入 $2.50 输出 $10.00 / 1M token',
        '档位', '按 token', '添加计费分支',
        'Token 价格', '$/1M token',
        '输入价格', '输出价格', '缓存读取价格', '缓存写入价格', '1 小时缓存写入价格',
        '媒体定价', '图像输入价格', '图片缓存输入价格', '图像输出价格', '音频输入价格', '音频输出价格',
        '请求规则计费', '条件满足时，最终价格乘以 X；多条命中的倍率会相乘；小于 1 的值为折扣。',
        '规则组 #1', '时间', '小时', 'Asia/Shanghai', '大于等于', '值',
        '新增参数/Header', '新增时间条件', '倍率', '匹配条件时，最终费用 = 基础费用 × 倍率',
        '新增规则组', '保存价格'
      ]

      function collect(doc, win, withChecks) {
        var fails = []
        var checks = 0

        function norm(v) {
          if (typeof v === 'number') return v
          var s = String(v == null ? '' : v).trim()
          if (/^-?\d+(\.\d+)?px$/.test(s)) return Number(s.replace('px', ''))
          return s
        }
        function normColor(s) {
          var m = String(s || '').match(/rgba?\(([^)]+)\)/)
          if (!m) return String(s || '')
          var p = m[1].split(',').map(function (t) { return Number(t.trim()) })
          var a = p.length > 3 ? p[3] : 1
          return a === 1 ? 'rgb(' + p[0] + ', ' + p[1] + ', ' + p[2] + ')' : 'rgba(' + p.join(', ') + ')'
        }
        function normShadow(s) {
          return String(s == null ? '' : s).replace(/rgba?\([^)]+\)/g, function (m) { return normColor(m) })
        }
        function splitSel(sel) {
          var s = String(sel).replace(/#(\d+)(?=\s|$)/g, '@@$1')
          var i = s.indexOf('@@')
          if (i === -1) return { base: s, n: 0, tail: '' }
          var head = s.slice(0, i)
          var rest = s.slice(i + 2).split(/\s+/)
          return { base: head.trim(), n: Number(rest[0]), tail: rest.slice(1).join(' ') }
        }
        function el(sel) {
          var sp = splitSel(sel)
          if (!sp.n && !sp.tail) return doc.querySelector(sp.base)
          var roots = doc.querySelectorAll(sp.base)
          var root = roots[sp.n]
          if (!root) return null
          return sp.tail ? root.querySelector(sp.tail) : root
        }
        function resolveAll(sel) {
          var sp = splitSel(sel)
          if (!sp.n && !sp.tail) return Array.prototype.slice.call(doc.querySelectorAll(sp.base))
          var roots = doc.querySelectorAll(sp.base)
          var root = roots[sp.n]
          if (!root) return []
          if (!sp.tail) return [root]
          return Array.prototype.slice.call(root.querySelectorAll(sp.tail))
        }
        function rect(sel) {
          var e = el(sel)
          if (!e) return null
          var r = e.getBoundingClientRect()
          return {
            x: Math.round(r.x), top: Math.round(r.top), right: Math.round(r.right),
            bottom: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height)
          }
        }
        function rects(sel) {
          return resolveAll(sel).map(function (e) {
            var r = e.getBoundingClientRect()
            return { x: Math.round(r.x), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height) }
          })
        }
        function css(sel, prop) {
          var e = el(sel)
          if (!e) return null
          var v = win.getComputedStyle(e)[prop]
          if (prop === 'boxShadow') return normShadow(v)
          return prop.toLowerCase().indexOf('color') >= 0 ? normColor(v) : norm(v)
        }
        function declared(sel, prop) {
          var sp = splitSel(sel)
          if (!el(sel)) return null
          for (var i = 0; i < doc.styleSheets.length; i++) {
            var rules
            try { rules = doc.styleSheets[i].cssRules } catch (e) { continue }
            for (var j = 0; j < rules.length; j++) {
              var r = rules[j]
              if (!r.selectorText || r.selectorText.indexOf('[') === 0) continue
              var sels = r.selectorText.split(',').map(function (s) { return s.trim().replace(/\[data-v-[^\]]+\]/g, '') })
              if (sels.indexOf(sp.base) === -1) continue
              var v = r.style && r.style[prop]
              if (v) return v
            }
          }
          return null
        }
        function chk(key, got, want, tol) {
          if (!withChecks) return got
          checks++
          var t = tol == null ? 0 : tol
          var g = norm(got)
          var w = norm(want)
          var gn = typeof g === 'number' ? g : (typeof g === 'string' && /^-?\d+(\.\d+)?$/.test(g) ? Number(g) : null)
          var wn = typeof w === 'number' ? w : (typeof w === 'string' && /^-?\d+(\.\d+)?$/.test(w) ? Number(w) : null)
          var ok
          if (gn !== null && wn !== null) ok = Math.abs(gn - wn) <= t
          else ok = g === w
          if (!ok) fails.push({ k: key, got: got, want: want })
          return got
        }
        function rectField(sel, key) {
          var r = rect(sel)
          if (!r) return null
          var f = String(key).split('.').pop()
          if (f === 'x' || f === 'left') return r.x
          if (f === 'right') return r.right
          if (f === 'top') return r.top
          if (f === 'bottom') return r.bottom
          if (f === 'w' || f === 'width') return r.w
          if (f === 'h' || f === 'height') return r.h
          return r
        }
        function chkR(key, sel, want, tol) { return chk(key, rectField(sel, key), want, tol) }
        function chkC(key, sel, prop, want, tol) { return chk(key, css(sel, prop), want, tol) }
        function chkD(key, sel, prop, want) { return chk(key, declared(sel, prop), want) }
        /* 数值数组逐项比较（设计帧小数坐标链取整后会有 ±1..2 差） */
        function chkList(key, got, want, tol) {
          if (!withChecks) return got
          checks++
          var t = tol == null ? 0 : tol
          var ok = got.length === want.length
          if (ok) {
            for (var i = 0; i < got.length; i++) {
              if (got[i] == null || Math.abs(got[i] - want[i]) > t) { ok = false; break }
            }
          }
          if (!ok) fails.push({ k: key, got: got.join(','), want: want.join(',') })
          return got
        }
        /* 字符串数组逐项比较（chkList 只做数值比较，字符串会被静默放过） */
        function chkStrs(key, got, want) {
          if (!withChecks) return got
          checks++
          var ok = got.length === want.length
          if (ok) {
            for (var i = 0; i < got.length; i++) {
              if (String(got[i]) !== String(want[i])) { ok = false; break }
            }
          }
          if (!ok) fails.push({ k: key, got: got.join(' | '), want: want.join(' | ') })
          return got
        }
        function texts(sel) { return resolveAll(sel).map(function (e) { return e.textContent.trim() }) }
        function colors(sel) { return resolveAll(sel).map(function (e) { return normColor(win.getComputedStyle(e).backgroundColor) }) }
        function textOf(sel) { var e = el(sel); return e ? e.textContent.trim() : null }
        function inputValue(sel) {
          var host = el(sel)
          if (!host) return null
          if (host.tagName === 'INPUT' || host.tagName === 'TEXTAREA') return host.value
          var inner = host.querySelector('input,textarea')
          return inner ? inner.value : null
        }
        function byTestId(id) { return doc.querySelector('[data-testid="' + id + '"]') }

        /* ============ 溢出（uni-app 内置测量元素不计入，见 §3 口径） ============ */
        var over = []
        Array.prototype.slice.call(doc.querySelectorAll('*')).forEach(function (e) {
          var r = e.getBoundingClientRect()
          if (r.width <= 0 || r.right <= win.innerWidth + 0.5) return
          if (e.closest && e.closest('uni-resize-sensor')) return
          if (String(e.tagName).toLowerCase() === 'uni-resize-sensor') return
          over.push({ tag: e.tagName, cls: String(e.className || '').slice(0, 70), left: Math.round(r.x), w: Math.round(r.width), right: Math.round(r.right) })
        })
        var bodyText = (doc.body && doc.body.innerText) || ''
        var missing = NEED_TEXT.filter(function (t) { return bodyText.indexOf(t) === -1 })

        /* ===================== 整页 ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.docHeight', docH, 1539, 2) /* 设计算术 98.4+1365+76 = 1539.4（PNG 1541 含底投影 AA） */
        chkC('page.bg', '.pricing', 'backgroundColor', 'rgb(245, 247, 251)')
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chk('page.cardCount', doc.querySelectorAll(CARD).length, 4)
        chkList('page.cardTops', rects(CARD).map(function (r) { return r.top }), [114, 210, 378, 989], 2)
        chkList('page.cardHeights', rects(CARD).map(function (r) { return r.h }), [82, 153, 597, 459], 2)
        chkList('page.cardX', rects(CARD).map(function (r) { return r.x }), [16, 16, 16, 16], 1)
        chkList('page.cardW', rects(CARD).map(function (r) { return r.w }), [398, 398, 398, 398], 1)
        chkC('page.cardRadius', '.card@@0', 'borderRadius', '16px')
        chkC('page.cardBg', '.card@@0', 'backgroundColor', 'rgb(255, 255, 255)')
        /* 设计 effects：四张卡均有 drop_shadow(0,4,16,rgba(15,23,42,.06)) */
        chkC('page.card1.shadow', '.card@@0', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkC('page.card2.shadow', '.card@@1', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkC('page.card3.shadow', '.card@@2', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')
        chkC('page.card4.shadow', '.card@@3', 'boxShadow', 'rgba(15, 23, 42, 0.06) 0px 4px 16px 0px')

        /* ===================== 顶部导航（design 5e8ed34f padding[48,16,12,16]） ===================== */
        chkR('nav.h', '.pricing__nav', 98, 1) /* PNG 白行 1..97 */
        chkC('nav.padTop', '.pricing__nav', 'paddingTop', 48)
        chkC('nav.padRight', '.pricing__nav', 'paddingRight', 16)
        chkC('nav.padBottom', '.pricing__nav', 'paddingBottom', 12)
        chkC('nav.padLeft', '.pricing__nav', 'paddingLeft', 16)
        chkC('nav.bg', '.pricing__nav', 'backgroundColor', 'rgb(255, 255, 255)')
        /* 返回图标：design 3900d52a w=26 · fs=24 → 盒 26×26（fs×1.1） */
        chkR('nav.back.x', '.nav__back', 16, 1)
        chkR('nav.back.w', '.nav__back', 26, 1)
        chkR('nav.back.h', '.nav__back', 26, 1)
        chkR('nav.back.top', '.nav__back', 54, 1) /* 48 + (38.4-26)/2 */
        /* 标题块：design ac90a6cb w145 padding[0,12,0,12] */
        chkR('nav.titles.x', '.nav__titles', 42, 1) /* 16 + 26 */
        chkC('nav.titles.padLeft', '.nav__titles', 'paddingLeft', 12)
        chkR('nav.title.x', '.nav__title', 54, 1)
        chkC('nav.title.fs', '.nav__title', 'fontSize', 18)
        chkC('nav.title.fw', '.nav__title', 'fontWeight', 700) /* SourceHanSans-Bold */
        chkC('nav.title.color', '.nav__title', 'color', 'rgb(15, 23, 42)')
        chkC('nav.title.lh', '.nav__title', 'lineHeight', 24) /* design 显式 height 24 */
        chkC('nav.subtitle.fs', '.nav__subtitle', 'fontSize', 10)
        chkC('nav.subtitle.fw', '.nav__subtitle', 'fontWeight', 400)
        chkC('nav.subtitle.color', '.nav__subtitle', 'color', 'rgb(148, 163, 184)')
        chkC('nav.subtitle.lh', '.nav__subtitle', 'lineHeight', 14.4) /* design 显式 height 14.4 */
        chkC('nav.save.fs', '.nav__save', 'fontSize', 14)
        chkC('nav.save.fw', '.nav__save', 'fontWeight', 600) /* SemiBold */
        chkC('nav.save.color', '.nav__save', 'color', 'rgb(37, 99, 235)')
        chkR('nav.save.right', '.nav__save', 414, 1) /* 430 - 16 */
        chkStrs('nav.texts', [textOf('.nav__title'), textOf('.nav__subtitle'), textOf('.nav__save')], ['gpt-4o', '模型定价', '保存'])

        /* ===================== 内容区（design 66b78139 padding16 gap14） ===================== */
        chkC('body.pad', '.pricing__body', 'padding', '16px')
        chkC('body.gap', '.pricing__body', 'gap', '14px')

        /* 卡1 模型信息（ea10ef4e padding[14,16,14,16] gap 10） */
        chkC('card1.pad', '.card--info', 'padding', '14px 16px')
        chkC('card1.gap', '.card--info', 'gap', '10px')
        chkR('card1.head.h', '.info__head', 26, 1)
        chkC('card1.head.gap', '.info__head', 'gap', '10px')
        chkR('card1.badge.x', '.info__badge', 32, 1)
        chkR('card1.badge.w', '.info__badge', 26, 1)
        chkR('card1.badge.h', '.info__badge', 26, 1)
        chkC('card1.badge.radius', '.info__badge', 'borderRadius', '13px')
        chkC('card1.badge.bg', '.info__badge', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('card1.badgeText.fs', '.info__badge-text', 'fontSize', 12)
        chkC('card1.badgeText.fw', '.info__badge-text', 'fontWeight', 700)
        chkC('card1.badgeText.color', '.info__badge-text', 'color', 'rgb(255, 255, 255)')
        chkC('card1.name.fs', '.info__name', 'fontSize', 15)
        chkC('card1.name.fw', '.info__name', 'fontWeight', 700)
        chkC('card1.name.color', '.info__name', 'color', 'rgb(15, 23, 42)')
        /* 模型标题行：design 折叠箭头 e47dc806 w=20 · fs=18 → 盒 20（≤26 不然卡1 顶成 83） */
        chkR('card1.chevron.w', '.ic-chevron-up', 20, 1)
        chkR('card1.chevron.h', '.ic-chevron-up', 20, 1)
        chkR('card1.chevron.right', '.ic-chevron-up', 398, 1)
        chkR('card1.summary.top', '.info__summary', 164, 1) /* 128 + 26 + 10 */
        chkR('card1.summary.h', '.info__summary', 18, 1) /* design 显式 height 18 */
        chkC('card1.summary.fs', '.info__summary', 'fontSize', 11)
        chkC('card1.summary.fw', '.info__summary', 'fontWeight', 400)
        chkC('card1.summary.color', '.info__summary', 'color', 'rgb(100, 116, 139)')
        chkC('card1.summary.lh', '.info__summary', 'lineHeight', 18)

        /* 卡2 计费方式（7d82920c padding[14,16,14,16] gap 12） */
        chkC('card2.pad', '.card--mode', 'padding', '14px 16px')
        chkC('card2.gap', '.card--mode', 'gap', '12px')
        chkC('card2.field.gap', '.mode__field', 'gap', '7px')
        chkC('card2.label.fs', '.field__label', 'fontSize', 12)
        chkC('card2.label.fw', '.field__label', 'fontWeight', 600)
        chkC('card2.label.color', '.field__label', 'color', 'rgb(51, 65, 85)')
        chkC('card2.label.lh', '.field__label', 'lineHeight', 18) /* design 显式 height 18 */
        chkR('card2.tierBox.top', '.card--mode .box--input', 249, 2)
        chkR('card2.tierBox.h', '.card--mode .box--input', 44, 1)
        chkR('card2.tierBox.x', '.card--mode .box--input', 32, 1)
        chkR('card2.tierBox.w', '.card--mode .box--input', 366, 1)
        chkC('card2.tierBox.pad', '.card--mode .box--input', 'padding', '0px 12px')
        chkC('card2.tierBox.radius', '.card--mode .box--input', 'borderRadius', '10px')
        chkC('card2.tierBox.bg', '.card--mode .box--input', 'backgroundColor', 'rgb(248, 250, 252)')
        /* ⚠️ normShadow 会把 alpha=1 的颜色归一成 rgb(...)（Chrome 序列化口径）→ want 写 rgb(...) */
        chkC('card2.tierBox.ring', '.card--mode .box--input', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px')
        chk('card2.tierValue', inputValue('[data-testid="tier-input"]'), 'base')
        chkC('card2.tierValue.fs', '.card--mode .box__input', 'fontSize', 13)
        chkC('card2.tierValue.fw', '.card--mode .box__input', 'fontWeight', 400)
        chkC('card2.tierValue.color', '.card--mode .box__input', 'color', 'rgb(15, 23, 42)')
        chkR('card2.modeRow.top', '.mode__row', 305, 2)
        chkR('card2.modeRow.h', '.mode__row', 44, 1)
        chkC('card2.modeRow.gap', '.mode__row', 'gap', '10px')
        /* 计费方式选择框 fill_container；添加计费分支按钮 fit_content = 12+18+4+73+12 = 119 */
        chkR('card2.select.x', '.box--select', 32, 1)
        chkR('card2.select.w', '.box--select', 237, 2)
        chkR('card2.select.h', '.box--select', 44, 1)
        chkC('card2.select.text', '.box__text', 'fontSize', 13)
        chkStrs('card2.select.texts', [textOf('.box__text'), textOf('.branch__text')], ['按 token', '添加计费分支'])
        chkR('card2.branch.x', '.box--branch', 279, 2) /* 398 - 119 */
        chkR('card2.branch.w', '.box--branch', 119, 2)
        chkR('card2.branch.h', '.box--branch', 44, 1)
        chkC('card2.branch.gap', '.box--branch', 'gap', '4px')
        chkC('card2.branch.bg', '.box--branch', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('card2.branch.ring', '.box--branch', 'boxShadow', 'rgb(147, 197, 253) 0px 0px 0px 0.8px')
        chkC('card2.branchText.fs', '.branch__text', 'fontSize', 12)
        chkC('card2.branchText.fw', '.branch__text', 'fontWeight', 600)
        chkC('card2.branchText.color', '.branch__text', 'color', 'rgb(37, 99, 235)')
        chkR('card2.branchIcon.w', '.box--branch .ic', 18, 1) /* design 84b1c4b0 w=18 fs=16 */
        chkR('card2.branchIcon.h', '.box--branch .ic', 18, 1)
        chkR('card2.selectCaret.w', '.box--select .ic', 18, 1) /* design 00bedca8 w=18 fs=16 */
        chkR('card2.selectCaret.h', '.box--select .ic', 18, 1)

        /* 卡3 Token 价格 + 媒体定价（61e7d071 padding[14,16,14,16] gap 14） */
        chkC('card3.pad', '.card--price', 'padding', '14px 16px')
        chkC('card3.gap', '.card--price', 'gap', '14px')
        chkR('card3.head.h', '.price__head', 24, 1) /* 单位标签 3+18+3 */
        chkC('card3.title.fs', '.price__title', 'fontSize', 14)
        chkC('card3.title.fw', '.price__title', 'fontWeight', 700)
        chkC('card3.title.color', '.price__title', 'color', 'rgb(15, 23, 42)')
        chkR('card3.unit.right', '.unit', 398, 1)
        chkR('card3.unit.h', '.unit', 24, 1)
        chkC('card3.unit.pad', '.unit', 'padding', '3px 8px')
        chkC('card3.unit.radius', '.unit', 'borderRadius', '9px')
        chkC('card3.unit.bg', '.unit', 'backgroundColor', 'rgb(241, 245, 249)')
        chkC('card3.unitText.fs', '.unit__text', 'fontSize', 11)
        chkC('card3.unitText.fw', '.unit__text', 'fontWeight', 600)
        chkC('card3.unitText.color', '.unit__text', 'color', 'rgb(100, 116, 139)')
        chkC('card3.unitText.lh', '.unit__text', 'lineHeight', 18)
        chkStrs('card3.unit.text', [textOf('.unit__text')], ['$/1M token'])
        chkC('card3.rows.gap', '.price__rows', 'gap', '14px')
        chkC('card3.row.gap', '.price__row@@0', 'gap', '12px')
        chkC('card3.field.gap', '.price__field@@0', 'gap', '7px')
        chkList('card3.labelRowTops', rects('.card--price .price__label-row').slice(0, 5).map(function (r) { return r.top }), [429, 429, 512, 512, 595], 2)
        chkList('card3.labelRowH', rects('.card--price .price__label-row').slice(0, 5).map(function (r) { return r.h }), [18, 18, 18, 18, 18], 1)
        chkList('card3.tokenBoxTops', [0, 2, 4].map(function (i) { return rects('.card--price .box--input')[i].top }), [454, 537, 620], 2)
        chkList('card3.tokenBoxW', rects('.card--price .box--input').slice(0, 4).map(function (r) { return r.w }), [177, 177, 177, 177], 1)
        chk('card3.tokenBoxH', rects('.card--price .box--input')[0].h, 44, 1)
        chkC('card3.box.pad', '.card--price .box--input', 'padding', '0px 12px')
        chkC('card3.box.radius', '.card--price .box--input', 'borderRadius', '10px')
        chkC('card3.box.bg', '.card--price .box--input', 'backgroundColor', 'rgb(248, 250, 252)')
        chkC('card3.box.ring', '.card--price .box--input', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px')
        chkC('card3.label.fs', '.price__label', 'fontSize', 12)
        chkC('card3.label.fw', '.price__label', 'fontWeight', 600)
        chkC('card3.label.color', '.price__label', 'color', 'rgb(51, 65, 85)')
        chkC('card3.label.lh', '.price__label', 'lineHeight', 14.4)
        chkStrs('card3.tokenLabels', texts('[data-testid^="price-label-"]'),
          ['输入价格', '输出价格', '缓存读取价格', '缓存写入价格', '1 小时缓存写入价格'])
        chk('card3.checkCount', doc.querySelectorAll('.check').length, 10)
        chk('card3.checkOnCount', doc.querySelectorAll('.check--on').length, 2)
        chkR('card3.check.w', '.check@@0', 18, 1)
        chkR('card3.check.h', '.check@@0', 18, 1)
        chkC('card3.check.radius', '.check@@0', 'borderRadius', '5px')
        chkC('card3.checkOn.bg', '.check--on@@0', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('card3.checkOn.shadow', '.check--on@@0', 'boxShadow', 'none')
        chkC('card3.checkOff.bg', '.check@@2', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('card3.checkOff.ring', '.check@@2', 'boxShadow', 'rgb(203, 213, 225) 0px 0px 0px 0.8px')
        chkStrs('card3.priceValues', ['input_price', 'output_price', 'cache_read_price', 'cache_write_price', 'cache_write_1h_price', 'image_input_price'].map(function (k) {
          return inputValue('[data-testid="price-' + k + '"]')
        }), ['2.50', '10.00', '0', '0', '0', '0'])
        chkR('card3.divider.top', '.divider', 678, 2)
        chkR('card3.divider.h', '.divider', 1, 0)
        chkC('card3.divider.bg', '.divider', 'backgroundColor', 'rgb(241, 245, 249)')
        chkR('card3.mediaHead.h', '.media__head', 18, 2) /* 本页字形行框 fs16×1.1 = 17.6 */
        chkC('card3.mediaTitle.fs', '.media__title', 'fontSize', 13)
        chkC('card3.mediaTitle.fw', '.media__title', 'fontWeight', 700)
        chkC('card3.mediaTitle.color', '.media__title', 'color', 'rgb(15, 23, 42)')
        chkC('card3.mediaTitle.lh', '.media__title', 'lineHeight', 15.6) /* design 显式 height 15.6 */
        chkC('card3.mediaCols.gap', '.media__cols', 'gap', '12px')
        chkC('card3.mediaCol.gap', '.media__col@@0', 'gap', '14px')
        chkList('card3.mediaColTops', rects('.media__col').map(function (r) { return r.top }), [726, 726], 2)
        chkList('card3.mediaColX', rects('.media__col').map(function (r) { return r.x }), [32, 221], 1)
        chkList('card3.mediaColW', rects('.media__col').map(function (r) { return r.w }), [177, 177], 1)
        chkList('card3.mediaColH', rects('.media__col').map(function (r) { return r.h }), [235, 152], 2)
        chkList('card3.mediaBoxTops', rects('.media__col .box--input').map(function (r) { return r.top }), [751, 834, 917, 751, 834], 2)
        chkC('card3.mediaLabel.fs', '.media__label', 'fontSize', 12)
        chkC('card3.mediaLabel.fw', '.media__label', 'fontWeight', 600)
        chkC('card3.mediaLabel.color', '.media__label', 'color', 'rgb(51, 65, 85)')
        chkC('card3.mediaLabel.lh', '.media__label', 'lineHeight', 14.4) /* design 显式 height 14.4 */
        chkStrs('card3.mediaLabels', texts('[data-testid^="media-label-"]'),
          ['图像输入价格', '图片缓存输入价格', '图像输出价格', '音频输入价格', '音频输出价格'])
        /* 设计里媒体列勾选框 stroke thickness = 1（token 列是 0.8） */
        chkC('card3.mediaCheck.ring', '.media__col .check@@0', 'boxShadow', 'rgb(203, 213, 225) 0px 0px 0px 1px')
        chkC('card3.mediaCheck.bg', '.media__col .check@@0', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('card3.mediaCheck.radius', '.media__col .check@@0', 'borderRadius', '5px')
        /* 媒体定价头折叠箭头：design ebc25539 fs=16 → 盒 18×18 */
        chkR('card3.mediaArrow.w', '.media__head .ic', 18, 1)
        chkR('card3.mediaArrow.h', '.media__head .ic', 18, 1)
        chkR('card3.mediaArrow.right', '.media__head .ic', 398, 1)

        /* 卡4 请求规则（53b7d46b padding[14,16,14,16] gap 12） */
        chkC('card4.pad', '.card--rule', 'padding', '14px 16px')
        chkC('card4.gap', '.card--rule', 'gap', '12px')
        chkR('card4.head.h', '.rule__head', 18, 2)
        chkC('card4.headLeft.gap', '.rule__head-left', 'gap', '8px')
        chkR('card4.bar.x', '.rule__bar', 32, 1)
        chkR('card4.bar.w', '.rule__bar', 5, 1)
        chkR('card4.bar.h', '.rule__bar', 16, 1)
        chkC('card4.bar.radius', '.rule__bar', 'borderRadius', '2px')
        chkC('card4.bar.bg', '.rule__bar', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('card4.title.fs', '.rule__title', 'fontSize', 14)
        chkC('card4.title.fw', '.rule__title', 'fontWeight', 700)
        chkC('card4.title.color', '.rule__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('card4.title.text', [textOf('.rule__title')], ['请求规则计费'])
        chkR('card4.note.h', '.rule__note', 26, 3) /* 2 行（design PNG ink 1035..1060） */
        chkC('card4.note.fs', '.rule__note', 'fontSize', 11)
        chkC('card4.note.color', '.rule__note', 'color', 'rgb(148, 163, 184)')
        chk('card4.noteLines', Math.round(rect('.rule__note').h / parseFloat(win.getComputedStyle(el('.rule__note')).lineHeight)), 2)
        chkR('card4.group.top', '.rule-group', 1073, 3) /* design PNG 组底 1075..1376 */
        chkR('card4.group.h', '.rule-group', 302, 4)
        chkR('card4.group.x', '.rule-group', 32, 1)
        chkR('card4.group.w', '.rule-group', 366, 1)
        chkC('card4.group.pad', '.rule-group', 'padding', '12px')
        chkC('card4.group.radius', '.rule-group', 'borderRadius', '12px')
        chkC('card4.group.bg', '.rule-group', 'backgroundColor', 'rgb(248, 250, 252)')
        chkC('card4.group.gap', '.rule-group', 'gap', '12px')
        chkR('card4.groupHead.h', '.rule-group__head', 18, 2)
        chkC('card4.groupTitle.fs', '.rule-group__title', 'fontSize', 12)
        chkC('card4.groupTitle.fw', '.rule-group__title', 'fontWeight', 700)
        chkC('card4.groupTitle.color', '.rule-group__title', 'color', 'rgb(51, 65, 85)')
        chkStrs('card4.groupTitle.text', [textOf('.rule-group__title')], ['规则组 #1'])
        chk('card4.groupCount', doc.querySelectorAll('.rule-group').length, 1)
        chkList('card4.condTops', rects('.rule-group .box--cond').map(function (r) { return r.top }), [1116, 1116, 1168, 1168, 1220, 1301], 3)
        chkList('card4.condH', rects('.rule-group .box--cond').map(function (r) { return r.h }), [40, 40, 40, 40, 40, 40], 1)
        chkList('card4.condX', rects('.rule-group .box--cond').map(function (r) { return r.x }), [44, 220, 44, 220, 44, 78], 2)
        chkC('card4.cond.pad', '.rule-group .box--cond', 'padding', '0px 12px')
        chkC('card4.cond.radius', '.rule-group .box--cond', 'borderRadius', '9px')
        chkC('card4.cond.bg', '.rule-group .box--cond', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('card4.cond.ring', '.rule-group .box--cond', 'boxShadow', 'rgb(226, 232, 240) 0px 0px 0px 0.8px')
        chkC('card4.condText.fs', '.cond__text', 'fontSize', 12)
        chkC('card4.condText.color', '.cond__text', 'color', 'rgb(51, 65, 85)')
        chkStrs('card4.condTexts', texts('.cond__text'), ['时间', '小时', 'Asia/Shanghai', '大于等于'])
        chkC('card4.condInput.fs', '.cond__input', 'fontSize', 12)
        chkR('card4.actions.h', '.rule-group__actions', 16, 2)
        chkC('card4.actions.gap', '.rule-group__actions', 'gap', '18px')
        chkC('card4.actionText.fs', '.action__text', 'fontSize', 12)
        chkC('card4.actionText.fw', '.action__text', 'fontWeight', 600)
        chkC('card4.actionText.color', '.action__text', 'color', 'rgb(37, 99, 235)')
        chkStrs('card4.actionTexts', texts('.action__text'), ['新增参数/Header', '新增时间条件'])
        chkR('card4.multiLabel.w', '.multiplier__label', 24, 2)
        chkR('card4.multiBox.top', '.rule-group__row--multi .box--cond', 1301, 3)
        chkR('card4.multiBox.h', '.rule-group__row--multi .box--cond', 40, 1)
        chk('card4.multiValue', inputValue('[data-testid="rule-multiplier-1"]'), '1.0')
        chkC('card4.multiLabel.fs', '.multiplier__label', 'fontSize', 12)
        chkC('card4.multiLabel.fw', '.multiplier__label', 'fontWeight', 600)
        chkC('card4.multiLabel.color', '.multiplier__label', 'color', 'rgb(51, 65, 85)')
        chkC('card4.groupNote.fs', '.rule-group__note', 'fontSize', 11)
        chkC('card4.groupNote.color', '.rule-group__note', 'color', 'rgb(148, 163, 184)')
        chkStrs('card4.groupNote.text', [textOf('.rule-group__note')], ['匹配条件时，最终费用 = 基础费用 × 倍率'])
        chkR('card4.addBtn.top', '.rule__add', 1389, 3)
        chkR('card4.addBtn.h', '.rule__add', 44, 1)
        chkR('card4.addBtn.w', '.rule__add', 366, 1)
        chkC('card4.addBtn.radius', '.rule__add', 'borderRadius', '10px')
        chkC('card4.addBtn.bg', '.rule__add', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('card4.addBtn.ring', '.rule__add', 'boxShadow', 'rgb(203, 213, 225) 0px 0px 0px 0.8px')
        chkC('card4.addBtn.gap', '.rule__add', 'gap', '6px')
        chkC('card4.addText.fs', '.rule__add-text', 'fontSize', 13)
        chkC('card4.addText.fw', '.rule__add-text', 'fontWeight', 600)
        chkC('card4.addText.color', '.rule__add-text', 'color', 'rgb(37, 99, 235)')
        chk('card4.ruleHintAbsent', !!byTestId('rule-hint'), false) /* 默认展开 → 折叠提示不渲染 */
        /* 规则卡图标盒：折叠箭头 990b61af fs=16 → 18×18 · 删除 ffbcc2d6 fs=16 → 18×18 ·
           新增参数/时间 77d95bec/ef6224d5 fs=14 → 15×15 · 新增规则组 a119149b w=18 → 18×18 */
        chkR('card4.ruleArrow.w', '.rule__head .ic', 18, 1)
        chkR('card4.ruleArrow.h', '.rule__head .ic', 18, 1)
        chkR('card4.trash.w', '.ic-trash', 18, 1)
        chkR('card4.trash.h', '.ic-trash', 18, 1)
        chkR('card4.actionPlus.w', '.ic-plus-sm@@0', 15, 1)
        chkR('card4.actionPlus.h', '.ic-plus-sm@@0', 15, 1)
        chkR('card4.addPlus.w', '.rule__add .ic', 18, 1)
        chkR('card4.addPlus.h', '.rule__add .ic', 18, 1)

        /* ===================== 底部操作条（69e37d20 padding[12,16,16,16]） ===================== */
        chkR('bar.top', '.pricing__bar', 1464, 2)
        chkR('bar.h', '.pricing__bar', 76, 1)
        chkC('bar.pad', '.pricing__bar', 'padding', '12px 16px 16px')
        chkC('bar.bg', '.pricing__bar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkR('bar.save.x', '.pricing__save', 16, 1)
        chkR('bar.save.w', '.pricing__save', 398, 1)
        chkR('bar.save.h', '.pricing__save', 48, 1)
        chkC('bar.save.radius', '.pricing__save', 'borderRadius', '12px')
        chkC('bar.save.bg', '.pricing__save', 'backgroundColor', 'rgb(37, 99, 235)')
        chkC('bar.save.gap', '.pricing__save', 'gap', '6px')
        chkC('bar.save.shadow', '.pricing__save', 'boxShadow', 'rgba(37, 99, 235, 0.28) 0px 6px 16px 0px')
        chkC('bar.saveText.fs', '.pricing__save-text', 'fontSize', 15)
        chkC('bar.saveText.fw', '.pricing__save-text', 'fontWeight', 600)
        chkC('bar.saveText.color', '.pricing__save-text', 'color', 'rgb(255, 255, 255)')
        chkR('bar.saveIcon.w', '.ic-check-white', 22, 1) /* design e1e80bd3 w=22 fs=20 */
        chk('bar.tabbarAbsent', !!doc.querySelector('.tabbar'), false)

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
          nav: rect('.pricing__nav'),
          cards: rects(CARD),
          bodies: {
            card1: rect('.info__head'),
            card2: rect('.mode__row'),
            priceHead: rect('.price__head'),
            divider: rect('.divider'),
            mediaHead: rect('.media__head'),
            ruleHead: rect('.rule__head'),
            ruleNote: rect('.rule__note'),
            ruleGroup: rect('.rule-group'),
            ruleAdd: rect('.rule__add'),
            bar: rect('.pricing__bar'),
            save: rect('.pricing__save')
          },
          tests: {
            unit: rect('.unit'),
            tierBox: rect('.card--mode .box--input'),
            select: rect('.box--select'),
            branch: rect('.box--branch'),
            check: rect('.check@@0'),
            condBoxes: rects('.rule-group .box--cond'),
            mediaCols: rects('.media__col'),
            tokenBoxes: rects('.card--price .box--input'),
            iconBoxes: {
              back: rect('.nav__back'),
              chevron: rect('.ic-chevron-up'),
              caret: rect('.box--select .ic'),
              branchPlus: rect('.box--branch .ic'),
              mediaArrow: rect('.ic-chevron-up-sm@@0'),
              trash: rect('.ic-trash'),
              actionPlus: rect('.ic-plus-sm@@0'),
              addPlus: rect('.rule__add .ic'),
              saveCheck: rect('.ic-check-white')
            }
          },
          texts: {
            navTitle: textOf('.nav__title'),
            navSubtitle: textOf('.nav__subtitle'),
            navSave: textOf('.nav__save'),
            modelName: textOf('.info__name'),
            summary: textOf('.info__summary'),
            tier: inputValue('[data-testid="tier-input"]'),
            mode: textOf('.box__text'),
            branch: textOf('.branch__text'),
            unit: textOf('.unit__text'),
            tokenLabels: texts('[data-testid^="price-label-"]'),
            mediaLabels: texts('[data-testid^="media-label-"]'),
            ruleTitle: textOf('.rule__title'),
            groupTitle: textOf('.rule-group__title'),
            condTexts: texts('.cond__text'),
            actionTexts: texts('.action__text'),
            multiplier: inputValue('[data-testid="rule-multiplier-1"]'),
            groupNote: textOf('.rule-group__note'),
            addText: textOf('.rule__add-text'),
            saveText: textOf('.pricing__save-text'),
            badge: textOf('.info__badge-text')
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

      /** 载体页侧读文本（collect() 里的 textOf 是那个作用域内的，这里补一个顶层版本） */
      function textIn(sel) {
        try {
          var e = f.contentDocument.querySelector(sel)
          return e ? e.textContent.trim() : null
        } catch (err) { return 'ERR:' + err.message }
      }

      /** 轮询等待页面渲染出目标元素（uni H5 路由是异步的，固定 sleep 会踩空） */
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
          if (NO_ACTION) return

          /* phase2：顶栏「保存」→ 真实 PUT /api/v1/quotes/items/qi1（serve 实收核对） */
          await sleep(600)
          var saveTop = clickIn('[data-testid="save-top"]')
          await sleep(1500)
          sink(2, {
            clickedSaveTop: saveTop,
            toastAfterSaveTop: toastText(f.contentDocument),
            hash: hashNow()
          })

          /* phase3：勾选「缓存读取价格」→ 点底部「保存价格」→ 真实 PUT（body 含 cache_read_price） */
          var toggled = clickIn('[data-testid="check-cache_read_price"]')
          await sleep(500)
          var onCount = f.contentDocument.querySelectorAll('.check--on').length
          var saveBottom = clickIn('[data-testid="save-bottom"]')
          await sleep(1500)
          sink(3, {
            clickedCheck: toggled,
            checkOnAfterToggle: onCount,
            clickedSaveBottom: saveBottom,
            toastAfterSaveBottom: toastText(f.contentDocument),
            hash: hashNow()
          })

          /* phase4：折叠请求规则 / 新增规则组 / 返回 */
          clickIn('[data-testid="collapse-rule"]')
          await sleep(400)
          var collapsed = {
            groupsVisible: f.contentDocument.querySelectorAll('.rule-group').length,
            hintText: textIn('[data-testid="rule-hint"]'),
            addBtnVisible: !!f.contentDocument.querySelector('[data-testid="btn-add-group"]')
          }
          clickIn('[data-testid="collapse-rule"]')
          await sleep(300)
          clickIn('[data-testid="btn-add-group"]')
          await sleep(400)
          var added = Array.prototype.slice.call(f.contentDocument.querySelectorAll('[data-testid^="rule-group-title-"]')).map(function (e) { return e.textContent.trim() })
          var groupCountAfterAdd = f.contentDocument.querySelectorAll('.rule-group').length
          var back = clickIn('[data-testid="back"]')
          await sleep(700)
          sink(4, {
            collapsed: collapsed,
            groupTitlesAfterAdd: added,
            groupCountAfterAdd: groupCountAfterAdd,
            clickedBack: back,
            hashAfterBack: hashNow()
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

with io.open(DST, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(HEAD + helpers + BODY + TAIL)
print("wrote", DST)
print("helpers lines:", len(helpers.split("\n")))
