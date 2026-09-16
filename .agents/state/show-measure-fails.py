#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""看一轮 DOM 实测 JSON 的 checkFails 与关键字段（探针自查用）。

用法:
  python .agents/state/show-measure-fails.py <json> [phase] [字段名 ...]
    <json>   例如 .agents/state/evidence/review-序号2-d3-run1.json
    [phase]  phase1 / phase2 ...；省略则自动取第一个含 checks 的 phase
    [字段]   追加打印这些顶层字段（点号分隔的嵌套键也可，如 ringParsed.segments）
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def dig(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else None
        else:
            return None
    return cur


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(BASE), "..", path)
        path = os.path.normpath(os.path.abspath(path))
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    phase = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].startswith("phase") else None
    if phase is None:
        for key in sorted(data.keys()):
            if isinstance(data[key], dict) and "checks" in data[key]:
                phase = key
                break
    block = data.get(phase, {}) if phase else data
    print("file=%s phase=%s" % (os.path.basename(path), phase))
    print("checkCount=%s checkFailCount=%s" % (block.get("checkCount"), block.get("checkFailCount")))
    for item in block.get("checkFails") or []:
        print("  FAIL %s" % item)

    fields = [a for a in sys.argv[3:] if a]
    if len(sys.argv) > 2 and not sys.argv[2].startswith("phase"):
        fields = [a for a in sys.argv[2:] if a]
    for name in fields:
        print("%s = %s" % (name, json.dumps(dig(block, name), ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
