#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""装置 README 自测条数取证（**轮次无关**）：`python tools/round-verify/selftest-counts.py <轮次>`

为什么有它：装置 README 引用的各工具 `--selftest` 条数是**纯数字自述**，机械轮次替换与任何审计都碰不到
（历史 201/206 的纯数字盲区族）。实测它与工具汇总行曾经分叉（自述 23/20/39 ⇔ 汇总行 26/23/44），
而**六个装置步骤全程无一处报警** —— 只能靠每轮显式核对。那次核对写在 `$TEMP` 的 aux 脚本里
（`emit-selftests.sh` + `consume.py`），而「只活在 $TEMP 的脚本」会随系统清理永久退场（历史 169/177/216）。
本工具把该核对固化为**轮次无关、可重跑、自带负向自测**的常驻实现。

判据（每条都配判别力实测；「0 发现」一律先怀疑判据，历史 46/75/98）：
  ① 每个工具的 `--selftest` 原始输出必须含**结束标记** —— 区分「完整结论」与「半截输出」（历史 240/251）；
  ② 汇总行支持**两种体裁**：`判据：PASS N / FAIL M`（审计/守卫类）与 `自测：N PASS / M FAIL（共 N 例）`
     （回归类）—— 数字与关键字的次序相反，只写一种 ⇒ 另一类整批 0 命中（历史 46/168）；
  ③ 条数 > 0 且 FAIL == 0（正向对照）；
  ④ README 自述条数 ⇔ 工具汇总行条数，逐工具相等；不等即**据实更正**，
     并做「写回后重读 ⇒ 判为已一致」的闭环复核（幂等，可重跑）；
  ⑤ 运行**全部** `--selftest` 前后 `git status --porcelain` **逐行相同**（只读守卫：装置自测不得有写副作用）。

纪律：本文件**不得**出现任何具体轮次号字面量（装置目录轮次无关性守卫，历史 201/205/217）；
证据一律 `newline="\\n"` 落盘并复核 CR==0（历史 69/84/146）。
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# 证据落盘一律 LF：Windows 上 `python … > out.txt` 的 stdout 默认把 "\n" 翻成 CRLF（同族工具同源做法）。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(newline="\n")
    except (ValueError, OSError):
        pass

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
DEV = ROOT / "tools" / "round-verify"
EV = ROOT / ".agents" / "state" / "evidence"
README = DEV / "README.md"
END_MARK = "SELFTEST_COUNTS_END=1"

# 汇总行两种体裁（见模块 docstring 判据②）。`\s*` 允许 `自测：26 PASS` 前的空格差异。
PAT = re.compile(r"^\s*(?:判据：PASS (\d+) / FAIL (\d+)|自测：\s*(\d+) PASS / (\d+) FAIL)", re.M)


def _argv_regression(R):
    # 注意：**只给子进程自己的实参** —— 脚本路径由 run_tool 拼在 `sys.executable` 之后。
    # 首版这里多带了一个脚本文件名，子进程把它当轮次 → `ROUND="REGRESSION.PY"` → rc=2 打用法行
    # （首跑被「结束标记缺失 + rc 报错」当场拦下，历史 46/175：崩溃/报错远好于静默产出）。
    return [R, "--selftest"]


def _argv_final_check(R):
    return [R, "--selftest"]


def _argv_independent(R):
    return ["--selftest"]


def _argv_backfill(R):
    return ["--selftest"]


def _argv_device_report(R):
    return [R, "--selftest"]


def _argv_selftest_counts(R):
    # 自身也纳入（否则本工具的条数自述会立即成为**新的**纯数字盲区 —— 「判据自己必须在判据里」，历史 182）；
    # `--selftest` 不调用 run_tool ⇒ 只递归一层，无环。
    return ["--selftest"]


# (工具文件名, 命令行工厂, 结束标记, README 中该条数的取值模式)
TOOLS = [
    ("regression.py", _argv_regression, "SELFTEST_END=1",
     re.compile(r"（\*\*(\d+)\*\* 例判别力实测")),
    ("final-check.py", _argv_final_check, "FINAL_CHECK_END=1",
     re.compile(r"`--selftest` = \*\*(\d+)\*\* 例合成夹具判别力实测")),
    ("independent.py", _argv_independent, "SELFTEST_END=1",
     re.compile(r"`--selftest` = \*\*(\d+)\*\* 例（合成 ctx")),
    ("backfill-c7.py", _argv_backfill, "SELFTEST_END=1",
     re.compile(r"`--selftest` = (\d+) 条合成夹具判据")),
    ("device-report.py", _argv_device_report, "SELFTEST_END=1",
     re.compile(r"`--selftest` = \*\*(\d+)\*\* 例纯函数负向自测")),
    ("selftest-counts.py", _argv_selftest_counts, "SELFTEST_END=1",
     re.compile(r"`--selftest` = \*\*(\d+)\*\* 例（两种体裁解析")),
]


