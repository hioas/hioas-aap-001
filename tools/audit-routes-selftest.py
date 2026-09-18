#!/usr/bin/env python3
"""`tools/audit-routes.py` 的负向自测（R31）。

纪律（skill 坑 32 / 46）：**每个判定分支都要有反例**，且必须同时有**正向对照** ——
否则「审计一直在报错」会被误当成「审计很严格」，而「审计永远 0 发现」会被误当成「仓库很干净」。

覆盖的分支：
  case_positive                    全部一致 → 13 条断言全 PASS、rc=0（正向对照）
  case_repo_external_root          `--root` 指向仓库外路径也能正常显示（坑 34）
  case_zero_write                  跑完夹具指纹不变（只读保证）
  case_impl_prefix_stripped        **本次真实返工的回归守卫**：实现路由带 /api/v1 前缀、清单键已归一，
                                   若忘了 strip_prefix → A3 会把 6 条全报成「未定位」（假发现）
  case_http_declaration_not_call   **本次真实返工的回归守卫**：`export function http<T>(path: string…)`
                                   是声明不是调用点，不得进「未能静态判定」（否则是纯噪声）
  case_client_helper_template      客户端 `${path(id)}/child` + 文件内 `const path = …` 助手必须解析到
  case_client_comment_not_call     注释里的路径不是调用点（坑 29 族：注释会让「越界调用」假红）
  case_client_stray_call           A4：客户端调用清单里没有的路径
  case_client_method_drift         A4：路径对但方法不同（只比路径会漏）
  case_md_method_drift             A1：md「方法」列与清单不一致
  case_md_path_drift               A1：md「路径」列与清单不一致
  case_md_row_dropped              A0b：md 少一行（解析覆盖性正向对照）
  case_md_escaped_pipe             回归：单元格内 `\\|` 不得让该行被静默跳过（坑 48）
  case_md_same_as_above            正向：方法列 `同上` 继承上一行取值
  case_md_same_as_above_no_prev    `同上` 无上一行 → 必须报 A6 FAIL
  case_openapi_path_drift          A2：openapi 路径与清单不一致
  case_openapi_method_drift        A2：openapi 方法 key 与清单不一致
  case_impl_missing_route          A3：清单有、实现没有该路由
  case_pathvar_name_drift          A5：`{id}` vs `{credId}`（门禁把变量名折叠掉，只有本审计看得见）
  case_missing_source              源文件缺失 → 显式 FAIL、rc=1

夹具写在 $LOCALAPPDATA/Temp 下的**唯一时间戳目录**（不做递归删除，skill 坑 28），
以 `--root` 指向仓库外路径（skill 坑 34）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "audit-routes.py"
REPO = HERE.parent
TMP_BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Temp"
HEAD10 = ["ID", "方法", "路径", "鉴权", "请求", "响应", "错误码", "幂等/并发", "依据", "状态"]
HEAD7 = ["ID", "方法", "路径", "角色", "请求/响应", "错误码", "状态"]

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def strip_prefix(path: str) -> str:
    return path[len("/api/v1"):] if path.startswith("/api/v1/") else path


# ---------------------------------------------------------------- 夹具内容

def base_eps() -> list[dict]:
    def ep(eid, method, path):
        return {"id": eid, "method": method, "path": path, "tag": "Syn", "auth": "authenticated",
                "request_model": "x", "response_model": "y", "query_params": [],
                "error_codes": [], "source": "真源", "task": "T99"}

    return [
        ep("SYN-01", "POST", "/api/v1/syn/one"),
        ep("SYN-02", "GET", "/api/v1/syn/two"),
        ep("SYN-03", "PUT", "/api/v1/syn/three/{id}"),
        ep("SYN-04", "DELETE", "/api/v1/syn/three/{id}/child"),
        ep("SYN-05", "GET", "/api/v1/admin/syn-five"),
        ep("SYN-06", "POST", "/api/v1/admin/syn-six"),
    ]


def md_rows10(eps: list[dict]) -> list[list[str]]:
    rows = []
    for e in eps[:4]:
        rows.append([e["id"], e["method"], f"`{strip_prefix(e['path'])}`", "✅",
                     "—", "`R`", "", "", "真源", "T99"])
    return rows


def md_rows7(eps: list[dict]) -> list[list[str]]:
    rows = []
    for e in eps[4:]:
        rows.append([e["id"], e["method"], f"`{strip_prefix(e['path'])}`", "SUPER_ADMIN",
                     "→ `R`", "", "T99"])
    return rows


def md_text(rows10: list[list[str]], rows7: list[list[str]]) -> str:
    def table(header, rows):
        out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        out += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(out)

    return ("# 合成清单\n\n## 1. 供应商端\n\n" + table(HEAD10, rows10)
            + "\n\n## 2. 管理端\n\n" + table(HEAD7, rows7) + "\n")


def openapi_text(eps: list[dict]) -> str:
    lines = ["openapi: 3.0.3", "info:", "  title: syn", '  version: "1.0"', "paths:"]
    for e in eps:
        lines.append(f"  {strip_prefix(e['path'])}:")
        lines.append(f"    {e['method'].lower()}:")
        lines.append(f"      operationId: {e['id']}")
        lines.append("      responses:")
        lines.append('        "200":')
        lines.append("          description: ok")
    return "\n".join(lines) + "\n"


CTRL_SYN = """package com.hioas.aap.syn;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynController {

    @PostMapping("/one")
    public String one() {
        return "one";
    }

    @GetMapping("/two")
    public String two() {
        return "two";
    }

    @PutMapping("/three/{id}")
    public String three() {
        return "three";
    }

    @DeleteMapping("/three/{id}/child")
    public String child() {
        return "child";
    }
}
"""

CTRL_ADMIN = """package com.hioas.aap.syn;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/admin")
public class AdminSynController {

