"""Build __measure-messages.html (序号 20 · page-20-2「【合同与通知】站内信列表 2」) as a
430-wide iframe probe with design-expectation checks (chk/chkR/chkC/chkD/chkList/chkStrs).

做法与 build-probe-10/11/12/12v2/12v3/15 同：从 __measure-contract.html（同族载体页，含
`resolveAll` / `declared` / `normShadow` / `pseudoStyle` 等全套 helpers）切四段「与帧无关的骨架」
（顶部作用域 / collect() helpers / 溢出统计 / sink+phase+点击工具）逐字节复用，
本文件只写 page-20-2 自己的 checks / return / main。

want 两类来源（先量再写，不凭截图目测）：
  (a) 声明值 .calicat/raw/pages/page-20-2/{design.json,design.tree.json}
      python .agents/state/dump-layout.py page-20-2      # 全字段（padding/gap/lineHeight/stroke/effects/圆角）
      python .agents/state/text-fields.py page-20-2      # 文本叶子 fontSize/字重/字色/宽高/文案
  (b) 设计截图 PNG 实测（430×760，本轮重抓 PNG sha256 b1398fdd… 与建页时同）
      python .agents/state/png-rows.py <png> v 5 0 760 2            # 导航/列表/TabBar 底色带
      python .agents/state/png-colorat.py <png> h 110 2563EB 20 5   # chip 横边界
      python .agents/state/stroke-rows.py <png> eef2f7 6 150 20 410 140 700   # 5 张卡上下边界
      python .agents/state/ink-runs.py <png> 320 420 45 76          # 「全部已读」图标/文字墨迹
      python .agents/state/png-textbands.py <png> 82 150 400 250    # 卡内标题/摘要/时间行墨迹

设计骨架（逐条与 PNG 墨迹对过）：
  顶部导航 0..86（padding 48/16/12/16 · 内容行 26 = 标题 fs20 行盒；PNG 标题墨迹 50..71）
  筛选行 86..140（padding 12/16 + chip 30；PNG chip 98..128）
  消息列表区 140..660（padding-top 12 · 5 卡 × 92 @152/256/360/464/568 · 间隙 12）
  卡内：图标 38×38 r12 @x32 · 内容列 padding-left 12 · 标题行 18 + 4 + 摘要 18 + 4 + 时间 16 = 60
        （PNG 卡1 墨迹：标题 170..183 / 摘要 193..205 / 时间 214..224）
  底部 TabBar 676..760（外包裹 padding-top 16 + 栏 84 = 8 + 图标块 33 + 3 + 文字 16 + 24）
        （PNG 图标墨迹 691..710 · 文字墨迹 722..732；4 项各 104 · space_between）
  ?scenario=guard|filter|readall|card|tab 逐个回放出口；不带 scenario（或 noaction）只取 phase1 设计期望值相。

本页定标：
  · 图标字形行盒 = 字号 × 1.5（fs20 → 盒 22×30(=声明宽 22 × 20×1.5) · fs16 → 盒 18×24）；形状画在盒内（D5）。
  · 文本行盒：显式 height 优先（摘要 18 / 时间 16）；无显式 height 的走设计 lineHeight 1.2
    （12px → 14.4 · 11px → 13.2）；只有「标题行 18」「导航内容行 26」取 PNG 实测。
  · stroke{align:center,thickness:1} → box-shadow: 0 0 0 1px（border 会占布局）· 无 effects（本页 5 张卡都只有描边）。
"""
import io
import os

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
HM = os.path.join(ROOT, ".agents/state/h5-measure")
SRC = os.path.join(HM, "__measure-contract.html")
DST = os.path.join(HM, "__measure-messages.html")

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
    "if (SHOT_ONLY) f.style.height = '1231px' /* = 设计帧高 */",
    "if (SHOT_ONLY) f.style.height = '760px' /* = 设计帧高 */",
)
assert "'760px'" in top, "SHOT 高度替换失败（顶部作用域切片变了？）"
preamble = "\n".join(src[i_collect:i_over])   # collect 签名 + helpers（未闭合）
overflow = "\n".join(src[i_over:i_checks])    # over / missing 统计（引用 NEED_TEXT / CARDS）
tail = "\n".join(src[i_sink:i_main])          # sink / phase / clickIn / toastText / hashNow / waitFor / sleep / textIn / countIn / bgsIn
assert "f.style.height = '900px'" in tail, "phase() 取数高度锚变了（应把 900 改成 760）"
tail = tail.replace("f.style.height = '900px'", "f.style.height = '760px'")
# ⚠️ 切片坑：__measure-contract.html 里 `function bgsIn` 的收尾 `}` 与 `async function main() {` **同一行**
# （`      }      async function main() {`）→ 按行切片到 main 之前会把它切掉，大括号净值 +1
# （node --check 只报「Unexpected end of input」，不给行号；用 js-depth.py 看净值最直接）。显式补回：
tail = tail + "\n      }\n"

