#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""装置侧证据生成器（**轮次无关**：`python tools/round-verify/device-report.py <轮次> --rework N --note <要点文件>`）。

为什么有它：历史上「装置侧证据」是每轮**现写一份脚本**（上一轮那版 24,579 字节，硬编码轮次号 / 被测提交 /
当轮发现），只活在 `$TEMP`（历史 169/177：系统清理即永久退场，且每轮都要重踩锚点过期一族缺陷）。
本工具把其中**可机器推导**的部分固化，人只提供 --note 里的返工条目叙事：

  一、装置面改动：被测提交..HEAD 触及装置目录的提交 + 工作区未提交条目 + 逐文件 numstat + 轮次无关性守卫；
  二、本轮返工真值：由 `--rework` 给出，条目文本来自 `--note`（单一事实源，与台账 / 状态文件共用）；
  三、本轮关键读数：读自 analyze / regression 证据（零手写值）；
  四、交付面零改动三判据：worktree 与 HEAD 差异行 + 窗口归属分类 + 本轮提交改动文件集合；
  五、下一族：由覆盖 missing 推出（missing=0 ⇒ 无）。

纪律：
  * 纯值只从 facts 与证据读，源码内零硬编码（历史 201/206/243-③）；本文件**不得**出现当前轮次号字面量；
  * 每个解析到的读数配 `> 0` 正向对照（历史 46/75/98：「0 发现」先怀疑判据）；
  * 写盘 `newline="\n"`（历史 69/84/146），写完**只读复核**（CR=0 / 结束标记 / 行数下限）；
  * `--selftest` = 纯函数的负向自测（合成夹具，零仓库写入）；合成轮次号一律**运行期拼接**，
    不写进源码字面量（否则本轮「轮次无关性守卫」会命中自己）。
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# 证据落盘一律 LF（历史 69/84/146）：Windows 上 `python … > evidence.txt` 的 stdout 默认把 "\n" 翻成 CRLF。
# 本工具此前**漏了**这一条（实测 `device-report.py <轮次> --selftest` 产出 CR=12 / 12 行，而 `regression.py` /
# `final-check.py` / `independent.py` 的同类输出 CR=0）；证据文件本身走 `write_text(newline="\n")` 不受影响，
# 但 stdout 回显（以及任何按行解析它的消费者）会被 `\r` 破坏锚定。与同族工具同源做法。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(newline="\n")
    except (ValueError, OSError):
        pass

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
T = Path("C:/Users/laitz/AppData/Local/Temp")
# 本轮自己产物的**合法归属**（留痕目录 / 装置目录）—— 窗口起点之后出现在别处的改动即「归属未定」（须为 0）。
STATE_PREFIXES = (".agents/state/", "tools/")
# 交付面路径前缀（出现即「本轮碰了交付面」，须为 0）。
DELIVERY_PREFIXES = ("aap-server/", "docs/", "aap-client/")
END_MARK = "DEVICE_REPORT_END=1"
SEP = "\x1f"


def partition_commits(log_text, external, prefixes):
    """把 `git log --format=%h%x1f%s --name-only <range>` 的输出切成 [(sha, subject, files)]，
    并按「是否显式申报为他方提交」分区。

    判据与语义一致（历史 81/193/198）：只有**本轮自己的提交**触及交付面才算命中。
    旧版把整个 `被测提交..HEAD` 区间当成「本轮提交」⇒ 他方在本轮窗口内推进提交时，
    他方的交付面改动会被误报成「本轮碰了交付面」（判据范围与语义不符）。
    返回 (commits, bad_files, ext_rows, missing_external)。"""
    commits, cur = [], None
    for ln in log_text.splitlines():
        if SEP in ln:
            sha, subj = ln.split(SEP, 1)
            cur = [sha.strip(), subj.strip(), []]
            commits.append(cur)
        elif ln.strip() and cur is not None:
            cur[2].append(ln.strip())
    shas = {c[0] for c in commits}
    missing = [s for s in sorted(external) if s not in shas]
    bad, ext_rows = [], []
    for sha, subj, files in commits:
        hits = [f for f in files if f.startswith(prefixes)]
        if sha in external:
            ext_rows.append((sha, subj, hits))
        else:
            bad.extend(hits)
    return [tuple(c) for c in commits], bad, ext_rows, missing


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def sh(*a):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(a), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def parse_facts(path):
    out = {}
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def ts2s(mt):
    """epoch 秒 -> 本地可读时刻（证据里只展示，不参与判据）。"""
    if mt < 0:
        return "(不可读)"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mt))


