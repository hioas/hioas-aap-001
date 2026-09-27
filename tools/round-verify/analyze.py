#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验轮分析器（**轮次无关**：`python tools/round-verify/analyze.py R490`）。

全部读数从 facts / run{1,2}.raw / wt-arch / coverage-report.json 解析，**零手写值**。

判据纪律（逐条都来自本仓历史返工）：
  * 每个解析器配 > 0 正向对照（0 命中先怀疑判据，历史 46/75/98）；
  * surefire 合计行必须**双前缀**（[INFO]/[ERROR]，历史 228）；类级行剥 Time elapsed 再排序（历史 59/79）；
  * `@Test` 用词边界计数并与 surefire 对账（历史 35/172）；禁用扫描必须 0 条；
  * 覆盖率按族相加 == total（历史 200 的内容级断言）；
  * 窗口/HEAD/轮次等纯值只从 facts 读，源码内零硬编码（历史 243-③）。
只写 .agents/state/evidence/ 下的证据文件；不写任何交付面文件。
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
T = Path("C:/Users/laitz/AppData/Local/Temp")

ROUND = (sys.argv[1] if len(sys.argv) > 1 else "").upper()
if not re.fullmatch(r"R\d+", ROUND):
    print("用法: python tools/round-verify/analyze.py R490")
    sys.exit(2)
PREV = "R%d" % (int(ROUND[1:]) - 1)
# --evidence-dir：把产物写到别处（回放预检 / 判别力实测用），输入仍读仓库内证据目录。
OUTDIR = EV
if "--evidence-dir" in sys.argv:
    OUTDIR = Path(sys.argv[sys.argv.index("--evidence-dir") + 1])
    OUTDIR.mkdir(parents=True, exist_ok=True)
W = T / "aap-round-verify" / ROUND
FACTSF = W / ("facts-%s.log" % ROUND)
HDR = ("%s 校验轮（missing==0 -> 交付代码零改动）；"
       "全部读数由 tools/round-verify/analyze.py 从 facts / run{1,2}.raw / wt-arch 解析，无手写值" % ROUND)

out = []
verdicts = []


def p(s=""):
    out.append(s)
    print(s)


