#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账「提交」列回填（**轮次无关**：`python tools/round-verify/backfill-c7.py <轮次> <主提交短号>`）。

为什么在装置里（历史 169/177 的又一次消除）：
  * 本步在 `README.md` 的巡检轮流程里是第 ⑥ 步，但装置此前**没有对应工具** —— 每轮都现写一份脚本、
    只活在 `$TEMP`，随系统清理即永久退场；
  * 首个临时版用 `raw.decode().splitlines()` 取行再交给 `csv.reader`：**字段内的内嵌换行会被吃掉**
    （`splitlines` 去掉行终止符，list 输入不会补回）⇒ 实测把两条**历史记录**（含内嵌换行的行）的换行删掉，
    `git diff --numstat` 报 3 插入 / 5 删除（正常应为 1 / 1）—— 改动落到**非本轮行**上（历史 80/155/169）。

本工具 = 结构性消除（轮次号由参数给出、基准来自 git、验收是内容级的）：
  * 基准 = `git show HEAD:<台账>`（回填发生在主提交之后，HEAD 内的本轮行 c7 必为空）；
  * **写入前**先做「工作区 ⇔ 基准」逐记录逐列比对（`csv.reader` 走文件对象，内嵌换行随行保留）；
    只允许「本轮行的 c7」这一处差异 —— 其它任何差异都是响亮失败，且**绝不改写文件**（零副作用）；
  * **写入后**再做内容级验收：差异集合恰为 `{(轮次, 提交)}`、记录数 / 物理行数 / 含内嵌换行的记录数三连守恒、CR = 0、
    描述列逐字符不变；
  * 主提交短号必须**真的存在**且**是 HEAD 的祖先**（`git merge-base --is-ancestor`，历史 200-②），
    传错号（如传收尾提交号）当场失败，失败信息区分「号不存在」与「号不是 HEAD 的祖先」。

用法：
  python tools/round-verify/backfill-c7.py <轮次> <主提交短号>          # 生产路径
  python tools/round-verify/backfill-c7.py --selftest                  # 负向自测（合成夹具，零接触仓库）
  python tools/round-verify/backfill-c7.py <轮次> <短号> --csv <f> --baseline <f>   # 夹具路径（自测用）

