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
  * **崩溃通道的完整理由行集参与跨轮比对**（sha256）：rc 逐条比对只能看见「rc 变了」这一维，
    而「常驻红通道**内容**变了、rc 没变」此前完全不可见（历史 98/187/219——「必须为空/不得变化」型
    判据的口径失效反而更「合规」；本仓活例 = 覆盖缺口通道把新增缺口吃进去而零告警）。
    判据口径：上一轮证据里 `CRASHCHAN tag=… sha256=…` 段与本轮逐通道比对，
    **理由行集必须完整**（不截断、不只取末行，历史 218/230）；上一轮无该段 ⇒ 判据不可用，**不得判绿**（历史 141）；
  * 「$TEMP 脚本已被归仓」这条耐久性守卫必须有 > 0 正向对照，否则「0 异常」无法区分「真干净」与「解析失效」；
  * 归仓守卫的判据是**逐字节**（sha256 三方一致：索引 ⇔ 归档 ⇔ 原文件），**不是**「归档文件存在」——
    原文件在归仓之后被就地改写过时，存在性判据照样判绿，而「归档 = 仍在使用的那份脚本」这个前提已不成立
    （归档退化成陈旧快照 ⇒ `--restore` 还原出过期脚本，历史 180 的留档侧）。`--selftest` 逐分支给判别力实测。
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

ROUND_ARGV = [a for a in sys.argv[1:]]
SELFTEST = "--selftest" in ROUND_ARGV
_p = [a for a in ROUND_ARGV if a != "--selftest"]
ROUND = ((_p[0] if _p else ("R0" if SELFTEST else ""))).upper()
if not re.fullmatch(r"R\d+", ROUND):
    print("用法: python tools/round-verify/regression.py R490 [--selftest]")
    sys.exit(2)
PREVR = "R%d" % (int(ROUND[1:]) - 1)
W = T / "aap-round-verify" / ROUND / "regression"
if not SELFTEST:
    W.mkdir(parents=True, exist_ok=True)
PY = sys.executable
ARCH_KEY = "tools/regression/archive"


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------- 崩溃/诊断行 + 路径归一：**定义在 --selftest 之前**，自测与生产路径共用同一判据（历史 230） ----------
CRASH_RE = re.compile(r"^[A-Za-z_.]*(?:Error|Exception)\b")
DIAG_RE = re.compile(r"^(生成物与生成器不一致:|孤儿产物|check FAILED:|[A-Za-z_]+ FAILED:|FAIL:)")
PATHFIX = [(r"[A-Za-z]:[/\\]workspaces[/\\]hioas[/\\]hioas-aap-001[/\\]", ""),
           (r"[A-Za-z]:[/\\]Users[/\\]laitz[/\\]AppData[/\\]Local[/\\]Temp[/\\]", "<T>/")]


def normpath(s):
    """路径归一（**唯一一份**，历史 191：同一口径两处副本 = 只改一处的半条规则）。"""
    for a, b in PATHFIX:
        s = re.sub(a, b, s)
    return s.replace("\\", "/")


def crash_reason(txt):
    """崩溃通道的**完整**理由 → (sha256, 行数, 首行前 160 字)。

    为什么要完整行集：只取末行 + 截断 160 字（旧写法）时，超长理由（本仓实测 4000+ 字符的缺口清单）
    在**中间**插入一条新条目而末行不变 ⇒ 比对判绿（历史 218 的同族：取证/判据的取值形态）。
    """
    ls = [ln.strip() for ln in txt.splitlines() if CRASH_RE.match(ln.strip()) or DIAG_RE.match(ln.strip())]
    if not ls:
        return "", 0, ""
    full = "\n".join(normpath(x) for x in ls)
    return hashlib.sha256(full.encode("utf-8")).hexdigest(), len(ls), ls[0][:160]


