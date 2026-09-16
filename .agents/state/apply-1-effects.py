# -*- coding: utf-8 -*-
"""apply-1-effects.py — 序号 1：补设计 effects（卡片 / 主按钮投影）的 checks + 实现。

设计声明（page-1-2 design.tree.json）：
  · 表单卡片 cab5940c effects=[drop_shadow(0,8,24,rgba(15,23,42,0.08))]
  · 主按钮   7e26d478 effects=[drop_shadow(0,8,20,rgba(37,99,235,0.28))]
像素证据（实现截图 430×1114 vs 设计 PNG）：卡底下方 y891..911 设计 235→248 渐变、实现恒为页面底色 248,250,252；
  主按钮下方 y721..740 设计 (207,221,250)→(247,249,254)、实现恒 255,255,255 → 两处投影整体缺失。

用法: python .agents/state/apply-1-effects.py [--dry]
"""
import io
import sys

PROBE = 'E:/workspaces/hioas/hioas-aap-001/.agents/state/h5-measure/__measure-login.html'
SRC = 'E:/workspaces/hioas/hioas-aap-001/aap-client/src/pages/login/index.vue'
dry = '--dry' in sys.argv

EDITS = []

# ① 载体页：两处 effects 声明值 checks（要整串比对，带 alpha 的颜色不能被 ringColor 吃掉 alpha）
EDITS.append((PROBE, (
    "        chk('agreeBox.ringColor', ringColor(g('.agree__box', 'boxShadow')), 'rgb(226,232,240)')\n",
    "        chk('agreeBox.ringColor', ringColor(g('.agree__box', 'boxShadow')), 'rgb(226,232,240)')\n"
    "        /* 设计 effects（逐节点声明值，整串比对：含 alpha 的投影色不能用 ringColor 归一化，否则把 alpha 吃掉）\n"
    "           表单卡片 cab5940c drop_shadow(0,8,24,rgba(15,23,42,0.08)) · 主按钮 7e26d478 drop_shadow(0,8,20,rgba(37,99,235,0.28))\n"
    "           像素证据：卡底 y891..911 设计 235→248 渐变 / 实现恒 248,250,252；按钮下 y721..740 设计 207,221,250→247,249,254 / 实现恒 255,255,255 */\n"
    "        chk('card.shadow', g('.card', 'boxShadow'), 'rgba(15, 23, 42, 0.08) 0px 8px 24px 0px')\n"
    "        chk('submit.shadow', g('.submit', 'boxShadow'), 'rgba(37, 99, 235, 0.28) 0px 8px 20px 0px')\n",
)))

# ② 实现：卡片投影（设计 0,8,24 rgba(15,23,42,.08)）
EDITS.append((SRC, (
    """  border-radius: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;""",
    """  border-radius: 20px;
  /* 设计 表单卡片 cab5940c effects=[drop_shadow(0,8,24,rgba(15,23,42,0.08))]
     像素证据：卡底下方 y891..911 设计 235→248 渐变；修前实现恒为页面底色 248,250,252（投影整体缺失） */
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;""",
)))

# ③ 实现：主按钮投影（设计 0,8,20 rgba(37,99,235,.28)）
EDITS.append((SRC, (
    """  border-radius: 14px;
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;

  &__text {""",
    """  border-radius: 14px;
  background: $color-primary;
  /* 设计 主按钮 7e26d478 effects=[drop_shadow(0,8,20,rgba(37,99,235,0.28))]
     像素证据：按钮下方 y721..740 设计 (207,221,250)→(247,249,254)；修前实现恒 255,255,255 */
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;

  &__text {""",
)))

state = {}
if '--probe-only' in sys.argv:
    EDITS = [e for e in EDITS if e[0] == PROBE]
for path, (old, new) in EDITS:
    if path not in state:
        state[path] = io.open(path, encoding='utf-8', newline='').read()
    n = state[path].count(old)
    if n != 1:
        print('ABORT: anchor hit %d in %s: %r' % (n, path.split('/')[-1], old[:60]))
        raise SystemExit(1)
    state[path] = state[path].replace(old, new)

print('plan ok: %d edits over %d files' % (len(EDITS), len(state)))
if dry:
    raise SystemExit(0)
for path, txt in state.items():
    io.open(path, 'w', encoding='utf-8', newline='').write(txt)
    print('written', path.split('/')[-1])
