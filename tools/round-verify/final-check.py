#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾核对（**轮次无关**：`python tools/round-verify/final-check.py <轮次> <主提交短号> [--external-commit <短号>]... [--selftest]`）。

为什么有它
----------
历史「收尾一致性核对」是每轮**现写一份 aux 脚本**，且把轮次号 / 被测提交 / 返工真值 / 自述标记字面量
全部硬编码（上一轮那版 90 行里 5 处纯值写死），只活在 `$TEMP`，**输出也不进仓库**（只出现在对话回复里）——
既违反「证据必须能反映真实结论」（历史 12），又每轮重踩锚点过期一族缺陷（历史 205/217/245），
且下一轮无人能复核「那 9 项 PASS 到底核对了什么」（历史 177④）。
本工具把核对固化成轮次无关的可重跑实现：纯值全部由**证据自身**推出，产物直接落盘（`newline="\\n"`）。

核对项（F0–F18，每条都配 `> 0` 正向对照，历史 46/75/98）
------------------------------------------------------
* F0  facts 轮次相符 + 完成标记（前提可用性）
* F1  台账 CR == 0
* F2  台账表头 == 8 列名 ∧ 每行列数 == 表头列数（历史 80/155/200）
* F3  本轮台账行恰好 1 条
* F4  台账 c7（提交列）== 命令行给出的主提交短号
* F5  描述列长度 >= 800（内容级下限，历史 200）
* F6  自述标记 `本轮返工 **N 处**` 在描述列里**恰好 1 次**（锚定真值形态，历史 217-④/226/250）
* F7  描述列关键锚点由事实推出且全部命中（轮次 / missing=0 / 被测提交 / rc=0/0 / 连续第 N 轮）
* F8  证据列每一项都在磁盘上（本文件与主提交后产生的证据单列，历史 222）
* F9  证据列每一项都被 git 跟踪 ∧ 在 HEAD 树内（同上豁免，历史 16/198）
* F10 **三处同源**：描述列 / history 行 / 状态小节 —— 返工真值、连续轮次、用例数、类数、回归面条数五组逐组相等
* F11 要点文本三处同源：装置证据 ↔ 状态小节**逐字符相等** ∧ 描述列**以它结尾**（历史 12/95/215）
* F12 装置证据的返工真值 == 描述列解析值 ∧ 含 missing=0
* F13 主提交是 HEAD 的祖先（历史 200-②）
* F14 我**方**提交（被测提交..HEAD ∖ 已申报他方提交）改动文件**不含交付面前缀**（须 0）
* F14b 他方并发提交**显式申报**（`--external-commit`）且逐枚可核（在区间内 ∧ 主题不含本轮轮次号）
* F15 CSV / history / 状态小节三处本轮记录**各恰好 1 条**（幂等，历史 46）
* F16 覆盖缺口扫描：`tools/*.py` 中未被回归面引用的条目 == **白名单键集**（双向 + 每条理由非空 + 上限，
      历史 57/68/178/213）—— 任何**新增**孤儿立刻转红
* F18 仓库跟踪的 `coverage-report.json` 与本轮跑测归档**投影相等**（total/implemented/missing/
      registered_routes/by_task）—— 该文件只在「主仓库直接跑测试」时被刷新，长期停旧口径会被误登记成「他方在途」
* F17 正向对照：全部解析读数 > 0（0 发现先怀疑判据）

纪律：本文件**不得**出现当前轮次号字面量（否则 `device-report.py` 的轮次无关性守卫会命中它）；
`--selftest` 用合成上下文（轮次号运行期拼接）做**注入缺陷判别力实测**：每个分支恰好新增 1 条点名 FAIL，
空上下文必须整体变红（历史 32/66/75/82/93/98/113）。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
# 相位（green/red）单一事实源：轮次标记 / 锚点 / 跨相位的措辞都由它推出（历史 12/554）。
# 纯值（轮次 / 用例数 / rc / missing）一律由证据推出，**不得**硬编码绿相位措辞（否则红轮无法收尾）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase import GREEN, RED, phase_of, streak_pat, streak_marker, cases_pat  # noqa: E402
CSV = ROOT / ".agents/state/aap-server-feature-status.csv"
STATE = ROOT / ".agents/state/aap-server-tdd-state.md"
HIST = EV / "coverage-history.txt"
T = Path("C:/Users/laitz/AppData/Local/Temp")
MAN = ROOT / "tools/round-verify/manifest.json"
ARCH = ROOT / "tools/regression/archive"
END_MARK = "FINAL_CHECK_END=1"

# 交付面路径前缀（本轮提交出现即「碰了交付面」）。
DELIVERY_PREFIXES = ("aap-server/", "docs/", "aap-client/")

# 覆盖缺口白名单：**显式 + 条数上限 + 每条理由非空**（历史 57/68/178：豁免必须被机器判据与上限夹住，
# 否则「加豁免」会把规则架空）。判据是**双向**的：孤儿集合 == 本白名单键集，多一个、少一个都转红。
ORPHAN_WHITELIST = {
    "biz-closure-e2e.py": "需活进程（本地后端 + 一体桩）的真实 HTTP 闭环验收 —— 非静态审计，由联调阶段手工驱动",
    "newapi-stub.py": "长驻桩服务（--port）—— 非静态审计；由联调流程拉起，跑完不退出",
    "round-archive-clean.py": "归档目录幂等化助手，触发条件已消失（装置改为每轮唯一 wt-arch 目录，不存在第二份测试源）；保留供手工调用",
}
ORPHAN_LIMIT = 3

