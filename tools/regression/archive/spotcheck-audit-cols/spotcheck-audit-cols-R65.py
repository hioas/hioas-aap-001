#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R65 抽查（只读）：写路径「审计留痕列」填充一致性（第三十九类可审计不变量）。

为什么两套门禁都看不见：
  · 契约测试只把**响应体**与 JSON Schema 比对 —— created_by/updated_by 是否落库**不在 schema 里**
    （审计列通常不出现在响应模型，或为 nullable）→ 写路径漏填、库里恒为 NULL，204 例全绿也看不见。
  · 覆盖门禁只比「方法 + 路径」；openapi 与客户端 TS 不被任何测试读取/执行。
真源：D DDL（表 → 是否含 created_by/updated_by）／O ORM 路径（实体 @Table 的 onInsert/onUpdate 挂载）／
     I 手写 SQL 路径（insert 列清单、update set 清单、on conflict do update set 分支）／
     A AuditContext 链路入口（set/clear 点与 SYSTEM actor 语义）／M md 声明（01-ER「审计字段（业务表通用）」）／
     T 测试背书（结构级 vs 取值级）／X 出口（响应模型是否暴露审计列）。
用法：python spotcheck-audit-cols-R65.py --root <repo>
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
    """把注释字符替换为空格（保留长度与换行），使偏移量与原文件一一对应。"""
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
    """返回 [(start, end, kind, text)]；code 必须是已剥注释的文本（偏移量保持一致）。"""
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
    """s[i] == op 时返回配对 cl 的下标；否则 -1。字符串内的括号成对，天然不误判。"""
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


def split_top(s, sep=","):
    parts, depth, i, start, n = [], 0, 0, 0, len(s)
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
        elif ch == sep and depth == 0:
            parts.append(s[start:i])
            start = i + 1
        i += 1
    parts.append(s[start:])
    return [p.strip() for p in parts]


def find_top(s, kw, start=0):
    """在顶层（括号深度 0、跳过单引号字符串）找关键字，返回下标或 -1。"""
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
    """按顶层 `;` 切分（跳过单引号字符串），返回 [(offset, stmt)]。"""
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


# --------------------------------------------------------------------------- 解析器
DDL_CREATE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)", re.I)


def parse_ddl(paths):
    """→ {table: {'created_by': bool, 'updated_by': bool, 'file': str, 'line': int}}"""
    tables = {}
    for p in sorted(paths):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        for m in DDL_CREATE.finditer(code):
            name = m.group(1).lower()
            op = code.find("(", m.end())
            if op < 0:
                continue
            cl = match_paren(code, op)
            if cl < 0:
                continue
            body = code[op + 1:cl]
            cols = set()
            for line in body.splitlines():
                line = line.strip().rstrip(",")
                if not line:
                    continue
                first = line.split()[0].lower().strip('"')
                cols.add(first)
            line_no = raw[:m.start()].count("\n") + 1
            # 分区子表 `create table if not exists X partition of Y` 单独出现 → 覆盖父表信息
            tables[name] = {
                "created_by": "created_by" in cols,
                "updated_by": "updated_by" in cols,
                "file": str(p),
                "line": line_no,
            }
    # 分区子表（partition of）不覆盖父表列信息
    for p in sorted(paths):
        raw = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)\s+partition\s+of\s+([a-z_][a-z0-9_]*)", raw, re.I):
            child, parent = m.group(1).lower(), m.group(2).lower()
            if parent in tables:
                tables[child] = dict(tables[parent])
                tables[child]["partition_of"] = parent
    return tables


TABLE_ANN = re.compile(r"@Table\s*\(")