def rec(name, cond, detail=""):
    verdicts.append((name, bool(cond), detail))
    p("[%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))
    return bool(cond)


def g1(text, pat, label, group=1, flags=0):
    m = re.search(pat, text, flags)
    if not m:
        raise SystemExit("[FAIL] 解析器失效（0 命中，历史 46）：%s :: %s" % (label, pat))
    if group > m.re.groups:
        raise SystemExit("[FAIL] 捕获组号越界（历史 237）：%s 请求第 %d 组、模式只有 %d 组"
                         % (label, group, m.re.groups))
    return m.group(group)


if not FACTSF.exists():
    print("[FAIL] facts 文件缺失（判据不可用，历史 128/141）：%s" % FACTSF)
    sys.exit(3)
facts_txt = FACTSF.read_text(encoding="utf-8", errors="replace")
FACTS = {}
for ln in facts_txt.splitlines():
    if "=" in ln:
        k, v = ln.split("=", 1)
        FACTS[k.strip()] = v.strip()
REQ = ["ENV_BASH", "ENV_UNAME", "ENV_MVN", "ENV_JAVA", "ENV_JPS", "FACTS_ROUND",
       "FACTS_WINDOW_START", "FACTS_WINDOW_START_TS", "FACTS_WINDOW_START_ISO",
       "FACTS_HEAD_AT_START", "FACTS_HEAD_AT_START_FULL", "PREFLIGHT_CONTROL_POS_MATCH",
       "PREFLIGHT_CONTROL_NEG_MATCH", "PREFLIGHT_RESULT", "PREFLIGHT_OK", "ROOT_STATUS_LINES_BEFORE",
       "WORKTREE_ADD_RC", "WORKTREE_PATH", "FACTS_TESTED_COMMIT", "FACTS_TESTED_COMMIT_FULL",
       "FACTS_TESTED_SUBJECT", "WT_DIRTY_LINES", "FACTS_RUN1_START", "FACTS_RUN1_END", "FACTS_RUN1_RC",
       "FACTS_RUN2_START", "FACTS_RUN2_END", "FACTS_RUN2_RC", "ARCH_TEST_FILES",
       "WORKTREE_REMOVE_RC", "FACTS_WINDOW_END", "FACTS_WINDOW_END_TS", "FACTS_WINDOW_END_ISO",
       "FACTS_HEAD_AT_END", "FACTS_HEAD_ADVANCED_COUNT", "FACTS_WRITTEN"]
MISSK = [k for k in REQ if k not in FACTS]
p(HDR)
p("=" * 78)

# ---------- ① 事实键齐备 + 轮次 ----------
rec("A0a facts 必填键齐备", not MISSK, "缺失 = %s（要求 %d 键）" % (MISSK or "无", len(REQ)))
rec("A0b facts 轮次 == %s" % ROUND, FACTS.get("FACTS_ROUND") == ROUND, "读到 %r" % FACTS.get("FACTS_ROUND"))


def sure(r):
    txt = (W / ("run%d.raw" % r)).read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()
    tot = re.findall(r"^\[(?:INFO|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)$",
                     txt, flags=re.M)
    cls = re.findall(r"^\[(?:INFO|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+), "
                     r"Time elapsed: [^-]*-- in ([\w.$]+)\s*$", txt, flags=re.M)
    if not tot:
        raise SystemExit("[FAIL] run%d 合计行解析到 0 条（判据失效，历史 46/228）" % r)
    if not cls:
        raise SystemExit("[FAIL] run%d 类级行解析到 0 条（判据失效，历史 46）" % r)
    # 判据：类名必须真的**区分得开**（t[4] 是第 5 个捕获组 = 全限定类名；
    # 历史返工：曾写成 `t[4][1]` ⇒ 只取类名第 2 个字符，跨轮「逐类 diff」因此丢掉类维度 = 空转假绿，历史 46/98）
    names = [t[4] for t in cls]
    if len(set(names)) != len(names):
        raise SystemExit("[FAIL] run%d 类名不可区分：%d 行 / 唯一 %d 个（判据失效，历史 98）"
                         % (r, len(names), len(set(names))))
    if not all(("." in n and len(n) > 10) for n in names):
        raise SystemExit("[FAIL] run%d 类名形态异常（应形如 com.hioas.…）：样本 = %r" % (r, names[:2]))
    key = sorted("tests=%s,fail=%s,err=%s,sk=%s,class=%s" % (t[0], t[1], t[2], t[3], t[4]) for t in cls)
    return {"rc": int(FACTS["FACTS_RUN%d_RC" % r]), "tot": tot[0], "n": int(tot[0][0]),
            "cls": cls, "key": key, "lines": len(lines), "unames": len(set(names)),
            "name_min": min(len(n) for n in names), "name_max": max(len(n) for n in names),
            "build_ok": "BUILD SUCCESS" in txt, "build_bad": "BUILD FAILURE" in txt}


def maven_time(txt):
    m = re.search(r"^\[INFO\] Total time:\s+(\d+):(\d+) min\s*$", txt, flags=re.M)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2)), "mm:ss min"
    m2 = re.search(r"^\[INFO\] Total time:\s+([\d.]+) s\s*$", txt, flags=re.M)
    if m2:
        return int(float(m2.group(1))), "s"
    return None, "(未解析到)"


R1, R2 = sure(1), sure(2)
t1, k1 = maven_time((W / "run1.raw").read_text(encoding="utf-8", errors="replace"))
t2, k2 = maven_time((W / "run2.raw").read_text(encoding="utf-8", errors="replace"))

# ---------- ② 两轮全绿 ----------
rec("A1 run1/run2 rc 均为 0", R1["rc"] == 0 and R2["rc"] == 0, "rc=%d/%d" % (R1["rc"], R2["rc"]))
rec("A2 两轮合计行五元组一致且全 0 失败",
    R1["tot"] == R2["tot"] and R1["tot"][1:] == ("0", "0", "0"),
    "run1=%s run2=%s" % (R1["tot"], R2["tot"]))
rec("A3 BUILD SUCCESS 两轮均为真", R1["build_ok"] and R2["build_ok"] and not R1["build_bad"] and not R2["build_bad"],
    "run1 SUCCESS=%s FAILURE=%s / run2 SUCCESS=%s FAILURE=%s" % (R1["build_ok"], R1["build_bad"], R2["build_ok"], R2["build_bad"]))
rec("A4 逐类结果（已剥 Time elapsed 再排序）两轮一致",
    R1["key"] == R2["key"], "逐类行数 %d / %d；diff = %d" % (len(R1["key"]), len(R2["key"]), len(set(R1["key"]) ^ set(R2["key"]))))
rec("A5 串行（run1_end <= run2_start）",
    FACTS["FACTS_RUN1_END"] <= FACTS["FACTS_RUN2_START"],
    "%s -> %s / %s -> %s" % (FACTS["FACTS_RUN1_START"], FACTS["FACTS_RUN1_END"], FACTS["FACTS_RUN2_START"], FACTS["FACTS_RUN2_END"]))
