#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立复核探针（**轮次无关**、**只读**；不采信装置自身的判定行）。

用法：
  python tools/round-verify/independent.py <轮次> [--device-change <路径>]...
         [--external-commit <他方提交短号>]... [--external-withdrawn <他方自主撤下的在途路径>]... [--no-write]
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
     ＋ **装置链自写面**（J5f 的第 4 类解释项；J5i/J5j = 判据可用性与「每轮须落盘」纪律）
* J6 装置面改动 == 申报集合（逐文件点名 · 双向）
* J7 本轮核心证据齐备 ∧ 字节级 CR == 0（历史 69/84/146）
* J8 装置目录轮次无关性（当前轮次号不得出现在装置源码里；判别力对照 = 1）
* J9 本工具的轮次无关性自证（源码内零当前轮次号字面量）

**他方并发活动的处理**（判据范围必须与语义一致，历史 81/193/198）：他方在本轮窗口内推进的提交、或他方自主撤下的
在途文件，会把「零推进 / 零改动 / 原样保留 / mtime 早于窗口」这几条判据的**前提**打破 —— 那不是本轮的违规，
但也不能靠人眼放行。正解是**显式申报 + 逐条可核**：`--external-commit`（他方提交，须落在 `被测提交..HEAD` 区间内
∧ 主题不含本轮轮次号）、`--external-withdrawn`（他方自主撤下的在途路径，须「在窗口起点快照里 ∧ 已从快照消失
∧ 不落在我方改动集合里」）。**未申报的外部活动照旧响亮失败**；核心不变量由 J5h 直接判：
**我方改动集合 ∩ 窗口起点他方在途集合 == ∅**。

**装置链自写面**（J5f 的**第 4 类**解释项；机器派生，不是人工申报，历史 66/210）：回归面命令表里的脚本会
**自己写回**追踪证据文件（本仓实测 `tools/audit-endpoint-tests.py` 每轮重写 `.agents/state/evidence/endpoint-test-audit.txt`
与同名 `.json`），这类产物常以「工作区已改动」的形态留在他方在途清单里 ⇒ 其 mtime 落窗时会被 J5f 误判成
「他方在途被碰」。正解不是人工加白名单（历史 210：逐条列举必然漏项），而是**机器派生**：命令表（`manifest.json`）
cmd 实参里的脚本 ∧ 其源码含写标记 ∧ 从源码抽出的证据文件名（按 basename 认 —— 常量常带目录变量）。
只有「路径落在证据目录 ∧ basename 属自写面」才可能被豁免，`README.md` / `pom.xml` 之流**永远**无法被豁免；
J5i 是「解析到 0 个即判据失效」的正向对照（历史 46/75/98）。配套 J5j：「自写面里的**追踪**文件 mtime 落窗 ⇒
提交后必须与 HEAD 一致」，把提交 `0aee5e72` 立下的约定（「回归面每次复跑都会重写 ⇒ 每轮须落盘」）固化成机器判据，
相位感知（提交前相位不适用，历史 243-①）。

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
# 相位（green/red）单一事实源：校验证据的前缀由它推出（历史 12/554）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase import GREEN, RED, ev_prefix, phase_of  # noqa: E402
END_MARK = "INDEPENDENT_END"
DELIVERY_PREFIXES = ("aap-server/", "docs/", "aap-client/")
# 本轮**自己的**写入前缀（留痕目录 + 装置目录）：窗口内新增的条目必须全部落在这两类里（判据 J5d）。
MY_PREFIXES = (".agents/state/", "tools/")
# 本轮核心证据（由 analyze.py / regression.py 产出）；收尾相位才产生的证据**不在此表内** —— 历史 222：
# 本文件不能把自己、或尚未产生的文件判成缺失。
# 5 条「校验证据」的**前缀由相位推出**（`phase.ev_prefix`）：绿轮 `green-verify-*`、红轮 `red-verify-*`
# —— 红轮的产物不得命名为 green（历史 12/554：文件名不能骗人）。
EVIDENCE_CORE = [
    "round-%s-analysis.txt",
    "audit-regression-%s.txt",
    "audit-regression-%s-rcseq.txt",
    "audit-regression-%s-failraw.txt",
    "audit-regression-%s-faildiff.txt",
    "regression-selftest-%s.txt",
]
EVIDENCE_STEMS = ["coverage-fields", "testcount", "tested-state", "full-run1", "full-run2"]


def evidence_core(round_):
    """本轮核心证据清单：校验证据前缀由**磁盘上的实际相位**推出（两种前缀都认，历史 181/554）。"""
    pfx = ev_prefix(RED if any(EV.glob("red-verify-%s-*.txt" % round_)) else GREEN)
    return ([n % round_ for n in EVIDENCE_CORE]
            + ["%s-%s-%s.txt" % (pfx, round_, s) for s in EVIDENCE_STEMS])
REQ_KEYS = ["FACTS_ROUND", "FACTS_WINDOW_START", "FACTS_WINDOW_START_TS", "FACTS_WINDOW_START_ISO",
            "FACTS_WINDOW_END", "FACTS_WINDOW_END_ISO", "FACTS_HEAD_AT_START", "FACTS_HEAD_AT_START_FULL",
            "FACTS_TESTED_COMMIT", "FACTS_TESTED_COMMIT_FULL", "WT_DIRTY_LINES", "FACTS_RUN1_START",
            "FACTS_RUN1_END", "FACTS_RUN1_RC", "FACTS_RUN2_START", "FACTS_RUN2_END", "FACTS_RUN2_RC",
            "ARCH_TEST_FILES", "FACTS_HEAD_AT_END", "FACTS_HEAD_AT_END_FULL", "FACTS_HEAD_ADVANCED_COUNT",
            "PREFLIGHT_OK", "PREFLIGHT_RESULT", "ENV_JPS_REACHABLE", "FACTS_WRITTEN", "WORKTREE_ADD_RC",
            "WORKTREE_REMOVE_RC", "WORKTREE_PATH"]

TOT_RE = re.compile(r"^\[(?:INFO|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)$", re.M)
CLS_RE = re.compile(r"^\[(?:INFO|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+), "
                    r"Time elapsed: [\d.]+ s(?: <<< [A-Z]+!)? -- in (\S+)$", re.M)
