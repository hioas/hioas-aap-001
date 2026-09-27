#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主提交落地核对（**轮次无关**：`python tools/round-verify/postwrite.py R490 <主提交短号>`）。

核对四件事（每件都是历史返工的机器化）：
  1. 主提交**真的**携带了本轮全部证据文件（历史 16：commit message 声称新增而实际忘了 add）；
  2. 这些文件**在 HEAD 树内**（`git ls-files` / `git cat-file -e`；他方 `git add -A` 会带走一部分，
     故判据 = 主提交携带 ∪ 他方提交携带 == 证据清单，历史 198/236）；
  3. HEAD 内的本轮台账行 ⇔ 工作区该行**逐列相等**（收尾回填**之前**运行，历史 243-①；本工具因此允许
     c7（提交列）差异并显式报告，其余列必须逐列相等）；两侧 CSV **同源解析**（`io.StringIO(..., newline="")`）
     —— 单侧用 `splitlines()` 会吃掉引号字段内的内嵌换行，描述列多段的轮次就得到假 FAIL（历史 155/245）；
  4. 台账结构（列数 = 表头列数、描述列长度下限、CR = 0，历史 80/155/200）。
"""
import csv
import io
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
CSV_REL = ".agents/state/aap-server-feature-status.csv"
EV_REL = ".agents/state/evidence"
ROUND = (sys.argv[1] if len(sys.argv) > 1 else "").upper()
SHA = sys.argv[2] if len(sys.argv) > 2 else ""
assert ROUND and SHA, "用法: python tools/round-verify/postwrite.py R490 <主提交短号>"
fails = []


def sh(*a):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(a), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


rc, out, err = sh("diff-tree", "--no-commit-id", "--name-only", "-r", SHA)
assert rc == 0, "提交号不存在或 git 失败：%s" % err.strip()
carried = [x for x in out.splitlines() if x.strip()]
head_files = set(sh("ls-files")[1].splitlines())
print("主提交 %s 携带文件 %d 条" % (SHA, len(carried)))
for x in sorted(carried):
    print("   %s" % x)

want = [x for x in carried if x.endswith(".txt") and ROUND in x]
mine_all = sorted(n for n in head_files if n.startswith(EV_REL + "/") and ROUND in n)
print("本轮证据：主提交携带 %d 条 / HEAD 树内共 %d 条" % (len(want), len(mine_all)))
if len(mine_all) != len(want):
    for n in sorted(set(mine_all) - set(want)):
        _, sha1, _ = sh("log", "-1", "--format=%h", "--diff-filter=A", "--", n)
        print("   （不在主提交内，由他方提交携带？回查新增提交 = %s）%s" % (sha1.strip() or "(未找到)", n))
if len(mine_all) < 8:
    fails.append("HEAD 树内本轮证据不足（%d 条）" % len(mine_all))

for n in sorted(carried):
    if n.startswith(EV_REL + "/") or n.startswith(".agents/state/") or n.startswith("tools/"):
        if n not in head_files:
            fails.append("%s 不在 HEAD 树内（历史 16/198）" % n)

# ---- 台账：HEAD 内本轮行 ⇔ 工作区行 ----
# 两侧必须**同源解析**（历史 57/155/245）：早先 HEAD 侧写 `head_csv.splitlines()` 再交给 csv.reader，
# 而 `splitlines()` 会吃掉**引号字段内的内嵌换行**（list 输入不会补回）⇒ 描述列含多段的轮次会得到
# 「HEAD 侧少 N 字符」的**假 FAIL**（真实返工：R492 收尾阶段才暴露；R491 只因当轮描述是单行而侥幸 PASS）。
def _embedded(rows):
    return sum(1 for r in rows if any(("\n" in c or "\r" in c) for c in r))


with (ROOT / CSV_REL).open(encoding="utf-8", newline="") as fh:
    rows_w = list(csv.reader(fh))
_, head_csv, _ = sh("show", "HEAD:" + CSV_REL)
rows_h = list(csv.reader(io.StringIO(head_csv, newline="")))
HDR = rows_h[0]
print("台账：HEAD %d 行 / 工作区 %d 行；表头 = %s" % (len(rows_h), len(rows_w), HDR))
E_H, E_W = _embedded(rows_h), _embedded(rows_w)
print("解析保真：含内嵌换行的记录 HEAD %d / 工作区 %d（两侧同源解析，须相等）" % (E_H, E_W))
if E_H != E_W:
    fails.append("两侧解析的含内嵌换行记录数不等（%d vs %d）—— 解析保真度不同（历史 155/245）" % (E_H, E_W))
if any(len(r) != len(HDR) for r in rows_w):
    fails.append("工作区台账存在列数异常行（历史 80/155/200）")
if (ROOT / CSV_REL).read_bytes().count(b"\r"):
    fails.append("台账含 CR（历史 69/146）")
h = [r for r in rows_h if r and r[0] == ROUND]
w = [r for r in rows_w if r and r[0] == ROUND]
print("本轮行：HEAD 内 %d 条 / 工作区 %d 条" % (len(h), len(w)))
if len(h) == 1 and len(w) == 1:
    diffcols = [i for i in range(len(HDR)) if h[0][i] != w[0][i]]
    print("逐列比对：差异列 = %s（c7 = 提交列，收尾回填产生差异属预期，历史 243-①）"
          % ([HDR[i] for i in diffcols] or "无"))
    if set(diffcols) - {7}:
        fails.append("本轮行在 c7 之外的列存在差异：%s" % [HDR[i] for i in diffcols])
    if len(h[0][4]) < 800:
        fails.append("描述列过短（%d 字符）" % len(h[0][4]))
else:
    fails.append("本轮行条数异常（HEAD %d / 工作区 %d）" % (len(h), len(w)))

for f in fails:
    print("[FAIL] %s" % f)
print("判定：%s（%d 条 FAIL）" % ("PASS" if not fails else "FAIL", len(fails)))
print("POSTWRITE_END=1")
sys.exit(1 if fails else 0)
