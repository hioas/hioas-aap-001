# -*- coding: utf-8 -*-
"""apply-1-ring-icon-src.py — 序号 1 登录页：center 描边 → ring（5 处）+ 输入框图标字形盒按设计声明。

设计依据（.calicat/raw/pages/page-1-2/design.tree.json + 设计 PNG 430×1114 实测）：
  · 0969fe4e / 4b7f22fc / 1b3579fd（三个输入框）stroke{align:center,thickness:1,rgba(226,232,240,1)}
  · 1bb97e22 图形验证码图 rgba(224,231,255,1) · b4fa89d5 获取验证码按钮 rgba(191,219,254,1)
  · 6cf8d63a 微信登录按钮 rgba(187,247,208,1) · 927a3b46 勾选框：选中态 fill rgba(37,99,235,1) 无描边
  · df37d41e / 930dc950 / c59ce992 输入框图标字形层 w=20 fs=18 fill=rgba(148,163,184,1)
    → 图标盒 20×27；描边字形墨迹 11×16 / 15×17 / 15×17
  · 165e103e / 515ac9c7 竖分隔两侧 spacer 8/8 · c825d0d3「+86」声明宽 25

用法: python .agents/state/apply-1-ring-icon-src.py [--dry]
"""
import io
import sys

P = 'E:/workspaces/hioas/hioas-aap-001/aap-client/src/pages/login/index.vue'
dry = '--dry' in sys.argv
src = io.open(P, encoding='utf-8', newline='').read()

EDITS = []

EDITS.append((
    """    background: $color-bg-page;
    border: 1px solid $color-border;
    border-radius: 12px;""",
    """    background: $color-bg-page;
    /* 设计 0969fe4e / 4b7f22fc / 1b3579fd：stroke{align:center,thickness:1,rgba(226,232,240,1)}
       → Figma center 描边不占布局，border 会把内容盒挤掉 2px（内容左界 49 vs 设计 48、右界 381 vs 设计 382）
       → 按同族页口径改用 box-shadow 表达 */
    box-shadow: 0 0 0 1px $color-border;
    border-radius: 12px;""",
))

EDITS.append((
    """  /* 图标占位（设计稿为矢量图标，禁用 emoji） */
  &__mark {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    margin-right: $gap-sm;
    border-radius: 4px;
    background: $color-primary-weak-2;

    &--phone {
      background: $color-primary-weak;
    }

    &--shield {
      border-radius: 50%;
      background: $color-primary-weak;
    }

    &--lock {
      background: $color-primary-weak;
    }
  }""",
    """  /* 图标占位（设计稿为矢量字形，禁用 emoji；D5 = CSS 绘制占位）
     设计 df37d41e / 930dc950 / c59ce992：声明宽 20 · fs18 → 盒 20×27（字号×1.5 字形行框）；
     形状按设计 PNG 实测墨迹画在盒内（手机 11×16 · 盾 15×17 · 锁 15×17），
     颜色 = 设计字形填充 rgba(148,163,184,1)（灰）→ 由伪元素承载（形状颜色读 ::before 的 border-color） */
  &__mark {
    width: 20px;
    height: 27px;
    flex-shrink: 0;
    margin-right: $gap-sm;
    display: flex;
    align-items: center;
    justify-content: center;

    &::before {
      content: '';
      box-sizing: border-box;
      border: 2px solid $color-text-placeholder;
    }

    &--phone::before {
      width: 11px;
      height: 16px;
      border-radius: 3px;
    }

    &--shield::before {
      width: 15px;
      height: 17px;
      border-radius: 7px 7px 50% 50%;
    }

    &--lock::before {
      width: 15px;
      height: 17px;
      border-radius: 3px;
    }
  }""",
))

EDITS.append((
    """  &__prefix {
    font-size: $font-base;
    color: $color-text-secondary-2;
    font-weight: 500;
    flex-shrink: 0;
  }""",
    """  &__prefix {
    width: 25px; /* 设计 c825d0d3 声明宽 25（PNG 墨迹 x76..99）→ 固定宽，使竖分隔/输入框左界不随回退字体漂移 */
    font-size: $font-base;
    color: $color-text-secondary-2;
    font-weight: 500;
    flex-shrink: 0;
  }""",
))

EDITS.append((
    """    width: 2px;
    height: 18px;
    margin: 0 $gap-md;""",
    """    width: 2px;
    height: 18px;
    /* 设计 165e103e / 515ac9c7：竖分隔两侧 spacer 8/8（原 $gap-md=12 会把输入框左界推到 123，设计 119） */
    margin: 0 $gap-sm;""",
))

EDITS.append((
    """  background: $color-primary-weak-2;
  border: 1px solid $color-captcha-border;""",
    """  background: $color-primary-weak-2;
  /* 设计 1bb97e22：stroke{align:center,thickness:1,rgba(224,231,255,1)} → box-shadow
     （border 实现会把块整体推到 x269，设计 270；右界 381，设计 382） */
  box-shadow: 0 0 0 1px $color-captcha-border;""",
))

EDITS.append((
    """  background: $color-primary-weak;
  border: 1px solid $color-brand-en;""",
    """  background: $color-primary-weak;
  /* 设计 b4fa89d5：stroke{align:center,thickness:1,rgba(191,219,254,1)} → box-shadow */
  box-shadow: 0 0 0 1px $color-brand-en;""",
))

EDITS.append((
    """  background: $color-wechat-weak;
  border: 1px solid $color-wechat-border;""",
    """  background: $color-wechat-weak;
  /* 设计 6cf8d63a：stroke{align:center,thickness:1,rgba(187,247,208,1)} → box-shadow */
  box-shadow: 0 0 0 1px $color-wechat-border;""",
))

EDITS.append((
    """  /* 设计：勾选框 18x18 r6（含 1px 描边的外框尺寸） */
  &__box {
    width: 18px;
    height: 18px;
    margin-right: $gap-sm;
    flex-shrink: 0;
    border: 1px solid $color-border;
    border-radius: 6px;
    background: $color-bg-card;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;

    &--checked {
      background: $color-primary;
      border-color: $color-primary;
    }
  }""",
    """  /* 设计 927a3b46：勾选框 18x18 r6，**选中态 = fill rgba(37,99,235,1) 且无描边**（fill-only）；
     未选中态是设计未画出的状态（PRD 校验门要求用户显式勾选）→ 用同族 ring 表达 1px 描边 */
  &__box {
    width: 18px;
    height: 18px;
    margin-right: $gap-sm;
    flex-shrink: 0;
    box-shadow: 0 0 0 1px $color-border;
    border-radius: 6px;
    background: $color-bg-card;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;

    &--checked {
      background: $color-primary;
      box-shadow: none;
    }
  }""",
))

out = src
problems = []
for old, new in EDITS:
    n = out.count(old)
    if n != 1:
        problems.append('anchor hit %d: %r' % (n, old[:60]))
        continue
    out = out.replace(old, new)
if problems:
    print('ABORT (nothing written)')
    for p in problems:
        print(' -', p)
    raise SystemExit(1)
print('plan ok: %d edits, %d -> %d bytes' % (len(EDITS), len(src), len(out)))
if dry:
    raise SystemExit(0)
io.open(P, 'w', encoding='utf-8', newline='').write(out)
print('written')
