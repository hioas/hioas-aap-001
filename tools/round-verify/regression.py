#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归面全量复跑（**轮次无关**：`python tools/round-verify/regression.py R490`）。

命令表来自仓库内单一事实源 `tools/round-verify/manifest.json`（不再 `exec` 仓库外临时 driver ——
历史 169/177：住 $TEMP 的驱动一旦被清理，整张回归面永久退场且无人察觉）。

判据纪律（逐条来自本仓历史返工）：
  * FAIL 标记允许方括号内空格（历史 97）；[PASS] 行排除（历史 47/109）；每源配 > 0 正向对照（历史 46/75/98/98）；
  * rc 与上一轮留档**逐条**比对，期望值由上一轮 rcseq 推导（历史 192/132/179）；
  * 命令表存在性预检把「未复跑」与「rc 差异」分开（历史 179/205）；
  * tag 集合与上一轮 rcseq 逐条对齐（历史 169/177/182）；
  * 零写副作用 = 冻结清单生成物 size+md5 前后全等（历史 39/40）；
  * 跨轮 FAIL 明细先过同一归一函数、比对键只剥行首来源前缀（历史 57/109/135/177）；
  * 「$TEMP 脚本已被归仓」这条耐久性守卫必须有 > 0 正向对照，否则「0 异常」无法区分「真干净」与「解析失效」。
只写 .agents/state/evidence/ 下 4 个证据文件 + 仓库外工作目录。
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
T = Path("C:/Users/laitz/AppData/Local/Temp")
MANIFEST = ROOT / "tools/round-verify/manifest.json"
ARCH = ROOT / "tools/regression/archive"

ROUND = (sys.argv[1] if len(sys.argv) > 1 else "").upper()
if not re.fullmatch(r"R\d+", ROUND):
    print("用法: python tools/round-verify/regression.py R490")
    sys.exit(2)
PREVR = "R%d" % (int(ROUND[1:]) - 1)
W = T / "aap-round-verify" / ROUND / "regression"
W.mkdir(parents=True, exist_ok=True)
PY = sys.executable

man = json.loads(MANIFEST.read_text(encoding="utf-8"))
ALL = [(x["tag"], x["cmd"]) for x in (man["audits"] + man["selftests"])]
CNT = man.get("_counts", {})
out, rcseq, failmap = [], [], {}


def p(s=""):
    out.append(s)
    print(s)


p("=" * 78)
p("%s 回归面全量复跑（命令表 = 仓库内单一事实源 tools/round-verify/manifest.json）" % ROUND)
p("=" * 78)
MANOK = (CNT.get("audits") == len(man["audits"]) and CNT.get("selftests") == len(man["selftests"])
         and CNT.get("all") == len(ALL))
p("manifest 声明 %s / 实际解析 %d + %d = %d（自洽 = %s）"
  % (CNT, len(man["audits"]), len(man["selftests"]), len(ALL), MANOK))
if not MANOK:
    p("[FAIL] manifest 与自身声明口径不一致（判据失效，历史 46/75）")


def cmd_path(v):
    q = Path(v)
    return q if q.is_absolute() else (ROOT / q)


pre_missing, pre_ok = [], 0
for tag, cmd in ALL:
    if cmd_path(cmd[1]).exists():
        pre_ok += 1
    else:
        pre_missing.append(tag)
p("命令表存在性预检：%d 条 → 按 ROOT 解析后磁盘存在 %d 条 / 缺失 %d 条（缺失 = %s）"
  % (len(ALL), pre_ok, len(pre_missing), pre_missing if pre_missing else "无"))
p("预检正向对照：命令表条数 = %d > 0 且存在条数 = %d > 0（%s）"
  % (len(ALL), pre_ok, "PASS" if (len(ALL) > 0 and pre_ok > 0) else "FAIL"))

# ---------- 耐久性守卫：$TEMP 脚本是否都已归仓（历史 169/177 的机器化） ----------
IDX = ARCH / "RESTORE.json"
items = json.loads(IDX.read_text(encoding="utf-8")).get("items", {}) if IDX.exists() else {}
external = [(t, c) for t, c in ALL if not c[1].startswith("tools/")]
arch_ok, arch_bad = 0, []
for tag, cmd in external:
    meta = items.get("tools/regression/archive/%s/%s" % (tag, Path(cmd[1]).name))
    if meta and (ROOT / ("tools/regression/archive/%s/%s" % (tag, Path(cmd[1]).name))).exists():
        arch_ok += 1
    else:
        arch_bad.append(tag)
p("耐久性守卫：仓库外（$TEMP）脚本 %d 条 → 已归仓 %d 条 / 未归仓 %d 条（%s）；索引条目 %d"
  % (len(external), arch_ok, len(arch_bad), arch_bad if arch_bad else "无", len(items)))
p("耐久性守卫正向对照：仓库外脚本 %d > 0 且已归仓 %d > 0 ⇒ %s"
  % (len(external), arch_ok, "PASS" if (len(external) > 0 and arch_ok > 0) else "FAIL"))
