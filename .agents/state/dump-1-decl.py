"""dump-1-decl.py — 打印 page-1-2 设计树声明值（供序号 1 剩余待办核对）。

用法: python .agents/state/dump-1-decl.py [pageId] [--grep 关键词]
输出行: 缩进 + <id>|<type>|<name>| w/h=… fs=… fam=… lh=… fill=… stroke=… effects=…
"""
import io
import json
import re
import sys

page = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'page-1-2'
kw = None
if '--grep' in sys.argv:
    kw = sys.argv[sys.argv.index('--grep') + 1]

data = json.load(io.open('.calicat/raw/pages/%s/design.tree.json' % page, encoding='utf-8'))
if isinstance(data, dict):
    nodes = data.get('nodes') or data.get('children') or data.get('layer_data') or [data]
else:
    nodes = data


def col(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        if 'hex' in v:
            return str(v['hex'])
        if 'color' in v:
            return str(v['color'])
        r = v.get('r')
        if r is not None:
            return 'rgb(%s,%s,%s,%s)' % (round(r * 255), round(g.get('g', 0) * 255), round(g.get('b', 0) * 255), g.get('a', 1))
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def fills(color_key):
    f = color_key
    if not f:
        return None
    if isinstance(f, dict):
        f = [f]
    if isinstance(f, list) and f and isinstance(f[0], dict):
        out = []
        for x in f:
            c = x.get('color') or x.get('hex') or x
            out.append(col(c))
        return '/'.join(str(o) for o in out)
    return str(f)


lines = []


def walk(n, depth):
    if not isinstance(n, dict):
        return
    nid = n.get('id') or n.get('layer_id') or '-'
    name = n.get('name') or n.get('layer_name') or ''
    parts = ['  ' * depth + '%s|%s|%s' % (nid, n.get('type') or '', name)]
    if n.get('width') is not None or n.get('height') is not None:
        parts.append('w=%s h=%s' % (n.get('width'), n.get('height')))
    for k, lbl in (('fontSize', 'fs'), ('fontFamily', 'fam'), ('lineHeight', 'lh'), ('textAlignHorizontal', 'alignH'), ('textAlignVertical', 'alignV')):
        if n.get(k) is not None:
            parts.append('%s=%s' % (lbl, n.get(k)))
    fl = fills(n.get('fills') or n.get('fill') or n.get('backgroundColor'))
    if fl:
        parts.append('fill=%s' % fl)
    st = n.get('strokes') or n.get('stroke') or n.get('border')
    if st:
        parts.append('stroke=%s' % fills(st) if not isinstance(st, dict) or 'color' in st or 'hex' in st else 'stroke=%s' % json.dumps(st, ensure_ascii=False))
    if n.get('strokeAlign') or n.get('strokeAlign'):
        parts.append('strokeAlign=%s' % n.get('strokeAlign'))
    if n.get('strokeWeight') is not None:
        parts.append('strokeW=%s' % n.get('strokeWeight'))
    if n.get('effects'):
        parts.append('effects=%s' % json.dumps(n.get('effects'), ensure_ascii=False))
    txt = n.get('characters') or n.get('content') or n.get('text')
    if isinstance(txt, str) and txt:
        parts.append('T="%s"' % txt.replace('\n', '\\n')[:60])
    line = ' '.join(str(p) for p in parts)
    if kw is None or kw in line:
        lines.append(line)
    for k in ('children', 'kids'):
        ch = n.get(k)
        if isinstance(ch, list):
            for c in ch:
                walk(c, depth + 1)
        elif isinstance(ch, dict):
            walk(ch, depth + 1)


for n in nodes:
    walk(n, 0)

print('\n'.join(lines))
print('--- total lines: %d' % len(lines))
