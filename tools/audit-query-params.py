#!/usr/bin/env python3
"""查询参数契约一致性审计（R32，只读）。

不变量：**每个端点的查询参数名集合**必须在多处真源逐端点一致 ——
与 `audit-contract-keys.py`（分页集合键名）、`audit-error-codes.py`（错误码）、
`audit-auth-contract.py`（鉴权级别）、`audit-routes.py`（方法+路径+路径变量名）同族，
换第五条契约不变量：**逐端点的查询参数名集合**。

  简称  来源                                                     承载方式
  ----  -------------------------------------------------------  ------------------------------------------
  M     docs/backend/endpoints.json                              逐端点 `query_params`（名单）
  D     docs/backend/02-API接口模型清单.md                       逐行「请求」/「请求/响应」列的 `q：…`
  O     docs/backend/openapi.yaml                                operation 下 `parameters` 中 `in: query`
  I     aap-server/src/main/java/**/*Controller.java              方法签名里的 `@RequestParam` 形参名
  C     aap-client/src/api/*.ts                                  GET 调用点的 `data:` 对象字面量键（弱证据）

为什么需要它（skill 坑 43 / 49 / 60 族）：
  * 契约测试只校验 JSON Schema —— **schema 里没有查询参数**（query 不是 body），204 例全绿也看不见；
  * 覆盖门禁 `EndpointCoverageTest` 只比 **Spring 路由注册表 ⇔ endpoints.json**（方法+路径，且把
    `{...}` 折叠），**完全不看查询参数**；
  * 路由审计（R31）把「方法+路径+路径变量名」钉住了，但**查询参数名**仍无人校验 ——
    而它是分页/筛选这类**跨页面通用字段**（skill 坑 1：客户端读法与后端字段名不一致 → 列表页整页空白）。
    真实后果：`pageSize` 被写成 `page_size`、`unread` 被写成 `isUnread` 时，**两套门禁全绿**，
    但客户端筛选静默失效（后端拿不到该参数 → 返回全量而非过滤结果）。

方向性（不是等价比对，避免假发现）：
  * M ⇔ D / M ⇔ O / M ⇔ I ：**双向**逐端点集合相等（四处都是契约侧，任一侧多写/少写都是漂移）；
  * C ⊆ M ：仅 **GET** 调用点可比（POST/PUT 的 `data` 是**请求体**不是查询参数，不参与比对），
    客户端解析不出的（`data: params` 变量形式）只记「未能静态判定」**信息项**，绝不当漂移（坑 58）。

**可选性（`?` / `required`）不参与硬断言**（只作信息项，理由见报告 A6）：
  §0 通用约定明写「请求 `page`（默认 1）/ `pageSize`（默认 20，上限 200）」＝缺省即容忍省略，
  md 的 `?` 表「客户端可省略」、openapi/Spring 的 `required: false` 表「服务端容忍省略」，
  两者语义不同但不矛盾；真正的必填校验在服务层（如 USE-02 `from`/`to` 必填 → E-1801），
  按 md 收窄成 `required = true` 反而会改变错误码路径（400 而非 E-1801）。故不作硬断言。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动。

用法：
  python tools/audit-query-params.py [--root <dir>] [--all]
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
REQ_PARAM_RE = re.compile(r"@RequestParam\b")
IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
Q_CELL_RE = re.compile(r"q\s*[：:]\s*(.*)$")
PAGING_SHORTHAND = ("分页",)          # md 里 `q：分页` = page + pageSize（§0 约定）


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


def key_of(method: str, path: str) -> tuple[str, str]:
    """跨源比对前**一律**过这个归一函数（skill 坑 57：两侧不归一 → 假发现）。"""
    return (method.upper(), norm_path(strip_prefix(path)))


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

def parse_manifest(p: Path) -> tuple[int, dict[str, dict]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    total = int(data.get("total", len(data.get("endpoints", []))))
    out: dict[str, dict] = {}
    for e in data["endpoints"]:
        names = {str(x).strip() for x in (e.get("query_params") or []) if str(x).strip()}
        out[e["id"]] = {"method": e["method"].upper(), "path": e["path"].strip(), "q": names}
    return total, out


# ---------------------------------------------------------------- D：md 清单

def split_row(ln: str) -> list[str]:
    """按**未被转义**的 `|` 切分（skill 坑 48）。"""
    cells = re.split(r"(?<!\\)\|", ln.strip("|"))
    return [c.replace("\\|", "|").strip() for c in cells]


def md_query_names(cell: str) -> tuple[set[str], str | None]:
    """从「请求」/「请求/响应」单元格取参数名集合 → (names, shorthand|None)。

    参数名一律写成反引号 token；`?` 后缀表可选（不参与硬断言，见文件头）。
    两种**非反引号**的既有写法也要认（否则是解析器假发现，skill 坑 46 族）：
      * `q：分页`            = §0 约定简写 → page + pageSize
      * `page/pageSize`      = QT-11 的斜杠写法（无 `q：` 前缀、无反引号）→ page + pageSize
    """
    m = Q_CELL_RE.search(cell)
    if m:
        seg = re.split(r"→|->", m.group(1))[0]
        names = set()
        for tok in re.findall(r"`([^`]+)`", seg):
            tok = tok.strip()
            if tok.endswith("?"):
                tok = tok[:-1]
            if IDENT_RE.match(tok):
                names.add(tok)
        if names:
            return names, None
        for s in PAGING_SHORTHAND:
            if s in seg:
                return {"page", "pageSize"}, s
        if re.search(r"\bpage\s*/\s*pageSize\b", seg):
            return {"page", "pageSize"}, "page/pageSize"
        return set(), None
    # 无 `q：` 前缀时**只**认 QT-11 的 `page/pageSize` 斜杠写法。
    # 这里绝不能做反引号提取：`body：`a` `b`` 这类请求体字段会被误当查询参数
    # （本审计第二版实测 → 11 条假漂移，含 CRED-02/PROV-02/QT-02/QT-08）。
    seg = re.split(r"→|->", cell)[0]
    if re.search(r"\bpage\s*/\s*pageSize\b", seg):
        return {"page", "pageSize"}, "page/pageSize"
    return set(), None


def parse_md_queries(p: Path) -> tuple[dict[str, set[str]], list[str], int]:
    """→ ({ID: 参数名集合}, problems, 用简写的端点数)。两套表头（10 列 / 7 列）都定位「请求」列（坑 49）。"""
    rows: dict[str, set[str]] = {}
    problems: list[str] = []
    shorthand_rows: list[str] = []
    header: list[str] | None = None
    for raw in p.read_text(encoding="utf-8").splitlines():
        ln = raw.strip()
        if not ln.startswith("|"):
            continue
        cells = split_row(ln)
        if cells and cells[0] == "ID":
            header = cells
            continue
        if header is None:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(header):
            continue                      # 非端点表（枚举字典等）
        row_id = cells[0]
        if not MD_ID_RE.match(row_id):
            continue
        col = None
        for cand in ("请求", "请求/响应"):
            if cand in header:
                col = cand
                break
        if col is None:
            problems.append(f"{row_id}: 当前表头无「请求」/「请求/响应」列（列序定位失败）")
            continue
        names, short = md_query_names(cells[header.index(col)])
        rows[row_id] = names
        if short:
            shorthand_rows.append(f"{row_id}({short})")
    return rows, problems, len(shorthand_rows)


# ---------------------------------------------------------------- O：openapi

def parse_openapi_queries(text: str) -> tuple[dict[str, set[str]], list[str]]:
    """→ ({operationId: query 参数名}, problems)。缩进必须逐层校验（skill 坑 44）。"""
    out: dict[str, set[str]] = {}
    problems: list[str] = []
    cur_path: str | None = None
    cur_method: str | None = None
    cur_op: str | None = None
    in_params = False
    cur_name: str | None = None
    for ln in text.splitlines():
        indent = len(ln) - len(ln.lstrip(" ")) if ln.strip() else 0
        m = re.match(r"^  (/[^\s:]*):\s*$", ln)
        if m:
            cur_path, cur_method, cur_op, in_params, cur_name = m.group(1), None, None, False, None
            continue
        m = re.match(r"^    (get|post|put|delete|patch):\s*$", ln)
        if m and cur_path:
            cur_method, cur_op, in_params, cur_name = m.group(1).upper(), None, False, None
            continue
        m = re.match(r"^      operationId:\s*(\S+)\s*$", ln)
        if m and cur_path and cur_method:
            cur_op = m.group(1)
            out.setdefault(cur_op, set())
            in_params, cur_name = False, None
            continue
        if cur_op is not None and ln.strip():
            if indent <= 6 and not re.match(r"^      (parameters|responses|security|tags|summary|description|x-aap-[\w-]+):", ln):
                in_params, cur_name = False, None
        m = re.match(r"^      parameters:\s*$", ln)
        if m and cur_op:
            in_params = True
            continue
        if in_params and cur_op:
            m = re.match(r"^        - name:\s*(\S+)\s*$", ln)
            if m:
                cur_name = m.group(1)
                continue
            m = re.match(r"^          in:\s*(\S+)\s*$", ln)
            if m:
                if m.group(1) == "query" and cur_name:
                    out[cur_op].add(cur_name)
                cur_name = None
                continue
    return out, problems


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


def skip_string(code: str, i: int) -> int:
    """i 指向引号，返回字符串结束后的下标（引号感知扫描的公共部分）。"""
    q, n, j = code[i], len(code), i + 1
    while j < n:
        if code[j] == "\\":
            j += 2
            continue
        if code[j] == q:
            return j + 1
        j += 1
    return n


def match_paren(code: str, open_idx: int) -> int:
    """从 `(` 起做引号感知的括号配对扫描，返回配对的 `)` 下标（-1 = 未闭合）。"""
    depth = 0
    i, n = open_idx, len(code)
    while i < n:
        c = code[i]
        if c in "'\"`":
            i = skip_string(code, i)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def body_brace(code: str, start: int) -> int:
    """方法体起点 = 从 start 起**括号深度 0 且不在字符串内**的第一个 `{`（skill 坑 55）。

    路径变量花括号（`@GetMapping("/{id}")`）在字符串里 → 不会被误判为方法体。
    """
    depth = 0
    i, n = start, len(code)
    while i < n:
        c = code[i]
        if c in "'\"`":
            i = skip_string(code, i)
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "{" and depth == 0:
            return i
        i += 1
    return -1


def req_param_name(sig: str, ann_end: int, close: int) -> tuple[str | None, bool]:
    """`@RequestParam(...)` → (参数名, required 标志)。

    显式 `name = "x"` / `value = "x"` / 位置实参优先；否则取注解之后、下一个顶层逗号（或签名右括号）
    之前的**最后一个标识符** = Java 形参名（本项目 78 处全部是 `(required = false) Type name` 写法）。
    """
    args = sig[ann_end:close + 1]
    explicit = re.search(r'(?:name|value)\s*=\s*"([^"]+)"', args)
    if explicit:
        return explicit.group(1), "required = false" not in args and "required=false" not in args
    positional = re.match(r'^\(\s*"([^"]+)"', args)
    if positional:
        return positional.group(1), "required = false" not in args
    required = not re.search(r"required\s*=\s*false", args)
    i, n, depth = close + 1, len(sig), 0
    while i < n:
        c = sig[i]
        if c in "'\"`":
            i = skip_string(sig, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    seg = sig[close + 1:i]
    toks = re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", seg)
    return (toks[-1] if toks else None), required


def parse_controllers(ctrl_dir: Path) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """→ ({(METHOD, 归一路径): {"q": 集合, "required": 集合}}, problems)。"""
    out: dict[tuple[str, str], dict] = {}
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
            k = m.end()
            while k < len(text) and text[k] in " \t\r\n":
                k += 1
            # 无实参的映射注解（如裸 `@GetMapping`）不能去 find(")")——会跳到下一个注解的右括号，
            # 让括号深度扫描从中间起步（深度为负）→ 方法体起点永远找不到（本审计首轮 11 条假异常）。
            if k < len(text) and text[k] == "(":
                close = match_paren(text, k)
                seg = text[k:close + 1] if close > 0 else ""
                sig_start = close + 1 if close > 0 else k
            else:
                close = m.end() - 1
                seg = ""
                sig_start = m.end()
            paths = re.findall(r'"([^"]*)"', seg)
            sub = paths[0] if paths else ""
            mbody = body_brace(text, sig_start)
            if mbody < 0:
                problems.append(f"{f.name}: {m.group(0)} 未定位到方法体起点")
                continue
            sig = text[m.end():mbody]
            names: set[str] = set()
            required: set[str] = set()
            for pm in REQ_PARAM_RE.finditer(sig):
                k = pm.end()
                while k < len(sig) and sig[k] in " \t\r\n":
                    k += 1
                if k >= len(sig) or sig[k] != "(":
                    problems.append(f"{f.name}: {m.group(0)} 的 @RequestParam 无实参列表")
                    continue
                pclose = match_paren(sig, k)
                if pclose < 0:
                    problems.append(f"{f.name}: @RequestParam( 未闭合")
                    continue
                name, req = req_param_name(sig, k, pclose)
                if not name:
                    problems.append(f"{f.name}: @RequestParam 未能解析形参名")
                    continue
                names.add(name)
                if req:
                    required.add(name)
            out[key_of(m.group(1), prefix + sub)] = {"q": names, "required": required}
            found += 1
        if found == 0:
            problems.append(f"{f.name}: 类内未解析到任何方法级映射注解")
    return out, problems


# ---------------------------------------------------------------- C：客户端调用点

def strip_comments(text: str) -> str:
    """去掉块注释与行注释，**保留字符串/模板字面量**（注释里的路径不是调用点，坑 58）。"""
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
            j = skip_string(text, i)
            out.append(text[i:j])
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def object_literal_keys(code: str, brace_idx: int) -> set[str] | None:
    """取 `{ ... }` 的**顶层**标识符键；不是对象字面量 → None。"""
    if brace_idx >= len(code) or code[brace_idx] != "{":
        return None
    depth, i, n = 0, brace_idx, len(code)
    keys: set[str] = set()
    end = None
    expect_key = True          # 只在「对象起点」或「顶层逗号之后」才认键（否则会把值的首标识符当键）
    while i < n:
        c = code[i]
        if c in "'\"`":
            i = skip_string(code, i)
            continue
        if c == "{":
            depth += 1
            i += 1
            continue
        if c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
            i += 1
            continue
        if depth == 1:
            if c == ",":
                expect_key = True
                i += 1
                continue
            if code[i:i + 3] == "...":
                return None        # 展开运算符 → 无法静态判定全部键
            if expect_key:
                m = re.match(r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*:", code[i:])
                if m:
                    keys.add(m.group(1))
                    expect_key = False
                    i += m.end()
                    continue
                m = re.match(r"\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*[,}]", code[i:])
                if m:
                    keys.add(m.group(1))
                    expect_key = False
                    i += m.end()
                    continue
                if c not in " \t\r\n":
                    return None    # 计算键 `[k]:` 等 → 未能静态判定
        i += 1
    if end is None:
        return None
    return keys


def var_object_keys(code: str, ident: str) -> set[str] | None:
    """同文件里 `const <ident> ... = { ... }` 的对象字面量键。"""
    for m in re.finditer(r"\b(?:const|let|var)\s+" + re.escape(ident) + r"\b", code):
        eq = code.find("=", m.end())
        if eq < 0:
            continue
        j = eq + 1
        while j < len(code) and code[j] in " \t\r\n":
            j += 1
        if j < len(code) and code[j] == "{":
            return object_literal_keys(code, j)
    return None


def parse_client_queries(client_dir: Path) -> tuple[dict[tuple[str, str], set[str]], list[str], list[str]]:
    """→ ({(METHOD, 路径): 查询参数名集合}, 未能静态判定描述, 被读文件)。只对 GET 生效（POST 的 data 是 body）。"""
    out: dict[tuple[str, str], set[str]] = {}
    unresolved: list[str] = []
    files: list[str] = []
    for f in sorted(client_dir.rglob("*.ts")):
        code = strip_comments(f.read_text(encoding="utf-8"))
        if not re.search(r"\bhttp\b", code):
            continue
        files.append(f.name)
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
                continue                      # 函数声明不是调用点（skill 坑 58①）
            if k >= n or code[k] != "(":
                continue
            end = match_paren(code, k)
            if end < 0:
                unresolved.append(f"{f.name}: http( 未闭合")
                continue
            call = code[k + 1:end]
            mm = re.search(r"method\s*:\s*['\"](\w+)['\"]", call)
            method = mm.group(1).upper() if mm else "GET"
            if method != "GET":
                continue                      # 非 GET 的 data 是请求体，不是查询参数
            dm = re.search(r"\bdata\s*:\s*", call)
            if not dm:
                continue                      # 无 data → 无查询参数（空集合，等价）
            j = dm.end()
            if j < len(call) and call[j] == "{":
                keys = object_literal_keys(call, j)
            else:
                vm = re.match(r"([A-Za-z_$][A-Za-z0-9_$]*)", call[j:])
                keys = var_object_keys(code, vm.group(1)) if vm else None
            first = call.split(",")[0].strip()
            if keys is None:
                unresolved.append(f"{f.name}: GET {first[:50]} 的 data 非对象字面量（未能静态判定）")
                continue
            p = first.strip("'\"`")
            p = re.sub(r"\$\{[^}]*\}", "{}", p)
            if not p.startswith("/"):
                unresolved.append(f"{f.name}: GET 路径表达式不可解析 {first[:50]}")
                continue
            out.setdefault(key_of(method, p), set()).update(keys)
    return out, unresolved, files


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

    total, m_eps = parse_manifest(paths["M"])
    d_q, d_problems, d_shorthand = parse_md_queries(paths["D"])
    o_q, o_problems = parse_openapi_queries(paths["O"].read_text(encoding="utf-8"))
    i_eps, i_problems = parse_controllers(ctrl_dir)
    c_q, c_unresolved, c_files = parse_client_queries(client_dir)

    m_key = {eid: key_of(v["method"], v["path"]) for eid, v in m_eps.items()}
    m_q = {eid: v["q"] for eid, v in m_eps.items()}
    n_with_q = sum(1 for eid in m_q if m_q[eid])

    r.info("--- 正向对照（解析器真的解析到了，skill 坑 46）---")
    r.check("A0a M 端点数 = total", total > 0 and len(m_eps) == total,
            f"total={total} parsed={len(m_eps)}")
    r.check("A0b D 行数 = total（裸 split 会漏行，坑 48）", len(d_q) == total,
            f"parsed={len(d_q)} 期望={total}")
    r.check("A0c O operation 数 = total", len(o_q) == total,
            f"parsed={len(o_q)} 期望={total}")
    r.check("A0d I 解析到控制器方法数 ≥ total", len(i_eps) >= total,
            f"parsed={len(i_eps)} 条（含无查询参数的方法）")
    # 本审计的**关键**正向对照：若一条查询参数都没解析出来，「0 漂移」毫无意义
    r.check("A0e 非空查询参数端点被真的解析出来（否则本审计空转）",
            n_with_q > 0 and len(d_q) == total and any(d_q.values()) and any(o_q.values()),
            f"M 非空 {n_with_q} 条；D 非空 {sum(1 for v in d_q.values() if v)} 条；"
            f"O 非空 {sum(1 for v in o_q.values() if v)} 条；I 非空 {sum(1 for v in i_eps.values() if v['q'])} 条")
    r.check("A0f I 解析无异常", not i_problems, "; ".join(i_problems[:5]))
    r.check("A0g O 解析无异常", not o_problems, "; ".join(o_problems[:5]))
    r.check("A0h D 解析无异常", not d_problems, "; ".join(d_problems[:5]))

    r.info("--- A1 md 清单 ⇔ endpoints.json（逐端点：查询参数名集合）---")
    d_drift = {eid: {"清单": sorted(m_q[eid]), "md": sorted(d_q.get(eid, set()))}
               for eid in sorted(m_q) if d_q.get(eid, set()) != m_q[eid]}
    r.check("A1 md 逐行 `q：…` = endpoints.json query_params", not d_drift,
            f"不一致 {len(d_drift)} 条")
    for eid, d in (list(d_drift.items()) if args.all else list(d_drift.items())[:12]):
        r.info(f"      · {eid}: 清单={d['清单']} md={d['md']}")

    r.info("--- A2 openapi ⇔ endpoints.json（逐端点：in: query 参数名集合）---")
    o_drift = {eid: {"清单": sorted(m_q[eid]), "openapi": sorted(o_q.get(eid, set()))}
               for eid in sorted(m_q) if o_q.get(eid, set()) != m_q[eid]}
    r.check("A2 openapi 每 operation 的 query 参数 = endpoints.json", not o_drift,
            f"不一致 {len(o_drift)} 条")
    for eid, d in (list(o_drift.items()) if args.all else list(o_drift.items())[:12]):
        r.info(f"      · {eid}: 清单={d['清单']} openapi={d['openapi']}")

    r.info("--- A3 实现 ⇔ 清单（逐端点：@RequestParam 形参名集合）---")
    unlocated = {eid: list(m_key[eid]) for eid in sorted(m_key) if m_key[eid] not in i_eps}
    i_drift = {eid: {"清单": sorted(m_q[eid]), "实现": sorted(i_eps[m_key[eid]]["q"])}
               for eid in sorted(m_q)
               if m_key[eid] in i_eps and i_eps[m_key[eid]]["q"] != m_q[eid]}
    r.check("A3a 清单每条端点都在实现里定位到同方法同路径的控制器方法", not unlocated,
            f"未定位 {len(unlocated)} 条")
    for eid, k in (list(unlocated.items()) if args.all else list(unlocated.items())[:12]):
        r.info(f"      · {eid}: 清单={k}")
    r.check("A3b 实现 @RequestParam 集合 = 清单 query_params", not i_drift,
            f"不一致 {len(i_drift)} 条")
    for eid, d in (list(i_drift.items()) if args.all else list(i_drift.items())[:12]):
        r.info(f"      · {eid}: 清单={d['清单']} 实现={d['实现']}")

    r.info("--- A4 客户端 GET 调用点 ⊆ 清单（客户端不得传清单外的查询参数）---")
    stray: dict[str, list[str]] = {}
    for k, names in sorted(c_q.items()):
        eids = [eid for eid, kk in m_key.items() if kk == k]
        if not eids:
            stray[f"{k[0]} {k[1]}"] = ["（该调用点不在清单内）"] + sorted(names)
            continue
        extra = sorted(names - m_q[eids[0]])
        if extra:
            stray[f"{k[0]} {k[1]}({eids[0]})"] = extra
    r.check("A4 客户端 GET 查询参数都在清单内", not stray, f"越界 {len(stray)} 处")
    for k, v in (list(stray.items()) if args.all else list(stray.items())[:12]):
        r.info(f"      · 客户端 {k} 多传：{v}")

    r.info("--- A6 可选性（信息项，不作硬断言；理由见文件头）---")
    opt_info = []
    for eid in sorted(m_key):
        impl = i_eps.get(m_key[eid])
        if impl and impl["required"]:
            opt_info.append(f"{eid}: 实现声明 required 的查询参数 {sorted(impl['required'])}")
    r.info(f"      · 实现里 `required = true`（不带 required=false）的查询参数：{len(opt_info)} 条"
           + (f" → {opt_info[:5]}" if opt_info else "（本项目一律 required = false，必填校验在服务层）"))

    r.info("--- 信息项（不算漂移）---")
    r.info(f"      · md 用 `q：分页` 简写（= page + pageSize，§0 约定）的端点 {d_shorthand} 条")
    if c_unresolved:
        r.info(f"      · 客户端未能静态判定的 GET 调用点 {len(c_unresolved)} 处（不当漂移）：{c_unresolved[:5]}")
    r.info(f"      · 客户端 GET 调用点中带 data 对象字面量的 {len(c_q)} 处（{len(c_files)} 个 api 文件）")

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
