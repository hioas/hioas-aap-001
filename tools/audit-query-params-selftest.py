#!/usr/bin/env python3
"""`tools/audit-query-params.py` 的负向自测（R32）。

纪律（skill 坑 32 / 46）：**每个判定分支都要有反例**，且必须同时有**正向对照** ——
否则「审计一直在报错」会被误当成「审计很严格」，而「审计永远 0 发现」会被误当成「仓库很干净」。

覆盖的分支：
  case_positive                  全部一致 → 14 条断言全 PASS、rc=0（正向对照）
  case_repo_external_root        `--root` 指向仓库外路径也能正常显示（坑 34）
  case_zero_write                跑完夹具指纹不变（只读保证）
  case_md_body_field_not_query   **本轮真实返工的回归守卫**：`body：`a` `b`` 是请求体字段，
                                 不得被当成查询参数（首轮实测 11 条假漂移：CRED-02/PROV-02/QT-02/QT-08…）
  case_md_paging_shorthand       正向：`q：分页` = page + pageSize（§0 约定）
  case_md_slash_paging           正向：`page/pageSize` 斜杠写法（无 `q：`、无反引号，QT-11 的真实写法）
  case_md_missing_param          A1：md 少写一个查询参数
  case_md_escaped_pipe           回归：单元格内 `\\|` 不得让该行被静默跳过（坑 48）
  case_openapi_missing_param     A2：openapi 少写一个 query 参数
  case_openapi_path_param_ok     正向：`in: path` 的参数**不得**算作查询参数（否则假漂移）
  case_impl_missing_param        A3b：实现少一个 `@RequestParam`
  case_impl_explicit_name        正向：`@RequestParam(name = "x")` 显式名要解析到（不是取形参名）
  case_impl_missing_route        A3a：清单有、实现没有该路由
  case_client_stray_query        A4：客户端 GET 传了清单外的查询参数
  case_client_non_get_ignored    正向：POST 的 `data` 是请求体，不参与查询参数比对
  case_client_var_data           正向：`data: params`（变量形式）只记「未能静态判定」，不算漂移（坑 58）
  case_missing_source            源文件缺失 → 显式 FAIL、rc=1
  teeth_body_brace_guard         **判别力实测**：把「无实参映射注解」的解析退回 find(")") 版
                                 → 正向夹具上 A0f 立刻转红（本轮首轮真实缺陷）
  teeth_object_keys_guard        **判别力实测**：把对象字面量键解析退回松散版（裸标识符也算键）
                                 → 正向夹具上 A4 报 `['params']`（与首轮真实输出一致）
  teeth_mutation_applied         两次注入必须**真的改到源码**（否则空转通过，skill 坑 41）

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
AUDIT = HERE / "audit-query-params.py"
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
    def ep(eid, method, path, q):
        return {"id": eid, "method": method, "path": path, "tag": "Syn", "auth": "authenticated",
                "request_model": "x", "response_model": "y", "query_params": list(q),
                "error_codes": [], "source": "真源", "task": "T99"}

    return [
        ep("SY-01", "GET", "/api/v1/syn", ["page", "pageSize"]),
        ep("SY-02", "POST", "/api/v1/syn/body", []),
        ep("SY-03", "GET", "/api/v1/syn/paged", ["page", "pageSize"]),
        ep("SY-04", "GET", "/api/v1/syn/slash", ["page", "pageSize"]),
        ep("SY-05", "DELETE", "/api/v1/syn/{id}", []),
        ep("SY-06", "GET", "/api/v1/admin/syn-records", ["quoteId"]),
    ]


def md_rows10(eps: list[dict]) -> list[list[str]]:
    """SY-01…05 的 10 列表；请求列刻意覆盖四种写法（含 `body：` 与 `—`）。"""
    req = {
        "SY-01": "q：`page` `pageSize`",
        "SY-02": "body：`a` `b`",
        "SY-03": "q：分页",
        "SY-04": "page/pageSize",
        "SY-05": "—",
    }
    return [[e["id"], e["method"], f"`{strip_prefix(e['path'])}`", "✅", req[e["id"]],
             "`R`", "", "", "真源", "T99"] for e in eps[:5]]


def md_rows7(eps: list[dict]) -> list[list[str]]:
    return [[e["id"], e["method"], f"`{strip_prefix(e['path'])}`", "SUPER_ADMIN",
             "q：`quoteId?` → `{items:[R]}`", "", "T99"] for e in eps[5:]]


def md_text(rows10: list[list[str]], rows7: list[list[str]]) -> str:
    def table(header, rows):
        out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        out += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(out)

    return ("# 合成清单\n\n## 1. 供应商端\n\n" + table(HEAD10, rows10)
            + "\n\n## 2. 管理端\n\n" + table(HEAD7, rows7) + "\n")


def openapi_text(eps: list[dict]) -> str:
    """SY-05 刻意带 `in: path` 参数：它**不得**被算作查询参数（正向对照）。"""
    lines = ["openapi: 3.0.3", "info:", "  title: syn", '  version: "1.0"', "paths:"]
    for e in eps:
        lines.append(f"  {strip_prefix(e['path'])}:")
        lines.append(f"    {e['method'].lower()}:")
        lines.append(f"      operationId: {e['id']}")
        params = list(e["query_params"])
        if params or "{" in e["path"]:
            lines.append("      parameters:")
            for name in params:
                lines.append(f"        - name: {name}")
                lines.append("          in: query")
                lines.append("          required: false")
            for vn in re.findall(r"\{([^}]*)\}", e["path"]):
                lines.append(f"        - name: {vn}")
                lines.append("          in: path")
                lines.append("          required: true")
        lines.append("      responses:")
        lines.append('        "200":')
        lines.append("          description: ok")
    return "\n".join(lines) + "\n"


CTRL_SYN = """package com.hioas.aap.syn;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynController {

    /** SY-01：**无实参的映射注解直接跟方法签名**（本项目真实写法，方法体定位的回归守卫）。 */
    @GetMapping
    public String list(@RequestParam(required = false) Integer page,
                       @RequestParam(required = false) Integer pageSize) {
        return "list";
    }

    @PostMapping("/body")
    @PreAuthorize("hasAnyRole('SUPPLIER')")
    public String body(@RequestBody String payload) {
        return "body";
    }

    /** SY-03：映射注解在前、@PreAuthorize 在后（本项目另一种真实写法，双窗口守卫）。 */
    @GetMapping("/paged")
    @PreAuthorize("hasAnyRole('SUPPLIER')")
    public String paged(@RequestParam(required = false) Integer page,
                        @RequestParam(required = false) Integer pageSize) {
        return "paged";
    }

    @GetMapping("/slash")
    public String slash(@RequestParam(required = false) Integer page,
                        @RequestParam(required = false) Integer pageSize) {
        return "slash";
    }

    @DeleteMapping("/{id}")
    public String remove(@PathVariable Long id) {
        return "removed";
    }
}
"""

CTRL_ADMIN = """package com.hioas.aap.syn;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/admin")
public class AdminSynController {

