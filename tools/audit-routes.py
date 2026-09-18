#!/usr/bin/env python3
"""路由契约一致性审计（R31，只读）。

不变量：**每个端点的 (HTTP 方法, 路径, 路径变量名)** 必须在多处真源逐端点一致 ——
与 `audit-contract-keys.py`（分页集合键名）、`audit-error-codes.py`（错误码）、
`audit-auth-contract.py`（鉴权级别）同族，换第四条契约不变量：**路由本身**。

  简称  来源                                                     承载方式
  ----  -------------------------------------------------------  ----------------------------------------
  M     docs/backend/endpoints.json                              逐端点 `method` + `path`（含 /api/v1 前缀）
  D     docs/backend/02-API接口模型清单.md                       逐行「方法」「路径」列（10 列 / 7 列两套表头）
  O     docs/backend/openapi.yaml                                路径项下的 `get|post|put|delete|patch` + operationId
  I     aap-server/src/main/java/**/*Controller.java              类级 @RequestMapping 前缀 + 方法级映射注解
  C     aap-client/src/api/*.ts                                  `http(...)` 调用点（方法由 `method:` 推、缺省 GET）

为什么需要它（skill 坑 43 / 49 族）：
  * 契约测试只校验 JSON Schema —— **schema 里没有路径**，204 例全绿也看不见路径漂移；
  * 覆盖门禁 `EndpointCoverageTest` 只比 **Spring 路由注册表 ⇔ endpoints.json**（见其 normalize()），
    即 **md 清单 / openapi / 客户端 三处与清单的路由一致性从未被任何门禁覆盖**；
  * 该门禁的 normalize() 把 `{...}` 一律折叠成 `{}` → **路径变量名（`{id}` vs `{jobId}`）全仓库无人校验**，
    而变量名是客户端 codegen 与真实调用方拼 URL 的依据。

方向性（不是等价比对，避免假发现）：
  * M ⊆ I ：清单每条端点必须在实现里有**同方法同路径**的路由（清单是承诺）；
  * C ⊆ M ：客户端每个调用点必须在清单里有**同方法同路径**的端点（客户端不得打不存在的接口）；
  * 反向（实现里有、清单没有）只作**信息项**输出，不算漂移 —— 框架路由（/error 等）与内部路由正常存在。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动。

用法：
  python tools/audit-routes.py [--root <dir>] [--all]
  （--root 供负向自测指向仓库外的夹具目录，skill 坑 34）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REL_STATIC = [
    "docs/backend/endpoints.json",
    "docs/backend/openapi.yaml",
    "docs/backend/02-API接口模型清单.md",
]
CONTROLLER_DIR = "aap-server/src/main/java/com/hioas/aap"
CLIENT_DIR = "aap-client/src/api"
PREFIX = "/api/v1"

VAR_RE = re.compile(r"\{[^}]*\}")
MAPPING_RE = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")
REQ_MAPPING_RE = re.compile(r"@RequestMapping\s*\(([^)]*)\)")
CLASS_DECL_RE = re.compile(r"^[A-Za-z@\s]*\bclass\s+\w+", re.MULTILINE)
MD_ID_RE = re.compile(r"^[A-Z]+-[A-Z0-9]+$")
HTTP_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def rel_path(p: Path, root: Path) -> str:
    """仓库外路径也能显示（skill 坑 34）。"""
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve())).replace(os.sep, "/")
    except ValueError:
        return str(Path(p).resolve()).replace(os.sep, "/")


def fingerprint(paths: list[Path]) -> dict:
    out = {}
    for p in paths:
        if not p.exists():
            out[str(p)] = None
            continue
        st = p.stat()
        out[str(p)] = (st.st_mtime_ns, st.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    return out


def norm_path(path: str) -> str:
    return VAR_RE.sub("{}", path.strip())


def strip_prefix(path: str) -> str:
    p = path.strip()
    if p == PREFIX:
        return "/"
    if p.startswith(PREFIX + "/"):
        return p[len(PREFIX):]
    return p


def var_names(path: str) -> list[str]:
    """路径变量名序列（含空名也算，形状漂移不得静默）。"""
    return re.findall(r"\{([^}]*)\}", path)


class Result:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.npass = 0
        self.nfail = 0

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        if ok:
            self.npass += 1
        else:
            self.nfail += 1
        self.lines.append(f"[{tag}] {name}" + (f"：{detail}" if detail else ""))
        return ok

    def info(self, text: str) -> None:
        self.lines.append(text)


# ---------------------------------------------------------------- M：endpoints.json

def parse_manifest(p: Path) -> tuple[int, dict[str, tuple[str, str]]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    total = int(data.get("total", len(data.get("endpoints", []))))
    out = {e["id"]: (e["method"].upper(), e["path"].strip()) for e in data["endpoints"]}
    return total, out


# ---------------------------------------------------------------- D：md 清单

def split_row(ln: str) -> list[str]:
    """按**未被转义**的 `|` 切分（skill 坑 48）。"""
    cells = re.split(r"(?<!\\)\|", ln.strip("|"))
    return [c.replace("\\|", "|").strip() for c in cells]


def md_path_cell(cell: str) -> str:
    """路径列取值：优先取反引号里的 token（表格里路径一律写成 `` `/x/y` ``）。"""
    for tok in re.findall(r"`([^`]+)`", cell):
        if tok.startswith("/"):
            return tok
    return cell


def parse_md_routes(p: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """→ {ID: (方法, 路径)}；两套表头（10 列 / 7 列）都要定位到「方法」「路径」列（skill 坑 49）。

    `同上` 在方法列出现时继承**上一行**取值（与 audit-auth-contract 同约定）。
    """
    rows: dict[str, tuple[str, str]] = {}
    problems: list[str] = []
    header: list[str] | None = None
    last_method: str | None = None
    for raw in p.read_text(encoding="utf-8").splitlines():
        ln = raw.strip()
        if not ln.startswith("|"):
            continue
        cells = split_row(ln)
        if cells and cells[0] == "ID":
            header = cells
            last_method = None
            continue
        if header is None:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(header):
            continue          # 非端点表（枚举字典等）
        row_id = cells[0]
        if not MD_ID_RE.match(row_id):
            continue
        for col in ("方法", "路径"):
            if col not in header:
                problems.append(f"{row_id}: 当前表头无「{col}」列（列序定位失败）")
                break
        else:
            method = cells[header.index("方法")].strip()
            if method == "同上":
                if last_method is None:
                    problems.append(f"{row_id}: 方法列的 `同上` 无上一行可继承")
                    continue
                method = last_method
            last_method = method
            rows[row_id] = (method.upper(), md_path_cell(cells[header.index("路径")]))
    return rows, problems


# ---------------------------------------------------------------- O：openapi

def parse_openapi_routes(text: str) -> dict[str, tuple[str, str]]:
    """→ {operationId: (METHOD, 路径)}。缩进必须逐层校验（skill 坑 44）。"""
    out: dict[str, tuple[str, str]] = {}
    cur_path: str | None = None
    cur_method: str | None = None
    for ln in text.splitlines():
        m = re.match(r"^  (/[^\s:]*):\s*$", ln)
        if m:
            cur_path, cur_method = m.group(1), None
            continue
        m = re.match(r"^    (get|post|put|delete|patch):\s*$", ln)
        if m and cur_path:
            cur_method = m.group(1).upper()
            continue
        m = re.match(r"^      operationId:\s*(\S+)\s*$", ln)
        if m and cur_path and cur_method:
            out[m.group(1)] = (cur_method, cur_path)
    return out


# ---------------------------------------------------------------- I：控制器

def class_body_start(text: str) -> int:
    m = CLASS_DECL_RE.search(text)
    if not m:
        return -1
    brace = text.find("{", m.end())
    return brace if brace >= 0 else -1


def class_prefix(text: str, body: int) -> str:
    prefix = ""
    for m in REQ_MAPPING_RE.finditer(text[:body]):
        vals = re.findall(r'"([^"]*)"', m.group(1))
        if vals:
            prefix = vals[0]
    return prefix


def parse_controllers(ctrl_dir: Path) -> tuple[set[tuple[str, str]], list[str]]:
    """→ {(METHOD, 路径)}；方法级映射注解的路径 + 类级前缀。"""
    routes: set[tuple[str, str]] = set()
    problems: list[str] = []
    for f in sorted(ctrl_dir.rglob("*Controller.java")):
        text = f.read_text(encoding="utf-8")
        body = class_body_start(text)
        if body < 0:
            problems.append(f"{f.name}: 未定位到类声明")
            continue
        prefix = class_prefix(text, body)
        if not prefix:
            problems.append(f"{f.name}: 未解析到类级 @RequestMapping 前缀")
        found = 0
        for m in MAPPING_RE.finditer(text):
            if m.start() < body:
                continue
            close = text.find(")", m.end())
            seg = text[m.end():close + 1] if close >= 0 else ""
            paths = re.findall(r'"([^"]*)"', seg)
            sub = paths[0] if paths else ""
            routes.add((m.group(1).upper(), norm_path(prefix + sub)))
            found += 1
        if found == 0:
            problems.append(f"{f.name}: 类内未解析到任何方法级映射注解")
    return routes, problems


# ---------------------------------------------------------------- C：客户端调用点

def strip_comments(text: str) -> str:
    """去掉块注释与行注释，**保留字符串/模板字面量**（注释里的路径不是调用点，skill 坑 29 族）。"""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
        elif c in "'\"`":
            q, j = c, i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_paren(code: str, open_idx: int) -> int:
    """从 `(` 起做**引号感知**的括号配对扫描，返回配对的 `)` 下标（-1 = 未闭合）。"""
    depth = 0
    i, n = open_idx, len(code)
    while i < n:
        c = code[i]
        if c in "'\"`":
            q, j = c, i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == q:
                    j += 1
                    break
                j += 1
            i = j
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def parse_path_helper(code: str) -> str | None:
    """`const path = (id: string) => \\`/credentials/${encodeURIComponent(id)}\\`` → 归一模板。"""
    m = re.search(r"\b(?:const|function)\s+path\b[^\n]*?=>\s*`([^`]*)`", code)
    if not m:
        m = re.search(r"\bfunction\s+path\s*\([^)]*\)\s*\{\s*return\s*`([^`]*)`", code)
    if not m:
        return None
    return VAR_RE.sub("{}", re.sub(r"\$\{[^}]*\}", "{}", m.group(1)))


def resolve_path_expr(expr: str, helper: str | None) -> str | None:
    """把 http(...) 的第一个实参解析成路径模板；解析不出 → None（记为「未能静态判定」，不当漂移）。"""
    e = expr.strip()
    if not e:
        return None
    if e[0] in "'\"":
        return e[1:-1]
    if e[0] == "`":
        body = e[1:-1]
        if helper is not None:
            body = re.sub(r"\$\{\s*path\s*\([^)]*\)\s*\}", helper, body)
        body = re.sub(r"\$\{[^}]*\}", "{}", body)
        return body
    if re.match(r"^path\s*\(", e):
        return helper
    return None


def parse_client_calls(client_dir: Path) -> tuple[set[tuple[str, str]], list[str], list[str]]:
    """→ ({(METHOD, 路径)}, 未能静态判定的调用点描述, 被跳过的文件)。

    只认「形如 http(...) 的调用」：本项目 api 层一律 `http<T>(path, { method })`，缺省 GET。
    """
    calls: set[tuple[str, str]] = set()
    unresolved: list[str] = []
    files: list[str] = []
    for f in sorted(client_dir.rglob("*.ts")):
        raw = f.read_text(encoding="utf-8")
        code = strip_comments(raw)
        if not re.search(r"\bhttp\b", code):
            continue
        files.append(f.name)
        helper = parse_path_helper(code)
        for m in re.finditer(r"\bhttp\b", code):
            k = m.end()
            n = len(code)
            while k < n and code[k] in " \t\r\n":
                k += 1
            if k < n and code[k] == "<":
                depth = 0
                while k < n:
                    if code[k] == "<":
                        depth += 1
                    elif code[k] == ">":
                        depth -= 1
                        if depth == 0:
                            k += 1
                            break
                    k += 1
                while k < n and code[k] in " \t\r\n":
                    k += 1
            if re.search(r"function\s*$", code[:m.start()]):
                continue          # 函数声明 `function http<T>(path: string, ...)` 不是调用点
            if k >= n or code[k] != "(":
                continue          # 不是调用（如类型声明）
            end = match_paren(code, k)
            if end < 0:
                unresolved.append(f"{f.name}: http( 未闭合")
                continue
            call = code[k + 1:end]
            # 第一个顶层实参 = 路径表达式
            depth = 0
            i, cut = 0, len(call)
            while i < len(call):
                c = call[i]
                if c in "'\"`":
                    q, j = c, i + 1
                    while j < len(call):
                        if call[j] == "\\":
                            j += 2
                            continue
                        if call[j] == q:
                            j += 1
                            break
                        j += 1
                    i = j
                    continue
                if c in "([{":
                    depth += 1
                elif c in ")]}":
                    depth -= 1
                elif c == "," and depth == 0:
                    cut = i
                    break
                i += 1
            first = call[:cut]
            rest = call[cut:]
            mm = re.search(r"method\s*:\s*['\"](\w+)['\"]", rest)
            method = mm.group(1).upper() if mm else "GET"
            path = resolve_path_expr(first, helper)
            if path is None:
                unresolved.append(f"{f.name}: {first.strip()[:60]}")
                continue
            calls.add((method, norm_path(strip_prefix(path))))
    return calls, unresolved, files


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--all", action="store_true", help="列出全部漂移明细（默认只列前 12 条）")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    paths = {k: root / r for k, r in zip(["M", "O", "D"], REL_STATIC)}
    ctrl_dir = root / CONTROLLER_DIR
    client_dir = root / CLIENT_DIR

    missing = [k for k, p in paths.items() if not p.exists()]
    if not ctrl_dir.exists():
        missing.append("I=" + str(ctrl_dir))
    if not client_dir.exists():
        missing.append("C=" + str(client_dir))
    if missing:
        print("[FAIL] 源文件/目录缺失：" + ", ".join(
            f"{k}={paths.get(k, ctrl_dir)}" for k in missing))
        return 1

    watched = list(paths.values()) + sorted(ctrl_dir.rglob("*.java")) + sorted(client_dir.rglob("*.ts"))
    before = fingerprint(watched)

    r = Result()
    r.info(f"根目录：{str(root).replace(os.sep, '/')}（仓库外路径也照常显示，skill 坑 34）")

    total, m_route = parse_manifest(paths["M"])
    o_route = parse_openapi_routes(paths["O"].read_text(encoding="utf-8"))
    d_route, d_problems = parse_md_routes(paths["D"])
    impl, i_problems = parse_controllers(ctrl_dir)
    calls, c_unresolved, c_files = parse_client_calls(client_dir)

    r.info("--- 正向对照（解析器真的解析到了，skill 坑 46）---")
    r.check("A0a M 端点数 = total", total > 0 and len(m_route) == total,
            f"total={total} parsed={len(m_route)}")
    r.check("A0b D 行数 = total（裸 split 会漏行，坑 48）", len(d_route) == total,
            f"parsed={len(d_route)} 期望={total}")
    r.check("A0c O operation 数 = total", len(o_route) == total,
            f"parsed={len(o_route)} 期望={total}")
    r.check("A0d I 解析到控制器路由", len(impl) > 0, f"parsed={len(impl)} 条路由")
    r.check("A0e C 解析到客户端调用点", len(calls) > 0,
            f"parsed={len(calls)} 个调用点（{len(c_files)} 个文件）；未能静态判定 {len(c_unresolved)} 处")
    r.check("A0f I 解析无异常", not i_problems, "; ".join(i_problems[:5]))

    def key_of(route: tuple[str, str]) -> tuple[str, str]:
        return (route[0].upper(), norm_path(strip_prefix(route[1])))

    m_key = {eid: key_of(v) for eid, v in m_route.items()}
    d_key = {eid: key_of(v) for eid, v in d_route.items()}
    o_key = {eid: key_of(v) for eid, v in o_route.items()}

    r.info("--- A1 md 清单 ⇔ endpoints.json（逐端点：方法 + 路径）---")
    d_drift = {eid: {"清单": list(m_key[eid]), "md": list(d_key.get(eid, ("?", "?")))}
               for eid in sorted(m_key) if d_key.get(eid) != m_key[eid]}
    r.check("A1 md 逐行「方法+路径」= endpoints.json（未归一前缀）", not d_drift,
            f"不一致 {len(d_drift)} 条")
    for eid, d in (list(d_drift.items()) if args.all else list(d_drift.items())[:12]):
        r.info(f"      · {eid}: 清单={d['清单']} md={d['md']}")

    r.info("--- A2 openapi ⇔ endpoints.json（逐端点：方法 + 路径）---")
    o_drift = {eid: {"清单": list(m_key[eid]), "openapi": list(o_key.get(eid, ("?", "?")))}
               for eid in sorted(m_key) if o_key.get(eid) != m_key[eid]}
    r.check("A2 openapi 每 operation 的「方法+路径」= endpoints.json", not o_drift,
            f"不一致 {len(o_drift)} 条")
    for eid, d in (list(o_drift.items()) if args.all else list(o_drift.items())[:12]):
        r.info(f"      · {eid}: 清单={d['清单']} openapi={d['openapi']}")

    r.info("--- A3 清单 ⊆ 实现（逐端点定位到同方法同路径的 Spring 路由）---")
    impl_key = {key_of(k) for k in impl}
    unlocated = {eid: list(m_key[eid]) for eid in sorted(m_key) if m_key[eid] not in impl_key}
    r.check("A3 清单每条端点都在实现里有同方法同路径的路由", not unlocated,
            f"未定位 {len(unlocated)} 条")
    for eid, k in (list(unlocated.items()) if args.all else list(unlocated.items())[:12]):
        r.info(f"      · {eid}: 清单={k}")

    r.info("--- A4 客户端 ⊆ 清单（客户端不得调用清单里没有的接口）---")
    stray = sorted(k for k in calls if k not in set(m_key.values()))
    r.check("A4 客户端每个调用点都在冻结清单内且方法一致", not stray,
            f"越界调用 {len(stray)} 个")
    for k in (stray if args.all else stray[:12]):
        r.info(f"      · 客户端 {k[0]} {k[1]} 不在清单中")

    r.info("--- A5 路径变量名（`{id}` vs `{jobId}`）逐端点一致（门禁把变量名折叠掉了）---")
    var_drift: dict[str, dict] = {}
    for eid in sorted(m_key):
        want = var_names(strip_prefix(m_route[eid][1]))
        got_d = var_names(strip_prefix(d_route[eid][1])) if eid in d_route else None
        got_o = var_names(strip_prefix(o_route[eid][1])) if eid in o_route else None
        bad = {}
        if got_d is not None and got_d != want:
            bad["md"] = got_d
        if got_o is not None and got_o != want:
            bad["openapi"] = got_o
        if bad:
            var_drift[eid] = {"清单": want, **bad}
    r.check("A5 路径变量名序列逐端点一致（清单 / md / openapi）", not var_drift,
            f"不一致 {len(var_drift)} 条")
    for eid, d in (list(var_drift.items()) if args.all else list(var_drift.items())[:12]):
        r.info(f"      · {eid}: 清单={d['清单']} 其余={ {k: v for k, v in d.items() if k != '清单'} }")

    r.check("A6 md 表头/行定位无异常", not d_problems, "; ".join(d_problems[:5]))

    r.info("--- 信息项（不算漂移）---")
    extra = sorted(k for k in impl_key if k not in set(m_key.values()))
    r.info(f"      · 实现里注册但清单未声明的路由 {len(extra)} 条（框架/内部路由属正常）：{extra[:8]}")
    wired = {k for k in calls}
    unwired = sorted(eid for eid, k in m_key.items() if k not in wired)
    r.info(f"      · 客户端未接线的清单端点 {len(unwired)} 条（适配层按页面逐步接线，属正常）")
    if c_unresolved:
        r.info(f"      · 客户端未能静态判定的调用点 {len(c_unresolved)} 处（不当漂移）：{c_unresolved[:5]}")

    r.info("--- 零写副作用自检 ---")
    after = fingerprint(watched)
    changed = [rel_path(Path(k), root) for k in before if before[k] != after[k]]
    r.check("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed,
            f"被改写={len(changed)} 个：{changed[:5]}")

    print("\n".join(r.lines))
    print(f"\n断言 {r.npass + r.nfail} 条：PASS {r.npass}，FAIL {r.nfail}")
    return 0 if r.nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