def classify(entries, window_ts, state_prefixes=STATE_PREFIXES, delivery_prefixes=DELIVERY_PREFIXES):
    """按「mtime 是否 >= 窗口起点」+「路径归属」分类。

    entries = [(status, path, mtime_ts)] -> dict(before, mine, unknown, delivery_touched)
      before  = 窗口起点之前（他方在途，只登记不触碰）
      mine    = 窗口起点之后且落在留痕 / 装置目录（= 本轮自己的产物）
      unknown = 窗口起点之后但落在别处（**须为 0**，否则「本轮改了什么」说不清）
      delivery_touched = 窗口起点之后且落在交付面前缀（**须为 0** ＝ 交付面零改动）
    判据范围与语义一致（历史 81）；边界取「>=」：窗口起点这一刻之后的改动才算本轮。
    """
    before, mine, unknown, touched = [], [], [], []
    for st, p, mt in entries:
        if mt < window_ts:
            before.append((st, p, mt))
            continue
        if p.startswith(state_prefixes):
            mine.append((st, p, mt))
        else:
            unknown.append((st, p, mt))
        if p.startswith(delivery_prefixes):
            touched.append((st, p, mt))
    return {"before": before, "mine": mine, "unknown": unknown, "delivery_touched": touched}


def scan_round_ref(text, digits):
    """扫「当前轮次号」的**全部写法**（历史 186/195：只换一种写法会静默漏）。

    口径 = 词边界 + `R` + 数字串；返回 (命中行号列表, 命中数)。行号 1-based。
    """
    pat = re.compile(r"\bR" + re.escape(str(digits)) + r"\b")
    hits = [i + 1 for i, ln in enumerate(text.splitlines()) if pat.search(ln)]
    return hits, len(hits)


