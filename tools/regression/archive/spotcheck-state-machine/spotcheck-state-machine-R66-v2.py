#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R66 抽查（只读）：状态变更（from → to）语义一致性（第四十类可审计不变量）。v2

为什么两套门禁都看不见：
  · 契约测试只把**响应体**与 JSON Schema 比对 —— 一次**被静默接受的非法流转**照样返回 200 + 合法 schema，
    状态列是否被合法推进**不在 schema 里** → 全量用例全绿也看不见。
  · 覆盖门禁只比「方法 + 路径」；openapi 与客户端 TS 不被任何测试读取/执行。
真源：
  M = docs/backend/02-API接口模型清单.md 逐端点的「错误码」列（状态类码）与「请求/响应」列的 from→to 声明
  S = 实现手写 SQL：`set status = <to>` 语句的 where 守卫集合（status = / in / <> / is null）—— 含**常量引用**
  O = 实现 ORM：`setStatus(` 写点（区分「创建时置初始状态」与「流转」）与其同方法体内的守卫证据
  J = 实现自述（Javadoc 里的 `X|Y → Z` 流转声明）
  E = ErrorCode.java 状态类码（码 → HTTP）
  T = 测试源里的状态类码断言（码级）与 HTTP 状态断言（结构级）
  P = .calicat/prd/17-零歧义执行规格spec.md §4 状态枚举（「任何不在合法流转表内的变更拒绝 E-1601」）
  D = 落库状态值可追溯性：spec §4 ∪ md 清单 ∪ 01-ER ∪ .calicat/prd/15-数据模型
用法：python spotcheck-state-machine-R66.py --root <repo>
"""
import argparse
import re
import sys
from pathlib import Path

FAIL = []
INFO = []
PASS = []


def emit(tag, aid, msg):
    line = "[%s] %s %s" % (tag, aid, msg)
    print(line)
    if tag == "FAIL":
        FAIL.append(aid)
    elif tag == "INFO":
        INFO.append(aid)
    else:
        PASS.append(aid)


# --------------------------------------------------------------------------- Java 词法
def strip_comments(src):
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif src[i] in ('"', "'"):
            q = src[i]
            if src.startswith('"""', i):
                j = i + 3
                while j < n:
                    if src.startswith('"""', j) and src[j - 1] != "\\":
                        break
                    j += 1
                i = j + 3
            else:
                j = i + 1
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == q:
                        break
                    j += 1
                i = j + 1
        else:
            i += 1
    return "".join(out)


def java_literals(code):
    out = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == '"':
            if code.startswith('"""', i):
                j = i + 3
                while j < n:
                    if code.startswith('"""', j) and code[j - 1] != "\\":
                        break
                    j += 1
                out.append((i, j + 3, "textblock", code[i + 3:j]))
                i = j + 3
                continue
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == '"':
                    break
                j += 1
            out.append((i, j + 1, "string", code[i + 1:j]))
            i = j + 1
            continue
        if c == "'":
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == "'":
                    break
                j += 1
            out.append((i, j + 1, "char", code[i + 1:j]))
            i = j + 1
            continue
        i += 1
    return out


def match_paren(s, i, op="(", cl=")"):
    if i >= len(s) or s[i] != op:
        return -1
    depth = 0
    j = i
    while j < len(s):
        ch = s[j]
        if ch in ('"', "'"):
            q = ch
            j += 1
            while j < len(s):
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == q:
                    break
                j += 1
        elif ch == op:
            depth += 1
        elif ch == cl:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def find_top(s, kw, start=0):
    depth, i, n, kwl = 0, start, len(s), kw.lower()
    while i < n:
        ch = s[i]
        if ch == "'":
            i += 1
            while i < n:
                if s[i] == "'":
                    if i + 1 < n and s[i + 1] == "'":
                        i += 2
                        continue
                    break
                i += 1
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif depth == 0 and s[i:i + len(kw)].lower() == kwl:
            if (i == 0 or not (s[i - 1].isalnum() or s[i - 1] == "_")) and \
               (i + len(kw) >= n or not (s[i + len(kw)].isalnum() or s[i + len(kw)] == "_")):
                return i
        i += 1
    return -1


def split_sql_statements(text):
    out, depth, i, start, n = [], 0, 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "'":
            i += 1
            while i < n:
                if text[i] == "'":
                    if i + 1 < n and text[i + 1] == "'":
                        i += 2
                        continue
                    break
                i += 1
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == ";" and depth == 0:
            out.append((start, text[start:i]))
            start = i + 1
        i += 1
    out.append((start, text[start:]))
    return out


