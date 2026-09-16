# -*- coding: utf-8 -*-
"""查看 textleaf dump 的叶子（含 rect/chain），供行盒判定。

用法:
  python .agents/state/tl-show.py <dump.json> [class 关键字]
"""
import io
import json
import sys


def main():
    path = sys.argv[1]
    d = json.load(io.open(path, encoding='utf-8'))
    leaves = d['leafs'] if isinstance(d, dict) and 'leafs' in d else (d if isinstance(d, list) else [])
    print('n =', len(leaves))
    if not leaves:
        print('no leaves; keys =', list(d.keys()) if isinstance(d, dict) else type(d))
        return
    print('sample:', json.dumps(leaves[0], ensure_ascii=False))
    kw = sys.argv[2] if len(sys.argv) > 2 else None
    for i, lf in enumerate(leaves):
        ch = lf.get('chain') or lf.get('ancestors') or ''
        cs = ch if isinstance(ch, str) else ' '.join(ch)
        if kw and kw not in cs:
            continue
        print('#%02d  cls=%r' % (i, cs))
        print('     %s' % json.dumps(lf, ensure_ascii=False))


main()
