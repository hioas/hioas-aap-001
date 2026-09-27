#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立复核探针（**轮次无关**、**只读**；不采信装置自身的判定行）。

用法：
  python tools/round-verify/independent.py <轮次> [--device-change <路径>]... [--no-write]
  python tools/round-verify/independent.py --selftest

为什么有它
----------
历史每轮巡检的「独立复核」都是**现写一份 aux 脚本**（上一轮那版 25,861 字节：硬编码上一轮轮次号 / 上一轮号 /
当轮装置改动文件清单），只活在 `$TEMP/aap-round-verify/<轮次>/aux/`（历史 169/177：系统清理即永久退场），
且每轮都要重踩「机械派生 + 逐处显式修正」那一整族缺陷（技能 `references/pitfalls-round-chain.md` 199–251）。

本工具把它固化成**轮次无关**的可重跑实现（与 `analyze.py` / `regression.py` / `device-report.py` 同一纪律）：
  * 轮次号、被测提交、窗口起止、rc 全部由 `facts-<轮次>.log`（执行器落盘的单一事实源）与**原始 maven 日志**
    读出，源码内**零硬编码纯值**（历史 201/206/243-③）；本文件不得出现任何轮次号字面量（见判据 J9）；
  * 装置改动集合由 `--device-change` **声明**、由 git **独立取证**，判据是「实得集合 == 申报集合」的
    **双向**核对（历史 12/95：自述与事实不一致在两个方向上都要响亮失败）；
  * 每个解析器都是**纯函数（入参 = 文本）**，主判定区只读 ctx（历史 499①/②）——
    判别力自测用合成 ctx 注入缺陷，断言「恰好新增目标判据」（历史 82/93/103：只比明细断言行）。

判据（J1–J9；每条读数都配 `> 0` 正向对照，历史 46/75/98）
--------------------------------------------------------
* J1 facts 完整性与窗口（含并发前置门槛**真的执行**，历史 238/251）
* J2 两轮原始日志独立解析（合计行 / 逐类 / 串行 / 耗时**双写法**，历史 175/228）
* J3 测试面：`@Test` 词边界对账 ∧ 禁用扫描 == 0（不得削弱测试）
* J4 覆盖三处独立读数一致（worktree 归档副本 / 仓库跟踪副本 / `endpoints.json`）
* J5 交付面零改动（**相位感知**：提交前看工作区、提交后看提交链）+ 在途归属 + worktree 回收
* J6 装置面改动 == 申报集合（逐文件点名 · 双向）
* J7 本轮核心证据齐备 ∧ 字节级 CR == 0（历史 69/84/146）
* J8 装置目录轮次无关性（当前轮次号不得出现在装置源码里；判别力对照 = 1）
* J9 本工具的轮次无关性自证（源码内零当前轮次号字面量）

相位（`--phase` 由 git 事实**推导**，不手写）：主提交之前 = 「工作区未提交」，之后 = 「提交链 N 枚」。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
T = Path("C:/Users/laitz/AppData/Local/Temp")
DEV_DIR = ROOT / "tools/round-verify"
END_MARK = "INDEPENDENT_END"
DELIVERY_PREFIXES = ("aap-server/", "docs/", "aap-client/")
# 本轮**自己的**写入前缀（留痕目录 + 装置目录）：窗口内新增的条目必须全部落在这两类里（判据 J5d）。
MY_PREFIXES = (".agents/state/", "tools/")
# 本轮核心证据（由 analyze.py / regression.py 产出）；收尾相位才产生的证据**不在此表内** —— 历史 222：
# 本文件不能把自己、或尚未产生的文件判成缺失。
EVIDENCE_CORE = [
    "round-%s-analysis.txt",
    "green-verify-%s-coverage-fields.txt",
    "green-verify-%s-testcount.txt",
    "green-verify-%s-tested-state.txt",
    "green-verify-%s-full-run1.txt",
    "green-verify-%s-full-run2.txt",
    "audit-regression-%s.txt",
    "audit-regression-%s-rcseq.txt",
    "audit-regression-%s-failraw.txt",
    "audit-regression-%s-faildiff.txt",
    "regression-selftest-%s.txt",
]
REQ_KEYS = ["FACTS_ROUND", "FACTS_WINDOW_START", "FACTS_WINDOW_START_TS", "FACTS_WINDOW_START_ISO",
            "FACTS_WINDOW_END", "FACTS_WINDOW_END_ISO", "FACTS_HEAD_AT_START", "FACTS_HEAD_AT_START_FULL",
            "FACTS_TESTED_COMMIT", "FACTS_TESTED_COMMIT_FULL", "WT_DIRTY_LINES", "FACTS_RUN1_START",
            "FACTS_RUN1_END", "FACTS_RUN1_RC", "FACTS_RUN2_START", "FACTS_RUN2_END", "FACTS_RUN2_RC",
            "ARCH_TEST_FILES", "FACTS_HEAD_AT_END", "FACTS_HEAD_AT_END_FULL", "FACTS_HEAD_ADVANCED_COUNT",
            "PREFLIGHT_OK", "PREFLIGHT_RESULT", "ENV_JPS_REACHABLE", "FACTS_WRITTEN", "WORKTREE_ADD_RC",
            "WORKTREE_REMOVE_RC", "WORKTREE_PATH"]

TOT_RE = re.compile(r"^\[(?:INFO|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)$", re.M)
CLS_RE = re.compile(r"^\[INFO\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+), "
                    r"Time elapsed: [\d.]+ s -- in (\S+)$", re.M)
# maven 耗时**双写法**（历史 175：>=1 分钟写 `mm:ss min`，<1 分钟写 `NN.NNN s`）
ELAPSED_RE = re.compile(r"^\[INFO\] Total time:  (?:(?P<mm>\d+):(?P<ss>\d+) min|(?P<s>[\d.]+) s)$", re.M)
TEST_RE = re.compile(r"@Test\b")
DISABLED_RE = re.compile(r"@Disabled\b|@Ignore\b|@DisabledIf\b|assumeTrue|Assumptions\.")
STATUS_RE = re.compile(r"^(?: M|\?\?|M |A |D |MM|AM) ?(\S.*)$")