def line_of(src, off):
    return src.count("\n", 0, off) + 1


def rel(p, root):
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


METHOD_RE = re.compile(
    r"(?m)^[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*\n[ \t]*)*"
    r"(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?"
    r"(?:[\w.$<>\[\],?\s]+?\s)?(\w+)\s*\(")
# 注：返回类型里可能有**逗号+空格**（`PageResult<Map<String, Object>>`）→ 字符类必须含 `\s`，
# 否则该方法整段收不进方法表，其内的 setStatus 被判「未能静态判定」（R66 真实返工）。


def java_methods(code):
    out = []
    for m in METHOD_RE.finditer(code):
        op = code.find("(", m.end() - 1)
        if op < 0:
            continue
        cl = match_paren(code, op)
        if cl < 0:
            continue
        bs = code.find("{", cl)
        if bs < 0:
            continue
        be = match_paren(code, bs, "{", "}")
        if be < 0:
            continue
        out.append((m.group(1), m.start(), bs, be))
    return out


# --------------------------------------------------------------------------- spec §4
ENUM_LINE = re.compile(r"^\s*(\w+)(Status|Type)?：([A-Z_/\\]+)", re.M)


def parse_spec_enums(path):
    enums = {}
    if not path.exists():
        return enums
    for m in ENUM_LINE.finditer(path.read_text(encoding="utf-8", errors="replace")):
        name = m.group(1) + (m.group(2) or "")
        vals = {v.strip() for v in m.group(3).replace("\\", "").split("/") if v.strip()}
        vals = {v for v in vals if re.fullmatch(r"[A-Z][A-Z0-9_]*", v)}
        if vals:
            enums[name] = vals
    return enums


def all_spec_values(enums):
    out = set()
    for v in enums.values():
        out |= v
    return out


# --------------------------------------------------------------------------- 实现：SQL
STATUS_SET = re.compile(r"\bstatus\s*=\s*('([^']*)'|\?)", re.I)
GUARD_EQ = re.compile(r"\bstatus\s*=\s*'([A-Z_]+)'", re.I)
GUARD_IN = re.compile(r"\bstatus\s+in\s*\(([^)]*)\)", re.I)
GUARD_NE = re.compile(r"\bstatus\s*<>\s*'([A-Z_]+)'", re.I)
GUARD_NULL = re.compile(r"\bstatus\s+is\s+(not\s+)?null", re.I)
GUARD_PARAM = re.compile(r"\bstatus\s*=\s*\?", re.I)
CONST_DEF = re.compile(r"(?:static\s+)?final\s+String\s+(\w+)\s*=\s*(\"\"\"[\s\S]*?\"\"\"|\"(?:[^\"\\]|\\.)*\")")


def parse_constants(code):
    """→ {常量名: SQL 文本}（常量引用的 SQL 是真实写法，坑 99-①）。"""
    out = {}
    for m in CONST_DEF.finditer(code):
        lit = m.group(2)
        if lit.startswith('"""'):
            out[m.group(1)] = lit[3:-3]
        else:
            out[m.group(1)] = lit[1:-1]
    return out


def parse_sql_status_writes(paths, root):
    out = []
    for p in sorted(paths):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        lits = java_literals(code)
        consts = parse_constants(code)
        for m in re.finditer(r"\.update\s*\(", code):
            op = code.find("(", m.end() - 1)
            cl = match_paren(code, op)
            if cl < 0:
                continue
            arg = code[op + 1:cl]
            span = [(a, b, k, t) for (a, b, k, t) in lits if a > op and b <= cl]
            chunks = [t for (_a, _b, _k, t) in span]
            for ident in re.findall(r"(?<![\w.])([A-Z][A-Z0-9_]{2,})\b", arg):
                if ident in consts:
                    chunks.append(consts[ident])
            if not chunks:
                continue
            sql_all = " ".join(chunks)
            if not re.search(r"\bset\b[\s\S]*?\bstatus\s*=", sql_all, re.I):
                continue
            base = span[0][0] if span else op
            for (off, stmt) in split_sql_statements(sql_all):
                if not re.search(r"\bset\b[\s\S]*?\bstatus\s*=", stmt, re.I):
                    continue
                set_i = find_top(stmt, "set")
                where_i = find_top(stmt, "where")
                if set_i < 0:
                    continue
                set_clause = stmt[set_i:where_i] if where_i > set_i else stmt[set_i:]
                where_clause = stmt[where_i:] if where_i > set_i else ""
                tm = STATUS_SET.search(set_clause)
                if not tm:
                    continue
                to_kind = "literal" if tm.group(2) is not None else "param"
                to_val = tm.group(2) if to_kind == "literal" else "?"
                guards = set()
                for g in GUARD_EQ.findall(where_clause):
                    guards.add(g)
                for g in GUARD_NE.findall(where_clause):
                    guards.add("<>" + g)
                for grp in GUARD_IN.findall(where_clause):
                    for v in re.findall(r"'([A-Z_]+)'", grp):
                        guards.add(v)
                if GUARD_NULL.search(where_clause):
                    guards.add("IS_NULL")
                weak = bool(GUARD_PARAM.search(where_clause))
                table = ""
                tm2 = re.search(r"\bupdate\s+([a-z_][a-z0-9_]*)", stmt, re.I)
                if tm2:
                    table = tm2.group(1)
                out.append({"file": rel(p, root), "line": line_of(code, base + off),
                            "sql": stmt.strip(), "to_kind": to_kind, "to": to_val,
                            "guards": sorted(guards), "weak": weak, "table": table})
    return out