def crash_diff(prev, cur):
    """跨轮比对（**纯函数**，`--selftest` 与生产路径同源；历史 230）。

    返回 (changed, added, gone, usable)：`changed` = 两侧同现但理由 sha256 不同 —— 这正是
    rc 逐条比对看不见、faildiff 也看不见（FAIL 明细为 0）的那一维（历史 98/187/219）。
    两侧都空是**期望态**（无崩溃通道）；上一轮无留档而本轮有 ⇒ usable=False（历史 141：不得判绿）。
    """
    common = sorted(set(prev) & set(cur))
    changed = sorted(t for t in common if prev[t] != cur[t])
    added = sorted(set(cur) - set(prev))
    gone = sorted(set(prev) - set(cur))
    usable = bool(prev) or not cur
    return changed, added, gone, usable


def durability(allx, arch_dir, index_path):
    """归仓耐久性守卫（**纯函数**：`--selftest` 用合成夹具调用，判据与生产路径同源）。

    三档判据：① 索引里有该 tag 的条目；② 归档文件存在且 sha256 == 索引值；
    ③ **原文件存在且 sha256 == 索引值**（逐字节三方一致）。
    ②③ 任一不成立 = bad（归档与在用脚本分叉 ⇒ `--restore` 还原出陈旧脚本，历史 180）；
    原文件缺失 = lost（可用 `--restore` 还原，单独成档，不与 bad 混计）。
    另查**双向覆盖**：索引里存在、却不在本轮命令表里的归档 = orphan（历史 57/68：索引必须被夹住）。
    """
    items = json.loads(index_path.read_text(encoding="utf-8")).get("items", {}) if index_path.exists() else {}
    external = [(t, c) for t, c in allx if not c[1].startswith("tools/")]
    ok, bad, lost, why = 0, [], [], []
    keys = set()
    for tag, cmd in external:
        key = "%s/%s/%s" % (ARCH_KEY, tag, Path(cmd[1]).name)
        keys.add(key)
        meta = items.get(key)
        a = arch_dir / tag / Path(cmd[1]).name
        o = Path(cmd[1])
        if not meta:
            bad.append(tag)
            why.append("%s（索引无条目）" % tag)
            continue
        if not a.exists():
            bad.append(tag)
            why.append("%s（归档缺失）" % tag)
            continue
        if sha256_of(a) != meta.get("sha256"):
            bad.append(tag)
            why.append("%s（归档内容与索引 sha256 不一致）" % tag)
            continue
        if not o.exists():
            lost.append(tag)
            continue
        if sha256_of(o) != meta.get("sha256"):
            bad.append(tag)
            why.append("%s（原文件与归档分叉：在用脚本已被就地改写，归档退化为陈旧快照）" % tag)
            continue
        ok += 1
    orphan = sorted(k for k in items if k not in keys)
    return {"external": external, "ok": ok, "bad": bad, "why": why, "lost": lost,
            "orphan": orphan, "index_n": len(items)}