def parse_entities(src_dir):
    """→ {table: {'on_insert': bool, 'on_update': bool, 'file': str}}"""
    out = {}
    if not src_dir.is_dir():
        return out
    for p in sorted(src_dir.rglob("*.java")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        for m in TABLE_ANN.finditer(code):
            op = code.find("(", m.end() - 1)
            cl = match_paren(code, op)
            if cl < 0:
                continue
            ann = code[op + 1:cl]
            vm = re.search(r'value\s*=\s*"([^"]+)"', ann)
            if not vm:
                vm = re.match(r'\s*"([^"]+)"', ann)
            if not vm:
                continue
            tbl = vm.group(1).lower()
            out[tbl] = {
                "on_insert": "onInsert" in ann,
                "on_update": "onUpdate" in ann,
                "file": str(p),
            }
    return out


STMT_START = re.compile(r"(?:insert\s+into|(?<!do\s)update)\s+([a-z_][a-z0-9_]*)", re.I)
KW_TABLES = {"set", "where", "values", "select", "from", "aap"}


def parse_sql_writes(src_dir):
    """→ list of dict(kind, table, cols, set_cols, upsert_set, file, line)"""
    writes = []
    if not src_dir.is_dir():
        return writes
    for p in sorted(src_dir.rglob("*.java")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        for (ls, le, kind, text) in java_literals(code):
            if not re.search(r"insert\s+into|update\s+[a-z_]", text, re.I):
                continue
            for (off, stmt) in split_sql_statements(text):
                m = STMT_START.search(stmt)
                if not m:
                    continue
                verb = m.group(0).split()[0].lower()
                tbl = m.group(1).lower()
                if tbl in KW_TABLES:
                    continue
                line_no = raw[:ls].count("\n") + text[:off + m.start()].count("\n") + 1
                rec = {
                    "kind": "insert" if verb.startswith("insert") else "update",
                    "table": tbl,
                    "cols": [],
                    "set_cols": [],
                    "upsert_set": [],
                    "file": str(p),
                    "line": line_no,
                }
                if rec["kind"] == "insert":
                    op = stmt.find("(", m.end())
                    if op >= 0:
                        cl = match_paren(stmt, op)
                        if cl > 0:
                            rec["cols"] = [c.split()[0].lower().strip('"') if c.split() else ""
                                           for c in split_top(stmt[op + 1:cl])]
                else:
                    si = find_top(stmt, "set", m.end())
                    if si >= 0:
                        wi = find_top(stmt, "where", si + 3)
                        seg = stmt[si + 3:wi] if wi > 0 else stmt[si + 3:]
                        rec["set_cols"] = [a.split("=")[0].strip().split(".")[-1].lower()
                                           for a in split_top(seg) if "=" in a]
                # on conflict ... do update set ...
                ci = find_top(stmt, "do update")
                if ci >= 0:
                    si = find_top(stmt, "set", ci + len("do update"))
                    if si >= 0:
                        wi = find_top(stmt, "where", si + 3)
                        seg = stmt[si + 3:wi] if wi > 0 else stmt[si + 3:]
                        rec["upsert_set"] = [a.split("=")[0].strip().split(".")[-1].lower()
                                             for a in split_top(seg) if "=" in a]
                writes.append(rec)
    return writes


def parse_audit_context(src_dir):
    sets, clears = [], []
    if not src_dir.is_dir():
        return sets, clears
    for p in sorted(src_dir.rglob("*.java")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        for m in re.finditer(r"AuditContext\.set\s*\(", code):
            line_no = raw[:m.start()].count("\n") + 1
            tail = code[m.end():m.end() + 160]
            sets.append({"file": str(p), "line": line_no, "arg": tail.split(";")[0].strip()[:120]})
        for m in re.finditer(r"AuditContext\.clear\s*\(", code):
            clears.append({"file": str(p), "line": raw[:m.start()].count("\n") + 1})
    return sets, clears


def parse_listener_source(src_dir):
    """读 AuditListeners.java：Update 里 updated_by 赋值是否被 `actorId != null` 守卫。"""
    for p in sorted(src_dir.rglob("AuditListeners.java")):
        code = strip_comments(p.read_text(encoding="utf-8", errors="replace"))
        i = code.find("class Update")
        if i < 0:
            i = 0
        seg = code[i:]
        j = seg.find("setUpdatedBy")
        if j < 0:
            return {"file": str(p), "guarded": None}
        window = seg[max(0, j - 300):j]
        guarded = bool(re.search(r"if\s*\(\s*actorId\s*!=\s*null\s*\)", window))
        return {"file": str(p), "guarded": guarded}
    return None


def parse_append_only(md_path, tables):
    """从 md 抽取被声明为 append-only 的表名（只认 DDL 里真实存在的表名，避免把列名当表名）。"""
    out = set()
    if not md_path.is_file():
        return out
    for line in md_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "append-only" in line:
            for m in re.finditer(r"`([a-z_][a-z0-9_]*)`", line):
                if m.group(1) in tables:
                    out.add(m.group(1))
            for m in re.finditer(r"\*\*([a-z_][a-z0-9_]*)\*\*", line):
                if m.group(1) in tables:
                    out.add(m.group(1))
    return out


def parse_md(md_path):
    if not md_path.is_file():
        return []
    lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [{"line": i + 1, "text": t} for i, t in enumerate(lines) if "审计字段" in t]


def parse_tests(test_dir):
    struct_refs, value_refs = [], []
    if not test_dir.is_dir():
        return struct_refs, value_refs
    for p in sorted(test_dir.rglob("*.java")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        code = strip_comments(raw)
        for m in re.finditer(r'"(created_by|updated_by)"', code):
            struct_refs.append({"file": str(p), "line": raw[:m.start()].count("\n") + 1})
        for m in re.finditer(r"(getCreatedBy|getUpdatedBy|createdBy|updatedBy)\s*\(", code):
            value_refs.append({"file": str(p), "line": raw[:m.start()].count("\n") + 1})
    return struct_refs, value_refs


def parse_response_exports(src_dir):
    hits = []
    if not src_dir.is_dir():
        return hits
    for p in sorted(src_dir.rglob("*.java")):
        raw = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\b(createdBy|updatedBy|created_by|updated_by)\b", raw):
            hits.append({"file": str(p), "line": raw[:m.start()].count("\n") + 1})
    return hits


# --------------------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--tests-dir", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()

    ddl_dir = root / "aap-server/src/main/resources/db/migration"
    main_dir = root / "aap-server/src/main/java"
    test_dir = Path(args.tests_dir).resolve() if args.tests_dir else root / "aap-server/src/test/java"
    md_path = root / "docs/backend/01-ER数据模型.md"

    print("root = %s" % root)
    tables = parse_ddl(sorted(ddl_dir.glob("*.sql"))) if ddl_dir.is_dir() else {}
    entities = parse_entities(main_dir)
    writes = parse_sql_writes(main_dir)
    ac_sets, ac_clears = parse_audit_context(main_dir)
    listener = parse_listener_source(main_dir)
    md_lines = parse_md(md_path)
    struct_refs, value_refs = parse_tests(test_dir)
    exports = parse_response_exports(main_dir)

    audit_tables = {t: v for t, v in tables.items() if v.get("created_by") or v.get("updated_by")}
    inserts = [w for w in writes if w["kind"] == "insert"]
    updates = [w for w in writes if w["kind"] == "update"]
    ins_with_cb = [w for w in inserts if "created_by" in w["cols"]]
    print("解析计数：DDL 表 %d（含审计列 %d）· 实体 @Table %d（挂 onInsert %d）· 手写写语句 %d"
          "（insert %d / update %d）· insert 列清单含 created_by %d · AuditContext.set %d/clear %d ·"
          " md 审计字段行 %d · 测试结构引用 %d / 取值引用 %d · 响应/实现里审计列名 %d"
          % (len(tables), len(audit_tables), len(entities),
             sum(1 for v in entities.values() if v["on_insert"]), len(writes), len(inserts), len(updates),
             len(ins_with_cb), len(ac_sets), len(ac_clears), len(md_lines), len(struct_refs), len(value_refs),
             len(exports)))
    print()

    # ---- 正向对照
    emit("PASS" if audit_tables else "FAIL", "A0a", "DDL 解析到含审计列的表 %d 张" % len(audit_tables))
    emit("PASS" if entities and sum(1 for v in entities.values() if v["on_insert"]) else "FAIL", "A0b",
         "实体 @Table 解析到 %d 个，其中挂 onInsert 监听器 %d 个"
         % (len(entities), sum(1 for v in entities.values() if v["on_insert"])))
    emit("PASS" if writes else "FAIL", "A0c", "手写 SQL 写语句解析到 %d 条（insert %d / update %d）"
         % (len(writes), len(inserts), len(updates)))
    emit("PASS" if ins_with_cb else "FAIL", "A0d",
         "insert 列清单解析器正向对照：解析到列清单且含 created_by 的 insert %d 条" % len(ins_with_cb))
    emit("PASS" if ac_sets else "FAIL", "A0e", "AuditContext 链路入口解析到 set %d 处 / clear %d 处"
         % (len(ac_sets), len(ac_clears)))
    emit("PASS" if struct_refs else "FAIL", "A0f", "测试源里出现审计列名字面量 %d 处" % len(struct_refs))
    emit("PASS" if md_lines else "FAIL", "A0g", "md 声明「审计字段（业务表通用）」行 %d 条" % len(md_lines))

    # ---- A1：insert 必须填充 created_by 与 updated_by
    if not audit_tables or not inserts:
        emit("FAIL", "A1", "判定不可用：含审计列的表 %d / insert 路径 %d（解析失效，坑 98/141）"
             % (len(audit_tables), len(inserts)))
    else:
        bad = []
        for w in inserts:
            t = w["table"]
            if t not in audit_tables:
                continue
            ent = entities.get(t)
            miss = [c for c in ("created_by", "updated_by") if c not in w["cols"]]
            if not miss:
                continue
            bad.append("%s:%d insert into %s 缺 %s（%s）"
                       % (Path(w["file"]).name, w["line"], t, "+".join(miss),
                          "该表有 ORM 实体（手写路径绕过监听器）" if ent and ent["on_insert"] else "无 ORM 实体"))
        if bad:
            emit("FAIL", "A1", "手写 insert 未填充审计列 %d 条：%s" % (len(bad), " | ".join(bad[:6])))
        else:
            emit("PASS", "A1", "所有手写 insert（%d 条）都显式填充了 created_by/updated_by"
                 % len([w for w in inserts if w["table"] in audit_tables]))

    # ---- A1b：ORM 实体必须挂 onInsert（否则 ORM 插入不填审计列）
    if not entities:
        emit("FAIL", "A1b", "判定不可用：未解析到任何 @Table 实体")
    else:
        bad = ["%s（%s）" % (t, Path(v["file"]).name)
               for t, v in sorted(entities.items()) if t in audit_tables and not v["on_insert"]]
        if bad:
            emit("FAIL", "A1b", "ORM 实体未挂 onInsert 监听器 %d 个（ORM 插入不填 created_by/updated_by）：%s"
                 % (len(bad), " | ".join(bad[:6])))
        else:
            emit("PASS", "A1b", "全部 %d 个含审计列的 ORM 实体都挂了 onInsert 监听器"
                 % len([t for t in entities if t in audit_tables]))

    # ---- A2：update 必须刷新 updated_by（含 upsert 的 do update 分支）
    if not audit_tables or not updates:
        emit("FAIL", "A2", "判定不可用：含审计列的表 %d / update 路径 %d（解析失效）"
             % (len(audit_tables), len(updates)))
    else:
        bad = []
        for w in writes:
            t = w["table"]
            if t not in audit_tables:
                continue
            ent = entities.get(t)
            if w["kind"] == "update" and "updated_by" not in w["set_cols"]:
                bad.append("%s:%d update %s 的 set 缺 updated_by（%s）"
                           % (Path(w["file"]).name, w["line"], t,
                              "有 ORM 实体（手写路径绕过监听器）" if ent and ent["on_update"] else "无 ORM 实体"))
            if w["upsert_set"] and "updated_by" not in w["upsert_set"]:
                bad.append("%s:%d upsert %s 的 do-update 分支缺 updated_by（已刷 updated_at 却不刷 updated_by）"
                           % (Path(w["file"]).name, w["line"], t))
        if bad:
            emit("FAIL", "A2", "手写 update / upsert 分支未刷新 updated_by %d 处：%s"
                 % (len(bad), " | ".join(bad[:8])))
        else:
            emit("PASS", "A2", "所有手写 update（%d 条）与 upsert do-update 分支都刷新了 updated_by"
                 % len([w for w in updates if w["table"] in audit_tables]))

    # ---- A2b：ORM 实体必须挂 onUpdate（append-only 表按 md 声明豁免，坑 57/68）
    append_only = parse_append_only(md_path, tables)
    if not entities:
        emit("FAIL", "A2b", "判定不可用：未解析到任何 @Table 实体")
    else:
        bad = ["%s（%s）" % (t, Path(v["file"]).name)
               for t, v in sorted(entities.items())
               if t in audit_tables and not v["on_update"] and t not in append_only]
        if bad:
            emit("FAIL", "A2b", "ORM 实体未挂 onUpdate 监听器 %d 个（ORM 更新不刷新 updated_by）：%s"
                 % (len(bad), " | ".join(bad[:6])))
        else:
            emit("PASS", "A2b", "含审计列的 ORM 实体（%d 个，已豁免 append-only %d 个）全部挂了 onUpdate 监听器"
                 % (len([t for t in entities if t in audit_tables]), len(append_only)))
    if len(append_only) > 2:
        emit("FAIL", "A2c", "append-only 豁免表 %d 个，超出上限 2（豁免会把规则架空，坑 57/68）" % len(append_only))
    else:
        used = []
        for t in sorted(append_only):
            has_upd = any(w["kind"] == "update" and w["table"] == t for w in writes)
            ent = entities.get(t)
            used.append("%s（md 声明 append-only；实现 update 路径=%d；实体 onUpdate=%s）"
                        % (t, 1 if has_upd else 0, ent["on_update"] if ent else "无实体"))
        emit("INFO", "A2c", "append-only 豁免 %d 个（上限 2）：%s" % (len(append_only), " | ".join(used) or "无"))

    # ---- A3：AuditListeners.Update 的 updated_by 赋值不得被 actorId 守卫（否则 SYSTEM 更新保留旧操作者）
    if listener is None:
        emit("FAIL", "A3", "判定不可用：未找到 AuditListeners 源文件")
    elif listener["guarded"] is None:
        emit("FAIL", "A3", "判定不可用：AuditListeners 里未找到 setUpdatedBy（解析失效）")
    elif listener["guarded"]:
        emit("FAIL", "A3", "AuditListeners.Update 的 updated_by 赋值被 `actorId != null` 守卫："
                           "SYSTEM 触发的更新会**保留上一次操作者**（留痕误导，非 NULL）")
    else:
        emit("PASS", "A3", "AuditListeners.Update 无条件刷新 updated_by（无 actorId 守卫）")

    # ---- A4：测试背书分档
    if not struct_refs and not value_refs:
        emit("FAIL", "A4", "判定不可用：测试源里 0 处审计列引用（解析失效或零背书）")
    elif not value_refs:
        emit("FAIL", "A4", "审计列**取值级**背书 0 处（仅结构级 %d 处：断言「表里有这几列」）→ "
                           "写路径漏填审计列时全量用例仍全绿" % len(struct_refs))
    else:
        emit("PASS", "A4", "审计列取值级背书 %d 处（结构级 %d 处）" % (len(value_refs), len(struct_refs)))
        hand = [w for w in writes if w["table"] in audit_tables]
        if hand:
            emit("INFO", "A4b", "取值级背书的覆盖范围：全部来自 ORM 路径（PersistenceBaseTest 断言 "
                                "createdBy/updatedBy = 9001L）；手写 SQL 写路径 %d 条**零**取值级背书" % len(hand))

    # ---- A5：md 声明（业务表通用）⇔ DDL 逐表
    if not md_lines:
        emit("FAIL", "A5", "判定不可用：md 未声明「审计字段（业务表通用）」→ 无对照基准")
    else:
        lack = sorted(t for t, v in tables.items() if not (v.get("created_by") and v.get("updated_by")))
        if lack:
            emit("FAIL", "A5", "md 声明审计字段为业务表通用，但 DDL 里 %d 张表缺列：%s"
                 % (len(lack), ", ".join(lack[:8])))
        else:
            emit("PASS", "A5", "md 声明「业务表通用」⇔ DDL %d 张表全部含 created_by/updated_by" % len(tables))

    # ---- 信息项
    orphan_tables = sorted(t for t in audit_tables if t not in entities
                           and not any(w["table"] == t for w in writes))
    emit("INFO", "A6", "既无 ORM 实体也无手写写路径的含审计列表 %d 张（只读或经别处写入）：%s"
         % (len(orphan_tables), ", ".join(orphan_tables[:8]) or "无"))
    emit("INFO", "A7", "响应/实现里出现审计列名的位置 %d 处（出口是否暴露 created_by/updated_by 需人工看上下文）"
         % len(exports))
    # A9：同文件内「同表多种 update 写法」并存（坑 44：同一函数内两种写法是漂移高发地）
    by_file_tbl = {}
    for w in updates:
        if w["table"] in audit_tables:
            by_file_tbl.setdefault((Path(w["file"]).name, w["table"]), []).append(
                "updated_by" in w["set_cols"])
    mixed = ["%s@%s（有 updated_by %d 处 / 无 %d 处）"
             % (t, f, sum(1 for x in v if x), sum(1 for x in v if not x))
             for (f, t), v in sorted(by_file_tbl.items()) if any(v) and not all(v)]
    emit("INFO", "A9", "同文件内同表「带/不带 updated_by」两种写法并存 %d 处（坑 44 的漂移高发形态）：%s"
         % (len(mixed), " | ".join(mixed[:5]) or "无"))
    if listener:
        emit("INFO", "A8", "监听器源：%s；Update 守卫=%s"
             % (Path(listener["file"]).name, listener["guarded"]))

    print()
    print("== 汇总 ==")
    print("PASS %d / FAIL %d / INFO %d" % (len(PASS), len(FAIL), len(INFO)))
    print("FAIL token 集合 = %s" % sorted(set(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
