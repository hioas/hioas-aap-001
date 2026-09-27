#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R69 抽查脚本的负向自测（spotcheck-pagination-R69.py）。

覆盖每个判定分支 + 正向对照 + 注入缺陷判别力 + 零写副作用。
纪律（均为真实返工）：① 每条注入都要断言「锚点真的命中、源码真的被改」（坑 66/90/94）；
② FAIL 集合按**断言前缀**比对，且写成「先跑基线，再断言恰好新增目标断言」（坑 82/93）；
③ 空夹具必须变红并点名全部 A0*（坑 98/132）；④ 夹具与脚本目录分开（坑 106）；
⑤ 基线变量另起名（坑 93）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
SCRIPT = Path("C:/Users/laitz/AppData/Local/Temp/aap-r69-spotcheck/spotcheck-pagination-R69.py")
FX = Path("C:/Users/laitz/AppData/Local/Temp/aap-r69-spotcheck-fixtures")
FAIL_RE = re.compile(r"^\[FAIL\s*\]\s+(\S+)")
PASS_RE = re.compile(r"^\[PASS\s*\]\s+(\S+)")

SVC = '''package demo;

import java.util.ArrayList;
import java.util.List;

public class Svc {
    private final JdbcTemplate jdbc = null;

    /** 分页站点 1：谓词变量同源 + 参数派生。 */
    public Object page(String status, Integer page, Integer pageSize) {
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        if (status != null) {
            where.append(" and upper(status) = upper(?)");
            args.add(status);
        }
        Long total = jdbc.queryForObject("select count(*) from aap_demo" + where, Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(pageSize);
        pageArgs.add((page - 1) * pageSize);
        List<Object> items = jdbc.query("select id from aap_demo" + where + " order by id desc limit ? offset ?",
                Svc::map, pageArgs.toArray());
        return PageResult.of(items, page, pageSize, total == null ? 0L : total);
    }

    /** 分页站点 2：保持 A0b/A0d 正向对照在注入后仍 > 0（坑 136 第二来源兜底）。 */
    public Object page2(Integer page, Integer pageSize) {
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        Long total2 = jdbc.queryForObject("select count(*) from aap_demo2" + where, Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(pageSize);
        pageArgs.add((page - 1) * pageSize);
        List<Object> items = jdbc.query("select id from aap_demo2" + where + " order by id desc limit ? offset ?",
                Svc::map, pageArgs.toArray());
        return PageResult.of(items, page, pageSize, total2 == null ? 0L : total2);
    }

    /** 非分页计数（保证 A0c 正向对照在注入后仍 > 0）。 */
    public long countOnly(Long id) {
        return jdbc.queryForObject("select count(*) from aap_demo where id = ? and deleted = false", Long.class, id);
    }
}
'''

CTL = '''package demo;

import java.util.List;

public class Ctl {
    private final Svc svc = null;

    public Object list(Object principal, String result, Integer page, Integer pageSize) {
        List<Object> items = svc.list(principal, page, pageSize, result);
        return PageResult.of(items, page, pageSize, svc.count(principal, result));
    }
}
'''


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def write_case(name: str, svc: str, ctl: str = CTL):
    d = FX / name
    if d.exists():
        shutil.rmtree(d)
    src = d / "src/main/java/demo"
    src.mkdir(parents=True)
    (src / "Svc.java").write_text(svc, encoding="utf-8", newline="\n")
    if ctl is not None:
        (src / "Ctl.java").write_text(ctl, encoding="utf-8", newline="\n")
    return d


