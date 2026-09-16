# -*- coding: utf-8 -*-
"""序号 23 证据合成（红基线转录 / 绿基线转录 / 交互相转录）。

用法:
  python .agents/state/gen-23-checks-evidence.py red      # 把当前 review-序号23-checks-run{1,2}.json 作为红基线归档
  python .agents/state/gen-23-checks-evidence.py green    # 作为绿基线归档（调用前先跑 review-measure.sh）
"""
import io
import json
import os
import subprocess
import sys

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
EVD = os.path.join(ROOT, ".agents/state/evidence")
STATE = os.path.join(ROOT, ".agents/state")
PY = sys.executable
mode = (sys.argv[1] if len(sys.argv) > 1 else "green").lower()


def show_phases(path):
    out = subprocess.run([PY, os.path.join(STATE, "show-phases.py"), path],
                         capture_output=True, text=True, encoding="utf-8")
    return ((out.stdout or "") + (out.stderr or "")).strip()


def cmp_runs(a, b, phase):
    out = subprocess.run([PY, os.path.join(STATE, "cmp-measure-runs.py"), a, b, phase],
                         capture_output=True, text=True, encoding="utf-8")
    return ((out.stdout or "") + (out.stderr or "")).strip()


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


runs = [os.path.join(EVD, "review-序号23-checks-run%d.json" % n) for n in (1, 2)]
for p in runs:
    if not os.path.exists(p):
        raise SystemExit("missing " + p)

fails = []
for n in (1, 2):
    d = load(runs[n - 1])
    ph = d.get("phase1") or d
    fails.append(ph.get("checkFailCount"))

lines = []
if mode == "red":
    lines.append("序号 23「【工作台与我的】我的设置 2」（page-23-2 / /pages/settings/index）设计期望值 checks —— 红基线")
    lines.append("载体页 __measure-settings.html（430 宽 iframe · 207 条 checks）· 源码未改（修复前）+ 同一份最终版探针两轮")
else:
    lines.append("序号 23「【工作台与我的】我的设置 2」（page-23-2 / /pages/settings/index）设计期望值 checks —— 绿基线")
    lines.append("载体页 __measure-settings.html（430 宽 iframe · 207 条 checks）· 修偏差后（同一份探针）两轮")
lines.append("命令: bash .agents/state/review-measure.sh 23-checks __measure-settings.html .agents/state/h5-measure/api-23 539x")
lines.append("")
for n in (1, 2):
    lines.append("---- run%d（review-序号23-checks-run%d.json · checkFailCount=%s）----" % (n, n, fails[n - 1]))
    lines.append(show_phases(runs[n - 1]))
    lines.append("")
lines.append("---- 两轮独立测量逐字段比对（cmp-measure-runs.py phase1）----")
lines.append(cmp_runs(runs[0], runs[1], "phase1"))

name = ("red-序号23-checks-设计期望值偏差.txt" if mode == "red"
        else "green-序号23-checks-设计期望值.txt")
with io.open(os.path.join(EVD, name), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print("wrote", name)
print("checkFailCount per run:", fails)

if mode == "red":
    for n in (1, 2):
        dst = os.path.join(EVD, "red-序号23-checks-run%d.json" % n)
        io.open(dst, "w", encoding="utf-8", newline="\n").write(
            io.open(runs[n - 1], encoding="utf-8").read())
        print("archived", os.path.basename(dst))