rec("A6 maven 耗时双写法解析器有牙齿（两形态各 1 条合成对照）",
    maven_time("[INFO] Total time:  01:00 min")[0] == 60 and maven_time("[INFO] Total time:  58.698 s")[0] == 58,
    "本轮实际形态 run1=%s(%s) run2=%s(%s)" % (t1, k1, t2, k2))
rec("A7 类级行数 > 0（正向对照）", len(R1["cls"]) > 0, "%d 类" % len(R1["cls"]))
rec("A8 类级行数与合计口径一致（类级 tests 相加 == 合计）",
    sum(int(t[0]) for t in R1["cls"]) == R1["n"] and sum(int(t[0]) for t in R2["cls"]) == R2["n"],
    "run1 类级和=%d / 合计=%d；run2 类级和=%d / 合计=%d"
    % (sum(int(t[0]) for t in R1["cls"]), R1["n"], sum(int(t[0]) for t in R2["cls"]), R2["n"]))

# ---------- ③ @Test 对账 + 禁用扫描 ----------
SRC = W / "wt-arch" / "testsrc"
tests = sorted(SRC.rglob("*.java"))
jun = sum(len(re.findall(r"@Test\b", q.read_text(encoding="utf-8", errors="replace"))) for q in tests)
jun_sub = sum(len(re.findall(r"@Test", q.read_text(encoding="utf-8", errors="replace"))) for q in tests)
DIS = ("@Disabled", r"@Ignore\b", "@DisabledIf", "assumeTrue", "Assumptions.")
dis_hits = []
for q in tests:
    tx = q.read_text(encoding="utf-8", errors="replace")
    for k in DIS:
        if re.search(k, tx):
            dis_hits.append("%s:%s" % (q.name, k))
rec("A9 归档测试源非空", len(tests) > 0, "%d 个 .java（facts 声明 %s）" % (len(tests), FACTS["ARCH_TEST_FILES"]))
rec("A10 @Test 词边界计数 == surefire 合计", jun == R1["n"], "@Test=%d vs surefire=%d（裸子串 %d 作对照，差 %d）"
    % (jun, R1["n"], jun_sub, jun_sub - jun))
rec("A11 禁用扫描 0 条（不得削弱测试）", not dis_hits, "命中 = %s" % (dis_hits or "无"))

# ---------- ④ 覆盖 ----------
cov = json.loads((W / "wt-arch" / "coverage-report.json").read_text(encoding="utf-8"))
bt = cov.get("by_task", {})
sum_bt = sum(v.get("total", 0) for v in bt.values())
sum_bt_impl = sum(v.get("implemented", 0) for v in bt.values())
fam = " · ".join("%s %d/%d" % (k if k else "(空任务号)", v["implemented"], v["total"])
                 for k, v in sorted(bt.items(), key=lambda kv: kv[0]))
rec("A12 覆盖 total/implemented/missing == %s/%s/0"
    % (cov.get("total"), cov.get("implemented")),
    cov.get("missing") == 0 and cov.get("total") == cov.get("implemented"),
    "total=%s implemented=%s missing=%s" % (cov.get("total"), cov.get("implemented"), cov.get("missing")))
rec("A13 按族相加 == total（内容级）", sum_bt == cov.get("total") and sum_bt_impl == cov.get("implemented"),
    "族和 = %d/%d（族数 %d）" % (sum_bt_impl, sum_bt, len(bt)))
rec("A14 registered_routes / not_registered",
    bool(cov.get("registered_routes")) and cov.get("not_registered") == [],
    "registered_routes=%s not_registered=%s" % (cov.get("registered_routes"), cov.get("not_registered")))

# ---------- ⑤ 被测状态 / 窗口 / 在途改动 ----------
p("---- 被测状态与窗口 ----")
rec("A15 worktree 与 HEAD 差异行数 == 0", FACTS["WT_DIRTY_LINES"] == "0", "WT_DIRTY_LINES=%s" % FACTS["WT_DIRTY_LINES"])
rec("A16 worktree 检出提交 == 窗口起点 HEAD",
    FACTS["FACTS_TESTED_COMMIT"] == FACTS["FACTS_HEAD_AT_START"],
    "tested=%s head_start=%s" % (FACTS["FACTS_TESTED_COMMIT"], FACTS["FACTS_HEAD_AT_START"]))
rec("A17 窗口内他方推进提交数", True, "FACTS_HEAD_ADVANCED_COUNT=%s（head_end=%s）"
    % (FACTS["FACTS_HEAD_ADVANCED_COUNT"], FACTS["FACTS_HEAD_AT_END"]))