def selftest(round_str):
    """纯函数负向自测：合成夹具，零仓库写入（历史 32/46：判定有几个分支就要有几条反例）。"""
    digits = round_str[1:]
    checks = []

    def chk(name, cond, info=""):
        checks.append((name, bool(cond), info))

    W = 1000
    entries = [
        ("M", "aap-server/pom.xml", W - 50),                 # 窗口前 · 他方在途（交付面路径但早于窗口）
        ("M", "README.md", W - 10),                          # 窗口前 · 他方在途
        ("M", ".agents/state/evidence/x.json", W),           # 边界：恰在窗口起点 -> 本轮产物
        ("??", "tools/round-verify/new.py", W + 5),          # 本轮装置产物（未跟踪）
        ("M", "README.md", W + 7),                           # 窗口后 · 归属未定（须为 0）
        ("M", "aap-server/src/main/java/X.java", W + 9),     # 窗口后 · 命中交付面（须为 0）
    ]
    c = classify(entries, W)
    chk("S1 窗口前条目归类 before", len(c["before"]) == 2)
    chk("S2 边界（mtime == 窗口起点）归于本轮 mine", any(p == ".agents/state/evidence/x.json" for _, p, _ in c["mine"]))
    chk("S3 装置目录未跟踪条目归 mine", any(p == "tools/round-verify/new.py" for _, p, _ in c["mine"]))
    chk("S4 窗口后 / 非留痕目录 -> unknown（须为 0 的那一类；此夹具里 2 条：README.md 与交付面 X.java）",
        len(c["unknown"]) == 2
        and sorted(p for _, p, _ in c["unknown"]) == ["README.md", "aap-server/src/main/java/X.java"],
        "实测 %d 条：%s" % (len(c["unknown"]), sorted(p for _, p, _ in c["unknown"])))
    chk("S5 窗口后 / 交付面路径 -> delivery_touched", len(c["delivery_touched"]) == 1)
    chk("S6 三分类计数守恒（before + mine + unknown == 输入条数）",
        len(c["before"]) + len(c["mine"]) + len(c["unknown"]) == len(entries))
    chk("S7 早于窗口的交付面路径**不得**算作交付面命中（否则他方在途会被算作本轮改动）",
        all(p != "aap-server/pom.xml" for _, p, _ in c["delivery_touched"]))

    # 轮次无关性守卫的**判别力**：合成串运行期拼接（源码里不出现本轮次号字面量）
    synth = "历史示例 R" + digits + " 与超串 R" + digits + "0"
    h1, n1 = scan_round_ref(synth, digits)
    chk("S8 守卫对合成串命中 1 次（证明它非空转，历史 75/98）", n1 == 1, "命中 %d：%s" % (n1, h1))
    # 历史 220/573（合成非真值必须**参数化** + 前置断言「合成值 != 真值」）：
    # 旧写法 `digits[:-1] + "0"`（「相邻轮次号」）在**轮次号以 0 结尾**时退化为真值本身，
    # 于是这条「必须 0 命中」的负向对照里混进了真值 ⇒ 每 10 轮必 FAIL 一次
    # （历史 12/95：成对断言在某一轮把真值形态与合成形态指向同一个串，判据自相矛盾）。
    # 改为「末位在 0/1 之间翻转」（与真值同长、同形、无包含关系且**必不相等**），
    # 并把「合成值 != 真值」并入本判据 —— 判据与合成值由不同来源推出，不再可能在某轮相等。
    synth_adj = digits[:-1] + ("1" if digits.endswith("0") else "0")
    h2, n2 = scan_round_ref("历史示例 R" + synth_adj + " 与 R" + digits + "0", digits)
    chk("S9 守卫对「超串 / 相邻轮次号」不命中（词边界生效；合成值须 != 真值）",
        n2 == 0 and synth_adj != digits, "命中 %d：%s（合成相邻轮次号 R%s）" % (n2, h2, synth_adj))
    h3, n3 = scan_round_ref("", digits)
    chk("S10 空文本命中 0（反向对照）", n3 == 0, "命中 %d" % n3)

    # 判别力：提交区间**按归属分区**（历史 81/193/198：他方在途不得算作本轮改动）
    log = ("aaaa111" + SEP + "feat(intake): 他方提交" + "\n"
           "aap-server/src/main/java/X.java" + "\n"
           "\n"
           "bbbb222" + SEP + "chore(state): R" + digits + " 本轮装置留痕" + "\n"
           ".agents/state/x.txt" + "\n")
    cm, bad, ext, miss = partition_commits(log, {"aaaa111"}, DELIVERY_PREFIXES)
    chk("S11 区间解析到 2 枚提交（正向对照）且他方提交的交付面改动**不**计入本轮",
        len(cm) == 2 and bad == [] and len(ext) == 1, "commits=%d bad=%s ext=%d" % (len(cm), bad, len(ext)))
    _cm2, bad2, ext2, _m2 = partition_commits(log, set(), DELIVERY_PREFIXES)
    chk("S12 未申报他方提交时交付面改动照旧判命中（向后兼容，不得放宽）",
        len(bad2) == 1 and ext2 == [], "bad=%s" % bad2)
    _cm3, _b3, _e3, miss3 = partition_commits(log, {"zzzz999"}, DELIVERY_PREFIXES)
    chk("S13 申报不存在的提交 -> missing 非空（判据失效，不得静默通过）",
        miss3 == ["zzzz999"], "missing=%s" % miss3)

    ok = sum(1 for _, c0, _ in checks if c0)
    for name, c0, info in checks:
        print("  [%s] %s%s" % ("PASS" if c0 else "FAIL", name, (" " + info) if info else ""))
    print("  判据：PASS %d / FAIL %d" % (ok, len(checks) - ok))
    print("SELFTEST_END=1")
    return 0 if ok == len(checks) else 1


