"""R50 抽查：审计留痕一致性与完整性 —— 第二十四类可审计不变量（抽查式，不新建仓库工具）。

不变量：`aap_audit_log` 的**声明面**（DDL 列 / ER 文档字段行 / 契约 JSON Schema / 查询列 / 响应视图）
与**写入面**（AuditService 写入路径实际 set 的列 / record 调用点实际使用的 action 常量）
必须一致，且 append-only（C8：无 UPDATE/DELETE）。

为什么两套门禁都看不见：
  * 契约测试只校验**响应体**与 JSON Schema：`audit-log.schema.json` 的 `additionalProperties: true`，
    且审计写入路径（INSERT 到 aap_audit_log）不在任何响应里 → 写入面漏列对全部用例不可见；
  * 覆盖门禁只比「HTTP 方法 + 路径」注册表；
  * openapi 与客户端 TS 不被任何测试读取/执行。

真源：
  D = DDL 列（V1__baseline.sql 的 aap_audit_log 建表块）+ 对 aap_audit_log 的 UPDATE/DELETE 语句
  E = ER 文档 §327 字段行 / C8 约束行
  S = docs/backend/json-schema/models/audit-log.schema.json（属性集合 + action enum）
  I = 实现（AuditLogEntity 字段 + BaseEntity 列 + AuditLogViews.Row 分量 + AuditAction 枚举
      + AuditService 写入路径 setter + AuditLogQueryService select 列 + auditService.record 调用点）
  M = md 清单里标注「审计」的端点行
  C = aap-client 对 /admin/audit-logs 的消费（信息项）

用法: python aap-r50-audit-log.py [--root DIR] [--out FILE]
只读：不写任何被测文件（自测里对夹具做 (size,md5) 前后比对）。
"""
import argparse
import hashlib
import json
import os
import re
import sys

DEFAULT_ROOT = r"E:/workspaces/hioas/hioas-aap-001"

AUTO_COLS = {"created_at", "updated_at", "created_by", "updated_by", "deleted", "version"}
# md 标注「审计」的端点 → 期望的审计动作（语义映射，见 01-ER §327 / 清单「审计」列）
EXPECT_ACTION = {
    "CRED-07": "CREDENTIAL_REVEAL",
    "ADM-C02": "CREDENTIAL_REVEAL",
    "DET-06": "DETECTION_RELEASE",
}

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MAPPING = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")
CLASS_REQ = re.compile(r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]*)\"")
FIELD = re.compile(r"(?:private|protected|public)\s+(?:final\s+)?([A-Z][A-Za-z0-9_<>,.\s]*?)\s+([a-z][A-Za-z0-9_]*)\s*(?:=[^;]*)?;")
RECORD_CALL = re.compile(r"auditService\s*\.\s*record\s*\(\s*(?:AuditService\s*\.\s*)?AuditAction\s*\.\s*([A-Z_][A-Z0-9_]*)")
RECORD_CALL_ANY = re.compile(r"auditService\s*\.\s*record\s*\(")
SETTER = re.compile(r"entity\s*\.\s*set([A-Z][A-Za-z0-9_]*)\s*\(")
ENUM_DECL = re.compile(r"public\s+enum\s+AuditAction\s*\{(.*?)\}", re.S)
COLUMN_ANN = re.compile(r"@Column\s*\(\s*(?:value\s*=\s*)?\"([a-z_][a-z0-9_]*)\"")
MD_ID = re.compile(r"^[A-Z]{2,5}(?:-[A-Z0-9]+)+$")
VERBS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


def camel_to_snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def strip_comments(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            out.append(text[i:j + 1])
            i = j + 1
        elif c == "'":
            j = text.find("'", i + 1)
            if j == -1:
                out.append(c)
                i += 1
            else:
                out.append(text[i:j + 1])
                i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i)
            j = n if j == -1 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_paren(text, open_idx):
    depth, i, n = 0, open_idx, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_body(text, start):
    """括号深度扫描找方法体 '{'（坑 55/63）。"""
    depth, i, n = 0, start, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "{" and depth == 0:
            return i
        elif ch == ";" and depth == 0:
            return -1
        i += 1
    return -1


