#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只读校验：生成的 openapi.yaml 是否可被标准 YAML 解析器解析（结构有效性证据）。

用法： python tools/check-openapi-parses.py [<openapi.yaml 路径>]
退出码：0 = 解析成功；1 = 解析失败或缺少解析器。
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv: list[str]) -> int:
    path = argv[0] if argv else os.path.join(ROOT, "docs", "backend", "openapi.yaml")
    try:
        import yaml  # type: ignore
    except ImportError:
        print("SKIP: 本机无 PyYAML，无法做标准解析器校验（不影响 --check 的一致性校验）")
        return 1
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    paths = doc.get("paths") or {}
    ops = sum(1 for item in paths.values() if isinstance(item, dict)
              for method in item if method in ("get", "post", "put", "delete", "patch"))
    print(f"OK: {os.path.relpath(path, ROOT)} 可解析；paths={len(paths)} operations={ops}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