def main():
    args = sys.argv[1:]
    ROUND = (args[0] if args else "").upper()
    if not re.fullmatch(r"R\d+", ROUND):
        print("用法: python tools/round-verify/device-report.py <轮次> --rework N --note <要点文件> "
              "[--external-commit <他方提交短号>]... [--selftest]")
        return 2
    if "--selftest" in args:
        return selftest(ROUND)
    REWORK = opt(args, "--rework")
    NOTE = opt(args, "--note")
    if not (REWORK is not None and re.fullmatch(r"\d+", REWORK)):
        print("[FAIL] --rework N 必填（返工真值由人判定，工具不猜）")
        return 2
    if not (NOTE and Path(NOTE).exists()):
        print("[FAIL] --note <文件> 必填（返工条目文本 = 单一事实源）")
        return 2
    note = Path(NOTE).read_text(encoding="utf-8", errors="replace")
    note = note.replace("\r\n", "\n").replace("\r", "\n").strip()
    if ("返工 %s 处" % REWORK) not in note:
        print("[FAIL] 要点文本里的返工计数与 --rework(%s) 不一致（两处分叉，历史 215）" % REWORK)
        return 2

    W = T / "aap-round-verify" / ROUND
    facts = parse_facts(W / ("facts-%s.log" % ROUND))
    if facts.get("FACTS_ROUND") != ROUND or facts.get("FACTS_WRITTEN") != "1":
        print("[FAIL] facts 轮次不符或未写完成标记（判据失效）")
        return 2
    TESTED = facts["FACTS_TESTED_COMMIT"]
    WSTART_TS = int(facts["FACTS_WINDOW_START_TS"])

    ana_p = EV / ("round-%s-analysis.txt" % ROUND)
    # 校验证据的前缀由**相位**推出（绿 `green-verify-*` / 红 `red-verify-*`，历史 12/554）——
    # 消费侧两种前缀都认（产出/消费双向一致，历史 181）。
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from phase import GREEN as _GREEN, phase_of as _phase_of, find_verify as _find_verify  # noqa: E402
    cov_p = _find_verify(EV, ROUND, "coverage-fields")
    if cov_p is None:
        print("[FAIL] 覆盖字段证据缺失：green-verify / red-verify 两种前缀都没有（须先跑 analyze.py，历史 181）")
        return 2
    reg_p = EV / ("audit-regression-%s.txt" % ROUND)
    # 跨轮 faildiff 是**独立证据文件**（不在主回归证据里）—— 读数源必须与产出方的写法一致（历史 205/218）：
    # 首版从主证据里找 faildiff 段 ⇒ 0 命中、断言响亮失败（修的是判据，不是期望值）。
    fdf_p = EV / ("audit-regression-%s-faildiff.txt" % ROUND)
    for p in (ana_p, cov_p, reg_p, fdf_p):
        if not p.exists():
            print("[FAIL] 证据缺失：%s（须先跑 analyze.py / regression.py）" % p.name)
            return 2
    ana = ana_p.read_text(encoding="utf-8", errors="replace")
    covf = cov_p.read_text(encoding="utf-8", errors="replace")
    reg = reg_p.read_text(encoding="utf-8", errors="replace")
    fdf = fdf_p.read_text(encoding="utf-8", errors="replace")

    # ---- 读数（全部从证据里解析，零手写；每个读数配 > 0 / 非 None 正向对照） ----
    def g1(text, pat, label):
        m = re.search(pat, text, flags=re.M)
        if not m:
            raise SystemExit("[FAIL] 读数未解析到：%s（判据失效，历史 46/168）" % label)
        return m

    m_jud = g1(ana, r"^判据：PASS (\d+) / FAIL (\d+)$", "analyze 判据行")
    NP, NF = m_jud.group(1), m_jud.group(2)
    m_streak = g1(ana, r"连续全绿 = 第 (\d+) 轮", "连续全绿轮次")
    STREAK = m_streak.group(1)
    m_cov = g1(covf, r"^total=(\d+) implemented=(\d+) missing=(\d+) registered_routes=(\d+) not_registered=(.*)$",
               "覆盖字段行")
    # `not_registered` 用 `(.*)` 而非 `(\S+)`：未注册清单非空时含空格（`[{'id': …}, …]`），
    # `\S+` 会**整行匹配失败**（历史 46：读数解析失败先怀疑判据；本仓实测红相位首次非空即暴露）。
    TOT, IMPL, MISS, ROUTES = m_cov.group(1), m_cov.group(2), m_cov.group(3), m_cov.group(4)
    m_rc = g1(reg, r"rc 变化 (\d+) 条、新增 (\d+)、未复跑 (\d+)", "回归面 rc 逐条比对行")
    m_fail = g1(reg, r"FAIL 明细：(\d+) 个脚本含 FAIL 行、合计 (\d+) 行", "回归面 FAIL 明细行")
    m_run = g1(reg, r"本轮复跑 = (\d+) 条 / 上一轮 (\S+) = (\d+) 条", "回归面复跑条数行")
    m_gone = g1(reg, r"零写副作用：生成物 size\+md5 运行前后 全等（变化 (\d+) 个）", "零写副作用行")
    m_emb = g1(fdf, r"上一轮 (\d+) 行 / 本轮 (\d+) 行；新增 (\d+) / 消失 (\d+)", "跨轮 faildiff 行")
    m_crash = g1(reg, r"rc!=0 条目 (\d+) 条，其中 FAIL 通道不可见[^\n]*= (\d+) 条", "崩溃通道行")
    if not (int(NP) > 0 and int(TOT) > 0 and int(m_run.group(1)) > 0 and int(m_fail.group(2)) > 0):
        print("[FAIL] 读数正向对照不足（0 发现先怀疑判据，历史 46/75/98）")
        return 2

    # ---- 一、装置面改动 ----
    DEV_DIR = "tools/round-verify"
    ls_before = [x for x in sh("ls-tree", "--name-only", "-r", "%s:%s" % (TESTED, DEV_DIR))[1].splitlines() if x.strip()]
    ls_now = sorted(p.name for p in (ROOT / DEV_DIR).iterdir() if p.is_file() and p.suffix in (".py", ".sh", ".json", ".md"))
    added = sorted(set(ls_now) - set(ls_before))
    removed = sorted(set(ls_before) - set(ls_now))
    _rc, log_out, _ = sh("log", "--format=%h %s", "%s..HEAD" % TESTED, "--", "tools/")
    dev_commits = [ln for ln in log_out.splitlines() if ln.strip()]
    _rc, st_out, _ = sh("status", "--porcelain", "--", "tools/")
    dev_dirty = [ln for ln in st_out.splitlines() if ln.strip()]
    # `git diff HEAD --numstat`（**不是** `git diff --numstat`）：后者比的是「工作区 vs 索引」，
    # 一旦装置改动已被 `git add`，它输出「无」而同段的 `status --porcelain` 仍列出 N 条 → 同一份证据自相矛盾
    # （历史 12/95 的自述侧，实测可复现：「工作区未提交 2 条」与「numstat 无」并存）。
    _rc, ns_out, _ = sh("diff", "HEAD", "--numstat", "--", "tools/")
    numstat = [ln for ln in ns_out.splitlines() if ln.strip()]

    # 轮次无关性守卫：本轮次号不得出现在**任何**装置脚本源码里（含本文件自身）。
    # 历史 201/205/217：派生 / 现写脚本硬编码当前轮次 ⇒ 产物对本轮作不实自述或下一轮必崩。
    guard_rows = []
    for p in sorted((ROOT / DEV_DIR).iterdir()):
        if p.is_file() and p.suffix in (".py", ".sh"):
            hits, n = scan_round_ref(p.read_text(encoding="utf-8", errors="replace"), ROUND[1:])
            guard_rows.append((p.name, hits, n))
    guard_total = sum(n for _, _, n in guard_rows)
    _h, guard_teeth = scan_round_ref("合成对照 R" + ROUND[1:] + " 行", ROUND[1:])
    if guard_total != 0 or guard_teeth != 1:
        print("[FAIL] 轮次无关性守卫：装置脚本内当前轮次号命中 = %d（须 0）/ 判别力对照 = %d（须 1）"
              % (guard_total, guard_teeth))
        return 2

    # ---- 四、交付面零改动三判据 ----
    _rc, porc, _ = sh("status", "--porcelain")
    entries = []
    for ln in porc.splitlines():
        if not ln.strip():
            continue
        path = ln[3:].strip().strip('"')
        try:
            mt = os.stat(str(ROOT / path)).st_mtime
        except OSError:
            mt = -1.0
        entries.append((ln[:2].strip(), path, mt))
    cls = classify(entries, WSTART_TS)
    # 本轮提交改动文件集合（被测提交..HEAD）——**按提交归属分区**：
    # 只有本轮自己的提交触及交付面才算命中；他方在本轮窗口内推进的提交必须显式申报
    # （`--external-commit <sha>`）后才不计入，且申报须可核（见下三处断言，历史 81/193/198）。
    _rc, dt_out, _ = sh("diff", "--name-only", "%s..HEAD" % TESTED)
    round_files = [x for x in dt_out.splitlines() if x.strip()]
    EXT = [args[i + 1] for i, a in enumerate(args) if a == "--external-commit"]
    _rc, log_out, _ = sh("log", "--format=%h%x1f%s", "--name-only", "%s..HEAD" % TESTED)
    commits, bad_files, ext_rows, missing_ext = partition_commits(log_out, set(EXT), DELIVERY_PREFIXES)
    if missing_ext:
        print("[FAIL] --external-commit 申报的提交不在 %s..HEAD 区间内：%s（申报不实 / 判据失效）"
              % (TESTED, missing_ext))
        return 2
    if [s for s, subj, _ in ext_rows if ROUND in subj]:
        print("[FAIL] --external-commit 申报的提交主题含本轮轮次号 %s —— 这不是他方提交（自述不实）" % ROUND)
        return 2
    if bad_files:
        print("[FAIL] 本轮自己的提交触及交付面路径 %d 条：%s" % (len(bad_files), bad_files[:5]))
        return 2

    # ---- 组文 ----
    L = []
    L.append("%s 装置侧证据（装置面改动 + 本轮返工真值 + 交付面零改动三判据）" % ROUND)
    L.append("=" * 78)
    L.append("生成方式：本文件由 `tools/round-verify/device-report.py` 从 git / facts / 证据的**真实输出**取值"
             "（数字零手写值），不接触交付面。")
    L.append("轮次 = %s；被测提交（HEAD 的独立 worktree 内检出）= %s；窗口 = %s -> %s（facts 落盘）"
             % (ROUND, TESTED, facts["FACTS_WINDOW_START_ISO"], facts["FACTS_WINDOW_END_ISO"]))
    L.append("")
    L.append("一、装置面改动（机器推导，零手写）")
    L.append("  被测提交的 `%s` 文件 = %d 个 / 工作区同名文件 = %d 个（新增 %d / 删除 %d）"
             % (DEV_DIR, len(ls_before), len(ls_now), len(added), len(removed)))
    if added:
        L.append("    新增：%s" % "、".join(added))
    if removed:
        L.append("    删除：%s" % "、".join(removed))
    L.append("  工作区未提交的 tools/ 条目 = %d 条%s"
             % (len(dev_dirty), ("：" + " | ".join(dev_dirty)) if dev_dirty else "（无）"))
    L.append("  「被测提交..HEAD」触及 tools/ 的提交 = %d 枚%s"
             % (len(dev_commits), ("：\n    " + "\n    ".join(dev_commits)) if dev_commits else "（本文件生成于主提交之前）"))
    L.append("  逐文件 numstat（工作区 vs HEAD，`插入/删除/路径`）：%s"
             % ("无" if not numstat else "; ".join(numstat)))
    L.append("  轮次无关性守卫：装置脚本（%d 个 .py/.sh）内当前轮次号命中 = **%d**（须 0" % (len(guard_rows), guard_total))
    L.append("    = 本轮的产物**不得**把当前轮次号写进装置源码，历史 201/205/217）；"
             "判别力对照 = %d（须 1，证明守卫非空转，历史 75/98）" % guard_teeth)
    L.append("")
    L.append("二、本轮返工真值 = **%s 处**（零交付面影响；条目文本来自单一事实源 `%s`，与台账描述列 / 状态文件小节共用）"
             % (REWORK, Path(NOTE).name))
    L.append("-" * 78)
    for ln in note.splitlines():
        L.append(ln)
    L.append("-" * 78)
    L.append("")
    L.append("三、本轮关键读数（读自 analyze / regression 证据，零手写值）")
    _phase = _phase_of(facts["FACTS_RUN1_RC"], facts["FACTS_RUN2_RC"], MISS)
    _streak_txt = (("连续第 %s 轮全绿" % STREAK) if _phase == _GREEN
                   else ("连续全绿计数 = %s（**红相位**清零）" % STREAK))
    L.append("  相位 = %s（两轮 rc=%s/%s ∧ missing=%s 的合取，判据见 tools/round-verify/phase.py）"
             % (_phase, facts["FACTS_RUN1_RC"], facts["FACTS_RUN2_RC"], MISS))
    L.append("  分析器判据 PASS %s / FAIL %s；覆盖 total=%s implemented=%s **missing=%s** registered_routes=%s；"
             "%s" % (NP, NF, TOT, IMPL, MISS, ROUTES, _streak_txt))
    L.append("  回归面：复跑 %s 条（上一轮 %s = %s 条）；rc 变化 %s / 新增 %s / 未复跑 %s；"
             "FAIL 明细 %s 脚本 %s 行" % (m_run.group(1), m_run.group(2), m_run.group(3),
                                          m_rc.group(1), m_rc.group(2), m_rc.group(3),
                                          m_fail.group(1), m_fail.group(2)))
    L.append("  零写副作用：生成物 size+md5 变化 %s 个（须 0）；跨轮 faildiff 上一轮 %s 行 / 本轮 %s 行、"
             "新增 %s / 消失 %s" % (m_gone.group(1), m_emb.group(1), m_emb.group(2), m_emb.group(3), m_emb.group(4)))
    L.append("  崩溃通道：rc!=0 条目 %s 条，其中 FAIL 通道不可见（rc!=0 ∧ FAIL 0 行）= %s 条"
             % (m_crash.group(1), m_crash.group(2)))
    L.append("")
    L.append("四、交付面零改动（三判据，避免把他方在途算作本轮改动，历史 81/193/198）")
    L.append("  ① 被测状态 = 提交态：worktree 与 HEAD 在 `aap-server/` 上的差异行数 = %s（facts `WT_DIRTY_LINES`，须 0）"
             % facts["WT_DIRTY_LINES"])
    L.append("  ② 工作区条目按 mtime 与**窗口起点**分三类：窗口前 %d 条（他方在途，只登记不触碰）/ "
             "窗口起点后且属留痕·装置目录 %d 条（本轮自己的产物）/ 其余（**归属未定**，须 0）%d 条；"
             "三类相加 = %d == `git status` 条目 %d"
             % (len(cls["before"]), len(cls["mine"]), len(cls["unknown"]),
                len(cls["before"]) + len(cls["mine"]) + len(cls["unknown"]), len(entries)))
    for st, p, mt in cls["before"]:
        L.append("      %s %s  mtime=%s" % (st, p, ts2s(mt)))
    for st, p, mt in cls["mine"]:
        L.append("      （本轮产物）%s %s  mtime=%s" % (st, p, ts2s(mt)))
    for st, p, mt in cls["unknown"]:
        L.append("      ⚠（归属未定）%s %s  mtime=%s" % (st, p, ts2s(mt)))
    if len(cls["before"]) + len(cls["mine"]) + len(cls["unknown"]) != len(entries):
        raise SystemExit("[FAIL] 归属分类计数与 git status 条数不等（判据失效）")
    L.append("      其中位于交付面前缀（%s）的窗口后条目 = %d 条（**须 0** ＝ 交付面零改动）"
             % ("、".join(x.rstrip("/") for x in DELIVERY_PREFIXES), len(cls["delivery_touched"])))
    L.append("  ③ 提交区间（%s..HEAD）改动文件 = %d 个；按**提交归属**分区（`--external-commit` 显式申报他方提交；"
             "申报须在区间内 ∧ 主题不含本轮轮次号）：区间内提交 %d 枚 = 他方 %d 枚 + 本轮 %d 枚"
             % (TESTED, len(round_files), len(commits), len(ext_rows), len(commits) - len(ext_rows)))
    for sha, subj, files in commits:
        tag = "他方（已申报）" if sha in set(EXT) else "本轮"
        nh = len([f for f in files if f.startswith(DELIVERY_PREFIXES)])
        L.append("      [%s] %s %s  文件 %d 个 / 交付面命中 %d 个"
                 % (tag, sha, subj[:64], len(files), nh))
    L.append("      ⇒ **本轮自己的提交**触及交付面前缀的 = %d 个（**须 0**）；他方提交的交付面改动不计入本轮"
             "（历史 81/193/198：他方在途不得算作本轮改动）" % len(bad_files))
    L.append("")
    L.append("五、下一族")
    if MISS == "0":
        L.append("  **无**（清单 %s/%s、missing=0）—— 本轮完成端点 0 条 / 新增用例 0 条、无红基线。"
                 % (IMPL, TOT))
    else:
        L.append("  missing=%s > 0：按 docs/backend 的任务顺序推进下一族（本轮完成端点 0 条 / 新增用例 0 条）。" % MISS)
    L.append("")
    L.append("六、留痕")
    out = EV / ("device-round-%s.txt" % ROUND)
    # 产出方与**消费方**的文件名必须机器核对（历史 181：写入格式 ⇔ 读取判据双向一致）——
    # 首版本工具写 `device-<轮次>.txt`，而 closeout.py 找的是 `device-round-<轮次>.txt` ⇒ 收尾会当场失败。
    _co = (ROOT / "tools/round-verify/closeout.py").read_text(encoding="utf-8", errors="replace")
    _m = re.findall(r'DEVEV = "(device-round-%s\.txt)" % ROUND', _co)
    if len(_m) != 1:
        raise SystemExit("[FAIL] closeout.py 的装置证据文件名判据解析到 %d 条（须 1，判据失效）" % len(_m))
    if _m[0].replace("%s", ROUND) != out.name:
        raise SystemExit("[FAIL] 本工具落盘名 %s 与 closeout.py 期望名 %s 不一致（产出/消费两侧须一致，历史 181）"
                         % (out.name, _m[0].replace("%s", ROUND)))
    L.append("  本文件 = %s（由本工具直接落盘，`newline=\"\\n\"`；文件名与 closeout.py 的消费名机器核对一致；行数下限判据与 CR=0 判据见下）"
             % out.relative_to(ROOT).as_posix())
    L.append(END_MARK)
    text = "\n".join(L) + "\n"
    if END_MARK not in text or text.count(END_MARK) != 1:
        raise SystemExit("[FAIL] 结束标记不唯一（判据失效，历史 222）")
    out.write_text(text, encoding="utf-8", newline="\n")
    # 写完**只读复核**（不拿「刚写下去的字节」当裁判，历史 230：断言必须落在实质内容上）
    rb = out.read_bytes()
    if rb.count(b"\r") != 0:
        print("[FAIL] 落盘含 CR（历史 69/84/146）")
        return 2
    got = rb.decode("utf-8")
    need = [ROUND, TESTED, "返工真值 = **%s 处**" % REWORK, "missing=%s" % MISS, "**须 0**"]
    missing_anchors = [x for x in need if x not in got]
    if missing_anchors:
        print("[FAIL] 落盘缺关键锚点：%s" % missing_anchors)
        return 2
    nlines = len(got.splitlines())
    if nlines < 30:
        print("[FAIL] 落盘行数 %d 过少（内容级下限，历史 200）" % nlines)
        return 2
    print("装置证据：%s（%d 行 / CR=0 / 锚点 %d 项全命中 / 装置提交 %d 枚 / 工作区 tools 条目 %d 条）"
          % (out.name, nlines, len(need), len(dev_commits), len(dev_dirty)))
    print("轮次无关性守卫：命中 %d（须 0）/ 判别力对照 %d（须 1）" % (guard_total, guard_teeth))
    print("DEVICE_REPORT_WROTE=%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
