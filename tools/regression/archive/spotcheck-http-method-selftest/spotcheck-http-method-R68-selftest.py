#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R68 抽查 `spotcheck-http-method-R68.py` 的负向自测（夹具 + 注入缺陷判别力）。

覆盖：合规夹具（rc=0 且 FAIL 明细空）／空夹具必须变红并点名 A0* 与条件化断言／
6 组注入缺陷（各断言「锚点命中 + 新文本真的出现 + **恰好**新增目标断言」，坑 66/90/94）／
2 组回归守卫（常量引用 SQL、FQ 字段类型：注入等价写法后结果**必须不变**，否则说明修复退化）／
夹具目录零写副作用（含不得留下 `__pycache__`）＋真实仓库关键文件 md5 只读守卫。

FAIL 判据：`[FAIL\\s*]` 正则（坑 97）；比对键用**断言前缀**（坑 82/93）；
基线变量独立命名（坑 93）；只比明细行、排除汇总行（坑 103）；FAIL 断言行数 > 0 作正向对照（坑 98）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
TMP = Path("C:/Users/laitz/AppData/Local/Temp/aap-r68-spotcheck-fixtures")
SCRIPT = Path("C:/Users/laitz/AppData/Local/Temp/aap-r68-spotcheck/spotcheck-http-method-R68.py")
FAIL_RE = re.compile(r"\[FAIL\s*\]")
WATCH = [ROOT / "docs/backend/endpoints.json", ROOT / "docs/backend/openapi.yaml",
         ROOT / "aap-server/src/main/java/com/hioas/aap/quote/QuoteController.java",
         ROOT / "aap-server/src/main/java/com/hioas/aap/credential/CredentialService.java"]

CTRL = """package com.x.web;

public class ThingController {
    private final com.x.svc.ThingService svc;

    public ThingController(com.x.svc.ThingService svc) { this.svc = svc; }

    /** 读端点：只读。 */
    @GetMapping("/a")
    public String read() { return svc.read(); }

    /** 写端点：落库。 */
    @PostMapping("/b")
    public String write() { return svc.write(); }
}
"""

SVC = """package com.x.svc;

public class ThingService {
    private final JdbcTemplate jdbc;

    private static final String RECORD_SQL = \"\"\"
            insert into t (a) values (?)
            \"\"\";

    private static final String PURGE_SQL = \"\"\"
            delete from t where created_at < ?
            \"\"\";

    public ThingService(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public String read() { return "ok"; }

    public String write() { record("a", "b", "c", "d"); return "ok"; }

    public void record(String a, String b, String c, String d) { jdbc.update(RECORD_SQL, a); }

    public void record(String a, String b, String c, String d, String e, String f, String g) { }

    /** 第二处写调用点：为 A0f 正向对照留「兜底来源」（坑 136），不被任何端点调用。 */
    public void purge() { jdbc.update(PURGE_SQL, 1); }
}
"""

TEST_SRC = """package com.x;

public class ThingIT {
    void t() { get("/a"); post("/b"); }
}
"""

MANIFEST = """{
  "endpoints": [
    {"id": "X-01", "method": "GET", "path": "/a"},
    {"id": "X-02", "method": "POST", "path": "/b"}
  ]
}
"""


def build(dest: Path, *, ctrl=CTRL, svc=SVC, test=TEST_SRC, manifest=MANIFEST, with_test=True):
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    m = dest / "aap-server/src/main/java/com/x"
    (m / "web").mkdir(parents=True)
    (m / "svc").mkdir(parents=True)
    (m / "web/ThingController.java").write_text(ctrl, encoding="utf-8", newline="\n")
    (m / "svc/ThingService.java").write_text(svc, encoding="utf-8", newline="\n")
    if with_test:
        t = dest / "aap-server/src/test/java/com/x"
        t.mkdir(parents=True)
        (t / "ThingIT.java").write_text(test, encoding="utf-8", newline="\n")
    d = dest / "docs/backend"
    d.mkdir(parents=True)
    (d / "endpoints.json").write_text(manifest, encoding="utf-8", newline="\n")


def run_audit(fixture_root: Path):
    cmd = [sys.executable, str(SCRIPT), "--root", str(fixture_root),
           "--src", str(fixture_root / "aap-server/src/main/java")]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", errors="replace")


def fails(text):
    """FAIL 明细行的**断言前缀**集合（排除汇总行，坑 103）。"""
    out = set()
    for ln in text.splitlines():
        if FAIL_RE.search(ln) and "汇总" not in ln:
            m = re.search(r"\[FAIL\s*\]\s+(\S+)", ln)
            if m:
                out.add(m.group(1))
    return out


def fail_lines(text):
    return [ln for ln in text.splitlines() if FAIL_RE.search(ln) and not ln.strip().startswith("[PASS]")]


