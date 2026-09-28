#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""相位（green / red）**单一事实源**（轮次无关；`python tools/round-verify/phase.py --selftest`）。

为什么有它
----------
巡检轮在「冻结清单被扩到 > implemented」的相位下**必然为红**（覆盖门禁要求 N/N 注册），
而装置此前只按「全绿相位」写产物与台账 ⇒ 红轮只有两条路：① 不记账（下一轮 `analyze.py` 的 A22
因「上一轮 history 行 0 条」**响亮失败**，作业自此死锁）；② 记账但写出「missing=0 / 连续第 N 轮全绿 /
rc=0/0」的**假绿行**（历史 12/95：证据文件名与内容都不得骗人）。两条都不可接受。

本模块把「相位」的判定与命名集中到一处，供 `analyze.py` / `closeout.py` / `device-report.py` /
`final-check.py` / `independent.py` 共用（历史 44/191：同一口径两处副本必然分叉，且「必须为空」型
守卫口径过期反而更「合规」= 空转假绿，历史 98/187）。

判据（**三判据全满足才算绿**，缺一即为红）
------------------------------------------
  ① 两轮 `rc == 0`；② 覆盖 `missing == 0`。

命名纪律
--------
红轮的产物**不得**叫 `green-verify-*`（历史 12：文件名不能骗人）⇒ 前缀由 `ev_prefix()` 推出，
产出侧与消费侧**共用**同一函数（历史 181：写入格式 ⇔ 读取判据双向一致）。

台账/历史的红相位记账口径（三条，缺一不可）
--------------------------------------------
  * 描述列 / history 行 / 状态小节**都不得**出现「连续第 N 轮全绿」与「rc=0/0」；
  * 三处**都**写 `连续全绿计数 = <N>（红相位…）`，且 N == 0（**计数清零**：下一次全绿从第 1 轮起算）；
  * 三处**都**写 `红相位` 标记 —— 下一轮的 A22/closeout 靠它区分「上一轮是红轮」与「上一轮的 history 行丢了」。
