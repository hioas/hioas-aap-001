#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R70 抽查：**ORM 实体 ↔ DDL 映射一致性**（第四十四类可审计不变量）。

为什么两套门禁都看不见：
  契约测试把**真实响应体**与 JSON Schema 比对 —— 实体字段映射到哪一列、列存不存在、
  列类型与 Java 类型是否相容、jsonb 列有没有 typeHandler、审计监听器要写的列在表里有没有，
  **全都不在任何 schema 里**；覆盖门禁只比「方法 + 路径」是否注册；openapi 与客户端 TS 不被任何测试读取/执行。
  → 实体字段映射到不存在的列（改名/漏加显式 @Column）时，**该实体的任何 ORM 查询都会抛
    `column ... does not exist`** → HTTP 层只看到 500 `E-2001`（坑 13/24/63 的实体侧），
    而 204 例全绿也看不见（用例未必走到那条查询）；反向（DDL 列未映射）与
    「jsonb 列无 typeHandler」「审计监听器要写的列表里没有」同理。

真源：
  D = DDL（`db/migration/*.sql`：表名 / 列名 + 类型词 / 内联与表级主键 / not null / default / 分区）
  O = ORM 实体（`@Table(value=...)` + 字段名 + 紧邻注解块里的 `@Column("x")` 与 `typeHandler`；含 `extends` 基类字段）
  S = 代码里的手写 SQL 写路径（`insert into <表>` / `update <表>`，用于区分「ORM 独占写入」）
  Q = 序列引用（`nextval('seq_x')` ∪ `nextVal("seq_x")` ∪ 常量引用回查）
  E = ER 文档（`docs/backend/01-ER数据模型.md` 里的 `aap_*` 表名）

判据：
  A0a..A0h 解析器正向对照（表数 / 实体数 / 映射字段数 / 序列数 / 定位率 / jsonb 与 typeHandler 计数 /
           手写写路径计数 / ER 表名计数 —— 均须 > 0，否则下游断言空转假绿，坑 46/75/87/98）
  A1  每个实体字段（含基类）映射到的列必须存在于该表（**判定不可用即 FAIL**，坑 141）
  A1b 每个 `@Table` 表名必须存在于 DDL
  A1c 每张有实体的表必须有主键（内联 `primary key` 与表级 `primary key (...)` 都认，坑 91 族）
  A1d 同一实体不得有两个字段映射到同一列
  A2  Java 类型 ↔ DDL 列类型族一致（Long↔bigint / Integer↔int|integer|smallint / Boolean↔boolean /
      String↔varchar|char|text / BigDecimal↔numeric|decimal / OffsetDateTime↔timestamptz）
  A3  jsonb 列 ⇔ `typeHandler` 双向（String 无 typeHandler 写 jsonb 列 / typeHandler 字段映射非 jsonb 列）
  A4  挂审计监听器（onInsert/onUpdate）的实体，其表必须有对应审计列
  A5  约定名（camel→snake）≠ 列名 的字段**必须**有显式 `@Column`（否则 ORM 直接映射到不存在的列）
  A5b 依赖显式 `@Column` 的字段条数 ≤ 上限（防止用注解掩盖命名漂移）
  A6  未映射的「NOT NULL 且无 default」列，且该表**无手写 SQL 写路径**（ORM 独占写入）→ 该列永远无法写入
  A7  代码引用的序列必须已在 DDL 声明；A7b 声明未引用的孤儿序列 ≤ 上限
  A8  DDL 表名 ↔ ER 文档表名一致（分区子表属豁免类，须有依据且 ≤ 上限）

用法：python spotcheck-entity-ddl-R70.py [--root E:/workspaces/hioas/hioas-aap-001]
                                          [--src <main 源码目录>] [--ddl <migration 目录>] [--er <ER 文档>]
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path("E:/workspaces/hioas/hioas-aap-001")