# 收尾相位才产生的证据（本文件自身 + 主提交之后产生的），只报状态、不断言「已跟踪」；
# 其余证据一律要求「存在 ∧ 已跟踪 ∧ 在 HEAD 树内」（历史 222：本文件不能把自己判成缺失）。
# 清单必须**跟上收尾链实际产出的证据**（历史 211：清单里的文件名是机械派生的文本盲区，
# 漏项的表现是「报告说证据未跟踪，而磁盘与 git 里其实都在」；收尾链的独立复核证据即实测漏项）。
POST_EVIDENCE = ("postwrite-check-%s.txt", "final-check-%s.txt", "independent-%s.txt")


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


def _g1(text, pat, label, flags=re.M):
    """取捕获组 1；未命中即抛（判据失效必须响亮，历史 46/168：0 命中先怀疑判据）。"""
    m = re.search(pat, text, flags=flags)
    if not m:
        raise LookupError(label)
    return m.group(1)


# ---------------------------------------------------------------- 判定（纯函数）
def evaluate(ctx):
    """全部核对项只读 ctx（dict），返回 [(检查项名, 是否通过, 说明)]。"""
    chk = []

    def add(name, cond, info=""):
        chk.append((name, bool(cond), info))

    R = ctx["round"]
    tests = []

    def probe(fn):
        """把「读数解析」包成可失败的探针：解析失败 -> 该检查项 FAIL 并给出点名信息（而不是抛穿）。"""
        try:
            return True, fn()
        except LookupError as e:
            return False, "读数未解析到：%s（判据失效，历史 46/168）" % e

    # ---- F0 前提可用性 ----
    add("F0", ctx["facts_round"] == R and ctx["facts_written"] == "1",
        "facts 轮次=%r（须 %s）完成标记=%r（须 '1'）" % (ctx["facts_round"], R, ctx["facts_written"]))

    # ---- F1/F2 CSV 结构 ----
    raw = ctx["csv_bytes"]
    add("F1", raw.count(b"\r") == 0, "台账 CR=%d（须 0，历史 69/146）" % raw.count(b"\r"))
    rows = ctx["csv_rows"]
    hdr = rows[0] if rows else []
    bad = [i + 1 for i, r in enumerate(rows) if len(r) != len(hdr)]
    add("F2", hdr == ctx["csv_hdr_expected"] and not bad,
        "表头 %r；列数异常行 %s" % (hdr, bad or "无"))

    def cell(r, i):
        """按列下标取值；行短于表头时返回 None 而不是越界抛（判据必须能容纳畸形行并**点名**，历史 80/155/200）。"""
        return r[i] if (r and len(r) > i) else None

    # ---- F3/F4 本轮行 ----
    mine = [r for r in rows if r and r[0] == R]
    add("F3", len(mine) == 1, "本轮台账行 %d 条（须 1）" % len(mine))
    row = mine[0] if len(mine) == 1 else None
    add("F4", cell(row, 7) == ctx["main"],
        "c7=%r（须 %s）" % (cell(row, 7), ctx["main"]))

    # ---- F5/F6/F7 描述列 ----
    desc = cell(row, 4) or ""
    add("F5", len(desc) >= 800, "描述列 %d 字符（须 >= 800）" % len(desc))
    ok6, v6 = probe(lambda: _g1(desc, r"本轮返工 \*\*(\d+) 处\*\*", "描述列自述标记"))
    if ok6:
        n = desc.count("本轮返工 **%s 处**" % v6)
        add("F6", n == 1, "自述标记『本轮返工 **%s 处**』出现 %d 次（须 1；锚定真值形态，历史 250）" % (v6, n))
    else:
        add("F6", False, v6)
    anchors = [R, "missing=%s" % ctx["miss_run"], "rc=%s" % ctx["rc_pair"], "被测提交 %s" % ctx["tested"],
               streak_marker(ctx["phase"], ctx["streak_src"]), "返工 **%s 处**" % ctx["rework_src"]]
    miss_a = [a for a in anchors if a not in desc]
    add("F7", not miss_a, "缺锚点 %s" % (miss_a or "无") + "（锚点全部由事实/相位推出）")

    # ---- F8/F9 证据列 ----
    ev = [x for x in ((cell(row, 6) or "").split("；")) if x.strip()]
    names = []
    for x in ev:
        nm = x.replace("evidence/", "").split("（")[0].strip()
        if nm:
            names.append(nm)
    post = [n % R for n in POST_EVIDENCE]
    must = [n for n in names if n not in post]
    gone = [n for n in must if n not in ctx["ev_disk"]]
    add("F8", bool(must) and not gone,
        "既有证据 %d 项 / 缺失 %s / 收尾相位证据 %s" % (len(must), gone or "无", [n for n in names if n in post]))
    untr = [n for n in must if n not in ctx["ev_tracked"]]
    not_head = [n for n in must if n not in ctx["ev_head"]]
    add("F9", bool(must) and not untr and not not_head,
        "未跟踪 %s / 不在 HEAD 树 %s（豁免 %s）" % (untr or "无", not_head or "无", post))

    # ---- F10 三处同源（四组数字逐组相等：描述 / history / 状态小节） ----
    ok10, why10 = True, []
    triples = [
        ("返工真值",
         lambda t: _g1(t, r"本轮返工 \*\*(\d+) 处\*\*", "描述·返工"),
         lambda t: _g1(t, r"本轮返工 (\d+) 处（判据/脚本侧）", "history·返工"),
         lambda t: _g1(t, r"本轮返工真值 = \*\*(\d+) 处\*\*", "状态·返工")),
        ("轮次/红相位计数",
         lambda t: _g1(t, streak_pat(ctx["phase"]), "描述·轮次"),
         lambda t: _g1(t, streak_pat(ctx["phase"]), "history·轮次"),
         lambda t: _g1(t, streak_pat(ctx["phase"]), "状态·轮次")),
        ("用例数/类数",
         lambda t: _g1(t, r"两轮 \*\*(\d+) 例 / (\d+) 类\*\*", "描述·用例"),
         lambda t: _g1(t, cases_pat(), "history·用例"),
         lambda t: _g1(t, r"各 \*\*(\d+) 例 / (\d+) 类\*\*", "状态·用例")),
        ("回归面条数",
         lambda t: _g1(t, r"回归面 \*\*(\d+) 条\*\*", "描述·回归面"),
         lambda t: _g1(t, r"回归面复跑 (\d+) 条", "history·回归面"),
         lambda t: _g1(t, r"复跑 (\d+) 条", "状态·回归面")),
    ]
    got10 = []
    for label, fd, fh, fs in triples:
        try:
            a, b, c = fd(desc), fh(ctx["hist_line"]), fs(ctx["state_sec"])
        except LookupError as e:
            ok10 = False
            why10.append("%s 读数未解析到（%s）" % (label, e))
            continue
        got10.append((label, a, b, c))
        if not (a == b == c):
            ok10 = False
            why10.append("%s 三处不等 描述=%r history=%r 状态=%r" % (label, a, b, c))
    add("F10", ok10 and len(got10) == len(triples),
        "四组读数 %s%s" % (got10, ("；" + "；".join(why10)) if why10 else ""))

    # ---- F11 要点文本三处同源 ----
    ns = ctx["note_state"]
    if ns is None:
        add("F11", False, "状态小节里的要点文本未解析到（判据失效，历史 46）")
    else:
        add("F11", ns == ctx["note_dev"] and desc.endswith(ns) and len(ns) >= 100,
            "要点 %d 字符；装置证据 == 状态小节 %s；描述列以它结尾 %s"
            % (len(ns), ns == ctx["note_dev"], desc.endswith(ns)))

    # ---- F12 装置证据的返工真值 ----
    ok12, why12 = probe(lambda: _g1(ctx["dev_text"], r"返工真值 = \*\*(\d+) 处\*\*", "装置证据·返工真值"))
    if ok12 and ok6:
        add("F12", why12 == v6 and ("missing=%s" % ctx["miss_run"]) in ctx["dev_text"],
            "装置证据返工真值=%r / 描述=%r；含 missing=%s %s"
            % (why12, v6, ctx["miss_run"], ("missing=%s" % ctx["miss_run"]) in ctx["dev_text"]))
    else:
        add("F12", False, why12 if not ok12 else "描述列自述标记未解析到")

    # ---- F13/F14/F14b 提交链 ----
    add("F13", ctx["ancestor"], "主提交 %s 是 HEAD 的祖先 = %s" % (ctx["main"], ctx["ancestor"]))
    bad_files = [x for x in ctx["round_files"] if x.startswith(DELIVERY_PREFIXES)]
    add("F14", bool(ctx["round_files"]) and not bad_files,
        "我**方**提交改动 %d 个文件 / 越界交付面 %d 个 %s（区间内共 %d 个，其中已申报他方提交触及 %d 个）"
        % (len(ctx["round_files"]), len(bad_files), bad_files[:5], len(ctx["round_files_all"]),
           len(ctx["ext_files"])))
    # F14b：他方并发提交必须**显式申报**且逐枚可核（区间内 ∧ 主题不含本轮轮次号）。未申报的外部活动
    # 照旧由 F14 响亮失败 —— 判据范围与语义一致（历史 81/193/198），与 `independent.py` / `device-report.py` 同族。
    add("F14b", not ctx["external_bad"] and (not ctx["external"] or bool(ctx["ext_files"])),
        "申报他方提交 %s / 触及文件 %d 个 / 不可核 %s"
        % (ctx["external"] or "无", len(ctx["ext_files"]), ctx["external_bad"] or "无"))

    # ---- F15 三处各恰好 1 条 ----
    add("F15", ctx["n_csv"] == 1 and ctx["n_hist"] == 1 and ctx["n_state"] == 1,
        "CSV %d / history %d / 状态小节 %d（各须 1）" % (ctx["n_csv"], ctx["n_hist"], ctx["n_state"]))

    # ---- F16 覆盖缺口扫描（双向 + 上限 + 理由非空） ----
    orph = set(ctx["orphans"])
    wl = ctx["orphan_whitelist"]
    extra = sorted(orph - set(wl))
    absent = sorted(set(wl) - orph)
    empty_reason = sorted(k for k, v in wl.items() if not v.strip())
    add("F16", not extra and not absent and not empty_reason and len(wl) <= ORPHAN_LIMIT and bool(orph),
        "孤儿 %d 条 / 白名单 %d 条（上限 %d）；未列入 %s / 白名单多余 %s / 理由为空 %s；扫描根 %s"
        % (len(orph), len(wl), ORPHAN_LIMIT, extra or "无", absent or "无", empty_reason or "无", ctx["scan_roots"]))

    # ---- F18 跟踪的巡检输出（coverage-report.json）与当前口径一致 ----
    # 为什么值得单列：该文件**被 git 跟踪**、被任务书当作覆盖门禁报告，却只在「主仓库直接跑测试」时被刷新
    # （worktree 跑测写的是 worktree 里那份）→ 长期停在旧口径，而每轮报告把它登记成「他方在途」（归属误标）。
    proj = sorted(["total", "implemented", "missing", "registered_routes", "by_task"])
    repo_cov, run_cov = ctx["cov_repo"], ctx["cov_run"]
    # 空/缺失两侧都不得判绿（历史 98：`all([])` / `{} == {}` 是空转假绿的经典形态）
    add("F18", bool(repo_cov) and bool(run_cov) and repo_cov == run_cov,
        "仓库跟踪副本 %s / 本轮跑测归档 %s（比对键 %s）"
        % ({k: (repo_cov or {}).get(k) for k in proj if k != "by_task"}, 
           {k: (run_cov or {}).get(k) for k in proj if k != "by_task"}, proj))

    # ---- F17 正向对照 ----
    pos = {"CSV 行数": len(rows), "history 行数": len(ctx["hist_text"].splitlines()),
           "状态文本行数": len(ctx["state_text"].splitlines()), "装置证据行数": len(ctx["dev_text"].splitlines()),
           "证据列项数": len(names), "本轮提交文件数": len(ctx["round_files"]),
           "扫描根数": len(ctx["scan_roots"]), "孤儿候选数": len(orph),
           "覆盖副本分族数": len((run_cov or {}).get("by_task", {}))}
    zeros = sorted(k for k, v in pos.items() if v <= 0)
    add("F17", not zeros, "各源解析读数 %s%s" % (pos, ("；为 0：%s" % zeros) if zeros else ""))

    return chk


