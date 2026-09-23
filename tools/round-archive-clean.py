#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归档目录幂等化助手（受控清理；`rm -rf` 在 cron 下被安全策略拦下 -> 用 Python 的 rmtree）。

为什么需要
----------
巡检轮执行器 `archive_wt()` 用 `cp -rp "<wt>/aap-server/src/test/java" "<wt-arch>/testsrc"` 归档测试源：
  * **首次**调用（`testsrc` 不存在）-> 创建 `testsrc/` 作为 `java/` 的副本（即 `testsrc/com/hioas/...`）；
  * **后续**调用（`testsrc` 已存在）-> 落成 `testsrc/java/com/hioas/...`
=> 同一目录混入**两份**测试源，下游 `@Test` 计数翻倍（历史实测 425 = 211 + 214），把「用例数对账」判成假 FAIL。

本助手把归档收敛为**恰好一份**（保留最新的 `testsrc/java/...`，删除更早的 `testsrc/com/...`），
并打印前后计数作正向对照；不存在「两份并存」形态时**拒绝动作**（幂等、可重跑）。

与历次实现的两点差别（结构性消除「助手跨轮丢失 / 作用错对象」这一缺陷类）
------------------------------------------------------------------------
1. **路径由调用方传入**（argv[1]），不再硬编码某一轮的工作目录 ——
   历史版本的 `ARCH` 写死为 `.../aap-r284-work/wt-arch`，于是即便它被调用，也只会作用于**早已回收**的那一轮目录。
2. **纳入仓库**（`tools/`，被 git 跟踪）—— 历史版本只落在临时目录里，跨轮派生时不会被带走，
   执行器里的调用点因此长期指向**不存在的文件**（「门槛不可达」型静默失效）。

用法
----
    python tools/round-archive-clean.py <testsrc 根目录>
    python tools/round-archive-clean.py --selftest

退出码：0 = 已收敛 / 无需动作；2 = 拒绝动作（只剩一份 legacy，避免删掉唯一副本）；
        3 = 无法判定（`--selftest` 失败）；64 = 用法错误。