def parse_counts(text):
    """解析汇总行 → (pass, fail, 原始行)。0 命中即判据失效（不得静默返回 0，历史 46/168/175）。"""
    ms = list(PAT.finditer(text))
    assert ms, "汇总行 0 命中（判据失效，历史 46/168）"
    m = ms[-1]
    a, b, c, d = m.group(1), m.group(2), m.group(3), m.group(4)
    if a is not None:
        return int(a), int(b), m.group(0).strip()
    return int(c), int(d), m.group(0).strip()


def verify_probe(text, endmark):
    """探针输出的完整性判据：结束标记必须出现（历史 240：区分完整结论与半截输出）。"""
    return endmark in text


def readme_value(text, pat):
    """README 自述条数：模式必须**恰好命中 1 次**（多命中/0 命中都判判据失效）。"""
    ms = list(pat.finditer(text))
    assert len(ms) == 1, "README 条数模式命中 %d 次（须 1，判据失效，历史 46）" % len(ms)
    return int(ms[0].group(1))


def prev_round_of(round_str):
    """上一轮轮次号（纯函数）：仅用于**取证文本里如实指认**上一轮的同项留痕文件名。"""
    return "R%d" % (int(round_str[1:]) - 1)


def patch_readme(text, pat, newval):
    """按「自述 ⇔ 汇总行」据实更正 → (新文本, 状态, 更正前值)。

    三态（历史 208/245）：值相等 → 已一致（幂等跳过）；不等且旧片段唯一 → 替换；
    模式命中数异常 → 判据失效（响亮失败，绝不静默）。
    """
    ms = list(pat.finditer(text))
    assert len(ms) == 1, "README 条数模式命中 %d 次（须 1，判据失效，历史 46）" % len(ms)
    m = ms[0]
    cur = int(m.group(1))
    if cur == newval:
        return text, "已一致", cur
    frag_old, frag_new = m.group(0), m.group(0).replace(m.group(1), str(newval), 1)
    n_old = text.count(frag_old)
    assert n_old == 1, "README 旧片段命中 %d 次（须 1，三态判据，历史 208/245）" % n_old
    out = text.replace(frag_old, frag_new)
    assert frag_old not in out and out.count(frag_new) == 1, "替换后残留检查失败（历史 208）"
    return out, "已更正", cur


def run_tool(name, argv, endmark):
    """跑一个装置工具的 `--selftest`（只读）：返回 (rc, 输出, 完整性)。"""
    p = subprocess.run([sys.executable, str(DEV / name)] + list(argv),
                       cwd=str(ROOT), capture_output=True)
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    return p.returncode, out, verify_probe(out, endmark)


def sh(*a):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(a), capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace")