def sh(*a):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(a), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def rd_text(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rd_bytes(p):
    try:
        return Path(p).read_bytes()
    except OSError:
        return b""


def json_or_none(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


# ============================ 纯解析函数区（入参 = 文本） ============================
def parse_facts(text):
    d = {}
    for ln in text.splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def parse_run(text):
    """-> {totals: [(t,f,e,s)], classes: {类名: (t,f,e,s)}, n_class, ok, bad}"""
    tot = [tuple(int(x) for x in m.groups()) for m in TOT_RE.finditer(text)]
    cls = {m.group(5): tuple(int(m.group(i)) for i in range(1, 5)) for m in CLS_RE.finditer(text)}
    return {"totals": tot, "classes": cls, "n_class": len(cls),
            "ok": bool(re.search(r"^\[INFO\] BUILD SUCCESS$", text, re.M)),
            "bad": bool(re.search(r"^\[INFO\] BUILD FAILURE$", text, re.M))}


def parse_elapsed(text):
    """-> (KIND, 原值)，KIND ∈ {'min','s','none'}（双写法都要收，历史 175/228）"""
    m = ELAPSED_RE.search(text)
    if not m:
        return ("none", "")
    if m.group("mm") is not None:
        return ("min", "%s:%s min" % (m.group("mm"), m.group("ss")))
    return ("s", "%s s" % m.group("s"))


def elapsed_seconds(text):
    kind, val = parse_elapsed(text)
    if kind == "min":
        mm, ss = val.split(" ")[0].split(":")
        return int(mm) * 60 + int(ss)
    if kind == "s":
        return float(val.split(" ")[0])
    return -1.0


def elapsed_tuple(text):
    kind, val = parse_elapsed(text)
    return (kind, val, elapsed_seconds(text))


def count_tests(text):
    return len(TEST_RE.findall(text))


def count_disabled(text):
    return len(DISABLED_RE.findall(text))


def count_cr(raw):
    """字节级 CR 计数（历史 70/146：行尾判据一律用字节手段，不用会被吞掉的 grep 模式）"""
    return raw.count(b"\r")


def proj_cov(obj):
    """跨源比对前的**同一个**归一函数（历史 57/92：两侧必须走同一个 key()）"""
    if not isinstance(obj, dict):
        return None
    return {"total": obj.get("total"), "implemented": obj.get("implemented"), "missing": obj.get("missing"),
            "registered_routes": obj.get("registered_routes"), "not_registered": obj.get("not_registered") or [],
            "by_task": {k: (v.get("total"), v.get("implemented"))
                        for k, v in sorted((obj.get("by_task") or {}).items())}}


def status_paths(text):
    out = []
    for ln in text.replace("\r\n", "\n").split("\n"):
        if not ln.strip():
            continue
        m = STATUS_RE.match(ln)
        if m:
            out.append(m.group(1).strip().strip('"'))
    return out


def scan_round_ref(text, digits):
    """扫「当前轮次号」的全部写法；返回 (行号列表, 命中数)。词边界 + R + 数字串。"""
    pat = re.compile(r"\bR" + re.escape(str(digits)) + r"\b")
    hits = [i + 1 for i, ln in enumerate(text.splitlines()) if pat.search(ln)]
    return hits, len(hits)


def prev_round(round_str):
    return "R%d" % (int(round_str[1:]) - 1)


# ============================ 主判定区（只读 ctx） ============================
def evaluate(ctx):
    """返回 [(判据名, 是否通过, 说明)]；纯函数（入参 = ctx）。"""
    chk = []

    def add(name, cond, info=""):
        chk.append((name, bool(cond), info))

    R = ctx["round"]
    facts = ctx["facts"]

    # ---------- J1 facts ----------
    miss = [k for k in REQ_KEYS if k not in facts]
    add("J1a facts 必填键齐备（正向对照 >0）", not miss and len(facts) >= 30,
        "缺失=%s ｜ 读到 %d 键" % (miss or "无", len(facts)))
    add("J1b facts 轮次 == 本轮 ∧ 完成标记",
        facts.get("FACTS_ROUND") == R and facts.get("FACTS_WRITTEN") == "1",
        "ROUND=%r WRITTEN=%r" % (facts.get("FACTS_ROUND"), facts.get("FACTS_WRITTEN")))
    add("J1c 窗口内 HEAD 零推进",
        facts.get("FACTS_HEAD_AT_START_FULL") == facts.get("FACTS_HEAD_AT_END_FULL")
        and facts.get("FACTS_HEAD_ADVANCED_COUNT") == "0",
        "advanced=%s（%s -> %s）" % (facts.get("FACTS_HEAD_ADVANCED_COUNT"), facts.get("FACTS_HEAD_AT_START"),
                                    facts.get("FACTS_HEAD_AT_END")))
    add("J1d 被测提交 == 窗口起点 HEAD ∧ worktree 零脏行",
        facts.get("FACTS_TESTED_COMMIT") == facts.get("FACTS_HEAD_AT_START") and facts.get("WT_DIRTY_LINES") == "0",
        "tested=%s head=%s dirty=%s" % (facts.get("FACTS_TESTED_COMMIT"), facts.get("FACTS_HEAD_AT_START"),
                                        facts.get("WT_DIRTY_LINES")))
    add("J1e worktree add/remove rc == 0",
        facts.get("WORKTREE_ADD_RC") == "0" and facts.get("WORKTREE_REMOVE_RC") == "0",
        "add=%s remove=%s" % (facts.get("WORKTREE_ADD_RC"), facts.get("WORKTREE_REMOVE_RC")))
    add("J1f 并发前置门槛**真的执行**（历史 238/251）",
        facts.get("PREFLIGHT_OK") == "1" and facts.get("PREFLIGHT_RESULT") == "CLEAR"
        and facts.get("ENV_JPS_REACHABLE") == "Y",
        "ok=%s result=%s jps_reachable=%s" % (facts.get("PREFLIGHT_OK"), facts.get("PREFLIGHT_RESULT"),
                                              facts.get("ENV_JPS_REACHABLE")))
    seq = [facts.get(k) for k in ("FACTS_WINDOW_START", "FACTS_RUN1_START", "FACTS_RUN1_END",
                                  "FACTS_RUN2_START", "FACTS_RUN2_END", "FACTS_WINDOW_END")]
    ok_seq = all(isinstance(x, str) and re.fullmatch(r"\d{2}:\d{2}:\d{2}", x) for x in seq) and seq == sorted(seq)
    add("J1g 窗口单调且两轮串行（同量纲 HH:MM:SS）", ok_seq, " → ".join(str(x) for x in seq))

    # ---------- J2 两轮 ----------
    r1, r2 = ctx["run1"], ctx["run2"]
    add("J2a 合计行解析正向对照（每轮恰好 1 条）", len(r1["totals"]) == 1 and len(r2["totals"]) == 1,
        "run1=%d run2=%d 条" % (len(r1["totals"]), len(r2["totals"])))
    add("J2b 两轮合计五元组全 0 失败且两轮一致",
        bool(r1["totals"]) and r1["totals"] == r2["totals"] and r1["totals"][0][1:] == (0, 0, 0),
        "run1=%s run2=%s" % (r1["totals"][:1], r2["totals"][:1]))
    add("J2c 两轮 BUILD SUCCESS 真 / BUILD FAILURE 假",
        r1["ok"] and r2["ok"] and not r1["bad"] and not r2["bad"],
        "run1 ok=%s bad=%s run2 ok=%s bad=%s" % (r1["ok"], r1["bad"], r2["ok"], r2["bad"]))
    add("J2d 逐类行数 > 0 且两轮相等（正向对照）", r1["n_class"] > 0 and r1["n_class"] == r2["n_class"],
        "%d / %d 类" % (r1["n_class"], r2["n_class"]))
    add("J2e 逐类五元组两轮逐条相等（耗时本就不入键，历史 79）", bool(r1["classes"]) and r1["classes"] == r2["classes"],
        "解析到 %d 类；差异 %d 类" % (len(r1["classes"]), len(set(r1["classes"]) ^ set(r2["classes"]))))
    s1 = sum(v[0] for v in r1["classes"].values())
    s2 = sum(v[0] for v in r2["classes"].values())
    t1t = r1["totals"][0][0] if r1["totals"] else None
    t2t = r2["totals"][0][0] if r2["totals"] else None
    add("J2f 类级用例数之和 == 合计（口径自洽）",
        bool(r1["totals"]) and bool(r2["totals"]) and s1 == t1t and s2 == t2t,
        "run1 %d vs %s ｜ run2 %d vs %s" % (s1, t1t, s2, t2t))
    add("J2g run1_end <= run2_start（串行）", facts.get("FACTS_RUN1_END", "9") <= facts.get("FACTS_RUN2_START", "0"),
        "%s <= %s" % (facts.get("FACTS_RUN1_END"), facts.get("FACTS_RUN2_START")))
    e1, e2 = ctx["elapsed"]
    add("J2h maven 耗时双写法解析（两种形态都要收，历史 175）",
        e1[0] in ("min", "s") and e2[0] in ("min", "s") and e1[2] > 0 and e2[2] > 0,
        "run1=%s(%s, %.3fs) run2=%s(%s, %.3fs)" % (e1[0], e1[1], e1[2], e2[0], e2[1], e2[2]))

    # ---------- J3 测试面 ----------
    blobs = ctx["arch_blobs"]
    ntest = sum(count_tests(b) for b in blobs)
    nbare = sum(len(re.findall(r"@Test", b)) for b in blobs)
    ntot = r1["totals"][0][0] if r1["totals"] else -1
    add("J3a 归档测试源非空且 == facts 声明",
        len(blobs) > 0 and str(len(blobs)) == facts.get("ARCH_TEST_FILES"),
        "%d 个 .java / facts 声明 %s" % (len(blobs), facts.get("ARCH_TEST_FILES")))
    add("J3b @Test 词边界计数 == surefire 合计（裸子串作对照）", ntest == ntot and ntest > 0,
        "@Test\\b=%d vs surefire=%d（裸子串 %d）" % (ntest, ntot, nbare))
    ndis = sum(count_disabled(b) for b in blobs)
    add("J3c 不得削弱测试：禁用扫描 == 0", ndis == 0, "命中 %d 条（0 才合规）" % ndis)

    # ---------- J4 覆盖（三处独立读数） ----------
    ca, cr_, ep = ctx["cov_run"], ctx["cov_repo"], ctx["ep"]
    if not ca:
        add("J4a 覆盖读数可用（worktree 归档副本）", False, "归档副本缺失/不可解析（判据不可用）")
    else:
        add("J4a missing == 0 ∧ implemented == total（正向对照 total > 0）",
            ca["missing"] == 0 and ca["implemented"] == ca["total"] and (ca["total"] or 0) > 0,
            "total=%s implemented=%s missing=%s" % (ca["total"], ca["implemented"], ca["missing"]))
        fsum = sum(v[0] for v in ca["by_task"].values())
        fimp = sum(v[1] for v in ca["by_task"].values())
        add("J4b 按族相加 == total（族数 > 0 正向对照）",
            len(ca["by_task"]) > 0 and fsum == ca["total"] and fimp == ca["implemented"],
            "族数=%d 族和 %d/%d" % (len(ca["by_task"]), fsum, fimp))
        add("J4c registered_routes > 0 ∧ not_registered == []",
            (ca["registered_routes"] or 0) > 0 and ca["not_registered"] == [],
            "routes=%s not_registered=%s" % (ca["registered_routes"], ca["not_registered"]))
        add("J4d endpoints.json 端点数 == 顶层 total == 覆盖 total（三处一致）",
            isinstance(ep, dict) and isinstance(ep.get("endpoints"), list)
            and ep.get("total") == len(ep["endpoints"]) == ca["total"],
            "endpoints=%s total=%s cov=%s" % (len((ep or {}).get("endpoints") or []), (ep or {}).get("total"),
                                              ca["total"]))
        add("J4e 仓库跟踪副本 == worktree 归档副本（投影后逐字段，历史 56/131）", bool(cr_) and cr_ == ca,
            "repo=%s arch=%s" % ((cr_ or {}).get("total"), ca["total"]))

    # ---------- J5 交付面 / 在途 / worktree ----------
    add("J5a 被测提交..HEAD 触及交付面的提交 == 0", ctx["delivery_commits"] == 0,
        "count=%d（被测提交=%s）" % (ctx["delivery_commits"], facts.get("FACTS_TESTED_COMMIT")))
    bad_files = [x for x in ctx["round_touched"] if x.startswith(DELIVERY_PREFIXES)]
    add("J5b 本轮改动集合不含交付面前缀（相位 = %s）" % ctx["phase"],
        bool(ctx["round_touched"]) and not bad_files,
        "改动 %d 个 / 越界 %d 个 %s" % (len(ctx["round_touched"]), len(bad_files), bad_files[:5]))
    add("J5c 快照差集方向一：窗口起点快照里的他方在途条目**原样保留**（须 0 条消失；正向对照 在途 > 0）",
        len(ctx["inflight"]) > 0 and not ctx["inflight_gone"],
        "在途 %d 条 / 消失或改动 %s" % (len(ctx["inflight"]), ctx["inflight_gone"] or "0 条"))
    add("J5d 快照差集方向二：新增条目**全部**落在本轮自己的前缀（留痕 / 装置）内（须 0 条越界）",
        bool(ctx["status_paths_after"]) and not ctx["inflight_foreign"],
        "新增 %d 条%s / 越界 %s" % (len(ctx["inflight_added"]),
                                    ("（" + "、".join(ctx["inflight_added"]) + "）") if ctx["inflight_added"] else "",
                                    ctx["inflight_foreign"] or "0 条"))
    # 零装置改动轮才可能（也应）达到「逐字节相等」；装置改动在窗口内落地时差集恰为申报集合（见 J6a），
    # 此时「相等」不是可成立的属性 —— 判据范围必须与语义一致（历史 81/195：口径要么说清依据、要么别用）。
    add("J5e 未申报装置改动时额外要求快照**逐字节相等**（零改动轮的严格形态）",
        bool(ctx["declared"]) or ctx["status_before"] == ctx["status_after"],
        "申报装置改动 %d 个 ⇒ %s" % (len(ctx["declared"]),
                                      "本判据不适用（由 J5c/J5d 给出双向归属核对）"
                                      if ctx["declared"] else "快照相等 = %s"
                                      % (ctx["status_before"] == ctx["status_after"])))
    add("J5f 在途改动 mtime 全部早于窗口起点（对象 = 窗口起点快照）",
        ctx["window_start_ts"] > 0 and len(ctx["inflight"]) > 0 and not ctx["inflight_late"],
        "在途 %d 条 / 落在窗口内 %s" % (len(ctx["inflight"]), ctx["inflight_late"] or "0 条"))
    add("J5g 本轮临时 worktree 已回收（磁盘不存在 ∧ git 未登记）",
        ctx["wt_path"] != "" and not ctx["wt_exists"] and ctx["wt_path"] not in ctx["wt_list"],
        "path=%s exists=%s listed=%s" % (ctx["wt_path"], ctx["wt_exists"], ctx["wt_path"] in ctx["wt_list"]))

    # ---------- J6 装置面改动 == 申报集合（双向） ----------
    got = sorted(ctx["device_actual"])
    want = sorted(ctx["declared"])
    add("J6a 装置面改动 == 申报集合（逐文件点名 · 相位 = %s）" % ctx["phase"], got == want,
        "实得=%s 申报=%s" % (got, want))
    absent = [f for f in want if not (ROOT / f).exists()]
    add("J6b 申报的装置文件在磁盘上真实存在", not absent, "缺失=%s" % (absent or "无"))
    into_delivery = [f for f in want if f.startswith(DELIVERY_PREFIXES)]
    add("J6c 申报的装置文件不落在交付面前缀内", not into_delivery, "越界=%s" % (into_delivery or "无"))
    add("J6d 该判据有牙齿（**集合相等 ≠ 集合非空**：注入「多一个文件」即不等，历史 75/98）",
        sorted(list(want) + ["tools/round-verify/analyze.py"]) != want,
        "申报 %d 个 / 注入集合 %d 个" % (len(want), len(want) + 1))

    # ---------- J7 证据齐备 + 字节级行尾 ----------
    names = [n % R for n in EVIDENCE_CORE]
    absent_ev = [n for n in names if n not in ctx["ev_disk"]]
    add("J7a 本轮核心证据齐备（%d 条，正向对照 >0）" % len(names), len(names) > 0 and not absent_ev,
        "缺失=%s ｜ 已落 %d 条" % (absent_ev or "无", len(names) - len(absent_ev)))
    crbad = sorted(n for n, c in ctx["ev_cr"].items() if c != 0)
    add("J7b 本轮核心证据字节级 CR == 0（历史 69/84/146）", bool(ctx["ev_cr"]) and not crbad,
        "含 CR 的文件=%s（逐字节检查 %d 条）" % (crbad or "无", len(ctx["ev_cr"])))
    add("J7c CR 检测器有牙齿（合成 CRLF 判含 CR / LF 判 0）",
        count_cr(b"a\r\nb\n") == 1 and count_cr(b"a\nb\n") == 0, "CRLF=1 / LF=0")

    # ---------- J8 装置目录轮次无关性 ----------
    add("J8a 装置源码内当前轮次号命中 == 0（历史 201/205/217）", ctx["dev_hits"] == 0,
        "命中 %d 处（扫描 %d 个 .py/.sh）" % (ctx["dev_hits"], ctx["dev_scanned"]))
    add("J8b 该守卫的判别力对照 == 1（非空转，历史 75/98）", ctx["dev_teeth"] == 1,
        "判别力对照 = %d（对合成串命中次数，须 1）" % ctx["dev_teeth"])

    # ---------- J9 本工具的轮次无关性自证 ----------
    _, n = scan_round_ref(ctx["self_src"], R[1:])
    add("J9 本工具源码内零当前轮次号字面量（自证轮次无关）", n == 0, "命中 %d 处" % n)

    return chk


# ============================ 真实上下文 ============================
def build_ctx(ROUND, declared):
    W = T / "aap-round-verify" / ROUND
    facts = parse_facts(rd_text(W / ("facts-%s.log" % ROUND)))
    tested = facts.get("FACTS_TESTED_COMMIT", "HEAD")
    _, out_c, _ = sh("rev-list", "--count", "%s..HEAD" % tested, "--", "tools/")
    _, files_c, _ = sh("diff", "--name-only", "%s..HEAD" % tested)
    _, files_t, _ = sh("diff", "--name-only", "%s..HEAD" % tested, "--", "tools/")
    _, out_w, _ = sh("status", "--porcelain", "--", "tools/")
    dirty = sorted(ln[3:].strip().strip('"') for ln in out_w.splitlines() if ln.strip())
    committed = sorted(x.strip() for x in files_t.splitlines() if x.strip())
    ncc = int(out_c.strip() or "0")
    sb = rd_text(W / "root-status-before.txt")
    sa = rd_text(W / "root-status-after.txt")
    inflight = status_paths(sb)
    if ncc == 0:
        phase = "提交前（工作区未提交）"
        device_actual = dirty
        # 本轮改动集合 = 工作区条目 − 窗口起点快照里的他方在途（历史 193/198：别把他方在途算成本轮改动）
        round_touched = sorted(set(status_paths(sh("status", "--porcelain")[1])) - set(inflight))
    else:
        phase = "提交后（提交链 %d 枚）" % ncc
        device_actual = committed
        round_touched = [x.strip() for x in files_c.splitlines() if x.strip()]
    _rc, out_d, _ = sh("rev-list", "--count", "%s..HEAD" % tested, "--", "aap-server/", "docs/", "aap-client/")
    delivery_commits = int(out_d.strip() or "0") if _rc == 0 else -1
    wtp = facts.get("WORKTREE_PATH", "")
    _, wtl, _ = sh("worktree", "list", "--porcelain")
    ws_ts = int(facts.get("FACTS_WINDOW_START_TS", "0") or "0")
    late = []
    for p in inflight:
        try:
            if (ROOT / p).stat().st_mtime > ws_ts:
                late.append(p)
        except OSError:
            late.append(p + "（不可读）")
    after_paths = status_paths(sa)
    gone = sorted(set(inflight) - set(after_paths))
    added = sorted(set(after_paths) - set(inflight))
    foreign = [p for p in added if not p.startswith(MY_PREFIXES)]
    ev_disk = set(p.name for p in EV.iterdir() if p.is_file())
    ev_cr = {}
    for nm in [n % ROUND for n in EVIDENCE_CORE]:
        if nm in ev_disk:
            ev_cr[nm] = count_cr(rd_bytes(EV / nm))
    dev_hits, dev_scanned = 0, 0
    for p in sorted(DEV_DIR.iterdir()):
        if p.is_file() and p.suffix in (".py", ".sh"):
            dev_scanned += 1
            _, n = scan_round_ref(rd_text(p), ROUND[1:])
            dev_hits += n
    _, teeth = scan_round_ref("合成对照 R" + ROUND[1:] + " 行", ROUND[1:])
    return {
        "round": ROUND, "prev": prev_round(ROUND), "facts": facts,
        "run1": parse_run(rd_text(W / "run1.raw")), "run2": parse_run(rd_text(W / "run2.raw")),
        "elapsed": [elapsed_tuple(rd_text(W / "run1.raw")), elapsed_tuple(rd_text(W / "run2.raw"))],
        "arch_blobs": [p.read_text(encoding="utf-8", errors="replace")
                       for p in sorted((W / "wt-arch/testsrc").rglob("*.java"))],
        "cov_run": proj_cov(json_or_none(W / "wt-arch/coverage-report.json")),
        "cov_repo": proj_cov(json_or_none(EV / "coverage-report.json")),
        "ep": json_or_none(ROOT / "docs/backend/endpoints.json"),
        "status_before": sb, "status_after": sa, "inflight": inflight, "inflight_late": late,
        "status_paths_after": after_paths, "inflight_gone": gone, "inflight_added": added,
        "inflight_foreign": foreign,
        "window_start_ts": ws_ts,
        "wt_path": wtp, "wt_exists": bool(wtp) and Path(wtp).exists(), "wt_list": wtl,
        "device_actual": device_actual, "declared": list(declared), "phase": phase,
        "delivery_commits": delivery_commits, "round_touched": round_touched,
        "ev_disk": ev_disk, "ev_cr": ev_cr,
        "dev_hits": dev_hits, "dev_scanned": dev_scanned, "dev_teeth": teeth,
        "self_src": rd_text(DEV_DIR / "independent.py"),
    }


# ============================ 合成上下文（判别力自测） ============================
SYNTH_R = "R" + "9" * 6          # 运行期拼接：源码内不出现任何轮次号字面量
SYNTH_FACTS = """FACTS_ROUND={R}
FACTS_WINDOW_START=12:00:00
FACTS_WINDOW_START_TS=1000
FACTS_WINDOW_START_ISO=2026-01-01 12:00:00
FACTS_WINDOW_END=12:06:00
FACTS_WINDOW_END_ISO=2026-01-01 12:06:00
FACTS_HEAD_AT_START=aaaaaaaa
FACTS_HEAD_AT_START_FULL=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
FACTS_TESTED_COMMIT=aaaaaaaa
FACTS_TESTED_COMMIT_FULL=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
WT_DIRTY_LINES=0
FACTS_RUN1_START=12:00:05
FACTS_RUN1_END=12:03:00
FACTS_RUN1_RC=0
FACTS_RUN2_START=12:03:01
FACTS_RUN2_END=12:05:59
FACTS_RUN2_RC=0
ARCH_TEST_FILES=2
FACTS_HEAD_AT_END=aaaaaaaa
FACTS_HEAD_AT_END_FULL=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
FACTS_HEAD_ADVANCED_COUNT=0
PREFLIGHT_OK=1
PREFLIGHT_RESULT=CLEAR
ENV_JPS_REACHABLE=Y
FACTS_WRITTEN=1
WORKTREE_ADD_RC=0
WORKTREE_REMOVE_RC=0
WORKTREE_PATH=C:/tmp/合成worktree-{R}
ENV_BASH=/usr/bin/bash
ENV_UNAME=MINGW64
ENV_MVN=/c/Users/x/bin/mvn
ENV_JAVA=/e/jdk/bin/java
""".format(R=SYNTH_R)

SYNTH_RUN = """[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 1.0 s -- in com.x.ATest
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.5 s -- in com.x.BTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
[INFO] Total time:  01:04 min
"""
SYNTH_JAVA = ["package com.x;\npublic class ATest {\n  @Test\n  void a(){}\n  @Test\n  void b(){}\n}\n",
              "package com.x;\npublic class BTest {\n  @Test\n  void a(){}\n}\n"]


def synth_ctx():
    facts = parse_facts(SYNTH_FACTS)
    run = parse_run(SYNTH_RUN)
    names = [n % SYNTH_R for n in EVIDENCE_CORE]
    dev = ["tools/round-verify/independent.py"]
    return {
        "round": SYNTH_R, "prev": prev_round(SYNTH_R), "facts": facts,
        "run1": run, "run2": run,
        "elapsed": [elapsed_tuple(SYNTH_RUN), elapsed_tuple(SYNTH_RUN)],
        "arch_blobs": list(SYNTH_JAVA),
        "cov_run": proj_cov({"total": 12, "implemented": 12, "missing": 0, "registered_routes": 9,
                             "by_task": {"": {"total": 2, "implemented": 2}, "T1": {"total": 10, "implemented": 10}}}),
        "cov_repo": proj_cov({"by_task": {"T1": {"implemented": 10, "total": 10}, "": {"implemented": 2, "total": 2}},
                              "missing": 0, "implemented": 12, "total": 12, "registered_routes": 9,
                              "not_registered": None}),
        "ep": {"total": 12, "endpoints": [{}] * 12},
        "status_before": " M README.md\n M aap-server/pom.xml\n",
        "status_after": " M README.md\n M aap-server/pom.xml\n M tools/round-verify/independent.py\n",
        "status_paths_after": ["README.md", "aap-server/pom.xml", "tools/round-verify/independent.py"],
        "inflight_gone": [], "inflight_added": ["tools/round-verify/independent.py"], "inflight_foreign": [],
        "inflight": ["README.md", "aap-server/pom.xml"], "inflight_late": [], "window_start_ts": 1000,
        "wt_path": "C:/tmp/合成worktree-%s" % SYNTH_R, "wt_exists": False, "wt_list": "",
        "device_actual": list(dev), "declared": list(dev), "phase": "提交前（工作区未提交）",
        "delivery_commits": 0,
        "round_touched": dev + [".agents/state/evidence/round-%s-analysis.txt" % SYNTH_R],
        "ev_disk": set(names), "ev_cr": {n: 0 for n in names},
        "dev_hits": 0, "dev_scanned": 9, "dev_teeth": 1,
        "self_src": "合成源码：不含任何轮次号字面量",
    }


def fails_of(chk):
    """只取**判据编号**（首个空白前的 token）作为比对键 —— 历史 82/93：拿整行文本当键会把有效守卫判失败。"""
    return sorted(n.split()[0] for n, ok, _ in chk if not ok)


# ============================ 判别力自测 ============================
def selftest():
    base = synth_ctx()
    out0 = evaluate(base)
    bad0 = fails_of(out0)
    res = []

    def chk(name, cond, info=""):
        res.append((name, bool(cond), info))

    def mutate(label, mut, expect):
        c = synth_ctx()
        mut(c)
        f = fails_of(evaluate(c))
        delta = sorted(set(f) - set(bad0))
        gone = sorted(set(bad0) - set(f))
        chk("T·%s → 恰好新增 %s" % (label, expect), delta == sorted(expect) and not gone,
            "新增=%s 消失=%s" % (delta, gone))

    chk("T0 合成上下文基线全绿（每条判据都有正向对照，历史 46/75）", not bad0, "FAIL=%s" % bad0)

    def m_facts(k, v, label, expect):
        mutate(label, lambda c: c.update(facts=dict(c["facts"], **{k: v})), expect)

    m_facts("FACTS_ROUND", "R0", "facts 轮次不符", ["J1b"])
    m_facts("FACTS_WRITTEN", "0", "facts 未写完成标记", ["J1b"])
    m_facts("FACTS_HEAD_ADVANCED_COUNT", "1", "窗口内 HEAD 推进", ["J1c"])
    m_facts("WT_DIRTY_LINES", "3", "worktree 脏行", ["J1d"])
    m_facts("WORKTREE_REMOVE_RC", "1", "worktree 回收失败", ["J1e"])
    m_facts("PREFLIGHT_RESULT", "CONC_BUSY_ABORT", "并发前置门槛未通过", ["J1f"])
    m_facts("FACTS_RUN1_END", "13:00:00", "窗口乱序（run1_end > run2_start）", ["J1g", "J2g"])
    bad_run = parse_run(SYNTH_RUN.replace("[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0",
                                          "[ERROR] Tests run: 3, Failures: 2, Errors: 1, Skipped: 0")
                        .replace("[INFO] BUILD SUCCESS", "[INFO] BUILD FAILURE"))
    mutate("run2 红基线（ERROR 前缀 + BUILD FAILURE）", lambda c: c.update(run2=bad_run), ["J2b", "J2c"])
    mutate("run2 逐类行消失（解析器失效可见）", lambda c: c.update(run2=parse_run("[INFO] BUILD SUCCESS\n")),
           ["J2a", "J2b", "J2d", "J2e", "J2f"])
    mutate("run1 耗时行解析不到",
           lambda c: c.update(elapsed=[("none", "", -1.0), c["elapsed"][1]]), ["J2h"])
    mutate("归档测试源少一个文件", lambda c: c.update(arch_blobs=c["arch_blobs"][:1]), ["J3a", "J3b"])
    mutate("注入一条 @Disabled（削弱测试）",
           lambda c: c.update(arch_blobs=[c["arch_blobs"][0].replace("void a(){}", "@Disabled\n  void a(){}")]
                              + c["arch_blobs"][1:]), ["J3c"])
    mutate("注入一条新用例（@Test 计数与 surefire 不符）",
           lambda c: c.update(arch_blobs=[c["arch_blobs"][0] + "  @Test\n  void c(){}\n"] + c["arch_blobs"][1:]),
           ["J3b"])
    mutate("覆盖 missing 变成 1（按族仍自洽）",
           lambda c: c.update(cov_run=proj_cov({"total": 12, "implemented": 11, "missing": 1,
                                                "registered_routes": 9,
                                                "by_task": {"": {"total": 2, "implemented": 2},
                                                            "T1": {"total": 10, "implemented": 9}}})),
           ["J4a", "J4e"])
    mutate("按族相加 != total",
           lambda c: c.update(cov_run=proj_cov({"total": 12, "implemented": 12, "missing": 0,
                                                "registered_routes": 9,
                                                "by_task": {"": {"total": 2, "implemented": 2},
                                                            "T9": {"total": 8, "implemented": 8}}})),
           ["J4b", "J4e"])
    mutate("not_registered 非空", lambda c: c.update(cov_run=dict(c["cov_run"], not_registered=["X-01"])),
           ["J4c", "J4e"])
    mutate("endpoints.json 端点数与 total 不符", lambda c: c.update(ep={"total": 12, "endpoints": [{}] * 11}),
           ["J4d"])
    mutate("仓库跟踪副本停在旧口径",
           lambda c: c.update(cov_repo=proj_cov({"total": 9, "implemented": 9, "missing": 0,
                                                 "registered_routes": 9,
                                                 "by_task": {"": {"total": 9, "implemented": 9}}})), ["J4e"])
    mutate("本轮提交触及交付面（提交数）", lambda c: c.update(delivery_commits=1), ["J5a"])
    mutate("本轮改动里混入交付面路径",
           lambda c: c.update(round_touched=c["round_touched"] + ["aap-server/src/main/java/X.java"]), ["J5b"])
    mutate("本轮改动集合为空（判据不可用而非合规）", lambda c: c.update(round_touched=[]), ["J5b"])
    mutate("他方在途条目被本轮改动 / 删除 / 回退（方向一）",
           lambda c: c.update(inflight_gone=["README.md"],
                              status_paths_after=["aap-server/pom.xml", "tools/round-verify/independent.py"],
                              inflight_added=["tools/round-verify/independent.py"]), ["J5c"])
    mutate("窗口内新增条目落在交付面 / 他方文件（方向二）",
           lambda c: c.update(inflight_foreign=["docs/backend/x.md"]), ["J5d"])
    mutate("零装置改动轮却出现新增条目（严格形态 J5e）",
           lambda c: c.update(declared=[], device_actual=[],
                              status_after=" M README.md\n M aap-server/pom.xml\n M tools/round-verify/x.py\n",
                              status_paths_after=["README.md", "aap-server/pom.xml", "tools/round-verify/x.py"]),
           ["J5e"])
    mutate("在途条目 mtime 落在窗口内", lambda c: c.update(inflight_late=["README.md"]), ["J5f"])
    mutate("临时 worktree 未回收", lambda c: c.update(wt_exists=True), ["J5g"])
    mutate("装置改动未申报（实得多一个文件）",
           lambda c: c.update(device_actual=["tools/round-verify/independent.py", "tools/round-verify/analyze.py"]),
           ["J6a"])
    mutate("申报了但实得为空（自述不实的另一方向）", lambda c: c.update(device_actual=[]), ["J6a"])
    mutate("申报的装置文件不存在", lambda c: c.update(declared=["tools/round-verify/不存在.py"]), ["J6a", "J6b"])
    mutate("申报的装置文件落在交付面", lambda c: c.update(declared=["aap-server/src/main/java/X.java"]),
           ["J6a", "J6b", "J6c"])
    mutate("核心证据缺一条",
           lambda c: (c.update(ev_disk=set(c["ev_disk"]) - {"round-%s-analysis.txt" % SYNTH_R},
                               ev_cr={k: v for k, v in c["ev_cr"].items()
                                      if k != "round-%s-analysis.txt" % SYNTH_R})), ["J7a"])
    mutate("核心证据含 CR（字节级）",
           lambda c: c.update(ev_cr=dict(c["ev_cr"], **{"regression-selftest-%s.txt" % SYNTH_R: 3})), ["J7b"])
    mutate("装置源码里出现当前轮次号", lambda c: c.update(dev_hits=2), ["J8a"])
    mutate("轮次无关性守卫判别力对照塌陷", lambda c: c.update(dev_teeth=0), ["J8b"])
    mutate("本工具源码内混入当前轮次号", lambda c: c.update(self_src="示例 " + SYNTH_R + " 行"), ["J9"])

    # 空上下文必须整体变红（历史 128/132：空夹具判「一致」是空转假绿的经典形态）
    empty = {k: (type(v)() if isinstance(v, (list, set, dict, str)) else v) for k, v in synth_ctx().items()}
    empty.update(facts={}, run1=parse_run(""), run2=parse_run(""), elapsed=[("none", "", -1.0)] * 2,
                 cov_run=None, cov_repo=None, ep=None, ev_disk=set(), ev_cr={}, wt_path="",
                 inflight=[], window_start_ts=0, round_touched=[], device_actual=[],
                 declared=["tools/round-verify/independent.py"], self_src="合成源码")
    fe = fails_of(evaluate(empty))
    chk("T-E 空上下文整体变红且点名 J1a/J2a/J3b/J4a/J5b/J5c/J5d/J6a/J7a",
        {"J1a", "J2a", "J3b", "J4a", "J5b", "J5c", "J5d", "J6a", "J7a"}.issubset(set(fe)), "FAIL=%s" % fe)
    # 轮次无关性守卫的正/反向对照（与 device-report.py 的 S8/S9 同源）
    _, h1 = scan_round_ref("合成对照 " + SYNTH_R + " 行", SYNTH_R[1:])
    _, h2 = scan_round_ref("超串 R" + SYNTH_R[1:] + "0 与相邻 R0", SYNTH_R[1:])
    chk("T-P1 轮次号守卫对合成串命中 1 次 / 对超串命中 0 次（正反各一条）", h1 == 1 and h2 == 0,
        "合成=%d 超串=%d" % (h1, h2))

    ok = sum(1 for _, c, _ in res if c)
    for name, c, info in res:
        print("  [%s] %s%s" % ("PASS" if c else "FAIL", name, (" " + info) if info else ""))
    print("  判据：PASS %d / FAIL %d（共 %d 例）" % (ok, len(res) - ok, len(res)))
    print("SELFTEST_END=1")
    return 0 if ok == len(res) else 1


# ============================ 主流程 ============================
def main():
    try:
        sys.stdout.reconfigure(newline="\n")
    except Exception:
        pass
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    ROUND = (args[0] if args else "").upper()
    if not re.fullmatch(r"R\d+", ROUND):
        print("用法: python tools/round-verify/independent.py <轮次> [--device-change <路径>]... [--no-write]")
        print("      python tools/round-verify/independent.py --selftest")
        return 2
    n_flag = sum(1 for a in args if a == "--device-change")
    declared = [args[i + 1] for i, a in enumerate(args) if a == "--device-change" and i + 1 < len(args)]
    if len(declared) != n_flag:
        print("[FAIL] --device-change 缺参数值")
        return 2
    ctx = build_ctx(ROUND, declared)
    # 真实上下文与合成上下文**键集必须相等**（只在合成侧补键会让自测全绿而真实运行 KeyError，历史 44/82）
    ref = synth_ctx()
    if set(ctx) != set(ref):
        print("[FAIL] 真实上下文与合成上下文键集不同：真实缺 %s / 真实多 %s"
              % (sorted(set(ref) - set(ctx)), sorted(set(ctx) - set(ref))))
        return 2
    chk = evaluate(ctx)
    nfail = len(fails_of(chk))
    L = ["%s 独立复核探针（轮次无关装置：tools/round-verify/independent.py；**只读**，不采信装置自身判定行）" % ROUND,
         "=" * 78,
         "相位 = %s；被测提交（facts）= %s；窗口 = %s -> %s；申报的装置改动 = %s"
         % (ctx["phase"], ctx["facts"].get("FACTS_TESTED_COMMIT"), ctx["facts"].get("FACTS_WINDOW_START_ISO"),
            ctx["facts"].get("FACTS_WINDOW_END_ISO"), ctx["declared"] or "（无）"),
         "生成方式：全部读数由**原始 maven 日志 / facts / 覆盖 JSON / git / 磁盘**独立解析得出，源码内零硬编码纯值；",
         "每个解析器都是纯函数（入参 = 文本）；判别力自测见 `--selftest`（合成 ctx + 注入缺陷，断言恰好新增目标判据）。",
         ""]
    for name, ok, info in chk:
        L.append("[%s] %s %s" % ("PASS" if ok else "FAIL", name, info))
    L.append("")
    L.append("独立复核：PASS %d / FAIL %d（共 %d 项判据）" % (len(chk) - nfail, nfail, len(chk)))
    L.append("%s=%d" % (END_MARK, 0 if nfail == 0 else 1))
    text = "\n".join(L) + "\n"
    print(text, end="")
    if "--no-write" in args:
        print("（--no-write：仅回显，未落盘）")
        return 1 if nfail else 0
    out = EV / ("independent-%s.txt" % ROUND)
    out.write_text(text, encoding="utf-8", newline="\n")
    rb = out.read_bytes()
    bad = []
    if rb.count(b"\r") != 0:
        bad.append("含 CR")
    got = rb.decode("utf-8")
    if got.count(END_MARK) != 1:
        bad.append("结束标记 %d 处（须 1）" % got.count(END_MARK))
    if len(got.splitlines()) < 12:
        bad.append("行数 %d 过少" % len(got.splitlines()))
    if "独立复核：PASS" not in got:
        bad.append("缺汇总行")
    if bad:
        print("[FAIL] 落盘复核失败：%s（历史 222/230）" % "；".join(bad))
        return 2
    print("独立复核证据 = %s（%d 行 / CR=0）" % (out.name, len(got.splitlines())))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
