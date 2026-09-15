#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Set the LEASE line in .agents/state/aap-tdd-state.md. Usage: lease-set.py <holder> <until>"""
import io, re, sys

path = ".agents/state/aap-tdd-state.md"
holder = sys.argv[1]
until = sys.argv[2]
text = io.open(path, encoding="utf-8").read()
line = "LEASE: %s until %s" % (holder, until)
text = re.sub(r"(?m)^LEASE:.*$", line, text, count=1)
io.open(path, "w", encoding="utf-8").write(text)
print(u"\n".join(text.splitlines()[:3]))
