#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R158 覆盖缺口复核（v2）：先解析目录变量映射，再解析 str(VAR / "name") 引用，
把本轮缺口集合与**上一轮（R157）的分类留档**逐条比对
（坑 178 的修正版 + 坑 57：两侧走同一个 key `aap-rNN/name.py`）。

纪律（坑 46/75/98）：每个解析器都配 `> 0` 正向对照；「集合相等」前先断言两侧条数都 > 0，
否则空集合恒等 → 空转假绿。
本轮为纯巡检轮、不新增不变量类，期望结论 = 缺口集合与 R157 留档完全一致、③ 真缺口 = 0 → 回归面不扩面。
另：`tools/` 侧 driver 覆盖（R109 补齐的安全门禁）本轮只做**只读事实量化**，见 evidence/gap-tools-scan-R158.txt。
"""
import re
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
T = Path("C:/Users/laitz/AppData/Local/Temp")
drv = (T / "aap-r158-work/r158-regression.py").read_text(encoding="utf-8")

# ---- 留档解析器（双写法）+ 分支正向对照 ----
CANON = re.compile(r"^([①②③])\s+(aap-r[^\s]+\.py)(?:\s|$)", re.M)
GAPFMT = re.compile(r"^GAP\s+([①②③])\s+(aap-r[^\s]+\.py)(?:\s|$)", re.M)


def parse_archive(txt: str) -> dict:
    out = {}
    for m in CANON.finditer(txt):
        out[m.group(2)] = m.group(1)
    for m in GAPFMT.finditer(txt):
        out[m.group(2)] = m.group(1)
    return out


_fx = [("① aap-r45-spotcheck/spotcheck-pagination-order.py  旧版本 → 被取代", "①"),
       ("GAP ② aap-r41/spotcheck-pagination.py", "②")]
_ok = 0
for _s, _exp in _fx:
    _d = parse_archive(_s)
    assert len(_d) == 1 and list(_d.values())[0] == _exp, "解析器失效：合成夹具 %r → %s" % (_s, _d)
    _ok += 1
assert _ok == 2, "留档解析器正向对照不足：%d/2" % _ok
print("留档解析器自检通过 %d/2（规范写法 + 上一轮的 GAP 写法，均为正向对照）" % _ok)

# ---- 解析 driver 的引用集（判据与 R83/R85 gap-scan 一致）----
var2dir = {}
for m in re.finditer(r'^(R\d+[A-Z]*)\s*=\s*Path\(T \+ "([^"]+)"\)', drv, re.M):
    var2dir[m.group(1)] = m.group(2)
assert len(var2dir) > 20, "解析器失效：目录变量只解析到 %d 个" % len(var2dir)
assert "R158W" in var2dir, "解析器失效：未识别带后缀的目录变量（如 R158W）→ 新写法会被误报为缺口"

used = set()
for m in re.finditer(r'str\((R\d+[A-Z]*) / "([^"]+)"\)', drv):
    assert m.group(1) in var2dir, "引用了未定义的目录变量 %s" % m.group(1)
    used.add("%s/%s" % (var2dir[m.group(1)], m.group(2)))
used |= {m.group(1) for m in re.finditer(r'"(tools/[A-Za-z0-9_.\-]+\.py)"', drv)}
assert len(used) > 40, "解析器失效：只解析到 %d 个引用" % len(used)

cand = []
for d in sorted(T.glob("aap-r*")):
    if not d.is_dir():
        continue
    for p in sorted(d.glob("*.py")):
        n = p.name.lower()
        if "spotcheck" in n or "audit" in n:
            cand.append(("%s/%s" % (d.name, p.name), p))
assert len(cand) > 0, "解析器失效：候选脚本解析到 0 个" % len(cand)

ROUND_DRIVER = re.compile(r"^(audit-regression|make-|gen-|notify|ledger|backfill|closeout|evidence|regression|"
                          r"r\d+-|covcheck|check-scripts|probe|r\d+-|csv|normlf|cov|fix|dbg|explore|recon|"
                          r"mut-|dump|write-|skill-|worktree|normalize|prepend|run-to-file|copy-)")
gap = []
for rel, p in cand:
    if rel in used:
        continue
    if ROUND_DRIVER.search(p.name.lower()):
        continue
    gap.append(rel)

# ---- 读上一轮（R157）的分类留档（同一 key：`aap-rNN/name.py`）----
prev_path = EV / "audit-regression-R157-coverage-gap.txt"
prev_txt = prev_path.read_text(encoding="utf-8", errors="replace")
prev = parse_archive(prev_txt)
assert len(prev) > 0, "解析器失效：R157 留档里一条分类行都没解析到（%s）" % prev_path
assert set(prev.values()) <= {"①", "②", "③"}, "解析器失效：出现未知分类 %s" % (set(prev.values()) - {"①", "②", "③"})
print("R157 留档解析到分类行 %d 条（正向对照：> 0）" % len(prev))

cur = set(gap)
prevs = set(prev)
only_cur = sorted(cur - prevs)
only_prev = sorted(prevs - cur)

tally = {}
for rel in gap:
    tally[prev.get(rel, "?")] = tally.get(prev.get(rel, "?"), 0) + 1

L = ["== R158 覆盖缺口复核（R80/R82 已补回 R45–R56 十类；R83–R157 复核真缺口 0，本轮再核对无残留缺口，坑 169/177） ==",
     "**本扫描的范围（须诚实声明）**：只扫 `aap-r*` 临时目录里名字含 spotcheck/audit 的脚本 → **`tools/` 目录不在范围内**；",
     "本轮另按坑 169/177/182 做了 `tools/` 侧的同族**只读事实量化**（见 evidence/gap-tools-scan-R158.txt）：",
     "`tools/*.py` 共 27 个、driver 引用 27 个 → **缺口 = 0**（`tools/evidence-secrets.py` 系 R109 补入 driver 那一轮的修复；本轮只复核该事实，不扩面）。",
     "判据：解析 `VAR = Path(T + \"dir\")` 映射 + `str(VAR / \"name\")` 引用（坑 178 的修正版）；",
     "      两侧（本轮 gap 集合 / R157 留档分类行）走同一个 key `aap-rNN/name.py`（坑 57）",
     "留档解析器：支持规范写法（行首 ①②③）与上一轮的 `GAP <cls> <key>` 写法，合成夹具正向对照 2/2",
     "driver 里解析到的目录变量 = %d 个（正向对照：> 20）" % len(var2dir),
     "driver 引用脚本数 = %d（正向对照：> 40）" % len(used),
     "候选（名字含 spotcheck/audit）= %d 个（正向对照：> 0）" % len(cand),
     "已在 driver 内的候选 = %d" % len([1 for rel, _ in cand if rel in used]),
     "本轮缺口集合 = %d 条（正向对照：> 0）" % len(cur),
     "R157 留档分类行 = %d 条（正向对照：> 0）" % len(prevs),
     "",
     "缺口集合与 R157 留档比对：仅本轮有 = %d %s；仅留档有 = %d %s → %s"
     % (len(only_cur), only_cur, len(only_prev), only_prev,
        "逐条一致 %d/%d" % (len(cur), len(prevs)) if not only_cur and not only_prev else "存在差异，需逐条归因"),
     "按 R157 分类计票：① 旧版本 = %d；② 语义重复 = %d；③ 真缺口 = %d；未分类 = %d"
     % (tally.get("①", 0), tally.get("②", 0), tally.get("③", 0), tally.get("?", 0)),
     ""]
for g in gap:
    L.append("%s %s" % (prev.get(g, "?"), g))
L += ["",
      "结论：%s（R80/R82 的十类补入已全部在序列内；本轮缺口集合与 R157 留档逐条一致、③ 真缺口 = 0 "
      "→ **本扫描的缺口集合无变化**；另按坑 169/177/182 复核 `tools/` 侧 driver 覆盖：`tools/*.py` 27 个、"
      "driver 引用 27 个 → 缺口 = 0（该侧由 R109 补齐；本轮只做只读事实量化、不扩面），"
      "见 evidence/gap-tools-scan-R158.txt；R109 为纯巡检轮 + 1 处覆盖缺口修复，复核链由 R85 补入 driver），"
      "见 evidence/audit-regression-R158.txt 的 rc 对齐段）"
      % ("无残留缺口、无新增缺口" if (not only_cur and not only_prev and tally.get("③", 0) == 0)
         else "需人工复核（差异 %d 条或真缺口 %d 条）" % (len(only_cur) + len(only_prev), tally.get("③", 0)))]

assert not only_cur and not only_prev, "缺口集合与 R157 留档不一致：仅本轮 %s / 仅留档 %s" % (only_cur, only_prev)
assert tally.get("③", 0) == 0, "出现 ③ 真缺口 %d 条：%s" % (tally.get("③", 0),
                                                       [g for g in gap if prev.get(g) == "③"])
out = EV / "audit-regression-R158-coverage-gap.txt"
out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
print("\n".join(L))
print("CR =", out.read_bytes().count(b"\r"))