# ============================ 负向自测 ============================
def selftest():
    checks = []

    def chk(name, cond, info=""):
        checks.append((name, bool(cond), info))

    # S1/S2 两种体裁各一条（只写一种 ⇒ 另一类整批 0 命中，历史 46/168）
    p1, f1, _ = parse_counts("[PASS] X\n判据：PASS 26 / FAIL 0\n")
    chk("S1 体裁一「判据：PASS N / FAIL M」解析到 (26,0)", (p1, f1) == (26, 0), "实得 (%d,%d)" % (p1, f1))
    p2, f2, _ = parse_counts("自测：26 PASS / 0 FAIL（共 26 例）\nSELFTEST_END=1\n")
    chk("S2 体裁二「自测：N PASS / M FAIL（共 N 例）」解析到 (26,0)", (p2, f2) == (26, 0), "实得 (%d,%d)" % (p2, f2))
    p3, f3, ln3 = parse_counts("[PASS] a\n判据：PASS 20 / FAIL 1\n尾注\n")
    chk("S3 取**最后**一条汇总行（前文无关行不干扰）且 FAIL 如实读出",
        (p3, f3) == (20, 1) and "判据" in ln3, "实得 (%d,%d) %r" % (p3, f3, ln3))
    raised = False
    try:
        parse_counts("[PASS] 没有任何汇总行的输出\n")
    except AssertionError:
        raised = True
    chk("S4 0 命中 ⇒ 抛错（判据失效，绝不静默返回 0，历史 175）", raised)
    raised = False
    try:
        readme_value("模式不存在的一行\n", TOOLS[0][3])
    except AssertionError:
        raised = True
    chk("S5 README 模式 0 命中 ⇒ 抛错（判据失效）", raised)

    # S6/S7 三态 + 判别力（用**合成** README 文本与合成值，不碰真仓库；历史 66/90/94：注入必须真的改到文本）
    synth = "| `regression.py <ROUND>` | … 带 `--selftest`（**23** 例判别力实测，纯函数 …） |"
    got = readme_value(synth, TOOLS[0][3])
    chk("S6 合成 README 上模式取值 == 自述值 23（非空转）", got == 23, "实得 %d" % got)
    new, state, before = patch_readme(synth, TOOLS[0][3], 26)
    chk("S7a 自述 23 ⇔ 汇总行 26 ⇒ 判「已更正」且文本真的变（注入必须真的改到，历史 66）",
        state == "已更正" and before == 23 and "**26**" in new and "**23**" not in new,
        "状态=%s 前=%d 新含 26=%s" % (state, before, "**26**" in new))
    new2, state2, _ = patch_readme(new, TOOLS[0][3], 26)
    chk("S7b 重跑同输入 ⇒ 判「已一致」（幂等，可重跑，历史 208）", state2 == "已一致" and new2 == new)
    raised = False
    try:
        patch_readme("两处 **23** 例判别力实测 与 **23** 例判别力实测\n", TOOLS[0][3], 26)
    except AssertionError:
        raised = True
    chk("S7c 模式多命中 ⇒ 抛错（不得猜哪一处才是自述）", raised)
    # S7d 判别力：把「不等」这种被测状态人为去掉（自述 = 汇总行）⇒ 必须判已一致，证明 S7a 的「已更正」
    # 不是恒真（成对断言：同一个函数在两种输入上给出不同结论）
    _, state3, _ = patch_readme("（**26** 例判别力实测）", TOOLS[0][3], 26)
    chk("S7d 成对对照：自述 == 汇总行 ⇒ 判「已一致」（S7a 的「已更正」因此非恒真）", state3 == "已一致")

    # S8 完整性判据（结束标记）双向对照
    chk("S8a 缺结束标记 ⇒ 判「半截输出」", not verify_probe("判据：PASS 26 / FAIL 0\n", "SELFTEST_END=1"))
    chk("S8b 含结束标记 ⇒ 判完整", verify_probe("判据：PASS 26 / FAIL 0\nSELFTEST_END=1\n", "SELFTEST_END=1"))

    # S9 每个工具的 README 模式都必须在**真 README** 上恰好命中 1 次（否则该工具的守卫是死的）
    rd = README.read_text(encoding="utf-8", errors="replace")
    hits = []
    for name, _f, _e, pat in TOOLS:
        hits.append((name, len(list(pat.finditer(rd)))))
    chk("S9 逐工具的 README 模式在真 README 上各命中 1 次（正向对照 > 0，历史 46/75/98）",
        all(n == 1 for _nm, n in hits), "逐工具命中 %s" % hits)

    # S10 本文件轮次无关自证（源码内不得出现形如 R+数字 的具体轮次号字面量）
    src = Path(__file__).read_text(encoding="utf-8", errors="replace")
    bad = re.findall(r'"R\d+"|\bR\d{2,}\b', src)
    chk("S10 本工具源码内零具体轮次号字面量（轮次无关，历史 201/205/217）", not bad, "命中 %s" % (bad or "无"))

    # S11 上一轮次号推导（纯函数；合成值**运行期拼接**，源码里不出现具体轮次号字面量，历史 201/206）
    d1 = "49" + "1"
    d2 = "57" + "0"
    chk("S11 上一轮次号推导（普通 / 末位为 0 的借位）",
        prev_round_of("R" + d1) == "R" + "49" + "0" and prev_round_of("R" + d2) == "R" + "56" + "9",
        "R%s -> R%s / R%s -> R%s" % (d1, "49" + "0", d2, "56" + "9"))

    ok = sum(1 for _n, c, _i in checks if c)
    for name, c, info in checks:
        print("  [%s] %s%s" % ("PASS" if c else "FAIL", name, (" " + info) if info else ""))
    print("  判据：PASS %d / FAIL %d（共 %d 例）" % (ok, len(checks) - ok, len(checks)))
    print("SELFTEST_END=1")
    return 0 if ok == len(checks) else 1