rec("A18 并发前置双向对照",
    FACTS["PREFLIGHT_CONTROL_POS_MATCH"] == "2/2" and FACTS["PREFLIGHT_CONTROL_NEG_MATCH"].startswith("0/2")
    and FACTS["PREFLIGHT_RESULT"] == "CLEAR" and FACTS["PREFLIGHT_OK"] == "1",
    "pos=%s neg=%s result=%s" % (FACTS["PREFLIGHT_CONTROL_POS_MATCH"], FACTS["PREFLIGHT_CONTROL_NEG_MATCH"], FACTS["PREFLIGHT_RESULT"]))
rec("A19 环境指纹齐备", all(FACTS.get(k) for k in ("ENV_BASH", "ENV_UNAME", "ENV_MVN", "ENV_JAVA", "ENV_JPS")),
    "bash=%s uname=%s mvn=%s java=%s jps_reach=%s" % (FACTS["ENV_BASH"], FACTS["ENV_UNAME"], FACTS["ENV_MVN"], FACTS["ENV_JAVA"], FACTS["ENV_JPS_REACHABLE"]))
rec("A20 worktree add/remove rc == 0", FACTS["WORKTREE_ADD_RC"] == "0" and FACTS["WORKTREE_REMOVE_RC"] == "0",
    "add=%s remove=%s" % (FACTS["WORKTREE_ADD_RC"], FACTS["WORKTREE_REMOVE_RC"]))
rec("A21 facts 写入完成标记 == 1", FACTS["FACTS_WRITTEN"] == "1", "FACTS_WRITTEN=%s" % FACTS["FACTS_WRITTEN"])

# ---------- ⑥ 覆盖率"连续轮次"由上一轮 history 行推导 ----------
hist_lines = (EV / "coverage-history.txt").read_text(encoding="utf-8", errors="replace").splitlines()
prev_line = [ln for ln in hist_lines if (" %s " % PREV) in ln]
rec("A22 上一轮 history 行恰好 1 条", len(prev_line) == 1, "命中 %d 条" % len(prev_line))
st_prev = g1(prev_line[0] if prev_line else "", r"连续第 (\d+) 轮", "上一轮连续轮数")
STREAK = int(st_prev) + 1
p("连续全绿 = 第 %d 轮（由上一轮 history 行推导：prev=%s 记 %s）" % (STREAK, PREV, st_prev))