为什么**不**进 `manifest.json` 回归面：它是**写盘器**（改台账），而回归面复跑必须在零写副作用的前提下只读
（`regression.py` 有「生成物 size+md5 全等」判据）—— 把写盘器放进回归面会把台账改坏。
"""
import csv
import hashlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
CSV_REL = ".agents/state/aap-server-feature-status.csv"
HDR_WANT = ['任务号', '接口ID', '方法', '路径', '依据', '状态', '证据', '提交']


def parse_bytes(b):
    return list(csv.reader(io.StringIO(b.decode("utf-8"), newline="")))


def n_embedded(rows):
    return sum(1 for r in rows if any(("\n" in c or "\r" in c) for c in r))


def n_lines(b):
    return b.decode("utf-8").count("\n")


def cells_diff(base_rows, rows, hdr):
    """返回差异集合 {(行标识, 列名)} —— 判据用**列名**而不是列号（可读、可与语义对齐）。"""
    d = set()
    if len(base_rows) != len(rows):
        d.add(("<记录数>", "记录数"))
        return d
    for k in range(len(base_rows)):
        for j in range(len(hdr)):
            a = base_rows[k][j] if j < len(base_rows[k]) else None
            b = rows[k][j] if j < len(rows[k]) else None
            if a != b:
                d.add((base_rows[k][0] or rows[k][0], hdr[j]))
    return d


def apply(round_, sha, csv_path, base_bytes, write=True):
    """回填本轮行 c7。返回 (rc, [消息行], 结果摘要 dict)。任何失败都在写盘之前返回（零副作用）。"""
    msgs, res = [], {}
    base_rows = parse_bytes(base_bytes)
    if not base_rows:
        return 2, ["[FAIL] 基准不可读（判据失效）"], res
    hdr = base_rows[0]
    if hdr != HDR_WANT:
        return 2, ["[FAIL] 表头与预期不符：%s" % hdr], res
    for tag, rows in (("基准", base_rows),):
        if any(len(r) != len(hdr) for r in rows):
            return 2, ["[FAIL] %s 存在列数异常行（历史 80/155/200）" % tag], res
    b_mine = [r for r in base_rows if r and r[0] == round_]
    if len(b_mine) != 1:
        return 2, ["[FAIL] 基准内 %s 行 %d 条（判据失效）" % (round_, len(b_mine))], res
    if b_mine[0][7] != "":
        return 2, ["[FAIL] 基准内 %s 行 c7 非空（%r）—— 回填顺序不对（须在主提交之后）"
                   % (round_, b_mine[0][7])], res
    cur_bytes = Path(csv_path).read_bytes()
    cur_rows = parse_bytes(cur_bytes)
    if any(len(r) != len(hdr) for r in cur_rows):
        return 1, ["[FAIL] 工作区台账存在列数异常行（历史 80/155/200）"], res
    w_mine = [r for r in cur_rows if r and r[0] == round_]
    if len(w_mine) != 1:
        return 2, ["[FAIL] 工作区 %s 行 %d 条（判据失效）" % (round_, len(w_mine))], res
    if w_mine[0][7] != "":
        return 1, ["[FAIL] 工作区 %s 行 c7 非空（%r）—— 回填顺序不对 / 疑似重复回填（历史 200-②）"
                   % (round_, w_mine[0][7])], res
    if len(cur_rows) != len(base_rows):
        return 1, ["[FAIL] 记录数 基准 %d -> 工作区 %d（判定：splitlines 类截断，历史 80/155）"
                   % (len(base_rows), len(cur_rows))], res
    pre = cells_diff(base_rows, cur_rows, hdr)
    if pre:
        return 1, ["[FAIL] 工作区与本轮基准存在差异 %s —— 拒绝改写（非本轮行不得被动，历史 81/198）"
                   % sorted(pre)], res
    res["base_lines"] = n_lines(base_bytes)
    res["base_embedded"] = n_embedded(base_rows)
    res["base_desc"] = b_mine[0][4]
    idx = [i for i, r in enumerate(cur_rows) if r and r[0] == round_][0]
    cur_rows[idx][7] = sha
    if not write:
        res["rows"] = cur_rows
        return 0, msgs, res
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(cur_rows)
    Path(csv_path).write_text(buf.getvalue(), encoding="utf-8", newline="")
    new_bytes = Path(csv_path).read_bytes()
    new_rows = parse_bytes(new_bytes)
    fails = []
    d = cells_diff(base_rows, new_rows, hdr)
    if d != {(round_, "提交")}:
        fails.append("写入后差异集合异常 %s（只允许本轮行的提交列，历史 200-②）" % sorted(d))
    if n_lines(new_bytes) != n_lines(base_bytes):
        fails.append("物理行数 %d -> %d（须守恒）" % (n_lines(base_bytes), n_lines(new_bytes)))
    if n_embedded(new_rows) != n_embedded(base_rows):
        fails.append("含内嵌换行的记录数 %d -> %d（须守恒，历史 80/155）"
                     % (n_embedded(base_rows), n_embedded(new_rows)))
    if new_bytes.count(b"\r"):
        fails.append("出现 CR（历史 69/146）")
    if any(len(r) != len(hdr) for r in new_rows):
        fails.append("列数异常行（历史 80/155/200）")
    n_mine = [r for r in new_rows if r and r[0] == round_]
    if len(n_mine) != 1 or n_mine[0][4] != res["base_desc"]:
        fails.append("本轮行描述列被改动或行数异常")
    res["new_lines"] = n_lines(new_bytes)
    res["new_embedded"] = n_embedded(new_rows)
    res["sha256_12"] = hashlib.sha256(new_bytes).hexdigest()[:12]
    if fails:
        return 1, ["[FAIL] %s" % f for f in fails], res
    return 0, msgs, res


# ---------------- 生产路径 ----------------
def git(*a):
    return subprocess.run(["git", "-C", str(ROOT)] + list(a), capture_output=True)


def run_production(round_, sha):
    rc, out, err = git("cat-file", "-e", sha + "^{commit}")
    if rc != 0:
        print("[FAIL] 提交号不存在：%s（%s）" % (sha, err.decode("utf-8", "replace").strip()))
        return 2
    anc = git("merge-base", "--is-ancestor", sha, "HEAD")
    if anc.returncode != 0:
        print("[FAIL] %s 不是 HEAD 的祖先 —— 传错号（勿传收尾提交号，历史 200-②）" % sha)
        return 2
    base = git("show", "HEAD:" + CSV_REL)
    assert base.returncode == 0, "取 HEAD 内台账失败：%s" % base.stderr.decode("utf-8", "replace")
    rc, msgs, res = apply(round_, sha, ROOT / CSV_REL, base.stdout, write=True)
    for m in msgs:
        print(m)
    if rc:
        return rc
    print("STATE=已回填 c7=%s（只动本轮行的提交列；其余行逐列不变）" % sha)
    print("记录守恒 / 物理行 %d -> %d / 含内嵌换行记录 %d -> %d / CR %d / 差异集合 [(%s, 提交)] / 台账 sha256=%s"
          % (res["base_lines"], res["new_lines"], res["base_embedded"], res["new_embedded"],
             (ROOT / CSV_REL).read_bytes().count(b"\r"), round_, res["sha256_12"]))
    print("BACKFILL_END=1")
    return 0


# ---------------- 负向自测（合成夹具；零接触仓库） ----------------
FIX_HDR = "任务号,接口ID,方法,路径,依据,状态,证据,提交\n"
R = "R999"
SHA = "0abc123"


def fixture(kind):
    """kind: happy / foreign / c7nonempty / truncated / no_row。返回 (基准 bytes, 工作区 bytes)"""
    body_a = '%s,,,,%s,"状态 A 第一段\n状态 A 第二段",evidence/a.txt,\n' % (R, "描述" + "字" * 800)
    other = 'R998,,,,,,evidence/b.txt,deadbee\n'
    base = (FIX_HDR + other + body_a).encode("utf-8")
    if kind == "happy":
        return base, base
    if kind == "foreign":
        w = base.replace(b"deadbee", b"cafebabe")
        return base, w
    if kind == "c7nonempty":
        w = base.replace(b"evidence/a.txt,\n", b"evidence/a.txt,9999999\n")
        return base, w
    if kind == "truncated":
        # 工作区少一条**非本轮**记录（splitlines 类损坏的等效形态；本轮行仍在）
        return base, (FIX_HDR.encode("utf-8") + body_a.encode("utf-8"))
    if kind == "no_row":
        return base, (FIX_HDR + other).encode("utf-8")
    raise AssertionError(kind)


def run_selftest():
    fails, passes = [], []

    def chk(name, cond, detail=""):
        (passes if cond else fails).append(name)
        print("[%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))

    tmp = Path(tempfile.mkdtemp(prefix="aap-backfill-selftest-"))
    f = tmp / "ledger.csv"
    # 正向对照：夹具真的含内嵌换行（否则「守恒」判据是空转）
    b, _ = fixture("happy")
    chk("A0a 夹具含内嵌换行记录数 >= 1（正向对照）", n_embedded(parse_bytes(b)) == 1,
        "实测 %d" % n_embedded(parse_bytes(b)))
    # A 正常回填
    b, w = fixture("happy")
    f.write_bytes(w)
    rc, msgs, res = apply(R, SHA, f, b, write=True)
    nb = f.read_bytes()
    chk("A1 正常回填 rc == 0", rc == 0, "rc=%d %s" % (rc, msgs))
    chk("A2 回填后 c7 == 提交短号", [r for r in parse_bytes(nb) if r[0] == R][0][7] == SHA)
    chk("A3 差异集合恰为 {(轮次, 提交)}",
        cells_diff(parse_bytes(b), parse_bytes(nb), HDR_WANT) == {(R, "提交")})
    chk("A4 内嵌换行守恒", n_embedded(parse_bytes(nb)) == n_embedded(parse_bytes(b)),
        "%d -> %d" % (n_embedded(parse_bytes(b)), n_embedded(parse_bytes(nb))))
    chk("A5 物理行数守恒", n_lines(nb) == n_lines(b), "%d -> %d" % (n_lines(b), n_lines(nb)))
    # B 非本轮行有差异 -> 响亮失败且不改文件（这就是首个临时版踩的坑）
    b, w = fixture("foreign")
    f.write_bytes(w)
    before = f.read_bytes()
    rc, msgs, _ = apply(R, SHA, f, b, write=True)
    chk("B1 非本轮差异 rc != 0", rc != 0, "rc=%d" % rc)
    chk("B2 失败信息点名该行", any("R998" in m for m in msgs), msgs[0][:90] if msgs else "")
    chk("B3 零副作用（文件字节不变）", f.read_bytes() == before)
    # C c7 非空 -> 顺序错，响亮失败
    b, w = fixture("c7nonempty")
    f.write_bytes(w)
    before = f.read_bytes()
    rc, msgs, _ = apply(R, SHA, f, b, write=True)
    chk("C1 c7 非空 rc != 0", rc != 0, "rc=%d" % rc)
    chk("C2 失败信息指 c7", any("c7" in m for m in msgs), msgs[0][:90] if msgs else "")
    chk("C3 零副作用（文件字节不变）", f.read_bytes() == before)
    # D 记录数塌陷（splitlines 类损坏）-> 失败
    b, w = fixture("truncated")
    f.write_bytes(w)
    before = f.read_bytes()
    rc, msgs, _ = apply(R, SHA, f, b, write=True)
    chk("D1 记录数不一致 rc != 0", rc != 0, "rc=%d" % rc)
    chk("D2 零副作用（文件字节不变）", f.read_bytes() == before, msgs[0][:70] if msgs else "")
    # E 本轮行缺失 -> 判据失效（rc=2）
    b, w = fixture("no_row")
    f.write_bytes(w)
    rc, msgs, _ = apply(R, SHA, f, b, write=True)
    chk("E1 本轮行缺失 rc == 2（判据失效）", rc == 2, "rc=%d" % rc)
    # F 反向对照：跨轮次号不得误伤（夹具里 R998 行的 c7 保持原值）
    b, w = fixture("happy")
    f.write_bytes(w)
    apply(R, SHA, f, b, write=True)
    chk("F1 其它轮次行逐列不变", [r for r in parse_bytes(f.read_bytes()) if r[0] == "R998"][0][7] == "deadbee")
    print("判据：PASS %d / FAIL %d" % (len(passes), len(fails)))
    print("SELFTEST_END=1" if not fails else "SELFTEST_FAIL=%s" % fails)
    return 1 if fails else 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        return run_selftest()
    if len(args) < 2 or not args[0].upper().startswith("R"):
        print("用法: python tools/round-verify/backfill-c7.py <轮次> <主提交短号> | --selftest")
        return 2
    return run_production(args[0].upper(), args[1])


if __name__ == "__main__":
    sys.exit(main())