def run_selftest():
    """归仓守卫的判别力实测：每分支一条反例 + 基线正向对照 + 注入必须真的改到源码（历史 46/66/75/94/98）。

    只写仓库外工作目录（`$TEMP/aap-round-verify/R0/selftest/`），每个用例独立子目录、不删任何既有目录。
    """
    rep, rc = [], 0
    fx = T / "aap-round-verify" / ROUND / "selftest"

    def case(name, cond, info=""):
        rep.append(("[PASS]" if cond else "[FAIL]", name, info))
        return bool(cond)

    def build(sub, live=b"A", archived=None, arch_file=None,
              entries=(("A", "a.py"), ("B", "b.py")), index=True, extra=None):
        """夹具构造：`live` = 原文件当前内容；`archived` = 索引记录的在归档时的校验和来源；
        `arch_file` = 归档文件当前内容（默认 = archived）。三者分开才能分别打中 ②/③ 两个分支。"""
        d = fx / sub
        arch_d, live_d = d / "archive", d / "live"
        (arch_d / "A").mkdir(parents=True, exist_ok=True)
        (arch_d / "B").mkdir(parents=True, exist_ok=True)
        live_d.mkdir(parents=True, exist_ok=True)
        arch_a = archived if archived is not None else live
        file_a = arch_file if arch_file is not None else arch_a
        (live_d / "a.py").write_bytes(live)
        (live_d / "b.py").write_bytes(b"B")
        for t, n in entries:
            (arch_d / t / n).write_bytes(file_a if t == "A" else b"B")
        items = {}
        if index:
            items["%s/A/a.py" % ARCH_KEY] = {"original": str(live_d / "a.py"),
                                             "sha256": hashlib.sha256(arch_a).hexdigest()}
            items["%s/B/b.py" % ARCH_KEY] = {"original": str(live_d / "b.py"),
                                             "sha256": hashlib.sha256(b"B").hexdigest()}
        if extra:
            items.update(extra)
        (d / "RESTORE.json").write_text(json.dumps({"items": items}, sort_keys=True) + "\n",
                                        encoding="utf-8", newline="\n")
        allx = [("A", [PY, str(live_d / "a.py")]), ("B", [PY, str(live_d / "b.py")])]
        return durability(allx, arch_d, d / "RESTORE.json"), live_d

    def redo(sub):
        """对同一夹具目录重跑判据（夹具被就地改动后必须**重新调用** durability —— 历史 230：
        不拿「刚写下去的字节」当裁判，也不复用改动前的读数）。"""
        d = fx / sub
        allx = [("A", [PY, str(d / "live" / "a.py")]), ("B", [PY, str(d / "live" / "b.py")])]
        return durability(allx, d / "archive", d / "RESTORE.json")

    D, _ = build("c1-baseline")
    case("S1 基线三方一致 → ok=2 / bad=0 / lost=0 / orphan=0",
         D["ok"] == 2 and D["bad"] == [] and D["lost"] == [] and D["orphan"] == [],
         "ok=%d bad=%s lost=%s orphan=%s" % (D["ok"], D["bad"], D["lost"], D["orphan"]))
    case("S1p 正向对照：仓库外脚本 %d > 0 ∧ ok %d > 0" % (len(D["external"]), D["ok"]),
         len(D["external"]) > 0 and D["ok"] > 0)
    D2, live2 = build("c2-orig-drift", live=b"A2", archived=b"A")
    mut2 = hashlib.sha256((live2 / "a.py").read_bytes()).hexdigest() != hashlib.sha256(b"A").hexdigest()
    case("S2 注入「归档后原文件被就地改写」→ 恰好点名 A（分支③ 原文件 ≠ 归档）", D2["bad"] == ["A"],
         "bad=%s why=%s" % (D2["bad"], D2["why"]))
    case("S2m 注入锚点真的改到了源码（逐字节变化）", mut2)
    case("S2d 判别力：FAIL 集合相对基线恰好新增 {A}", set(D2["bad"]) - set(D["bad"]) == {"A"})
    case("S2l 原文件仍在 → 不得误记为 lost", D2["lost"] == [], "lost=%s" % D2["lost"])
    D3, _ = build("c3-arch-drift", arch_file=b"A2")
    case("S3 注入「归档内容被就地改写」→ 恰好点名 A（分支② 归档 ≠ 索引）", D3["bad"] == ["A"],
         "bad=%s why=%s" % (D3["bad"], D3["why"]))
    _d4, _ = build("c4-arch-missing")
    (fx / "c4-arch-missing" / "archive" / "B" / "b.py").unlink()
    D4 = redo("c4-arch-missing")
    case("S4 B 的归档文件缺失（索引条目仍在）→ 恰好点名 B", D4["bad"] == ["B"],
         "bad=%s why=%s" % (D4["bad"], D4["why"]))
    _d5, _ = build("c5-orig-lost")
    (fx / "c5-orig-lost" / "live" / "a.py").unlink()
    D5 = redo("c5-orig-lost")
    case("S5 原文件已丢失 → lost=[A] ∧ bad=[]（两档分开，不混计）",
         D5["lost"] == ["A"] and D5["bad"] == [], "lost=%s bad=%s" % (D5["lost"], D5["bad"]))
    D6, _ = build("c6-index-empty", index=False)
    case("S6 索引为空 → 两条全 bad（判据不可用时不得判绿）", sorted(D6["bad"]) == ["A", "B"],
         "bad=%s" % D6["bad"])
    D7, _ = build("c7-index-orphan", extra={"%s/Z/z.py" % ARCH_KEY: {"original": "x", "sha256": "0" * 64}})
    case("S7 索引里有本轮命令表之外的归档 → orphan 点名",
         D7["orphan"] == ["%s/Z/z.py" % ARCH_KEY] and D7["bad"] == [],
         "orphan=%s" % D7["orphan"])
    D8 = durability([("X", [PY, "tools/x.py"])], fx / "c8" / "archive", fx / "c8" / "RESTORE.json")
    case("S8 空夹具（仓库外脚本 0 条）→ 正向对照必须转红（防空转判绿）",
         not (len(D8["external"]) > 0 and D8["ok"] > 0), "external=%d" % len(D8["external"]))
    case("S9 夹具只写仓库外（零写副作用）", ROOT != fx and ROOT not in fx.parents, str(fx))

    # ---- 崩溃通道跨轮比对（纯函数 crash_reason / crash_diff，判据与生产路径同源） ----
    # 合成理由刻意做成「超长且只在**中段**变化」：这正是旧写法（只取末行 + 截断 160 字）判绿的形态。
    base_txt = "".join("    at frame %d\n" % i for i in range(200)) + \
        "AssertionError: 缺口集合不一致：%s\n" % ", ".join("aap-r%d-work/audit-x-%d.py" % (i, i) for i in range(1, 40))
    h0, n0, head0 = crash_reason(base_txt)
    ch, ad, go, us = crash_diff({"A": h0}, {"A": h0})
    case("S10 基线：两侧同现且理由一致 → changed/added/gone 皆空 ∧ usable=True",
         (ch, ad, go, us) == ([], [], [], True), "changed=%s added=%s gone=%s usable=%s" % (ch, ad, go, us))
    case("S10p 正向对照：理由行集解析到 %d 行 > 0 ∧ 首行非空" % n0, n0 > 0 and bool(head0),
         "nlines=%d head=%r" % (n0, head0[:40]))
    txt2 = base_txt.replace("aap-r20-work", "aap-r20-work-新增缺口")
    h1, n1, head1 = crash_reason(txt2)
    ch2 = crash_diff({"A": h0}, {"A": h1})[0]
    case("S11 注入「常驻红通道的理由在中段变化」→ 恰好点名 A（rc 未变 ⇒ rc 通道与 FAIL 明细都看不见）",
         ch2 == ["A"], "sha %s -> %s" % (h0[:12], h1[:12]))
    case("S11m 注入锚点真的改到了源码（理由 sha256 逐字节变化）", h1 != h0)
    case("S11t 旧写法（只取末行 + 截断 160 字）在该注入下判绿 ⇒ 证明新判据的取值形态是必需的",
         head0 == head1 and h0 != h1, "head 相同 = %s" % (head0 == head1))
    case("S12 判别力：changed 相对基线**恰好新增** {A}", set(ch2) - set(ch) == {"A"},
         "delta=%s" % (set(ch2) - set(ch)))
    case("S13 A 转绿（本轮不再 rc!=0）→ gone 点名 ∧ changed 为空（不得报成变化）",
         crash_diff({"A": h0}, {})[:3] == ([], [], ["A"]))
    case("S14 上一轮无留档而本轮有 → usable=False（历史 141：判据不可用时不得判绿）",
         crash_diff({}, {"A": h0})[3] is False)
    case("S15 两侧同时为空（本就不存在崩溃通道）→ usable=True ∧ 三集合皆空",
         crash_diff({}, {}) == ([], [], [], True))
    case("S16 新增通道 → added 点名（rc 通道已覆盖该转移，此处只作信息档）",
         crash_diff({"A": h0}, {"A": h0, "B": h1})[1] == ["B"])

    print("=" * 78)
    print("%s 装置判据判别力实测（合成夹具；判据与生产路径同源 = durability() / crash_reason() / crash_diff()）" % ROUND)
    print("=" * 78)
    for st, name, info in rep:
        print("%s %s%s" % (st, name, (" ｜ " + info) if info else ""))
    npass = sum(1 for s, _, _ in rep if s == "[PASS]")
    print("-" * 78)
    print("自测：%d PASS / %d FAIL（共 %d 例）" % (npass, len(rep) - npass, len(rep)))
    rc = 0 if npass == len(rep) else 1
    print("SELFTEST_END=%d" % (1 if rc == 0 else 0))
    return rc


