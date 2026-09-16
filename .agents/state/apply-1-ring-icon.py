# -*- coding: utf-8 -*-
"""apply-1-ring-icon.py — 给序号 1 载体页加「center 描边 → ring / 输入框图标字形盒」设计期望值 checks（先红后绿）。

用法: python .agents/state/apply-1-ring-icon.py [--dry]
每个锚点必须恰好命中 1 次，否则整文件不写。
"""
import io
import sys

P = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/h5-measure/__measure-login.html'
dry = '--dry' in sys.argv
src = io.open(P, encoding='utf-8', newline='').read()

EDITS = []

# R1 输入框：border 检查改成 ring 检查（新增 ring 断言见新块）
EDITS.append((
    "        chk('fieldBox.borderColor', g('.field__box', 'borderTopColor'), 'rgba(226,232,240,1)')\n"
    "        chk('fieldBox.borderWidth', g('.field__box', 'borderTopWidth'), '1px')\n",
    "        chk('fieldBox.borderWidth', g('.field__box', 'borderTopWidth'), '0px')   /* 设计 center 描边 → ring（见本节末） */\n",
))

# R2~R4 三个固定尺寸块的 borderColor 检查 → 由新块的 ring 检查取代
EDITS.append((
    "        chk('captcha.borderColor', g('.captcha', 'borderTopColor'), 'rgba(224,231,255,1)')\n",
    "",
))
EDITS.append((
    "        chk('smsBtn.borderColor', g('.sms-btn', 'borderTopColor'), 'rgba(191,219,254,1)')\n",
    "",
))
EDITS.append((
    "        chk('wechat.borderColor', g('.wechat', 'borderTopColor'), 'rgba(187,247,208,1)')\n",
    "",
))

NEW_BLOCK = """        /* —— 19:0x 轮新增：Figma center 描边 → ring（同族页口径）+ 输入框图标字形盒按设计声明 ——
           ① 设计声明（page-1-2 design.tree.json，均为 stroke{align:center,thickness:1}）：
              · 三个输入框 0969fe4e / 4b7f22fc / 1b3579fd → rgba(226,232,240,1)
              · 图形验证码图 1bb97e22 → rgba(224,231,255,1) · 获取验证码按钮 b4fa89d5 → rgba(191,219,254,1)
              · 微信登录按钮 6cf8d63a → rgba(187,247,208,1)
              center 描边**不占布局**（Figma）→ 只能 box-shadow 0 0 0 1px；用 border 会把内容盒挤掉 2px
              （实测：输入框内容左界 49 vs 设计 48、右界 381 vs 设计 382；验证码图 269 vs 270）
           ② 三个输入框图标字形层 df37d41e / 930dc950 / c59ce992：w=20 fs=18 remixicon fill=rgba(148,163,184,1)
              → 图标盒 20×27（声明宽 × 字号×1.5）；描边字形墨迹（设计 PNG 430×1114 实测）：
                手机 11×16（x52..62 y407..422）· 盾 15×17（x50..64 y496..512）· 锁 15×17（x50..64 y586..602）
           ③ 设计行内 spacer：图标后 8（7b9de106 / c6fa6587 / bc8183c8）· 竖分隔两侧 8/8（165e103e / 515ac9c7）
              → 占位文本左界 = 48 + 20 + 8 = 76（修前实现 49+16+8 = 73）；手机号输入框左界 = 110 + 8 = 119 */
        function ringNums(sel) {
          var v = String(g(sel, 'boxShadow'))
          var m = v.match(/-?[\\d.]+px/g)
          return m ? m.join(' ') : v
        }
        var marks = rects(doc, '.field__mark'), inputs = rects(doc, '.field__input')
        var prefixR = rectFor(doc, '.field__prefix'), dividerR2 = rectFor(doc, '.field__divider')
        chk('fieldBox.contentLeft', marks.length ? Math.round(marks[0].left) : null, 48)
        chk('fieldBox.ringNums', ringNums('.field__box'), '0px 0px 0px 1px')
        chk('fieldBox.ringColor', ringColor(g('.field__box', 'boxShadow')), 'rgb(226,232,240)')
        chk('mark.sizes', marks.map(function (r) { return r.w + 'x' + r.h }).join(','), '20x27,20x27,20x27')
        chk('mark.lefts', marks.map(function (r) { return r.left }).join(','), '48,48,48')
        chk('markPhone.shapeW', pseudo('.field__mark--phone', 'width'), '11px')
        chk('markPhone.shapeH', pseudo('.field__mark--phone', 'height'), '16px')
        chk('markPhone.shapeBorderW', pseudo('.field__mark--phone', 'borderTopWidth'), '2px')
        chk('markPhone.shapeColor', pseudo('.field__mark--phone', 'borderTopColor'), 'rgba(148,163,184,1)')
        chk('markShield.shapeW', pseudo('.field__mark--shield', 'width'), '15px')
        chk('markShield.shapeH', pseudo('.field__mark--shield', 'height'), '17px')
        chk('markShield.shapeBorderW', pseudo('.field__mark--shield', 'borderTopWidth'), '2px')
        chk('markShield.shapeColor', pseudo('.field__mark--shield', 'borderTopColor'), 'rgba(148,163,184,1)')
        chk('markLock.shapeW', pseudo('.field__mark--lock', 'width'), '15px')
        chk('markLock.shapeH', pseudo('.field__mark--lock', 'height'), '17px')
        chk('markLock.shapeBorderW', pseudo('.field__mark--lock', 'borderTopWidth'), '2px')
        chk('markLock.shapeColor', pseudo('.field__mark--lock', 'borderTopColor'), 'rgba(148,163,184,1)')
        chk('prefix.left', prefixR ? Math.round(prefixR.left) : null, 76)
        chk('prefix.right', prefixR ? Math.round(prefixR.right) : null, 101)
        chk('divider.left', dividerR2 ? Math.round(dividerR2.left) : null, 109)
        chk('input.lefts', inputs.map(function (r) { return r.left }).join(','), '119,76,76')
        chk('captcha.borderWidth', g('.captcha', 'borderTopWidth'), '0px')
        chk('captcha.ringNums', ringNums('.captcha'), '0px 0px 0px 1px')
        chk('captcha.ringColor', ringColor(g('.captcha', 'boxShadow')), 'rgb(224,231,255)')
        chk('captcha.x', dim('.captcha', 'x'), 270)
        chk('smsBtn.borderWidth', g('.sms-btn', 'borderTopWidth'), '0px')
        chk('smsBtn.ringNums', ringNums('.sms-btn'), '0px 0px 0px 1px')
        chk('smsBtn.ringColor', ringColor(g('.sms-btn', 'boxShadow')), 'rgb(191,219,254)')
        chk('wechat.borderWidth', g('.wechat', 'borderTopWidth'), '0px')
        chk('wechat.ringNums', ringNums('.wechat'), '0px 0px 0px 1px')
        chk('wechat.ringColor', ringColor(g('.wechat', 'boxShadow')), 'rgb(187,247,208)')
        chk('agreeBox.borderWidth', g('.agree__box', 'borderTopWidth'), '0px')
        chk('agreeBox.ringNums', ringNums('.agree__box'), '0px 0px 0px 1px')
        chk('agreeBox.ringColor', ringColor(g('.agree__box', 'boxShadow')), 'rgb(226,232,240)')

        return checks
"""

