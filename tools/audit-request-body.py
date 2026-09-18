#!/usr/bin/env python3
"""请求体**字段名集合 / 有无请求体**契约一致性审计（R39，只读）。

不变量：**每个端点的「有没有请求体」与「请求体字段名集合」在五处真源里必须一致**。
与 `audit-contract-keys.py`（分页集合键名）、`audit-routes.py`（方法/路径/路径变量名）、
`audit-query-params.py`（查询参数名）、`audit-error-codes.py`（错误码）、`audit-time-format.py`
（时间格式）、`audit-enum-sets.py`（枚举取值集合）、`audit-response-shape.py`（响应形状）、
`audit-id-types.py`（ID 对外类型）同族，换**第十四条契约不变量：请求体字段名集合**。

  简称  来源                                                          承载方式
  ----  ------------------------------------------------------------  ----------------------------------
  M     docs/backend/02-API接口模型清单.md                             「请求」列（`body：`/`{...}`/`—`/`→`）
  D     docs/backend/endpoints.json + json-schema/requests/*.json      `request_model` → 请求模型 schema 属性
  O     docs/backend/openapi.yaml                                     `requestBody` 存在性 + 组件 `$ref` → 文件属性
  I     aap-server/src/main/java/**/*Controller.java                  `@RequestBody` DTO 的 record 分量名
  C     aap-client/src/**/*.ts                                        请求调用的 `data:` 对象字面量键（弱证据，仅 GET 之外）

为什么需要它（skill 坑 43 / 62 / 73 族）：
  * 契约测试把**真实响应**与 JSON Schema 比对 —— 请求模型 schema 只用于**入参校验**，
    「schema 里多一个没人绑定的字段」「实现 DTO 与 schema 字段名不同」这类漂移
    在响应侧完全看不见；
  * 覆盖门禁只比「方法 + 路径」；
  * 客户端 `data:` 键不被任何测试读取/执行 → 客户端按 schema 发字段而实现按另一个名字绑定，
    表现为**字段被静默忽略**（HTTP 200、库里没变），排查成本极高（坑 1 同族）。

方向性（避免假发现，skill 坑 29 / 46 / 57 / 75）：
  * 每个源都配 **`> 0` 的正向对照**（A0a…A0e）与「真的比对了 N 条端点」的正向对照（A5b）；
  * md 的「请求」列有**多种写法**（本项目实测 6 类）：只解析**无歧义**写法，
    `同 CRED-02 的可写子集`、`八大单价 + …`、`…` 这类**描述式/引用式**一律记
    「未能静态判定」信息项，**绝不当漂移**（坑 65：先 grep 出全部写法再写解析器）；
  * md 单元格可能有**转义竖线**（`` `{target_status:ENABLED\|DISABLED}` ``），
    必须按**未转义**的 `|` 切分并还原字面竖线（坑 48）；
  * `@RequestBody` 可能带实参（`@RequestBody(required = false)`）或换行 —— 必须先
    `match_paren` 跳过实参再取类型（坑 55 / 63：注解实参里的括号会吃掉方法体扫描）；
  * 客户端对象字面量只在**键位置**取键（`expect_key`），值位置的裸标识符不算（坑 64）。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动（Z1）。

用法：
  python tools/audit-request-body.py [--root <dir>] [--all]
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

MD_DOC = "docs/backend/02-API接口模型清单.md"
ENDPOINTS = "docs/backend/endpoints.json"
OPENAPI = "docs/backend/openapi.yaml"
REQ_SCHEMA_DIR = "docs/backend/json-schema/requests"
JAVA_DIR = "aap-server/src/main/java/com/hioas/aap"
CLIENT_DIR = "aap-client/src"

ID_CELL_RE = re.compile(r"^[A-Z][A-Z0-9]*-(?:[A-Z]*\d+|[A-Z0-9]+)$")
GENERIC_BODY_TYPES = {"Map", "Object", "JsonNode", "JsonObject", "Map<String,Object>"}

# 请求体字段名的合法形状（契约一律 snake_case / camelCase，见 §0）
FIELD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


def match_paren(s: str, i: int) -> int:
    """`s[i] == '('` → 返回配对 `)` 的下标；找不到返回 -1（坑 55 / 63 的正确实现）。"""
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j
    return -1


def norm_key(method: str, path: str) -> tuple[str, str]:
    """跨源比对**唯一**的归一函数（坑 57：两侧必须走同一个归一，否则报出整批假发现）。

    去 `/api/v1` 前缀 + 路径变量折叠成 `{}`。
    """
    p = path.replace("/api/v1", "", 1)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if not p.startswith("/"):
        p = "/" + p
    return method.upper(), p


def body_start(s: str, i: int) -> int:
    """括号深度扫描定位方法体 `{`（字符串里的 `{}` 天然成对，不会误判，坑 55）。"""
    d = 0
    for j in range(i, len(s)):
        c = s[j]
        if c == "{":
            if d == 0:
                return j
            d += 1
        elif c == "}":
            d -= 1
    return -1


def split_md_row(line: str) -> list[str]:
    """按**未转义**的 `|` 切分并还原字面竖线（坑 48）。"""
    cells = re.split(r"(?<!\\)\|", line)
    out = [c.replace("\\|", "|") for c in cells]
    if out and out[0].strip() == "":
        out = out[1:]
    if out and out[-1].strip() == "":
        out = out[:-1]
    return [c.strip() for c in out]


def top_level_keys(inner: str) -> list[str | None]:
    """对象字面量/花括号内容 → **最外层**键名列表（`None` = 该项不可静态判定）。

    只在「对象起点 / 顶层逗号之后」认键（坑 64）：`items:[{a,b}]` → `['items']`；
    `...rest` 或计算键 → `None`。
    """
    out: list[str | None] = []
    depth, cur = 0, ""
    parts: list[str] = []
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    parts.append(cur)
    for text in parts:
        s = text.strip()
        if not s:
            continue
        if s.startswith("...") or s.startswith("["):
            out.append(None)
            continue
        m = re.match(r"^([A-Za-z_]\w*)\s*(?::|$|\?)", s)
        out.append(m.group(1) if m else None)
    return out


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


# ------------------------------------------------------------------ M：md 清单「请求」列

def parse_md_bodies(root: Path) -> tuple[dict, dict, list[Path]]:
    """→ ({端点ID: frozenset(字段名)}, {端点ID: 未能静态判定原因}, 读过的文件)。"""
    p = root / MD_DOC
    bodies: dict[str, frozenset] = {}
    undecided: dict[str, str] = {}
    read: list[Path] = []
    if not p.exists():
        return bodies, undecided, read
    read.append(p)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

    col_req = None
    for ln in lines:
        if not ln.lstrip().startswith("|"):
            continue
        cells = split_md_row(ln)
        if len(cells) < 6:
            continue
        if cells[0] == "ID" and ("请求" in cells or "请求/响应" in cells):
            # 表头：定位「请求」列（10 列表）或「请求/响应」列（7 列表）
            if "请求" in cells:
                col_req = cells.index("请求")
            else:
                col_req = cells.index("请求/响应")
            continue
        if col_req is None or len(cells) <= col_req or len(cells) < 3:
            continue
        eid = cells[0]
        if not ID_CELL_RE.match(eid):
            continue
        cell = cells[col_req]
        if "q：" in cell:
            # GET 端点的「请求」列承载的是**查询参数**（q：…），属查询参数审计的不变量（坑 62），
            # 不是请求体 —— 记为「无请求体」而不是「未能静态判定」。
            bodies[eid] = frozenset()
            continue
        body = cell.split("→")[0].strip() if "→" in cell else cell.strip()
        if cell.strip().startswith("→") or body in ("", "—", "-", "—（无请求体）", "无"):
            bodies[eid] = frozenset()
            continue
        if "同 " in body or "同上" in body:
            undecided[eid] = f"引用式写法（{body[:40]}）"
            continue
        fields: set[str] = set()
        residual = body
        # 花括号式：body {a?,b:ENUM}；**只取最外层对象的键**，嵌套对象/数组元素的键记信息项
        # （嵌套键由元素 schema 校验，不能当成本层的请求体字段 —— 真实返工：QT-05
        #   `{items:[{model_name,model_alias?}]}` 曾被扁平化成 4 个字段 → 假漂移）
        while True:
            bi = residual.find("{")
            if bi < 0:
                break
            depth, end = 0, -1
            for j in range(bi, len(residual)):
                if residual[j] == "{":
                    depth += 1
                elif residual[j] == "}":
                    depth -= 1
                    if depth == 0:
                        end = j
                        break
            if end < 0:
                undecided[eid] = "花括号不配对（无法静态判定）"
                break
            inner = residual[bi + 1:end]
            for name in top_level_keys(inner):
                if name is None:
                    undecided[eid] = f"花括号式含不可静态判定项（{{{inner[:40]}}}）"
                    continue
                fields.add(name)
            residual = residual[:bi] + " " + residual[end + 1:]
        # 反引号式：`name?` / `name[]` / `name:ENUM`
        for m in re.finditer(r"`([^`]+)`", residual):
            tok = m.group(1).strip()
            name = tok.split(":")[0].strip().rstrip("?").rstrip("[]").strip()
            if FIELD_RE.match(name):
                fields.add(name)
            residual = residual.replace(m.group(0), " ")
        residual = re.sub(r"\bbody\b|body：|：|\+|\s|（[^）]*）|\(|\)|、|,", "", residual)
        if residual:
            undecided[eid] = f"描述式残留 {residual[:30]!r}"
            continue
        if eid in undecided:
            continue
        bodies[eid] = frozenset(fields)
    return bodies, undecided, read


# ------------------------------------------------------------------ D：endpoints.json + 请求 schema

def parse_endpoints(root: Path) -> tuple[list[dict], list[Path]]:
    p = root / ENDPOINTS
    if not p.exists():
        return [], []
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("endpoints", []), [p]


def parse_request_schemas(root: Path) -> tuple[dict, list[Path]]:
    """→ ({模型名: {属性名: 类型归一}}, 读过的文件)。"""
    base = root / REQ_SCHEMA_DIR
    out: dict[str, dict] = {}
    read: list[Path] = []
    if not base.exists():
        return out, read
    for p in sorted(base.glob("*.schema.json")):
        read.append(p)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        model = p.name[: -len(".schema.json")]
        props = d.get("properties") or {}
        out[model] = {k: (v.get("type") if isinstance(v, dict) else None) for k, v in props.items()}
    return out, read


# ------------------------------------------------------------------ O：openapi.yaml

def parse_openapi_bodies(root: Path) -> tuple[dict, dict, list[str], list[Path]]:
    """→ ({端点ID: 请求体组件名 or None}, {组件名: ('ref', 目标) | ('inline', {属性})}, 悬空引用, 读过的文件)。

    openapi 的 `x-aap-id` 逐 operation 标注端点 ID，直接用它对齐清单（避免路径归一误差）。
    """
    p = root / OPENAPI
    op_bodies: dict[str, str | None] = {}
    comps: dict[str, tuple] = {}
    dangling: list[str] = []
    read: list[Path] = []
    if not p.exists():
        return op_bodies, comps, dangling, read
    read.append(p)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()

    cur_id = None
    for i, ln in enumerate(lines):
        m = re.match(r"^      x-aap-id: (\S+)\s*$", ln)
        if m:
            cur_id = m.group(1)
            op_bodies.setdefault(cur_id, None)
            continue
        if cur_id and re.match(r"^      requestBody:\s*$", ln):
            # 向下找 `$ref: "#/components/schemas/XXX"`
            for j in range(i + 1, min(i + 12, len(lines))):
                mr = re.search(r"\$ref:\s*\"?#/components/schemas/(\w+)\"?", lines[j])
                if mr:
                    op_bodies[cur_id] = mr.group(1)
                    break
                if re.match(r"^      [a-z]", lines[j]):
                    break
            else:
                op_bodies[cur_id] = op_bodies.get(cur_id)

    # components.schemas
    in_schemas = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.match(r"^  schemas:\s*$", ln):
            in_schemas = True
            i += 1
            continue
        if in_schemas and re.match(r"^  \S", ln) and not re.match(r"^  schemas:", ln):
            in_schemas = False
        if in_schemas:
            m = re.match(r"^    (\w+):\s*$", ln)
            if m:
                name = m.group(1)
                kind, body, j = "empty", {}, i + 1
                while j < len(lines) and (lines[j].startswith("      ") or not lines[j].strip()):
                    s = lines[j]
                    mr = re.match(r"^      \$ref: (\S+)\s*$", s)
                    if mr:
                        kind = "ref"
                        target = mr.group(1).strip('"')
                        body = target
                        tgt = (root / "docs/backend" / target.replace("./", "")).resolve()
                        if not tgt.exists():
                            dangling.append(f"{name} → {target}")
                    elif re.match(r"^      properties:\s*$", s):
                        if kind == "empty":
                            kind = "inline"
                        k = j + 1
                        while k < len(lines) and lines[k].startswith("        "):
                            mp = re.match(r"^        (\w+):\s*$", lines[k])
                            if mp:
                                body[mp.group(1)] = None
                            k += 1
                    j += 1
                comps[name] = (kind, body)
                i = j
                continue
        i += 1
    return op_bodies, comps, dangling, read


# ------------------------------------------------------------------ I：控制器 @RequestBody DTO

def parse_controllers(root: Path) -> tuple[dict, dict, list[Path]]:
    """→ ({(方法, 归一路径): (DTO 名 or None, 未能静态判定原因)}, DTO 解析表, 读过的文件)。

    DTO 解析表 = {"by_file": {文件名: {record 名: [分量名]}}, "global": {record 名: [分量名] | None}}；
    `global[name] is None` 表示**同名 record 出现在多个文件**（本项目实测 `SaveRequest` / `RefreshRequest`
    各 2 处）→ 必须**同文件优先**，否则会把 report-template 的分量算到 detection-config 端点上
    （真实返工：5 条假漂移；坑 74 同族「按类名硬编码/全局首匹配」）。
    """
    base = root / JAVA_DIR
    methods: dict[tuple[str, str], tuple] = {}
    read: list[Path] = []
    if not base.exists():
        return methods, {"by_file": {}, "global": {}}, read
    imports: dict[str, dict[str, list[str]]] = {}
    for f in sorted(base.rglob("*Controller.java")):
        read.append(f)
        t = f.read_text(encoding="utf-8", errors="replace")
        imap: dict[str, list[str]] = {}
        for im in re.finditer(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", t, re.M):
            segs = im.group(1).split(".")
            if len(segs) >= 2:
                # 嵌套 record：`…DetectionConfigViews.SaveRequest` → 文件 DetectionConfigViews.java；
                # 顶层类：`…quote.CreateRequest` → 文件 CreateRequest.java（两个候选都试）
                imap[segs[-1]] = [segs[-2] + ".java", segs[-1] + ".java"]
        imports[f.name] = imap
    for f in sorted(base.rglob("*Controller.java")):
        read.append(f)
        t = f.read_text(encoding="utf-8", errors="replace")
        bm = re.search(r'@RequestMapping\("([^"]+)"\)', t)
        bpath = bm.group(1) if bm else ""
        for m in re.finditer(r"@(Get|Post|Put|Patch|Delete)Mapping", t):
            http = m.group(1).upper()
            k = m.end()
            path = ""
            if k < len(t) and t[k] == "(":
                e = match_paren(t, k)
                if e < 0:
                    continue
                inner = t[k + 1:e]
                pm = re.search(r'"([^"]*)"', inner)
                path = pm.group(1) if pm else ""
                k = e + 1
            bs = body_start(t, k)
            if bs < 0:
                continue
            sig = t[k:bs]
            rb = re.search(r"@RequestBody", sig)
            key = norm_key(http, bpath + path)
            if not rb:
                methods[key] = (None, "实现无 @RequestBody", f.name)
                continue
            rest = sig[rb.end():]
            if rest.startswith("("):
                e = match_paren(rest, 0)
                rest = rest[e + 1:] if e >= 0 else rest
            # 方法签名里 `@RequestBody` 之后可能紧跟**修饰符**再跟类型
            # （真实返工：`@RequestBody\n public Object b(SynRequest request)` 会把 `public`
            #  当成类型名 → 报「未找到 record public」；负向自测的 ok 夹具抓出来的）
            rest = re.sub(r"^\s*(?:(?:public|private|protected|static|final)\s+)+", "", rest)
            tm = re.match(r"\s*(?:@\w+(?:\([^)]*\))?\s+)*([A-Za-z_][\w.]*(?:\s*<[^>]*>)?)\s+(\w+)", rest)
            if not tm:
                methods[key] = (None, "未能静态判定（@RequestBody 后未解析到类型）", f.name)
                continue
            typ = re.sub(r"\s+", "", tm.group(1))
            methods[key] = (typ, None, f.name)
    # record 定义：同文件优先 + 同名歧义标记
    by_file: dict[str, dict[str, list[str]]] = {}
    seen: dict[str, int] = {}
    for f in sorted(base.rglob("*.java")):
        if f not in read:
            read.append(f)
        t = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\brecord\s+([A-Z]\w*)\s*(<[^>(]*>)?\s*\(", t):
            name = m.group(1)
            e = match_paren(t, m.end() - 1)
            if e < 0:
                continue
            inner = t[m.end():e]
            parts, d, cur = [], 0, ""
            for ch in inner:
                if ch in "<([":
                    d += 1
                elif ch in ">)]":
                    d -= 1
                if ch == "," and d == 0:
                    parts.append(cur)
                    cur = ""
                else:
                    cur += ch
            parts.append(cur)
            names = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                jp = re.search(r'@JsonProperty\("([^"]+)"\)', part)
                nm = re.search(r"(\w+)\s*$", part)
                if jp:
                    names.append(jp.group(1))
                elif nm:
                    names.append(nm.group(1))
            by_file.setdefault(f.name, {}).setdefault(name, names)
            seen[name] = seen.get(name, 0) + 1
    global_map: dict[str, list[str] | None] = {}
    for fname, recs in by_file.items():
        for name, comps in recs.items():
            if seen[name] > 1:
                global_map[name] = None
            else:
                global_map.setdefault(name, comps)
    return methods, {"by_file": by_file, "global": global_map, "imports": imports}, read


# ------------------------------------------------------------------ C：客户端 data 键（弱证据）

def strip_comments(txt: str) -> str:
    """剥注释但保留字符串/模板字面量（skill 坑 58③）。"""
    out = []
    i, n = 0, len(txt)
    while i < n:
        c = txt[i]
        if c in "\"'`":
            q = c
            out.append(c)
            i += 1
            while i < n:
                if txt[i] == "\\":
                    out.append(txt[i:i + 2])
                    i += 2
                    continue
                out.append(txt[i])
                if txt[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if txt.startswith("//", i):
            j = txt.find("\n", i)
            i = n if j < 0 else j
            continue
        if txt.startswith("/*", i):
            j = txt.find("*/", i)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def object_keys(inner: str) -> tuple[list[str], bool]:
    """对象字面量取键：只在**键位置**认（对象起点 / 顶层逗号之后），坑 64。

    → (键列表, 是否含不可静态判定项)
    """
    keys: list[str] = []
    d, cur, parts, expect_key = 0, "", [], True
    for ch in inner:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == "," and d == 0:
            parts.append((cur, expect_key))
            cur, expect_key = "", True
            continue
        cur += ch
    parts.append((cur, expect_key))
    undecided = False
    for text, is_key in parts:
        s = text.strip()
        if not s:
            continue
        if not is_key:
            continue
        if s.startswith("..."):
            undecided = True
            continue
        if s.startswith("["):
            undecided = True
            continue
        m = re.match(r"^([A-Za-z_]\w*)\s*(?::|$)", s)
        if m:
            keys.append(m.group(1))
        else:
            undecided = True
    return keys, undecided


def parse_client_bodies(root: Path) -> tuple[dict, dict, int, list[Path]]:
    """→ ({归一路径: 键集合}, {归一路径: 原因}, 解析到的 data 字面量处数, 读过的文件)。"""
    base = root / CLIENT_DIR
    out: dict[str, set] = {}
    undecided: dict[str, str] = {}
    occ = 0
    read: list[Path] = []
    if not base.exists():
        return out, undecided, occ, read
    for p in sorted(list(base.rglob("*.ts")) + list(base.rglob("*.tsx"))):
        read.append(p)
        txt = strip_comments(p.read_text(encoding="utf-8", errors="replace"))
        for m in re.finditer(r"\bhttp\s*(?:<[^>]*>)?\s*\(", txt):
            e = match_paren(txt, m.end() - 1)
            if e < 0:
                continue
            call = txt[m.end():e]
            # 路径：第一个参数里的字符串/模板字面量
            pm = re.match(r"\s*(?:'([^']*)'|\"([^\"]*)\"|`([^`]*)`)", call)
            raw_path = pm.group(1) or pm.group(2) or pm.group(3) if pm else None
            if raw_path is None:
                continue
            norm = re.sub(r"\$\{[^}]*\}", "{}", raw_path)
            norm = re.sub(r"\{[^}]*\}", "{}", norm)
            dm = re.search(r"\bdata\s*:\s*\{", call)
            if not dm:
                continue
            mm = re.search(r"method\s*:\s*['\"](\w+)['\"]", call)
            method = (mm.group(1) if mm else "GET").upper()
            if method in ("GET", "HEAD"):
                # GET 的 `data` 是**查询参数**，不是请求体（坑 62：POST/PUT 的 data 才是请求体）
                continue
            occ += 1
            bs = call.index("{", dm.end() - 1)
            # 匹配花括号
            d, j = 0, bs
            while j < len(call):
                if call[j] == "{":
                    d += 1
                elif call[j] == "}":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            keys, undec = object_keys(call[bs + 1:j])
            norm = norm_key(method, norm)[1]
            if undec:
                undecided[norm] = "data 字面量含展开/计算键"
            elif keys:
                out.setdefault(norm, set()).update(keys)
    return out, undecided, occ, read


# ------------------------------------------------------------------ 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    m_bodies, m_undec, m_read = parse_md_bodies(root)
    eps, e_read = parse_endpoints(root)
    d_models, d_read = parse_request_schemas(root)
    o_bodies, o_comps, o_dangling, o_read = parse_openapi_bodies(root)
    i_methods, i_dtos, i_read = parse_controllers(root)
    c_bodies, c_undec, c_occ, c_read = parse_client_bodies(root)

    watched = m_read + e_read + d_read + o_read + i_read + c_read
    before = fingerprint(watched)

    r = Result()
    r.info("== 请求体字段名集合 / 有无请求体 契约审计（第十四类不变量；只读） ==")
    r.info(f"仓库根：{root}")

    # ---------------- A0 正向对照（坑 46 / 75） ----------------
    r.info("--- A0 正向对照：每个源都真的解析到了条目 ---")
    n_m = sum(1 for v in m_bodies.values() if v)
    r.check("A0a M 解析到 md「请求」列的请求体字段 > 0", n_m > 0,
            f"有请求体的端点 {n_m} 个 / 解析到端点 {len(m_bodies)} 个")
    n_d = sum(1 for e in eps if e.get("request_model"))
    r.check("A0b D 解析到 endpoints.json 的 request_model > 0", n_d > 0,
            f"带 request_model 的端点 {n_d} 个 / 请求模型文件 {len(d_models)} 个")
    n_o = sum(1 for v in o_bodies.values() if v)
    r.check("A0c O 解析到 openapi 的 requestBody > 0", n_o > 0,
            f"带 requestBody 的 operation {n_o} 个 / 解析到 x-aap-id {len(o_bodies)} 个")
    n_i = sum(1 for v in i_methods.values() if v[0])
    r.check("A0d I 解析到控制器 @RequestBody > 0", n_i > 0,
            f"带 @RequestBody 的控制器方法 {n_i} 个 / 解析到方法 {len(i_methods)} 个 / "
            f"record 定义 {len(i_dtos['global'])} 个（同名歧义 {sum(1 for v in i_dtos['global'].values() if v is None)} 个）")
    r.check("A0e C 解析到客户端 data 对象字面量 > 0", c_occ > 0, f"data 字面量 {c_occ} 处")

    # ---------------- A1 D：模型文件与孤儿 ----------------
    r.info("--- A1 D：request_model ↔ 请求模型 schema 文件 ---")
    miss_file = sorted({e["request_model"] for e in eps if e.get("request_model")} - set(d_models))
    r.check("A1a 每个 request_model 都有对应的请求模型 schema 文件", not miss_file,
            f"缺 {len(miss_file)} 个：{miss_file[:6]}")
    used = {e["request_model"] for e in eps if e.get("request_model")}
    orphan = sorted(set(d_models) - used)
    r.check("A1b 孤儿请求模型 schema 文件 = 0（仓库里有、清单无端点引用）", not orphan,
            f"孤儿 {len(orphan)} 个：{orphan[:6]}")

    # ---------------- A2 O：requestBody 存在性 ----------------
    r.info("--- A2 O：openapi requestBody 存在性 ⇔ endpoints.json request_model ---")
    d_has = {e["id"] for e in eps if e.get("request_model")}
    o_has = {k for k, v in o_bodies.items() if v}
    only_d = sorted(d_has - o_has)
    only_o = sorted(o_has - d_has)
    r.check("A2a 清单有请求体而 openapi 无 requestBody = 0", not only_d,
            f"缺 {len(only_d)} 条：{only_d[:8]}")
    r.check("A2b openapi 有 requestBody 而清单无请求体 = 0", not only_o,
            f"多 {len(only_o)} 条：{only_o[:8]}")

    # ---------------- A2c/A2d md ↔ 清单：有无请求体（坑 73 族的「有无」方向） ----------------
    md_no_body_but_has = sorted(e["id"] for e in eps
                                if e.get("request_model") and e["id"] in m_bodies and not m_bodies[e["id"]])
    md_body_but_none = sorted(e["id"] for e in eps
                              if not e.get("request_model") and m_bodies.get(e["id"]))
    r.check("A2c md 说「无请求体」而清单声明 request_model = 0", not md_no_body_but_has,
            f"不一致 {len(md_no_body_but_has)} 条：{md_no_body_but_has[:8]}")
    r.check("A2d md 写了请求体字段而清单无 request_model = 0", not md_body_but_none,
            f"不一致 {len(md_body_but_none)} 条：{md_body_but_none[:8]}")

    # ---------------- A3 O：组件引用与属性 ----------------
    r.info("--- A3 O：请求体组件 $ref 可解析、属性集合 = 请求模型 schema ---")
    r.check("A3a 请求体组件 $ref 悬空引用 = 0", not o_dangling,
            f"悬空 {len(o_dangling)} 条：{o_dangling[:5]}")
    o_attr_mismatch: dict[str, str] = {}
    for eid, comp in sorted(o_bodies.items()):
        if not comp:
            continue
        info = o_comps.get(comp)
        if info is None:
            o_attr_mismatch[eid] = f"{comp} 组件不存在"
            continue
        kind, body = info
        model = next((e.get("request_model") for e in eps if e["id"] == eid), None)
        if kind == "ref":
            target = str(body)
            tgt = (root / "docs/backend" / target.replace("./", "")).resolve()
            if tgt.exists():
                try:
                    props = set((json.loads(tgt.read_text(encoding="utf-8")).get("properties") or {}).keys())
                except Exception:
                    props = set()
                if model and props != set(d_models.get(model, {}).keys()):
                    o_attr_mismatch[eid] = f"openapi 文件属性 ≠ schema 属性（{comp}）"
        elif kind == "inline" and model:
            if set(body.keys()) != set(d_models.get(model, {}).keys()):
                o_attr_mismatch[eid] = f"内联组件属性 ≠ schema 属性（{comp}）"
    r.check("A3b 每个请求体组件解析到的属性集合 = 该端点的请求模型 schema", not o_attr_mismatch,
            f"不一致 {len(o_attr_mismatch)} 条：{ {k: o_attr_mismatch[k] for k in sorted(o_attr_mismatch)[:5]} }")

    # ---------------- A4 M ⊆ D ----------------
    r.info("--- A4 M⊆D：md 声明的请求字段必须都在请求模型 schema 里（文档字段必须可校验） ---")
    m_missing: dict[str, str] = {}
    for eid, fields in sorted(m_bodies.items()):
        if not fields:
            continue
        e = next((x for x in eps if x["id"] == eid), None)
        if not e or not e.get("request_model"):
            m_missing[eid] = "清单端点无 request_model（md 却写了请求体字段）"
            continue
        props = set(d_models.get(e["request_model"], {}).keys())
        extra = sorted(set(fields) - props)
        if extra:
            m_missing[eid] = f"{e['request_model']} 缺 {extra}"
    r.check("A4 md「请求」列字段都在请求模型 schema 的 properties 里", not m_missing,
            f"缺 {len(m_missing)} 条：{ {k: m_missing[k] for k in sorted(m_missing)[:6]} }")

    # ---------------- A5 D ↔ I ----------------
    r.info("--- A5 D↔I：请求模型 schema 属性 ↔ 控制器 @RequestBody DTO 分量（双向） ---")
    i_by_key = {k: v for k, v in i_methods.items()}
    dtos_by_file = i_dtos["by_file"]
    dtos_global = i_dtos["global"]
    compared, d_i_drift = 0, {}
    for e in eps:
        if not e.get("request_model"):
            continue
        key = norm_key(e["method"], e["path"])
        hit = i_by_key.get(key)
        if hit is None:
            d_i_drift[e["id"]] = "未定位到控制器方法（路由审计已覆盖）"
            continue
        typ, why, srcfile = hit
        if not typ:
            d_i_drift[e["id"]] = why or "未能静态判定"
            continue
        simple = typ.split("<")[0].split(".")[-1]
        if simple in GENERIC_BODY_TYPES or typ in GENERIC_BODY_TYPES:
            d_i_drift[e["id"]] = f"泛型请求体（{typ}），无法静态比对"
            continue
        comps = (dtos_by_file.get(srcfile) or {}).get(simple)   # ① 同文件优先（同名歧义）
        if comps is None:                                        # ② import 解析（嵌套 record 所在文件）
            for cand in (i_dtos["imports"].get(srcfile) or {}).get(simple, []):
                comps = (dtos_by_file.get(cand) or {}).get(simple)
                if comps is not None:
                    break
        if comps is None:                                        # ③ 全仓库唯一同名
            comps = dtos_global.get(simple)
        if comps is None:
            d_i_drift[e["id"]] = f"未找到 record {simple}（同名歧义或不存在）"
            continue
        props = set(d_models.get(e["request_model"], {}).keys())
        miss = sorted(props - set(comps))
        extra = sorted(set(comps) - props)
        if miss or extra:
            d_i_drift[e["id"]] = (f"{e['request_model']} schema-not-in-dto={miss} "
                                  f"dto-not-in-schema={extra}")
        else:
            compared += 1
    r.check("A5b 正向对照：真的完成了 D↔I 逐端点比对的端点 > 0", compared > 0, f"完成比对 {compared} 个端点")
    r.check("A5 每个端点的请求模型 schema 属性 = 控制器 DTO 分量（双向）", not d_i_drift,
            f"不一致 {len(d_i_drift)} 条：{ {k: d_i_drift[k] for k in sorted(d_i_drift)[:8]} }")

    # ---------------- A6 C ⊆ D ----------------
    r.info("--- A6 C⊆D：客户端发送的请求体键必须都在 schema 里（客户端为准，坑 1） ---")
    c_out: dict[str, str] = {}
    c_matched = 0
    for norm_path, keys in sorted(c_bodies.items()):
        e = next((x for x in eps if norm_key(x["method"], x["path"])[1] == norm_path), None)
        if not e:
            continue
        c_matched += 1
        if not e.get("request_model"):
            c_out[e["id"]] = f"客户端发 {sorted(keys)} 而清单无请求体"
            continue
        props = set(d_models.get(e["request_model"], {}).keys())
        extra = sorted(set(keys) - props)
        if extra:
            c_out[e["id"]] = f"{e['request_model']} 缺 {extra}"
    r.check("A6 客户端 data 键都在请求模型 schema 里", not c_out,
            f"越界 {len(c_out)} 条：{ {k: c_out[k] for k in sorted(c_out)[:6]} }（匹配到端点 {c_matched} 个）")

    # ---------------- A7 信息项 ----------------
    r.info("--- A7 信息项（不判 FAIL；未能静态判定的写法一律不当漂移，坑 65） ---")
    r.info(f"      · M 未能静态判定 {len(m_undec)} 条：{ {k: m_undec[k] for k in sorted(m_undec)[:8]} }")
    r.info(f"      · D↔I 未完成比对 {len(d_i_drift)} 条（原因见 A5 明细）")
    r.info(f"      · C 未能静态判定 {len(c_undec)} 条（data 为变量或含展开键）："
           f"{ {k: c_undec[k] for k in sorted(c_undec)[:6]} }")
    if args.all:
        for eid in sorted(m_undec):
            r.info(f"      · M {eid}: {m_undec[eid]}")

    after = fingerprint(watched)
    changed = [k for k in before if before[k] != after.get(k)]
    r.check("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed,
            f"被改写={len(changed)} 个：{changed[:3]}")

    print("\n".join(r.lines))
    print(f"\n== 断言：PASS {r.npass} / FAIL {r.nfail} ==")
    if r.nfail:
        print("结论：存在请求体字段名/有无请求体 契约漂移（两套门禁都看不见：契约测试只读响应 JSON Schema，"
              "覆盖门禁只比方法+路径；openapi 与客户端 TS 不被任何测试读取/执行）。")
        return 1
    print("结论：请求体字段名集合与有无请求体在 M/D/O/I/C 五处一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