if SELFTEST:
    sys.exit(run_selftest())

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

# ---------- 耐久性守卫：$TEMP 脚本是否都已归仓（历史 169/177 的机器化；判据 = 逐字节三方一致） ----------
IDX = ARCH / "RESTORE.json"
DUR = durability(ALL, ARCH, IDX)
arch_ok, arch_bad = DUR["ok"], DUR["bad"]
p("耐久性守卫（三方逐字节：索引 ⇔ 归档 ⇔ 原文件）：仓库外（$TEMP）脚本 %d 条 → 一致 %d 条 / 异常 %d 条（%s）"
  % (len(DUR["external"]), arch_ok, len(arch_bad), DUR["why"] if DUR["why"] else "无"))
p("  另查：原文件已丢失 %d 条（%s；可用 tools/round-verify/archive-temp-scripts.py --restore 还原）；"
  "索引条目 %d / 索引孤儿 %d（%s）"
  % (len(DUR["lost"]), DUR["lost"] if DUR["lost"] else "无", DUR["index_n"],
     len(DUR["orphan"]), DUR["orphan"] if DUR["orphan"] else "无"))
p("耐久性守卫正向对照：仓库外脚本 %d > 0 且三方一致 %d > 0 ⇒ %s"
  % (len(DUR["external"]), arch_ok, "PASS" if (len(DUR["external"]) > 0 and arch_ok > 0) else "FAIL"))