# --------------------------------------------------------------------------- 实现：ORM
ORM_SET = re.compile(r"(?<![\w.])(\w+)\.setStatus\s*\(")
SIBLING_READ = re.compile(r"(\w+)\.(getGateStatus|getSyncStatus|getDetectStatus|getReviewStatus)\s*\(\s*\)")
CONTAINS_GUARD = re.compile(r"!?\s*[\w.]*\.contains\s*\(\s*(\w+)\.(?:getStatus|status)\s*\(\s*\)\s*\)")
EQUALS_GUARD = re.compile(r"(?:!\s*)?(\w+)\.(?:getStatus|status)\s*\(\s*\)\s*\.equals\s*\(")
LIT_EQUALS_GUARD = re.compile(r"(?:!\s*)?\"([A-Z_]+)\"\s*\.equals\s*\(\s*(\w+)\.(?:getStatus|status)\s*\(\s*\)\s*\)")
SWITCH_GUARD = re.compile(r"switch\s*\(\s*(\w+)\.(?:getStatus|status)\s*\(\s*\)\s*\)")
REJECT = re.compile(r"throw\s+new\s+ApiException|throw\s+new\s+[A-Z]\w*Exception|errors\.add\s*\(")
OPTIMISTIC = re.compile(r"ifMatch|getVersion\s*\(\s*\)|\.update\s*\(\s*\w+\s*\)\s*!=\s*1|rows\s*!=\s*1")


def parse_orm_status_writes(paths, root):
    out = []
    for p in sorted(paths):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        methods = java_methods(code)
        for m in ORM_SET.finditer(code):
            recv = m.group(1)
            if recv in ("response", "builder", "resp"):
                continue
            if re.search(r"void\s+$", code[max(0, m.start() - 12):m.start()]):
                continue
            op = code.find("(", m.end() - 1)
            cl = match_paren(code, op)
            arg = code[op + 1:cl].strip() if cl > 0 else ""
            tm = re.match(r'"([^"]*)"', arg)
            to_val = tm.group(1) if tm else (arg[:40] or "?")
            body = None
            for (_nm, _ss, bs, be) in methods:
                if bs < m.start() < be and (body is None or (be - bs) < (body[1] - body[0])):
                    body = (bs, be)
            if body is None:
                out.append({"file": rel(p, root), "line": line_of(code, m.start()), "recv": recv,
                            "to": to_val, "kind": "unknown", "cls": "未能静态判定", "sib": False})
                continue
            b = code[body[0]:body[1]]
            is_create = bool(re.search(r"\bnew\s+\w*(?:Entity|Record)\s*\(", b)) or bool(re.search(r"\.insert\s*\(", b))
            self_read = bool(re.search(r"\b%s\.(?:getStatus|status)\s*\(\s*\)" % re.escape(recv), b))
            other_read = any(r != recv for r in
                             re.findall(r"(\w+)\.(?:getStatus|status)\s*\(\s*\)", b))
            sibling = bool(SIBLING_READ.search(b))
            reject = bool(REJECT.search(b))
            optimistic = bool(OPTIMISTIC.search(b))
            if is_create:
                cls = "create"
            elif self_read and reject:
                cls = "strong"
            elif sibling and reject:
                cls = "sibling"
            elif other_read and reject and optimistic:
                cls = "related"
            elif reject and optimistic:
                cls = "optimistic"
            else:
                cls = "none"
            out.append({"file": rel(p, root), "line": line_of(code, m.start()), "recv": recv,
                        "to": to_val, "kind": "create" if is_create else "transition",
                        "cls": cls, "sib": sibling})
    return out