TYPE_WORDS = ("bigint", "int", "integer", "smallint", "boolean", "bool", "varchar", "char",
              "text", "jsonb", "json", "numeric", "decimal", "timestamptz", "timestamp",
              "date", "time", "uuid", "bytea", "double", "real", "serial", "bigserial", "interval")
CONSTRAINT_WORDS = ("primary", "unique", "constraint", "foreign", "check", "key", "exclude")

# Java 类型 → 允许的 DDL 类型词集合
TYPE_FAMILY = {
    "Long": {"bigint"},
    "Integer": {"int", "integer", "smallint"},
    "Short": {"smallint"},
    "Boolean": {"boolean", "bool"},
    "String": {"varchar", "char", "text"},
    "BigDecimal": {"numeric", "decimal"},
    "OffsetDateTime": {"timestamptz"},
    "LocalDate": {"date"},
    "UUID": {"uuid"},
}
AUDIT_LISTENER_COLS = {"onInsert": ["created_at", "created_by"], "onUpdate": ["updated_at", "updated_by"]}

CAP_EXPLICIT_COLUMN = 3     # A5b：依赖显式 @Column 的字段上限
CAP_ORPHAN_SEQ = 3          # A7b：声明未引用的序列上限
CAP_PARTITION_TABLES = 2    # A8b：ER 文档差异里的分区子表上限
CAP_HANDWRITTEN_NOTNULL = 8  # A6b：有手写 SQL 写路径的未映射 NOT NULL 列上限
SQL_KEYWORDS = {"select", "from", "where", "join", "left", "right", "inner", "outer", "on", "cast",
                "lateral", "values", "set", "as", "and", "or", "not", "null", "case", "when",
                "then", "else", "end", "union", "all", "distinct", "limit", "offset", "order",
                "group", "by", "having", "with", "returning", "into", "update", "insert", "delete",
                "table", "exists", "using", "natural", "cross", "full", "the", "a", "jsonb_each"}

FIELD_RE = re.compile(r"^\s{4}(?:private|protected)\s+([\w<>.]+)\s+(\w+)\s*(?:=[^;]*)?;")
COLUMN_VALUE_RE = re.compile(r'@Column\(\s*(?:value\s*=\s*)?"([^"]+)"')