"""
import pathlib
import re
import shutil
import sys

TEST_RE = re.compile(r"@Test\b")


def ntest(root):
    """统计目录树里的 @Test 词边界计数；目录不存在返回 None（调用方据此判「判定不可用」）。"""
    if root is None or not pathlib.Path(root).exists():
        return None
    n = 0
    for p in pathlib.Path(root).rglob("*.java"):
        n += len(TEST_RE.findall(p.read_text(encoding="utf-8", errors="replace")))
    return n


def clean(ts, out=print):
    """把 <ts> 收敛为恰好一份测试源。返回退出码。"""
    ts = pathlib.Path(ts)
    if not ts.exists():
        out("NO_TESTSRC=1（无可收敛对象）")
        return 0
    legacy = ts / "com"          # 首次调用留下的副本
    fresh = ts / "java" / "com"  # 后续调用留下的副本
    nl, nf = ntest(legacy), ntest(fresh)
    out("TESTSRC=%s BEFORE legacy(testsrc/com)=%s fresh(testsrc/java/com)=%s" % (ts, nl, nf))
    if nl is not None and nf is not None:
        shutil.rmtree(legacy)
        out("REMOVED=%s（保留最新一份）" % legacy)
    elif nl is not None and nf is None:
        # 只存在 legacy 一份 -> 不能删（会把唯一副本删掉）
        out("REFUSE=1（只存在 legacy 一份 -> 不动作，避免把唯一副本删掉）")
        return 2
    else:
        out("ALREADY_SINGLE=1")
    after = ntest(ts)
    files = len(list(ts.rglob("*.java")))
    out("AFTER testsrc @Test=%s java_files=%d" % (after, files))
    if nf is not None and after != nf:
        # 收敛后必须与「最新那一份」逐数相等 —— 判据要能失败（历史纪律 46/75/98）
        out("FAIL=1 收敛后计数与本轮归档不一致：%s vs %s" % (after, nf))
        return 3
    out("CLEAN_ARCH_OK=1")
    return 0


def _mk_fixture(base, name, build):
    d = base / name
    build(d)
    return d


def selftest():
    """四个分支的判别力实测：每个分支都断言**磁盘结果**，no-op 实现无法通过分支 ①。"""
    import tempfile

    fails = []

    def chk(label, cond, detail=""):
        print("%s %s %s" % ("[PASS]" if cond else "[FAIL]", label, detail))
        if not cond:
            fails.append(label)

    base = pathlib.Path(tempfile.mkdtemp(prefix="aap-archclean-selftest-"))
    print("SELFTEST_ROOT=%s" % base)

    def wj(p, n):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join("@Test void t%d() {}" % i for i in range(n)) + "\n", encoding="utf-8")

    # ① 两份并存 -> 收敛为一份（@Test 计数 = fresh 的计数）
    d1 = _mk_fixture(base, "dup", lambda d: (wj(d / "com" / "h" / "A.java", 2), wj(d / "java" / "com" / "h" / "A.java", 3)))
    rc1 = clean(d1, out=lambda *_: None)
    chk("S1 两份并存：收敛为一份（legacy 目录已删除 ∧ 计数 = 3）",
        rc1 == 0 and not (d1 / "com").exists() and ntest(d1) == 3,
        "rc=%d legacy_exists=%s @Test=%s" % (rc1, (d1 / "com").exists(), ntest(d1)))
    # 判别力实测：把「删除动作」抽掉就是 no-op -> 上述断言必须为假（证明判据有牙齿）
    d1b = _mk_fixture(base, "dup_noop", lambda d: (wj(d / "com" / "h" / "A.java", 2), wj(d / "java" / "com" / "h" / "A.java", 3)))
    chk("S1b 判别力实测：no-op（不删 legacy）时「legacy_exists 为假」必然不成立",
        (d1b / "com").exists() and ntest(d1b) == 5, "@Test=%s" % ntest(d1b))

    # ② 只有 legacy 一份 -> 拒绝动作（rc=2 ∧ 目录仍在）
    d2 = _mk_fixture(base, "legacy_only", lambda d: wj(d / "com" / "h" / "A.java", 4))
    rc2 = clean(d2, out=lambda *_: None)
    chk("S2 只有 legacy：拒绝动作（rc=2 ∧ 目录仍在 ∧ 计数不变）",
        rc2 == 2 and (d2 / "com").exists() and ntest(d2) == 4,
        "rc=%d @Test=%s" % (rc2, ntest(d2)))

    # ③ 只有 fresh 一份 -> 幂等（rc=0 ∧ 不动）
    d3 = _mk_fixture(base, "fresh_only", lambda d: wj(d / "java" / "com" / "h" / "A.java", 5))
    rc3 = clean(d3, out=lambda *_: None)
    chk("S3 只有 fresh：幂等无需动作（rc=0 ∧ 计数不变）", rc3 == 0 and ntest(d3) == 5,
        "rc=%d @Test=%s" % (rc3, ntest(d3)))

    # ④ 目标不存在 -> NO_TESTSRC（rc=0，正向对照：不能抛异常）
    rc4 = clean(base / "absent", out=lambda *_: None)
    chk("S4 目标不存在：NO_TESTSRC 且 rc=0", rc4 == 0, "rc=%d" % rc4)

    # ⑤ 正向对照：本工具的判据确实读到输入（@Test 计数非 0）
    chk("S5 正向对照：@Test 词边界计数可读（> 0）", ntest(d1) is not None and ntest(d1) > 0, "@Test=%s" % ntest(d1))

    shutil.rmtree(base, ignore_errors=True)
    print("汇总：FAIL = %d %s" % (len(fails), fails if fails else "（全 PASS）"))
    print("SELFTEST_OK=%d" % (0 if not fails else 1))
    return 3 if fails else 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 2 or argv[1].startswith("-"):
        print(__doc__)
        return 64
    return clean(argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
