#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Report installed versions of build/test toolchain packages."""
import io, json, os

BASE = r"E:\workspaces\hioas\hioas-aap-001\aap-client\node_modules"
PKGS = ["typescript", "vue-tsc", "vitest", "@vue/test-utils", "@vue/tsconfig", "vite"]

for p in PKGS:
    f = os.path.join(BASE, p.replace("/", os.sep), "package.json")
    try:
        with io.open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        print("%-20s %s" % (p, data.get("version")))
    except Exception as exc:
        print("%-20s MISSING (%s)" % (p, exc))
