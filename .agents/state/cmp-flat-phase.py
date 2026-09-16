#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把「扁平单段的老留证」与「新载体页的某个 phase」逐字段对比（跨代探针对比）。

背景：序号 2 的建页留证 `measure-序号2-修后.json` 是扁平结构（无 phase 包层），
而本轮新载体页 `__measure-workbench.html` 输出 phase1/phase2/... 分组。
`review-compare.py` 按 phase 分组比对，遇到这种跨代文件会看不到公共 phase → 本脚本补齐。

用法:
  python .agents/state/cmp-flat-phase.py <old_flat.json> <new.json> <phase> [字段名 ...]
  省略字段名 = 比对两侧都存在的全部键。
"""
import io
import json
import os
import sys


def load(p):
    """兼容三种留证：纯 JSON、`MEASURE_JSON:{...}` 单行、多行拼接（用 raw_decode 取第一整个对象）。"""
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    text = text.strip()
    if text.startswith("MEASURE_JSON:"):
        text = text[len("MEASURE_JSON:"):]
    text = text.lstrip()
    try:
        return json.loads(text)
    except ValueError:
        return json.JSONDecoder().raw_decode(text)[0]


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    old = load(sys.argv[1])
    new = load(sys.argv[2])
    phase = sys.argv[3]
    fields = sys.argv[4:]
    if phase not in new:
        print("新文件没有 phase %s（有：%s）" % (phase, sorted(new)))
        return 1
    cur = new[phase]
    if not fields:
        fields = sorted(set(old) & set(cur))
    same, diff, only_old = [], [], []
    for k in fields:
        if k not in cur:
            only_old.append(k)
            continue
        if old.get(k) == cur.get(k):
            same.append(k)
        else:
            diff.append((k, old.get(k), cur.get(k)))
    print("对比 %s（老留证）vs %s[%s]：公共键 %d → 相同 %d / 不同 %d / 老留证独有 %d"
          % (os.path.basename(sys.argv[1]), os.path.basename(sys.argv[2]), phase, len(fields), len(same), len(diff), len(only_old)))
    for k, o, n in diff:
        print("  DIFF  %-22s 老=%s  新=%s" % (k, json.dumps(o, ensure_ascii=False)[:90], json.dumps(n, ensure_ascii=False)[:90]))
    if only_old:
        print("  （老留证独有键，新探针未输出：%s）" % ", ".join(only_old))
    return 0


if __name__ == "__main__":
    sys.exit(main())