    @GetMapping("/syn-five")
    public String five() {
        return "five";
    }

    @PostMapping("/syn-six")
    public String six() {
        return "six";
    }
}
"""

CLIENT_TS = """/**
 * 合成客户端适配层。
 * 未接线（本页不调用）：GET /syn/comment-only-missing —— 注释里的路径不是调用点。
 */
import { http } from './http'

export interface RequestOptions { method?: 'GET' | 'POST' | 'PUT' | 'DELETE' }

export function http<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  return fetch(path, options) as Promise<T>
}

const path = (id: string) => `/syn/three/${encodeURIComponent(id)}`

export const synApi = {
  one() {
    return http<unknown>('/syn/one', { method: 'POST', data: {} })
  },
  two() {
    return http<unknown>('/syn/two')
  },
  three(id: string) {
    return http<unknown>(`${path(id)}`, { method: 'PUT', data: {} })
  },
  child(id: string) {
    return http<unknown>(`${path(id)}/child`, { method: 'DELETE' })
  }
}
"""


def write_fixture(root: Path, *, eps: list[dict] | None = None,
                  rows10: list[list[str]] | None = None, rows7: list[list[str]] | None = None,
                  oa: str | None = None, ctrls: dict[str, str] | None = None,
                  client: str | None = None, skip: tuple[str, ...] = ()) -> None:
    eps = eps if eps is not None else base_eps()
    rows10 = rows10 if rows10 is not None else md_rows10(eps)
    rows7 = rows7 if rows7 is not None else md_rows7(eps)
    docs = root / "docs/backend"
    docs.mkdir(parents=True, exist_ok=True)
    if "endpoints" not in skip:
        (docs / "endpoints.json").write_text(
            json.dumps({"total": len(eps), "endpoints": eps}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    if "openapi" not in skip:
        (docs / "openapi.yaml").write_text(oa if oa is not None else openapi_text(eps),
                                           encoding="utf-8")
    if "md" not in skip:
        (docs / "02-API接口模型清单.md").write_text(md_text(rows10, rows7), encoding="utf-8")
    if "ctrl" not in skip:
        cdir = root / "aap-server/src/main/java/com/hioas/aap/syn"
        cdir.mkdir(parents=True, exist_ok=True)
        for name, text in (ctrls if ctrls is not None else
                           {"SynController.java": CTRL_SYN, "AdminSynController.java": CTRL_ADMIN}).items():
            (cdir / name).write_text(text, encoding="utf-8")
    if "client" not in skip:
        cdir = root / "aap-client/src/api"
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "syn.ts").write_text(client if client is not None else CLIENT_TS, encoding="utf-8")


def build(name: str, **kw) -> Path:
    root = TMP_BASE / f"aap-routes-selftest-{name}-{int(time.time() * 1000)}"
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
        print("\n".join("    " + ln for ln in out.splitlines()[-18:]))
    return out


PASS13 = "断言 13 条：PASS 13，FAIL 0"
A1_OK = "A1 md 逐行「方法+路径」= endpoints.json（未归一前缀）：不一致 0 条"
A3_OK = "A3 清单每条端点都在实现里有同方法同路径的路由：未定位 0 条"
A4_OK = "A4 客户端每个调用点都在冻结清单内且方法一致：越界调用 0 个"
A5_OK = "A5 路径变量名序列逐端点一致（清单 / md / openapi）：不一致 0 条"


def main() -> int:
    global AUDIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default=str(AUDIT),
                    help="被测审计脚本（默认 tools/audit-routes.py；供注入缺陷做判别力测试）")
    args = ap.parse_args()
    AUDIT = Path(args.audit).resolve()
    print(f"夹具根目录：{TMP_BASE}")
    print(f"被测审计：{AUDIT}")

    # 1 正向对照 + 只读 + 仓库外路径 + 两条真实返工的回归守卫
    root = build("positive")
    fp_before = fingerprint_tree(root)
    out = case("case_positive", root, 0, PASS13)
    case("case_repo_external_root", root, 0, f"根目录：{str(root).replace(os.sep, '/')}")
    case("case_impl_prefix_stripped", root, 0, A3_OK)
    case("case_http_declaration_not_call", root, 0, "未能静态判定 0 处")
    case("case_client_helper_template", root, 0, "A0e C 解析到客户端调用点：parsed=4 个调用点")
    case("case_client_comment_not_call", root, 0, A4_OK)
    fp_after = fingerprint_tree(root)
    record("case_zero_write", fp_before == fp_after,
           f"夹具 {len(fp_before)} 个文件 (mtime,size,md5) 不变" if fp_before == fp_after else "有文件被改写")

    eps = base_eps()

    # 2 A4：客户端
    stray = CLIENT_TS.replace("return http<unknown>('/syn/two')",
                              "return http<unknown>('/syn/two')\n    return http<unknown>('/syn/nope')")
    case("case_client_stray_call", build("stray", client=stray), 1,
         "A4 客户端每个调用点都在冻结清单内且方法一致：越界调用 1 个")
    method_drift = CLIENT_TS.replace("return http<unknown>('/syn/two')",
                                     "return http<unknown>('/syn/two', { method: 'POST' })")
    case("case_client_method_drift", build("clientmethod", client=method_drift), 1,
         "A4 客户端每个调用点都在冻结清单内且方法一致：越界调用 1 个")

    # 3 A1 / A0b：md
    r10 = md_rows10(eps)
    case("case_md_method_drift", build("mdmethod", rows10=[[r10[0][0], "PUT"] + r10[0][2:]] + r10[1:]),
         1, "A1 md 逐行「方法+路径」= endpoints.json（未归一前缀）：不一致 1 条")
    case("case_md_path_drift", build("mdpath", rows10=r10[:3] + [[r10[3][0], r10[3][1],
         "`/syn/three/{id}/children`"] + r10[3][3:]]), 1,
         "A1 md 逐行「方法+路径」= endpoints.json（未归一前缀）：不一致 1 条")
    case("case_md_row_dropped", build("mddrop", rows10=r10[:3]), 1, "A0b D 行数 = total")
    rows_pipe = [r[:4] + [r[4] + " `{s:ENABLED\\|DISABLED}`"] + r[5:] for r in md_rows7(eps)]
    case("case_md_escaped_pipe", build("mdpipe", rows7=rows_pipe), 0, "A0b D 行数 = total（裸 split 会漏行，坑 48）：parsed=6 期望=6")
    eps_same = [dict(e, method="POST") if e["id"] in ("SYN-05", "SYN-06") else e for e in eps]
    rows7_same = [[md_rows7(eps_same)[0][0], "POST", md_rows7(eps_same)[0][2], "SUPER_ADMIN", "→ `R`", "", "T99"],
                  [md_rows7(eps_same)[1][0], "同上", md_rows7(eps_same)[1][2], "SUPER_ADMIN", "→ `R`", "", "T99"]]
    ctrl_admin_post = CTRL_ADMIN.replace('@GetMapping("/syn-five")', '@PostMapping("/syn-five")')
    ctrls_same = {"SynController.java": CTRL_SYN, "AdminSynController.java": ctrl_admin_post}
    case("case_md_same_as_above", build("mdsame", eps=eps_same, rows10=md_rows10(eps_same),
                                        rows7=rows7_same, ctrls=ctrls_same), 0, A1_OK)
    rows7_noprev = [[rows7_same[0][0], "同上"] + rows7_same[0][2:]] + rows7_same[1:]
    case("case_md_same_as_above_no_prev",
         build("mdnoprev", eps=eps_same, rows10=md_rows10(eps_same), rows7=rows7_noprev, ctrls=ctrls_same), 1,
         "A6 md 表头/行定位无异常")

    # 4 A2：openapi
    oa = openapi_text(eps)
    case("case_openapi_path_drift", build("oapath", oa=oa.replace("  /syn/two:", "  /syn/twos:")),
         1, "A2 openapi 每 operation 的「方法+路径」= endpoints.json：不一致 1 条")
    oa_method = oa.replace("  /syn/one:\n    post:", "  /syn/one:\n    put:")
    case("case_openapi_method_drift", build("oamethod", oa=oa_method), 1,
         "A2 openapi 每 operation 的「方法+路径」= endpoints.json：不一致 1 条")

    # 5 A3：实现
    ctrl_missing = CTRL_SYN.replace('''    @DeleteMapping("/three/{id}/child")
    public String child() {
        return "child";
    }
''', "")
    case("case_impl_missing_route",
         build("implmiss", ctrls={"SynController.java": ctrl_missing, "AdminSynController.java": CTRL_ADMIN}),
         1, "A3 清单每条端点都在实现里有同方法同路径的路由：未定位 1 条")

    # 6 A5：路径变量名（A1 已把变量名折叠，只有本审计看得见）
    case("case_pathvar_name_drift",
         build("var", rows10=[[r10[2][0], r10[2][1], "`/syn/three/{credId}`"] + r10[2][3:]] + r10[:2] + r10[3:]),
         1, "A5 路径变量名序列逐端点一致（清单 / md / openapi）：不一致 1 条")

    # 7 源文件缺失
    case("case_missing_source", build("nosrc", skip=("endpoints",)), 1, "源文件/目录缺失")

    print()
    npass = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}：{detail}")
    print(f"\n自测断言 {len(results)} 条：PASS {npass}，FAIL {len(results) - npass}")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