# ============================ 主流程 ============================
def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    ROUND = (args[0] if args else "").upper()
    if not re.fullmatch(r"R\d+", ROUND):
        print("用法: python tools/round-verify/selftest-counts.py <轮次> （或 --selftest）")
        return 2

    # 只读守卫：五个 `--selftest` 前后工作区必须逐行相同（装置自测不得有写副作用）
    rc0, st_before = sh("status", "--porcelain")
    assert rc0 == 0, "git status 读取失败（判据不可用）"

    rows, counts = [], {}
    for name, argvf, endmark, pat in TOOLS:
        rc, out, complete = run_tool(name, argvf(ROUND), endmark)
        if not complete:
            tail = "\n".join(out.strip().splitlines()[-6:]) or "(无输出)"
            print("[FAIL] %s 的 --selftest 输出缺结束标记 %s（半截输出，判据不可用，历史 240）\n"
                  "       子进程 argv = %s；rc=%s；输出尾 6 行（区分「半截输出」与「子进程直接崩」）：\n%s"
                  % (name, endmark, argvf(ROUND), rc, tail))
            return 2
        npass, nfail, line = parse_counts(out)
        if nfail != 0:
            print("[FAIL] %s 自测有 FAIL %d 条（装置自测必须先全绿）" % (name, nfail))
            return 2
        if npass <= 0:
            print("[FAIL] %s 自测条数 = 0（正向对照失败，历史 46/75/98）" % name)
            return 2
        counts[name] = npass
        rows.append((name, rc, endmark, line, npass))

    rc1, st_after = sh("status", "--porcelain")
    assert rc1 == 0, "git status 读取失败（判据不可用）"
    ro_ok = (st_before == st_after)

    rd = README.read_bytes()
    assert rd.count(b"\r") == 0, "README 含 CR（行尾判据，历史 69/70）"
    rtext = rd.decode("utf-8")
    prev_name = "device-selftest-counts-%s.txt" % prev_round_of(ROUND)
    prev_exists = (EV / prev_name).exists()
    fixes = []
    for name, _argvf, _endmark, pat in TOOLS:
        newtext, state, before = patch_readme(rtext, pat, counts[name])
        fixes.append((name, before, counts[name], state))
        rtext = newtext
    changed = [f for f in fixes if f[3] == "已更正"]
    if changed:
        assert rtext.count("\r") == 0
        README.write_bytes(rtext.encode("utf-8"))            # 字节级：不做行尾翻译
        back = README.read_bytes()
        assert back.count(b"\r") == 0, "写回含 CR（历史 69/84/146）"
        # 闭环复核：写回后重读 ⇒ 每个工具都必须判「已一致」（幂等，可重跑）
        bt = back.decode("utf-8")
        again = [nm for nm, _f, _e, pat in TOOLS
                 if patch_readme(bt, pat, counts[nm])[1] != "已一致"]
        assert not again, "写回后仍不自述一致：%s（判据失效）" % again
        md5 = hashlib.md5(back).hexdigest()
    else:
        # 更正 0 条 ⇒ **不写回**（README 字节未动）—— 用「运行后再读一次逐字节相等」当机器证据，
        # 而不是拿刚算出的文本自比（历史 230：断言必须可能为假）。幂等性本身由 `--selftest` 的
        # S7b（同输入重跑 ⇒ 判「已一致」）与 S7d（成对对照）覆盖，此处只证「本轮真的零写」。
        assert README.read_bytes() == rd, "README 在本工具运行期间被改动（零写守卫，判据失效）"
        md5 = hashlib.md5(rd).hexdigest()

    # ---- 证据落盘（LF / 结束标记唯一 / 行数下限 / 关键锚点） ----
    L = []
    L.append("%s 装置 README 自测条数取证（自述 ⇔ 工具汇总行；轮次无关工具 tools/round-verify/selftest-counts.py）"
             % ROUND)
    L.append("=" * 78)
    L.append("生成方式：本工具逐个执行装置工具的 `--selftest`（`sys.executable` + `cwd=仓库根`，不经 shell），")
    L.append("从**汇总行**解析条数（零手写值），再与 `tools/round-verify/README.md` 的自述值逐工具比对；")
    L.append("本文件即勘误留痕；上一轮同项留痕 %s（磁盘上存在 = %s）。" % (prev_name, prev_exists))
    L.append("")
    L.append("一、原始输出与汇总行（每项断言结束标记存在 = 完整结论，非半截输出，历史 240）")
    for name, rc, endmark, line, npass in rows:
        L.append("  %-18s rc=%d 结束标记 %-19s 汇总行「%s」→ 条数 = %d"
                 % (name, rc, endmark, line, npass))
    L.append("  正向对照：%d 项条数均 > 0（%s）；FAIL 均 = 0。" % (len(counts), sorted(counts.values())))
    L.append("")
    L.append("二、README 自述 ⇔ 汇总行（逐工具，模式须各命中 1 次；不等即据实更正，历史 201/206/12）")
    for name, before, now, state in fixes:
        verdict = "一致" if before == now else "**分叉**：自述 %d → 更正为 %d" % (before, now)
        L.append("  %-18s 自述 %d ⇔ 汇总行 %d ⇒ %s（%s）" % (name, before, now, verdict, state))
    if changed:
        L.append("  更正条数 = %d（据实更正后**已写回**，写回后重读逐工具判「已一致」＝幂等，可重跑）。" % len(changed))
    else:
        L.append("  更正条数 = 0（本轮 README 自述与工具汇总行本已一致，**未写回**：README 运行期逐字节未动）。")
    L.append("  README sha256(前 12) = %s（= 本工具运行**前**的 README 字节指纹）"
             % hashlib.sha256(rd).hexdigest()[:12])
    L.append("  README md5 = %s" % md5)
    L.append("")
    L.append("三、只读守卫（装置自测不得有写副作用）")
    L.append("  全部 %d 个 `--selftest` 运行前后 `git status --porcelain` 逐行相同 = %s（行数 %d ⇒ %d）"
             % (len(rows), ro_ok, len(st_before.splitlines()), len(st_after.splitlines())))
    if not ro_ok:
        L.append("  ⚠ 运行前后工作区**发生了变化** —— 装置自测存在写副作用（须排查）：")
        for ln in st_after.splitlines():
            if ln not in st_before.splitlines():
                L.append("      + %s" % ln)
        for ln in st_before.splitlines():
            if ln not in st_after.splitlines():
                L.append("      - %s" % ln)
    L.append("")
    L.append("四、为什么值得常驻")
    L.append("  装置 README 的条数是**纯数字自述**：机械轮次替换（只认轮次号形态）与 84 条回归面（只跑工具不读文档）")
    L.append("  都碰不到它 ⇒ 手工维护必然过期，而六个装置步骤全程零报警。本工具把「每轮核对 + 据实更正 + 幂等复核」")
    L.append("  固化成轮次无关实现，取代此前只活在 $TEMP 的 aux 脚本（历史 169/177/216：系统清理即永久退场）。")
    L.append(END_MARK)
    text = "\n".join(L) + "\n"
    assert text.count(END_MARK) == 1, "结束标记不唯一（历史 222）"
    out = EV / ("device-selftest-counts-%s.txt" % ROUND)
    out.write_text(text, encoding="utf-8", newline="\n")
    rb = out.read_bytes()
    assert rb.count(b"\r") == 0, "证据落盘含 CR（历史 69/84/146）"
    got = rb.decode("utf-8")
    need = [ROUND, "正向对照", "只读守卫", END_MARK]
    miss = [x for x in need if x not in got]
    assert not miss, "落盘缺关键锚点：%s" % miss
    nlines = len(got.splitlines())
    assert nlines >= 24, "落盘行数 %d 过少（内容级下限，历史 200）" % nlines
    if not ro_ok:
        print("[FAIL] 只读守卫失败：装置 `--selftest` 存在写副作用（证据已落盘供排查）")
        return 2
    print("自测条数（由各工具汇总行解析）= %s" % counts)
    print("README 更正 = %s" % ([f[0] for f in changed] or "无（本已一致）"))
    print("只读守卫（运行前后 git status 逐行相同）= %s" % ro_ok)
    print("证据：%s（%d 行 / CR=0 / 结束标记唯一）" % (out.name, nlines))
    print("SELFTEST_COUNTS_WROTE=%s" % out.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