    @GetMapping("/syn-records")
    public String records(@RequestParam(required = false) String quoteId) {
        return "records";
    }
}
"""

CLIENT_TS = """/**
 * 合成客户端适配层。
 * 未接线（本页不调用）：GET /syn/slash —— 注释里的路径不是调用点。
 */
import { http } from './http'

export function http<T = unknown>(path: string, options: Record<string, unknown> = {}): Promise<T> {
  return fetch(path, options) as Promise<T>
}

export const synApi = {
  list(params?: { page?: number; pageSize?: number }) {
    return http<unknown>('/syn', { method: 'GET', data: { page: params?.page, pageSize: params?.pageSize } })
  },
  create(payload: Record<string, unknown>) {
    return http<unknown>('/syn/body', { method: 'POST', data: payload })
  },
  paged() {
    return http<unknown>('/syn/paged', { method: 'GET', data: { page: 1, pageSize: 20 } })
  },
  records() {
    return http<unknown>('/admin/syn-records', { method: 'GET', data: { quoteId: '1' } })
  },
  remove(id: string) {
    return http<unknown>(`/syn/${id}`, { method: 'DELETE' })
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
    root = TMP_BASE / f"aap-qparam-selftest-{name}-{int(time.time() * 1000)}"
    root.mkdir(parents=True, exist_ok=True)
    write_fixture(root, **kw)
    return root


def run_audit(root: Path, audit: Path | None = None) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(audit or AUDIT), "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "").replace("\r\n", "\n") + (p.stderr or "")


def fingerprint_tree(root: Path) -> dict:
    out = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            st = f.stat()
            out[str(f)] = (st.st_mtime_ns, st.st_size, hashlib.md5(f.read_bytes()).hexdigest())
    return out


def case(name: str, root: Path, want_rc: int, want: str, must_not: str = "",
         audit: Path | None = None) -> str:
    rc, out = run_audit(root, audit)
    ok = rc == want_rc and want in out and (not must_not or must_not not in out)
    detail = f"rc={rc}(期望 {want_rc}) 命中「{want}」={'是' if want in out else '否'}"
    if must_not:
        detail += f" 反证「{must_not}」={'出现(异常)' if must_not in out else '未出现'}"
    record(name, ok, detail)
    if not ok:
        print(f"    --- {name} 实际输出 ---")
        print("\n".join("    " + ln for ln in out.splitlines()[-18:]))
    return out


PASS14 = "断言 14 条：PASS 14，FAIL 0"
A1_OK = "A1 md 逐行 `q：…` = endpoints.json query_params：不一致 0 条"
A2_OK = "A2 openapi 每 operation 的 query 参数 = endpoints.json：不一致 0 条"
A3B_OK = "A3b 实现 @RequestParam 集合 = 清单 query_params：不一致 0 条"
A4_OK = "A4 客户端 GET 查询参数都在清单内：越界 0 处"

# ---------------------------------------------------------------- 判别力注入（本轮两条真实缺陷）
MUT_A_OLD = """            # 无实参的映射注解（如裸 `@GetMapping`）不能去 find(")")——会跳到下一个注解的右括号，
            # 让括号深度扫描从中间起步（深度为负）→ 方法体起点永远找不到（本审计首轮 11 条假异常）。
            if k < len(text) and text[k] == "(":
                close = match_paren(text, k)
                seg = text[k:close + 1] if close > 0 else ""
                sig_start = close + 1 if close > 0 else k
            else:
                close = m.end() - 1
                seg = ""
                sig_start = m.end()
"""
MUT_A_NEW = """            close = text.find(")", m.end())
            seg = text[m.end():close + 1] if close >= 0 else ""
            sig_start = close + 1 if close >= 0 else m.end()
"""

MUT_B_OLD = """            if expect_key:
                m = re.match(r"\\s*([A-Za-z_$][A-Za-z0-9_$]*)\\s*:", code[i:])
                if m:
                    keys.add(m.group(1))
                    expect_key = False
                    i += m.end()
                    continue
                m = re.match(r"\\s*([A-Za-z_$][A-Za-z0-9_$]*)\\s*[,}]", code[i:])
                if m:
                    keys.add(m.group(1))
                    expect_key = False
                    i += m.end()
                    continue
                if c not in " \\t\\r\\n":
                    return None    # 计算键 `[k]:` 等 → 未能静态判定
"""
MUT_B_NEW = """            m = re.match(r"([A-Za-z_$][A-Za-z0-9_$]*)\\s*:", code[i:])
            if m and (i == 0 or code[i - 1] in " ,{"):
                keys.add(m.group(1))
                i += m.end()
                continue
            m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", code[i:])
            if m and (i == 0 or code[i - 1] in " ,{"):
                keys.add(m.group(0))
                i += m.end()
                continue
"""


def mutate(dst: Path, *pairs: tuple[str, str]) -> list[str]:
    """把审计源码的若干片段替换成缺陷版；返回**未命中**的锚点列表（空 = 全部替换成功）。"""
    text = AUDIT.read_text(encoding="utf-8")
    missed = []
    for old, new in pairs:
        if old not in text:
            missed.append(old.strip().splitlines()[0][:60])
            continue
        text = text.replace(old, new, 1)
    dst.write_text(text, encoding="utf-8")
    return missed


def main() -> int:
    global AUDIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", default=str(AUDIT),
                    help="被测审计脚本（默认 tools/audit-query-params.py）")
    args = ap.parse_args()
    AUDIT = Path(args.audit).resolve()
    print(f"夹具根目录：{TMP_BASE}")
    print(f"被测审计：{AUDIT}")

    # 1 正向对照 + 只读 + 仓库外路径 + 三条真实返工的回归守卫
    root = build("positive")
    fp_before = fingerprint_tree(root)
    out_pos = case("case_positive", root, 0, PASS14)
    case("case_repo_external_root", root, 0, f"根目录：{str(root).replace(os.sep, '/')}")
    # 回归守卫 1：`body：`a` `b`` 不得被当成查询参数（否则 A1 报假漂移）
    record("case_md_body_field_not_query", A1_OK in out_pos,
           "md 请求体字段未被误当查询参数（SY-02 的 `body：` 单元格）")
    # 回归守卫 2：无实参映射注解 + 紧随的 @PreAuthorize（A0f/A3a 必须干净）
    record("case_mapping_no_args_annotation",
           "[PASS] A0f I 解析无异常" in out_pos and "A3a 清单每条端点都在实现里定位到同方法同路径的控制器方法：未定位 0 条" in out_pos,
           "裸 @GetMapping 直接跟签名（无 @PreAuthorize 间隔）的方法体定位正常")
    # 回归守卫 3：对象字面量只取键、不取值的首标识符（`{ page: params?.page }` → page）
    record("case_object_literal_value_not_key", A4_OK in out_pos,
           "`data: { page: params?.page, … }` 解析出的键 = {page,pageSize}")
    # 正向：`q：分页` 与 `page/pageSize` 两种写法都要认（SY-03 / SY-04）
    record("case_md_paging_notations", A1_OK in out_pos,
           "`q：分页`（§0 简写）与 `page/pageSize`（斜杠写法）都被识别")
    fp_after = fingerprint_tree(root)
    record("case_zero_write", fp_before == fp_after,
           f"夹具 {len(fp_before)} 个文件 (mtime,size,md5) 不变" if fp_before == fp_after else "有文件被改写")

    eps = base_eps()
    r10 = md_rows10(eps)

    # 2 A1 / A0b：md
    case("case_md_missing_param",
         build("mdmiss", rows10=[[r10[0][0], r10[0][1], r10[0][2], r10[0][3], "q：`page`"] + r10[0][5:]] + r10[1:]),
         1, "A1 md 逐行 `q：…` = endpoints.json query_params：不一致 1 条")
    rows_pipe = [r[:4] + [r[4] + " `{s:ENABLED\\|DISABLED}`"] + r[5:] for r in md_rows7(eps)]
    case("case_md_escaped_pipe", build("mdpipe", rows7=rows_pipe), 0,
         "A0b D 行数 = total（裸 split 会漏行，坑 48）：parsed=6 期望=6")

    # 3 A2：openapi（含 `in: path` 不算查询参数的正向对照）
    oa = openapi_text(eps)
    case("case_openapi_path_param_ok", build("oapath"), 0, A2_OK)
    case("case_openapi_missing_param",
         build("oamiss", oa=oa.replace("        - name: pageSize\n          in: query\n", "", 1)),
         1, "A2 openapi 每 operation 的 query 参数 = endpoints.json：不一致 1 条")

    # 4 A3：实现
    case("case_impl_missing_param",
         build("implmiss", ctrls={"SynController.java": CTRL_SYN.replace(
             "@RequestParam(required = false) Integer pageSize) {\n        return \"paged\";",
             "int unused) {\n        return \"paged\";"), "AdminSynController.java": CTRL_ADMIN}),
         1, "A3b 实现 @RequestParam 集合 = 清单 query_params：不一致 1 条")
    case("case_impl_explicit_name",
         build("implname", ctrls={"SynController.java": CTRL_SYN, "AdminSynController.java": CTRL_ADMIN.replace(
             "@RequestParam(required = false) String quoteId", '@RequestParam(name = "quoteId") String qid')}),
         0, A3B_OK)
    case("case_impl_missing_route",
         build("implroute", ctrls={"SynController.java": CTRL_SYN.replace('@GetMapping("/slash")', '@GetMapping("/slashed")'),
                                   "AdminSynController.java": CTRL_ADMIN}),
         1, "A3a 清单每条端点都在实现里定位到同方法同路径的控制器方法：未定位 1 条")

    # 5 A4：客户端
    stray = CLIENT_TS.replace("data: { page: params?.page, pageSize: params?.pageSize }",
                              "data: { page: params?.page, pageSize: params?.pageSize, unread: true }")
    case("case_client_stray_query", build("stray", client=stray), 1,
         "A4 客户端 GET 查询参数都在清单内：越界 1 处")
    non_get = CLIENT_TS.replace("data: payload })", "data: { a: 1, b: 2 } })")
    case("case_client_non_get_ignored", build("nonget", client=non_get), 0, A4_OK)
    var_data = CLIENT_TS.replace("data: { page: 1, pageSize: 20 }", "data: params")
    case("case_client_var_data", build("vardata", client=var_data), 0,
         "A4 客户端 GET 查询参数都在清单内：越界 0 处")

    # 6 源文件缺失
    case("case_missing_source", build("nosrc", skip=("endpoints",)), 1, "源文件/目录缺失")

    # 7 判别力实测：把本轮两条真实缺陷注入审计副本，正向夹具上必须立刻转红
    buggy_a = TMP_BASE / f"aap-qparam-buggyA-{int(time.time() * 1000)}.py"
    buggy_b = TMP_BASE / f"aap-qparam-buggyB-{int(time.time() * 1000)}.py"
    missed_a = mutate(buggy_a, (MUT_A_OLD, MUT_A_NEW))
    missed_b = mutate(buggy_b, (MUT_B_OLD, MUT_B_NEW))
    record("teeth_mutation_applied", not missed_a and not missed_b,
           f"未命中锚点：A={missed_a} B={missed_b}（非空即为空转，skill 坑 41）")
    if not missed_a:
        case("teeth_body_brace_guard", root, 1, "A0f I 解析无异常", audit=buggy_a)
    if not missed_b:
        case("teeth_object_keys_guard", root, 1, "A4 客户端 GET 查询参数都在清单内：越界 1 处", audit=buggy_b)

    print()
    npass = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}：{detail}")
    print(f"\n自测断言 {len(results)} 条：PASS {npass}，FAIL {len(results) - npass}")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