def mutate(text, pairs):
    """逐 (old,new) 替换并**断言锚点命中**（坑 66/94/104）；返回 (新文本, 未命中锚点)。"""
    missed = []
    for old, new in pairs:
        if old not in text:
            missed.append(old)
        text = text.replace(old, new)
    return text, missed


results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("%s %s%s" % ("[PASS]" if cond else "[FAIL]", name, (" | " + detail) if detail else ""))


print("== R68 抽查负向自测 ==")
before = {str(p): (p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest()) for p in WATCH if p.exists()}

# ---------- 1. 合规夹具 ----------
ok_root = TMP / "ok"
build(ok_root)
ok_rc, ok_out = run_audit(ok_root)
check("合规夹具 rc=0", ok_rc == 0, "rc=%d" % ok_rc)
check("合规夹具 FAIL 明细为空", not fail_lines(ok_out), "FAIL 行 %d" % len(fail_lines(ok_out)))
ok_fail = fails(ok_out)
check("合规夹具正向对照 A0a…A0h 全 PASS", all(("[PASS] " + a) in ok_out for a in
      ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h")), "")
check("合规夹具 A1/A2/A3/A4 全 PASS", all(("[PASS] " + a) in ok_out for a in ("A1 ", "A2 ", "A3 ", "A4 ")), "")
check("合规夹具解析到 2 个端点（GET 1 / POST 1）", "读端点 1 个" in ok_out and "写端点 1 个" in ok_out, "")

# ---------- 2. 空夹具必须变红 ----------
empty_root = TMP / "empty"
build(empty_root)
shutil.rmtree(empty_root / "aap-server", ignore_errors=True)
(empty_root / "docs/backend/endpoints.json").unlink()
e_rc, e_out = run_audit(empty_root)
check("空夹具 rc≠0", e_rc != 0, "rc=%d" % e_rc)
e_fail = fails(e_out)
check("空夹具点名全部 A0* 与条件化断言 A1/A2/A3/A4",
      {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h", "A1", "A2", "A3", "A4"} <= e_fail,
      "缺：%s" % sorted({"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h", "A1", "A2", "A3", "A4"} - e_fail))
check("空夹具无 A0* PASS（条件化断言不得空转假绿，坑 98/132/141）",
      not any(("[PASS] " + a) in e_out for a in ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h")), "")

# ---------- 3. 注入：GET 链上出现写副作用 ----------
svc2, miss = mutate(SVC, [('public String read() { return "ok"; }',
                           'public String read() { jdbc.update(RECORD_SQL, "x"); return "ok"; }')])
check("注入 inj-get-write 锚点全部命中", not miss, "未命中：%s" % miss)
check("注入 inj-get-write 新文本真的出现", 'public String read() { jdbc.update(RECORD_SQL, "x")' in svc2, "")
r = TMP / "inj-get-write"
build(r, svc=svc2)
rc, out = run_audit(r)
check("注入 inj-get-write 恰好新增目标断言 A1", fails(out) - ok_fail == {"A1"} and ok_fail - fails(out) == set(),
      "新增 %s / 消失 %s" % (sorted(fails(out) - ok_fail), sorted(ok_fail - fails(out))))

# ---------- 4. 注入：写端点链上零写 ----------
svc3, miss = mutate(SVC, [("jdbc.update(RECORD_SQL, a); }", "int n = 0; }"),
                          ('String RECORD_SQL = """\n            insert into t (a) values (?)\n            """',
                           'String RECORD_SQL = """\n            select a from t where a = ?\n            """')])
check("注入 inj-post-noread 锚点全部命中", not miss, "未命中：%s" % miss)
check("注入 inj-post-noread 新文本真的出现",
      "select a from t where a = ?" in svc3 and "int n = 0; }" in svc3, "")
r = TMP / "inj-post-noread"
build(r, svc=svc3)
rc, out = run_audit(r)
check("注入 inj-post-noread 恰好新增目标断言 A2", fails(out) - ok_fail == {"A2"} and ok_fail - fails(out) == set(),
      "新增 %s / 消失 %s" % (sorted(fails(out) - ok_fail), sorted(ok_fail - fails(out))))

# ---------- 5. 注入：实参个数无匹配重载（调用链断链） ----------
ctrl5, miss = mutate(CTRL, [])
check("注入 inj-arity 锚点全部命中", not miss, "未命中：%s" % miss)
svc5, miss2 = mutate(SVC, [('public String write() { record("a", "b", "c", "d"); return "ok"; }',
                            'public String write() { record("a", "b", "c", "d", "e", "f", "g", "h"); return "ok"; }')])
check("注入 inj-arity 锚点全部命中（服务侧）", not miss2, "未命中：%s" % miss2)
check("注入 inj-arity 新文本真的出现", 'record("a", "b", "c", "d", "e", "f", "g", "h")' in svc5, "")
r = TMP / "inj-arity"
build(r, ctrl=ctrl5, svc=svc5)
rc, out = run_audit(r)
check("注入 inj-arity 恰好新增目标断言 A2（重载无匹配 → 链断 → 写不可见）",
      fails(out) - ok_fail == {"A2"} and ok_fail - fails(out) == set(),
      "新增 %s / 消失 %s" % (sorted(fails(out) - ok_fail), sorted(ok_fail - fails(out))))

# ---------- 6. 回归守卫：常量引用 SQL ↔ 内联字面量 SQL 等价 ----------
svc6, miss = mutate(SVC, [("jdbc.update(RECORD_SQL, a); }",
                           'jdbc.update("insert into t (a) values (?)", a); }')])
check("回归守卫 inj-const-inline 锚点全部命中", not miss, "未命中：%s" % miss)
check("回归守卫 inj-const-inline 新文本真的出现", 'jdbc.update("insert into t (a) values (?)", a); }' in svc6, "")
r = TMP / "inj-const-inline"
build(r, svc=svc6)
rc, out = run_audit(r)
check("回归守卫 inj-const-inline 结果必须不变（两种写法都要被计入）", fails(out) == ok_fail and rc == 0,
      "FAIL 差异：%s rc=%d" % (sorted(fails(out) ^ ok_fail), rc))

# ---------- 7. 回归守卫：FQ 字段类型 ↔ 简单类型等价 ----------
ctrl7, miss = mutate(CTRL, [("private final com.x.svc.ThingService svc;", "private final ThingService svc;")])
check("回归守卫 inj-fq-simple 锚点全部命中", not miss, "未命中：%s" % miss)
check("回归守卫 inj-fq-simple 新文本真的出现", "private final ThingService svc;" in ctrl7, "")
r = TMP / "inj-fq-simple"
build(r, ctrl=ctrl7)
rc, out = run_audit(r)
check("回归守卫 inj-fq-simple 结果必须不变（FQ 与简单类型都要归一）", fails(out) == ok_fail and rc == 0,
      "FAIL 差异：%s rc=%d" % (sorted(fails(out) ^ ok_fail), rc))

# ---------- 8. 注入：清单方法语义漂移（A3） ----------
man8, miss = mutate(MANIFEST, [('{"id": "X-02", "method": "POST", "path": "/b"}',
                                '{"id": "X-02", "method": "GET", "path": "/b"}')])
check("注入 inj-manifest-method 锚点全部命中", not miss, "未命中：%s" % miss)
check("注入 inj-manifest-method 新文本真的出现", '"method": "GET", "path": "/b"' in man8, "")
r = TMP / "inj-manifest-method"
build(r, manifest=man8)
rc, out = run_audit(r)
check("注入 inj-manifest-method 恰好新增目标断言 A3", fails(out) - ok_fail == {"A3"} and ok_fail - fails(out) == set(),
      "新增 %s / 消失 %s" % (sorted(fails(out) - ok_fail), sorted(ok_fail - fails(out))))

# ---------- 9. 注入：测试源缺失（A4） ----------
r = TMP / "inj-no-test"
build(r, with_test=False)
rc, out = run_audit(r)
check("注入 inj-no-test 恰好新增目标断言 A4", fails(out) - ok_fail == {"A4"} and ok_fail - fails(out) == set(),
      "新增 %s / 消失 %s" % (sorted(fails(out) - ok_fail), sorted(ok_fail - fails(out))))

# ---------- 10. 夹具目录零写副作用 + 真实仓库只读守卫 ----------
stray = [str(p) for p in TMP.rglob("*") if p.name == "__pycache__" or p.suffix in (".pyc", ".tmp")]
check("夹具目录零写副作用（无 __pycache__/.pyc/.tmp 残留）", not stray, "残留：%s" % stray[:5])
after = {str(p): (p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest()) for p in WATCH if p.exists()}
check("真实仓库关键文件 md5 不变（只读守卫）", before == after,
      "变化：%s" % [k for k in set(before) | set(after) if before.get(k) != after.get(k)])
check("空夹具产出 FAIL 明细行 > 0（收集器有效，坑 98/46）", len(fail_lines(e_out)) > 0,
      "空夹具 FAIL 明细 %d 行" % len(fail_lines(e_out)))

bad = [n for n, c, _ in results if not c]
print()
print("自测：%d 条，PASS %d / FAIL %d" % (len(results), len(results) - len(bad), len(bad)))
if bad:
    print("失败项：%s" % bad)
sys.exit(1 if bad else 0)