def run(case_dir: Path, src: Path = None):
    src_dir = src or (case_dir / "src/main/java")
    cmd = [sys.executable, str(SCRIPT), "--root", str(case_dir), "--src", str(src_dir)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", errors="replace")
    fails = {FAIL_RE.match(ln).group(1) for ln in out.replace("\r\n", "\n").split("\n") if FAIL_RE.match(ln)}
    passes = {PASS_RE.match(ln).group(1) for ln in out.replace("\r\n", "\n").split("\n") if PASS_RE.match(ln)}
    return p.returncode, fails, passes, out


def mutate(text: str, old: str, new: str, count: int = 1):
    """返回 (新文本, 命中次数)。锚点未命中即**空转通过**（坑 66/94）。"""
    n = text.count(old)
    return text.replace(old, new, count), n


results = []
fails = []


def check(name, ok, detail=""):
    results.append("%s %s%s" % ("[PASS]" if ok else "[FAIL]", name, (" — " + detail) if detail else ""))
    if not ok:
        fails.append(name)


# ---------------------------------------------------------------- 基线（合规夹具）
base_dir = write_case("base", SVC)
base_rc, base_fails, base_passes, base_out = run(base_dir)
check("T1 合规夹具 rc=0", base_rc == 0, "rc=%d" % base_rc)
check("T2 合规夹具 FAIL 明细为空", not base_fails, "FAIL=%s" % sorted(base_fails))
check("T3 合规夹具 A0a..A0g 七条正向对照全 PASS",
      {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"} <= base_passes,
      "PASS=%s" % sorted(base_passes))
check("T4 合规夹具解析到 2 个分页站点", "分页站点 2" in base_out, "见 A0b 行")
check("T5 合规夹具 A6c 判同源（无 FAIL）", "A6c" not in base_fails)

# ---------------------------------------------------------------- 空夹具
empty = FX / "empty"
if empty.exists():
    shutil.rmtree(empty)
empty.mkdir(parents=True)
e_rc, e_fails, e_passes, _ = run(empty)
check("T6 空夹具 rc≠0", e_rc != 0, "rc=%d" % e_rc)
check("T7 空夹具点名全部 A0*", {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"} <= e_fails,
      "FAIL=%s" % sorted(e_fails))
check("T8 空夹具下 A0* 无一条 PASS", not ({"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"} & e_passes))

# ---------------------------------------------------------------- 注入缺陷（每分支一条）
def case(name, old, new, target, svc=SVC, ctl=CTL, count=1, which="svc"):
    if which == "ctl":
        t, n = mutate(ctl, old, new, count)
        ctl_new = t
        svc_new = svc
    else:
        t, n = mutate(svc, old, new, count)
        svc_new = t
        ctl_new = ctl
    check("注入 %s 锚点命中" % name, n == count, "命中 %d 次（期望 %d）" % (n, count))
    if n != count:
        return
    d = write_case(name, svc_new, ctl_new)
    rc, f, _p, out = run(d)
    delta = f - base_fails
    check("%s 恰好新增目标断言 %s" % (name, target), delta == {target},
          "新增=%s 消失=%s rc=%d" % (sorted(delta), sorted(base_fails - f), rc))


case("N1-谓词不同源",
     'jdbc.queryForObject("select count(*) from aap_demo" + where',
     'jdbc.queryForObject("select count(*) from aap_demo where deleted = false and tenant_id = 1"',
     "A1")
case("N2-参数不同源",
     "Svc::map, pageArgs.toArray());\n        return PageResult.of(items, page, pageSize, total == null",
     "Svc::map, otherArgs.toArray());\n        return PageResult.of(items, page, pageSize, total == null",
     "A2")
case("N3-total 取自 items.size()",
     "PageResult.of(items, page, pageSize, total == null ? 0L : total);",
     "PageResult.of(items, page, pageSize, (long) items.size());",
     "A3")
case("N4-分页响应无 count",
     'Long total = jdbc.queryForObject("select count(*) from aap_demo" + where, Long.class, args.toArray());',
     "Long total = 0L;",
     "A4")
case("N5-分页响应无 limit/offset",
     'List<Object> items = jdbc.query("select id from aap_demo" + where + " order by id desc limit ? offset ?",',
     'List<Object> items = jdbc.query("select id from aap_demo" + where + " order by id desc",',
     "A5b")
case("N6-两次查询之间改写谓词",
     'Long total = jdbc.queryForObject("select count(*) from aap_demo" + where, Long.class, args.toArray());',
     'Long total = jdbc.queryForObject("select count(*) from aap_demo" + where, Long.class, args.toArray());\n'
     '        where.append(" and extra = ?");',
     "A1c")
case("N7-跨方法 count 缺筛选实参",
     "return PageResult.of(items, page, pageSize, svc.count(principal, result));",
     "return PageResult.of(items, page, pageSize, svc.count(principal));",
     "A6c", which="ctl")
# 表不同源
case("N8-count 与 list 表不同",
     'jdbc.queryForObject("select count(*) from aap_demo" + where',
     'jdbc.queryForObject("select count(*) from aap_demo_other" + where',
     "A1b")

# ---------------------------------------------------------------- 回归守卫（形态变化不得改结论）
def guard(name, pairs, svc=SVC):
    t = svc
    ok = True
    for old, new in pairs:
        t, n = mutate(t, old, new, 1)
        check("回归守卫 %s 锚点命中" % name, n == 1, "命中 %d 次（锚点：%s）" % (n, old[:40]))
        if n != 1:
            ok = False
    if not ok:
        return
    d = write_case(name, t)
    rc, f, _p, _o = run(d)
    check("回归守卫 %s 结果不变（仍 0 FAIL）" % name, f == base_fails,
          "新增=%s rc=%d" % (sorted(f - base_fails), rc))


guard("R1-SQL 走常量引用", [
    ('private final JdbcTemplate jdbc = null;',
     'private final JdbcTemplate jdbc = null;\n'
     '    private static final String COUNT_SQL = "select count(*) from aap_demo";'),
    ('jdbc.queryForObject("select count(*) from aap_demo" + where, Long.class, args.toArray());',
     'jdbc.queryForObject(COUNT_SQL + where, Long.class, args.toArray());'),
])
guard("R2-谓词内联（别名不同但语义相同）", [
    ('Long total = jdbc.queryForObject("select count(*) from aap_demo" + where, Long.class, args.toArray());\n'
     "        List<Object> pageArgs = new ArrayList<>(args);\n"
     "        pageArgs.add(pageSize);\n"
     "        pageArgs.add((page - 1) * pageSize);\n"
     '        List<Object> items = jdbc.query("select id from aap_demo" + where + " order by id desc limit ? offset ?",\n'
     "                Svc::map, pageArgs.toArray());",
     'Long total = jdbc.queryForObject("select count(*) from aap_demo where deleted = false and status = ?", Long.class, status);\n'
     '        List<Object> items = jdbc.query("select id from aap_demo d where d.deleted = false and d.status = ? order by d.id desc limit ? offset ?",\n'
     "                Svc::map, status, pageSize, (page - 1) * pageSize);"),
])

# ---------------------------------------------------------------- 只读守卫
def fingerprint(d: Path):
    return {str(p.relative_to(d)): (p.stat().st_size, md5(p)) for p in sorted(d.rglob("*.java"))}


fx_before = {c.name: fingerprint(c) for c in sorted(FX.iterdir()) if c.is_dir()}
repo_before = {str(p): (p.stat().st_size, md5(p)) for p in [
    ROOT / "aap-server/src/main/java/com/hioas/aap/report/ReportController.java",
    ROOT / "aap-server/src/main/java/com/hioas/aap/report/ReportService.java",
    ROOT / ".agents/state/evidence/coverage-report.json",
] if p.exists()}
r1_rc, r1_f, _p, _o = run(ROOT, ROOT / "aap-server/src/main/java")   # 真实仓库跑一次
r2_rc, r2_f, _p, _o = run(ROOT, ROOT / "aap-server/src/main/java")   # 再跑一次（只读、无状态）
fx_after = {c.name: fingerprint(c) for c in sorted(FX.iterdir()) if c.is_dir()}
repo_after = {str(p): (p.stat().st_size, md5(p)) for p in [
    ROOT / "aap-server/src/main/java/com/hioas/aap/report/ReportController.java",
    ROOT / "aap-server/src/main/java/com/hioas/aap/report/ReportService.java",
    ROOT / ".agents/state/evidence/coverage-report.json",
] if p.exists()}
check("T9 夹具目录零写副作用", fx_before == fx_after)
check("T10 真实仓库关键文件 md5 不变（只读）", repo_before == repo_after)
check("T11 真实仓库两次运行 FAIL 集合一致", r1_f == r2_f, "r1=%s r2=%s" % (sorted(r1_f), sorted(r2_f)))
check("T12 真实仓库 FAIL 集合 = {A6c}（本轮真发现）", r1_f == {"A6c"}, "FAIL=%s" % sorted(r1_f))
check("T13 夹具目录不残留 __pycache__", not list(FX.rglob("__pycache__")))

print("\n".join(results))
print("")
print("== 汇总：%d/%d PASS，FAIL %d 条 %s ==" % (len(results) - len(fails), len(results), len(fails), fails))
sys.exit(1 if fails else 0)