HEAD = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>measure-messages</title>
    <style>
      body { margin: 0; font: 12px monospace; }
      /* iframe 取数高度 = 设计帧高 760：页面 min-height:100vh 会把测量高度顶到 iframe 高，
         760 时 docScrollHeight 恰好等于设计帧高（TabBar fixed 也在 676..760）。 */
      iframe { width: 430px; height: 760px; border: 0; }
      /* 取数用 <pre> 包进 0 尺寸 overflow:hidden 容器：textContent 可读，但不渲染、不会被 --screenshot 截进图里 */
      #sink { position: absolute; top: 0; left: 0; width: 0; height: 0; overflow: hidden; }
    </style>
  </head>
  <body>
    <!-- 430 宽 iframe 模拟小程序视口；数字优先，不靠 vision 猜（uni-app 技能 §5 口径）
         页面 20：/pages/messages/index（【合同与通知】站内信列表 2，page-20-2 · layer_id 76700922-02b2-45f3-9343-256eb34bace0）
         设计真源：.calicat/raw/pages/page-20-2/design.tree.json（本轮重抓 sha256 02600c1b… 逐字节相同）
         设计骨架（声明值 + 设计 PNG 430x760 实测）：
           顶部导航 0..86（padding 48/16/12/16 · 标题行盒 26 · 未读胶囊 h22 r11 #FEF2F2 · 全部已读 343..414）
           筛选行 86..140（padding 12/16 · chip 30 r10 @x16/74/132/190 · 间隙 9）
           消息列表区 140..660（padding-top 12 · 5 卡 × 92 @152/256/360/464/568 · 间隙 12 · 描边 1px #EEF2F7）
           卡内：图标 38×38 r12 @x32 · 内容列 +12 · 标题行 18 +4 摘要 18 +4 时间 16 = 60 · 未读点 9×8 r4
           底部 TabBar 676..760（84 = 8 + 图标块 33 + 3 + 文字 16 + 24 · 4 项各 104 · 高亮「我的」#007AFF）
         ?scenario=guard|filter|readall|card|tab 逐个回放出口；不带 scenario（或 noaction）只取 phase1 设计期望值相 -->
    <iframe id="f" src="/index.html#/pages/messages/index"></iframe>
    <div id="sink"><pre id="m">pending</pre></div>
    <script>
"""

PRELUDE = r"""
        var CARDS = '.msg'
        /* 设计树里每一个独立文本图层（文案完整性检查清单，逐字抄自 page-20-2 design.tree.json；图标字形层
           content 为空不进清单）。5 条时间文案是设计帧写法（相对时间）→ mock 时间戳由
           `python .agents/state/refresh-notification-mock.py` 每轮按「相对现在」重写，否则会漂成
           「N 小时前」而报假缺陷（08:11 复核轮已踩到）。 */
        var NEED_TEXT = [
          '消息', '3 条未读', '全部已读',
          '全部', '未读', '订单', '系统',
          '检测报告已生成（通过）', '华东主线路综合评分 92 分，可进入报价流程。', '10 分钟前',
          '报价单被驳回，请修改后重提', '06 月增量报价：输出价高于市场均价 18%。', '2 小时前',
          '合同待签署提醒', 'API 接入服务合同请在 06-20 前完成签署。', '昨天 18:20',
          '6 月账单已出，结算金额 ¥12,860.00', '预计 07-15 打款至绑定对公账户。', '3 天前',
          '平台系统升级公告', '06-16 02:00–04:00 计费系统维护，期间不影响调用。', '5 天前',
          '工作台', '报告', '报价', '我的'
        ]
