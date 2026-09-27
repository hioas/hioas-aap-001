"""R46 抽查的负向自测（判别力对照）。

纪律（每条都对应一次真实返工）：
  - 基线变量另起名 ok_out（坑 93：基线被覆盖会让「恰好新增」恒为空）；
  - FAIL 集合按**断言前缀**（A1/A4b…）比对，不拿整行文本当键（坑 82/93）；
  - 注入必须**真的改到源码**（replace 命中数断言，坑 66/94），且注入值不得与旧值互为子串（坑 90）；
  - 合规夹具必须 rc=0 且 FAIL 0（正向对照，坑 46/75：只有反例时「一直在报错」会被当成合格）；
  - 空夹具必须变红并点名解析器失效（坑 75/98）；
  - 零写副作用：真实仓库关键文件 md5 全等（坑 39）。
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "audit-pagination-defaults.py")
REAL = r"E:/workspaces/hioas/hioas-aap-001"
FIX = os.path.join(HERE, "fixtures")
PY = sys.executable
FAIL_LINE = re.compile(r"^\s*\[FAIL\]\s*(.*)$")

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), str(detail)))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + str(detail)) if detail else ""))
    return bool(ok)


def run(root):
    p = subprocess.run([PY, AUDIT, "--root", root], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    fails = []
    for ln in out.splitlines():
        m = FAIL_LINE.match(ln)
        if m:
            fails.append(m.group(1).strip())
    return p.returncode, out, fails


def labels(fails):
    """FAIL 断言前缀集合（坑 82/93：按前缀比对，不拿整行当键）。"""
    out = set()
    for f in fails:
        m = re.match(r"([A-Za-z0-9]+[a-z]?)\b", f)
        out.add(m.group(1) if m else f[:8])
    return out


def build_fixture(name):
    dst = os.path.join(FIX, name)
    if os.path.isdir(dst):
        shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    os.makedirs(os.path.join(dst, "docs/backend"), exist_ok=True)
    for rel in ("docs/backend/02-API接口模型清单.md", "docs/backend/openapi.yaml",
                "docs/backend/endpoints.json"):
        shutil.copy2(os.path.join(REAL, rel), os.path.join(dst, rel))
    for rel in ("aap-server/src/main/java", "aap-server/src/test/java", "aap-client/src"):
        shutil.copytree(os.path.join(REAL, rel), os.path.join(dst, rel), dirs_exist_ok=True)
    return dst


def mutate(path, old, new, count=1):
    t = open(path, encoding="utf-8").read()
    hits = t.count(old)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t.replace(old, new, count))
    return hits


def fix_openapi(path):
    """合规修法：给每个 page/pageSize 参数补 default（pageSize 再补 maximum），模拟「生成器补齐」。"""
    lines = open(path, encoding="utf-8").read().split("\n")
    out, cur, hits = [], None, 0
    for ln in lines:
        out.append(ln)
        m = re.match(r"\s*- name: (page|pageSize)\s*$", ln)
        if m:
            cur = m.group(1)
            continue
        if cur and re.match(r"\s*minimum: 1\s*$", ln):
            ind = ln[:len(ln) - len(ln.lstrip())]
            if cur == "page":
                out.append(ind + "default: 1")
            else:
                out.append(ind + "default: 20")
                out.append(ind + "maximum: 200")
            hits += 1
            cur = None
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out))
    return hits


def drop_one_minimum(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    out, cur, hits = [], None, 0
    for ln in lines:
        m = re.match(r"\s*- name: (page|pageSize)\s*$", ln)
        if m:
            cur = m.group(1)
        if cur == "pageSize" and re.match(r"\s*minimum: 1\s*$", ln) and hits == 0:
            hits += 1
            cur = None
            continue
        out.append(ln)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out))
    return hits


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def main():
    print("== R46 抽查（分页参数缺省值与上限）负向自测 ==")
    print("审计脚本：%s" % AUDIT)
    print()
    if os.path.isdir(FIX):
        shutil.rmtree(FIX, ignore_errors=True)
    os.makedirs(FIX, exist_ok=True)

    # ---- T0：真实仓库基线（只读；先把关键文件指纹留下）
    key_files = [
        "docs/backend/02-API接口模型清单.md",
        "docs/backend/openapi.yaml",
        "aap-server/src/main/java/com/hioas/aap/common/PageQuery.java",
        "aap-server/src/main/java/com/hioas/aap/usage/UsageController.java",
    ]
    before = {k: md5(os.path.join(REAL, k)) for k in key_files}

    print("T0 真实仓库基线")
    ok_rc, ok_out, ok_fails = run(REAL)
    check("T0 真实仓库 rc=1（存在待拍板漂移）", ok_rc == 1, "rc=%d" % ok_rc)
    check("T0 真实仓库 FAIL 恰好 = {A1, A2}（正向对照：不是「全都没事」）",
          labels(ok_fails) == {"A1", "A2"}, "labels=%s" % sorted(labels(ok_fails)))

    # ---- T1：合规夹具（注入修法）→ 必须 rc=0 且 FAIL 0
    print("\nT1 合规夹具（openapi 补齐 default/maximum）")
    d = build_fixture("compliant")
    hits = fix_openapi(os.path.join(d, "docs/backend/openapi.yaml"))
    check("T1 注入修法锚点命中 46 处（= page+pageSize 参数数）", hits == 46, "hits=%d" % hits)
    rc, out, fails = run(d)
    check("T1 合规夹具 rc=0 且 FAIL 0（判据不是「永远报错」）", rc == 0 and not fails,
          "rc=%d fails=%d" % (rc, len(fails)))

    # ---- T2：md 上限 200 → 500
    print("\nT2 注入：md 上限改成 500")
    d = build_fixture("md_max")
    hits = mutate(os.path.join(d, "docs/backend/02-API接口模型清单.md"), "上限 200", "上限 500")
    check("T2 锚点命中 1 处", hits == 1, "hits=%d" % hits)
    check("T2 注入值语义真的变了（新旧不互为子串）",
          "上限 200" not in "上限 500" and "上限 500" not in "上限 200")
    rc, out, fails = run(d)
    check("T2 FAIL 集合恰好新增 A4", labels(fails) == {"A1", "A2", "A4"}, "labels=%s" % sorted(labels(fails)))

    # ---- T3：openapi 去掉一个 pageSize 的 minimum
    print("\nT3 注入：openapi 去掉一个 pageSize 的 minimum")
    d = build_fixture("oa_min")
    hits = drop_one_minimum(os.path.join(d, "docs/backend/openapi.yaml"))
    check("T3 锚点命中 1 处", hits == 1, "hits=%d" % hits)
    rc, out, fails = run(d)
    check("T3 FAIL 集合恰好新增 A3", labels(fails) == {"A1", "A2", "A3"}, "labels=%s" % sorted(labels(fails)))

    # ---- T4：服务层去掉夹取
    print("\nT4 注入：CredentialService 不再夹取（new PageQuery 替掉 PageQuery.of）")
    d = build_fixture("svc_noclamp")
    hits = mutate(os.path.join(d, "aap-server/src/main/java/com/hioas/aap/credential/CredentialService.java"),
                  "PageQuery.of(page, pageSize)",
                  "new PageQuery(page == null ? 1 : page, pageSize == null ? 20 : pageSize)")
    check("T4 锚点命中 1 处", hits == 1, "hits=%d" % hits)
    rc, out, fails = run(d)
    check("T4 FAIL 集合恰好新增 A5", labels(fails) == {"A1", "A2", "A5"}, "labels=%s" % sorted(labels(fails)))
    check("T4 FAIL 文案点名 CRED-01", any("CRED-01" in f for f in fails if f.startswith("A5")),
          [f for f in fails if f.startswith("A5")][:1])

    # ---- T5：控制器把裸 pageSize 传给服务
    print("\nT5 注入：UsageController 传裸 pageSize（判据 pageSize() 子串真的失配）")
    d = build_fixture("ctrl_raw")
    hits = mutate(os.path.join(d, "aap-server/src/main/java/com/hioas/aap/usage/UsageController.java"),
                  "pageQuery.pageSize()", "pageSize")
    check("T5 锚点命中 1 处", hits == 1, "hits=%d" % hits)
    check("T5 判据真的失配（注入后实参不含 pageSize() 子串）",
          "pageSize()" not in "pageSize")
    rc, out, fails = run(d)
    check("T5 FAIL 集合恰好新增 A6", labels(fails) == {"A1", "A2", "A6"}, "labels=%s" % sorted(labels(fails)))

    # ---- T6：客户端越上限
    print("\nT6 注入：客户端 pageSize: 20 → 500")
    d = build_fixture("client_big")
    hits = mutate(os.path.join(d, "aap-client/src/pages/quote-models/index.vue"), "pageSize: 20", "pageSize: 500")
    check("T6 锚点命中 1 处", hits == 1, "hits=%d" % hits)
    rc, out, fails = run(d)
    check("T6 FAIL 集合恰好新增 A7", labels(fails) == {"A1", "A2", "A7"}, "labels=%s" % sorted(labels(fails)))

    # ---- T7：空夹具必须变红
    print("\nT7 空夹具（解析器失效必须红）")
    d = os.path.join(FIX, "empty")
    os.makedirs(d, exist_ok=True)
    rc, out, fails = run(d)
    check("T7 空夹具 rc!=0", rc != 0, "rc=%d" % rc)
    check("T7 空夹具点名 A0a/A0b/A0c/A0d（解析器失效）",
          {"A0a", "A0b", "A0c", "A0d"} <= labels(fails), "labels=%s" % sorted(labels(fails)))

    # ---- T8：零写副作用（真实仓库关键文件 md5 全等）
    print("\nT8 零写副作用守卫")
    after = {k: md5(os.path.join(REAL, k)) for k in key_files}
    check("T8 真实仓库 %d 个关键文件 md5 全等（抽查只读）" % len(key_files),
          before == after, "" if before == after else "changed=%s" % [k for k in before if before[k] != after[k]])

    n_pass = sum(1 for _n, ok, _d in RESULTS if ok)
    print("\n== 自测结果：PASS %d / FAIL %d ==" % (n_pass, len(RESULTS) - n_pass))
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
