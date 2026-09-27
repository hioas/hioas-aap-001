#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R158 覆盖缺口复核（v2）：先解析目录变量映射，再解析 str(VAR / "name") 引用，把本轮缺口集合与**上一轮（R157）的分类留档**逐条比对
（坑 178 的修正版 + 坑 57：两侧走同一个 key `aap-rNN/name.py`）。

纪律（坑 46/75/98）：每个解析器都配 `> 0` 正向对照；「集合相等」前先断言两侧条数都 > 0，否则空集合恒等 → 空转假绿。
本轮为纯巡检轮、不新增不变量类，期望结论 = 缺口集合与 R157 留档完全一致、③ 真缺口 = 0 → 回归面不扩面。
"""
import subprocess
import sys
import re
from pathlib import Path

T = Path("C:/Users/laitz/AppData/Local/Temp")
WORK = T / "aap-r158-work"
SRC = WORK / "gap-verify-R158-v2.py"
FIX = T / "aap-r158-gapselftest-fixtures"
FIX.mkdir(parents=True, exist_ok=True)
# 坑 216（布局解决范围问题）：注入变体**不写进产物目录**——否则它们会被残留/假自述守卫
# 当成产物扫描，且修完产物后变体仍是旧文本 → 报出假违规。一次性变体一律落在夹具目录的子目录里。
VAR = FIX / "variants"
VAR.mkdir(parents=True, exist_ok=True)
EV = Path("E:/workspaces/hioas/hioas-aap-001/.agents/state/evidence")
REAL_ARCHIVE = EV / "audit-regression-R157-coverage-gap.txt"      # 上一轮留档（v2 写入 = 规范写法）
GAP_ARCHIVE = EV / "audit-regression-R84-coverage-gap.txt"       # GAP 写法留档（供 T3 分支对照）
ARCH_TEXT = REAL_ARCHIVE.read_text(encoding="utf-8", errors="replace")
GAP_TEXT = GAP_ARCHIVE.read_text(encoding="utf-8", errors="replace")

src = SRC.read_text(encoding="utf-8")
ANCHOR = 'prev_path = EV / "audit-regression-R157-coverage-gap.txt"'
assert ANCHOR in src, "注入锚点未命中（坑 66/94）：prev_path 行"
assert src.count(ANCHOR) == 1, "注入锚点非唯一：%d 处" % src.count(ANCHOR)
# 前置正向对照：两份留档的写法确实不同（否则 T3 不是有效分支对照）
assert re.search(r"^[①②③]\s+aap-r", ARCH_TEXT, re.M), "R157 留档不是规范写法"
assert not re.search(r"^GAP\s+[①②③]\s+aap-r", ARCH_TEXT, re.M), "R157 留档竟含 GAP 行（写法未改）"
assert re.search(r"^GAP\s+[①②③]\s+aap-r", GAP_TEXT, re.M), "R84 留档不是 GAP 写法"
print("[PASS] 前置对照：R157 留档 = 规范写法、R84 留档 = GAP 写法（两角色与 R157 版相同、未互换）")

FAIL_RE = re.compile(r"\[FAIL\s*\]")


def run(variant_path):
    p = subprocess.run([sys.executable, str(variant_path)], capture_output=True)
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    return p.returncode, out


# ---------- T0 基线 ----------
rc, ok_out = run(SRC)
assert rc == 0, "T0 基线应当 rc=0，实际 rc=%d\n%s" % (rc, ok_out[-1500:])
assert "留档解析器自检通过 2/2" in ok_out, "T0 基线缺少「留档解析器自检通过 2/2」正向对照\n%s" % ok_out[-1500:]
assert "逐条一致 18/18" in ok_out, "T0 基线缺少「逐条一致 18/18」正向对照\n%s" % ok_out[-1500:]
assert "③ 真缺口 = 0" in ok_out, "T0 基线缺少「③ 真缺口 = 0」\n%s" % ok_out[-1500:]
print("[PASS] T0 基线 rc=0 且含「留档解析器自检通过 2/2」「逐条一致 18/18」「③ 真缺口 = 0」")

cases = []

# ---------- T1 注入：删掉一条分类行（留档少一条 → 集合不等） ----------
lines = ARCH_TEXT.split("\n")
del_idx = next(i for i, ln in enumerate(lines) if ln.startswith("① aap-r45-spotcheck/"))
removed = lines[del_idx]
t1 = "\n".join(lines[:del_idx] + lines[del_idx + 1:])
assert t1 != ARCH_TEXT and removed not in t1, "T1 注入未真的改到源码（坑 66）"
(FIX / "archive-missing-line.txt").write_text(t1, encoding="utf-8", newline="\n")
cases.append(("T1 留档缺一行", "archive-missing-line.txt", "缺口集合与 R157 留档不一致"))

# ---------- T2 注入：把一条 ① 改成 ③（真缺口 1 条，集合仍相等） ----------
t2 = ARCH_TEXT.replace("① aap-r66-spotcheck/spotcheck-state-machine-R66.py",
                       "③ aap-r66-spotcheck/spotcheck-state-machine-R66.py")
assert t2 != ARCH_TEXT, "T2 注入未真的改到源码（坑 66）"
(FIX / "archive-fake-gap.txt").write_text(t2, encoding="utf-8", newline="\n")
cases.append(("T2 伪造真缺口", "archive-fake-gap.txt", "出现 ③ 真缺口"))

for name, fixture, expect in cases:
    vp = VAR / ("gap-verify-%s.py" % name.split()[0].lower())
    body = src.replace(ANCHOR, 'prev_path = Path("C:/Users/laitz/AppData/Local/Temp/'
                               'aap-r158-gapselftest-fixtures/%s")' % fixture)
    assert ANCHOR not in body, "变体里仍残留原锚点"
    assert fixture in body, "变体里未出现夹具路径"
    vp.write_text(body, encoding="utf-8", newline="\n")
    rc, out = run(vp)
    assert rc != 0, "%s：应当转红，实际 rc=0\n%s" % (name, out[-1500:])
    assert expect in out, "%s：未点名目标断言 %r\n%s" % (name, expect, out[-1500:])
    print("[PASS] %s：rc=%d 且点名「%s」（注入真的改到了源码）" % (name, rc, expect))

# ---------- T3 分支对照：换成 GAP 写法留档（R84 那份）→ 必须仍绿 ----------
vp = VAR / "gap-verify-t3.py"
body = src.replace(ANCHOR, 'prev_path = Path("C:/Users/laitz/AppData/Local/Temp/'
                           'aap-r158-gapselftest-fixtures/archive-gapfmt.txt")')
assert ANCHOR not in body and "archive-gapfmt.txt" in body, "T3 变体构造失败"
(FIX / "archive-gapfmt.txt").write_text(GAP_TEXT, encoding="utf-8", newline="\n")
vp.write_text(body, encoding="utf-8", newline="\n")
rc, out = run(vp)
assert rc == 0, "T3 GAP 写法分支：应当 rc=0（读得动 GAP 写法留档），实际 rc=%d\n%s" % (rc, out[-1500:])
assert "逐条一致 18/18" in out, "T3 未复现「逐条一致 18/18」\n%s" % out[-1500:]
print("[PASS] T3 GAP 写法分支：rc=0 且「逐条一致 18/18」（v2 的双写法读取两分支均可核对）")

print("自测汇总：PASS %d / %d（前置对照 1 + T0 基线 + %d 条注入 + T3 分支对照）"
      % (3 + len(cases), 3 + len(cases), len(cases)))
