"""R49 抽查的负向自测（每个判定分支一条反例 + 正向对照 + 注入缺陷判别力 + 零写副作用）。

夹具与脚本分开命名（坑 106）：脚本在 aap-r49-spotcheck/，夹具在 aap-r49-spotcheck-fixtures/。
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys

TMP = os.environ["LOCALAPPDATA"] + "/Temp"
SCRIPT = os.path.join(TMP, "aap-r49-spotcheck", "aap-r49-param-reach.py")
FIX = os.path.join(TMP, "aap-r49-spotcheck-fixtures")
ROOT = r"E:/workspaces/hioas/hioas-aap-001"
FAIL_RE = re.compile(r"\[FAIL\s*\]\s*([A-Za-z0-9]+)")

PASS_CNT = [0]
FAIL_CNT = [0]


def check(name, cond, detail=""):
    if cond:
        PASS_CNT[0] += 1
        print("  [PASS] %s%s" % (name, (" | " + detail) if detail else ""))
    else:
        FAIL_CNT[0] += 1
        print("  [FAIL ] %s%s" % (name, (" | " + detail) if detail else ""))


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def run(src_root, endpoints):
    p = subprocess.run([sys.executable, SCRIPT, "--src-root", src_root, "--endpoints", endpoints],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    tokens = sorted({m.group(1) for ln in out.splitlines()
                     if not ln.strip().startswith("[PASS]")   # 排除自指噪声（坑 47/77）
                     for m in [FAIL_RE.search(ln)] if m})
    return p.returncode, out, tokens


def endpoints_json(path, rows):
    import json
    eps = [{"id": i, "method": m, "path": p, "query_params": q, "auth": "user"}
           for (i, m, p, q) in rows]
    w(path, json.dumps({"total": len(eps), "endpoints": eps}, indent=2))


CTRL_HEAD = """package com.hioas.aap.fixture;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RequestMapping("/api/v1/fixt")
public class %s {
"""


def scenario_ok(d):
    """合规夹具：一个参数控制器内直接用，一个参数经服务（含私有助手，2 跳）使用。"""
    src = os.path.join(d, "src/com/hioas/aap/fixture")
    w(os.path.join(src, "FixtController.java"), CTRL_HEAD % "FixtController" + """
    private final FixtService svc = new FixtService();

    @GetMapping
    public Object list(@RequestParam(required = false) String status,
                       @RequestParam(required = false) Integer page,
                       @RequestParam(required = false) Integer pageSize) {
        if ("all".equals(status)) {
            return Collections.emptyList();
        }
        return svc.query(page, pageSize);
    }
}
""")
    w(os.path.join(src, "FixtService.java"), """package com.hioas.aap.fixture;

import java.util.*;

public class FixtService {

    public Object query(Integer page, Integer pageSize) {
        return page(" where deleted = false", page, pageSize);
    }

    private Object page(String baseWhere, Integer page, Integer pageSize) {
        PageQuery q = PageQuery.of(page, pageSize);
        return new ArrayList<>(List.of(baseWhere, q));
    }
}
""")
    w(os.path.join(src, "PageQuery.java"), """package com.hioas.aap.fixture;

public class PageQuery {

    public static PageQuery of(Integer page, Integer pageSize) {
        int p = page == null || page < 1 ? 1 : page;
        int size = pageSize == null || pageSize < 1 ? 20 : Math.min(pageSize, 200);
        return new PageQuery(p, size);
    }
}
""")
    endpoints_json(os.path.join(d, "endpoints.json"),
                   [("FIX-01", "GET", "/api/v1/fixt", ["status", "page", "pageSize"])])


def scenario_unused(d):
    """缺陷夹具 A1：控制器声明 status 但方法体里一次都没用。"""
    src = os.path.join(d, "src/com/hioas/aap/fixture")
    w(os.path.join(src, "FixtController.java"), CTRL_HEAD % "FixtController" + """
    private final FixtService svc = new FixtService();

    @GetMapping
    public Object list(@RequestParam(required = false) String status,
                       @RequestParam(required = false) Integer page) {
        return svc.query(page);
    }
}
""")
    w(os.path.join(src, "FixtService.java"), """package com.hioas.aap.fixture;

import java.util.*;

public class FixtService {

    public Object query(Integer page) {
        return new ArrayList<>(List.of(page));
    }
}
""")
    endpoints_json(os.path.join(d, "endpoints.json"),
                   [("FIX-02", "GET", "/api/v1/fixt", ["status", "page"])])


def scenario_ignored_downstream(d):
    """缺陷夹具 A1（下游忽略）：status 传进服务，服务方法体里不用。"""
    src = os.path.join(d, "src/com/hioas/aap/fixture")
    w(os.path.join(src, "FixtController.java"), CTRL_HEAD % "FixtController" + """
    private final FixtService svc = new FixtService();

    @GetMapping
    public Object list(@RequestParam(required = false) String status) {
        return svc.query(status);
    }
}
""")
    w(os.path.join(src, "FixtService.java"), """package com.hioas.aap.fixture;