EDITS.append(("        return checks\n", NEW_BLOCK))

# R6 phase5：勾选后按设计校核勾选框（设计 927a3b46 = 选中态 fill rgba(37,99,235,1)，**无描边**）
EDITS.append((
    """        var cAgree = clickIn('[data-test="agree-box"]')
        await sleep(300)
""",
    """        var cAgree = clickIn('[data-test="agree-box"]')
        await sleep(300)
        /* 设计 927a3b46 勾选框：选中态 = fill rgba(37,99,235,1) 且**无描边**（fill-only，不是描边框） */
        var agreeEl = f.contentDocument.querySelector('.agree__box')
        var agreeCs = agreeEl ? f.contentWindow.getComputedStyle(agreeEl, null) : null
        var chk5 = []
        function chk5add(k, got, want) {
          var a = norm(got), b = norm(want)
          chk5.push({ k: k, got: a, want: b, ok: a === b })
        }
        chk5add('agreeBoxChecked.bg', agreeCs ? agreeCs.backgroundColor : null, 'rgba(37,99,235,1)')
        chk5add('agreeBoxChecked.borderWidth', agreeCs ? agreeCs.borderTopWidth : null, '0px')
        chk5add('agreeBoxChecked.shadow', agreeCs ? agreeCs.boxShadow : null, 'none')
        chk5add('agreeBoxChecked.w', agreeEl ? Math.round(agreeEl.getBoundingClientRect().width) : null, 18)
        chk5add('agreeBoxChecked.h', agreeEl ? Math.round(agreeEl.getBoundingClientRect().height) : null, 18)
""",
))

EDITS.append((
    """          smsBtnDisabledClass: !!(f.contentDocument.querySelector('.sms-btn--disabled')),""",
    """          smsBtnDisabledClass: !!(f.contentDocument.querySelector('.sms-btn--disabled')),
          agreeBoxChecked: {
            bg: agreeCs ? agreeCs.backgroundColor : null,
            shadow: agreeCs ? agreeCs.boxShadow : null,
            borderWidth: agreeCs ? agreeCs.borderTopWidth : null,
            cls: agreeEl ? String(agreeEl.className) : null
          },
          checks: chk5,
          checkFails: chk5.filter(function (c) { return !c.ok }).map(function (c) { return c.k + ': got ' + JSON.stringify(c.got) + ' want ' + JSON.stringify(c.want) }),
          checkCount: chk5.length,
          checkFailCount: chk5.filter(function (c) { return !c.ok }).length,""",
))

out = src
problems = []
for old, new in EDITS:
    n = out.count(old)
    if n != 1:
        problems.append('anchor hit %d times: %r' % (n, old[:80]))
        continue
    out = out.replace(old, new)

if problems:
    print('ABORT (nothing written):')
    for p in problems:
        print(' -', p)
    raise SystemExit(1)

print('plan ok: %d edits, %d -> %d bytes' % (len(EDITS), len(src), len(out)))
if dry:
    raise SystemExit(0)
io.open(P, 'w', encoding='utf-8', newline='').write(out)
print('written')