def strip_java_comments(src: str) -> str:
    """剥注释，**保留**字符串/文本块字面量（坑 58/140：注释里的引用不是调用点）。"""
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('"""', i):
            j = src.find('"""', i + 3)
            j = n if j < 0 else j + 3
            out.append(src[i:j])
            i = j
            continue
        c = src[i]
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:min(j + 1, n)])
            i = min(j + 1, n)
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def parse_ddl(ddl_dir: Path):
    """D → tables{tbl:{cols{col:type},pk,notnull,default,partition}} · seqs · partitions"""
    tables, seqs, partitions = {}, set(), set()
    for f in sorted(ddl_dir.glob("*.sql")):
        raw = f.read_text(encoding="utf-8", errors="replace")
        txt = re.sub(r"--[^\n]*", "", raw)
        cur = None
        for line in txt.splitlines():
            s = line.strip()
            m = re.match(r"create table if not exists\s+(\w+)\s*\(", s, re.I)
            if m:
                cur = m.group(1).lower()
                tables.setdefault(cur, {"cols": {}, "pk": set(), "notnull": set(),
                                        "default": set(), "partition": False, "file": f.name})
                continue
            if cur is None:
                continue
            if s.startswith(")"):
                tail = s
                if re.search(r"partition\s+by", tail, re.I):
                    tables[cur]["partition"] = True
                    partitions.add(cur)
                cur = None
                continue
            if not s:
                continue
            s2 = s.rstrip(",")
            cm = re.match(r"^([a-z_][a-z0-9_]*)\s+(.+)$", s2, re.I)
            if not cm:
                continue
            col, rest = cm.group(1).lower(), cm.group(2).strip()
            w = re.match(r"^([a-z_]+)", rest, re.I)
            first = w.group(1).lower() if w else ""
            if first in CONSTRAINT_WORDS:
                if first == "primary":
                    pk = re.search(r"primary key\s*\(([^)]*)\)", rest, re.I)
                    if pk:
                        for c in pk.group(1).split(","):
                            tables[cur]["pk"].add(c.strip().lower())
                continue
            if first not in TYPE_WORDS:
                continue
            tables[cur]["cols"][col] = first
            if re.search(r"\bnot null\b", rest, re.I):
                tables[cur]["notnull"].add(col)
            if re.search(r"\bdefault\b", rest, re.I):
                tables[cur]["default"].add(col)
            if re.search(r"\bprimary key\b", rest, re.I):   # 内联主键（坑 91 族：漏收会造 34 条假 FAIL）
                tables[cur]["pk"].add(col)
        for m in re.finditer(r"alter table\s+(\w+)\s+add column(?: if not exists)?\s+(\w+)\s+([a-z]+)",
                             txt, re.I):
            t = m.group(1).lower()
            tables.setdefault(t, {"cols": {}, "pk": set(), "notnull": set(),
                                  "default": set(), "partition": False, "file": f.name})
            tables[t]["cols"][m.group(2).lower()] = m.group(3).lower()
        for m in re.finditer(r"create table if not exists\s+(\w+)\s+partition of\s+(\w+)", txt, re.I):
            t = m.group(1).lower()
            tables.setdefault(t, {"cols": {}, "pk": set(), "notnull": set(),
                                  "default": set(), "partition": True, "file": f.name})
            tables[t]["partition"] = True
            partitions.add(t)
        for m in re.finditer(r"create sequence if not exists\s+(\w+)", txt, re.I):
            seqs.add(m.group(1).lower())
        for m in re.finditer(r"create table if not exists\s+(\w+_default)\b", txt, re.I):
            partitions.add(m.group(1).lower())
    return tables, seqs, partitions


def parse_fields(lines, start=0):
    """字段 → (name, java_type, explicit_col, has_typehandler)；注解取「紧邻注解块」（坑 107/116）。"""
    fields = []
    for i in range(start, len(lines)):
        m = FIELD_RE.match(lines[i])
        if not m:
            continue
        anns, j = [], i - 1
        while j >= 0:
            t = lines[j].strip()
            if t.startswith("@"):
                anns.append(t)
                j -= 1
                continue
            if t == "" or t.startswith("//") or t.startswith("/*") or t.startswith("*"):
                j -= 1
                continue
            break
        anns.reverse()
        col, th = None, False
        for a in anns:
            mm = COLUMN_VALUE_RE.search(a)
            if mm:
                col = mm.group(1)
            if "typeHandler" in a:
                th = True
        fields.append((m.group(2), m.group(1), col, th))
    return fields