# --------------------------------------------------------------------------- 实现自述（Javadoc）
JDOC = re.compile(r"/\*\*([\s\S]*?)\*/")
SELF_TRANS = re.compile(r"([A-Z][A-Z0-9_]*(?:\s*\|\s*[A-Z][A-Z0-9_]*)*)\s*→\s*([A-Z][A-Z0-9_]*)")


def parse_self_declared_transitions(paths, root):
    out = []
    for p in sorted(paths):
        raw = p.read_text(encoding="utf-8", errors="replace")
        for m in JDOC.finditer(raw):
            body = m.group(1)
            for t in SELF_TRANS.finditer(body):
                frm = [x.strip() for x in t.group(1).split("|")]
                if all(re.fullmatch(r"[A-Z][A-Z0-9_]*", x) for x in frm):
                    out.append((rel(p, root), line_of(raw, m.start()), tuple(frm), t.group(2)))
    return out


# --------------------------------------------------------------------------- md / ER / 码表
def md_cells(line):
    parts = re.split(r"(?<!\\)\|", line.strip())
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [c.replace("\\|", "|").strip() for c in parts]


def parse_md_manifest(path):
    rows, n10, n7 = [], 0, 0
    if not path.exists():
        return rows, 0, 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = md_cells(line)
        if len(cells) >= 10 and cells[1] == "方法":
            n10 += 1
            continue
        if len(cells) == 7 and cells[1] == "方法":
            n7 += 1
            continue
        if len(cells) >= 10 and re.fullmatch(r"[A-Z]+-[A-Z0-9]+", cells[0]):
            rows.append((cells[0], cells[6], cells[5], cells[8], cells[9]))
        elif len(cells) == 7 and re.fullmatch(r"[A-Z]+-[A-Z0-9]+", cells[0]):
            rows.append((cells[0], cells[5], cells[4], "", cells[6]))
    return rows, n10, n7


MD_CODE_TABLE = re.compile(r"^\|\s*`(E-\d{4})`\s*\|\s*(\d{3})\s*\|\s*([^|]*)\|")


