#!/usr/bin/env python3
"""`tools/audit-auth-contract.py` 的负向自测（R30）。

纪律（skill 坑 32 / 46）：**每个判定分支都要有反例**，且必须同时有**正向对照** ——
否则「审计一直在报错」会被误当成「审计很严格」。

覆盖的分支：
  case_positive                 全部一致 → 17 条断言全 PASS、rc=0（正向对照）
  case_zero_write               跑完夹具指纹不变（只读保证）
  case_repo_external_root       `--root` 指向仓库外路径也能显示（坑 34）
  case_parser_pathvar_braces    回归：`/{id}` 的 `{` 不得被当成方法体 → 方法级 @PreAuthorize 必须解析到
  case_parser_order_before      回归：`@PreAuthorize` 写在映射注解**之前**也要解析到
  case_parser_class_inherit     正向：方法无注解时继承**类级** @PreAuthorize
  case_parser_alias             正向：`SUPPLIER` ≡ `PROVIDER` 别名归一后才比对
  case_md_same_as_above         正向：md 的 `同上` 继承上一行取值
  case_md_escaped_pipe          回归：单元格内 `\\|` 不得让该行被静默跳过（坑 48）
  case_md_same_as_above_no_prev `同上` 无上一行 → 必须报异常（A9 FAIL）
  case_anon_not_public          A3a：清单 anon 但实现没进 PUBLIC_PATHS
  case_anon_leak                A3b：非 anon 端点被放进 PUBLIC_PATHS（等于匿名可访问）
  case_anon_with_preauth        A4：anon 端点上多了 @PreAuthorize
  case_role_drift               A5：清单角色集合 ≠ 实现 @PreAuthorize 角色集合
  case_auth_only_restricted     A6：清单 `authenticated` 但实现收窄成角色限制
  case_openapi_anon_mismatch    A2：openapi `security: []` 与清单 anon 不一致
  case_md_anon_mismatch         A7：md `免` 行与清单 anon 不一致
  case_md_role_mismatch         A8：md 角色列与清单不一致
  case_route_unlocated          A1：清单端点定位不到实现路由（解析器覆盖性）
  case_missing_source           源文件缺失 → 显式 FAIL、rc=1

夹具写在 $LOCALAPPDATA/Temp 下的**唯一时间戳目录**（不做递归删除，skill 坑 28），
以 `--root` 指向仓库外路径（skill 坑 34）。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "audit-auth-contract.py"
REPO = HERE.parent

TMP_BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Temp"

HEAD10 = ["ID", "方法", "路径", "鉴权", "请求", "响应", "错误码", "幂等/并发", "依据", "状态"]
HEAD7 = ["ID", "方法", "路径", "角色", "请求/响应", "错误码", "状态"]

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


# ---------------------------------------------------------------- 夹具构造

def base_endpoints() -> list[dict]:
    def ep(eid, method, path, auth, task="T99"):
        return {"id": eid, "method": method, "path": path, "tag": "Syn", "auth": auth,
                "request_model": "x", "response_model": "y", "query_params": [],
                "error_codes": [], "source": "真源", "task": task}

    return [
        ep("SYN-01", "POST", "/api/v1/syn/one", "anon"),
        ep("SYN-02", "GET", "/api/v1/syn/two", "authenticated"),
        ep("SYN-03", "POST", "/api/v1/syn/three/{id}", "TECH_OPS,SUPER_ADMIN"),
        ep("SYN-04", "GET", "/api/v1/syn/four", "TECH_OPS,SUPER_ADMIN"),
        ep("SYN-05", "GET", "/api/v1/syn/five", "PROVIDER"),
        ep("SYN-06", "DELETE", "/api/v1/syn/six", "BIZ_OPERATOR,SUPER_ADMIN"),
    ]


def base_md_rows() -> list[tuple[list[str], list[list[str]]]]:
    rows10 = [
        ["SYN-01", "POST", "`/syn/one`", "免", "body `{a}`", "`R`", "", "", "真源", "T99"],
        ["SYN-02", "GET", "`/syn/two`", "✅", "—", "`R`", "", "", "真源", "T99"],
    ]
    rows7 = [
        ["SYN-03", "POST", "`/syn/three/{id}`", "TECH_OPS SUPER_ADMIN", "→ `R`", "", "T99"],
        ["SYN-04", "GET", "`/syn/four`", "同上", "→ `R`", "", "T99"],
        ["SYN-05", "GET", "`/syn/five`", "PROVIDER", "→ `R`", "", "T99"],
        ["SYN-06", "DELETE", "`/syn/six`", "BIZ_OPERATOR SUPER_ADMIN", "→ `R`", "", "T99"],
    ]
    return [(HEAD10, rows10), (HEAD7, rows7)]


def md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def openapi(eps: list[dict], anon_ids: set[str] | None = None) -> str:
    if anon_ids is None:
        anon_ids = {e["id"] for e in eps if e["auth"] == "anon"}
    out = ["openapi: 3.0.3", "paths:"]
    for e in eps:
        out += [f"  {e['path']}:", f"    {e['method'].lower()}:",
                f"      operationId: {e['id']}",
                "      tags:", "        - Syn"]
        if e["id"] in anon_ids:
            out.append("      security: []")
        else:
            out += ["      security:", "        - bearerAuth: []"]
        out += ["      responses:", "        200:", "          description: 成功"]
    return "\n".join(out) + "\n"


CONTROLLERS = {
    # 无类级 @PreAuthorize：anon / authenticated 两条
    "SynPublicController.java": """package com.hioas.aap.syn;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynPublicController {

    @PostMapping("/one")
    public String one() {
        return "one";
    }

    @GetMapping("/two")
    public String two() {
        return "two";
    }
}
""",
    # 类级 @PreAuthorize：SYN-03 方法级（映射注解在前、带路径变量）、SYN-04 继承类级
    "SynAdminController.java": """package com.hioas.aap.syn;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class SynAdminController {

    private final String marker = "x";

    @PostMapping("/three/{id}")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public String three(@PathVariable String id) {
        return id;
    }

    @GetMapping("/four")
    public String four() {
        return marker;
    }
}
""",
    # 类级别名：清单写 PROVIDER，实现写 SUPPLIER/PROVIDER
    "SynProviderController.java": """package com.hioas.aap.syn;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class SynProviderController {

    @GetMapping("/five")
    public String five() {
        return "five";
    }
}
""",
    # 注解写在映射注解**之前**
    "SynBizController.java": """package com.hioas.aap.syn;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynBizController {

    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    @DeleteMapping("/six")
    public String six() {
        return "six";
    }
}
""",
}


def write_fixture(root: Path, *, eps: list[dict] | None = None,
                  md_tables: list[tuple[list[str], list[list[str]]]] | None = None,
                  openapi_anon_ids: set[str] | None = None,
                  public_paths: list[str] | None = None,
                  controllers: dict[str, str] | None = None,
                  skip_endpoints: bool = False) -> None:
    eps = base_endpoints() if eps is None else eps
    md_tables = base_md_rows() if md_tables is None else md_tables
    public_paths = ["/actuator/health", "/api/v1/syn/one"] if public_paths is None else public_paths
    controllers = CONTROLLERS if controllers is None else controllers

    (root / "docs/backend").mkdir(parents=True, exist_ok=True)
    (root / "aap-server/src/main/java/com/hioas/aap/config").mkdir(parents=True, exist_ok=True)
    (root / "aap-server/src/main/java/com/hioas/aap/syn").mkdir(parents=True, exist_ok=True)

    if not skip_endpoints:
        (root / "docs/backend/endpoints.json").write_text(
            json.dumps({"total": len(eps), "endpoints": eps}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    (root / "docs/backend/openapi.yaml").write_text(openapi(eps, openapi_anon_ids), encoding="utf-8")

    md = ["# 夹具清单\n"]
    for header, rows in md_tables:
        md.append(md_table(header, rows))
    (root / "docs/backend/02-API接口模型清单.md").write_text("\n".join(md), encoding="utf-8")

    quoted = ", ".join(f'"{p}"' for p in public_paths)
    (root / "aap-server/src/main/java/com/hioas/aap/config/SecurityConfig.java").write_text(
        "package com.hioas.aap.config;\n\npublic class SecurityConfig {\n\n"
        f"    private static final String[] PUBLIC_PATHS = {{{quoted}}};\n}}\n", encoding="utf-8")

    for name, text in controllers.items():
        (root / "aap-server/src/main/java/com/hioas/aap/syn" / name).write_text(text, encoding="utf-8")


def build(name: str, **kw) -> Path:
    root = TMP_BASE / f"aap-auth-selftest-{name}-{int(time.time() * 1000)}"
    root.mkdir(parents=True, exist_ok=True)
    write_fixture(root, **kw)
    return root


def run_audit(root: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "").replace("\r\n", "\n") + (p.stderr or "")


def fingerprint_tree(root: Path) -> dict:
    out = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            st = f.stat()
            out[str(f)] = (st.st_mtime_ns, st.st_size, hashlib.md5(f.read_bytes()).hexdigest())
    return out


def case(name: str, root: Path, want_rc: int, want: str, must_not: str = "") -> str:
    rc, out = run_audit(root)
    ok = rc == want_rc and want in out and (not must_not or must_not not in out)
    detail = f"rc={rc}(期望 {want_rc}) 命中「{want}」={'是' if want in out else '否'}"
    if must_not:
        detail += f" 反证「{must_not}」={'出现(异常)' if must_not in out else '未出现'}"
    record(name, ok, detail)
    if not ok:
        print(f"    --- {name} 实际输出 ---")
        print("\n".join("    " + ln for ln in out.splitlines()[-16:]))
    return out


PASS17 = "断言 17 条：PASS 17，FAIL 0"
A5_OK = "A5 清单角色集合 = 实现 @PreAuthorize 角色集合（逐端点，别名归一）：不一致 0 条"


def main() -> int:
    print(f"夹具根目录：{TMP_BASE}")
    print(f"被测审计：{AUDIT.relative_to(REPO)}")

    # 1 正向对照 + 只读 + 仓库外路径
    root = build("positive")
    fp_before = fingerprint_tree(root)
    out = case("case_positive", root, 0, PASS17)
    case("case_repo_external_root", root, 0, f"根目录：{str(root).replace(os.sep, '/')}")
    fp_after = fingerprint_tree(root)
    record("case_zero_write", fp_before == fp_after,
           f"夹具 {len(fp_before)} 个文件 (mtime,size,md5) 不变" if fp_before == fp_after else "有文件被改写")

    # 2 解析器分支回归（首轮真实缺陷：`/{id}` 的 `{` 被当成方法体 → 22 条假发现）
    eps = base_endpoints()
    # 该夹具**去掉类级注解**，两个角色端点各自带方法级注解：
    # 若 `/{id}` 的 `{` 被当成方法体，SYN-03 的方法级注解就解析不到 → 必然报 A5 漂移（判别力）
    ctrl_pathvar = dict(CONTROLLERS)
    ctrl_pathvar["SynAdminController.java"] = """package com.hioas.aap.syn;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynAdminController {

    @PostMapping("/three/{id}")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public String three(@PathVariable String id) {
        return id;
    }

    @GetMapping("/four")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public String four() {
        return "four";
    }
}
"""
    case("case_parser_pathvar_braces", build("pathvar", controllers=ctrl_pathvar), 0, A5_OK)
    case("case_parser_order_before", build("orderbefore"), 0, A5_OK)
    case("case_parser_class_inherit", build("classinherit"), 0, A5_OK)
    case("case_parser_alias", build("alias"), 0, A5_OK)
    case("case_md_same_as_above", build("sameasabove"), 0, "A8 md「角色」列 = 清单角色集合")

    # 3 md 解析纪律
    rows7 = base_md_rows()[1][1]
    rows_pipe = [r[:4] + [r[4] + " `{s:ENABLED\\|DISABLED}`"] + r[5:] for r in rows7]
    case("case_md_escaped_pipe", build("pipe", md_tables=[base_md_rows()[0], (HEAD7, rows_pipe)]), 0,
         "A0b D 行数 = total：parsed=6 期望=6")
    rows_first_same = [["SYN-01", "POST", "`/syn/one`", "同上", "→ `R`", "", "T99"]]
    case("case_md_same_as_above_no_prev",
         build("noprev", md_tables=[base_md_rows()[0], (HEAD7, rows_first_same + rows7[1:])]), 1,
         "A9 md 表头定位无异常")

    # 4 各判定分支的反例
    case("case_anon_not_public", build("a3a", public_paths=["/actuator/health"]), 1,
         "A3a 清单 anon 的端点都在 SecurityConfig.PUBLIC_PATHS 里")
    case("case_anon_leak", build("a3b", public_paths=["/api/v1/syn/one", "/api/v1/syn/two"]), 1,
         "A3b 非 anon 的端点都不在 PUBLIC_PATHS 里")
    ctrl_anon_auth = dict(CONTROLLERS)
    ctrl_anon_auth["SynPublicController.java"] = CONTROLLERS["SynPublicController.java"].replace(
        '@PostMapping("/one")',
        '@PostMapping("/one")\n    @PreAuthorize("hasAnyRole(\'TECH_OPS\')")').replace(
        "import org.springframework.web.bind.annotation.GetMapping;",
        "import org.springframework.security.access.prepost.PreAuthorize;\nimport org.springframework.web.bind.annotation.GetMapping;")
    case("case_anon_with_preauth", build("a4", controllers=ctrl_anon_auth), 1,
         "A4 anon 端点上没有 @PreAuthorize")
    case("case_role_drift", build("a5", eps=[dict(e, auth="TECH_OPS") if e["id"] == "SYN-03" else e for e in eps]),
         1, "A5 清单角色集合 = 实现 @PreAuthorize 角色集合（逐端点，别名归一）：不一致 1 条")
    case("case_auth_only_restricted",
         build("a6", eps=[dict(e, auth="authenticated") if e["id"] == "SYN-03" else e for e in eps],
               md_tables=[base_md_rows()[0], (HEAD7, [["SYN-03", "POST", "`/syn/three/{id}`", "✅", "→ `R`", "", "T99"]] + base_md_rows()[1][1][1:])]),
         1, "A6 清单 `authenticated` 的端点实现里不带角色限制")
    case("case_openapi_anon_mismatch", build("a2", openapi_anon_ids={"SYN-01", "SYN-02"}), 1,
         "A2 openapi `security: []` 集合 = 清单 anon 集合")
    case("case_md_anon_mismatch",
         build("a7", md_tables=[(HEAD10, [base_md_rows()[0][1][0], ["SYN-02", "GET", "`/syn/two`", "免", "—", "`R`", "", "", "真源", "T99"]]), base_md_rows()[1]]),
         1, "A7 md 的 `免` 行集合 = 清单 anon 集合")
    case("case_md_role_mismatch",
         build("a8", md_tables=[base_md_rows()[0], (HEAD7, base_md_rows()[1][1][:2] + [["SYN-05", "GET", "`/syn/five`", "BIZ_OPERATOR", "→ `R`", "", "T99"]] + base_md_rows()[1][1][3:])]),
         1, "A8 md「角色」列 = 清单角色集合")
    case("case_route_unlocated",
         build("a1", eps=eps + [dict(eps[0], id="SYN-07", method="GET", path="/api/v1/syn/seven")],
               md_tables=base_md_rows()),
         1, "A1 清单每条端点都能在实现里定位到路由")

    # 5 源文件缺失
    case("case_missing_source", build("nosrc", skip_endpoints=True), 1, "源文件缺失")

    print()
    npass = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}：{detail}")
    print(f"\n自测断言 {len(results)} 条：PASS {npass}，FAIL {len(results) - npass}")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
