# -*- coding: utf-8 -*-
"""列出某帧设计树里所有文本叶子的声明值（fs / 字体 / lineHeight / 宽高 / 文案）。

用法: python .agents/state/leaves-5.py <page-id> [--fs 12]

用途: 判「同帧同字号的显式 height」—— 判据① 的第一手尺子。
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(REPO, '.calicat', 'raw', 'pages')


def walk(node, out, depth=0):
    if not isinstance(node, dict):
        return
    t = node.get('type')
    td = node.get('layer_data') or node
    if isinstance(node.get('layer_data'), dict):
        td = node['layer_data']
    if t in ('rectangle', 'paragraph', 'text') or td.get('type') in ('rectangle', 'paragraph', 'text'):
        if td.get('content'):
            out.append(td)
    for ch in (td.get('children') or []):
        walk(ch, out, depth + 1)


def main():
    pid = sys.argv[1]
    want_fs = None
    if '--fs' in sys.argv:
        want_fs = float(sys.argv[sys.argv.index('--fs') + 1])
    root = json.load(io.open(os.path.join(RAW, pid, 'design.tree.json'), encoding='utf-8'))
    leaves = []
    walk(root, leaves)
    print('文本叶子 %d 条（%s）' % (len(leaves), pid))
    print('%-10s %5s %-24s %6s %8s %8s  %s' % ('id', 'fs', 'font', 'lh', 'w', 'h', 'text'))
    for lf in leaves:
        fs = lf.get('fontSize')
        if want_fs is not None and fs != want_fs:
            continue
        print('%-10s %5s %-24s %6s %8s %8s  %s' % (
            str(lf.get('id'))[:8], fs, str(lf.get('fontFamily'))[:24], lf.get('lineHeight'),
            lf.get('width'), lf.get('height'), (lf.get('content') or '')[:34]))


if __name__ == '__main__':
    main()