def own_of(all_files, ext_files):
    """归属归一（纯函数，入参 = 文本列表）：把**已申报他方提交**触及的文件从区间改动集合里剔除。

    与 `independent.py` 的同名纯函数**必须同语义**（同一事实只有一种写法，历史 44）：
    判据是集合差，且只对**成员**生效 —— 非成员项不得改动集合，否则「申报」可架空守卫
    （历史 57/68/190）。空申报时恒等（零外部活动轮次口径不变）。
    """
    ext = set(ext_files)
    return sorted(x for x in all_files if x not in ext)


# ---------------------------------------------------------------- 真实上下文
def build_ctx(ROUND, MAIN, external=()):
    facts = parse_facts(T / "aap-round-verify" / ROUND / ("facts-%s.log" % ROUND))
    tested = facts["FACTS_TESTED_COMMIT"]
    raw = CSV.read_bytes()
    import csv as _csv
    import io as _io
    rows = list(_csv.reader(_io.StringIO(raw.decode("utf-8"), newline="")))
    hist_text = HIST.read_text(encoding="utf-8", errors="replace")
    state_text = STATE.read_text(encoding="utf-8", errors="replace")
    dev_text = (EV / ("device-round-%s.txt" % ROUND)).read_text(encoding="utf-8", errors="replace")

    hist_lines = [ln for ln in hist_text.splitlines() if (" %s " % ROUND) in ln]
    hist_line = hist_lines[0] if len(hist_lines) == 1 else ""

    st_lines = state_text.splitlines()
    marks = [i for i, ln in enumerate(st_lines) if ln.startswith("### %s 巡检轮" % ROUND)]
    if len(marks) == 1:
        i0 = marks[0]
        i1 = next((j for j in range(i0 + 1, len(st_lines)) if st_lines[j].startswith("### ")), len(st_lines))
        state_sec = "\n".join(st_lines[i0:i1])
    else:
        state_sec = ""

    m_note = re.search(r"- \*\*本轮要点（单一事实源 = [^）]*）\*\*：\n(.*?)\n- \*\*返工真值\*\*", state_sec, flags=re.S)
    note_state = m_note.group(1) if m_note else None
    m_dev = re.search(r"\n-{20,}\n(.*?)\n-{20,}\n", dev_text, flags=re.S)
    note_dev = m_dev.group(1) if m_dev else None

    _, tracked, _ = sh("ls-files", ".agents/state/evidence")
    ev_tracked = set(tracked.splitlines())
    _, headl, _ = sh("ls-tree", "--name-only", "HEAD:.agents/state/evidence")
    ev_head = set(headl.splitlines())
    _, _, _ = sh("cat-file", "-t", MAIN)

    # 覆盖缺口：扫描根**显式枚举**（历史 213①：扫描范围本身是盲区，必须显式枚举 + 断言）
    import json as _json
    man = _json.loads(MAN.read_text(encoding="utf-8"))
    refs = set()
    for sec in ("audits", "selftests"):
        for e in man.get(sec, []):
            for a in e.get("cmd", []):
                if str(a).endswith((".py", ".sh")):
                    refs.add(Path(str(a).replace("\\", "/")).name)
    scan_roots = []
    top = sorted(p.name for p in (ROOT / "tools").glob("*.py"))
    scan_roots.append("tools/*.py(%d)" % len(top))
    scan_roots.append("manifest.audits+selftests(%d)" % sum(len(man.get(s, [])) for s in ("audits", "selftests")))
    scan_roots.append("archive/ 归仓目录(%d)" % len([d for d in ARCH.iterdir() if d.is_dir()]))
    orphans = sorted(n for n in top if n not in refs)

    def _cov(p):
        try:
            d = _json.loads(Path(p).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return None
        return {k: d.get(k) for k in ("total", "implemented", "missing", "registered_routes", "by_task")}

    cov_repo = _cov(ROOT / ".agents/state/evidence/coverage-report.json")
    cov_run = _cov(T / "aap-round-verify" / ROUND / "wt-arch/coverage-report.json")

    # 三处「本轮记录条数」
    n_csv = len([r for r in rows if r and r[0] == ROUND])
    n_state = len(marks)

    # ---- F13/F14/F14b 提交链 ----
    # 提交链：`被测提交..HEAD` 的全部改动文件按**归属**分区 —— 已申报他方提交触及的文件从「我方改动集合」
    # 里剔除（纯函数 `own_of`，只对成员生效；未申报的外部改动照旧留在集合里由 F14 响亮失败）。
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
    rc_anc, _, _ = sh("merge-base", "--is-ancestor", MAIN, "HEAD")
    _, dt_out, _ = sh("diff", "--name-only", "%s..HEAD" % tested)
    round_files_all = [x for x in dt_out.splitlines() if x.strip()]
    round_files = own_of(round_files_all, ext_files)

    desc_row = next((r[4] for r in rows if r and r[0] == ROUND), "")
    # 相位由**事实源**推出（facts 的两轮 rc ∧ 本轮跑测归档的 missing）—— 不读描述列，否则循环论证。
    rc1, rc2 = facts.get("FACTS_RUN1_RC", "1"), facts.get("FACTS_RUN2_RC", "1")
    miss_run = (cov_run or {}).get("missing", 1)
    phase = phase_of(rc1, rc2, miss_run)
    streak = ""
    rework = ""
    m = re.search(streak_pat(phase), desc_row)
    if m:
        streak = m.group(1)
    m = re.search(r"本轮返工 \*\*(\d+) 处\*\*", desc_row)
    if m:
        rework = m.group(1)

    out = {
        "round": ROUND, "main": MAIN, "tested": tested,
        "facts_round": facts.get("FACTS_ROUND", ""), "facts_written": facts.get("FACTS_WRITTEN", ""),
        "csv_bytes": raw, "csv_rows": rows,
        "csv_hdr_expected": ['任务号', '接口ID', '方法', '路径', '依据', '状态', '证据', '提交'],
        "hist_text": hist_text, "hist_line": hist_line,
        "state_text": state_text, "state_sec": state_sec,
        "dev_text": dev_text, "note_state": note_state, "note_dev": note_dev,
        "ev_disk": set(p.name for p in EV.iterdir() if p.is_file()),
        "ev_tracked": set(x.split("/")[-1] for x in ev_tracked),
        "ev_head": set(x.split("/")[-1] for x in ev_head),
        "ancestor": rc_anc == 0, "round_files": round_files,
        "round_files_all": round_files_all, "external": [s for s in external if s not in ext_bad],
        "external_bad": ext_bad, "ext_files": ext_files,
        "orphans": orphans, "orphan_whitelist": ORPHAN_WHITELIST, "scan_roots": scan_roots,
        "n_csv": n_csv, "n_hist": len(hist_lines), "n_state": n_state,
        "streak_src": streak, "rework_src": rework,
        "phase": phase, "rc_pair": "%s/%s" % (rc1, rc2), "miss_run": miss_run,
        "cov_repo": cov_repo, "cov_run": cov_run,
    }
    # 真实上下文与合成上下文的**键集必须相等**：新增 ctx 键时只在合成侧补齐，
    # 会让自测全绿而真实运行 KeyError（历史 44/82：同一事实两处写法是漂移高发地）。
    _ref = synth_ctx()
    if set(out) != set(_ref):
        raise SystemExit("[FAIL] 真实上下文与合成上下文键集不同：真实缺 %s / 真实多 %s"
                         % (sorted(set(_ref) - set(out)), sorted(set(out) - set(_ref))))
    return out


# ---------------------------------------------------------------- 自测
SYNTH = "R" + "9" * 6          # 合成轮次号（运行期拼接，源码内不出现当前轮次号字面量）
SYNTH_TESTED = "aaaaaaaa"
SYNTH_MAIN = "bbbbbbbb"


def synth_ctx():
    R = SYNTH
    pad = "补足长度以便描述列过 800 字符下限。" * 40
    note = ("本轮返工 3 处（判据/脚本侧，零交付面影响）：① 合成要点第①条，说明判据口径；"
            "② 合成要点第②条，说明读数来源；③ 合成要点第③条，说明落盘纪律。" + pad)
    desc = ("%s 巡检轮（missing=0 ⇒ **校验轮**：**交付面零改动**（交付代码 / 测试面 / 冻结清单生成物零改动；"
            "本轮**装置面与交付面均零改动**）） · 清单 **108/108**（作业目标「90 条全部落地」已含于 total 之中；"
            "**基线 = 被测提交 %s**）连续第 **476** 轮全绿 · 两轮 **263 例 / 45 类** rc=0/0（串行 12:00:00→12:05:00，"
            "逐类 diff=0） · 回归面 **84 条** rc 变化 0 / 新增 0 / 未复跑 0；FAIL 明细 42 脚本 161 行（= 上一轮，"
            "跨轮 faildiff 新增 0） · 分析器 PASS 25 / FAIL 0 · registered_routes=125 · 本轮返工 **3 处**（装置侧） · "
            "证据 14 条 · " % (R, SYNTH_TESTED)) + note
    hist = ("2026-09-27 12:06:59 %s %s 巡检轮 | 清单 108/108（作业目标「90 条全部落地」已含于 total 之中；"
            "**基线 = 被测提交 %s**） missing=0 registered_routes=125 not_registered=[] | 全量两轮 263 例全绿"
            "（连续第 476 轮；两轮 rc=0/0、逐类 diff=0） | 回归面复跑 84 条 rc 变化 0 条 / FAIL 明细 42 脚本 161 行 | "
            "分析器 PASS 25 / FAIL 0 | 本轮返工 3 处（判据/脚本侧） | 证据 14 条" % (R, R, SYNTH_TESTED))
    sec = ("### %s 巡检轮（校验轮：missing=0 ⇒ 交付面零改动）\n\n- **性质**：`missing=0` ⇒ **交付面零改动**。\n"
           "- **两轮全量（串行）**：被测提交 = %s；各 **263 例 / 45 类**、rc=0/0、Failures-Errors-Skipped = 0-0-0。\n"
           "- **覆盖**：total=108 implemented=108 **missing=0**、registered_routes=125；连续第 **476** 轮全绿。\n"
           "- **回归面**：复跑 84 条；rc 变化 0 条、新增 0、未复跑 0。\n"
           "- **本轮要点（单一事实源 = round-note.md）**：\n%s\n"
           "- **返工真值**：本轮返工真值 = **3 处**（装置/脚本侧）。\n"
           "- **权威数字**：权威数字 = 返工 3 处。\n" % (R, SYNTH_TESTED, note))
    dev = ("%s 装置侧证据（装置面改动 + 本轮返工真值 + 交付面零改动三判据）\n%s\n"
           "二、本轮返工真值 = **3 处**（零交付面影响）\n%s\n%s\n%s\n"
           "三、本轮关键读数：分析器判据 PASS 25 / FAIL 0；覆盖 total=108 implemented=108 **missing=0** "
           "registered_routes=125；连续第 476 轮全绿\n" % (R, "=" * 78, "-" * 78, note, "-" * 78))
    evnames = ["round-%s-analysis.txt" % R, "device-round-%s.txt" % R,
               "postwrite-check-%s.txt" % R, "final-check-%s.txt" % R]
    return {
        "round": R, "main": SYNTH_MAIN, "tested": SYNTH_TESTED,
        "facts_round": R, "facts_written": "1",
        "csv_bytes": ("任务号,接口ID,方法,路径,依据,状态,证据,提交\n"
                      'R900000,"","","","%s","","evidence/a.txt；evidence/b.txt","%s"\n' % (desc, SYNTH_MAIN)).encode("utf-8"),
        "csv_rows": [['任务号', '接口ID', '方法', '路径', '依据', '状态', '证据', '提交'],
                     [R, "", "", "", desc, "", "evidence/round-%s-analysis.txt；evidence/device-round-%s.txt；"
                      "evidence/postwrite-check-%s.txt；evidence/final-check-%s.txt" % (R, R, R, R), SYNTH_MAIN]],
        "csv_hdr_expected": ['任务号', '接口ID', '方法', '路径', '依据', '状态', '证据', '提交'],
        "hist_text": hist + "\n", "hist_line": hist,
        "state_text": sec, "state_sec": sec,
        "dev_text": dev, "note_state": note, "note_dev": note,
        "ev_disk": set(evnames), "ev_tracked": set(evnames), "ev_head": set(evnames),
        "ancestor": True, "round_files": [".agents/state/evidence/device-round-%s.txt" % R,
                                          "tools/round-verify/final-check.py"],
        # 合成「他方并发提交」形态：区间内共 3 个文件，其中交付面那 1 个由**已申报他方提交**触及 ⇒
        # 归属归一后我方改动集合只剩 2 个（F14 绿）；把它改回未申报即 F14 红（判别力实测，历史 66/90）。
        "round_files_all": [".agents/state/evidence/device-round-%s.txt" % R,
                            "tools/round-verify/final-check.py",
                            "aap-server/src/main/java/X.java"],
        "external": ["deadbee"], "external_bad": [], "ext_files": ["aap-server/src/main/java/X.java"],
        "orphans": sorted(ORPHAN_WHITELIST), "orphan_whitelist": ORPHAN_WHITELIST,
        "scan_roots": ["tools/*.py(31)", "manifest.audits+selftests(84)", "archive/ 归仓目录(54)"],
        "n_csv": 1, "n_hist": 1, "n_state": 1,
        "streak_src": "476", "rework_src": "3",
        "phase": GREEN, "rc_pair": "0/0", "miss_run": 0,
        "cov_repo": {"total": 108, "implemented": 108, "missing": 0, "registered_routes": 125,
                     "by_task": {"": {"total": 9, "implemented": 9}, "T17": {"total": 6, "implemented": 6}}},
        "cov_run": {"total": 108, "implemented": 108, "missing": 0, "registered_routes": 125,
                    "by_task": {"": {"total": 9, "implemented": 9}, "T17": {"total": 6, "implemented": 6}}},
    }


def synth_ctx_red():
    """红相位合成上下文：与 `synth_ctx()` **只差相位相关字段**（描述列 / history / 状态小节 / 装置证据的关键读数）。

    为什么需要它：F7 锚点、F10 的轮次三元组、F12 的 missing 读数都是**相位相关**判据 —— 只在绿相位夹具上
    自测，红相位分支永远不被执行（历史 32/75/98：判定有几个分支就要有几条反例）。
    """
    c = synth_ctx()

    def red(t):
        # 顺序敏感（历史 245①）：先做通用替换，再做**形态相关**替换 —— 反序会让「形态锚点」再也匹配不到。
        t = t.replace("missing=0", "missing=9")
        t = t.replace("missing=9 ⇒ **校验轮**", "missing=9（**红相位**）⇒ 红相位轮")
        t = t.replace("连续第 **476** 轮全绿", "%s = **0**（红相位**计数清零**）" % "连续全绿计数")
        t = t.replace("连续第 **476** 轮", "%s = **0**（红相位**计数清零**）" % "连续全绿计数")
        t = t.replace("连续第 476 轮全绿", "%s = 0（红相位清零）" % "连续全绿计数")
        t = t.replace("连续第 476 轮", "%s = 0（红相位清零）" % "连续全绿计数")
        return t.replace("rc=0/0", "rc=1/1")

    c["phase"], c["rc_pair"], c["miss_run"], c["streak_src"] = RED, "1/1", 9, "0"
    c["cov_repo"] = dict(c["cov_repo"], total=117, implemented=108, missing=9)
    c["cov_run"] = dict(c["cov_run"], total=117, implemented=108, missing=9)
    c["csv_rows"][1][4] = red(c["csv_rows"][1][4])
    c["hist_line"] = red(c["hist_line"])
    c["hist_text"] = c["hist_line"] + "\n"
    c["state_sec"] = red(c["state_sec"])
    c["state_text"] = c["state_sec"]
    c["dev_text"] = red(c["dev_text"])
    return c


def fails_of(chk):
    return sorted(n for n, ok, _ in chk if not ok)


def selftest():
    base = synth_ctx()
    out0 = evaluate(base)
    bad0 = fails_of(out0)
    res = []

    def chk(name, cond, info=""):
        res.append((name, bool(cond), info))

    chk("T0 合成上下文基线全绿（每条判据都有正向对照，历史 46/75）", not bad0, "FAIL=%s" % bad0)

    def mutate(mut, expect):
        c = synth_ctx()
        mut(c)
        f = fails_of(evaluate(c))
        delta = sorted(set(f) - set(bad0))
        gone = sorted(set(bad0) - set(f))
        chk("T·%s 注入缺陷 -> 恰好新增 %s" % ("/".join(expect), expect),
            delta == sorted(expect) and not gone, "新增=%s 消失=%s" % (delta, gone))

    # T1 描述列缺锚点（rc=0/0）
    mutate(lambda c: c.update(csv_rows=[c["csv_rows"][0],
                                        c["csv_rows"][1][:4] + [c["csv_rows"][1][4].replace("rc=0/0", "rc=0")] + c["csv_rows"][1][5:]]),
           ["F7"])
    # T2 c7 改号
    mutate(lambda c: c.update(csv_rows=[c["csv_rows"][0], c["csv_rows"][1][:7] + ["deadbeef"]]), ["F4"])
    # T3 三处不同源（history 返工值 3 -> 9）
    mutate(lambda c: c.update(hist_line=c["hist_line"].replace("本轮返工 3 处", "本轮返工 9 处")), ["F10"])
    # T4 要点文本不同源（描述列不再以要点结尾）
    mutate(lambda c: c.update(csv_rows=[c["csv_rows"][0], c["csv_rows"][1][:4] + [c["csv_rows"][1][4] + "尾注"] + c["csv_rows"][1][5:]]),
           ["F11"])
    # T5 证据文件缺失
    mutate(lambda c: c.update(ev_disk=set(c["ev_disk"]) - {"round-%s-analysis.txt" % SYNTH}), ["F8"])
    # T6 证据未被 git 跟踪
    mutate(lambda c: c.update(ev_tracked=set(c["ev_tracked"]) - {"device-round-%s.txt" % SYNTH}), ["F9"])
    # T7 主提交不是 HEAD 祖先
    mutate(lambda c: c.update(ancestor=False), ["F13"])
    # T8 本轮提交触及交付面
    mutate(lambda c: c.update(round_files=c["round_files"] + ["aap-server/src/main/java/X.java"]), ["F14"])
    # T9 新增未列入白名单的孤儿
    mutate(lambda c: c.update(orphans=sorted(set(c["orphans"]) | {"audit-brand-new.py"})), ["F16"])
    # T10 白名单条目其实已被引用（双向：少一条也转红）
    mutate(lambda c: c.update(orphans=sorted(set(c["orphans"]) - {"newapi-stub.py"})), ["F16"])
    # T11 白名单某条理由为空
    mutate(lambda c: c.update(orphan_whitelist=dict(ORPHAN_WHITELIST, **{"biz-closure-e2e.py": "  "})), ["F16"])
    # T12 台账出现列数异常**行**（注入限定在「新增一条畸形行」，不改变本轮行的可用性 —— 历史 104：作用域要精确）
    mutate(lambda c: c.update(csv_rows=c["csv_rows"] + [["RX", "", ""]]), ["F2"])
    # T13 CSV 出现 CR
    mutate(lambda c: c.update(csv_bytes=c["csv_bytes"].replace(b"\n", b"\r\n", 1)), ["F1"])
    # T14 状态小节本轮记录两条
    mutate(lambda c: c.update(n_state=2), ["F15"])
    # T15 装置证据返工真值 != 描述列
    mutate(lambda c: c.update(dev_text=c["dev_text"].replace("返工真值 = **3 处**", "返工真值 = **7 处**")), ["F12"])
    # T16 描述列自述标记出现两次（自述标记唯一性）
    mutate(lambda c: c.update(csv_rows=[c["csv_rows"][0],
                                        c["csv_rows"][1][:4] + [c["csv_rows"][1][4] + " 本轮返工 **3 处**（重复）"] + c["csv_rows"][1][5:]]),
           ["F6", "F11"])
    # T19 仓库跟踪的 coverage-report 副本停在旧口径（F18）
    mutate(lambda c: c.update(cov_repo=dict(c["cov_repo"], total=102, implemented=102)), ["F18"])
    # T23/T24/T25 他方并发提交的申报语义（与 `independent.py` / `device-report.py` 同族，历史 81/193/198）：
    # 未申报 ⇒ 交付面文件留在「我方改动集合」里由 F14 响亮失败；申报了但不可核 / 解析不到触及文件 ⇒ F14b 红。
    mutate(lambda c: c.update(round_files=c["round_files_all"], ext_files=[], external=[]), ["F14"])
    mutate(lambda c: c.update(external_bad=["deadbee"]), ["F14b"])
    mutate(lambda c: c.update(external=["deadbee"], ext_files=[]), ["F14b"])
    chk("T25 own_of 三态：恒等（空申报）/ 剔除成员 / 非成员不得被剔除（历史 57/68/190）",
        own_of(["a", "b"], []) == ["a", "b"] and own_of(["a", "b"], ["a"]) == ["b"]
        and own_of(["a", "b"], ["zz"]) == ["a", "b"], "见条件")
    # 跨工具同族守卫：两个工具对「归属归一」必须同语义（同一事实只有一种写法，历史 44）。
    # 导入失败必须判红（不得静默跳过 —— 历史 98：守卫不可用 ≠ 守卫通过）。
    try:
        from independent import own_of as _own_ind
        _same = _own_ind(["a", "b"], ["a"]) == own_of(["a", "b"], ["a"]) == ["b"]
    except Exception:
        _same = False
    chk("T26 与 independent.py 的 own_of 同语义（归属归一只有一种写法，历史 44）", _same, "见条件")
    # T17 空上下文必须整体变红（空夹具判据，历史 128/132）
    empty = {k: (type(v)() if isinstance(v, (list, set, dict, str)) else v) for k, v in synth_ctx().items()}
    empty.update(csv_bytes=b"", csv_rows=[], hist_line="", state_sec="", dev_text="",
                 note_state=None, note_dev=None, n_csv=0, n_hist=0, n_state=0,
                 cov_repo=None, cov_run=None)
    fe = fails_of(evaluate(empty))
    chk("T17 空上下文整体变红且点名 F7/F10/F11/F12/F16",
        {"F7", "F10", "F11", "F12", "F16"}.issubset(set(fe)), "FAIL=%s" % fe)
    # T18 正向对照：真实仓库的覆盖缺口扫描读数 > 0
    chk("T18 白名单与孤儿候选都非空（判据非空转）",
        len(ORPHAN_WHITELIST) > 0 and len(synth_ctx()["orphans"]) > 0)

    # ---- 相位分支的判别力实测（历史 32/75/98：判定有几个分支就要有几条反例） ----
    bad_red = fails_of(evaluate(synth_ctx_red()))
    chk("T20 红相位合成上下文基线全绿（F7/F10/F12 的**红相位分支**真的被执行）", not bad_red, "FAIL=%s" % bad_red)
    c21 = synth_ctx_red()
    c21["csv_rows"][1][4] = c21["csv_rows"][1][4].replace("missing=9", "missing=N")
    f21 = fails_of(evaluate(c21))
    chk("T21 红相位注入「描述列 missing 锚点被改」-> 恰好新增 F7（F10 的轮次/用例/回归面读数不受影响）",
        sorted(set(f21) - set(bad_red)) == ["F7"] and not (set(bad_red) - set(f21)),
        "新增=%s 消失=%s" % (sorted(set(f21) - set(bad_red)), sorted(set(bad_red) - set(f21))))
    c22 = synth_ctx()
    c22["csv_rows"][1][4] = synth_ctx_red()["csv_rows"][1][4]
    chk("T22 互斥：红相位措辞喂给**绿相位**上下文 -> F7 转红（锚点不跨相位假命中）",
        "F7" in fails_of(evaluate(c22)), "FAIL=%s" % fails_of(evaluate(c22)))

    ok = sum(1 for _, c, _ in res if c)
    for name, c, info in res:
        print("  [%s] %s%s" % ("PASS" if c else "FAIL", name, (" " + info) if info else ""))
    print("  判据：PASS %d / FAIL %d" % (ok, len(res) - ok))
    print(END_MARK)
    return 0 if ok == len(res) else 1


# ---------------------------------------------------------------- 主流程
def main():
    try:
        sys.stdout.reconfigure(newline="\n")
    except Exception:
        pass
    args = sys.argv[1:]
    ROUND = (args[0] if args else "").upper()
    if not re.fullmatch(r"R\d+", ROUND):
        print("用法: python tools/round-verify/final-check.py <轮次> <主提交短号> [--selftest]")
        return 2
    if "--selftest" in args:
        return selftest()
    MAIN = (args[1] if len(args) > 1 else "")
    if not re.fullmatch(r"[0-9a-f]{7,40}", MAIN):
        print("[FAIL] 主提交短号必填（第 2 个参数）")
        return 2
    n_ex = sum(1 for a in args if a == "--external-commit")
    external = [args[i + 1] for i, a in enumerate(args) if a == "--external-commit" and i + 1 < len(args)]
    if len(external) != n_ex:
        print("[FAIL] --external-commit 缺参数值")
        return 2
    ctx = build_ctx(ROUND, MAIN, external)
    chk = evaluate(ctx)
    out = EV / ("final-check-%s.txt" % ROUND)
    L = ["%s 收尾核对（轮次无关装置：tools/round-verify/final-check.py）" % ROUND, "=" * 78,
         "生成方式：纯值全部由**证据自身**推出（台账 CSV / history / 状态小节 / 装置证据 / git / facts），源码内零硬编码；",
         "本文件由工具直接落盘（newline=\"\\n\"），不依赖 shell 重定向。",
         "轮次 = %s；主提交（核对参数）= %s；被测提交（facts）= %s；核对时 HEAD = %s"
         % (ROUND, MAIN, ctx["tested"], sh("rev-parse", "--short", "HEAD")[1].strip()),
         ""]
    for name, ok, info in chk:
        L.append("[%s] %s %s" % ("PASS" if ok else "FAIL", name, info))
    nfail = len([1 for _, ok, _ in chk if not ok])
    L.append("")
    L.append("覆盖缺口扫描明细（扫描根**显式枚举**；白名单 = 显式 + 条数上限 + 每条理由非空，"
             "历史 57/68/178/213：豁免必须被机器判据与上限夹住，任何**新增**孤儿立刻转红）")
    L.append("  扫描根 = %s" % "、".join(ctx["scan_roots"]))
    L.append("  未入回归面的候选 = %d 条（上限 %d）" % (len(ORPHAN_WHITELIST), ORPHAN_LIMIT))
    for k in sorted(ORPHAN_WHITELIST):
        L.append("    · %s —— %s" % (k, ORPHAN_WHITELIST[k]))
    L.append("")
    L.append("核对项：PASS %d / FAIL %d（%d 项）" % (len(chk) - nfail, nfail, len(chk)))
    L.append(END_MARK)
    text = "\n".join(L) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    rb = out.read_bytes()
    if rb.count(b"\r") != 0:
        print("[FAIL] 落盘含 CR（历史 69/84/146）")
        return 2
    got = rb.decode("utf-8")
    need = [ROUND, MAIN, "核对项：PASS", END_MARK]
    miss = [x for x in need if x not in got]
    if miss or got.count(END_MARK) != 1 or len(got.splitlines()) < 10:
        print("[FAIL] 落盘复核失败：缺 %s / 结束标记 %d / 行数 %d（历史 222/230）"
              % (miss, got.count(END_MARK), len(got.splitlines())))
        return 2
    for name, ok, info in chk:
        if not ok:
            print("[FAIL] %s %s" % (name, info))
    print("收尾核对：PASS %d / FAIL %d；证据 = %s（%d 行 / CR=0）"
          % (len(chk) - nfail, nfail, out.name, len(got.splitlines())))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