# `(?: <<< FAILURE!)?` 必须有：**失败**的类级行形如 `… Time elapsed: 0.1 s <<< FAILURE! -- in <类>`，
# 不带该可选组时整行漏收 ⇒ 类级求和比合计少 1（本仓实测红相位 304 vs 305，历史 228 族/81：判据形态必须与实际一致）。
# 与之配套的正向对照见自测 S18：合成 `[ERROR] … <<< FAILURE! -- in` 行必须被解析到。
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
            # 有失败的那一轮 maven 写的是 `[ERROR] BUILD FAILURE`（绿轮才写 `[INFO] BUILD SUCCESS`）——
            # 只认 `[INFO]` 前缀时「红轮的 bad 恒假」，而绿轮的 J2c 只用 `not bad` ⇒ **缺陷在绿轮完全不可见**
            # （历史 228 同族：前缀随成败变化，恰恰红轮才是采集器最该工作的时刻）。
            "bad": bool(re.search(r"^\[(?:INFO|ERROR)\] BUILD FAILURE$", text, re.M))}


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


def phase_and_touched(n_commits, commit_files, worktree_files, inflight):
    """相位判定 + 「本轮改动集合」（纯函数 ⇒ 可被负向自测覆盖，历史 66/94）。

    语义：判据是「本轮**是否已有提交**」，`n_commits` 必须取 `<被测提交>..HEAD` 的**全部路径**提交数。
    真实缺陷（本仓实测）：判据范围写成 `rev-list --count <被测>..HEAD -- tools/` ⇒ 零装置改动轮
    （装置面与交付面均零改动、只提交留痕）在**提交后**仍被判成「提交前」，于是它去读**已清空的工作区**
    得到空集合，而 J5b 又把空集合判成「判据不可用」⇒ 对合法状态报**假失败**（历史 81/141/175）。
    提交后相位**仍把工作区残留并入集合**（并集，比只看提交链更严：不会漏掉未提交的交付面改动）。
    """
    n = int(n_commits or 0)
    left = sorted(set(worktree_files) - set(inflight))
    if n == 0:
        return "提交前（工作区未提交）", left
    return "提交后（提交链 %d 枚）" % n, sorted(set(commit_files) | set(left))


def own_of(all_files, ext_files):
    """归属归一（纯函数，入参 = 文本列表）：把**已申报他方提交**触及的文件从区间改动集合里剔除。

    判据是**集合差**，且必须只对**成员**生效：`ext_files` 里的非成员项不得改动集合 —— 否则「申报」
    就能凭空剔除任意路径、把守卫架空（历史 57/68/190：豁免必须被机器判据夹住）。空申报时恒等
    （零外部活动轮次的口径完全不变，历史 208 的可重跑性）。
    """
    ext = set(ext_files)
    return sorted(x for x in all_files if x not in ext)


def ext_commits_ok(n_advanced, declared, bad):
    """窗口内 HEAD 推进数 == 已申报他方提交数 ∧ 申报项逐枚可核（纯函数，历史 66/94）。

    `bad` = 不可核的申报项（不在 `被测提交..HEAD` 区间内 ∧ 或主题含本轮轮次号）。
    三态：零推进 + 零申报 = 合法；推进了却未申报 = 红；申报了却不可核 = 红。
    """
    return int(n_advanced or 0) == len(declared) and not bad


# ========== 装置链自写面（J5f 的**第 4 类**解释项；机器派生，不是人工申报，历史 66/210） ==========
# 为什么需要它：回归面命令表里的脚本会**自己写回**追踪证据文件（本仓实测 `tools/audit-endpoint-tests.py`
# 每轮重写 `.agents/state/evidence/endpoint-test-audit.txt`），而这类产物往往同时以「工作区已改动」的形态
# 留在他方在途清单里 ⇒ 其 mtime 落在窗口内时，J5f 会把「**我方工具自写**」误判成「他方在途条目被碰」
# （判据范围必须与语义一致：豁免只放宽**我方自己的**动作，历史 81/193/198）。
# 判据必须**机器派生**（历史 210：人工逐条列举必然漏项）：
#   ① 命令表（`manifest.json`）cmd 实参里以 .py/.sh 结尾的脚本；
#   ② 该脚本源码里含**写标记**（`write_text` / `write_bytes` / `open(`）；
#   ③ 从这类脚本源码里抽出的**证据文件名**（常量常带目录变量 ⇒ 按 basename 认，历史 218/225）。
# 只有「路径落在证据目录 ∧ basename 属自写面」才可能被豁免；README.md / pom.xml 之流**永远**无法被豁免。
WRITE_MARK_RE = re.compile(r"write_text|write_bytes|open[(]")
EVID_PREFIX = ".agents/state/evidence/"
EVID_NAME_RE = re.compile(r'"([A-Za-z0-9_.-]+[.](?:txt|json|jsonl|csv|md))"')


def manifest_script_args(manifest_text):
    """命令表里引用的脚本路径（纯函数，入参 = manifest 文本）：按 .py/.sh 结尾认，出现顺序去重。"""
    try:
        m = json.loads(manifest_text)
    except ValueError:
        return []
    out = []
    for grp in ("audits", "selftests"):
        for e in (m.get(grp) or []):
            for a in (e.get("cmd") or []):
                a = str(a).replace(chr(92), "/")   # chr(92) = 反斜杠：不写字面量，避开转义歧义
                if a.endswith((".py", ".sh")) and a not in out:
                    out.append(a)
    return out


def writer_output_names(pairs):
    """装置链自写面（纯函数，入参 = [(脚本路径, 源码文本)]）：写脚本源码里出现的证据文件名集合。"""
    names = set()
    for _p, src in pairs:
        if src and WRITE_MARK_RE.search(src):
            names |= set(EVID_NAME_RE.findall(src))
    return sorted(names)


def selfwritten_exempt(late, names):
    """自写豁免集合（纯函数）：落窗在途项里「路径在证据目录 ∧ basename 属自写面」的那些。"""
    ns = set(names)
    return [p for p in late if p.startswith(EVID_PREFIX) and p[len(EVID_PREFIX):] in ns]


def late_unexplained(late, declared, ext_files, withdrawn, selfwritten=()):
    """J5f 的判据对象（纯函数）：落窗在途项 ∖ 已解释项（装置改动 ∪ 他方提交触及 ∪ 他方自主撤下 ∪ 装置链自写）。

    形状纪律（本轮真实返工，历史 218/225）：判据对象与豁免集合必须**同形** —— 不可读项若存成
    「路径 + （不可读）后缀」，豁免比对恒不命中，合法态照样报红。故 `late` 一律存**原始路径**，
    「不可读」只作为并列读数（`inflight_late_unread`）。
    """
    ex = set(declared) | set(ext_files) | set(withdrawn) | set(selfwritten)
    return [p for p in late if p not in ex]


