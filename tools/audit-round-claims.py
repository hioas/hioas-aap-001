#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轮次自述真值一致性审计（只读，零写副作用）。

为什么两套门禁都看不见：
  * 覆盖门禁/契约测试只读「交付代码 + 测试源 + JSON Schema」，取证台账与状态文件的**散文自述**不在任何测试的读取面内；
  * 因此「同一件事实在同一轮里被写成两个不同的数字」（例：一处写 `本轮返工真值 = 4 处`、另一处写 `权威数字 = 返工 3 处`）
    对全量用例完全不可见 —— 这正是历史 215/217-③/250 的「同一事实两种写法」缺陷类。

判据（全部锚定**自述形态**，不扫裸子串 —— 历史 202/204/226）：
  A 形态（本轮自述）  = `本轮返工真值 = N 处`
  B 形态（权威声明）  = `权威数字 = 返工 N 处`（允许前缀如「更正后」）
  * 历史引用（如 `所记「返工 2 处」`、`由「2 处」更正为`）不匹配 A/B，天然豁免；
  * 归属：状态文件按**段标题**（`## RNNN` / `【(收尾 |更正 )?RNNN` …）归属，**绝不**按「行内最后一个 R 号」
    （真实陷阱：收尾行正文会引用更早轮次的 R 号，按行内最后 R 号归属会把 R359 段判成 R357）。

断言：A1 同轮 A 与 B 必须相等；A2 同轮「状态文件 B」与「台账描述列 B」必须相等；
      A0* 各源解析条数 > 0（正向对照，历史 46/75/98）；A4 归属锚点反向对照（合成行）。
