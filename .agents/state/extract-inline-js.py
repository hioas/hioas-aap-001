#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract the last <script>...</script> block of an HTML file to a .js file (syntax check helper).

Usage: extract-inline-js.py <html> <out.js>
"""
import io
import re
import sys

html = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
io.open(sys.argv[2], "w", encoding="utf-8").write(blocks[-1] if blocks else "")
print("blocks=%d wrote=%s" % (len(blocks), sys.argv[2]))