# 窗口时刻解算 = 装置内**共享**纯函数（`windowtime.py`）：轮次会跨午夜，按 HH:MM:SS 字符串比单调/串行
# 会把合法窗口判成「非单调」（假失败，历史 12/244）。单一事实源，`analyze.py` A5 共用同一份（历史 44/191）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from windowtime import resolve_window_seq  # noqa: E402


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
    add("J1c 窗口内 HEAD 推进数 == 已申报他方提交数 ∧ 申报项逐枚可核（他方并发活动须显式申报，历史 193/198）",
        ext_commits_ok(facts.get("FACTS_HEAD_ADVANCED_COUNT"), ctx["external"], ctx["external_bad"]),
        "advanced=%s 申报他方提交=%s 不可核=%s（%s -> %s）"
        % (facts.get("FACTS_HEAD_ADVANCED_COUNT"), ctx["external"] or "无", ctx["external_bad"] or "无",
           facts.get("FACTS_HEAD_AT_START"), facts.get("FACTS_HEAD_AT_END")))
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
    ok_seq, det_seq = resolve_window_seq(facts, ("FACTS_WINDOW_START", "FACTS_RUN1_START", "FACTS_RUN1_END",
                                                 "FACTS_RUN2_START", "FACTS_RUN2_END", "FACTS_WINDOW_END"))
    add("J1g 窗口单调且两轮串行（按绝对时刻解算：轮次可跨午夜，HH:MM:SS 字符串比会假失败）", ok_seq, det_seq)

    # ---------- J2 两轮 ----------
    r1, r2 = ctx["run1"], ctx["run2"]
    # 相位（green/red）由**同一事实源**推出（与 analyze / closeout 共用 `phase_of`）：红相位下
    # 「两轮全 0 失败 / BUILD SUCCESS / missing==0」不是可成立的属性 ⇒ 判据必须按相位分支，
    # 否则独立复核会在红相位下报 4~5 条**结构性假 FAIL**（判据范围与语义不符，历史 81/195）。
    _ca0 = ctx["cov_run"] or {}
    try:
        PH2 = phase_of(str(facts.get("FACTS_RUN1_RC", "")), str(facts.get("FACTS_RUN2_RC", "")),
                       str(_ca0.get("missing", "")))
    except ValueError:
        PH2 = RED  # 判据不可用 ≠ 绿（历史 98/141）
    add("J2a 合计行解析正向对照（每轮恰好 1 条）", len(r1["totals"]) == 1 and len(r2["totals"]) == 1,
        "run1=%d run2=%d 条" % (len(r1["totals"]), len(r2["totals"])))
    _t1 = r1["totals"][0] if r1["totals"] else None
    _t2 = r2["totals"][0] if r2["totals"] else None
    _failcls = sorted(k for k, v in r1["classes"].items() if v and v[1])  # 类名 → 失败数 > 0
    if PH2 == GREEN:
        add("J2b 两轮合计五元组全 0 失败且两轮一致",
            bool(_t1) and _t1 == _t2 and _t1[1:] == (0, 0, 0),
            "run1=%s run2=%s" % (r1["totals"][:1], r2["totals"][:1]))
        add("J2c 两轮 BUILD SUCCESS 真 / BUILD FAILURE 假",
            r1["ok"] and r2["ok"] and not r1["bad"] and not r2["bad"],
            "run1 ok=%s bad=%s run2 ok=%s bad=%s" % (r1["ok"], r1["bad"], r2["ok"], r2["bad"]))
    else:
        add("J2b 红相位：两轮合计逐条一致 ∧ Errors=0 ∧ Skipped=0 ∧ Failures≥1（失败可归因，点名失败类）",
            bool(_t1) and _t1 == _t2 and _t1[2] == 0 and _t1[3] == 0 and _t1[1] >= 1 and bool(_failcls),
            "run1=%s run2=%s 失败类=%s" % (r1["totals"][:1], r2["totals"][:1], _failcls or "（无！判据失效）"))
        add("J2c 红相位：两轮 BUILD FAILURE 真 / BUILD SUCCESS 假",
            r1["bad"] and r2["bad"] and not r1["ok"] and not r2["ok"],
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
    ok_ser, det_ser = resolve_window_seq(facts, ("FACTS_RUN1_END", "FACTS_RUN2_START"))
    add("J2g run1_end <= run2_start（串行；同一解算：跨午夜不假失败）", ok_ser, det_ser)
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
        if PH2 == GREEN:
            add("J4a missing == 0 ∧ implemented == total（正向对照 total > 0）",
                ca["missing"] == 0 and ca["implemented"] == ca["total"] and (ca["total"] or 0) > 0,
                "total=%s implemented=%s missing=%s" % (ca["total"], ca["implemented"], ca["missing"]))
        else:
            add("J4a 红相位：读数自洽（implemented + missing == total ∧ total>0 ∧ missing>0 ∧ 未注册条数 == missing）",
                (ca["implemented"] + ca["missing"] == ca["total"] and (ca["total"] or 0) > 0 and ca["missing"] > 0
                 and len(ca["not_registered"]) == ca["missing"]),
                "total=%s implemented=%s missing=%s 未注册 %d 条"
                % (ca["total"], ca["implemented"], ca["missing"], len(ca["not_registered"])))
        fsum = sum(v[0] for v in ca["by_task"].values())
        fimp = sum(v[1] for v in ca["by_task"].values())
        add("J4b 按族相加 == total（族数 > 0 正向对照）",
            len(ca["by_task"]) > 0 and fsum == ca["total"] and fimp == ca["implemented"],
            "族数=%d 族和 %d/%d" % (len(ca["by_task"]), fsum, fimp))
        if PH2 == GREEN:
            add("J4c registered_routes > 0 ∧ not_registered == []",
                (ca["registered_routes"] or 0) > 0 and ca["not_registered"] == [],
                "routes=%s not_registered=%s" % (ca["registered_routes"], ca["not_registered"]))
        else:
            add("J4c 红相位：registered_routes > 0 ∧ 未注册清单非空且逐条给出 ID（与 missing 同源）",
                (ca["registered_routes"] or 0) > 0 and len(ca["not_registered"]) > 0
                and all("id" in (d or {}) for d in ca["not_registered"]),
                "routes=%s 未注册 ID=%s" % (ca["registered_routes"],
                                            [d.get("id") for d in ca["not_registered"]]))
        add("J4d endpoints.json 端点数 == 顶层 total == 覆盖 total（三处一致）",
            isinstance(ep, dict) and isinstance(ep.get("endpoints"), list)
            and ep.get("total") == len(ep["endpoints"]) == ca["total"],
            "endpoints=%s total=%s cov=%s" % (len((ep or {}).get("endpoints") or []), (ep or {}).get("total"),
                                              ca["total"]))
        add("J4e 仓库跟踪副本 == worktree 归档副本（投影后逐字段，历史 56/131）", bool(cr_) and cr_ == ca,
            "repo=%s arch=%s" % ((cr_ or {}).get("total"), ca["total"]))

    # ---------- J5 交付面 / 在途 / worktree ----------
    add("J5a 我**方**提交（被测提交..HEAD ∖ 已申报他方提交）触及交付面的提交 == 0",
        ctx["delivery_commits"] == 0,
        "count=%d（区间内触及交付面 %d 枚，其中申报他方 %d 枚；被测提交=%s）"
        % (ctx["delivery_commits"], ctx["delivery_commits_all"], len(ctx["external"]),
           facts.get("FACTS_TESTED_COMMIT")))
    bad_files = [x for x in ctx["round_touched"] if x.startswith(DELIVERY_PREFIXES)]
    add("J5b 我方改动集合不含交付面前缀（相位 = %s）" % ctx["phase"],
        bool(ctx["round_touched"]) and not bad_files,
        "改动 %d 个 / 越界 %d 个 %s" % (len(ctx["round_touched"]), len(bad_files), bad_files[:5]))
    # J5h = **直接不变量**：我方提交链改动文件 ∩ 窗口起点他方在途集合 == ∅（须 0 条交集）。
    # 它比下面的快照差集更贴语义：差集判据会把**他方自己的**活动（撤下自己的在途文件）算成我方违规
    # （判据范围与语义不符，历史 81/193/198）。正向对照要求**两侧都非空**，否则 `∩ = ∅` 是空转假绿（历史 98）。
    overlap = sorted(set(ctx["round_touched"]) & set(ctx["inflight"]))
    add("J5h 我方改动集合 ∩ 窗口起点他方在途集合 == ∅（正向对照：我方改动 > 0 ∧ 在途 > 0）",
        bool(ctx["round_touched"]) and len(ctx["inflight"]) > 0 and not overlap,
        "我方 %d 个 / 在途 %d 个 / 交集 %s" % (len(ctx["round_touched"]), len(ctx["inflight"]), overlap or "0 条"))
    # 差集方向一：他方在途条目的消失/改动**必须显式申报**（`--external-withdrawn`），且申报项逐条可核
    # （「在窗口起点快照里 ∧ 已从快照消失 ∧ 不落在我方改动集合里」三条件缺一即不可核）。未申报 ⇒ 照旧红。
    gone_bad = [p for p in ctx["inflight_gone"] if p not in set(ctx["ext_withdrawn"])]
    add("J5c 快照差集方向一：消失/改动的在途条目**全部已申报**（他方自主撤下须显式申报；须 0 条未申报 ∧ 0 条不可核申报）",
        len(ctx["inflight"]) > 0 and not gone_bad and not ctx["ext_withdrawn_bad"],
        "在途 %d 条 / 消失 %s / 已申报撤下 %s / 未申报 %s / 不可核申报 %s"
        % (len(ctx["inflight"]), ctx["inflight_gone"] or "0 条", ctx["ext_withdrawn"] or "无", gone_bad or "无",
           ctx["ext_withdrawn_bad"] or "无"))
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
    add("J5f 在途改动落在窗口内的条目**全部已解释**（申报装置改动 / 他方提交触及 / 他方自主撤下 / **装置链自写**；未解释 ⇒ 红）",
        ctx["window_start_ts"] > 0 and len(ctx["inflight"]) > 0 and not ctx["inflight_late_eff"],
        "在途 %d 条 / 落在窗口内（已剔除申报项：装置 %d ＋ 他方提交触及 %d ＋ 自主撤下 %d ＋ 装置链自写 %d；其中「文件已不在磁盘」%d 条）%s"
        % (len(ctx["inflight"]), len(ctx["inflight_late_exempt"]), len(ctx["ext_files"]),
           len(ctx["ext_withdrawn"]), len(ctx["inflight_late_selfwritten"]), len(ctx["inflight_late_unread"]),
           ctx["inflight_late_eff"] or "0 条"))
    # J5i/J5j = 「装置链自写面」的判据可用性 + 落盘纪律（历史 66 第 4 类；约定出处 = 提交 0aee5e72
    # 「回归面每次复跑都会重写 ⇒ 每轮须落盘」）。两者都**机器派生**：名字取自命令表脚本源码里的证据文件名。
    add("J5i 装置链自写面解析到 N 个证据文件名（正向对照 > 0；0 即判据失效，历史 46/75）",
        len(ctx["selfwritten_names"]) > 0,
        "自写面 %d 个 / 命令表脚本 %d 个：%s"
        % (len(ctx["selfwritten_names"]), len(ctx["manifest_scripts"]),
           "、".join(ctx["selfwritten_names"][:6]) or "（空）"))
    pre_phase = str(ctx["phase"]).startswith("提交前")
    add("J5j 装置链自写面的**追踪**文件 mtime 落窗 ⇒ 提交后必须与 HEAD 一致（「每轮须落盘」，约定出处 = 提交 0aee5e72）",
        pre_phase or not ctx["selfwritten_dirty"],
        "落窗自写追踪文件 %d 个%s；%s"
        % (len(ctx["selfwritten_scope"]),
           ("（" + "、".join(ctx["selfwritten_scope"]) + "）") if ctx["selfwritten_scope"] else "",
           "本判据不适用（提交前相位：工作区尚未提交，历史 243-①）" if pre_phase
           else ("与 HEAD 不一致 %d 个" % len(ctx["selfwritten_dirty"]))))
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
    names = evidence_core(R)
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
def build_ctx(ROUND, declared, external=(), withdrawn=()):
    W = T / "aap-round-verify" / ROUND
    facts = parse_facts(rd_text(W / ("facts-%s.log" % ROUND)))
    tested = facts.get("FACTS_TESTED_COMMIT", "HEAD")
    # ---- 他方并发活动：显式申报 + 逐枚/逐条可核（未申报的外部活动照旧响亮失败，历史 81/193/198） ----
    ext_files, ext_bad = [], []
    for s in external:
        a_in, _, _ = sh("merge-base", "--is-ancestor", s, "HEAD")      # 必须是 HEAD 的祖先
        a_old, _, _ = sh("merge-base", "--is-ancestor", s, tested)     # 但**不得**落在被测提交及更早
        _, subj, _ = sh("log", "-1", "--format=%s", s)
        if a_in != 0 or a_old == 0 or (ROUND in subj):
            ext_bad.append(s)
            continue
        _, fs, _ = sh("show", "--name-only", "--format=", s)
        ext_files.extend(x.strip() for x in fs.splitlines() if x.strip())
    ext_files = sorted(set(ext_files))
    ext_short = [s[:7] for s in external]
    # 相位判定的**判据范围**：`<被测提交>..HEAD` 的**全部路径**提交数（历史 81/141/175）。
    # 只看 `-- tools/` 会让「装置面与交付面均零改动」的轮次在**提交后**仍被判成「提交前」，
    # 于是它去读已清空的工作区得到空集合，而 J5b 把空集合判成「判据不可用」⇒ 对合法状态报假失败。
    # 「本轮**自己的**提交数」= 区间提交数 ∖ 已申报他方提交（他方提交不发源于本轮）。
    _, out_c, _ = sh("rev-list", "--count", "%s..HEAD" % tested)
    _, files_c, _ = sh("diff", "--name-only", "%s..HEAD" % tested)
    _, files_t, _ = sh("diff", "--name-only", "%s..HEAD" % tested, "--", "tools/")
    _, out_w, _ = sh("status", "--porcelain", "--", "tools/")
    dirty = sorted(ln[3:].strip().strip('"') for ln in out_w.splitlines() if ln.strip())
    ncc = int(out_c.strip() or "0")
    all_commit_files = sorted(x.strip() for x in files_c.splitlines() if x.strip())
    own_commit_files = own_of(all_commit_files, ext_files)      # 归属归一（纯函数：只对成员生效）
    n_own = max(0, ncc - len([s for s in external if s not in ext_bad]))
    committed = sorted(x.strip() for x in files_t.splitlines() if x.strip() and x.strip() not in set(ext_files))
    sb = rd_text(W / "root-status-before.txt")
    sa = rd_text(W / "root-status-after.txt")
    inflight = status_paths(sb)
    phase, round_touched = phase_and_touched(
        n_own, own_commit_files, status_paths(sh("status", "--porcelain")[1]), inflight)
    # 装置面改动取**并集**（工作区未提交 ∪ 提交链），与 `closeout.py` 的同一判据同源 ——
    # 提交后仍留未提交的 tools/ 改动时不能被静默漏掉（历史 81/195）。
    device_actual = sorted(set(committed) | set(dirty)) if ncc else dirty
    _dlrc, out_d, _ = sh("rev-list", "%s..HEAD" % tested, "--", "aap-server/", "docs/", "aap-client/")
    all_delivery = [x.strip() for x in out_d.splitlines() if x.strip()] if _dlrc == 0 else []
    own_delivery = [c for c in all_delivery
                    if not any(c.startswith(s) or s.startswith(c) for s in ext_short)]
    delivery_commits = len(own_delivery) if _dlrc == 0 else -1
    delivery_commits_all = len(all_delivery)
    wtp = facts.get("WORKTREE_PATH", "")
    _, wtl, _ = sh("worktree", "list", "--porcelain")
    ws_ts = int(facts.get("FACTS_WINDOW_START_TS", "0") or "0")
    late, late_unread = [], []
    for p in inflight:
        try:
            if (ROOT / p).stat().st_mtime > ws_ts:
                late.append(p)
        except OSError:
            # 不可读（文件已不在磁盘上）= 他方在窗口内撤下自己的在途文件，与「mtime 落在窗口内」同类。
            # 判据对象一律存**原始路径**（不带后缀）：后缀会让 J5f 的申报豁免比对恒不命中
            # （「判据里的字符串必须与对象同形」，历史 218/225）。
            late.append(p)
            late_unread.append(p)
    # ---- 装置链自写面（机器派生；J5f 第 4 类豁免 + J5i/J5j 的判据对象，历史 66/210） ----
    m_scripts = manifest_script_args(rd_text(DEV_DIR / "manifest.json"))
    sw_names = writer_output_names([(s, rd_text(ROOT / s)) for s in m_scripts])
    sw_late = selfwritten_exempt(late, sw_names)
    # J5j 的作用域 = 自写面里的**追踪**文件 ∧ mtime 落窗（未追踪的本轮新证据不在「须落盘」纪律内，历史 222）。
    # 注意它**不能**从 `inflight` 推（那份快照取自窗口起点）：文件在窗口起点干净、被命令表在窗口内重写时
    # 同样必须进作用域 —— 否则「忘了落盘」这类缺陷永远看不见（历史 98/187：判据范围必须覆盖语义）。
    sw_scope = []
    for n in sw_names:
        p = EVID_PREFIX + n
        try:
            if not (ROOT / p).exists() or int((ROOT / p).stat().st_mtime) <= ws_ts:
                continue
        except OSError:
            continue
        if sh("ls-files", "--error-unmatch", "--", p)[0] != 0:
            continue
        sw_scope.append(p)
    sw_dirty = [p for p in sw_scope if sh("status", "--porcelain", "--", p)[1].strip()]
    after_paths = status_paths(sa)
    gone = sorted(set(inflight) - set(after_paths))
    added = sorted(set(after_paths) - set(inflight))
    foreign = [p for p in added if not p.startswith(MY_PREFIXES)]
    # 他方自主撤下的申报必须**三条件可核**：① 在窗口起点快照里 ② 已从快照消失 ③ **不落在我方改动集合里**。
    # 第 ③ 条才是牙齿：若我方提交/改动了该路径，申报必须被驳回（否则「申报」可架空 J5c，历史 57/68/190）。
    own_changes = set(own_commit_files) | set(round_touched)
    wd_bad = [p for p in withdrawn
              if not (p in inflight and p not in after_paths and p not in own_changes)]
    ev_disk = set(p.name for p in EV.iterdir() if p.is_file())
    ev_cr = {}
    for nm in evidence_core(ROUND):
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
        "inflight_late_unread": late_unread,
        # J5f 的**判据范围**：本轮**已申报**的装置改动、他方提交触及的文件、他方自主撤下的在途路径
        # 按定义会在窗口内落地/变化，不能与他方在途的「未解释」项混谈（判据范围必须与语义一致，
        # 历史 81/193/195）；豁免 = 申报集合的子集（机器核对，不是人列举）。
        "inflight_late_eff": late_unexplained(late, declared, ext_files, withdrawn, sw_late),
        "inflight_late_exempt": [p for p in late if p in set(declared)],
        # J5f 的**第 4 类**解释项：装置链自写面（机器派生，见文件上方 WRITE_MARK_RE 段）
        "manifest_scripts": m_scripts, "selfwritten_names": sw_names,
        "inflight_late_selfwritten": sw_late, "selfwritten_scope": sw_scope,
        "selfwritten_dirty": sw_dirty,
        "status_paths_after": after_paths, "inflight_gone": gone, "inflight_added": added,
        "inflight_foreign": foreign,
        "window_start_ts": ws_ts,
        "wt_path": wtp, "wt_exists": bool(wtp) and Path(wtp).exists(), "wt_list": wtl,
        "device_actual": device_actual, "declared": list(declared), "phase": phase,
        "external": [s for s in external if s not in ext_bad], "external_bad": ext_bad,
        "ext_files": ext_files,
        "ext_withdrawn": [p for p in withdrawn if p not in wd_bad], "ext_withdrawn_bad": wd_bad,
        "own_commit_files": own_commit_files,
        "delivery_commits": delivery_commits, "delivery_commits_all": delivery_commits_all,
        "round_touched": round_touched,
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

# 红相位夹具：与 SYNTH_RUN 只差「合计有失败 / 类级失败行 / BUILD FAILURE」，且@测试数仍与合计一致
SYNTH_RUN_RED = """[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 1.0 s -- in com.x.ATest
[ERROR] Tests run: 1, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.1 s <<< FAILURE! -- in com.x.CovTest
[ERROR] Tests run: 3, Failures: 1, Errors: 0, Skipped: 0
[ERROR] BUILD FAILURE
[INFO] Total time:  01:04 min
"""


def synth_ctx():
    facts = parse_facts(SYNTH_FACTS)
    run = parse_run(SYNTH_RUN)
    names = evidence_core(SYNTH_R)
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
        "inflight_late_unread": [],
        "inflight_late_eff": [], "inflight_late_exempt": [],
        "manifest_scripts": ["tools/audit-endpoint-tests.py"],
        "selfwritten_names": ["endpoint-test-audit.txt"], "inflight_late_selfwritten": [],
        "selfwritten_scope": [], "selfwritten_dirty": [],
        "wt_path": "C:/tmp/合成worktree-%s" % SYNTH_R, "wt_exists": False, "wt_list": "",
        "device_actual": list(dev), "declared": list(dev), "phase": "提交前（工作区未提交）",
        "external": [], "external_bad": [], "ext_files": [],
        "ext_withdrawn": [], "ext_withdrawn_bad": [],
        "own_commit_files": dev + [".agents/state/evidence/round-%s-analysis.txt" % SYNTH_R],
        "delivery_commits": 0, "delivery_commits_all": 0,
        "round_touched": dev + [".agents/state/evidence/round-%s-analysis.txt" % SYNTH_R],
        "ev_disk": set(names), "ev_cr": {n: 0 for n in names},
        "dev_hits": 0, "dev_scanned": 9, "dev_teeth": 1,
        "self_src": "合成源码：不含任何轮次号字面量",
    }