import java.util.*;

public class FixtService {

    public Object query(String status) {
        return new ArrayList<>(List.of("static"));
    }
}
""")
    endpoints_json(os.path.join(d, "endpoints.json"),
                   [("FIX-03", "GET", "/api/v1/fixt", ["status"])])


def scenario_not_declared(d):
    """缺陷夹具 A2：契约声明 page，但控制器根本没接收。"""
    src = os.path.join(d, "src/com/hioas/aap/fixture")
    w(os.path.join(src, "FixtController.java"), CTRL_HEAD % "FixtController" + """
    @GetMapping
    public Object list() {
        return Collections.emptyList();
    }
}
""")
    endpoints_json(os.path.join(d, "endpoints.json"),
                   [("FIX-04", "GET", "/api/v1/fixt", ["page"])])


def scenario_empty(d):
    """空夹具：src 里没有任何控制器 → A0a 必须变红（解析器失效判定，坑 46）。"""
    os.makedirs(os.path.join(d, "src/com/hioas/aap/fixture"), exist_ok=True)
    endpoints_json(os.path.join(d, "endpoints.json"),
                   [("FIX-05", "GET", "/api/v1/fixt", ["page"])])


def scenario_nested(d):
    """回归守卫：嵌套调用取最内层跨度 + 同类裸调用解析（本轮两条真实返工）。"""
    src = os.path.join(d, "src/com/hioas/aap/fixture")
    w(os.path.join(src, "FixtController.java"), CTRL_HEAD % "FixtController" + """
    private final FixtService svc = new FixtService();

    @GetMapping
    public Object list(@RequestParam(required = false) Integer pageSize) {
        return wrap(svc.query(parse(pageSize)));
    }

    private Object wrap(Object v) {
        return v;
    }

    private static Integer parse(Integer v) {
        return v;
    }
}
""")
    w(os.path.join(src, "FixtService.java"), """package com.hioas.aap.fixture;

import java.util.*;

public class FixtService {

    public Object query(Integer size) {
        return deep(size);
    }

    private Object deep(Integer size) {
        return PageQuery.of(1, size);
    }
}
""")
    w(os.path.join(src, "PageQuery.java"), """package com.hioas.aap.fixture;

public class PageQuery {