def brace_body(code, body_open):
    depth, i, n = 0, body_open, len(code)
    while i < n:
        ch = code[i]
        if ch == '"':
            i += 1
            while i < n:
                if code[i] == "\\":
                    i += 2
                    continue
                if code[i] == '"':
                    break
                i += 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return code[body_open + 1:i]
        i += 1
    return None


def split_top(text):
    parts, depth, cur, i, n = [], 0, [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            cur.append(text[i:j + 1])
            i = j + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def norm_path(p):
    """跨源统一的 key()：折叠路径变量 + 剥 /api/v1 前缀（坑 57/89：两侧必须过同一个归一函数）。"""
    p = p or ""
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if p and not p.startswith("/"):
        p = "/" + p
    p = re.sub(r"^/api/v\d+", "", p)
    return p.rstrip("/") or "/"


def parse_java(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    code = strip_comments(raw)
    cm = re.search(r"\bclass\s+([A-Za-z0-9_]+)", code)
    cls = cm.group(1) if cm else os.path.basename(path)[:-5]
    prefix = ""
    class_pos = cm.start() if cm else len(code)
    for m in CLASS_REQ.finditer(code):
        if m.start() < class_pos:
            prefix = m.group(1)
    methods = []
    for m in MAPPING.finditer(code):
        verb = m.group(1).upper()
        after = m.end()
        seg = code[after:after + 400]
        if seg.lstrip().startswith("("):
            oi = after + len(seg) - len(seg.lstrip())
            ci = match_paren(code, oi)
            if ci == -1:
                continue
            sm = re.search(r"\"([^\"]*)\"", code[oi + 1:ci])
            path_arg = sm.group(1) if sm else ""
            sig_start = ci + 1
        else:
            path_arg = ""
            sig_start = after
        body_open = find_body(code, sig_start)
        if body_open == -1:
            continue
        body = brace_body(code, body_open)
        if body is None:
            continue
        sig = code[sig_start:body_open]
        nm = re.search(r"([A-Za-z0-9_]+)\s*\(", sig)
        methods.append({"file": path, "cls": cls, "verb": verb,
                        "path": norm_path(prefix + (path_arg or "")),
                        "name": nm.group(1) if nm else "?",
                        "body": body})
    return {"file": path, "cls": cls, "prefix": prefix, "code": code, "methods": methods}


def load_java_tree(src_root):
    by_class = {}
    for dirpath, _d, files in os.walk(src_root):
        for fn in files:
            if not fn.endswith(".java"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                info = parse_java(p)
            except Exception as e:  # noqa
                print("WARN 解析失败 %s: %s" % (p, e))
                continue
            by_class[info["cls"]] = info
    return by_class


def plain_method(cls_info, name):
    code = cls_info["code"]
    for m in re.finditer(r"\b%s\s*\(" % re.escape(name), code):
        oi = code.find("(", m.start())
        ci = match_paren(code, oi)
        if ci == -1:
            continue
        bo = find_body(code, ci + 1)
        if bo == -1:
            continue
        body = brace_body(code, bo)
        if body is None:
            continue
        return body
    return None


def find_method(cls_info, name):
    for m in cls_info["methods"]:
        if m["name"] == name:
            return m
    body = plain_method(cls_info, name)
    if body is not None:
        return {"cls": cls_info["cls"], "name": name, "body": body, "path": None, "verb": None}
    return None


# ----------------------------------------------------------------- 各源解析
def parse_ddl(root):
    path = os.path.join(root, "aap-server/src/main/resources/db/migration/V1__baseline.sql")
    if not os.path.isfile(path):
        cands = []
        base = os.path.join(root, "aap-server/src/main/resources/db/migration")
        if os.path.isdir(base):
            cands = [os.path.join(base, f) for f in sorted(os.listdir(base)) if f.endswith(".sql")]
        path = None
        for c in cands:
            txt = open(c, encoding="utf-8", errors="replace").read()
            if re.search(r"create\s+table\s+(if\s+not\s+exists\s+)?aap_audit_log\b", txt, re.I):
                path = c
                break
    if path is None or not os.path.isfile(path):
        return {"path": path, "cols": []}
    txt = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"create\s+table\s+(?:if\s+not\s+exists\s+)?aap_audit_log\s*\((.*?)\)\s*;", txt, re.I | re.S)
    cols = []
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            cm = re.match(r"([a-z_][a-z0-9_]*)\s+[a-z]", line, re.I)
            if cm and cm.group(1).lower() not in ("primary", "unique", "constraint", "foreign", "check"):
                cols.append(cm.group(1).lower())
    return {"path": path, "cols": sorted(set(cols))}


def parse_write_statements(root):
    """对 aap_audit_log 的 UPDATE/DELETE 语句（DDL/实现/映射文件）。"""
    hits = []
    base = os.path.join(root, "aap-server/src/main")
    for dirpath, _d, files in os.walk(base):
        for fn in files:
            if not fn.endswith((".java", ".sql", ".xml")):
                continue
            p = os.path.join(dirpath, fn)
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                low = line.lower()
                if "aap_audit_log" not in low:
                    continue
                if re.search(r"\b(update|delete)\b", low):
                    hits.append("%s:%d" % (os.path.relpath(p, root).replace("\\", "/"), i))
    return hits


def parse_schema(root):
    path = os.path.join(root, "docs/backend/json-schema/models/audit-log.schema.json")
    if not os.path.isfile(path):
        return {"path": path, "props": [], "enum": []}
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception:  # noqa
        return {"path": path, "props": [], "enum": []}
    props = sorted(doc.get("properties", {}).keys())
    enum = list(doc.get("properties", {}).get("action", {}).get("enum", []))
    return {"path": path, "props": props, "enum": enum}


def parse_entity(root, tree):
    ent = tree.get("AuditLogEntity")
    fields = []
    cols = []
    if ent:
        body = ent["code"][ent["code"].find("class AuditLogEntity"):]
        for t, n in FIELD.findall(body):
            if t.strip() in ("static", "final"):
                continue
            fields.append(n)
        cols = [camel_to_snake(f) for f in fields]
    base = tree.get("BaseEntity")
    base_cols = sorted(set(COLUMN_ANN.findall(base["code"]))) if base else []
    return {"fields": fields, "cols": cols, "base_cols": base_cols}


def parse_views(root, tree):
    path = os.path.join(root, "aap-server/src/main/java/com/hioas/aap/support/AuditLogViews.java")
    if not os.path.isfile(path):
        return {"path": path, "names": []}
    code = strip_comments(open(path, encoding="utf-8", errors="replace").read())
    m = re.search(r"record\s+Row\s*\(", code)
    names = []
    if m:
        oi = code.find("(", m.start())
        ci = match_paren(code, oi)
        for part in split_top(code[oi + 1:ci]):
            jp = re.search(r"@JsonProperty\s*\(\s*\"([^\"]+)\"", part)
            if jp:
                names.append(jp.group(1))
                continue
            toks = IDENT.findall(part)
            if toks:
                names.append(toks[-1])
    return {"path": path, "names": sorted(names)}


def parse_enum_and_writers(root, tree):
    path = os.path.join(root, "aap-server/src/main/java/com/hioas/aap/support/AuditService.java")
    code = strip_comments(open(path, encoding="utf-8", errors="replace").read()) if os.path.isfile(path) else ""
    enum = []
    m = ENUM_DECL.search(code)
    if m:
        for tok in re.findall(r"[A-Z_][A-Z0-9_]{2,}", m.group(1)):
            enum.append(tok)
    writers = sorted(set(camel_to_snake(s) for s in SETTER.findall(code)))
    results = sorted(set(re.findall(r"entity\s*\.\s*setResult\s*\(\s*\"([^\"]*)\"", code)))
    return {"path": path, "enum": enum, "writers": writers, "result_literals": results}


def parse_record_calls(root):
    """全部 auditService.record(...) 调用点（含无法静态判定 action 的）。"""
    calls, unresolved = [], []
    base = os.path.join(root, "aap-server/src/main/java")
    for dirpath, _d, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".java") or fn == "AuditService.java":
                continue
            p = os.path.join(dirpath, fn)
            code = strip_comments(open(p, encoding="utf-8", errors="replace").read())
            rel = os.path.relpath(p, root).replace("\\", "/")
            for m in RECORD_CALL.finditer(code):
                calls.append({"file": rel, "action": m.group(1),
                              "line": code[:m.start()].count("\n") + 1})
            for m in RECORD_CALL_ANY.finditer(code):
                seg = code[m.end():m.end() + 200]
                if not re.match(r"\s*(?:AuditService\s*\.\s*)?AuditAction\s*\.", seg):
                    unresolved.append("%s:%d" % (rel, code[:m.start()].count("\n") + 1))
    return calls, unresolved


SQL_KEYWORDS = {"select", "distinct", "as", "count", "from", "where", "and", "or", "text", "cast",
                "null", "not", "order", "by", "limit", "offset", "desc", "asc", "coalesce"}


def parse_query_select(root, tree):
    """查询里投影到的列（按顶层逗号切分 select 列表，取每项的列名；坑 82/107：判据过宽会假报）。"""
    path = os.path.join(root, "aap-server/src/main/java/com/hioas/aap/support/AuditLogQueryService.java")
    if not os.path.isfile(path):
        return []
    code = strip_comments(open(path, encoding="utf-8", errors="replace").read())
    cols = []
    for m in re.finditer(r"select\s+(.*?)\s+from\s+aap_audit_log", code, re.S | re.I):
        seg = m.group(1)
        if re.match(r"\s*(count|sum|max|min)\s*\(", seg, re.I):
            continue                      # 计数查询：无投影列
        for item in split_top(seg):
            toks = [t for t in re.findall(r"[a-z_][a-z0-9_]*", item) if t not in SQL_KEYWORDS]
            if toks:
                cols.append(toks[-1])
    return sorted(set(cols))


def parse_md_audit_endpoints(root):
    """md 清单里带「审计」标注的端点行（未转义竖线切分，坑 48/89）。"""
    path = os.path.join(root, "docs/backend/02-API接口模型清单.md")
    rows = []
    if not os.path.isfile(path):
        return rows
    for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)[1:-1]]
        if len(cells) < 4:
            continue
        eid = cells[0].strip("` ")
        verb = cells[1].strip("` ").upper()
        if not MD_ID.match(eid) or verb not in VERBS:
            continue
        if any("审计" in c for c in cells):
            rows.append({"id": eid, "verb": verb, "path": cells[2].strip("` "), "line": i})
    return rows