if arch_bad:
    p("[FAIL] 归仓守卫异常（$TEMP 被清理即永久退场 / 归档与在用脚本分叉）：%s" % arch_bad)
if DUR["orphan"]:
    p("[FAIL] 归仓索引含本轮命令表之外的归档（索引膨胀或 tag 被改名，历史 169/177/182）：%s" % DUR["orphan"])

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

rc_of = dict((x.split(" rc=")[0], int(x.split(" rc=")[1])) for x in rcseq)
silent_red = sorted(t for t in ran if rc_of[t] != 0 and not failmap.get(t))
p("-- 崩溃通道：rc!=0 条目 %d 条，其中 FAIL 通道不可见（rc!=0 ∧ FAIL 0 行）= %d 条 %s"
  % (len(nonzero), len(silent_red), silent_red))
CURCRASH = {}
for t in silent_red:
    h, n, head = crash_reason((W / (t + ".log")).read_text(encoding="utf-8", errors="replace"))
    CURCRASH[t] = h
    p("      %-30s rc=%d 理由 = %s" % (t, rc_of[t], head or "（无！）"))
    # 机器可读行（下一轮据此比对**内容**，不只比 rc）—— 唯一入口，展示行也从同一函数取值。
    p("      CRASHCHAN tag=%s rc=%d sha256=%s nlines=%d head=%s"
      % (t, rc_of[t], h or "none", n, head or "（无！）"))

# ---------- 崩溃通道跨轮比对（历史 98/187/219：rc 不变而**内容变了**的通道此前完全不可见） ----------
CH_RE = re.compile(r"^\s*CRASHCHAN tag=(\S+) rc=(-?\d+) sha256=(\S+) nlines=(\d+) head=(.*)$", re.M)
PREVREG = EV / ("audit-regression-%s.txt" % PREVR)
PREVCRASH = {}
if PREVREG.exists():
    for m in CH_RE.finditer(PREVREG.read_text(encoding="utf-8", errors="replace")):
        PREVCRASH[m.group(1)] = m.group(3)
CRASH_CHANGED, CRASH_ADDED, CRASH_GONE, CRASH_USABLE = crash_diff(PREVCRASH, CURCRASH)
p("-- 崩溃通道跨轮比对（判据：上一轮同处「rc!=0 ∧ FAIL 0 行」的通道，其**完整理由行集** sha256 必须不变；"
  "rc 逐条比对只能看见「rc 变了」，FAIL 明细又为 0 ⇒ 内容变化此前零可见性）--")
