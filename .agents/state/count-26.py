#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印 page-26 设计树里若干文本节点的原文与字符数（核对「设计文案长度 vs 实现长度」）。"""
import json
import sys

PATH = '.calicat/raw/pages/page-26/design.tree.json'
KEYS = sys.argv[1:] or ['带出的模型', '报价单号由系统', '请先在上方选择凭证', '首次保存成功后', '报价单名称建议']


def walk(node, out):
    if not isinstance(node, dict):
        return
    t = node.get('text') or node.get('TEXT')
    if isinstance(t, str) and t.strip():
        out.append(t)
    for v in node.values():
        if isinstance(v, dict):
            walk(v, out)
        elif isinstance(v, list):
            for it in v:
                walk(it, out)


def main() -> None:
    data = json.load(open(PATH, encoding='utf-8'))
    texts = []
    walk(data, texts)
    for key in KEYS:
        hits = [t for t in texts if key in t]
        if not hits:
            print('MISS', key)
        for t in hits:
            print(f'len={len(t)} chars · width≈{len(t) * 11}px@11px · {t!r}')
    print('--- 全部文本层数 =', len(texts))


if __name__ == '__main__':
    main()
