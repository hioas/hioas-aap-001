#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把本页截图文件名里的手写时间戳改成真实拍摄时间（09:32 → 09:21，取自 PNG 的 mtime）。

- `logs/screenshots/<old>.png` → `<new>.png`（logs/ 被 gitignore，仅为本地一致）
- `.agents/state/evidence/<old>.png` → `<new>.png`（入库的审计件，用 git mv）
- 三处文本引用（决策台账 / 状态文件 / 台账 CSV）同步替换
"""
import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OLD = "20260916-0932-序号2-工作台-图例统一口径D3-h5-430宽"
NEW = "20260916-0921-序号2-工作台-图例统一口径D3-h5-430宽"

TARGETS = [
    os.path.join(ROOT, ".agents", "state", "aap-decisions.md"),
    os.path.join(ROOT, ".agents", "state", "aap-tdd-state.md"),
    os.path.join(ROOT, ".agents", "state", "aap-feature-status.csv"),
]


def main():
    log_old = os.path.join(ROOT, "logs", "screenshots", OLD + ".png")
    log_new = os.path.join(ROOT, "logs", "screenshots", NEW + ".png")
    ev_old = os.path.join(ROOT, ".agents", "state", "evidence", OLD + ".png")
    ev_new = os.path.join(ROOT, ".agents", "state", "evidence", NEW + ".png")

    if os.path.isfile(log_old):
        shutil.move(log_old, log_new)
        print("renamed (logs): %s" % os.path.basename(log_new))
    if os.path.isfile(ev_old):
        subprocess.check_call(["git", "mv", ev_old, ev_new], cwd=ROOT)
        print("git mv (evidence): %s" % os.path.basename(ev_new))

    for path in TARGETS:
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        if OLD not in text:
            print("no ref in %s" % os.path.basename(path))
            continue
        with io.open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace(OLD, NEW))
        print("updated %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
