#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""造 mock 目录变体（取证用）：复制一份 mock 目录，可选删掉若干相对路径。

用途：给「同一探针 before/after」留证——例如把 api 复制成 api-tmp-noq9items 并删掉
v1/quotes/q9/items/index，就能在同一个载体页上跑出「fixture 缺失 → 报错」的红基线，
再对原目录跑出绿。

用法:
  python .agents/state/make-mock-variant.py <src> <dst> [relpath ...]   # 复制并删除
  python .agents/state/make-mock-variant.py --clean <dst>               # 删除变体目录

<src>/<dst> 是 .agents/state/h5-measure 下的目录名（相对名，避免 Windows 路径拼接问题）。
"""
import os
import shutil
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "h5-measure")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--clean":
        target = os.path.join(BASE, args[1])
        if os.path.isdir(target):
            shutil.rmtree(target)
            print("removed %s" % target)
        else:
            print("not found %s" % target)
        return 0
    src = os.path.join(BASE, args[0])
    dst = os.path.join(BASE, args[1])
    drops = args[2:]
    if not os.path.isdir(src):
        print("src not found: %s" % src)
        return 1
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    removed = []
    for rel in drops:
        target = os.path.join(dst, rel.replace("/", os.sep))
        if os.path.isdir(target):
            shutil.rmtree(target)
            removed.append(rel + "/")
        elif os.path.isfile(target):
            os.remove(target)
            removed.append(rel)
        else:
            print("WARN 不存在，未删除：%s" % rel)
    print("created %s (src=%s) removed=%s" % (dst, args[0], removed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