def parse_md_code_table(path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = MD_CODE_TABLE.match(line)
        if m:
            out[m.group(1)] = (int(m.group(2)), m.group(3).strip())
    return out


def parse_error_codes(path):
    out = {}
    if not path.exists():
        return out
    for m in re.finditer(r'E_(\d{4})\(\s*"(E-\d{4})"\s*,\s*(\d{3})\s*,\s*"([^"]*)"',
                         path.read_text(encoding="utf-8", errors="replace")):
        out[m.group(2)] = (int(m.group(3)), m.group(4))
    return out


STATE_CODE_DESC = re.compile(r"状态|终态|不可取消|已结束|未签署")


def state_codes_from_table(table):
    return {c for c, (http, desc) in table.items() if http == 409 and STATE_CODE_DESC.search(desc)}


ARROW_INLINE = re.compile(r"（\s*([A-Z_]+)\s*→\s*([A-Z_]+)\s*[，,]?")


def parse_md_transitions(rows):
    out = []
    for (eid, _codes, resp, basis, _task) in rows:
        for cell in (resp, basis):
            if not cell:
                continue
            for m in ARROW_INLINE.finditer(cell):
                out.append((eid, m.group(1), m.group(2)))
    return out


def doc_upper_tokens(paths):
    out = set()
    for p in paths:
        if not p.exists():
            continue
        for t in re.findall(r"[A-Z][A-Z0-9_]{2,}", p.read_text(encoding="utf-8", errors="replace")):
            out.add(t)
    return out


# --------------------------------------------------------------------------- 测试
TEST_CODE = re.compile(r'"\s*(E-\d{4})\s*"')
STATUS_ASSERT = re.compile(r"\.status(?:Code)?\s*\(\s*\)\s*\)?[\s\S]{0,40}?\.isEqualTo\s*\(\s*(\d{3})\s*\)")


def parse_tests(paths):
    code_asserts, http_asserts = {}, {}
    for p in sorted(paths):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in TEST_CODE.finditer(text):
            code_asserts.setdefault(m.group(1), []).append((str(p), text.count("\n", 0, m.start()) + 1))
        for m in STATUS_ASSERT.finditer(text):
            http_asserts[m.group(1)] = http_asserts.get(m.group(1), 0) + 1
    return code_asserts, http_asserts


# --------------------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--src", default=None)
    ap.add_argument("--tests-dir", default=None)
    ap.add_argument("--md", default=None)
    ap.add_argument("--spec", default=None)
    ap.add_argument("--er", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    src = Path(a.src) if a.src else root / "aap-server/src/main/java"
    tests = Path(a.tests_dir) if a.tests_dir else root / "aap-server/src/test/java"
    md = Path(a.md) if a.md else root / "docs/backend/02-API接口模型清单.md"
    spec = Path(a.spec) if a.spec else root / ".calicat/prd/17-零歧义执行规格spec.md"
    er = Path(a.er) if a.er else root / "docs/backend/01-ER数据模型.md"
    prd15 = root / ".calicat/prd/15-数据模型ER与数据字典.md"

    print("== R66 抽查（只读）：状态变更（from → to）语义一致性（第四十类可审计不变量） ==")
    print("为什么两套门禁都看不见：契约测试只把**响应体**与 JSON Schema 比对 —— 被静默接受的非法流转照样返回 200 +")
    print("合法 schema，状态列是否被合法推进不在 schema 里；覆盖门禁只比「方法 + 路径」；openapi 与客户端 TS 不被执行。")
    print("真源：M md 逐端点错误码列/响应列 · S 手写 SQL（含常量引用）set status 的 where 守卫 · O ORM setStatus 写点")
    print("      与其守卫分类 · J 实现自述（Javadoc 流转） · E ErrorCode.java 状态类码 · T 测试码级/结构级断言 ·")
    print("      P spec §4 状态枚举 · D 落库状态值可追溯性（spec §4 ∪ md ∪ ER ∪ prd15）。")
    print("root = %s" % root)

    java_main = sorted(src.rglob("*.java")) if src.exists() else []
    java_tests = sorted(tests.rglob("*.java")) if tests.exists() else []

    enums = parse_spec_enums(spec)
    spec_vals = all_spec_values(enums)
    md_table = parse_md_code_table(md)
    ec = parse_error_codes(src / "com/hioas/aap/common/ErrorCode.java")
    state_codes = state_codes_from_table(md_table) or state_codes_from_table(ec)
    rows, n10, n7 = parse_md_manifest(md)
    transitions = parse_md_transitions(rows)
    sql_writes = parse_sql_status_writes(java_main, root)
    orm_writes = parse_orm_status_writes(java_main, root)
    self_decl = parse_self_declared_transitions(java_main, root)
    code_asserts, http_asserts = parse_tests(java_tests)
    doc_vals = doc_upper_tokens([md, er, prd15]) | spec_vals

    guarded_sql = [w for w in sql_writes if w["guards"]]
    trans_orm = [w for w in orm_writes if w["kind"] == "transition"]
    create_orm = [w for w in orm_writes if w["kind"] == "create"]
    unk_orm = [w for w in orm_writes if w["kind"] == "unknown"]
    by_cls = {}
    for w in trans_orm:
        by_cls[w["cls"]] = by_cls.get(w["cls"], 0) + 1
    md_state_endpoints = [(r[0], [c for c in re.findall(r"E-\d{4}", r[1]) if c in state_codes]) for r in rows]
    md_state_endpoints = [(i, cs) for (i, cs) in md_state_endpoints if cs]
    n_state_assert = sum(len(v) for k, v in code_asserts.items() if k in state_codes)

    print("解析计数：spec 状态枚举 %d 组/%d 值 · md 清单 %d 行（10 列表 %d + 7 列表 %d）· md 码表 %d 码（状态类 %d）· "
          "实现 SQL 状态变更语句 %d（带守卫 %d）· ORM setStatus 写点 %d（流转 %d / 创建 %d / 未判定 %d）· "
          "实现自述流转 %d · md from→to 声明 %d · 测试状态类码断言 %d 处 / HTTP 状态断言 %s"
          % (len(enums), len(spec_vals), len(rows), n10, n7, len(md_table), len(state_codes),
             len(sql_writes), len(guarded_sql), len(orm_writes), len(trans_orm), len(create_orm),
             len(unk_orm), len(self_decl), len(transitions), n_state_assert,
             "、".join("%s×%d" % (k, v) for k, v in sorted(http_asserts.items())) or "0 处"))
    print("ORM 流转守卫分类：%s" % "、".join("%s=%d" % (k, by_cls[k]) for k in sorted(by_cls)))
    print("")

    # ---------------- 正向对照
    if len(enums) > 0 and len(spec_vals) > 0:
        emit("PASS", "A0a", "spec §4 解析到状态枚举 %d 组 / %d 个状态值" % (len(enums), len(spec_vals)))
    else:
        emit("FAIL", "A0a", "spec §4 状态枚举解析为 0 → 判定不可用")
    if len(md_table) > 0 and len(state_codes) > 0:
        emit("PASS", "A0b", "md §4 码表解析到 %d 个码，其中状态类码 %d 个：%s"
             % (len(md_table), len(state_codes), " ".join(sorted(state_codes))))
    else:
        emit("FAIL", "A0b", "md §4 码表或状态类码解析为 0 → 判定不可用")
    if n10 > 0 and n7 > 0 and len(rows) > 0:
        emit("PASS", "A0c", "md 清单解析到 %d 行（两套表头 %d + %d 合计，坑 89）" % (len(rows), n10, n7))
    else:
        emit("FAIL", "A0c", "md 清单解析行数异常（10 列 %d / 7 列 %d / 行 %d）→ 判定不可用" % (n10, n7, len(rows)))
    if len(sql_writes) > 0 and len(guarded_sql) > 0:
        emit("PASS", "A0d", "实现解析到 SQL 状态变更语句 %d 条（含常量引用解析），其中带 from 守卫 %d 条"
             % (len(sql_writes), len(guarded_sql)))
    else:
        emit("FAIL", "A0d", "SQL 状态变更语句或带守卫语句解析为 0（%d / %d）→ 判定不可用" % (len(sql_writes), len(guarded_sql)))
    if len(orm_writes) > 0 and len(trans_orm) > 0 and len(create_orm) > 0:
        emit("PASS", "A0e", "实现解析到 ORM setStatus 写点 %d 个（流转 %d / 创建 %d）" % (len(orm_writes), len(trans_orm), len(create_orm)))
    else:
        emit("FAIL", "A0e", "ORM 写点分类异常（总 %d / 流转 %d / 创建 %d）→ 判定不可用" % (len(orm_writes), len(trans_orm), len(create_orm)))
    if len(transitions) > 0:
        emit("PASS", "A0f", "md 清单解析到 from→to 声明 %d 条：%s"
             % (len(transitions), "、".join("%s %s→%s" % t for t in transitions)))
    else:
        emit("FAIL", "A0f", "md 清单 from→to 声明解析为 0 → 判定不可用")
    if n_state_assert > 0:
        emit("PASS", "A0g", "测试源解析到状态类码断言 %d 处（码级背书）" % n_state_assert)
    else:
        emit("FAIL", "A0g", "测试状态类码断言解析为 0 → 判定不可用")
    if len(self_decl) > 0:
        emit("PASS", "A0h", "实现自述（Javadoc）解析到流转声明 %d 条" % len(self_decl))
    else:
        emit("FAIL", "A0h", "实现自述流转声明解析为 0 → 判定不可用")

    # ---------------- A1 手写 SQL
    bad_sql = [w for w in sql_writes if not w["guards"]]
    if bad_sql:
        det = " | ".join("%s:%d %s（表 %s，to=%s%s）" % (w["file"], w["line"], re.sub(r"\s+", " ", w["sql"])[:56],
                                                       w["table"], w["to"],
                                                       "，参数化目标状态" if w["to_kind"] == "param" else "")
                         for w in bad_sql)
        emit("FAIL", "A1", "手写 SQL 状态变更**缺 from 守卫** %d 条（非法流转会被静默接受）：%s" % (len(bad_sql), det))
    else:
        emit("PASS", "A1", "全部 %d 条手写 SQL 状态变更语句都带 from 守卫" % len(sql_writes))

    # ---------------- A2 ORM 流转点
    bad_orm = [w for w in trans_orm if w["cls"] == "none"]
    if bad_orm:
        det = " | ".join("%s:%d %s.setStatus(\"%s\") 无任何守卫证据" % (w["file"], w["line"], w["recv"], w["to"]) for w in bad_orm)
        emit("FAIL", "A2", "ORM 状态流转点无守卫证据 %d 个：%s" % (len(bad_orm), det))
    else:
        emit("PASS", "A2", "全部 %d 个 ORM 状态流转点都有守卫证据（分类见 A2c/A2d/A2e）" % len(trans_orm))
    if unk_orm:
        emit("INFO", "A2b", "ORM setStatus 未能静态判定 %d 个：%s"
             % (len(unk_orm), " | ".join("%s:%d %s" % (w["file"], w["line"], w["recv"]) for w in unk_orm)))
    for cls, cap, label in (("related", 4, "守卫在**关联实体**状态上（需同时有对被写实体的乐观锁/条件更新断言）"),
                            ("sibling", 2, "守卫在**姊妹列**上（如 gate_status）"),
                            ("optimistic", 2, "**仅乐观锁**守卫（防并发，不防非法流转）")):
        hits = [w for w in trans_orm if w["cls"] == cls]
        if not hits:
            continue
        tag = "FAIL" if len(hits) > cap else "INFO"
        emit(tag, "A2%s" % {"related": "c", "sibling": "d", "optimistic": "e"}[cls],
             "%s %d 个（上限 %d）：%s" % (label, len(hits), cap,
                                        " | ".join("%s:%d %s.setStatus(\"%s\")" % (w["file"], w["line"], w["recv"], w["to"]) for w in hits)))

    # ---------------- A3 md from→to ⇔ 实现守卫
    sql_index, orm_index = {}, {}
    for w in sql_writes:
        if w["to"] and w["to"] != "?":
            sql_index.setdefault(w["to"], []).append((w["file"], w["line"], w["guards"]))
    for w in orm_writes:
        orm_index.setdefault(w["to"], []).append((w["file"], w["line"], w["cls"]))
    drift = []
    for (eid, frm, to) in transitions:
        impl = sql_index.get(to, []) + [(f, ln, []) for (f, ln, _c) in orm_index.get(to, [])]
        if not impl:
            drift.append("%s md 声明 %s→%s，实现里找不到把状态写成 %s 的写点" % (eid, frm, to, to))
            continue
        if not any(frm in gs for (_f, _l, gs) in impl):
            drift.append("%s md 声明 %s→%s，实现写点（%s）from 守卫=%s（不含 %s）"
                         % (eid, frm, to, " / ".join("%s:%d" % (f, ln) for (f, ln, _g) in impl[:3]),
                            "/".join(sorted(set(g for (_f, _l, gs) in impl for g in gs))) or "无", frm))
    if transitions and not drift:
        emit("PASS", "A3", "md 声明的 %d 条 from→to 与实现的守卫/目标状态逐条一致" % len(transitions))
    elif drift:
        emit("FAIL", "A3", "md from→to 与实现不一致 %d 条：%s" % (len(drift), " | ".join(drift)))
    else:
        emit("FAIL", "A3", "md from→to 声明为 0，判定不可用")

    # ---------------- A3b 实现自述 ⇔ 实现守卫（同文件两种写法，坑 44）
    # 判据范围必须与语义一致（坑 81/140）：ORM 写点的守卫是**内存守卫**，from 集合无法静态提取
    #   → 只在「该 to 存在**手写 SQL 写点**」时才做 from 覆盖的硬断言；
    #     纯 ORM 写点只做「有没有守卫」的核验（无守卫才是 FAIL），其余记 INFO。
    self_drift, self_info = [], []
    for (f, ln, frms, to) in self_decl:
        sqlw = sql_index.get(to, [])
        ormw = orm_index.get(to, [])
        if sqlw:
            all_guards = set(g for (_f, _l, gs) in sqlw for g in gs)
            if not all_guards:
                self_drift.append("%s:%d 自述 %s→%s，但实现里写向 %s 的 SQL 语句**全部没有守卫**"
                                  % (f, ln, "|".join(frms), to, to))
            elif not set(frms) <= all_guards:
                self_drift.append("%s:%d 自述 %s→%s，实现 SQL 守卫=%s"
                                  % (f, ln, "|".join(frms), to, "/".join(sorted(all_guards))))
            else:
                self_info.append("%s:%d 自述 %s→%s ⇔ SQL 守卫 %s 一致"
                                 % (f, ln, "|".join(frms), to, "/".join(sorted(all_guards))))
        elif ormw:
            classes = {c for (_f, _l, c) in ormw}
            if classes == {"none"}:
                self_drift.append("%s:%d 自述 %s→%s，但实现里写向 %s 的写点**全部无守卫**"
                                  % (f, ln, "|".join(frms), to, to))
            else:
                self_info.append("%s:%d 自述 %s→%s 由 ORM 内存守卫承接（%s），from 集合无法静态核验"
                                 % (f, ln, "|".join(frms), to, "/".join(sorted(classes))))
    if self_decl and not self_drift:
        emit("PASS", "A3b", "实现自述的 %d 条流转声明与实现的守卫集合一致（其中 ORM 内存守卫 %d 条仅核验「有守卫」）"
             % (len(self_decl), len(self_info)))
    elif self_drift:
        emit("FAIL", "A3b", "实现自述与守卫集合不一致 %d 条：%s" % (len(self_drift), " | ".join(self_drift)))
    if self_info:
        emit("INFO", "A3c", "自述流转的守卫承接方式 %d 条（SQL 守卫可直接核验 from；ORM 内存守卫只能核验「有守卫」）：%s"
             % (len(self_info), " | ".join(self_info)))

    # ---------------- A4 状态类码可达性
    impl_throw = {}
    for p in java_main:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"ErrorCode\.(E_\d{4})", text):
            impl_throw.setdefault("E-" + m.group(1)[2:], []).append(
                "%s:%d" % (rel(p, root), text.count("\n", 0, m.start()) + 1))
    missing_throw = [c for c in sorted(state_codes) if c not in impl_throw]
    if not state_codes:
        emit("FAIL", "A4", "状态类码集合为空 → 判定不可用（不得判 PASS，坑 98）")
    elif missing_throw:
        emit("FAIL", "A4", "md 声明的状态类码在实现里零抛点 %d 个：%s" % (len(missing_throw), " ".join(missing_throw)))
    else:
        emit("PASS", "A4", "md 声明的 %d 个状态类码在实现里都有抛点（%s）"
             % (len(state_codes), "、".join("%s×%d" % (c, len(impl_throw[c])) for c in sorted(state_codes))))

    # ---------------- A5 落库状态值可追溯性
    written = {}
    for w in sql_writes:
        if w["to_kind"] == "literal" and w["to"]:
            written.setdefault(w["to"], []).append("%s:%d" % (w["file"], w["line"]))
    for w in orm_writes:
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", w["to"] or ""):
            written.setdefault(w["to"], []).append("%s:%d" % (w["file"], w["line"]))
    untraceable = {v: loc for v, loc in written.items() if v not in doc_vals}
    if untraceable:
        emit("FAIL", "A5", "落库状态值在任何冻结文档（spec §4 / md / ER / prd15）里都查不到 %d 个：%s"
             % (len(untraceable), "、".join("%s(%s)" % (v, loc[0]) for v, loc in sorted(untraceable.items()))))
    else:
        emit("PASS", "A5", "全部 %d 个落库状态值都可在冻结文档里追溯" % len(written))
    only_impl = sorted(v for v in written if v not in spec_vals)
    emit("INFO", "A5b", "spec §4 未声明、但 md/ER/prd15 已声明并实际落库的状态值 %d 个（文档一致性项，需人拍板是补 spec §4 还是判实现越界）：%s"
         % (len(only_impl), "、".join("%s(%d 处)" % (v, len(written[v])) for v in only_impl)))

    # ---------------- A6 测试背书分档
    zero = [eid for (eid, cs) in md_state_endpoints if not any(c in code_asserts for c in cs)]
    if md_state_endpoints:
        emit("INFO", "A6", "声明状态类码的端点 %d 个：码级背书 %d / 零背书 %d（%s）"
             % (len(md_state_endpoints), len(md_state_endpoints) - len(zero), len(zero),
                "、".join(zero) if zero else "无"))
    else:
        emit("FAIL", "A6", "md 未解析到任何声明状态类码的端点 → 判定不可用")
    for c in sorted(state_codes):
        hits = code_asserts.get(c, [])
        emit("INFO", "A6b", "%s 测试断言 %d 处%s" % (c, len(hits),
                                                    "（" + "、".join("%s:%d" % (Path(f).name, l) for (f, l) in hits[:4]) + "）" if hits else "（零背书）"))
    emit("INFO", "A6c", "**结构级**（HTTP 状态）背书：409 断言 %d 处 / 200 断言 %d 处 —— 码级断言不能替代状态码断言（坑 143-①：码断言 + 状态码断言才是完整背书）"
         % (http_asserts.get("409", 0), http_asserts.get("200", 0)))

    # ---------------- A7 宽守卫 / 参数化目标状态
    wide = [w for w in sql_writes if w["guards"] and all(g.startswith("<>") or g == "IS_NULL" for g in w["guards"])]
    param_to = [w for w in sql_writes if w["to_kind"] == "param"]
    emit("INFO", "A7", "宽守卫（status <> X / is null，可能放行未声明来源）%d 条；目标状态为参数（to 无法静态判定）%d 条：%s"
         % (len(wide), len(param_to),
            " | ".join("%s:%d 表 %s 守卫=%s" % (w["file"], w["line"], w["table"], "/".join(w["guards"]) or "无")
                       for w in param_to[:8])))

    print("")
    print("汇总：PASS %d / FAIL %d / INFO %d" % (len(PASS), len(FAIL), len(INFO)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
