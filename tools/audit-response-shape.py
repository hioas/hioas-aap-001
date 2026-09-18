#!/usr/bin/env python3
"""响应形状（分页包装）契约一致性审计（R37，只读）。

不变量：**每个端点的成功响应形状（`data` 是「分页集合 `{items,page,pageSize,total}`」还是「单对象」）**
必须在多处真源逐端点一致 —— 与 `audit-contract-keys.py`（分页集合**键名**）、`audit-routes.py`（方法/路径/
路径变量名）、`audit-query-params.py`（查询参数名）、`audit-error-codes.py`（错误码）同族，
换第七条契约不变量：**分页包装本身**（不是键名，是「该不该包」）。

  简称  来源                                                     承载方式
  ----  -------------------------------------------------------  --------------------------------------------
  M     docs/backend/endpoints.json                              逐端点 `response_model` + `query_params`
  D     docs/backend/02-API接口模型清单.md                       逐行「响应」列 / 「请求·响应」列（散文，弱证据）
  O     docs/backend/openapi.yaml                                每 operation `200` 的 `data` 形状 + 组件 → 文件
  S     docs/backend/json-schema/models/*.schema.json            元素模型自身的形状（不得又是分页包装）
  I     aap-server/src/main/java/**/*Controller.java              控制器返回类型 `ApiEnvelope<PageResult<…>>`

为什么需要它（skill 坑 43 / 44 / 72 族）：
  * 契约测试只把真实响应与 **JSON Schema** 比对 —— 而 schema 描述的是**元素模型**（单对象），
    分页包装由 `common/page.schema.json` 另行描述，**schema 里没有「哪个端点该分页」的信息** →
    openapi 把单对象端点声明成分页集合时，204 例全绿也完全看不见；
  * 覆盖门禁 `EndpointCoverageTest` 只比「方法 + 路径」注册表；
  * `openapi.yaml` 不被任何测试读取/执行 → 客户端 codegen 或第三方按 openapi 生成的分页读取代码
    会对着**单对象**响应找 `data.items` → 列表页静默空白（与坑 1 同族，后果一致）。

方向性（避免假发现，skill 坑 29 / 46）：
  * 硬断言只用在**机器可精确判定**的两侧：O（openapi 的 `data` 形状）与 I（控制器返回类型）；
  * md 是散文（同一列里既有 `{items:[QuoteItem]}` 也有 `分页 ReportTemplate`，还有 `{job_id,total,items:[…]}`），
    只作**弱证据信息项**（A7），不判 FAIL；
  * 第三证人（不依赖任何解析）：**分页语义自洽性** —— 清单 §0 约定分页请求带 `page`/`pageSize`，
    若 openapi 声明某端点分页响应、而该端点**没有**分页查询参数，则自相矛盾（A4）。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动（Z1）。

用法：
  python tools/audit-response-shape.py [--root <dir>] [--all]
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

REL_STATIC = {
    "M": "docs/backend/endpoints.json",
    "O": "docs/backend/openapi.yaml",
    "D": "docs/backend/02-API接口模型清单.md",
}
SCHEMA_DIR = "docs/backend/json-schema"
CONTROLLER_DIR = "aap-server/src/main/java/com/hioas/aap"
PREFIX = "/api/v1"

VAR_RE = re.compile(r"\{[^}]*\}")
MAPPING_RE = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")
REQ_MAPPING_RE = re.compile(r"@RequestMapping\s*\(([^)]*)\)")
CLASS_DECL_RE = re.compile(r"^[A-Za-z@\s]*\bclass\s+\w+", re.MULTILINE)
MD_ID_RE = re.compile(r"^[A-Z]+-[A-Z0-9]+$")
METHOD_LINE_RE = re.compile(r"^    (get|post|put|delete|patch):$")
PATH_LINE_RE = re.compile(r"^  (/[^ ]*):$")
OPID_LINE_RE = re.compile(r"^      operationId: (\S+)$")
QUERY_NAME_RE = re.compile(r"^        - name: ([A-Za-z0-9_]+)$", re.MULTILINE)
QUERY_IN_RE = re.compile(r"^        - name: ([A-Za-z0-9_]+)\n          in: query$", re.MULTILINE)
DATA_SINGLE_RE = re.compile(r"^ +data:\n +\$ref: \"?#/components/schemas/(\w+)\"?$", re.MULTILINE)
DATA_KIND_RE = re.compile(r"^ +data:\n +(allOf|oneOf):$", re.MULTILINE)
ITEMS_REF_RE = re.compile(r"^ +items:\n +\$ref: \"?#/components/schemas/(\w+)\"?$", re.MULTILINE)
COMPONENT_RE = re.compile(r"^    (\w+):\n      \$ref: (\S+)$", re.MULTILINE)
INLINE_COMPONENT_RE = re.compile(r"^    (\w+):\n      type: string$", re.MULTILINE)


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


def comp_name(model: str) -> str:
    """与生成器 `_comp()` 完全同构：`usage-summary` → `UsageSummary`。"""
    return "".join(part.capitalize() for part in model.split("-"))


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
        out[e["id"]] = {
            "method": e["method"].upper(),
            "path": e["path"].strip(),
            "resp": e.get("response_model"),
            "params": {str(x).strip() for x in (e.get("query_params") or []) if str(x).strip()},
        }
    return total, out


# ---------------------------------------------------------------- D：md 清单（散文，弱证据）

def split_row(ln: str) -> list[str]:
    """按**未转义**竖线切分并还原字面竖线（skill 坑 48）。"""
    cells = re.split(r"(?<!\\)\|", ln)
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip().replace("\\|", "|") for c in cells]


def md_shape(cell: str) -> str:
    """散文列 → list / none / html / single / unknown。

    真实写法（先 grep 出全部写法再写解析器，skill 坑 65）：
      `{items:[CredentialRow],page,pageSize,total}`、`{job_id,total,items:[DetectionResult]}`、
      `分页 ReportTemplate`、`—`、`null`、`text/html`、`LoginResult{token,…}`。
    """
    c = cell.strip()
    if not c or c in ("—", "-", "–"):
        return "unknown"
    if c in ("null", "`null`"):
        return "none"
    if "text/html" in c:
        return "html"
    if re.search(r"\bitems\s*:", c) or "分页" in c:
        return "list"
    return "single"


def parse_md_shapes(p: Path) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """→ ({ID: 形状}, {ID: 原始单元格}, problems)。表头按**列数**就近匹配（10 列与 7 列并存，skill 坑 49）。"""
    out: dict[str, str] = {}
    raw: dict[str, str] = {}
    problems: list[str] = []
    lines = p.read_text(encoding="utf-8").splitlines()
    headers: dict[int, list[str]] = {}
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = split_row(ln)
        if cells and cells[0] == "ID":
            headers[len(cells)] = cells
            continue
        if not cells or not MD_ID_RE.match(cells[0]):
            continue
        hdr = headers.get(len(cells))
        if hdr is None:
            problems.append(f"{cells[0]}: 找不到同列数表头（{len(cells)} 列）")
            out[cells[0]] = "unknown"
            continue
        idx = None
        for cand in ("响应", "请求/响应"):
            if cand in hdr:
                idx = hdr.index(cand)
                break
        if idx is None or idx >= len(cells):
            problems.append(f"{cells[0]}: 表头里没有响应列")
            out[cells[0]] = "unknown"
            continue
        raw[cells[0]] = cells[idx]
        out[cells[0]] = md_shape(cells[idx])
    return out, raw, problems


# ---------------------------------------------------------------- O：openapi

def parse_openapi(text: str) -> tuple[dict[str, dict], list[str]]:
    """→ ({operationId: {shape, comps, query, method, path}}, problems)。

    shape ∈ none（无 data）| single（data.$ref）| page（data.allOf[PageMeta,{items:[]}]）|
            oneof（data.oneOf）| unknown（解析不出来，必须为 0，否则先怀疑解析器）
    """
    lines = text.splitlines()
    ops: dict[str, dict] = {}
    problems: list[str] = []
    cur_path = cur_method = cur_id = None
    buf: list[str] = []

    def flush() -> None:
        if cur_id is None:
            return
        body = "\n".join(buf)
        rec = {"method": (cur_method or "").upper(), "path": cur_path or "", "query": set()}
        rec["query"] = set(QUERY_IN_RE.findall(body))
        # 只取 200 段（4XX 段不参与形状判定）
        seg = body
        i200 = seg.find("        200:")
        if i200 >= 0:
            seg = seg[i200:]
            j4 = seg.find("        4XX:")
            if j4 > 0:
                seg = seg[:j4]
        m_single = DATA_SINGLE_RE.search(seg)
        m_kind = DATA_KIND_RE.search(seg)
        if m_single:
            rec.update(shape="single", comps=[m_single.group(1)])
        elif m_kind:
            kind = m_kind.group(1)
            comps = ITEMS_REF_RE.findall(seg[m_kind.start():])
            if kind == "allOf":
                if "PageMeta" in seg[m_kind.start():] and comps:
                    rec.update(shape="page", comps=[comps[-1]])
                else:
                    rec.update(shape="unknown", comps=comps)
            else:
                rec.update(shape="oneof", comps=comps)
        elif "data:" not in seg:
            rec.update(shape="none", comps=[])
        else:
            rec.update(shape="unknown", comps=[])
        ops[cur_id] = rec

    for ln in lines:
        m = OPID_LINE_RE.match(ln)
        if m:
            flush()
            cur_id, buf = m.group(1), []
            continue
        mp = PATH_LINE_RE.match(ln)
        if mp:
            flush()
            cur_id, buf, cur_path, cur_method = None, [], mp.group(1), None
            continue
        mm = METHOD_LINE_RE.match(ln)
        if mm:
            cur_method = mm.group(1)
        if cur_id is not None:
            buf.append(ln)
    flush()
    for oid, rec in ops.items():
        if rec["shape"] == "unknown":
            problems.append(f"{oid}: 200 的 data 形状未能解析（先怀疑解析器，skill 坑 72）")
    return ops, problems


def parse_components(text: str) -> tuple[dict[str, str], set[str]]:
    """→ ({组件名: $ref 文件}, 内联组件名集合)。"""
    refs = {m.group(1): m.group(2).strip('"') for m in COMPONENT_RE.finditer(text)}
    inline = {m.group(1) for m in INLINE_COMPONENT_RE.finditer(text)}
    return refs, inline


# ---------------------------------------------------------------- S：JSON Schema

def schema_shape(p: Path) -> str:
    """模型自身形状：`paged`（自带 page/pageSize/total）| `object` | `missing`。"""
    if not p.exists():
        return "missing"
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return "unreadable"
    props = set((obj.get("properties") or {}).keys())
    if {"page", "pageSize", "total"} <= props:
        return "paged"
    return "object"


# ---------------------------------------------------------------- I：控制器

def skip_string(code: str, i: int) -> int:
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
    depth, i, n = 0, open_idx, len(code)
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
    """方法体起点 = 括号深度 0 且不在字符串内的第一个 `{`（skill 坑 55 / 63）。"""
    depth, i, n = 0, start, len(code)
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


def class_body_start(text: str) -> int:
    m = CLASS_DECL_RE.search(text)
    if not m:
        return -1
    brace = text.find("{", m.end())
    return brace if brace >= 0 else -1


RECORD_RE = re.compile(r"\brecord\s+([A-Z][A-Za-z0-9_]*)\s*(?:<[^>(]*>)?\s*\(")
ANN_RE = re.compile(r"@\w+\s*(\([^)]*\))?")
STR_LIT_RE = re.compile(r'"[^"]*"')


def top_level_split(s: str) -> list[str]:
    """按顶层逗号切分（`<>`/`()`/`[]` 内的逗号不算）。"""
    out, depth, cur, i, n = [], 0, [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "'\"`":
            j = skip_string(s, i)
            cur.append(s[i:j])
            i = j
            continue
        if c in "<([":
            depth += 1
        elif c in ">)]":
            depth -= 1
        if c == "," and depth == 0:
            out.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    if cur:
        out.append("".join(cur))
    return [x for x in (t.strip() for t in out) if x]


def body_brace_end(code: str, open_idx: int) -> int:
    """从 `{` 起做引号感知的花括号配对扫描，返回配对 `}` 之后的下标。"""
    depth, i, n = 0, open_idx, len(code)
    while i < n:
        c = code[i]
        if c in "'\"`":
            i = skip_string(code, i)
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


CLASS_DECL2_RE = re.compile(r"\bclass\s+([A-Z][A-Za-z0-9_]*)")
FIELD_RE = re.compile(
    r"\b(?:private|protected|public)\s+(?:static\s+|final\s+|transient\s+|volatile\s+)*"
    r"[\w.<>,\[\]\s?]+?\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*[;=]")


def class_members(text: str) -> list[tuple[str, set[str]]]:
    out = []
    for m in CLASS_DECL2_RE.finditer(text):
        b = text.find("{", m.end())
        if b < 0:
            continue
        body = text[b:body_brace_end(text, b)]
        out.append((m.group(1), set(FIELD_RE.findall(body))))
    return out


def parse_records(java_dir: Path) -> dict[str, dict[str, set[str]]]:
    """→ {简单类名: {所在文件: 分量名集合}}（供「返回的 DTO 是否分页形状」判定）。

    分页形状的判据与 `PageResult` 同构：分量含 `items` + `page` + `pageSize` + `total`
    （本项目 `AuditLogViews.Page` / `PaymentViews.PaymentPage` / `NotificationViews.ListResult`
    都自带这四个分量，只按「类名 == PageResult」判会误报，skill 坑 46）。
    record 与 class 两种写法都收（`LoginResult`/`MeResult`/`ProviderProfileResponse` 是 class）。
    """
    out: dict[str, dict[str, set[str]]] = {}
    for f in sorted(java_dir.rglob("*.java")):
        text = f.read_text(encoding="utf-8")
        for m in RECORD_RE.finditer(text):
            close = match_paren(text, m.end() - 1)
            if close < 0:
                continue
            names: set[str] = set()
            for comp in top_level_split(text[m.end():close]):
                c = STR_LIT_RE.sub(" ", ANN_RE.sub(" ", comp))
                toks = re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", c)
                if toks:
                    names.add(toks[-1])
            out.setdefault(m.group(1), {})[f.name] = names
        for name, members in class_members(text):
            out.setdefault(name, {})[f.name] = members
    return out


PAGE_COMPONENTS = {"items", "page", "pageSize", "total"}


def dto_page_shape(ret: str | None, records: dict[str, dict[str, set[str]]]) -> bool | None:
    """返回类型 → True（分页形状）/ False（非分页）/ None（未能静态判定）。"""
    if not ret:
        return None
    m = re.search(r"ApiEnvelope<(.+)>\s*$", ret.strip())
    inner = m.group(1).strip() if m else ret.strip()
    inner = re.sub(r"<.*>\s*$", "", inner).strip()
    parts = [p for p in inner.split(".") if p]
    name = parts[-1].strip() if parts else ""
    if name in ("ResponseEntity", "String", "void", "Void", "Map", "Object", "List",
                "Integer", "Long", "Boolean", ""):
        return False
    cands = records.get(name)
    if not cands:
        return None
    # 限定名（`CredentialViews.Detail`）先用外层类名当文件提示，避免同名 record 串味（skill 坑 64）
    if len(parts) >= 2:
        hint = parts[-2] + ".java"
        if hint in cands:
            members = cands[hint]
            return (PAGE_COMPONENTS <= set(members)) if members else None
    sets = {frozenset(v) for v in cands.values()}
    if len(sets) > 1:
        return None  # 同名 record 多份且分量不同 → 不猜（skill 坑 64）
    members = next(iter(sets))
    return (PAGE_COMPONENTS <= set(members)) if members else None


def class_prefix(text: str, body: int) -> str:
    prefix = ""
    for m in REQ_MAPPING_RE.finditer(text[:body]):
        vals = re.findall(r'"([^"]*)"', m.group(1))
        if vals:
            prefix = vals[0]
    return prefix


def parse_controllers(ctrl_dir: Path) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """→ ({(METHOD, 归一路径): {ret, file}}, problems)。"""
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
            # 无实参的映射注解绝不能去 find(")")（skill 坑 63）
            if k < len(text) and text[k] == "(":
                close = match_paren(text, k)
                seg = text[k:close + 1] if close > 0 else ""
                sig_start = close + 1 if close > 0 else k
            else:
                seg = ""
                sig_start = m.end()
            paths = re.findall(r'"([^"]*)"', seg)
            sub = paths[0] if paths else ""
            mbody = body_brace(text, sig_start)
            if mbody < 0:
                problems.append(f"{f.name}: {m.group(0)} 未定位到方法体起点")
                continue
            sig = text[m.end():mbody]
            mm = re.search(r"\bpublic\s+([\w.<>,\[\]\s]+?)\s+\w+\s*\(", sig)
            ret = mm.group(1).strip() if mm else None
            out[key_of(m.group(1), prefix + sub)] = {"ret": ret, "file": f.name}
            found += 1
        if found == 0:
            problems.append(f"{f.name}: 类内未解析到任何方法级映射注解")
    return out, problems


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--all", action="store_true", help="列出全部明细（默认只列前 12 条）")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    paths = {k: root / v for k, v in REL_STATIC.items()}
    ctrl_dir = root / CONTROLLER_DIR
    schema_dir = root / SCHEMA_DIR

    missing = [f"{k}={p}" for k, p in paths.items() if not p.exists()]
    if not ctrl_dir.exists():
        missing.append(f"I={ctrl_dir}")
    if not schema_dir.exists():
        missing.append(f"S={schema_dir}")
    if missing:
        print("[FAIL] 源文件/目录缺失：" + ", ".join(missing))
        return 1

    watched = list(paths.values()) + sorted(ctrl_dir.rglob("*.java")) + \
        sorted(schema_dir.rglob("*.schema.json"))
    before = fingerprint(watched)

    r = Result()
    r.info(f"根目录：{rel_path(root, root)}（仓库外路径也照常显示，skill 坑 34）")

    total, manifest = parse_manifest(paths["M"])
    md_shapes, md_raw, md_problems = parse_md_shapes(paths["D"])
    otext = paths["O"].read_text(encoding="utf-8")
    ops, o_problems = parse_openapi(otext)
    comp_refs, comp_inline = parse_components(otext)
    impl, i_problems = parse_controllers(ctrl_dir)
    records = parse_records(ctrl_dir)

    r.info("--- 正向对照（解析器真的解析到了，skill 坑 46 / 72）---")
    r.check("A0a M 端点数 = total", total > 0 and len(manifest) == total,
            f"total={total} parsed={len(manifest)}")
    r.check("A0b D 行数 = total（转义竖线按未转义切分，坑 48）", len(md_raw) == total,
            f"parsed={len(md_raw)} 期望={total}")
    r.check("A0c O operation 数 = total", len(ops) == total,
            f"parsed={len(ops)} 期望={total}")
    r.check("A0d O 组件表解析到 $ref 组件（否则跨源比对是空转，坑 72）", len(comp_refs) > 0,
            f"$ref 组件={len(comp_refs)} 内联组件={len(comp_inline)}")
    r.check("A0e I 解析到控制器路由", len(impl) > 0, f"parsed={len(impl)} 条路由")
    r.check("A0f I 解析无异常", not i_problems, "; ".join(i_problems[:5]))
    r.check("A0g D 解析无异常（表头/列定位）", not md_problems, "; ".join(md_problems[:5]))
    r.check("A0h O 形状解析无 unknown（unknown 先怀疑解析器）", not o_problems,
            "; ".join(o_problems[:5]))
    r.check("A0i I 解析到 DTO record 声明（分页形状判据的正向对照）", len(records) > 0,
            f"record 类名={len(records)}")
    dist: dict[str, int] = {}
    for rec in ops.values():
        dist[rec["shape"]] = dist.get(rec["shape"], 0) + 1
    r.info(f"      O 形状分布：{dist}")
    mdist: dict[str, int] = {}
    for v in md_shapes.values():
        mdist[v] = mdist.get(v, 0) + 1
    r.info(f"      D 形状分布（散文，弱证据）：{mdist}")

    def impl_rec(eid: str) -> dict | None:
        return impl.get(key_of(manifest[eid]["method"], manifest[eid]["path"]))

    def impl_page(eid: str) -> bool | None:
        rec = impl_rec(eid)
        return dto_page_shape(rec.get("ret") if rec else None, records)

    r.info("--- A1 openapi 形状/组件绑定 ⇔ endpoints.json 的 response_model（逐端点）---")
    unlocated: dict[str, str] = {}
    comp_drift: dict[str, dict] = {}
    file_drift: dict[str, dict] = {}
    for eid in sorted(manifest):
        rec = ops.get(eid)
        if rec is None:
            unlocated[eid] = f"{manifest[eid]['method']} {manifest[eid]['path']}"
            continue
        want = manifest[eid]["resp"]
        if want is None:
            if rec["shape"] != "none":
                comp_drift[eid] = {"期望": "无 data（Envelope）", "openapi": rec["shape"]}
            continue
        want_comp = comp_name(want)
        got = rec["comps"]
        if not got or want_comp not in got:
            comp_drift[eid] = {"期望组件": want_comp, "openapi": got or rec["shape"]}
            continue
        f_ref = comp_refs.get(want_comp)
        if f_ref is None:
            file_drift[eid] = {"组件": want_comp, "问题": "组件不存在或不是 $ref"}
            continue
        want_file = f"./json-schema/models/{want}.schema.json"
        if f_ref != want_file:
            file_drift[eid] = {"组件": want_comp, "期望": want_file, "openapi": f_ref}
    r.check("A1a 清单每条端点在 openapi 里都能定位", not unlocated,
            f"未定位 {len(unlocated)} 条")
    for eid, d in (list(unlocated.items()) if args.all else list(unlocated.items())[:12]):
        r.info(f"      · {eid}: {d}")
    r.check("A1b 每端点 200 的 data 绑定组件 = PascalCase(response_model)", not comp_drift,
            f"不一致 {len(comp_drift)} 条")
    for eid, d in (list(comp_drift.items()) if args.all else list(comp_drift.items())[:12]):
        r.info(f"      · {eid}: {d}")
    r.check("A1c 被绑定组件解析到的文件 = models/<response_model>.schema.json", not file_drift,
            f"不一致 {len(file_drift)} 条")
    for eid, d in (list(file_drift.items()) if args.all else list(file_drift.items())[:12]):
        r.info(f"      · {eid}: {d}")

    r.info("--- A2 分页包装 ⇔ 实现返回分页形状 DTO（逐端点，硬断言）---")
    page_drift: dict[str, dict] = {}
    i_unknown: dict[str, str] = {}
    for eid in sorted(manifest):
        rec = ops.get(eid)
        if rec is None:
            continue
        o_page = rec["shape"] == "page"
        i_page = impl_page(eid)
        if i_page is None:
            i_unknown[eid] = (impl_rec(eid) or {}).get("ret") or "未定位"
            continue
        if o_page != i_page:
            page_drift[eid] = {
                "方法": manifest[eid]["method"], "路径": manifest[eid]["path"],
                "openapi": "分页 data={items,page,pageSize,total}" if o_page else "非分页",
                "实现": (impl_rec(eid) or {}).get("ret"),
                "md": md_shapes.get(eid, "?"),
            }
    r.check("A2 openapi 声明分页 ⇔ 实现返回分页形状 DTO（items+page+pageSize+total）",
            not page_drift, f"不一致 {len(page_drift)} 条（openapi 与实现至少一侧错）")
    for eid, d in (list(page_drift.items()) if args.all else list(page_drift.items())[:12]):
        r.info(f"      · {eid}: {d['方法']} {d['路径']} openapi={d['openapi']} "
               f"实现={d['实现']} md(散文)={d['md']}")
    r.check("A2b 未能静态判定的返回类型 ≤ 8（超出说明判据覆盖不足，坑 57）",
            len(i_unknown) <= 8, f"{len(i_unknown)} 条：{sorted(i_unknown.items())[:8]}")

    r.info("--- A3 第三证人（不依赖解析）：声明分页的端点必须带 page/pageSize 查询参数（清单 §0）---")
    selfcontra: dict[str, dict] = {}
    for eid in sorted(manifest):
        rec = ops.get(eid)
        if rec is None or rec["shape"] != "page":
            continue
        miss = {"page", "pageSize"} - set(rec["query"])
        if miss:
            selfcontra[eid] = {"缺": sorted(miss), "openapi_query": sorted(rec["query"])}
    r.check("A3 openapi 分页响应 ⇒ 该端点声明 page+pageSize 查询参数", not selfcontra,
            f"自相矛盾 {len(selfcontra)} 条")
    for eid, d in (list(selfcontra.items()) if args.all else list(selfcontra.items())[:12]):
        r.info(f"      · {eid}: 缺 {d['缺']}；openapi 参数={d['openapi_query']}")

    r.info("--- A4 反向：实现返回分页形状 DTO 的端点，openapi 必须声明分页 ---")
    rev = {eid: (impl_rec(eid) or {}).get("ret") for eid in sorted(manifest)
           if impl_page(eid) is True and (ops.get(eid) or {}).get("shape") != "page"}
    r.check("A4 实现分页形状 DTO ⇒ openapi 分页", not rev, f"不一致 {len(rev)} 条")
    for eid, ret in (list(rev.items()) if args.all else list(rev.items())[:12]):
        r.info(f"      · {eid}: 实现={ret}")

    r.info("--- A5 元素模型 schema 自身不得又是分页包装（否则双重包装）---")
    self_paged: dict[str, str] = {}
    for eid in sorted(manifest):
        want = manifest[eid]["resp"]
        if not want:
            continue
        sp = schema_dir / "models" / f"{want}.schema.json"
        sh = schema_shape(sp)
        if sh == "paged":
            self_paged[eid] = f"models/{want}.schema.json 自带 page/pageSize/total"
        elif sh != "object":
            self_paged[eid] = f"models/{want}.schema.json = {sh}"
    r.check("A5 元素模型 schema 存在且是单对象模型", not self_paged,
            f"异常 {len(self_paged)} 条")
    for eid, d in (list(self_paged.items()) if args.all else list(self_paged.items())[:12]):
        r.info(f"      · {eid}: {d}")

    r.info("--- A6 md 散文列弱证据（信息项，不判 FAIL；只作第三方裁判）---")
    md_list_not_page = sorted(eid for eid in manifest
                              if md_shapes.get(eid) == "list" and (ops.get(eid) or {}).get("shape") != "page")
    md_single_is_page = sorted(eid for eid in manifest
                               if md_shapes.get(eid) == "single" and (ops.get(eid) or {}).get("shape") == "page")
    r.info(f"      · md 说「列表」而 openapi 非分页：{len(md_list_not_page)} 条 {md_list_not_page[:12]}")
    r.info(f"      · md 说「单对象」而 openapi 声明分页：{len(md_single_is_page)} 条 {md_single_is_page[:12]}")
    r.check("A6a md 说「列表」而 openapi 非分页 ≤ 5（超出先怀疑散文解析，坑 65）",
            len(md_list_not_page) <= 5, f"{len(md_list_not_page)} 条")
    r.check("A6b D 解析到「列表」形状的端点 > 0（散文解析器的正向对照，坑 46）",
            sum(1 for v in md_shapes.values() if v == "list") > 0,
            f"列表={sum(1 for v in md_shapes.values() if v == 'list')} 单对象="
            f"{sum(1 for v in md_shapes.values() if v == 'single')}")

    r.info("--- A7 第三方裁判（不依赖任何解析）：漂移端点能否被「schema required」或「md 散文列」证伪 ---")
    # 契约测试把**真实响应体**与元素模型 schema 比对；若元素模型 schema 的 required 含非分页字段，
    # 则「分页包体」根本通不过该 schema → 真实响应不可能是分页的 → openapi 侧就是错的那一侧（skill 坑 51）。
    # 4 个模型的 required 为空（quote-compare / review-record / model-info / credential-precheck），
    # 对它们改用第二证人：md 散文列未声明 page/pageSize/分页 → 清单侧也没说要分页。
    PAGEFIELDS = {"items", "page", "pageSize", "total"}
    unproven: dict[str, str] = {}
    for eid in sorted(page_drift):
        want = manifest[eid]["resp"]
        sp = schema_dir / "models" / f"{want}.schema.json"
        try:
            req = set((json.loads(sp.read_text(encoding="utf-8")).get("required") or []))
        except Exception:
            req = set()
        if req and not (req <= PAGEFIELDS):
            continue
        cell = md_raw.get(eid, "")
        if not any(k in cell for k in ("page", "pageSize", "分页")):
            continue
        unproven[eid] = f"models/{want}.schema.json required={sorted(req)} 且 md 列未证伪：{cell[:40]}"
    r.check("A7 每个漂移端点都有第三方证伪（schema required 或 md 散文列未声明分页字段）",
            not unproven, f"无法证伪 {len(unproven)} 条")
    for eid, d in (list(unproven.items()) if args.all else list(unproven.items())[:12]):
        r.info(f"      · {eid}: {d}")

    r.info("--- A8 修复方向（待拍板，本审计不改任何文件）---")
    should_page = sorted(eid for eid in sorted(manifest) if impl_page(eid) is True)
    r.info(f"      · 实现返回分页形状 DTO 的端点（openapi 应声明分页）：{len(should_page)} 条 {should_page}")
    r.info(f"      · openapi 应改为非分页的端点：{len(page_drift)} 条 {sorted(page_drift)}")
    r.info("      · 生成器现状：`LIST_RESPONSE_MODELS` 是**模型级**集合（一个模型被列表端点与单对象端点共用时"
           "无法区分，如 detection-config / report-template / contract / sync-task / provider-profile），"
           "而 `PAGEABLE` 字典（端点级）已定义却**全文件零引用**（死码）。"
           "修法二选一：① 把 PAGEABLE 改成端点级白名单并让 `_enveloped()` 接收端点 ID；"
           "② 在 PATHS 元组里加 `pageable` 列。改完必须复跑本审计 + 生成器 --check + 全量测试。")

    after = fingerprint(watched)
    changed = [k for k in before if before[k] != after.get(k)]
    r.check("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed,
            f"被改写={len(changed)} 个：{changed[:3]}")

    print("\n".join(r.lines))
    print(f"\n== 断言：PASS {r.npass} / FAIL {r.nfail} ==")
    if r.nfail:
        print("结论：存在响应形状（分页包装）契约漂移 —— openapi 与实现/清单至少一侧不一致，"
              "两套门禁都看不见（契约测试只读 JSON Schema；覆盖门禁只比方法+路径）。")
        return 1
    print("结论：逐端点响应形状一致（openapi ⇔ 实现 ⇔ 元素模型 schema；md 散文列作第三方裁判）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