用法：python tools/audit-round-claims.py [--root <dir>] [--selftest]
退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 解析器不可用（判据失效）
"""
import argparse, csv, hashlib, re, sys
from pathlib import Path

RE_A = re.compile(r"本轮返工真值\s*=\s*\**\s*(\d+)\s*处")
RE_B = re.compile(r"权威数字\s*=\s*返工\s*(\d+)\s*处")
# 段标题：`## R360 …` / `### R360（…）` / `【收尾 R360（据实）】` / `【更正 R360】` / `【R360 …】`
RE_HEAD = re.compile(r"(?:^#{2,4}\s*R(\d{2,3})\b)|(?:【\s*(?:收尾\s*|更正\s*)?R(\d{2,3})[^】]*】)")
RE_ROWID = re.compile(r"^R(\d{2,3})$")

OUT = []
def say(s=""):
    OUT.append(s); print(s)

def parse_state(text):
    """返回 (A 形态列表[(round,val,line)], B 形态列表[(round,val,line)], 段数)"""
    a, b, segs = [], [], set()
    cur = None
    for i, ln in enumerate(text.splitlines(), 1):
        m = RE_HEAD.search(ln)
        if m:
            cur = "R" + (m.group(1) or m.group(2))
            segs.add(cur)
        for mm in RE_A.finditer(ln):
            a.append((cur, int(mm.group(1)), i))
        for mm in RE_B.finditer(ln):
            b.append((cur, int(mm.group(1)), i))
    return a, b, segs

def parse_csv(text):
    rows = list(csv.reader(text.splitlines()))
    hdr = rows[0] if rows else []
    b = []
    for r in rows[1:]:
        if not r or not RE_ROWID.match(r[0].strip()):
            continue
        blob = " | ".join(r)
        for mm in RE_B.finditer(blob):
            b.append(("R" + RE_ROWID.match(r[0].strip()).group(1), int(mm.group(1)), 0))
    return hdr, b

def audit(root):
    state_p = root / ".agents/state/aap-server-tdd-state.md"
    csv_p = root / ".agents/state/aap-server-feature-status.csv"
    fails, passes = [], []
    def chk(cond, name, detail=""):
        (passes if cond else fails).append("%s %s%s" % ("[PASS]" if cond else "[FAIL]", name, (" | " + detail) if detail else ""))
        return cond
    if not state_p.exists() or not csv_p.exists():
        say("[FAIL] A0x 数据源缺失 state=%s csv=%s" % (state_p.exists(), csv_p.exists()))
        return 2, ["A0x"], []
    st = state_p.read_text(encoding="utf-8")
    cv = csv_p.read_text(encoding="utf-8")
    sa, sb, segs = parse_state(st)
    hdr, cb = parse_csv(cv)

    # A0* 是「判据可用性」正向对照：任一为假 -> 判据失效（rc=2），不是「合规」（历史 46/75/98/141）
    usable = True
    usable &= chk(len(sa) > 0, "A0a 状态文件 A 形态（本轮自述）解析到 > 0 条", "n=%d" % len(sa))
    usable &= chk(len(sb) > 0, "A0b 状态文件 B 形态（权威声明）解析到 > 0 条", "n=%d" % len(sb))
    usable &= chk(len(cb) > 0, "A0c 台账描述列 B 形态解析到 > 0 条", "n=%d" % len(cb))
    usable &= chk(len(segs) > 0, "A0d 状态文件段标题归属锚点解析到 > 0 段", "n=%d" % len(segs))
    usable &= chk(len(hdr) == 8, "A0e 台账表头列数 = 8", "cols=%d" % len(hdr))

    say("  · 状态文件 A 形态：%d 条" % len(sa))
    for r, v, i in sa:
        say("      round=%s val=%d line=%d" % (r, v, i))
    say("  · 状态文件 B 形态：%d 条" % len(sb))
    for r, v, i in sb:
        say("      round=%s val=%d line=%d" % (r, v, i))
    say("  · 台账 B 形态：%d 条" % len(cb))

    # A1 同轮 A 与 B 必须相等
    sbm = {}
    for r, v, i in sb:
        sbm.setdefault(r, set()).add(v)
    sam = {}
    for r, v, i in sa:
        sam.setdefault(r, set()).add(v)
    cmp_rounds = sorted(set(sam) & set(sbm))
    chk(len(cmp_rounds) > 0, "A3 可做「A↔B 同轮比对」的轮次数 > 0", "n=%d %s" % (len(cmp_rounds), cmp_rounds))
    bad1 = [(r, sorted(sam[r]), sorted(sbm[r])) for r in cmp_rounds if sam[r] != sbm[r]]
    chk(not bad1, "A1 同轮「本轮自述」与「权威数字」相等",
        "违规 %d: %s" % (len(bad1), "; ".join("%s A=%s B=%s" % t for t in bad1)))

    # A2 同轮 状态文件 B 与 台账 B 必须相等
    cbm = {}
    for r, v, i in cb:
        cbm.setdefault(r, set()).add(v)
    cmp2 = sorted(set(sbm) & set(cbm))
    chk(len(cmp2) > 0, "A3b 可做「跨文件（状态↔台账）比对」的轮次数 > 0", "n=%d %s" % (len(cmp2), cmp2))
    bad2 = [(r, sorted(sbm[r]), sorted(cbm[r])) for r in cmp2 if sbm[r] != cbm[r]]
    chk(not bad2, "A2 同轮「状态文件权威数字」与「台账描述列权威数字」相等",
        "违规 %d: %s" % (len(bad2), "; ".join("%s state=%s csv=%s" % t for t in bad2)))

    # A4 归属锚点反向对照：段内引用更早/更晚轮次号不得改变归属
    synth = ("【收尾 R360（据实）】本轮返工真值 = **4 处**（与 R359 的「收尾期才暴露」同族）。"
             "权威数字 = 返工 3 处；权威文本 = 台账描述列。")
    sa2, sb2, _ = parse_state(synth)
    chk([x[0] for x in sa2] == ["R360"] and [x[0] for x in sb2] == ["R360"],
        "A4 归属锚点=段标题（段内引用他轮 R 号不得改变归属）",
        "A=%s B=%s" % ([x[0] for x in sa2], [x[0] for x in sb2]))
    chk(len(sa2) == 1 and len(sb2) == 1, "A4b 合成行两形态各恰 1 条", "A=%d B=%d" % (len(sa2), len(sb2)))
    if not usable:
        return 2, fails, passes
    return (1 if fails else 0), fails, passes

def selftest(root):
    """负向自测：每个判定分支一条反例 + 正向对照 + 归属反例 + 零写副作用。"""
    import tempfile
    base = Path(tempfile.gettempdir()) / "aap-r360-claims-fixtures"
    repo = Path(__file__).resolve().parents[1]
    if str(base).lower().startswith(str(repo).lower().replace("/", "\\").lower()):
        print("[FAIL] S0 夹具目录落在仓库内（会污染被测对象）：%s" % base)
        return 1
    print("[PASS] S0 夹具目录在仓库外（历史 106：脚本与夹具分目录）| base=%s" % base)
    W = base
    W.mkdir(parents=True, exist_ok=True)
    (W / ".agents/state").mkdir(parents=True, exist_ok=True)
    state_p = W / ".agents/state/aap-server-tdd-state.md"
    csv_p = W / ".agents/state/aap-server-feature-status.csv"
    HDR = "任务号,接口ID,方法,路径,依据,状态,证据,提交\n"

    def fixture(state_body, csv_rows):
        state_p.write_text(state_body, encoding="utf-8", newline="\n")
        csv_p.write_text(HDR + "".join(csv_rows), encoding="utf-8", newline="\n")
        return audit(W)

    def md5(p):
        return hashlib.md5(p.read_bytes()).hexdigest()

    good_state = ("## R360 段\n本轮返工真值 = **4 处**（判据侧）。\n\n"
                  "## R359 段\n【收尾 R360（据实）】权威数字 = 返工 4 处；权威文本 = 台账描述列。\n")
    good_csv = ["R360,,,,desc,,\"权威数字 = 返工 4 处\",abc\n"]
    fails = []
    def expect(name, got, want_rc, must_have=(), must_not_have=()):
        okrc = (got[0] == want_rc)
        blob = "\n".join(got[1])
        okh = all(s in blob for s in must_have)
        okn = all(s not in blob for s in must_not_have)
        # 「不应出现」判据必须带 '[FAIL] ' 前缀（历史 77）
        okh = all(s in blob for s in must_have)
        res = okrc and okh and okn
        print("[%s] SELFTEST %s rc=%s(期望 %s) have=%s nothave=%s" % (
            "PASS" if res else "FAIL", name, got[0], want_rc,
            [s for s in must_have if s in blob] == list(must_have),
            [s for s in must_not_have if s in blob] == []))
        if not res:
            fails.append(name)

    # S1 合规夹具 -> 0 FAIL：同轮同时承载 A（本轮自述）与 B（权威数字）且值相等
    ok_state = ("## R360 段\n本轮返工真值 = **4 处**（判据侧）。\n\n"
                "【收尾 R360（据实）】权威数字 = 返工 4 处；权威文本 = 台账描述列。\n")
    ok_csv = ["R360,,,,desc,,\"权威数字 = 返工 4 处\",abc\n"]
    expect("S1 合规夹具 -> rc=0 且无 A1/A2 违规", fixture(ok_state, ok_csv), 0, (), ["[FAIL]"])

    # S2 注入「同轮 A≠B」（旧值 4，新值 3；与旧值无子串包含关系 -> 历史 90/94）
    mut_state = ok_state.replace("权威数字 = 返工 4 处", "权威数字 = 返工 3 处")
    if mut_state == ok_state:
        fails.append("S2 注入未命中锚点（坑 66）")
    got = fixture(mut_state, ok_csv)
    expect("S2 同轮 A≠B -> 恰好点名 A1 违规", got, 1, ("[FAIL] A1", "R360 A=[4] B=[3]"), ())

    # S3 注入「跨文件 B≠B」（台账侧改 5）
    mut_csv = ["R360,,,,desc,,\"权威数字 = 返工 5 处\",abc\n"]
    got = fixture(ok_state, mut_csv)
    expect("S3 跨文件 state=4 / csv=5 -> 恰好点名 A2 违规", got, 1, ("[FAIL] A2", "R360 state=[4] csv=[5]"), ("[FAIL] A1",))

    # S4 空夹具 -> 必须变红（判据不可用），且点名 A0a/A0b/A0c
    got = fixture("", [])
    expect("S4 空夹具 -> 判据不可用（点名 A0a/A0b/A0c）", got, 2, ("[FAIL] A0a", "[FAIL] A0b", "[FAIL] A0c"), ())

    # S5 归属反例：段内引用更早轮次号 -> 归属仍为段标题轮次，不得假 FAIL
    state5 = ("## R360 段\n【收尾 R360（据实）】本轮返工真值 = **4 处**（与 R359 的「收尾期才暴露」同族）。\n"
              "权威数字 = 返工 4 处；权威文本 = 台账描述列。\n")
    got = fixture(state5, ok_csv)
    expect("S5 归属反例（段内引用 R359）-> rc=0", got, 0, (), ["[FAIL]"])

    # S6 零写副作用：审计本体（非夹具构造）不得改动被读文件（历史 39：mtime 变了而 md5 没变也算写副作用）
    fixture(ok_state, ok_csv)
    def fp(p):
        stt = p.stat()
        return (stt.st_mtime_ns, stt.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    b = (fp(state_p), fp(csv_p))
    audit(W); audit(W)
    a = (fp(state_p), fp(csv_p))
    ok6 = (a == b)
    print("[%s] SELFTEST S6 审计本体零写副作用（两文件 mtime/size/md5 前后全等）" % ("PASS" if ok6 else "FAIL"))
    if not ok6:
        fails.append("S6")
    print("[PASS] SELFTEST 夹具目录 = %s" % W)
    print("SELFTEST_FAILS = %d %s" % (len(fails), fails))
    return 0 if not fails else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    print("=" * 78)
    print("轮次自述真值一致性审计（数值形态：本轮自述 A ⇔ 权威数字 B；同轮 A==B ∧ 跨文件 B==B）")
    print("ROOT = %s | SELFTEST = %s" % (root, a.selftest))
    print("=" * 78)
    if a.selftest:
        rc = selftest(root)
        print("SELFTEST_RC = %d" % rc)
        return rc
    rc, fails, passes = audit(root)
    for x in fails + passes:
        say(x)
    say("判据：PASS %d / FAIL %d / rc=%d" % (len(passes), len(fails), rc))
    return rc

if __name__ == "__main__":
    sys.exit(main())