"""

CHECKS = r"""
        /* ===================== 整页（设计帧 430×760） ===================== */
        var docH = Math.max(doc.documentElement.scrollHeight, doc.body.scrollHeight)
        chk('page.innerWidth', win.innerWidth, 430)
        chk('page.docScrollWidth', doc.documentElement.scrollWidth, 430)
        chk('page.docHeight', docH, 760, 2) /* PNG 实测 760 行（TabBar 676..760） */
        chk('page.overflowingCount', over.length, 0)
        chk('page.missingTextCount', missing.length, 0)
        chkC('page.bg', '.messages', 'backgroundColor', 'rgb(248, 250, 252)') /* 站内信列表页 0330ea02 fills rgba(248,250,252,1) */
        chk('page.cardCount', doc.querySelectorAll(CARDS).length, 5)
        chk('page.inputCount', doc.querySelectorAll('input,textarea').length, 0)
        chk('page.padBottom', css('.messages', 'paddingBottom'), 100) /* 列表止于 660 + 16(TabBar 前间隙) + 84(TabBar fixed 占位) */

        /* ===================== 顶部导航（design 49663acf padding[48,16,12,16]） ===================== */
        chkR('nav.top', '.messages__topbar', 0, 1)
        chkR('nav.h', '.messages__topbar', 86, 1) /* 48 + 内容行 26 + 12（PNG 0..86） */
        chkC('nav.pad', '.messages__topbar', 'padding', '48px 16px 12px')
        chkC('nav.bg', '.messages__topbar', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('nav.align', '.messages__topbar', 'alignItems', 'center')
        chkD('nav.borderDeclared', '.messages__topbar', 'borderBottom', null) /* 设计无分隔线（本页导航全白） */
        chkR('nav.title.x', '.messages__title', 16, 1)
        chkR('nav.title.top', '.messages__title', 48, 1)
        chkR('nav.title.h', '.messages__title', 26, 1) /* 导航内容行：PNG 标题墨迹 50..71 居中于 48..74 */
        chkC('nav.title.fs', '.messages__title', 'fontSize', 20) /* 864f2889 fs20 Bold */
        chkC('nav.title.fw', '.messages__title', 'fontWeight', 700)
        chkC('nav.title.lh', '.messages__title', 'lineHeight', 26) /* 设计 fit_content 高 = 26（navigation 内容行） */
        chkC('nav.title.color', '.messages__title', 'color', 'rgb(15, 23, 42)')
        chkStrs('nav.title.text', [textOf('.messages__title')], ['消息'])
        chk('nav.badgeWrap.pad', css('.messages__badge-wrap', 'paddingLeft'), 8) /* 2c72dc06 padding-left 8 */
        chk('nav.badge.gap', rect('[data-testid="unread-badge"]').x - rect('.messages__title').right, 8, 2)
        chkR('nav.badge.top', '[data-testid="unread-badge"]', 50, 1) /* 内容行 26 内垂直居中（PNG #FEF2F2 50..72） */
        chkR('nav.badge.h', '[data-testid="unread-badge"]', 22, 1) /* f96212e9 h22 r11 padding[0,8] */
        chkC('nav.badge.pad', '[data-testid="unread-badge"]', 'padding', '0px 8px')
        chkC('nav.badge.radius', '[data-testid="unread-badge"]', 'borderRadius', '11px')
        chkC('nav.badge.bg', '[data-testid="unread-badge"]', 'backgroundColor', 'rgb(254, 242, 242)')
        chkD('nav.badge.borderDeclared', '[data-testid="unread-badge"]', 'border', null)
        chkC('nav.badgeText.fs', '.messages__badge-text', 'fontSize', 11) /* f947ddee fs11 SemiBold rgba(185,28,28,1) */
        chkC('nav.badgeText.fw', '.messages__badge-text', 'fontWeight', 600)
        chkC('nav.badgeText.lh', '.messages__badge-text', 'lineHeight', 13.2, 0.2) /* 设计 lineHeight 1.2 × 11 */
        chkC('nav.badgeText.color', '.messages__badge-text', 'color', 'rgb(185, 28, 28)')
        chkStrs('nav.badgeText.text', [textOf('[data-testid="unread-badge"]')], ['3 条未读'])
        chk('nav.spacer.grow', css('.messages__spacer', 'flexGrow'), 1) /* 设计 spacer fill_container */
        chkR('nav.readAll.x', '[data-testid="read-all"]', 343, 2) /* PNG 图标墨迹 344..358 / 文字 365..412 → 盒 343..414 */
        chkR('nav.readAll.right', '[data-testid="read-all"]', 414, 1)
        chkR('nav.readAll.w', '[data-testid="read-all"]', 71, 2) /* 图标盒 18 + 容器 padding-left 4 + 文字 49 */
        chkR('nav.readAllIcon.w', '.messages__read-all-icon', 18, 1) /* 11dda916 fs16 w18 */
        chkR('nav.readAllIcon.h', '.messages__read-all-icon', 24, 1) /* 字形行盒 = 字号 × 1.5 */
        chkC('nav.readAllGlyph.bg', '.messages__read-all-glyph', 'backgroundColor', 'rgb(37, 99, 235)')
        chk('nav.readAllText.pad', css('.messages__read-all-text-wrap', 'paddingLeft'), 4) /* 46ba7d62 padding-left 4 */
        chk('nav.readAllText.x', rect('.messages__read-all-text').x, 365, 1) /* 361 + 4 = PNG 墨迹左界 365 */
        chkC('nav.readAllText.fs', '.messages__read-all-text', 'fontSize', 12) /* 9225bd30 fs12 Medium #2563EB */
        chkC('nav.readAllText.fw', '.messages__read-all-text', 'fontWeight', 500)
        chkC('nav.readAllText.lh', '.messages__read-all-text', 'lineHeight', 14.4, 0.2) /* 设计 1.2 × 12 */
        chkC('nav.readAllText.color', '.messages__read-all-text', 'color', 'rgb(37, 99, 235)')
        chkStrs('nav.readAllText.text', [textOf('[data-testid="read-all"]')], ['全部已读'])

        /* ===================== 筛选行（design 42d2aeb5 padding[12,16] · chip h30 r10 · 间距 9） ===================== */
        chkR('filters.top', '.messages__filters', 86, 1)
        chkR('filters.h', '.messages__filters', 54, 1) /* 12 + 30 + 12（PNG chip 98..128） */
        chkC('filters.pad', '.messages__filters', 'padding', '12px 16px')
        chkC('filters.bg', '.messages__filters', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('filters.align', '.messages__filters', 'alignItems', 'center')
        chk('filters.chipCount', doc.querySelectorAll('.chip').length, 4)
        chk('filters.chip.top', rect('.chip').top, 98, 1) /* PNG 98..128 */
        /* PNG chip 边界 16..65 / 74..123 / 132..181 / 190..239（宽 49 = 声明文本 25 + 左右 12）。
           H5 回退字体 CJK 每字恰 12 → 文本盒 24 → chip 实测 48，其后每枚累计 −1（第 4 枚 −3）→
           want 取「同一 padding/gap + 实测文本宽」链算值并登记残差（不写死 49，避免换字体后失真）。 */
        chkList('filters.chipX', rects('.chip').map(function (r) { return r.x }), [16, 73, 130, 187], 1)
        chkList('filters.chipW', rects('.chip').map(function (r) { return r.w }), [48, 48, 48, 48], 1)
        chkList('filters.chipH', rects('.chip').map(function (r) { return r.h }), [30, 30, 30, 30], 1)
        chkList('filters.chipGaps', [1, 2, 3].map(function (i) { var c = rects('.chip'); return c[i].x - c[i - 1].right }), [9, 9, 9], 1)
        chkC('filters.chip.pad', '.chip', 'padding', '0px 12px')
        chkC('filters.chip.radius', '.chip', 'borderRadius', '10px')
        chkStrs('filters.chipBgs', colors('.chip'),
          ['rgb(37, 99, 235)', 'rgb(241, 245, 249)', 'rgb(241, 245, 249)', 'rgb(241, 245, 249)'])
        chkStrs('filters.chipTexts', texts('.chip__text'), ['全部', '未读', '订单', '系统'])
        chkStrs('filters.chipTextColors', textColors('.chip__text'),
          ['rgb(255, 255, 255)', 'rgb(100, 116, 139)', 'rgb(100, 116, 139)', 'rgb(100, 116, 139)'])
        chkC('filters.chipText.fs', '.chip__text', 'fontSize', 12) /* 0240859d fs12 Medium */
        chkC('filters.chipText.fw', '.chip__text', 'fontWeight', 500)
        chkC('filters.chipText.lh', '.chip__text', 'lineHeight', 14.4, 0.2) /* 设计 1.2 × 12（chip 高 30 固定，居中） */
        chk('filters.activeText', textOf('.chip--active'), '全部') /* 设计 筛选全部 fills rgba(37,99,235,1) */

        /* ===================== 消息列表区（design 863dc36b padding[12,16,0,16] · 卡 92 r14 · stroke 1） ===================== */
        chkR('list.top', '.messages__list', 140, 1)
        chkR('list.h', '.messages__list', 520, 1) /* 140..660 */
        chkC('list.pad', '.messages__list', 'padding', '12px 16px 0px')
        chkList('list.cardTops', rects(CARDS).map(function (r) { return r.top }), [152, 256, 360, 464, 568], 2) /* PNG 描边行 151/244·255/348·359/452·463/556·567/660 */
        chkList('list.cardH', rects(CARDS).map(function (r) { return r.h }), [92, 92, 92, 92, 92], 1) /* 16 + 60 + 16 */
        chkList('list.cardX', rects(CARDS).map(function (r) { return r.x }), [16, 16, 16, 16, 16], 1)
        chkList('list.cardW', rects(CARDS).map(function (r) { return r.w }), [398, 398, 398, 398, 398], 1)
        chkList('list.cardGaps', [1, 2, 3, 4].map(function (i) { var c = rects(CARDS); return c[i].top - c[i - 1].bottom }), [12, 12, 12, 12], 1)
        chkC('list.card.pad', '.msg', 'padding', '16px')
        chkC('list.card.radius', '.msg', 'borderRadius', '14px')
        chkC('list.card.bg', '.msg', 'backgroundColor', 'rgb(255, 255, 255)')
        chkC('list.card.align', '.msg', 'alignItems', 'flex-start')
        chkStrs('list.cardRings', ['@@0', '@@1', '@@2', '@@3', '@@4'].map(function (s) { return css(CARDS + s, 'boxShadow') }),
          ['rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px',
           'rgb(238, 242, 247) 0px 0px 0px 1px', 'rgb(238, 242, 247) 0px 0px 0px 1px']) /* stroke{align:center,thickness:1} */
        chkD('list.card.borderDeclared', '.msg', 'border', null) /* 反向断言：中心描边只能用 ring 表达 */

        /* 卡内图标（design 消息X图标 38×38 r12 · 字形层 fs20 声明宽 22 → 盒 22×30） */
        chkList('card.iconX', rects('.msg__icon').map(function (r) { return r.x }), [32, 32, 32, 32, 32], 1)
        chkList('card.iconTops', rects('.msg__icon').map(function (r) { return r.top }), [168, 272, 376, 480, 584], 1)
        chkList('card.iconW', rects('.msg__icon').map(function (r) { return r.w }), [38, 38, 38, 38, 38], 1)
        chkList('card.iconH', rects('.msg__icon').map(function (r) { return r.h }), [38, 38, 38, 38, 38], 1)
        chkC('card.icon.radius', '.msg__icon', 'borderRadius', '12px')
        chkStrs('card.iconBgs', colors('.msg__icon'),
          ['rgb(239, 246, 255)', 'rgb(255, 247, 237)', 'rgb(236, 253, 245)', 'rgb(239, 246, 255)', 'rgb(241, 245, 249)'])
        chkList('card.glyphBoxTops', rects('.msg__glyph-box').map(function (r) { return r.top }), [172, 276, 380, 484, 588], 1) /* 38 高盒内居中 30 高字形盒 → +4 */
        chkList('card.glyphBoxW', rects('.msg__glyph-box').map(function (r) { return r.w }), [22, 22, 22, 22, 22], 1) /* 字形层声明 w22 */
        chkList('card.glyphBoxH', rects('.msg__glyph-box').map(function (r) { return r.h }), [30, 30, 30, 30, 30], 1) /* 字形行盒 = 字号 20 × 1.5 */
        chkStrs('card.glyphBg', colors('.msg__glyph'),
          ['rgb(37, 99, 235)', 'rgb(217, 119, 6)', 'rgb(22, 163, 74)', 'rgb(37, 99, 235)', 'rgb(100, 116, 139)']) /* 字形 fills 逐条 */

        /* 卡内三行文字（标题行 18 + 4 + 摘要 18 + 4 + 时间 16 = 60） */
        chk('card.body.pad', css('.msg__body', 'paddingLeft'), 12) /* container padding-left 12 */
        chkList('card.titleRowTops', rects('.msg__title-row').map(function (r) { return r.top }), [168, 272, 376, 480, 584], 1)
        chkList('card.titleRowH', rects('.msg__title-row').map(function (r) { return r.h }), [18, 18, 18, 18, 18], 1)
        chkC('card.title.fs', '.msg__title', 'fontSize', 13) /* 4697a234 fs13 SemiBold */
        chkC('card.title.fw', '.msg__title', 'fontWeight', 600)
        chkC('card.title.lh', '.msg__title', 'lineHeight', 18)
        chkStrs('card.titleColors', textColors('.msg__title'),
          ['rgb(15, 23, 42)', 'rgb(15, 23, 42)', 'rgb(15, 23, 42)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)']) /* 未读/已读两态 */
        chkStrs('card.titles', texts('.msg__title'),
          ['检测报告已生成（通过）', '报价单被驳回，请修改后重提', '合同待签署提醒', '6 月账单已出，结算金额 ¥12,860.00', '平台系统升级公告'])
        chk('card.dotCount', doc.querySelectorAll('[data-testid="unread-dot"]').length, 3)
        chkList('card.dotW', rects('[data-testid="unread-dot"]').map(function (r) { return r.w }), [9, 9, 9], 1) /* 未读点 9×8 r4 */
        chkList('card.dotH', rects('[data-testid="unread-dot"]').map(function (r) { return r.h }), [8, 8, 8], 1)
        chkC('card.dot.radius', '.msg__dot', 'borderRadius', '4px')
        chkC('card.dot.bg', '.msg__dot', 'backgroundColor', 'rgb(239, 68, 68)') /* fills rgba(239,68,68,1) */
        chk('card.dotWrap.pad', css('.msg__dot-wrap', 'paddingLeft'), 8) /* 标题行内容器 padding-left 8 */
        chk('card.dot1.gap', rect('[data-testid="unread-dot"]').x - rect('.msg__title@@0').right, 8, 2) /* 卡1 标题声明 w144 / H5 实测 143 */
        /* 行盒口径：设计是「容器 padding-top 4 + 文本行」两层（同 __measure-contract 的 status.deadline：
           容器盒 = padding + 行盒）→ 文本盒另测（PNG 摘要墨迹 193..205 落在文本盒 190..208 内） */
        chkList('card.contentRowTops', rects('.msg__content-row').map(function (r) { return r.top }), [186, 290, 394, 498, 602], 1)
        chkList('card.contentRowH', rects('.msg__content-row').map(function (r) { return r.h }), [22, 22, 22, 22, 22], 1) /* 4 + 18 */
        chkList('card.contentBoxTops', rects('.msg__content').map(function (r) { return r.top }), [190, 294, 398, 502, 606], 1)
        chkList('card.contentBoxH', rects('.msg__content').map(function (r) { return r.h }), [18, 18, 18, 18, 18], 1) /* 设计显式 height 18 */
        chk('card.contentRow.padTop', css('.msg__content-row', 'paddingTop'), 4)
        chkC('card.content.fs', '.msg__content', 'fontSize', 12) /* 47b9b24d fs12 Regular h18 */
        chkC('card.content.fw', '.msg__content', 'fontWeight', 400)
        chkC('card.content.lh', '.msg__content', 'lineHeight', 18)
        chkStrs('card.contents', texts('.msg__content'),
          ['华东主线路综合评分 92 分，可进入报价流程。', '06 月增量报价：输出价高于市场均价 18%。',
           'API 接入服务合同请在 06-20 前完成签署。', '预计 07-15 打款至绑定对公账户。',
           '06-16 02:00–04:00 计费系统维护，期间不影响调用。'])
        chkList('card.timeRowTops', rects('.msg__time-row').map(function (r) { return r.top }), [208, 312, 416, 520, 624], 1)
        chkList('card.timeRowH', rects('.msg__time-row').map(function (r) { return r.h }), [20, 20, 20, 20, 20], 1) /* 4 + 16 */
        chkList('card.timeBoxTops', rects('.msg__time').map(function (r) { return r.top }), [212, 316, 420, 524, 628], 1) /* PNG 时间墨迹 214..224 落在 212..228 内 */
        chkList('card.timeBoxH', rects('.msg__time').map(function (r) { return r.h }), [16, 16, 16, 16, 16], 1) /* 设计显式 height 16 */
        chk('card.timeRow.padTop', css('.msg__time-row', 'paddingTop'), 4)
        chkC('card.time.fs', '.msg__time', 'fontSize', 11) /* 8e568d58 fs11 Regular h16 */
        chkC('card.time.fw', '.msg__time', 'fontWeight', 400)
        chkC('card.time.lh', '.msg__time', 'lineHeight', 16)
        chkStrs('card.timeColors', textColors('.msg__time'),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(203, 213, 225)', 'rgb(203, 213, 225)'])
        chkStrs('card.times', texts('.msg__time'), ['10 分钟前', '2 小时前', '昨天 18:20', '3 天前', '5 天前'])
        chk('card.lastBottom', rect(CARDS + '@@4').bottom, 660, 1) /* 列表止于 660（PNG 卡5 底线 660） */

        /* ===================== 底部 TabBar（共享组件 AppTabBar · design c02e59d8） ===================== */
        chkR('tabbar.top', '.tabbar', 676, 1) /* PNG 676..760 */
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
        chk('tabbar.gap.h', css('.tabbar__gap', 'height'), 3) /* 容器 padding-top 3 */
        chkStrs('tabbar.glyphBg', colors('.tabbar__glyph'),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(0, 122, 255)']) /* page-20-2 高亮 = #007AFF */
        chkStrs('tabbar.labels', texts('.tabbar__label'), ['工作台', '报告', '报价', '我的'])
        chkC('tabbar.label.fs', '.tabbar__label', 'fontSize', 11)
        chkC('tabbar.label.lh', '.tabbar__label', 'lineHeight', 16)
        chkStrs('tabbar.labelColors', textColors('.tabbar__label'),
          ['rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(148, 163, 184)', 'rgb(0, 122, 255)'])
        chkStrs('tabbar.labelWeights', ['@@0', '@@1', '@@2', '@@3'].map(function (s) { return css('.tabbar__label' + s, 'fontWeight') }),
          [400, 400, 400, 400]) /* page-20-2 四行文本全为 SourceHanSans-Regular（与 page-21-2 的高亮 SemiBold 逐帧不同） */
        chk('tabbar.activeLabel', textOf('.tabbar__label--active'), '我的')

        /* 设计帧字面量登记（不照抄/派生项，逐条说明） */
        var designLiteralDiff = [
          '徽标「3 条未读」由未读条数派生（unreadBadgeText），设计帧示例值 3 来自 mock 的 3 条未读',
          '5 条时间文案是相对时间派生规则（PRD 零定义，台账序号 20 备注④）→ mock 时间戳由 refresh-notification-mock.py 按设计写法生成',
          'chip 宽设计声明 25+12+12 = 49；H5 回退字体 CJK 每字恰 12 → 实测 48（同类残差已登记，未写死宽度）',
          '标题「消息」设计声明 w41；CJK 2 字 × fs20 = 40',
          '图标字形为 CSS 占位形状（D5）：卡图标盒按设计图层 22×30、形状墨迹 17（设计 remixicon 墨迹 17×20）；「全部已读」形状 14（设计墨迹 15）；'
            + 'TabBar 形状 18×18（设计墨迹 17×20，共享组件未改，避免越帧 churn）',
          'toast 文案（数据加载失败 / 操作失败）设计帧无稿 → 占位（missing-prd）',
          '消息卡落点由 biz_type → 路由推断（PRD 零枚举，台账序号 20 备注⑧）→ 未知一律不跳转'
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
          nav: rect('.messages__topbar'),
          navTitle: rect('.messages__title'),
          badge: rect('[data-testid="unread-badge"]'),
          readAll: rect('[data-testid="read-all"]'),
          readAllIcon: rect('.messages__read-all-icon'),
          readAllText: rect('.messages__read-all-text'),
          filters: rect('.messages__filters'),
          chips: rects('.chip'),
          list: rect('.messages__list'),
          cards: rects(CARDS),
          icons: rects('.msg__icon'),
          glyphBoxes: rects('.msg__glyph-box'),
          titleRows: rects('.msg__title-row'),
          contentRows: rects('.msg__content-row'),
          timeRows: rects('.msg__time-row'),
          dots: rects('[data-testid="unread-dot"]'),
          tabbar: rect('.tabbar'),
          tabItems: rects('.tabbar__item'),
          texts: {
            title: textOf('.messages__title'),
            badge: textOf('[data-testid="unread-badge"]'),
            readAll: textOf('[data-testid="read-all"]'),
            chips: texts('.chip__text'),
            titles: texts('.msg__title'),
            times: texts('.msg__time'),
            tabs: texts('.tabbar__label')
          },
          counts: {
            cards: doc.querySelectorAll(CARDS).length,
            dots: doc.querySelectorAll('[data-testid="unread-dot"]').length,
            inputs: doc.querySelectorAll('input,textarea').length
          },
          userAgent: win.navigator.userAgent
        }
      }

"""


MAIN = r"""      async function main() {
        try {
          await waitFor('[data-testid="message-row"]')
          await sleep(1400)
          phase(1)
          if (NO_ACTION || !SCENARIO) return

          /* ?scenario=guard：点「已选中」的 chip 不应重复取数（onFilterTap 同项短路）
             → 硬证据 = serve 实收仍只有首屏那一行 GET /notifications */
          if (SCENARIO === 'guard') {
            var cGuard = clickIn('[data-testid="filter-all"]')
            await sleep(1500)
            sink(2, {
              scenario: SCENARIO, clicked: cGuard,
              activeChip: textIn('.chip--active'),
              rowCount: countIn('.msg'),
              hash: hashNow()
            })
            return
          }

          /* ?scenario=filter：点「未读」→ GET /notifications?unread=true → chip 高亮切换 */
          if (SCENARIO === 'filter') {
            var cFilter = clickIn('[data-testid="filter-unread"]')
            await sleep(1800)
            sink(2, {
              scenario: SCENARIO, clicked: cFilter,
              activeChip: textIn('.chip--active'),
              chipBgs: bgsIn('.chip'),
              rowCount: countIn('.msg'),
              hash: hashNow()
            })
            return
          }

          /* ?scenario=readall：「全部已读」= 逐条 POST /notifications/{id}/read（18-API 无批量接口）
             → 硬证据 = serve 实收 3 行 POST；设计帧未定义 toast，故成功不弹 toast */
          if (SCENARIO === 'readall') {
            var cAll = clickIn('[data-testid="read-all"]')
            await sleep(3500)
            sink(2, {
              scenario: SCENARIO, clicked: cAll,
              dotsAfter: countIn('[data-testid="unread-dot"]'),
              badgeAfter: textIn('[data-testid="unread-badge"]'),
              toast: toastText(f.contentDocument),
              hash: hashNow()
            })
            return
          }

          /* ?scenario=card：点第 1 条 → POST /notifications/n1/read → navigateTo 落点（biz_type REPORT + biz_id r1） */
          if (SCENARIO === 'card') {
            var cCard = clickIn('[data-testid="message-row"]')
            await sleep(3000)
            sink(2, {
              scenario: SCENARIO, clicked: cCard,
              toast: toastText(f.contentDocument),
              hash: hashNow(),
              landingText: textIn('.report__score') || textIn('.report') || textIn('.rp')
            })
            return
          }

          /* ?scenario=tab：点 TabBar「工作台」→ navigateTo /pages/workbench/index */
          if (SCENARIO === 'tab') {
            var cTab = clickIn('[data-testid="tab-工作台"]')
            await sleep(2500)
            sink(2, {
              scenario: SCENARIO, clicked: cTab,
              hash: hashNow(),
              landingText: textIn('.workbench')
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