def synth_ctx_red():
    """红相位合成上下文：与 `synth_ctx()` **只差相位相关字段**（两轮 rc / 合计五元组 / 覆盖读数 / 未注册清单）。

    为什么必须有：J2b / J2c / J4a / J4c 都是**相位分支**判据，只有绿夹具时红分支**永不执行**
    （历史 32/75/98：判定有几个分支就要有几条反例）；本仓实测红相位下这四条曾报结构性假 FAIL。
    """
    c = dict(synth_ctx())
    run = parse_run(SYNTH_RUN_RED)
    nr = [{"id": "NEW-%02d" % i} for i in range(1, 4)]  # 3 条未注册 == missing == 3
    c.update(
        run1=run, run2=run, elapsed=[elapsed_tuple(SYNTH_RUN_RED)] * 2,
        facts=dict(parse_facts(SYNTH_FACTS), FACTS_RUN1_RC="1", FACTS_RUN2_RC="1"),
        cov_run=proj_cov({"total": 12, "implemented": 9, "missing": 3, "registered_routes": 12,
                          "not_registered": nr,
                          "by_task": {"": {"total": 2, "implemented": 2}, "T1": {"total": 10, "implemented": 7}}}),
        cov_repo=proj_cov({"by_task": {"T1": {"implemented": 7, "total": 10}, "": {"implemented": 2, "total": 2}},
                           "missing": 3, "implemented": 9, "total": 12, "registered_routes": 12,
                           "not_registered": nr}),
    )
    return c


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
    # 跨午夜（合法）判别力对照：窗口 23:58:00 → 次日 00:04:00，run1 结束 23:59:50、run2 起跑 00:00:05。
    # 按 HH:MM:SS **字符串**比会把 23:59:50 > 00:00:05 判成「非串行」（假失败）；按绝对时刻解算后必须**不新增 FAIL**。
    # 该对照同时证明修法没把牙齿拔掉：上面那条「注入到窗口之外」的用例仍必须照旧点名 J1g/J2g。
    mutate("窗口跨午夜（合法）：按绝对时刻解算必须不假失败",
           lambda c: c.update(facts=dict(c["facts"], **{
               "FACTS_WINDOW_START": "23:58:00", "FACTS_WINDOW_START_ISO": "2026-01-01 23:58:00",
               "FACTS_RUN1_START": "23:58:10", "FACTS_RUN1_END": "23:59:50",
               "FACTS_RUN2_START": "00:00:05", "FACTS_RUN2_END": "00:03:50",
               "FACTS_WINDOW_END": "00:04:00", "FACTS_WINDOW_END_ISO": "2026-01-02 00:04:00"})),
           [])
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
    mutate("覆盖 missing 变成 1（按族仍自洽 ⇒ 相位翻红、两轮全绿与之自相矛盾）",
           lambda c: c.update(cov_run=proj_cov({"total": 12, "implemented": 11, "missing": 1,
                                                "registered_routes": 9,
                                                "by_task": {"": {"total": 2, "implemented": 2},
                                                            "T1": {"total": 10, "implemented": 9}}})),
           ["J2b", "J2c", "J4a", "J4c", "J4e"])
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
    mutate("本轮改动集合为空（判据不可用而非合规；J5h 的正向对照同步转红，历史 98）",
           lambda c: c.update(round_touched=[]), ["J5b", "J5h"])
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
    mutate("在途条目 mtime 落在窗口内（他方在途，未申报装置改动）",
           lambda c: c.update(inflight_late_eff=["README.md"], inflight_late=["README.md"]), ["J5f"])
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

    # ---- T-P2/T-P3/T-P4：相位判据的**范围**（生产实测的装置缺陷回归守卫，历史 81/141/175/251） ----
    # 缺陷：`n_commits` 曾取 `rev-list --count <被测>..HEAD -- tools/` ⇒ 零装置改动轮在**提交后**
    # 被判成「提交前」⇒ 读已清空的工作区得空集合 ⇒ J5b 把空集合判成「判据不可用」⇒ **假失败**。
    _cf = [".agents/state/aap-server-feature-status.csv",
           ".agents/state/evidence/round-%s-analysis.txt" % SYNTH_R]
    _if = ["README.md", "aap-server/pom.xml"]
    _ph_new, _tc_new = phase_and_touched(3, _cf, [], _if)
    chk("T-P2 相位判据取**全部路径**提交数：零装置改动轮在提交后判「提交后」且集合非空（历史 81/141）",
        _ph_new.startswith("提交后") and sorted(_tc_new) == sorted(_cf),
        "相位=%s / 集合 %d 个" % (_ph_new, len(_tc_new)))
    _ph_old, _tc_old = phase_and_touched(0, _cf, [], _if)   # 旧口径：只看 tools/ 提交 ⇒ 0 枚
    _b_old = fails_of(evaluate(dict(synth_ctx(), phase=_ph_old, round_touched=_tc_old)))
    chk("T-P3 反证：旧口径在同一输入上得**空集合**且 J5b 据此假失败 ⇒ 证明本次修复非空转",
        _tc_old == [] and "J5b" in _b_old, "旧集合=%s / 旧相位=%s / FAIL=%s" % (_tc_old, _ph_old, _b_old))
    _ph_pre, _tc_pre = phase_and_touched(0, _cf, ["留痕A", "留痕B"] + _if, _if)
    chk("T-P4 提交前相位：工作区条目 − 他方在途（须把他方在途剔干净，历史 193/198）",
        _ph_pre.startswith("提交前") and sorted(_tc_pre) == ["留痕A", "留痕B"] and bool(_tc_pre),
        "相位=%s / 集合=%s" % (_ph_pre, _tc_pre))

    # ---- T18/T19：失败类级行的形态 + 红相位分支（本仓生产实测的两处装置缺陷的回归守卫） ----
    chk("T18 失败类级行（`<<< FAILURE!` 变体）必须被解析到：类级求和 == 合计（历史 228/81）",
        (lambda rf: rf["n_class"] == 2 and bool(rf["totals"])
         and sum(v[0] for v in rf["classes"].values()) == rf["totals"][0][0] == 3)(parse_run(SYNTH_RUN_RED)),
        "旧判据（无 `(?: <<< FAILURE!)?`）会漏收失败类 → 类和 2 ≠ 合计 3")
    c_red = synth_ctx_red()
    bad_red = fails_of(evaluate(c_red))
    chk("T19 红相位合成上下文基线全绿（J2b/J2c/J4a/J4c 的红分支必须真的被执行到）", not bad_red,
        "FAIL=%s" % bad_red)
    def mutate_red(label, mut, expect):
        """红相位基线之上的判别力实测（基线必须另起名：拿绿基线比会让「消失」集合恒空，历史 93）。"""
        c = synth_ctx_red()
        mut(c)
        f = fails_of(evaluate(c))
        delta = sorted(set(f) - set(bad_red))
        gone = sorted(set(bad_red) - set(f))
        chk("T·%s → 恰好新增 %s" % (label, expect), delta == sorted(expect) and not gone,
            "新增=%s 消失=%s" % (delta, gone))

    mutate_red("红相位：run2 合计与 run1 不一致", lambda c: c.update(run2=parse_run(SYNTH_RUN)),
               ["J2b", "J2c", "J2e"])
    mutate_red("红相位：未注册清单比 missing 少一条（读数不自洽）", lambda c: c.update(
        cov_run=dict(c["cov_run"], not_registered=c["cov_run"]["not_registered"][:2])), ["J4a", "J4e"])
    mutate_red("红相位：BUILD FAILURE 但合计 0 失败（相位自相矛盾）", lambda c: c.update(
        run1=parse_run(SYNTH_RUN_RED.replace("Failures: 1, Errors: 0", "Failures: 0, Errors: 0")),
        run2=parse_run(SYNTH_RUN_RED.replace("Failures: 1, Errors: 0", "Failures: 0, Errors: 0"))), ["J2b"])

    # ---- 他方并发活动的申报语义（判据范围与语义一致，历史 81/193/198/227） ----
    # 正向对照（expect 空）：已申报且逐枚可核 = 合法态，必须**不新增 FAIL**；反例则必须**恰好点名**目标判据。
    mutate("已申报他方提交且逐枚可核（合法态，正向对照：不新增 FAIL）",
           lambda c: c.update(facts=dict(c["facts"], FACTS_HEAD_ADVANCED_COUNT="1"),
                              external=["deadbee"], external_bad=[], delivery_commits=0), [])
    mutate("申报项不可核（不在区间内 / 主题含本轮轮次号）",
           lambda c: c.update(facts=dict(c["facts"], FACTS_HEAD_ADVANCED_COUNT="1"),
                              external=["deadbee"], external_bad=["deadbee"]), ["J1c"])
    mutate("在途条目消失但**未申报**（原「原样保留」判据的牙齿仍在）",
           lambda c: c.update(inflight_gone=["aap-server/X.java"]), ["J5c"])
    mutate("在途条目消失且已申报他方自主撤下（合法态，正向对照：不新增 FAIL）",
           lambda c: c.update(inflight_gone=["aap-server/X.java"], ext_withdrawn=["aap-server/X.java"],
                              ext_withdrawn_bad=[]), [])
    mutate("申报撤下但该路径落在我方改动集合里（不可核 ⇒ 必须转红，豁免不得被架空）",
           lambda c: c.update(inflight_gone=["aap-server/X.java"], ext_withdrawn=["aap-server/X.java"],
                              ext_withdrawn_bad=["aap-server/X.java"]), ["J5c"])
    mutate("我方改动集合落在窗口起点他方在途文件上（J5h 直接不变量）",
           lambda c: c.update(round_touched=list(c["round_touched"]) + ["README.md"]), ["J5h"])
    chk("T-EXT1 own_of 三态：恒等（空申报）/ 剔除成员 / 非成员不得被剔除（历史 57/68/190）",
        own_of(["a", "b"], []) == ["a", "b"] and own_of(["a", "b"], ["a"]) == ["b"]
        and own_of(["a", "b"], ["zz"]) == ["a", "b"], "见条件")
    chk("T-EXT2 ext_commits_ok 四态：零/合法/未申报/不可核",
        ext_commits_ok(0, [], []) and ext_commits_ok(1, ["s"], [])
        and not ext_commits_ok(1, [], []) and not ext_commits_ok(0, ["s"], ["s"]), "见条件")
    # 本轮真实返工的回归守卫：J5f 的豁免必须与 `late` 项**同形**（不可读项存原始路径）。
    chk("T-EXT3 late_unexplained 三态：未解释原样 / 已申报撤下豁免 / **带后缀的对象豁免失效**（旧写法指纹）",
        late_unexplained(["a"], [], [], []) == ["a"]
        and late_unexplained(["a"], [], [], ["a"]) == []
        and late_unexplained(["a（不可读）"], [], [], ["a"]) == ["a（不可读）"], "见条件")

    # ---- 装置链自写面（J5f 第 4 类豁免 + J5i/J5j 落盘纪律；约定出处 = 提交 0aee5e72，历史 66/210） ----
    chk("T-SW1 writer_output_names 三态：写脚本命中 / 无写标记脚本不命中 / 空输入空集",
        writer_output_names([("a.py", 'X = "e.txt"\nP.write_text(X)')]) == ["e.txt"]
        and writer_output_names([("a.py", 'X = "e.txt"\nprint(X)')]) == []
        and writer_output_names([]) == [], "三态各一条")
    chk("T-SW2 manifest_script_args 两态：解析 cmd 实参里的脚本 / 坏 JSON 退化为空集",
        manifest_script_args('{"audits":[{"tag":"t","cmd":["py.exe","tools/x.py","--check"]}],'
                             '"selftests":[{"cmd":["py.exe","tools/y-selftest.py"]}]}')
        == ["tools/x.py", "tools/y-selftest.py"]
        and manifest_script_args("{ 不是 JSON") == [], "两态各一条")
    chk("T-SW3 selfwritten_exempt 两态 + 两条反例：证据目录 ∧ basename 命中才豁免",
        selfwritten_exempt([".agents/state/evidence/e.txt"], ["e.txt"]) == [".agents/state/evidence/e.txt"]
        and selfwritten_exempt(["README.md"], ["README.md"]) == []
        and selfwritten_exempt([".agents/state/evidence/other.txt"], ["e.txt"]) == [], "见条件")
    chk("T-SW4 late_unexplained 第 4 类：自写豁免生效 ∧ 非自写项不得被豁免（历史 57/68/190）",
        late_unexplained([".agents/state/evidence/e.txt"], [], [], [], [".agents/state/evidence/e.txt"]) == []
        and late_unexplained(["README.md"], [], [], [], [".agents/state/evidence/e.txt"]) == ["README.md"],
        "见条件")
    # 正向对照 = 自写的落窗项**必须不新增 FAIL**；反例 = 同一项未被豁免时必须点名 J5f。
    mutate("落窗在途项属装置链自写面（合法态，正向对照：不新增 FAIL）",
           lambda c: c.update(inflight_late=[".agents/state/evidence/e.txt"], inflight_late_eff=[],
                              inflight_late_selfwritten=[".agents/state/evidence/e.txt"]), [])
    mutate("落窗在途项**不属**自写面（README.md 永远无法被豁免）",
           lambda c: c.update(inflight_late=["README.md"], inflight_late_eff=["README.md"],
                              inflight_late_selfwritten=[]), ["J5f"])
    mutate("自写面解析为空（判据失效 ⇒ 必须点名 J5i，历史 46/75）",
           lambda c: c.update(selfwritten_names=[]), ["J5i"])
    mutate("提交后相位 + 落窗自写追踪文件与 HEAD 不一致（漏落盘 ⇒ 点名 J5j）",
           lambda c: c.update(phase="提交后（提交链 1 枚）", selfwritten_scope=[".agents/state/evidence/e.txt"],
                              selfwritten_dirty=[".agents/state/evidence/e.txt"]), ["J5j"])
    mutate("提交前相位 + 同一读数（判据不适用 ⇒ 不得假失败，历史 243-①）",
           lambda c: c.update(phase="提交前（工作区未提交）", selfwritten_scope=[".agents/state/evidence/e.txt"],
                              selfwritten_dirty=[".agents/state/evidence/e.txt"]), [])

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
        print("用法: python tools/round-verify/independent.py <轮次> [--device-change <路径>]...")
        print("      [--external-commit <他方提交短号>]... [--external-withdrawn <他方自主撤下的在途路径>]...")
        print("      [--no-write]")
        print("      python tools/round-verify/independent.py --selftest")
        return 2

    def _vals(flag):
        n = sum(1 for a in args if a == flag)
        v = [args[i + 1] for i, a in enumerate(args) if a == flag and i + 1 < len(args)]
        return n, v

    n_flag, declared = _vals("--device-change")
    n_ex, external = _vals("--external-commit")
    n_wd, withdrawn = _vals("--external-withdrawn")
    if len(declared) != n_flag or len(external) != n_ex or len(withdrawn) != n_wd:
        print("[FAIL] --device-change / --external-commit / --external-withdrawn 缺参数值")
        return 2
    ctx = build_ctx(ROUND, declared, external, withdrawn)
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
         "申报的他方并发活动 = 提交 %s / 自主撤下的在途路径 %s（判据 J1c/J5a/J5b/J5c/J5f 的**前提**由它们给出；"
         "未申报的外部活动照旧响亮失败，历史 81/193/198）"
         % (ctx["external"] or "（无）", ctx["ext_withdrawn"] or "（无）"),
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
