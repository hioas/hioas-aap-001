# -*- coding: utf-8 -*-
"""给 aap-client 的登录页按**设计声明的字重**补齐 font-weight（RED→GREEN 的 GREEN 步）。

设计依据：.calicat/raw/pages/page-1-2 各文本叶子的 fontFamily（Bold 700 / SemiBold 600 / Medium 500），
         由 textleaf-audit.py 全量扫描查出实现侧 10 处 computed 字重为 400。

安全：每处锚点必须**恰好匹配 1 次**，任一不满足则整文件不写（避免误改）。
用法: python .agents/state/apply-login-fw.py [--dry]
"""
import io
import sys

REPO = 'E:/workspaces/hioas/hioas-aap-001'
PATH = REPO + '/aap-client/src/pages/login/index.vue'

EDITS = [
    (700, ['&__name {'], 'brand__name（设计 2774910e SourceHanSans-Bold）'),
    (700, ['&__title {', 'margin-top: 28px;'], 'brand__title（设计 15a710ce Bold）'),
    (700, ['&__title {', 'font-size: $font-2xl;', 'line-height: 1.3;'], 'card__title（设计 c127cbae Bold）'),
    (700, ['&__text {', 'font-size: $font-lg;', 'letter-spacing: 2px;'], 'captcha__text（设计 282a01d9 Bold）'),
    (600, ['border: 1px solid $color-text-placeholder;', 'margin-right: 6px;', 'flex-shrink: 0;', '}', '', '&__title {'],
     'disclaimer__title（设计 b2f5825d SemiBold）'),
    (500, ['&__label {'], 'field__label（设计 125de7eb/1ed971c8/bcbaf093 Medium）'),
    (500, ['&__prefix {', 'font-size: $font-base;', 'color: $color-text-secondary-2;'], 'field__prefix（设计 c825d0d3 Medium）'),
    (500, ['&__text {', 'font-size: $font-sm;', 'color: $color-primary;'], 'sms-btn__text（设计 c9f25ca7 Medium）'),
    (600, ['&__text {', 'font-size: $font-lg;', 'color: $color-bg-card;'], 'submit__text（设计 fcfe15cf SemiBold）'),
    (500, ['&__text {', 'font-size: $font-md;', 'color: $color-wechat-text;'], 'wechat__text（设计 5ecf7b26 Medium）'),
]

src = io.open(PATH, encoding='utf-8').read()
lines = src.split('\n')
stripped = [l.strip() for l in lines]

plan = []
for weight, ctx, why in EDITS:
    hits = []
    for i in range(len(stripped) - len(ctx) + 1):
        if stripped[i:i + len(ctx)] == ctx:
            hits.append(i)
    if len(hits) != 1:
        print('!! 锚点匹配 %d 次（要求恰好 1 次）: %s  ctx=%s' % (len(hits), why, ctx))
        sys.exit(1)
    plan.append((hits[0] + len(ctx) - 1, weight, why))

# 从后往前插入，行号不受影响
plan.sort(key=lambda t: -t[0])
for idx, weight, why in plan:
    lines.insert(idx + 1, '    font-weight: %d;' % weight)
    print('插入 font-weight: %d  ← %s（第 %d 行之后）' % (weight, why, idx + 1))

out = '\n'.join(lines)
if '--dry' in sys.argv:
    print('dry-run：未写文件')
    sys.exit(0)
io.open(PATH, 'w', encoding='utf-8', newline='\n').write(out)
print('已写入 %s（新增 %d 行）' % (PATH, len(plan)))