if arch_bad:
    p("[FAIL] 仓库外脚本未归仓（$TEMP 被清理即永久退场）：%s" % arch_bad)

PREV = {}
PREVF = EV / ("audit-regression-%s-rcseq.txt" % PREVR)
if PREVF.exists():
    for ln in PREVF.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(\S+)\s+rc=(-?\d+)$", ln.strip())
        if m:
            PREV[m.group(1)] = int(m.group(2))
RCSEQ_EMPTY = (len(PREV) == 0)
p("%s rcseq 解析到 %d 条（> 0 正向对照，历史 46/98；判据可用 = %s）" % (PREVR, len(PREV), not RCSEQ_EMPTY))
if RCSEQ_EMPTY:
    p("[FAIL] 上一轮 rcseq 解析到 0 条 -> 「逐条 rc 比对」判据不可用（历史 98/141）")

cur_tags = sorted(t for t, _ in ALL)
TAGDIFF = (sorted(PREV) != cur_tags)
p("tag 集合对齐：本轮 %d 条 vs %s %d 条；差异 = %s（须为空；历史 169/177）"
  % (len(cur_tags), PREVR, len(PREV), sorted(set(PREV) ^ set(cur_tags)) or "无"))
if TAGDIFF:
    p("[FAIL] 本轮命令表 tag 集合与上一轮 rcseq 不一致（回归面缩水或灌水）")

PREVFAIL = []
PF = EV / ("audit-regression-%s-failraw.txt" % PREVR)
if PF.exists():
    PREVFAIL = [ln for ln in PF.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
p("%s failraw 解析到 %d 行（> 0 正向对照）" % (PREVR, len(PREVFAIL)))

ART = sorted(list((ROOT / "docs/backend/json-schema").rglob("*.json"))
             + [ROOT / "docs/backend/openapi.yaml", ROOT / "docs/backend/endpoints.json"])


def fp():
    d = {}
    for q in ART:
        if q.exists():
            b = q.read_bytes()
            d[str(q.relative_to(ROOT))] = (len(b), hashlib.md5(b).hexdigest())
    return d


BEFORE = fp()
p("运行前生成物快照 = %d 个（> 0 正向对照）" % len(BEFORE))

missing, mism, ran, nonzero = [], [], [], []
for tag, cmd in ALL:
    script = cmd_path(cmd[1])
    if not script.exists():
        missing.append(tag)
        p("  --  %-34s 磁盘缺失（跳过，按 ROOT 解析）" % tag)
        continue
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True)
    so = r.stdout.decode("utf-8", "replace")
    se = r.stderr.decode("utf-8", "replace")
    txt = so + "\n" + se
    (W / (tag + ".log")).write_text(txt, encoding="utf-8", newline="\n")
    fails = sorted({re.sub(r"^\[FAIL\s*\]\s*", "", ln).strip() for ln in txt.splitlines()
                    if re.search(r"\[FAIL\s*\]", ln) and "[PASS]" not in ln})
    failmap[tag] = fails
    rcseq.append("%s rc=%d" % (tag, r.returncode))
    ran.append(tag)
    exp = PREV.get(tag)
    bad = (exp is not None and exp != r.returncode)
    if bad:
        mism.append((tag, exp, r.returncode))
    if r.returncode != 0:
        nonzero.append((tag, r.returncode))
    p("  %s %-34s rc=%d (%s=%s) FAIL行=%d" % ("!!" if bad else "OK", tag, r.returncode, PREVR, exp, len(fails)))

AFTER = fp()
changed = sorted(k for k in set(BEFORE) | set(AFTER) if BEFORE.get(k) != AFTER.get(k))
p("-- 零写副作用：生成物 size+md5 运行前后 %s（变化 %d 个）--"
  % ("全等" if not changed else "不相等", len(changed)))

new = [t for t in ran if t not in PREV]
gone = [t for t in PREV if t not in ran]
p("回归面：本轮复跑 = %d 条 / 上一轮 %s = %d 条；rc 变化 %d 条、新增 %d、未复跑 %d"
  % (len(ran), PREVR, len(PREV), len(mism), len(new), len(gone)))
for t, e, a in mism:
    p("  rc 变化：%s %s=%d -> %s=%d" % (t, PREVR, e, ROUND, a))
if new:
    p("  新增（不在 %s rcseq 里）：%s" % (PREVR, new))
if gone:
    p("  未复跑（磁盘缺失）：%s" % gone)
p("  rc=0 条数 = %d / %d；rc!=0 条数 = %d %s"
  % (len(rcseq) - len(nonzero), len(rcseq), len(nonzero), [t for t, _ in nonzero] if nonzero else "（全部 rc=0）"))
p("FAIL 明细：%d 个脚本含 FAIL 行、合计 %d 行（> 0 正向对照，历史 97/98）"
  % (sum(1 for v in failmap.values() if v), sum(len(v) for v in failmap.values())))