"""
import re
import sys

GREEN = "green"
RED = "red"
RED_MARK = "红相位"                  # 三处（描述列 / history / 状态小节）必须同时出现的标记
STREAK_KW = "连续全绿计数"           # 红相位的轮次计数写法（与绿相位的「连续第 N 轮」互斥）


def phase_of(rc1, rc2, missing):
    """三判据：两轮 rc=0 ∧ missing=0。参数可以是 str/int（facts 里都是 str）。"""
    return GREEN if (int(rc1) == 0 and int(rc2) == 0 and int(missing) == 0) else RED


def ev_prefix(phase):
    """证据文件前缀：**文件名不得骗人**（历史 12）。"""
    return "green-verify" if phase == GREEN else "red-verify"


def verify_names(round_, phase):
    """本相位下 `analyze.py` 落盘的 5 条校验证据（产出侧定义；消费侧一律用 `find_*`）。"""
    p = ev_prefix(phase)
    return ["%s-%s-coverage-fields.txt" % (p, round_),
            "%s-%s-testcount.txt" % (p, round_),
            "%s-%s-tested-state.txt" % (p, round_),
            "%s-%s-full-run1.txt" % (p, round_),
            "%s-%s-full-run2.txt" % (p, round_)]


def find_verify(ev_dir, round_, stem):
    """消费侧：两种前缀都认（返回 Path 或 None）。`stem` 如 'coverage-fields'。"""
    from pathlib import Path
    ev = Path(ev_dir)
    for ph in (GREEN, RED):
        q = ev / ("%s-%s-%s.txt" % (ev_prefix(ph), round_, stem))
        if q.exists():
            return q
    return None


def state_section_mark(state_path, prev):
    """上一轮「红相位未记账」的唯一机器判据：状态文件里存在 `### <PREV> ` 小节、且其标题含「红」。

    返回 `(命中小节数, 是否为合法的红相位小节)`。`analyze.py`（A22）与 `closeout.py`（上一轮行前置）
    共用本函数 —— 两处各自实现会让同一事实有两种判据（历史 44/191）。
    """
    from pathlib import Path
    p = Path(state_path)
    if not p.exists():
        return (0, False)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    mk = [i for i, ln in enumerate(lines) if ln.startswith("### %s " % prev)]
    return (len(mk), len(mk) == 1 and ("红" in lines[mk[0]]))


def streak_marker(phase, streak):
    """描述列里的轮次**锚点式**（绿 / 红互斥；`final-check.py` 的 F7 锚点据此推出）。

    红相位**故意不含右括号**：文案后缀（`（红相位**计数清零**，下次全绿从第 1 轮起算）`）会变，
    锚点耦合后缀会让「改文案」变成「改判据」（历史 217-③：锚点取正文，不要绑文案后缀）。
    """
    return ("连续第 **%s** 轮" % streak) if phase == GREEN else ("%s = **%s**（%s" % (STREAK_KW, streak, RED_MARK))


def streak_pat(phase):
    """`final-check.py` F10 的「轮次」三元组模式：三处（描述 / history / 状态）共用同一模式。"""
    if phase == GREEN:
        return r"连续第 (?:\*\*)?(\d+)(?:\*\*)? 轮"
    return r"%s = (?:\*\*)?(\d+)" % STREAK_KW


def cases_pat():
    """用例数三元组模式：`全量两轮 N 例全绿` 与红相位的 `全量两轮 N 例**红相位**` 共用同一前缀。"""
    return r"全量两轮 (\d+) 例"


# ---------------------------------------------------------------- 判别力自测
def selftest():
    res = []

    def chk(name, cond, info=""):
        res.append((name, bool(cond), info))

    # P1 三判据：两轮 rc=0 且 missing=0 才绿
    chk("P1 三判据合取（rc=0/0 ∧ missing=0 ⇒ green）", phase_of(0, 0, 0) == GREEN, phase_of(0, 0, 0))
    # P2 逐条反例：任一判据不满足即红（三条反例，历史 32：判定有几个分支就要有几条反例）
    chk("P2a 反例：run1 rc!=0 ⇒ red", phase_of(1, 0, 0) == RED, phase_of(1, 0, 0))
    chk("P2b 反例：run2 rc!=0 ⇒ red", phase_of(0, 1, 0) == RED, phase_of(0, 1, 0))
    chk("P2c 反例：missing>0 ⇒ red", phase_of(0, 0, 9) == RED, phase_of(0, 0, 9))

    # P3 命名：红轮前缀不得等于绿轮（历史 12）
    chk("P3 红相位前缀 != 绿相位前缀", ev_prefix(RED) != ev_prefix(GREEN), "%s / %s" % (ev_prefix(RED), ev_prefix(GREEN)))
    chk("P3b 绿相位 5 条名字全部以 green-verify 开头",
        all(n.startswith("green-verify-") for n in verify_names("R900", GREEN)), verify_names("R900", GREEN)[0])
    chk("P3c 红相位 5 条名字全部以 red-verify 开头（且不含 green）",
        all(n.startswith("red-verify-") and "green" not in n for n in verify_names("R900", RED)), verify_names("R900", RED)[0])

    # P4 轮次标记：两相位互斥（判据不得跨相位假命中）
    g, r = streak_marker(GREEN, 476), streak_marker(RED, 0)
    chk("P4a 绿相位标记可被绿模式命中", re.search(streak_pat(GREEN), g) is not None, g)
    chk("P4b 红相位标记**不**被绿模式命中（互斥）", re.search(streak_pat(GREEN), r) is None, r)
    chk("P4c 红相位标记可被红模式命中", re.search(streak_pat(RED), r) is not None, r)
    chk("P4d 绿相位标记**不**被红模式命中（互斥）", re.search(streak_pat(RED), g) is None, g)

    # P5 红相位不得出现绿相位的两个关键词（三处同源判据的前提；合成反例证明守卫有牙齿）
    chk("P5a 合成绿行被「不得含绿相位措辞」判据抓出",
        ("连续第 3 轮全绿" in "…连续第 3 轮全绿…") and (RED_MARK not in "…连续第 3 轮全绿…"))
    chk("P5b 合成红行同时含 RED_MARK 与计数关键词", (RED_MARK in r) and (STREAK_KW in r), r)

    # P6 用例数模式两相位共用（绿行 `全量两轮 305 例全绿` / 红行 `全量两轮 305 例**红相位**`）
    chk("P6a 绿行用例数可解析", re.search(cases_pat(), "全量两轮 305 例全绿") is not None)
    chk("P6b 红行用例数可解析", re.search(cases_pat(), "全量两轮 305 例**红相位**") is not None)

    # P7 空输入不得判绿（历史 98：`all([])` 型空转假绿）；配正向对照证明探针非空转
    chk("P7a 空/畸形输入必须响亮失败而非判绿（判据不可用 ≠ 绿）", _empty_not_green())
    chk("P7b 探针正向对照：同一探针的合法输入路径上给出相反结论", _green_probe())

    ok = sum(1 for _, c, _ in res if c)
    for name, c, info in res:
        print("  [%s] %s%s" % ("PASS" if c else "FAIL", name, (" " + info) if info else ""))
    print("  判据：PASS %d / FAIL %d" % (ok, len(res) - ok))
    print("PHASE_SELFTEST_END=1")
    return 0 if ok == len(res) else 1


def _empty_not_green():
    """空/畸形输入必须**响亮失败**而不是被当成绿（判据不可用 ≠ 绿）。"""
    try:
        phase_of("", "", "")
    except ValueError:
        return True
    return False


def _green_probe():
    """正向对照：同一条探针在**合法输入**上判绿（证明 P7a 不是「恒真」的探针）。"""
    return phase_of(0, 0, 0) == GREEN


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("用法: python tools/round-verify/phase.py --selftest")
    sys.exit(2)