p("上一轮 %s 证据里的 CRASHCHAN 段解析到 %d 条 / 本轮 %d 条（正向对照：两侧都 > 0，或两侧同时为 0）"
  % (PREVR, len(PREVCRASH), len(CURCRASH)))
p("可比通道（两侧同现）= %d 条；理由变化 = %d 条 %s；本轮新增通道 = %s；本轮转绿（消失）= %s"
  % (len(set(PREVCRASH) & set(CURCRASH)), len(CRASH_CHANGED), CRASH_CHANGED or "无",
     CRASH_ADDED or "无", CRASH_GONE or "无"))
if not CRASH_USABLE:
    p("[FAIL] 崩溃通道内容比对判据不可用：上一轮证据 %s 无 CRASHCHAN 段（本判据自本轮建立，"
      "按历史 141/98 判据不可用时不得判绿 ⇒ 本轮计入非零退出，下一轮起自动生效）" % PREVREG.name)
for t in CRASH_CHANGED:
    p("[FAIL] 崩溃通道内容变化（rc 未变，故 rc 通道与 FAIL 明细都看不见）: %s  sha256 %s -> %s"
      % (t, PREVCRASH[t][:12], CURCRASH[t][:12]))

VERDICT = ("判据不可用（上一轮 rcseq 解析到 0 条，不得判绿）" if RCSEQ_EMPTY else
           ("零回归" if not (mism or changed or gone or TAGDIFF or arch_bad or DUR["orphan"]
                             or CRASH_CHANGED or not CRASH_USABLE) else "存在差异"))
if changed:
    VERDICT += "（生成物被改写）"
if mism:
    VERDICT += "（rc 差异已逐条归因）"
if gone:
    VERDICT += "（未复跑 %d 条，判据计入）" % len(gone)
if TAGDIFF:
    VERDICT += "（tag 集合不一致）"
if arch_bad:
    VERDICT += "（%d 条归仓守卫异常：归档与在用脚本分叉或缺失）" % len(arch_bad)
if DUR["orphan"]:
    VERDICT += "（索引孤儿 %d 条）" % len(DUR["orphan"])
if DUR["lost"]:
    VERDICT += "（原文件已丢失 %d 条，可用 --restore 还原）" % len(DUR["lost"])
if silent_red:
    VERDICT += "；另有 %d 条 rc!=0 但 FAIL 明细 0 行（FAIL 通道不可见，须在上文逐条给出理由）" % len(silent_red)
if not CRASH_USABLE:
    VERDICT += "（崩溃通道内容比对：上一轮无留档 ⇒ 判据本轮建立）"
if CRASH_CHANGED:
    VERDICT += "（崩溃通道内容变化 %d 条：rc 通道与 FAIL 明细均看不见）" % len(CRASH_CHANGED)
p("判定：%s" % VERDICT)
p("REGRESSION_END=1")

(EV / ("audit-regression-%s.txt" % ROUND)).write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
(EV / ("audit-regression-%s-rcseq.txt" % ROUND)).write_text("\n".join(rcseq) + "\n", encoding="utf-8", newline="\n")
fd = [("%s | %s" % (k, fa)) for k in sorted(failmap) for fa in failmap[k]]
(EV / ("audit-regression-%s-failraw.txt" % ROUND)).write_text("\n".join(fd) + "\n", encoding="utf-8", newline="\n")
p("FAIL 明细行数 = %d（写入 audit-regression-%s-failraw.txt）" % (len(fd), ROUND))

# ---------- 跨轮 FAIL 明细归一比对（历史 109/135/177/192/219） ----------
CURFAIL = fd[:]


# 路径归一**唯一一份**（历史 191：同一口径两处副本 ⇒ 只改一处的半条规则）——崩溃通道与 faildiff 共用。
norm1 = normpath


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
sys.exit(1 if (mism or gone or changed or RCSEQ_EMPTY or not MANOK or TAGDIFF or silent_red
               or arch_bad or DUR["orphan"] or DUR["lost"] or CRASH_CHANGED or not CRASH_USABLE) else 0)