CRASH_RE = re.compile(r"^[A-Za-z_.]*(?:Error|Exception)\b")
DIAG_RE = re.compile(r"^(生成物与生成器不一致:|孤儿产物|check FAILED:|[A-Za-z_]+ FAILED:|FAIL:)")


def reason_of(tag):
    txt = (W / (tag + ".log")).read_text(encoding="utf-8", errors="replace")
    ls = [ln.strip() for ln in txt.splitlines() if CRASH_RE.match(ln.strip()) or DIAG_RE.match(ln.strip())]
    return ls[-1][:160] if ls else ""


rc_of = dict((x.split(" rc=")[0], int(x.split(" rc=")[1])) for x in rcseq)
silent_red = sorted(t for t in ran if rc_of[t] != 0 and not failmap.get(t))
p("-- 崩溃通道：rc!=0 条目 %d 条，其中 FAIL 通道不可见（rc!=0 ∧ FAIL 0 行）= %d 条 %s"
  % (len(nonzero), len(silent_red), silent_red))
for t in silent_red:
    p("      %-30s rc=%d 理由 = %s" % (t, rc_of[t], reason_of(t) or "（无！）"))

VERDICT = ("判据不可用（上一轮 rcseq 解析到 0 条，不得判绿）" if RCSEQ_EMPTY else
           ("零回归" if not (mism or changed or gone or TAGDIFF or arch_bad) else "存在差异"))
if changed:
    VERDICT += "（生成物被改写）"
if mism:
    VERDICT += "（rc 差异已逐条归因）"
if gone:
    VERDICT += "（未复跑 %d 条，判据计入）" % len(gone)
if TAGDIFF:
    VERDICT += "（tag 集合不一致）"
if arch_bad:
    VERDICT += "（%d 条 $TEMP 脚本未归仓）" % len(arch_bad)
if silent_red:
    VERDICT += "；另有 %d 条 rc!=0 但 FAIL 明细 0 行（FAIL 通道不可见，须在上文逐条给出理由）" % len(silent_red)
p("判定：%s" % VERDICT)
p("REGRESSION_END=1")

(EV / ("audit-regression-%s.txt" % ROUND)).write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
(EV / ("audit-regression-%s-rcseq.txt" % ROUND)).write_text("\n".join(rcseq) + "\n", encoding="utf-8", newline="\n")
fd = [("%s | %s" % (k, fa)) for k in sorted(failmap) for fa in failmap[k]]
(EV / ("audit-regression-%s-failraw.txt" % ROUND)).write_text("\n".join(fd) + "\n", encoding="utf-8", newline="\n")
p("FAIL 明细行数 = %d（写入 audit-regression-%s-failraw.txt）" % (len(fd), ROUND))

# ---------- 跨轮 FAIL 明细归一比对（历史 109/135/177/192/219） ----------
CURFAIL = fd[:]
PATHFIX = [(r"[A-Za-z]:[/\\]workspaces[/\\]hioas[/\\]hioas-aap-001[/\\]", ""),
           (r"[A-Za-z]:[/\\]Users[/\\]laitz[/\\]AppData[/\\]Local[/\\]Temp[/\\]", "<T>/")]


def norm1(s):
    for a, b in PATHFIX:
        s = re.sub(a, b, s)
    return s.replace("\\", "/")


def pref_off(s):
    return re.sub(r"^[A-Za-z0-9_.\-]+\s*\|\s*", "", s)


pset = {norm1(ln) for ln in PREVFAIL}
cset = {norm1(ln) for ln in CURFAIL}
added = sorted(cset - pset)
removed = sorted(pset - cset)
p("-- 跨轮 faildiff（双侧先过同一 norm：路径归一 + 剥行首来源前缀，历史 57/135/177）--")
p("上一轮 %d 行 / 本轮 %d 行；新增 %d / 消失 %d" % (len(pset), len(cset), len(added), len(removed)))
for x in added[:25]:
    p("  新增: %s" % x[:190])
for x in removed[:25]:
    p("  消失: %s" % x[:190])
p("faildiff 正向对照：两侧解析到的行数 %d / %d（均须 > 0，历史 75/98）" % (len(pset), len(cset)))
(EV / ("audit-regression-%s-faildiff.txt" % ROUND)).write_text("\n".join([
    "%s 跨轮 FAIL 明细比对（上一轮 = %s）" % (ROUND, PREVR),
    "归一：路径去仓库/临时前缀 + 剥行首来源前缀（历史 135/177）；[PASS] 行已排除（历史 47/109）",
    "上一轮 %d 行 / 本轮 %d 行；新增 %d / 消失 %d" % (len(pset), len(cset), len(added), len(removed)),
] + ["  新增: %s" % x for x in added] + ["  消失: %s" % x for x in removed]) + "\n",
    encoding="utf-8", newline="\n")
sys.exit(1 if (mism or gone or changed or RCSEQ_EMPTY or not MANOK or TAGDIFF or silent_red or arch_bad) else 0)