# ---------- ⑦ 在途改动（只登记，不触碰） ----------
inflight = [x for x in (W / "root-status-before.txt").read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
ws, we = int(FACTS["FACTS_WINDOW_START_TS"]), int(FACTS["FACTS_WINDOW_END_TS"])
inwin = []
p("主体仓库在途改动（只登记、不触碰）= %d 条" % len(inflight))
for ln in inflight:
    rel = ln[3:].strip().rstrip("/")
    q = ROOT / rel
    mt = datetime.fromtimestamp(q.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if q.exists() else "(不存在)"
    p("   %-70s mtime=%s" % (ln[:70], mt))
    if q.exists() and ws <= int(q.stat().st_mtime) <= we:
        inwin.append(rel)
rec("A23 在途改动中 mtime 落在本轮窗口内的条数", True, "%d 条 %s" % (len(inwin), inwin or "（无）"))

# ---------- ⑧ 落盘 ----------
p("=" * 78)
np_ = sum(1 for _, ok, _ in verdicts if ok)
nf_ = len(verdicts) - np_
p("判据：PASS %d / FAIL %d" % (np_, nf_))


def wr(name, text):
    (OUTDIR / name).write_text(text + "\n", encoding="utf-8", newline="\n")
    return name


wr("round-%s-analysis.txt" % ROUND, "\n".join(out))
wr("green-verify-%s-tested-state.txt" % ROUND, "\n".join([
    HDR, "=" * 78,
    "被测状态（worktree 实际检出） = %s" % FACTS["FACTS_TESTED_COMMIT"],
    "被测提交全 SHA = %s" % FACTS["FACTS_TESTED_COMMIT_FULL"],
    "被测提交主题 = %s" % FACTS["FACTS_TESTED_SUBJECT"],
    "run1 = %s -> %s rc=%s / run2 = %s -> %s rc=%s（串行：run1_end <= run2_start = %s）"
    % (FACTS["FACTS_RUN1_START"], FACTS["FACTS_RUN1_END"], FACTS["FACTS_RUN1_RC"],
       FACTS["FACTS_RUN2_START"], FACTS["FACTS_RUN2_END"], FACTS["FACTS_RUN2_RC"],
       FACTS["FACTS_RUN1_END"] <= FACTS["FACTS_RUN2_START"]),
    "窗口 = %s -> %s（%s -> %s，由执行器落盘、消费方只读，历史 243-3）"
    % (FACTS["FACTS_WINDOW_START"], FACTS["FACTS_WINDOW_END"], FACTS["FACTS_WINDOW_START_TS"], FACTS["FACTS_WINDOW_END_TS"]),
    "HEAD 起点 = %s / 终点 = %s；窗口内他方推进提交数 = %s"
    % (FACTS["FACTS_HEAD_AT_START"], FACTS["FACTS_HEAD_AT_END"], FACTS["FACTS_HEAD_ADVANCED_COUNT"]),
    "worktree 与 HEAD 差异行数 = %s（0 才说明两轮跑的是提交态）" % FACTS["WT_DIRTY_LINES"],
    "主体仓库在途改动（只登记、不触碰）= %d 条" % len(inflight),
] + ["   %s" % ln for ln in inflight] + [
    "窗口内（按 mtime 读于分析时刻）落在窗口的条数 = %d %s" % (len(inwin), inwin or "（无）"),
    "环境指纹：bash=%s uname=%s mvn=%s java=%s jps=%s（可达=%s）"
    % (FACTS["ENV_BASH"], FACTS["ENV_UNAME"], FACTS["ENV_MVN"], FACTS["ENV_JAVA"], FACTS["ENV_JPS"], FACTS["ENV_JPS_REACHABLE"]),
]))
wr("green-verify-%s-testcount.txt" % ROUND, "\n".join([
    HDR, "=" * 78,
    "run1 合计 = %s" % (R1["tot"],), "run2 合计 = %s" % (R2["tot"],),
    "@Test 词边界计数 = %d（子串计数 = %d 作对照，差 = %d）" % (jun, jun_sub, jun_sub - jun),
    "surefire 合计 = %d" % R1["n"],
    "对齐 = %s" % ("一致" if jun == R1["n"] else "不一致"),
    "归档测试源码文件数 = %d；禁用扫描 = %d 条" % (len(tests), len(dis_hits)),
    "逐类结果行数 run1 = %d / run2 = %d；逐类 diff = %d"
    % (len(R1["key"]), len(R2["key"]), len(set(R1["key"]) ^ set(R2["key"]))),
]))
for r, RR in ((1, R1), (2, R2)):
    assert RR["unames"] == len(RR["cls"]), \
        "[FAIL] run%d 类名不可区分：%d 行 / 唯一 %d（判据失效，历史 98；落盘前拦下）" % (r, len(RR["cls"]), RR["unames"])
    assert len(RR["cls"]) > 0, "[FAIL] run%d 逐类行数 0 —— 解析器失效（历史 46）" % r
    wr("green-verify-%s-full-run%d.txt" % (ROUND, r), "\n".join([
        HDR, "=" * 78,
        "run%d 合计 = %s" % (r, RR["tot"]),
        "BUILD SUCCESS = %s / BUILD FAILURE = %s（maven 耗时 = %02d:%02d min，形态=%s；rc = %d）"
        % (RR["build_ok"], RR["build_bad"], (t1 if r == 1 else t2) // 60, (t1 if r == 1 else t2) % 60,
           (k1 if r == 1 else k2), RR["rc"]),
        "原始日志行数 = %d" % RR["lines"],
        "类名唯一数 = %d / 行数 = %d（须相等；类名字符数区间 = %d–%d —— 类维度必须真的能区分，历史 98）"
        % (RR["unames"], len(RR["cls"]), RR["name_min"], RR["name_max"]),
        "逐类结果（已剥 Time elapsed，排序后）共 %d 行：" % len(RR["cls"]),
    ] + ["  %s" % k for k in RR["key"]]))
wr("green-verify-%s-coverage-fields.txt" % ROUND, "\n".join([
    HDR, "=" * 78,
    "total=%s implemented=%s missing=%s registered_routes=%s not_registered=%s"
    % (cov.get("total"), cov.get("implemented"), cov.get("missing"), cov.get("registered_routes"), cov.get("not_registered")),
    "按族分布：%s" % fam,
    "连续全绿 = 第 %d 轮（由上一轮 coverage-history 行推导：prev=%s）" % (STREAK, PREV),
    "上一轮行用例数 = %s；本轮两轮用例数 = %d / %d"
    % (g1(prev_line[0], r"两轮 (\d+) 例全绿", "上一轮用例数") if prev_line else "(未解析到)", R1["n"], R2["n"]),
]))
print("ANALYZE_WROTE = round-%s-analysis.txt / green-verify-%s-*.txt（5 条）" % (ROUND, ROUND))
sys.exit(1 if nf_ else 0)