    public static PageQuery of(Integer page, Integer pageSize) {
        return new PageQuery();
    }
}
""")
    endpoints_json(os.path.join(d, "endpoints.json"),
                   [("FIX-06", "GET", "/api/v1/fixt", ["pageSize"])])


def mutate(text):
    """注入缺陷：把合规夹具里 status 的使用整段删掉；返回 (新文本, 未命中锚点列表)（坑 66）。"""
    anchors = ['        if ("all".equals(status)) {\n            return Collections.emptyList();\n        }\n']
    miss = [a for a in anchors if a not in text]
    new = text
    for a in anchors:
        new = new.replace(a, "")
    return new, miss


def fail_detail(out, token):
    """取点名某断言 token 的 FAIL 明细行（按前缀匹配，坑 82：整行文本当键会误判）。"""
    return [ln.strip() for ln in out.splitlines()
            if ln.strip().startswith("[FAIL") and re.search(r"\]\s*%s\b" % token, ln)]


def tokens_of(out):
    return sorted({m.group(1) for ln in out.splitlines()
                   if not ln.strip().startswith("[PASS]")
                   for m in [FAIL_RE.search(ln)] if m})


def main():
    if os.path.isdir(FIX):
        shutil.rmtree(FIX, ignore_errors=True)
    os.makedirs(FIX, exist_ok=True)

    print("== R49 抽查负向自测（参数可达性） ==")
    print("脚本：%s" % SCRIPT)
    print("夹具：%s" % FIX)
    print()

    print("--- 分支 1：合规夹具（direct + 2 跳下游）应为零 FAIL ---")
    d = os.path.join(FIX, "ok")
    scenario_ok(d)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    ok_out = out                      # 基线专用名（坑 93：不要复用变量）
    check("B1 合规夹具 FAIL 集合为空", tokens == [], "tokens=%s" % tokens)
    check("B1 合规夹具含 A1 PASS 行（正向对照：真的判过）", "A1 控制器已接收的查询参数" in ok_out)
    check("B1 定位率 1/1（解析器真的解析到）", "已定位端点 1 / 1" in ok_out)

    print()
    print("--- 分支 2：控制器声明但未使用 → 恰好新增 A1 ---")
    d = os.path.join(FIX, "unused")
    scenario_unused(d)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    added = sorted(set(tokens) - set(tokens_of(ok_out)))
    # A0e 白名单：极简夹具没有「下游链」样本，故该正向对照在此夹具必然为红（非被测缺陷）
    check("B2 恰好新增 A1（除夹具自带 A0e 控制外无其它）", added == ["A0e", "A1"], "added=%s" % added)
    check("B2 点名的端点/参数正确（FIX-02 `status`）",
          any("FIX-02" in x and "`status`" in x for x in fail_detail(out, "A1")),
          "detail=%s" % fail_detail(out, "A1"))

    print()
    print("--- 分支 3：传入下游但下游忽略 → 恰好新增 A1 ---")
    d = os.path.join(FIX, "ignored")
    scenario_ignored_downstream(d)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    added = sorted(set(tokens) - set(tokens_of(ok_out)))
    check("B3 恰好新增 A1（下游忽略，非「弱证据」放过）", added == ["A0e", "A1"], "added=%s" % added)
    check("B3 点名的端点/参数正确（FIX-03 `status`）",
          any("FIX-03" in x and "`status`" in x for x in fail_detail(out, "A1")),
          "detail=%s" % fail_detail(out, "A1"))

    print()
    print("--- 分支 4：契约声明但控制器未接收 → 恰好新增 A2 ---")
    d = os.path.join(FIX, "notdecl")
    scenario_not_declared(d)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    added = sorted(set(tokens) - set(tokens_of(ok_out)))
    check("B4 恰好新增 A2", added == ["A0e", "A2"], "added=%s" % added)
    check("B4 点名的端点/参数正确（FIX-04 `page`）",
          any("FIX-04" in x and "`page`" in x for x in fail_detail(out, "A2")),
          "detail=%s" % fail_detail(out, "A2"))

    print()
    print("--- 分支 5：空夹具必须变红（解析器失效） ---")
    d = os.path.join(FIX, "empty")
    scenario_empty(d)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    check("B5 空夹具变红且点名 A0a", "A0a" in tokens, "tokens=%s" % tokens)
    check("B5 空夹具同时点名 A1（参与判定 0 → 不得判「全可达」）", "A1" in tokens, "tokens=%s" % tokens)

    print()
    print("--- 分支 6：嵌套调用 / 裸同类调用回归守卫（本轮两条真实返工） ---")
    d = os.path.join(FIX, "nested")
    scenario_nested(d)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    check("B6 嵌套 + 裸调用链上参数可达（零 FAIL）", tokens == [], "tokens=%s" % tokens)
    check("B6 该参数判为下游使用（不是弱证据）", "USED_DOWNSTREAM" in out and "WEAK_UNRESOLVED" not in out)

    print()
    print("--- 分支 7：注入缺陷判别力（注入必须真的改到源码，坑 66/90/94） ---")
    d = os.path.join(FIX, "inject")
    scenario_ok(d)
    p = os.path.join(d, "src/com/hioas/aap/fixture/FixtController.java")
    orig = open(p, encoding="utf-8").read()
    new, miss = mutate(orig)
    check("B7a 注入锚点全部命中", miss == [], "未命中=%s" % miss)
    check("B7b 注入真的改到了源码", new != orig)
    w(p, new)
    rc, out, tokens = run(os.path.join(d, "src"), os.path.join(d, "endpoints.json"))
    base = sorted({m.group(1) for ln in ok_out.splitlines() if not ln.strip().startswith("[PASS]")
                   for m in [FAIL_RE.search(ln)] if m})
    added = sorted(set(tokens) - set(base))
    check("B7c 注入后 FAIL 集合恰好新增 A1", added == ["A1"], "added=%s tokens=%s" % (added, tokens))

    print()
    print("--- 分支 8：真实仓库只读运行（正向对照 + 零写副作用） ---")
    watch = [os.path.join(ROOT, "aap-server/src/main/java/com/hioas/aap/contract/ContractController.java"),
             os.path.join(ROOT, "aap-server/src/main/java/com/hioas/aap/contract/ContractService.java"),
             os.path.join(ROOT, "docs/backend/endpoints.json")]
    before = {f: hashlib.md5(open(f, "rb").read()).hexdigest() for f in watch}
    rc, out, tokens = run(os.path.join(ROOT, "aap-server/src/main/java"),
                          os.path.join(ROOT, "docs/backend/endpoints.json"))
    after = {f: hashlib.md5(open(f, "rb").read()).hexdigest() for f in watch}
    check("B8 真实仓库运行零写副作用（md5 全等）", before == after)
    check("B8 真实仓库解析到的 FAIL 行数 > 0（正向对照，坑 97/98）", len(tokens) > 0, "tokens=%s" % tokens)
    check("B8 真实仓库 A1（声明但未用）= 0", "A1" not in tokens, "tokens=%s" % tokens)
    check("B8 真实仓库 A2（未接收）= 已登记 4 条", tokens == ["A2"], "tokens=%s" % tokens)
    check("B8 定位率 25/25", "已定位端点 25 / 25" in out)
    check("B8 弱证据 0 条（解析器把链走到底）", "不可静态解析）条数（信息项，非漂移） | 0" in out)

    print()
    print("== 汇总：PASS %d / FAIL %d ==" % (PASS_CNT[0], FAIL_CNT[0]))
    return 0 if FAIL_CNT[0] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