def parse_entities(src_dir: Path):
    """O → [{'file','table','fields','raw','base'}]，含 extends 基类字段（深度 1）。"""
    cache = {}
    for p in src_dir.rglob("*.java"):
        try:
            cache[p] = strip_java_comments(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    ents = []
    for p, txt in sorted(cache.items(), key=lambda kv: str(kv[0])):
        tm = re.search(r'@Table\(\s*value\s*=\s*"(\w+)"', txt)
        if not tm:
            continue
        own = parse_fields(txt.splitlines())
        base_name = None
        bm = re.search(r"class\s+\w+[^{]*?\bextends\s+(\w+)", txt)
        if bm:
            base_name = bm.group(1)
        base_fields = []
        if base_name:
            for q, qt in cache.items():
                if q.name == base_name + ".java":
                    base_fields = parse_fields(qt.splitlines())
                    break
        ents.append({"file": p, "table": tm.group(1).lower(), "fields": own,
                     "base_fields": base_fields, "base": base_name, "raw": txt})
    return ents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--src", default=None)
    ap.add_argument("--ddl", default=None)
    ap.add_argument("--er", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    src_dir = Path(a.src) if a.src else root / "aap-server/src/main/java"
    ddl_dir = Path(a.ddl) if a.ddl else root / "aap-server/src/main/resources/db/migration"
    er_path = Path(a.er) if a.er else root / "docs/backend/01-ER数据模型.md"

    lines, fails = [], []

    def emit(tag, ok, msg):
        lines.append("[%s] %s %s" % ("PASS" if ok else "FAIL", tag, msg))
        if not ok:
            fails.append(tag)

    def info(tag, msg):
        lines.append("[INFO] %s %s" % (tag, msg))

    if not ddl_dir.exists():
        info("A0a", "DDL 目录不存在：%s" % ddl_dir)
        tables, seqs, partitions = {}, set(), set()
    else:
        tables, seqs, partitions = parse_ddl(ddl_dir)
    ents = parse_entities(src_dir) if src_dir.exists() else []

    n_cols = sum(len(t["cols"]) for t in tables.values())
    n_fields = sum(len(e["fields"]) + len(e["base_fields"]) for e in ents)
    info("", "解析计数：DDL 表 %d · DDL 列 %d · 序列 %d · 分区表 %d · 实体 %d · 实体字段 %d"
         % (len(tables), n_cols, len(seqs), len(partitions), len(ents), n_fields))

    emit("A0a", len(tables) > 0, "解析到 DDL 表 %d（须 > 0）" % len(tables))
    emit("A0b", len(ents) > 0, "解析到 ORM 实体 %d（须 > 0）" % len(ents))
    emit("A0c", n_fields > 0, "解析到实体字段 %d（须 > 0，否则 A1/A2 空转）" % n_fields)
    emit("A0d", len(seqs) > 0, "解析到 DDL 序列 %d（须 > 0，否则 A7 空转）" % len(seqs))

    # ---- 定位率（坑 87：先看「解析到几条」再看「是否全绿」）
    located = [e for e in ents if e["table"] in tables]
    emit("A0e", len(located) > 0 and len(located) == len(ents),
         "实体表定位率 %d / %d（未定位：%s）"
         % (len(located), len(ents), ", ".join(e["table"] for e in ents if e["table"] not in tables) or "无"))

    # ---- A1 字段 → 列存在性
    n_eval = 0
    if not ents:
        emit("A1", False, "判定不可用：未解析到任何实体（空输入不得判「全部通过」，坑 98/141）")
    else:
        for e in ents:
            if e["table"] not in tables:
                continue
            cols = tables[e["table"]]["cols"]
            for name, typ, explicit, th in e["fields"] + e["base_fields"]:
                col = explicit or snake(name)
                n_eval += 1
                if col not in cols:
                    emit("A1", False, "%s 表=%s 字段=%s → 列 %s 在 DDL 不存在（显式 @Column=%s）"
                         % (e["file"].name, e["table"], name, col, explicit))
        if n_eval == 0:
            emit("A1", False, "判定不可用：已定位实体上未解析到任何字段（坑 98）")
    emit("A0f", n_eval > 0, "已判定 A1 的字段映射 %d 条（须 > 0，定位率不足时不得判「全部通过」，坑 87）" % n_eval)

    # ---- A1b 表名存在性
    for e in ents:
        if e["table"] not in tables:
            emit("A1b", False, "%s 的 @Table 表名 %s 在 DDL 不存在" % (e["file"].name, e["table"]))

    # ---- A1c 主键
    n_pk_eval = 0
    for e in ents:
        if e["table"] not in tables:
            continue
        n_pk_eval += 1
        if not tables[e["table"]]["pk"]:
            emit("A1c", False, "%s 表=%s 无 primary key（内联与表级均未解析到）" % (e["file"].name, e["table"]))
    if n_pk_eval == 0:
        emit("A1c", False, "判定不可用：无可判定的实体表（坑 98）")

    # ---- A1d 同列重复映射
    n_dup_eval = 0
    for e in ents:
        seen = {}
        for name, typ, explicit, th in e["fields"] + e["base_fields"]:
            seen.setdefault(explicit or snake(name), []).append(name)
            n_dup_eval += 1
        for col, names in seen.items():
            if len(names) > 1:
                emit("A1d", False, "%s 表=%s 列 %s 被多个字段映射：%s" % (e["file"].name, e["table"], col, names))
    if n_dup_eval == 0:
        emit("A1d", False, "判定不可用：无字段可判定（坑 98）")

    # ---- A2 类型族
    n_t2 = 0
    for e in ents:
        if e["table"] not in tables:
            continue
        cols = tables[e["table"]]["cols"]
        for name, typ, explicit, th in e["fields"] + e["base_fields"]:
            col = explicit or snake(name)
            ctype = cols.get(col)
            java_base = typ.split("<")[0]
            if ctype is None or ctype == "jsonb" or java_base not in TYPE_FAMILY:
                continue        # jsonb 列由 A3 判（A2 = 标量类型族，坑 81 判据范围）
            if th:      # 有 typeHandler 的字段由 A3 判（String+JsonbTypeHandler ↔ jsonb）
                continue
            n_t2 += 1
            if ctype not in TYPE_FAMILY[java_base]:
                emit("A2", False, "%s 表=%s 列 %s：Java=%s 与 DDL=%s 类型族不符（允许 %s）"
                     % (e["file"].name, e["table"], col, java_base, ctype,
                        "/".join(sorted(TYPE_FAMILY[java_base]))))
    emit("A0g", n_t2 > 0, "已判定 A2 的类型对 %d 条（须 > 0）" % n_t2)
    if n_t2 == 0:
        emit("A2", False, "判定不可用：无可比对的类型对（坑 98/141）")

    # ---- A3 jsonb ⇔ typeHandler（A0h 统计**全 DDL 表**的 jsonb 列与**全实体**的 typeHandler 字段，
    #      使正向对照不依赖「表是否被定位」，避免表名错时连带打红，坑 82 夹具侧）
    n_jsonb_cols, n_th_fields = 0, 0
    n_jsonb_cols = sum(1 for t in tables.values() for c, ty in t["cols"].items() if ty == "jsonb")
    n_th_fields = sum(1 for e in ents for _, _, _, th in e["fields"] if th)
    for e in ents:
        if e["table"] not in tables:
            continue
        cols = tables[e["table"]]["cols"]
        for name, typ, explicit, th in e["fields"]:
            col = explicit or snake(name)
            ctype = cols.get(col)
            if th:
                if ctype and ctype != "jsonb":
                    emit("A3", False, "%s 表=%s 列 %s 有 typeHandler 但 DDL 类型=%s（须 jsonb）"
                         % (e["file"].name, e["table"], col, ctype))
            if ctype == "jsonb" and not th:
                emit("A3", False, "%s 表=%s 列 %s 是 jsonb 但字段 %s 无 typeHandler（写入必失败）"
                     % (e["file"].name, e["table"], col, name))
    emit("A0h", n_jsonb_cols > 0 and n_th_fields > 0,
         "解析到 jsonb 列 %d · 带 typeHandler 字段 %d（两者均须 > 0，否则 A3 空转）"
         % (n_jsonb_cols, n_th_fields))

    # ---- A4 审计监听器 ↔ 审计列
    n_lis = 0
    for e in ents:
        if e["table"] not in tables:
            continue
        need = []
        for k, cols_ in AUDIT_LISTENER_COLS.items():
            if re.search(k + r"\s*=", e["raw"]):
                need += cols_
        if not need:
            continue
        n_lis += 1
        missing = [c for c in need if c not in tables[e["table"]]["cols"]]
        if missing:
            emit("A4", False, "%s 表=%s 挂审计监听器但缺列 %s" % (e["file"].name, e["table"], missing))
    if n_lis == 0:
        emit("A4", False, "判定不可用：无挂审计监听器的实体（坑 98）")
    else:
        info("A4", "挂审计监听器的实体 %d 个，审计列齐备性已判定" % n_lis)

    # ---- A5 约定名 ≠ 列名 必须有显式 @Column（n_explicit 统计**全实体**，不依赖表是否被定位）
    n_explicit = sum(1 for e in ents for n, _, ex, _ in e["fields"]
                     if ex and ex != snake(n))
    for e in ents:
        if e["table"] not in tables:
            continue
        cols = tables[e["table"]]["cols"]
        for name, typ, explicit, th in e["fields"]:
            conv = snake(name)
            if explicit and explicit != conv:
                info("A5", "%s 表=%s 字段=%s 约定名=%s 显式 @Column=%s（依赖注解，列存在=%s）"
                     % (e["file"].name, e["table"], name, conv, explicit, explicit in cols))
            elif not explicit and conv not in cols:
                emit("A5", False, "%s 表=%s 字段=%s 约定名 %s 不在 DDL 且无显式 @Column（ORM 会映射到不存在的列）"
                     % (e["file"].name, e["table"], name, conv))
    if not ents or n_explicit == 0:
        emit("A5", False, "判定不可用：无实体或未解析到「约定名 ≠ 列名」的显式 @Column 字段（坑 98/141）")
    else:
        emit("A5b", n_explicit <= CAP_EXPLICIT_COLUMN,
             "依赖显式 @Column 的字段 %d 条（上限 %d —— 超限说明命名漂移被注解掩盖）"
             % (n_explicit, CAP_EXPLICIT_COLUMN))

    # ---- A6 未映射的 NOT NULL 无 default 列
    sql_text, n_write = "", 0
    for p in src_dir.rglob("*.java"):
        sql_text += strip_java_comments(p.read_text(encoding="utf-8", errors="replace"))
    n_write = len(re.findall(r"\binsert\s+into\s+\w+|\bupdate\s+\w+\s+set", sql_text, re.I))
    emit("A0i", n_write > 0, "解析到手写 SQL 写路径 %d 处（须 > 0，否则 A6 的「ORM 独占写入」判定空转）"
         % n_write)
    n_a6, n_a6_ex = 0, 0
    for e in ents:
        if e["table"] not in tables:
            continue
        mapped = {explicit or snake(n) for n, _, explicit, _ in e["fields"] + e["base_fields"]}
        ti = tables[e["table"]]
        risky = sorted(c for c in ti["notnull"] if c not in ti["default"] and c not in mapped)
        if not risky:
            continue
        hand = bool(re.search(r"insert\s+into\s+" + e["table"] + r"\b", sql_text, re.I)) or \
            bool(re.search(r"update\s+" + e["table"] + r"\b", sql_text, re.I))
        if hand:
            n_a6_ex += len(risky)
            info("A6", "%s 表=%s 未映射 NOT NULL 列 %s —— 该表有手写 SQL 写路径 → 豁免（须逐条核对）"
                 % (e["file"].name, e["table"], risky))
        else:
            n_a6 += 1
            emit("A6", False, "%s 表=%s 未映射「NOT NULL 且无 default」列 %s，且全仓库无该表的手写 SQL 写路径"
                              " → ORM 独占写入时该列永远无法赋值（insert 必失败）"
                 % (e["file"].name, e["table"], risky))
    if not ents:
        emit("A6", False, "判定不可用：无实体（坑 98）")
    emit("A6b", n_a6_ex <= CAP_HANDWRITTEN_NOTNULL,
         "手写 SQL 写路径豁免的未映射 NOT NULL 列 %d 条（上限 %d）" % (n_a6_ex, CAP_HANDWRITTEN_NOTNULL))

    # ---- A7 序列引用 ↔ 声明
    used = set()
    used |= {m.group(1).lower() for m in re.finditer(r"nextval\(\s*'(\w+)'", sql_text)}
    used |= {m.group(1).lower() for m in re.finditer(r'nextVal\(\s*"(\w+)"', sql_text)}
    consts = {m.group(1): m.group(2).lower()
              for m in re.finditer(r'static\s+final\s+String\s+(\w+)\s*=\s*"(\w+)"', sql_text)}
    for m in re.finditer(r"nextval?\(\s*(\w+)\s*\)", sql_text, re.I):
        if m.group(1) in consts:
            used.add(consts[m.group(1)])
    info("A7", "代码引用序列 %d 个（nextval 字面量 ∪ nextVal(\"...\") ∪ 常量回查）" % len(used))
    if not used:
        emit("A7", False, "判定不可用：未解析到任何序列引用（坑 98）")
    for s in sorted(used - seqs):
        emit("A7", False, "代码引用序列 %s 但 DDL 未声明（运行时 relation does not exist）" % s)
    orphan = sorted(seqs - used)
    emit("A7b", len(orphan) <= CAP_ORPHAN_SEQ,
         "声明未引用的孤儿序列 %d 条（上限 %d）：%s" % (len(orphan), CAP_ORPHAN_SEQ, orphan or "无"))

    # ---- A8 DDL 表 ↔ ER 文档
    er_tables = set()
    if er_path.exists():
        er_tables = {m.group(1).lower()
                     for m in re.finditer(r"`(aap_[a-z0-9_]+)`", er_path.read_text(encoding="utf-8",
                                                                                  errors="replace"))}
    emit("A0j", len(er_tables) > 0, "解析到 ER 文档表名 %d（须 > 0，否则 A8 空转）" % len(er_tables))
    only_ddl = sorted(set(tables) - er_tables)
    exempt = [t for t in only_ddl if t in partitions or t.endswith("_default")]
    hard = [t for t in only_ddl if t not in exempt]
    for t in hard:
        emit("A8", False, "DDL 有表 %s 但 ER 文档未声明（且非分区子表）" % t)
    emit("A8b", len(exempt) <= CAP_PARTITION_TABLES,
         "ER 文档差异中的分区子表 %d 条（上限 %d）：%s" % (len(exempt), CAP_PARTITION_TABLES, exempt or "无"))
    for t in sorted(er_tables - set(tables)):
        emit("A8", False, "ER 文档声明表 %s 但 DDL 未建（漏建表）" % t)

    # ---- A9 手写 SQL 表名必须都在 DDL 里存在
    refs = {}
    for pat in (r"insert\s+into\s+([a-z_]\w*)", r"update\s+([a-z_]\w*)\s+set",
                r"\bfrom\s+([a-z_]\w*)", r"\bjoin\s+([a-z_]\w*)",
                r"delete\s+from\s+([a-z_]\w*)"):
        for mm in re.finditer(pat, sql_text, re.I):
            refs.setdefault(mm.group(1).lower(), set()).add(pat[:6])
    emit("A0k", len(refs) > 0, "解析到手写 SQL 引用的表名 %d 个（须 > 0，否则 A9 空转）" % len(refs))
    unknown_tbl = sorted(k for k in refs if k not in tables and k not in SQL_KEYWORDS)
    for t in unknown_tbl:
        emit("A9", False, "手写 SQL 引用表 %s 但 DDL 未建（运行时 relation does not exist）" % t)
    info("A9", "手写 SQL 引用的表名 %d 个，未命中 DDL 的 %d 个（已排除 SQL 关键字）"
         % (len(refs), len(unknown_tbl)))

    lines.append("")
    lines.append("== 汇总：FAIL %d 条 %s ==" % (len(fails), sorted(set(fails))))
    print("\n".join(lines))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
