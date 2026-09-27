#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R67 抽查脚本的**负向自测**：写路径事务边界（多写原子性 + 事务内外部 I/O）。

覆盖：
  ① 合规夹具 → rc=0 且 FAIL 明细空；
  ② 每条解析器正向对照（A0a…A0h）在夹具上 PASS（含 `> 0`）；
  ③ 空夹具 → rc≠0 且**点名**全部 A0* 与条件化断言（A1/A2/A3/A4/A5，坑 98/132/141）；
  ④ 5 组注入缺陷 → 先跑基线，再断言 FAIL 断言名集合**恰好新增**目标断言（坑 82/93/103）；
     每个注入都断言「锚点命中」且「新文本真的出现」（坑 66/90/94/104）；
  ⑤ 夹具目录零写副作用（含不得留下 __pycache__，坑 106）；
  ⑥ 真实仓库关键文件 md5 不变（只读守卫）。

用法：python spotcheck-tx-boundary-R67-selftest.py
"""
import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
AUDIT = HERE / "spotcheck-tx-boundary-R67.py"
ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
STAMP = str(int(time.time()))
FIX = Path("C:/Users/laitz/AppData/Local/Temp") / ("aap-r67-tx-fixtures-" + STAMP)
EMPTY = Path("C:/Users/laitz/AppData/Local/Temp") / ("aap-r67-tx-fixtures-empty-" + STAMP)

FAIL_RE = re.compile(r"\[FAIL\s*\]")
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("%s %s%s" % ("[PASS]" if cond else "[FAIL]", name, (" | " + detail) if detail else ""))


def tokens(text):
    out = []
    for ln in text.splitlines():
        if FAIL_RE.search(ln):
            parts = ln.split()
            out.append(parts[1] if len(parts) > 1 else "?")
    return sorted(set(out))


def run_audit(src_root):
    p = subprocess.run([sys.executable, str(AUDIT), "--root", str(src_root)],
                       cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", errors="replace")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


SERVICE = '''package com.hioas.aap.syn;

import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * 夹具：事务边界审计（第四十一类可审计不变量）用的最小实现。
 *
 * <p>独立事务落库：失败也要留痕，故用 REQUIRES_NEW（依据说明写在此处）。
 */
public class SynService {

    private final SynMapper synMapper = new SynMapper();
    private final SynOtherMapper otherMapper = new SynOtherMapper();
    private final SynHttp httpClient = new SynHttp();

    @Transactional
    public void guardedMultiWrite() {
        synMapper.insert();
        otherMapper.update();
    }

    public void nonTxCaller() {
        guardedMultiWrite();
    }

    @Transactional
    public void txEntry() {
        helperMultiWrite();
    }

    private void helperMultiWrite() {
        synMapper.delete();
        synMapper.insert();
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordFailure() {
        synMapper.insert();
    }

    public void ioOutsideTx() {
        httpClient.send();
    }

    @Transactional
    public void chainEntry() {
        synMapper.insert();
        chainHelper();
    }

    private void chainHelper() {
        otherMapper.update();
    }
}
'''

CONTROLLER = '''package com.hioas.aap.syn;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynController {

    private final SynService synService = new SynService();

    @PostMapping("/chain")
    public Object chainEndpoint() {
        return synService.chainEntry();
    }

    @PostMapping("/plain")
    public Object plainEndpoint() {
        return synService.ioOutsideTx();
    }
}
'''

MAPPER = '''package com.hioas.aap.syn;

public class %s {

    public int insert(Object row) {
        return 1;
    }

    public int update(Object row) {
        return 1;
    }

    public int delete(Object row) {
        return 1;
    }
}
'''

HTTP = '''package com.hioas.aap.syn;

public class SynHttp {

    public Object send() {
        return null;
    }
}
'''

TESTFILE = '''package com.hioas.aap.syn;

class SynServiceTest {

    void atomicity() {
        // 失败后不留痕：由基类 truncateAll 清表后断言计数为 0
        org.assertj.core.api.Assertions.assertThat(0).isEqualTo(0);
    }
}
'''


def build_fixture(base: Path):
    main = base / "aap-server/src/main/java/com/hioas/aap/syn"
    test = base / "aap-server/src/test/java/com/hioas/aap/syn"
    write(main / "SynService.java", SERVICE)
    write(main / "SynController.java", CONTROLLER)
    write(main / "SynMapper.java", MAPPER % "SynMapper")
    write(main / "SynOtherMapper.java", MAPPER % "SynOtherMapper")
    write(main / "SynHttp.java", HTTP)
    write(test / "SynServiceTest.java", TESTFILE)


def tree_fingerprint(base: Path):
    out = {}
    if not base.exists():
        return out
    for p in sorted(base.rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            out[str(p.relative_to(base))] = (len(b), hashlib.md5(b).hexdigest())
    return out


def repo_fingerprint():
    keys = [ROOT / "tools/audit-routes.py", ROOT / "tools/gen-backend-models.py",
            ROOT / "docs/backend/endpoints.json", ROOT / "docs/backend/openapi.yaml",
            ROOT / "aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java",
            ROOT / ".agents/state/aap-server-feature-status.csv"]
    out = {}
    for p in keys:
        if p.exists():
            b = p.read_bytes()
            out[str(p)] = hashlib.md5(b).hexdigest()
    return out


def mutate(path: Path, old: str, new: str):
    """注入缺陷；返回「锚点是否命中」。注入后断言新文本真的出现（坑 66/94）。"""
    txt = path.read_text(encoding="utf-8")
    if old not in txt:
        return False
    path.write_text(txt.replace(old, new, 1), encoding="utf-8", newline="\n")
    return new in path.read_text(encoding="utf-8")


def main():
    if not AUDIT.exists():
        print("[FAIL] 审计脚本不存在：%s" % AUDIT)
        return 2
    shutil.rmtree(FIX, ignore_errors=True)
    shutil.rmtree(EMPTY, ignore_errors=True)
    build_fixture(FIX)
    EMPTY.mkdir(parents=True, exist_ok=True)

    repo_before = repo_fingerprint()

    # ---- ① 合规夹具 ----
    rc0, out0 = run_audit(FIX)
    check("①合规夹具 rc=0", rc0 == 0, "rc=%d" % rc0)
    check("①合规夹具 FAIL 明细为空", not FAIL_RE.search(out0),
          "FAIL 行 = %d" % len([l for l in out0.splitlines() if FAIL_RE.search(l)]))

    # ---- ② 正向对照 ----
    for tag in ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h"):
        check("②正向对照 %s 在夹具上 PASS" % tag, ("[PASS] %s " % tag) in out0)
    check("②A1 在夹具上 PASS（多写方法全部有边界）", "[PASS] A1 " in out0)
    check("②A1b 在夹具上 PASS（调用链豁免 1 条）", "[PASS] A1b " in out0)
    check("②A2 在夹具上 PASS（REQUIRES_NEW 带依据）", "[PASS] A2 " in out0)
    check("②A3 在夹具上 PASS（I/O 不在事务内）", "[PASS] A3 " in out0)
    check("②A4 在夹具上 PASS（链上多写在事务内）", "[PASS] A4 " in out0)
    check("②A5 在夹具上 PASS（测试源非空）", "[PASS] A5 " in out0)
    ok_tokens = tokens(out0)

    # ---- ③ 空夹具必须变红并点名全部断言 ----
    rc1, out1 = run_audit(EMPTY)
    empty_tokens = tokens(out1)
    check("③空夹具 rc≠0", rc1 != 0, "rc=%d" % rc1)
    want = {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h", "A1", "A2", "A3", "A4", "A5"}
    missing = sorted(want - set(empty_tokens))
    check("③空夹具点名全部 A0*/条件化断言", not missing, "缺：%s；实得：%s" % (missing, empty_tokens))
    check("③空夹具无 A0* PASS（不得空转假绿）",
          not any(("[PASS] %s " % t) in out1 for t in ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h")))

    # ---- ④ 注入缺陷判别力（先跑基线，再断言恰好新增） ----
    cases = [
        ("inj-a1-去多写方法的事务注解", "SynService.java",
         "    @Transactional\n    public void guardedMultiWrite() {",
         "    public void guardedMultiWrite() {", {"A1"}),
        ("inj-a2-去 REQUIRES_NEW 依据说明", "SynService.java",
         "独立事务落库：失败也要留痕，故用 REQUIRES_NEW（依据说明写在此处）。",
         "夹具说明（无依据字样）。", {"A2"}),
        ("inj-a3-给 I/O 方法加事务注解", "SynService.java",
         "    public void ioOutsideTx() {",
         "    @Transactional\n    public void ioOutsideTx() {", {"A3"}),
        ("inj-a4-去链上唯一事务注解", "SynService.java",
         "    @Transactional\n    public void chainEntry() {",
         "    public void chainEntry() {", {"A4"}),
    ]
    for name, fname, old, new, expect in cases:
        d = Path(str(FIX) + "-" + name.split("-")[1])
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(FIX, d)
        hit = mutate(d / "aap-server/src/main/java/com/hioas/aap/syn" / fname, old, new)
        check("④%s：注入锚点命中且新文本出现" % name, hit)
        rc, out = run_audit(d)
        delta = set(tokens(out)) - set(ok_tokens)
        check("④%s：FAIL 集合恰好新增 %s" % (name, sorted(expect)), delta == expect,
              "delta=%s rc=%d" % (sorted(delta), rc))
        shutil.rmtree(d, ignore_errors=True)

    d5 = Path(str(FIX) + "-inj-a5")
    shutil.rmtree(d5, ignore_errors=True)
    shutil.copytree(FIX, d5)
    (d5 / "aap-server/src/test/java/com/hioas/aap/syn/SynServiceTest.java").unlink()
    rc, out = run_audit(d5)
    delta = set(tokens(out)) - set(ok_tokens)
    check("④inj-a5-删测试源：FAIL 集合恰好新增 ['A5']", delta == {"A5"}, "delta=%s rc=%d" % (sorted(delta), rc))
    shutil.rmtree(d5, ignore_errors=True)

    # ---- ⑤ 夹具目录零写副作用 ----
    fp_before = tree_fingerprint(FIX)
    _, _ = run_audit(FIX)
    fp_after = tree_fingerprint(FIX)
    check("⑤夹具目录零写副作用（含无 __pycache__）", fp_before == fp_after,
          "before=%d after=%d" % (len(fp_before), len(fp_after)))
    check("⑤夹具目录无 __pycache__", not any("__pycache__" in k for k in fp_after))

    # ---- ⑥ 真实仓库只读守卫 ----
    check("⑥真实仓库关键文件 md5 不变", repo_before == repo_fingerprint(),
          "%d 个文件" % len(repo_before))

    shutil.rmtree(FIX, ignore_errors=True)
    shutil.rmtree(EMPTY, ignore_errors=True)

    bad = [n for n, c, _ in results if not c]
    print()
    print("自测 %d 项：PASS %d / FAIL %d" % (len(results), len(results) - len(bad), len(bad)))
    if bad:
        print("失败项：" + "；".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
