# -*- coding: utf-8 -*-
"""序号 22 证据合成（红/绿/交互/像素对账判读 → 单一转录文件 + 结构带结论追记）。

用法: python .agents/state/gen-22-checks-evidence.py
产出（都在 .agents/state/evidence/）：
  green-序号22-checks-设计期望值.txt      绿：两轮独立测量（267 条 checks 全通过）
  review-序号22-checks-报告.md            本轮报告（自动汇总 + 手写结论拼装）
  cmp-序号22-设计PNGvs实现截图-结构带.txt 追加未命中逐条判读（比对工具只打命中/未命中清单）
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


def show_phases(path):
    out = subprocess.run([PY, os.path.join(STATE, "show-phases.py"), path],
                         capture_output=True, text=True, encoding="utf-8")
    return (out.stdout or "") + (out.stderr or "")


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


lines = []
lines.append("序号 22「【工作台与我的】我的与用量概览 2」（page-22-2 / /pages/usage/index）设计期望值 checks 绿基线")
lines.append("载体页 __measure-usage.html（430 宽 iframe · 267 条 checks）· 两轮独立测量")
lines.append("命令: bash .agents/state/review-measure.sh 22 __measure-usage.html .agents/state/h5-measure/api-22 5341")
lines.append("")
for run in (1, 2):
    p = os.path.join(EVD, "review-序号22-run%d.json" % run)
    lines.append("---- run%d（%s）----" % (run, os.path.basename(p)))
    lines.append(show_phases(p).strip())
    lines.append("")

with io.open(os.path.join(EVD, "green-序号22-checks-设计期望值.txt"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")

# ---- 交互出口转录 ----
ilines = []
ilines.append("序号 22 交互相（三出口 · 各两轮 · serve 实收请求行逐字节比对）")
for tag, desc in (
    ("back", "返回 = navigation（navigateBack；H5 无栈 → hash 不变 + 零写请求）"),
    ("month", "月份 picker = client-only + 重新取数（uni-picker 覆盖层 → 确认 → 第二次 GET 带新 month）"),
    ("detail", "「查看逐日 / 逐模型明细」= 无落点（画布无明细页）→ no-op：hash 不变 / 无 toast / 无新请求"),
):
    ilines.append("")
    ilines.append("==== %s：%s ====" % (tag, desc))
    for run in (1, 2):
        p = os.path.join(EVD, "review-序号22-%s-run%d.json" % (tag, run))
        d = load(p)
        p2 = d.get("phase2") or {}
        ilines.append("  run%d phase2: %s" % (run, json.dumps(p2, ensure_ascii=False)[:420]))
        rq = io.open(os.path.join(EVD, "requests-序号22-%s-run%d.txt" % (tag, run)), encoding="utf-8").read().strip().split("\n")
        ilines.append("  run%d requests(%d): %s" % (run, len(rq), " | ".join(x[:64] for x in rq)))
    a = io.open(os.path.join(EVD, "requests-序号22-%s-run1.txt" % tag), encoding="utf-8").read()
    b = io.open(os.path.join(EVD, "requests-序号22-%s-run2.txt" % tag), encoding="utf-8").read()
    ilines.append("  两轮 requests：%s" % ("逐字节相同" if a == b else "不一致"))

with io.open(os.path.join(EVD, "interactions-序号22-三出口.txt"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(ilines) + "\n")

# ---- 像素对账未命中判读（追加到结构带文件末尾）----
judge = """

=== 未命中逐条判读（本轮） ===
未命中 8 条（内容列 4 + 明细/进度列 4）= 2 类，均非页面缺陷：
① 内容列 [107, 350, 353, 359] —— 汇总卡投影的**衰减尾**：x=200 列实测
   设计 336..345 带 (238,240,243)→(243,245,247) 后 349..359 仍有 (252..254) 淡染、360+ 纯白；
   实现 336..339 同值、341..344 (241,243,246)、348+ 即纯白 → 起点与峰值一致，只有 Figma/Chrome 的模糊衰减步长差
   （1~3/255；与序号 5/9/12/15 登记的同类现象一致）→ 非页面缺陷。
② 明细/进度列 [839, 843, 869, 873] —— 成本行右对齐值 H5 回退字体的**字距/右留白**：
   设计 '¥4,120' 墨迹 353..391（右留白 3px）、实现 355..393（右留白 1px）→ 两者都是右对齐到 394、墨迹同宽 39，
   差 2px 属字体度量（合成墨迹段 3 段 vs 1 段）→ 非页面缺陷。
结构带命中 39 / 未命中 8；命中处位移中位 0（内容列 min −3 / max +3，0 位移 14 个）→ 无整体平移。
"""
with io.open(os.path.join(EVD, "cmp-序号22-设计PNGvs实现截图-结构带.txt"), "a", encoding="utf-8", newline="\n") as fh:
    fh.write(judge)

print("wrote green-序号22-checks-设计期望值.txt / interactions-序号22-三出口.txt / cmp 判读追记")
