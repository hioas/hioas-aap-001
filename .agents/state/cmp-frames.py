"""逐层对比两帧设计树（按子节点数量 / 名称），输出结构差异。

用法：python .agents/state/cmp-frames.py <pageA> <pageB>
"""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(page):
    return json.load(open(os.path.join(root, '.calicat', 'raw', 'pages', page, 'design.tree.json'), encoding='utf-8'))


def kids(n):
    return n.get('children') or []


a, b = load(sys.argv[1]), load(sys.argv[2])
path = []


def name(n):
    return '%s[%s]' % (n.get('name'), n.get('type'))


def walk(x, y):
    ca, cb = kids(x), kids(y)
    if len(ca) != len(cb):
        print('CHILD-COUNT %s: A=%d B=%d' % ('/'.join(path + [name(x)]), len(ca), len(cb)))
        print('   A kids: %s' % [name(k) for k in ca])
        print('   B kids: %s' % [name(k) for k in cb])
    for i in range(min(len(ca), len(cb))):
        if ca[i].get('name') != cb[i].get('name'):
            print('NAME%s: A=%s B=%s' % ('' if len(ca) == len(cb) else '(maybe shifted)', name(ca[i]), name(cb[i])))
        path.append(name(x))
        walk(ca[i], cb[i])
        path.pop()


walk(a, b)
print('done')
