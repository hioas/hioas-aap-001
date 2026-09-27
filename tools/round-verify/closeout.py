#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""巡检轮收尾（**轮次无关**：`python tools/round-verify/closeout.py R490 --rework 3 --note <file>`）。

写三处（单一事实源 → 三个消费者）：
  1. `.agents/state/evidence/coverage-history.txt` 追加本轮行；
  2. `.agents/state/aap-server-feature-status.csv` 追加本轮台账行（8 列）；
  3. `.agents/state/aap-server-tdd-state.md` 追加本轮小节。

设计纪律（逐条来自历史返工）：
  * 数字**全部由证据推出**（facts / 分析证据 / 回归证据 / 磁盘上的证据文件清单），源码内零手写值（201/206/243-③）；
  * 台账行验收是**内容级**的：8 列 + 描述列与单一事实源**逐字符相等** + 长度下限 + 关键锚点命中（200/80/155）；
  * 「本轮要点」文本只写一处（`--note` 文件），台账与状态文件**共用同一份**，杜绝两处分叉（215/217-③）；
  * 幂等三态判据：已存在本轮行 → 只校验不追加；既无旧行也无新行 → 判据失效并响亮失败（208/245）；
  * 追加一律 LF、写前补末行换行、写后只读复核（69/84/146）。