def parse_client(root):
    base = os.path.join(root, "aap-client/src")
    hits, ua = [], []
    if not os.path.isdir(base):
        return hits, ua
    for dirpath, _d, files in os.walk(base):
        for fn in files:
            if not fn.endswith((".ts", ".vue", ".js")):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace("\\", "/")
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                if "audit-logs" in line:
                    hits.append("%s:%d" % (rel, i))
                if "user_agent" in line:
                    ua.append("%s:%d" % (rel, i))
    return hits, ua


# ----------------------------------------------------------------- 断言
class Report:
    def __init__(self):
        self.lines = []
        self.n_pass = 0
        self.n_fail = 0

    def ok(self, tag, text):
        self.n_pass += 1
        self.lines.append("  [PASS] %s %s" % (tag, text))

    def fail(self, tag, text):
        self.n_fail += 1
        self.lines.append("  [FAIL ] %s %s" % (tag, text))

    def info(self, tag, text):
        self.lines.append("  [INFO] %s %s" % (tag, text))


def audit(root, out_path=None):
    tree = load_java_tree(os.path.join(root, "aap-server/src/main/java"))
    ddl = parse_ddl(root)
    writes = parse_write_statements(root)
    schema = parse_schema(root)
    ent = parse_entity(root, tree)
    views = parse_views(root, tree)
    svc = parse_enum_and_writers(root, tree)
    calls, unresolved = parse_record_calls(root)
    qcols = parse_query_select(root, tree)
    md_rows = parse_md_audit_endpoints(root)
    client_hits, client_ua = parse_client(root)

    r = Report()
    r.lines.append("== R50 抽查：审计留痕一致性与完整性 —— 第二十四类可审计不变量 ==")
    r.lines.append("真源：D=DDL 列 ⇔ S=契约 schema 属性 ⇔ I=实体/视图/查询/枚举/写入 setter ⇔ M=md「审计」标注端点")
    r.lines.append("仓库根：%s" % root)
    r.lines.append("")

    r.lines.append("== 解析计数 ==")
    r.lines.append("   D DDL 列=%d  DDL 写语句(update/delete)=%d  S schema 属性=%d  S enum=%d"
                   % (len(ddl["cols"]), len(writes), len(schema["props"]), len(schema["enum"])))
    r.lines.append("   I 实体字段=%d  BaseEntity 列=%d  视图 Row 分量=%d  写入 setter=%d  查询 select 列=%d"
                   % (len(ent["fields"]), len(ent["base_cols"]), len(views["names"]),
                      len(svc["writers"]), len(qcols)))
    r.lines.append("   I record 调用点=%d（未能静态判定 action=%d）  M md「审计」端点=%d"
                   % (len(calls), len(unresolved), len(md_rows)))
    r.lines.append("")

    # ---- A0 正向对照（任一为 0 即解析器失效，坑 46/75）
    if ddl["cols"]:
        r.ok("A0a", "D 解析到 DDL 列 > 0 | %d" % len(ddl["cols"]))
    else:
        r.fail("A0a", "D 解析到 DDL 列 > 0 | 0（解析器失效，不得据此判一致）")
    if schema["props"] and schema["enum"]:
        r.ok("A0b", "S 解析到 schema 属性与 enum > 0 | %d / %d" % (len(schema["props"]), len(schema["enum"])))
    else:
        r.fail("A0b", "S 解析到 schema 属性与 enum > 0 | %d / %d（解析器失效）"
               % (len(schema["props"]), len(schema["enum"])))
    if ent["fields"] and views["names"] and svc["enum"] and svc["writers"]:
        r.ok("A0c", "I 解析到实体字段/视图分量/枚举/写入 setter 均 > 0 | %d/%d/%d/%d"
             % (len(ent["fields"]), len(views["names"]), len(svc["enum"]), len(svc["writers"])))
    else:
        r.fail("A0c", "I 解析到实体字段/视图分量/枚举/写入 setter 均 > 0 | %d/%d/%d/%d（解析器失效）"
               % (len(ent["fields"]), len(views["names"]), len(svc["enum"]), len(svc["writers"])))
    if calls:
        r.ok("A0d", "I 解析到 record 调用点 > 0 | %d" % len(calls))
    else:
        r.fail("A0d", "I 解析到 record 调用点 > 0 | 0（解析器失效）")
    if md_rows:
        r.ok("A0e", "M 解析到 md「审计」标注端点 > 0 | %d" % len(md_rows))
    else:
        r.fail("A0e", "M 解析到 md「审计」标注端点 > 0 | 0（解析器失效）")
    r.lines.append("")

    # ---- A1 契约 schema ⇔ 响应视图（1:1 投影）
    s_set, v_set = set(schema["props"]), set(views["names"])
    if s_set and v_set and s_set == v_set:
        r.ok("A1", "契约 schema 属性集合 = 响应视图分量集合 | %d/%d" % (len(s_set), len(v_set)))
    elif not s_set or not v_set:
        r.fail("A1", "契约 schema 属性集合 = 响应视图分量集合 | 有一侧解析到 0（空转假绿，坑 75/98）schema=%d 视图=%d"
               % (len(s_set), len(v_set)))
    else:
        r.fail("A1", "契约 schema 属性集合 = 响应视图分量集合 | 仅 schema=%s 仅视图=%s"
               % (sorted(s_set - v_set), sorted(v_set - s_set)))

    # ---- A2 实体字段 ∪ BaseEntity 列 ⇔ DDL 列
    e_set = set(ent["cols"]) | set(ent["base_cols"])
    d_set = set(ddl["cols"])
    if e_set and d_set and e_set == d_set:
        r.ok("A2", "实体字段 ∪ BaseEntity 列 = DDL 列 | %d/%d" % (len(e_set), len(d_set)))
    elif not e_set or not d_set:
        r.fail("A2", "实体字段 ∪ BaseEntity 列 = DDL 列 | 有一侧解析到 0（空转假绿）实体=%d DDL=%d"
               % (len(e_set), len(d_set)))
    else:
        r.fail("A2", "实体字段 ∪ BaseEntity 列 = DDL 列 | 仅实体=%s 仅 DDL=%s"
               % (sorted(e_set - d_set), sorted(d_set - e_set)))

    # ---- A3 实现枚举 ⇔ 契约 enum
    if svc["enum"] and schema["enum"] and set(svc["enum"]) == set(schema["enum"]):
        r.ok("A3", "AuditAction 枚举 = 契约 action enum | %d/%d" % (len(svc["enum"]), len(schema["enum"])))
    elif not svc["enum"] or not schema["enum"]:
        r.fail("A3", "AuditAction 枚举 = 契约 action enum | 有一侧解析到 0（空转假绿）实现=%d 契约=%d"
               % (len(svc["enum"]), len(schema["enum"])))
    else:
        r.fail("A3", "AuditAction 枚举 = 契约 action enum | 仅实现=%s 仅契约=%s"
               % (sorted(set(svc["enum"]) - set(schema["enum"])),
                  sorted(set(schema["enum"]) - set(svc["enum"]))))

    # ---- A4 append-only（C8）
    if not writes:
        r.ok("A4", "append-only：全仓库对 aap_audit_log 无 UPDATE/DELETE 语句 | 0 处")
    else:
        r.fail("A4", "append-only：对 aap_audit_log 出现 UPDATE/DELETE | %d 处：%s" % (len(writes), writes))
    mapper_ok = not re.search(r"auditLogMapper\s*\.\s*(update|delete)",
                              "\n".join(open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
                                        for dirpath, _d, files in os.walk(os.path.join(root, "aap-server/src/main/java"))
                                        for fn in files if fn.endswith(".java")))
    if mapper_ok:
        r.ok("A4b", "auditLogMapper 仅 insert（无 update/delete 调用）")
    else:
        r.fail("A4b", "auditLogMapper 出现 update/delete 调用（违反 C8 append-only）")

    # ---- A5 查询列 ⇔ DDL 列（查询不得引用不存在的列）
    if qcols:
        bad = sorted(set(qcols) - d_set)
        if not bad:
            r.ok("A5", "查询 select 列全部存在于 DDL | %d 列" % len(qcols))
        else:
            r.fail("A5", "查询 select 列全部存在于 DDL | 越界列=%s" % bad)
    else:
        r.fail("A5", "查询 select 列全部存在于 DDL | 解析到 0 列（解析器失效）")

    # ---- A6 枚举常量被真实使用（无孤儿 action）
    used = set(c["action"] for c in calls)
    orphan = sorted(set(svc["enum"]) - used)
    if not orphan:
        r.ok("A6", "契约目录的 action 全部有实现调用点 | %d/%d" % (len(used), len(svc["enum"])))
    else:
        r.fail("A6", "契约目录的 action 全部有实现调用点 | 孤儿 action %d 个：%s"
               % (len(orphan), orphan))
    if unresolved:
        r.info("A6b", "未能静态判定 action 的 record 调用点 %d 处（信息项，非漂移）：%s"
               % (len(unresolved), unresolved[:5]))

    # ---- A7 写入路径填充的列 ⇔ DDL 非自动列
    expect_written = d_set - AUTO_COLS - {"id"}
    w_set = set(svc["writers"])
    missing = sorted(expect_written - w_set)
    if not missing:
        r.ok("A7", "写入路径覆盖全部非自动列 | %d/%d" % (len(w_set & expect_written), len(expect_written)))
    else:
        r.fail("A7", "写入路径覆盖全部非自动列 | 声明但写入路径从不填充的列 %d 个：%s"
               % (len(missing), missing))
    extra = sorted(w_set - d_set)
    if extra:
        r.fail("A7b", "写入路径不得填充 DDL 之外的列 | %s" % extra)
    else:
        r.ok("A7b", "写入路径填充的列都在 DDL 内 | %d 个" % len(w_set))
    r.info("A7c", "写入路径 result 字面量取值域（信息项）| %s" % (svc["result_literals"] or "未解析到"))

    # ---- A8 md「审计」标注端点 → 实现调用链真的有审计写入，且 action 语义匹配
    located = 0
    for row in md_rows:
        ctrl_m = None
        for info in tree.values():
            for m in info["methods"]:
                if m["verb"] == row["verb"] and m["path"] == norm_path(row["path"]):
                    ctrl_m = (info, m)
                    break
            if ctrl_m:
                break
        if not ctrl_m:
            r.info("A8", "%s 未能定位控制器方法（信息项，非漂移）| %s %s"
                   % (row["id"], row["verb"], row["path"]))
            continue
        located += 1
        info, m = ctrl_m
        found = None
        for cm2 in re.finditer(r"([a-z][A-Za-z0-9_]*)\s*\.\s*([a-zA-Z][A-Za-z0-9_]*)\s*\(", m["body"]):
            recv, meth = cm2.group(1), cm2.group(2)
            tgt = tree.get(recv[:1].upper() + recv[1:])
            if tgt is None:
                continue
            callee = find_method(tgt, meth)
            if callee is None:
                continue
            rc = RECORD_CALL.search(callee["body"] or "")
            if rc:
                found = (tgt["cls"], meth, rc.group(1))
                break
        exp = EXPECT_ACTION.get(row["id"])
        if found is None:
            r.fail("A8", "%s 链路未发现审计写入 | %s.%s" % (row["id"], info["cls"], m["name"]))
        elif exp is None:
            r.info("A8", "%s 链路审计 action=%s（无期望映射，信息项）" % (row["id"], found[2]))
        elif found[2] == exp:
            r.ok("A8", "%s 链路审计 action 语义匹配 | %s.%s → %s"
                 % (row["id"], found[0], found[1], found[2]))
        else:
            r.fail("A8", "%s 链路审计 action 语义不匹配 | 期望 %s，实现 %s（%s.%s）"
                   % (row["id"], exp, found[2], found[0], found[1]))
    if md_rows:
        if located == len(md_rows) and located > 0:
            r.ok("A8c", "md「审计」端点定位率 | 已定位 %d / %d" % (located, len(md_rows)))
        else:
            r.fail("A8c", "md「审计」端点定位率（必须全部定位，否则 A8 是空转）| 已定位 %d / %d"
                   % (located, len(md_rows)))

    # ---- INFO 客户端与 ER 侧
    r.info("A9", "客户端 /admin/audit-logs 消费点（信息项）| %d 处 %s" % (len(client_hits), client_hits[:3]))
    r.info("A9b", "客户端 user_agent 字段消费点（信息项）| %d 处" % len(client_ua))
    er = os.path.join(root, "docs/backend/01-ER数据模型.md")
    if os.path.isfile(er):
        txt = open(er, encoding="utf-8", errors="replace").read()
        c8 = "C8" in txt and "审计不可变" in txt
        r.info("A9c", "ER 文档 C8「审计不可变」约束行存在（信息项）| %s" % ("是" if c8 else "否"))

    r.lines.append("")
    r.lines.append("== 断言汇总 ==")
    r.lines.append("  断言 %d 条：PASS %d，FAIL %d" % (r.n_pass + r.n_fail, r.n_pass, r.n_fail))

    text = "\n".join(r.lines) + "\n"
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return r.n_fail, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    n_fail, text = audit(a.root, a.out)
    sys.stdout.write(text)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