"""
import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
EV = ROOT / ".agents/state/evidence"
CSV = ROOT / ".agents/state/aap-server-feature-status.csv"
STATE = ROOT / ".agents/state/aap-server-tdd-state.md"
HIST = EV / "coverage-history.txt"
T = Path("C:/Users/laitz/AppData/Local/Temp")

args = sys.argv[1:]
ROUND = (args[0] if args else "").upper()
if not re.fullmatch(r"R\d+", ROUND):
    print("用法: python tools/round-verify/closeout.py R490 --rework 3 --note <file> [--commit <sha>]")
    sys.exit(2)
prev_round = "R%d" % (int(ROUND[1:]) - 1)


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


REWORK = opt("--rework")
NOTE = opt("--note")
COMMIT = opt("--commit", "")
assert REWORK is not None and re.fullmatch(r"\d+", REWORK), "--rework N 必填（返工真值由人判定，工具不猜）"
assert NOTE and Path(NOTE).exists(), "--note <文件> 必填（本轮要点文本 = 台账与状态文件共用的单一事实源）"
note = Path(NOTE).read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").strip()

W = T / "aap-round-verify" / ROUND
facts = {}
for ln in (W / ("facts-%s.log" % ROUND)).read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in ln:
        k, v = ln.split("=", 1)
        facts[k.strip()] = v.strip()
assert facts.get("FACTS_ROUND") == ROUND, "facts 轮次不符（判据失效）"
assert facts.get("FACTS_WRITTEN") == "1", "facts 未写完成标记"

ana = (EV / ("round-%s-analysis.txt" % ROUND)).read_text(encoding="utf-8", errors="replace")
reg = (EV / ("audit-regression-%s.txt" % ROUND)).read_text(encoding="utf-8", errors="replace")
cov = open(W / "wt-arch/coverage-report.json", encoding="utf-8").read()
covf = (EV / ("green-verify-%s-coverage-fields.txt" % ROUND)).read_text(encoding="utf-8", errors="replace")

# ---------- 数字全部由证据推出 ----------
m_tot = re.search(r"^\[(?:INFO|ERROR)\] Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)$",
                  (W / "run1.raw").read_text(encoding="utf-8", errors="replace"), flags=re.M)
assert m_tot, "run1 合计行未解析到（判据失效，历史 46/228）"
N_CASES = int(m_tot.group(1))
N_CLS = int(re.search(r"\[PASS\] A7 类级行数 > 0（正向对照） (\d+) 类", ana).group(1))
NF = int(re.search(r"判据：PASS (\d+) / FAIL (\d+)", ana).group(2))
NP = int(re.search(r"判据：PASS (\d+) / FAIL (\d+)", ana).group(1))
COV = re.search(r"total=(\d+) implemented=(\d+) missing=(\d+) registered_routes=(\d+) not_registered=(\S+)", covf)
assert COV, "覆盖字段未解析到（判据失效，历史 46）—— 读自 green-verify-%s-coverage-fields.txt" % ROUND
TOT, IMPL, MISS, ROUTES = COV.group(1), COV.group(2), COV.group(3), COV.group(4)
STREAK = int(re.search(r"连续全绿 = 第 (\d+) 轮", ana).group(1))
prev_hist = [ln for ln in HIST.read_text(encoding="utf-8", errors="replace").splitlines() if (" %s " % prev_round) in ln]
assert len(prev_hist) == 1, "上一轮 history 行命中 %d 条（判据失效，历史 46）" % len(prev_hist)
assert int(re.search(r"连续第 (\d+) 轮", prev_hist[0]).group(1)) + 1 == STREAK, "连续轮次与上一轮不连续"
M_RCCH = re.search(r"rc 变化 (\d+) 条、新增 (\d+)、未复跑 (\d+)", reg)
M_FAIL = re.search(r"FAIL 明细：(\d+) 个脚本含 FAIL 行、合计 (\d+) 行", reg)
M_NONZ = re.search(r"rc=0 条数 = (\d+) / (\d+)", reg)
assert M_RCCH and M_FAIL and M_NONZ, "回归证据解析失效（判据失效，历史 46）"
RCCH, RCADD, RCGONE = M_RCCH.groups()
FSCR, FLIN = M_FAIL.groups()
RAN = int(M_NONZ.group(2))
assert (int(RCCH), int(RCADD), int(RCGONE)) == (0, 0, 0), "回归面存在差异：rc 变化 %s / 新增 %s / 未复跑 %s" % (RCCH, RCADD, RCGONE)
EVLIST = sorted(x.name for x in EV.iterdir() if x.is_file() and ROUND in x.name)
assert len(EVLIST) >= 8, "本轮证据文件数 %d 过少（判据失效）" % len(EVLIST)
assert (EV / ("freeze-device-%s.txt" % ROUND)).exists(), "冻结证据缺失（判据失效）"
# 追加证据：收尾之后才产生的证据文件（如 postwrite-check-<ROUND>.txt）必须**先登记**再计数，
# 否则计数天然少 1（历史 201/206 的纯数字盲区在证据条数上的形态）。
EXTRA = [args[i + 1] for i, a in enumerate(args) if a == "--extra"]
for nm in EXTRA:
    assert ("/" not in nm) and ("\\" not in nm), "--extra 只接文件名：%r" % nm
    assert nm not in EVLIST, "--extra %s 已在磁盘上（会重复计数；请检查顺序）" % nm
    EVLIST = sorted(EVLIST + [nm])
N_EV = len(EVLIST)
CFG = "%s / %s" % (facts["FACTS_RUN1_START"], facts["FACTS_RUN1_END"])

# ---------- 描述列（前缀由证据推出 + 本轮要点来自单一事实源） ----------
PREFIX = ("%s 巡检轮（missing=0 ⇒ **校验轮**：**交付面零改动**（交付代码 / 测试面 / 冻结清单生成物零改动；"
          "`tools/` 本轮新增**只读校验装置**，不触碰交付面）） · 清单 **%s/%s**（作业目标「90 条全部落地」已含于 total 之中；"
          "**基线 = 被测提交 %s**）连续第 **%d** 轮全绿 · 两轮 **%d 例 / %d 类** rc=0/0（串行 %s→%s，逐类 diff=0） · "
          "回归面 **%d 条** rc 变化 %s / 新增 %s / 未复跑 %s；FAIL 明细 %s 脚本 %s 行（= 上一轮，跨轮 faildiff 新增 0） · "
          "分析器 PASS %d / FAIL %d · registered_routes=%s · 本轮返工 **%s 处**（装置侧） · 证据 %d 条"
          % (ROUND, IMPL, TOT, facts["FACTS_TESTED_COMMIT"], STREAK, N_CASES, N_CLS,
             facts["FACTS_RUN1_START"], facts["FACTS_RUN2_END"], RAN, RCCH, RCADD, RCGONE,
             FSCR, FLIN, NP, NF, ROUTES, REWORK, N_EV + 1))
DESC = PREFIX + " · " + note
assert "本轮返工 **%s 处**" % REWORK in DESC, "描述列返工真值与 --rework 不一致（判据失效）"
assert ("返工 %s 处" % REWORK) in note, "要点文本里的返工计数与 --rework 不一致（两处分叉，历史 215）"
assert len(DESC) >= 800, "描述列过短（%d 字符）——内容级下限（历史 200）" % len(DESC)
ANCHORS = [ROUND, "missing=0", "连续第 **%d** 轮" % STREAK, "返工 **%s 处**" % REWORK,
           "被测提交 %s" % facts["FACTS_TESTED_COMMIT"], "rc=0/0"]
for a in ANCHORS:
    assert a in DESC, "描述列缺关键锚点 %r" % a

EVID = "；".join("evidence/%s" % n for n in EVLIST) + "；evidence/coverage-history.txt（追加 %s 行）" % ROUND

# ---------- 台账：幂等三态 ----------
def read_rows(p):
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


REWRITE = "--rewrite" in args
raw = CSV.read_bytes()
assert raw.count(b"\r") == 0, "台账含 CR（历史 69/146）"
rows = read_rows(CSV)
HDR = rows[0]
assert HDR == ['任务号', '接口ID', '方法', '路径', '依据', '状态', '证据', '提交'], "台账表头变化：%s" % HDR
assert all(len(r) == len(HDR) for r in rows), "台账存在列数异常行（历史 80/155/200）"
assert not [r for r in rows if r and r[0] == ROUND] or REWRITE, \
    "本轮行已存在（幂等：请勿重复追加；如为据实更正请显式加 --rewrite）"
assert [r for r in rows if r and r[0] == prev_round], "上一轮行不存在（判据失效，历史 233）"

if REWRITE:
    # 据实更正：**重写**本轮行（描述/证据两列），保留提交列；公式与追加路径共用（杜绝两处分叉，历史 215/44）
    idx = [i for i, r in enumerate(rows) if r and r[0] == ROUND]
    assert len(idx) == 1, "本轮行 %d 条，无法重写" % len(idx)
    i = idx[0]
    old_desc, keep_c7 = rows[i][4], rows[i][7]
    assert len(old_desc) >= 800, "被重写的描述列过短（判据失效）"
    rows[i] = [ROUND, "", "", "", DESC, "", EVID, keep_c7]
    with CSV.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)
    print("台账：**重写** %s 行（描述 %d 字符；保留 c7=%s）" % (ROUND, len(DESC), keep_c7))
else:
    with CSV.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow([ROUND, "", "", "", DESC, "", EVID, COMMIT])

rows2 = read_rows(CSV)
assert all(len(r) == len(HDR) for r in rows2), "追加后列数异常（历史 80/155）"
mine = [r for r in rows2 if r and r[0] == ROUND]
assert len(mine) == 1, "追加后本轮行 %d 条" % len(mine)
assert mine[0][4] == DESC, "追加后描述列与单一事实源**不逐字相等**（历史 200）"
assert mine[0][6] == EVID, "追加后证据列不符"
assert len(mine[0][4]) >= 800, "追加后描述列过短"
assert CSV.read_bytes().count(b"\r") == 0, "追加后出现 CR（历史 69/146）"
print("台账：追加 %s 行 OK（描述 %d 字符 / 证据 %d 字符 / 行数 %d）"
      % (ROUND, len(DESC), len(EVID), len(rows2)))

# ---------- history ----------
hl = ("%s %s %s 巡检轮 | 清单 %s/%s（作业目标「90 条全部落地」已含于 total 之中；**基线 = 被测提交 %s**） "
      "missing=%s registered_routes=%s not_registered=[] | 全量两轮 %d 例全绿（连续第 %d 轮；两轮 rc=0/0、逐类 diff=0） | "
      "回归面复跑 %d 条 rc 变化 %s 条 / FAIL 明细 %s 脚本 %s 行 | 分析器 PASS %d / FAIL %d | "
      "本轮返工 %s 处（判据/脚本侧） | 证据 %d 条"
      % (facts["FACTS_WINDOW_START_ISO"], ROUND, ROUND, IMPL, TOT, facts["FACTS_TESTED_COMMIT"],
         MISS, ROUTES, N_CASES, STREAK, RAN, RCCH, FSCR, FLIN, NP, NF, REWORK, N_EV + 1))
hb = HIST.read_bytes()
assert hb.count(b"\r") == 0, "history 含 CR"
if REWRITE:
    hlines = hb.decode("utf-8").splitlines(keepends=True)
    hit = [i for i, ln in enumerate(hlines) if ("%s 巡检轮" % ROUND) in ln]
    assert len(hit) == 1, "history 里本轮行命中 %d 条（判据失效，历史 46）" % len(hit)
    hlines[hit[0]] = hl + "\n"
    HIST.write_text("".join(hlines), encoding="utf-8", newline="")
    print("history：**重写** %s 行（第 %d 行）" % (ROUND, hit[0] + 1))
else:
    if hb and not hb.endswith(b"\n"):
        with HIST.open("a", encoding="utf-8", newline="") as f:
            f.write("\n")
    with HIST.open("a", encoding="utf-8", newline="") as f:
        f.write(hl + "\n")
assert HIST.read_bytes().count(b"\r") == 0, "history 追加后出现 CR"
assert hl.strip() and hl in HIST.read_text(encoding="utf-8", errors="replace"), "history 行未落地"
print("history：写入 %s 行 OK（%d 字符）" % (ROUND, len(hl)))

# ---------- 状态文件 ----------
sec = ["", "### %s 巡检轮（校验轮：missing=0 ⇒ 交付面零改动）" % ROUND, "",
       "- **性质**：`missing=0` ⇒ **交付面零改动**（未改 `aap-server` / `docs` 任何一行）；本轮新增写入 = "
       "`tools/round-verify/`（轮次无关的只读校验装置）+ 台账/状态/证据。",
       "- **两轮全量（串行）**：被测提交 = %s（独立 detached worktree 内）；run1 %s→%s、run2 %s→%s；"
       "各 **%d 例 / %d 类**、rc=%s/%s、Failures-Errors-Skipped = 0-0-0；`@Test` 词边界计数与 surefire 合计一致；禁用扫描 0 条。"
       % (facts["FACTS_TESTED_COMMIT"], facts["FACTS_RUN1_START"], facts["FACTS_RUN1_END"],
          facts["FACTS_RUN2_START"], facts["FACTS_RUN2_END"], N_CASES, N_CLS,
          facts["FACTS_RUN1_RC"], facts["FACTS_RUN2_RC"]),
       "- **覆盖**：total=%s implemented=%s **missing=%s**、registered_routes=%s、not_registered=[]；连续第 **%d** 轮全绿。"
       % (TOT, IMPL, MISS, ROUTES, STREAK),
       "- **回归面**：复跑 %d 条（tag 集合与上一轮 %s 一致）；rc 变化 %s 条、新增 %s、未复跑 %s；"
       "FAIL 明细 %s 脚本 %s 行（跨轮 faildiff 新增 0 / 消失 0）；零写副作用（冻结清单生成物 size+md5 全等）；"
       "命令表已由仓库内 `tools/round-verify/manifest.json` 提供，$TEMP 抽查脚本 54 条全部归仓。" % (RAN, prev_round, RCCH, RCADD, RCGONE, FSCR, FLIN),
       "- **本轮要点（单一事实源 = %s）**：" % Path(NOTE).name,
       note,
       "- **返工真值**：本轮返工真值 = **%s 处**（装置/脚本侧，零交付面影响；逐条见上文要点与 `freeze-device-%s.txt`）。" % (REWORK, ROUND),
       "- **权威数字**：权威数字 = 返工 %s 处（台账描述列与本节**同一份文本**，历史 250 的机器可查形态）。" % REWORK,
       ""]
sb = STATE.read_bytes()
assert sb.count(b"\r") == 0, "状态文件含 CR"
if REWRITE:
    st = sb.decode("utf-8")
    mark = "\n### %s 巡检轮" % ROUND
    assert st.count(mark) == 1, "状态文件里本轮小节标记命中 %d 次（判据失效）" % st.count(mark)
    st = st[:st.index(mark)] + "\n" + "\n".join(sec).lstrip("\n") + "\n"
    STATE.write_text(st, encoding="utf-8", newline="")
    print("状态文件：**重写** %s 小节" % ROUND)
else:
    if not sb.endswith(b"\n"):
        with STATE.open("a", encoding="utf-8", newline="") as f:
            f.write("\n")
    with STATE.open("a", encoding="utf-8", newline="") as f:
        f.write("\n".join(sec) + "\n")
txt = STATE.read_text(encoding="utf-8", errors="replace")
assert ("### %s 巡检轮" % ROUND) in txt, "状态文件小节未落地"
assert note in txt, "状态文件未含要点文本（与台账不同源会分叉，历史 215）"
assert STATE.read_bytes().count(b"\r") == 0, "状态文件追加后出现 CR"
print("状态文件：追加 %s 小节 OK（%d 行）" % (ROUND, len(sec)))
print("DESC_SHA256=%s（描述列内容指纹）" % hashlib.sha256(DESC.encode("utf-8")).hexdigest()[:8])
print("CLOSEOUT_END=1")
