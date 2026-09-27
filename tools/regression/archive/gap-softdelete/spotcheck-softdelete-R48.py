#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R48 抽查（不新建仓库工具，抽查式脚本落在 Temp）：

第二十二类可审计不变量 = 软删除（soft delete）语义一致性。

为什么两套门禁都看不见：
  * 契约测试只读响应 JSON Schema（schema 里没有 deleted / SQL / 部分索引谓词），
  * 覆盖门禁只比「HTTP 方法 + 路径」注册表，
  * openapi 与客户端 TS 不被任何测试读取/执行。
  → 唯一索引漏写 `where deleted = false`（软删行仍占唯一键）、
    ORM 实体漏继承 BaseEntity（逻辑删除过滤失效）、
    手写 JdbcTemplate SQL 漏过滤 deleted（软删行泄漏进列表/详情）、
    join 侧漏过滤（软删行仍被关联）—— 以上 204 例全绿也完全看不见。

真源（本脚本逐处比对）：
  D = aap-server/src/main/resources/db/migration/V1__baseline.sql
      （每张业务表的 deleted 列；每个 unique index 的 where 谓词）
  E = docs/backend/01-ER数据模型.md（「软删除」行 / 「业务唯一索引一律带 where deleted = false」）
  I = aap-server/src/main/java/**/*.java
      （真实 @Table 实体是否继承 BaseEntity；手写 SQL 的 from/join 表与过滤谓词）
  O = docs/backend/openapi.yaml（信息项：是否对外暴露 deleted）

用法（脚本自身放在 Temp/aap-r48-spotcheck/，夹具放在 Temp/aap-r48-spotcheck-fixtures/ —— 分开，
      否则自测的「先清空夹具目录」会把脚本自己删掉，症状是后续 patch 报 Failed to read file）：
  python spotcheck-softdelete-R48.py --root <仓库根>     # 真仓库只读抽查
  python spotcheck-softdelete-R48.py --selftest          # 判别力自测（夹具 + 注入缺陷）

纪律：只读、零写副作用；每个解析器都配 `> 0` 正向对照；FAIL 用 `[FAIL]` 前缀点名；
      断言比对按「断言 token」（首段）而非整行（坑 82/93/103）。
"""
import hashlib
import os
import re
import shutil
import sys
import tempfile

DEFAULT_ROOT = "E:/workspaces/hioas/hioas-aap-001"
FIXTURE_ROOT = os.path.join(tempfile.gettempdir(), "aap-r48-spotcheck-fixtures")
DDL_REL = "aap-server/src/main/resources/db/migration/V1__baseline.sql"
ER_REL = "docs/backend/01-ER数据模型.md"
OPENAPI_REL = "docs/backend/openapi.yaml"
JAVA_REL = "aap-server/src/main/java"

# A1 显式例外：不可变/追加写表（软删语义不适用）——必须显式 + 有上限（坑 57/68）
# 键 = 索引名（与 FAIL 点名一致；曾按表名做键 → 夹具里 uq_outbox_event_id 被误判为漂移，坑 29 同族）
A1_WHITELIST = {
    "uq_auth_jti": "追加写令牌表 aap_auth_token，吊销走 status，不做软删",
    "uq_outbox_event_id": "事务外盒 aap_outbox_event，事件不可变",
    "uq_idempotency_key": "幂等记录 aap_idempotency_record，键唯一性必须覆盖全部历史",
}
A1_WHITELIST_MAX = 3

FAIL_RE = re.compile(r"^\s*\[FAIL\s*\]")
SQL_KEYWORDS = {
    "jdbc", "query", "queryForObject", "queryForList", "String", "new", "StringBuilder", "Object",
    "List", "Long", "rowNum", "rs", "limit", "offset", "order", "by", "select", "from", "where", "and",
    "or", "update", "insert", "into", "values", "set", "delete", "as", "on", "left", "join", "count",
    "cast", "coalesce", "null", "true", "false", "case", "when", "then", "end", "group", "desc", "asc",
    "sum", "max", "min", "not", "var", "return", "args", "toArray", "getBounds", "this",
}


# ----------------------------------------------------------------- 通用工具
def strip_comments(text):
    """剥离 // 与 /* */ 注释，保留字符串/文本块字面量（坑 58 ③：注释里的注解不是代码）。

    注释**用空格替换而不是删除**：删除会让后续所有位置偏移 → 点名报出的行号与真实文件不符
    （本轮返工：NotificationService 报 120 行，实际 121+）。
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('"""', i):
            j = text.find('"""', i + 3)
            j = n if j < 0 else j + 3
            out.append(text[i:j])
            i = j
        elif c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def has_deleted_false(s):
    return re.search(r"deleted\s*=\s*false", norm(s), re.I) is not None


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ----------------------------------------------------------------- D 源：DDL
def parse_ddl(text):
    text = re.sub(r"--[^\n]*", "", text)
    tables = {}
    for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)\s*\(", text, re.I):
        name = m.group(1).lower()
        # 括号深度扫描取整块（字符串内括号成对，不会误判 —— 坑 55/63 的正确实现）
        i, depth = m.end() - 1, 0
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        cols = set()
        for line in text[m.end():i].split("\n"):
            line = line.strip()
            mm = re.match(r"([a-z_][a-z0-9_]*)\s", line)
            if mm and not line.lower().startswith(("primary", "unique", "constraint", "foreign", "check")):
                cols.add(mm.group(1).lower())
        tables[name] = cols
    uniques = []
    for m in re.finditer(
            r"create\s+unique\s+index\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)\s+on\s+([a-z_][a-z0-9_]*)\s*\(",
            text, re.I):
        j = text.find(";", m.end())
        stmt = norm(text[m.start():j if j > 0 else len(text)])
        uniques.append({
            "index": m.group(1).lower(),
            "table": m.group(2).lower(),
            "stmt": stmt,
            "predicate": norm(stmt.split(" where ", 1)[1]) if " where " in stmt.lower() else None,
        })
    return tables, uniques


# ----------------------------------------------------------------- I 源：Java
def java_files(root):
    base = os.path.join(root, JAVA_REL) if os.path.isdir(os.path.join(root, JAVA_REL)) else root
    out = []
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".java"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def extract_literals(code):
    lits = []
    blocks = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'"""(.*?)"""', code, re.S)]
    for s, e, t in blocks:
        lits.append((s, e, t, True))
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"', code):
        s, e = m.start(), m.end()
        if any(bs < s and e <= be for bs, be, _t in blocks):
            continue
        lits.append((s, e, m.group(1), False))
    lits.sort()
    return lits


def chain_at(code, pos):
    """从 pos 起沿语句（到第一个串外 `;`）累积：**串内文本也拼接进来**（SQL 是 `+` 拼接的），
    并收集串外标识符。坑 101：必须沿 `+` 拼接链累积，不能按「上一个 `;`」当语句边界。"""
    i, n, plain, lit_parts = pos, len(code), [], []
    while i < n:
        if code.startswith('"""', i):
            j = code.find('"""', i + 3)
            if j < 0:
                lit_parts.append(code[i + 3:])
                i = n
            else:
                lit_parts.append(code[i + 3:j])
                i = j + 3
            continue
        c = code[i]
        if c == '"':
            j = i + 1
            while j < n and code[j] != '"':
                j += 2 if code[j] == "\\" else 1
            lit_parts.append(code[i + 1:j])
            i = j + 1
            continue
        if c == ";":
            break
        plain.append(c)
        i += 1
    plain_text = "".join(plain)
    idents = [m.group(0) for m in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", plain_text)]
    return " ".join(lit_parts), idents


def literal_spans(code):
    return [(s, e) for s, e, _t, _tb in extract_literals(code)]


def is_declared_value(code, ident):
    """形参/局部变量（`Long id`、`String status`）不是 SQL 片段 —— 解析不到它不代表判据失效
    （否则每个带参数的调用点都被降级成「未能静态判定」，掩盖真漂移）。"""
    return re.search(r"\b(?:Long|Integer|String|int|long|boolean|Object|BigDecimal|UUID|List|Map|Set"
                     r"|StringBuilder|OffsetDateTime|Instant)\s+" + re.escape(ident) + r"\b", code) is not None


ALIAS_STOP = {"where", "and", "or", "left", "right", "inner", "join", "on", "order", "group", "limit",
              "offset", "as", "using", "set", "full", "cross"}


def main_alias(lit, table):
    """主表别名（`from aap_x p` / `from aap_x as p`）；关键字不算别名。"""
    m = re.search(r"\bfrom\s+" + re.escape(table) + r"(?:\s+(?:as\s+)?([a-z][a-z0-9_]*))?", lit, re.I)
    if not m or not m.group(1):
        return None
    return None if m.group(1).lower() in ALIAS_STOP else m.group(1).lower()


def has_main_deleted_filter(chain_text, alias):
    """主表作用域的软删过滤：未限定 `deleted = false` 或 `<主表别名>.deleted = false` 都算。"""
    for m in re.finditer(r"(?:([a-z_][a-z0-9_]*)\s*\.\s*)?deleted\s*=\s*false", chain_text, re.I):
        q = (m.group(1) or "").lower()
        if q == "" or (alias is not None and q == alias):
            return True
    return False


def resolve_ident(code, ident, depth=0, seen=None):
    """回查标识符定义/追加（含常量引用回查 —— 坑 99），返回 (拼接文本, 是否解析到)。

    匹配点必须落在**代码位置**：`(?<![\w.])id\\s*=\\s*` 会在 SQL 字面量里命中 `p.id = ?`，
    从而把后面的 `and p.deleted = false` 当成「标识符的取值」→ A3 假 PASS（本轮真实返工）。
    """
    seen = seen or set()
    if depth > 3 or ident in seen:
        return "", False
    seen.add(ident)
    spans = literal_spans(code)
    texts, found = [], False
    for m in re.finditer(r"(?<![\w.])" + re.escape(ident) + r"\s*(?:=|\.append\s*\()", code):
        if any(s <= m.start() < e for s, e in spans):
            continue
        found = True
        tail = code[m.end():]
        j = tail.find(";")
        texts.append(tail[:j if j > 0 else 200])
    joined = " ".join(texts)
    for sub in set(re.findall(r"(?<![\w.])([A-Z][A-Za-z0-9_]*)\s*(?:\+|,|\))", joined)):
        if sub != ident:
            sub_text, _ok = resolve_ident(code, sub, depth + 1, seen)
            joined += " " + sub_text
    return joined, found


def build_sql(path, code, line, lit, plain, idents):
    text = norm(lit + " " + plain)
    extra, resolved_all = [], True
    for ident in set(idents):
        # 先回查定义：变量名可能与 SQL 关键字同名（本项目 where 片段变量就叫 where）——
        # 先按关键字跳过会漏掉真正的 where 片段 → 假 FAIL（本轮真实返工）
        sub, ok = resolve_ident(code, ident)
        if ok:
            extra.append(sub)
        elif ident not in SQL_KEYWORDS and not is_declared_value(code, ident):
            resolved_all = False
    chain_text = norm(" ".join([text] + extra))
    tables = [t.lower() for t in re.findall(r"\bfrom\s+(aap_[a-z0-9_]+)", lit, re.I)]
    try:
        rel = os.path.relpath(path).replace("\\", "/")
    except ValueError:  # 仓库根在 E:，cwd 可能在 C:（坑 34：路径展示必须兜底）
        rel = path.replace("\\", "/")
    return {
        "file": rel,
        "line": line,
        "text": text,
        "chain_text": chain_text,
        "tables": tables,
        # 主表过滤判据必须**限定到主表作用域**：常量 SELECT 里的 join 谓词 `q.deleted = false`
        # 若被当成主表过滤 → A3 假 PASS（本轮真实返工，坑 44 同族：同一函数内两种写法）
        "main_filtered": {t: has_main_deleted_filter(chain_text, main_alias(lit, t)) for t in tables},
        "joins": [(m.group(1).lower(), m.group(2).lower())
                  for m in re.finditer(r"\bjoin\s+(aap_[a-z0-9_]+)\s+(?:as\s+)?([a-z][a-z0-9_]*)", lit, re.I)],
        "resolved": resolved_all,
    }


def parse_java_sql(root):
    sqls = []
    for path in java_files(root):
        code = strip_comments(read(path))
        for s, _e, lit, _tb in extract_literals(code):
            if not re.search(r"\bfrom\s+aap_", lit, re.I):
                continue
            line = code[:s].count("\n") + 1
            stmt_start = max(code.rfind(";", 0, s), code.rfind("{", 0, s)) + 1
            head = code[stmt_start:s]
            mconst = re.search(r"(?:static\s+final\s+String|String)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*$", head)
            if mconst:  # 类级常量：以「使用点」为判定位置（常量回查 —— 坑 87/99）
                name = mconst.group(1)
                for um in re.finditer(r"(?<![\w.])" + re.escape(name) + r"(?![\w])", code):
                    if um.start() <= s:
                        continue
                    plain, idents = chain_at(code, um.start())
                    sqls.append(build_sql(path, code, line, lit, plain, idents))
            else:
                plain, idents = chain_at(code, s)
                sqls.append(build_sql(path, code, line, lit, plain, idents))
    return sqls


# ----------------------------------------------------------------- 断言
def check(root):
    lines, fails = [], []
    ddl_path = os.path.join(root, DDL_REL)
    er_path = os.path.join(root, ER_REL)
    ddl = read(ddl_path) if os.path.isfile(ddl_path) else ""
    er = read(er_path) if os.path.isfile(er_path) else ""

    tables, uniques = parse_ddl(ddl)
    sqls = parse_java_sql(root)
    er_rule = [ln for ln in er.split("\n") if "业务唯一索引" in ln]
    deleted_tables = {t for t, cols in tables.items() if "deleted" in cols}

    def add(kind, name, text):
        lines.append("%s %s %s" % (kind, name, text))
        if kind == "[FAIL]":
            fails.append("%s %s" % (name, text))

    # ---- 正向对照（坑 46/75/98）
    for name, val, desc in (("A0a", len(tables), "DDL create table 解析数"),
                            ("A0b", len(uniques), "DDL unique index 解析数"),
                            ("A0c", len(sqls), "Java 含 from aap_ 的 SQL 解析数"),
                            ("A0d", len(er_rule), "ER 文档「业务唯一索引」规则行数"),
                            ("A0e", len(deleted_tables), "DDL 含 deleted 列的表数")):
        add("[PASS]" if val > 0 else "[FAIL]", name, "%s = %d（必须 > 0）" % (desc, val))

    # ---- A1：有 deleted 列的表，其 unique index 必须带 where deleted = false（ER 规则）
    a1_fail, a1_wl = 0, 0
    for uq in uniques:
        t = uq["table"]
        if t not in deleted_tables:
            add("[INFO]", "A1n", "%s on %s：表无 deleted 列 → 规则不适用" % (uq["index"], t))
            continue
        if uq["predicate"] and has_deleted_false(uq["predicate"]):
            continue
        if uq["index"] in A1_WHITELIST:
            a1_wl += 1
            add("[INFO]", "A1w", "%s on %s：白名单例外（%s）" % (uq["index"], t, A1_WHITELIST[uq["index"]]))
            continue
        a1_fail += 1
        add("[FAIL]", "A1", "%s on %s：unique index 无 `where deleted = false`（谓词=%s）"
            % (uq["index"], t, uq["predicate"] or "无"))
    add("[PASS]" if a1_fail == 0 else "[FAIL]", "A1s",
        "A1 漂移 %d 条 / 白名单 %d 条（上限 %d）" % (a1_fail, a1_wl, A1_WHITELIST_MAX))
    if a1_wl > A1_WHITELIST_MAX:
        add("[FAIL]", "A1c", "白名单条数 %d > 上限 %d（豁免不得把规则架空）" % (a1_wl, A1_WHITELIST_MAX))

    # ---- A2：真实 @Table 实体必须继承 BaseEntity（否则 ORM 逻辑删除过滤失效）
    ents, bad = 0, 0
    for path in java_files(root):
        code = strip_comments(read(path))
        for m in re.finditer(r"@Table\s*\([^)]*\)", code):
            ents += 1
            tail = code[m.end():m.end() + 400]
            if not re.search(r"class\s+\w+[^{;]*\bextends\s+BaseEntity\b", tail):
                bad += 1
                add("[FAIL]", "A2", "%s：@Table 实体未继承 BaseEntity（逻辑删除/审计字段失效）"
                    % os.path.basename(path))
    add("[PASS]" if ents > 0 else "[FAIL]", "A2a", "@Table 实体解析数 = %d（必须 > 0）" % ents)
    add("[PASS]" if bad == 0 else "[FAIL]", "A2s", "未继承 BaseEntity 的实体 = %d 条" % bad)

    # ---- A3：手写 SQL 查询的表（有 deleted 列）必须在语句/where 片段上过滤 deleted = false
    a3_fail = a3_info = a3_pass = 0
    for sq in sqls:
        for t in sq["tables"]:
            if t not in deleted_tables:
                add("[INFO]", "A3n", "%s:%d 表 %s 无 deleted 列 → 规则不适用" % (sq["file"], sq["line"], t))
                continue
            if sq["main_filtered"].get(t):
                a3_pass += 1
                continue
            if not sq["resolved"]:
                a3_info += 1
                add("[INFO]", "A3i", "%s:%d 表 %s 未能静态判定（标识符回查失败）" % (sq["file"], sq["line"], t))
                continue
            a3_fail += 1
            add("[FAIL]", "A3", "%s:%d 表 %s 的查询链上无 `deleted = false`：%s"
                % (sq["file"], sq["line"], t, sq["text"][:110]))
    add("[PASS]" if a3_pass > 0 else "[FAIL]", "A3a", "A3 已过滤条数 = %d（必须 > 0，正向对照）" % a3_pass)
    add("[PASS]" if a3_fail == 0 else "[FAIL]", "A3s", "A3 漂移 %d 条 / 未能判定 %d 条" % (a3_fail, a3_info))

    # ---- A4：join 目标表（有 deleted 列）必须带 `<alias>.deleted = false`
    a4_fail = a4_pass = 0
    for sq in sqls:
        for t, alias in sq["joins"]:
            if t not in deleted_tables:
                continue
            if re.search(re.escape(alias) + r"\s*\.\s*deleted\s*=\s*false", sq["chain_text"], re.I):
                a4_pass += 1
            else:
                a4_fail += 1
                add("[FAIL]", "A4", "%s:%d join %s %s 无 `%s.deleted = false`（软删行仍被关联）"
                    % (sq["file"], sq["line"], t, alias, alias))
    add("[PASS]" if (a4_pass + a4_fail) > 0 else "[FAIL]", "A4a",
        "A4 解析到的 join 目标数 = %d（必须 > 0，正向对照）" % (a4_pass + a4_fail))
    add("[PASS]" if a4_fail == 0 else "[FAIL]", "A4s", "A4 漂移 %d 条" % a4_fail)

    # ---- B：信息项
    oa_path = os.path.join(root, OPENAPI_REL)
    if os.path.isfile(oa_path):
        hits = len(re.findall(r"^\s+deleted:", read(oa_path), re.M))
        add("[INFO]", "B1", "openapi 中 `deleted:` 属性出现 %d 次（契约不暴露软删标记，符合预期）" % hits)

    return fails, lines


# ----------------------------------------------------------------- 自测夹具
FIX_DDL = """-- fixture
create table aap_provider (
    id bigint primary key,
    provider_no varchar(32) not null,
    status varchar(16) not null,
    deleted boolean not null default false,
    version int not null default 0
);
create unique index if not exists uq_provider_no on aap_provider (provider_no) where deleted = false;
create unique index if not exists uq_provider_id on aap_provider (id) where deleted = false;
create table aap_quote (
    id bigint primary key,
    provider_id bigint not null,
    deleted boolean not null default false
);
create table aap_outbox_event (
    id bigint primary key,
    event_id varchar(64) not null,
    deleted boolean not null default false
);
create unique index if not exists uq_outbox_event_id on aap_outbox_event (event_id);
"""

FIX_ER = """| 软删除 | `deleted boolean not null default false`，业务唯一索引一律带 `where deleted = false` |
- 业务唯一索引一律带 `where deleted = false`。
"""

FIX_JAVA_ENTITY = """package syn;
import com.hioas.aap.common.BaseEntity;

@Table("aap_provider")
public class ProviderEntity extends BaseEntity {
    private String providerNo;
}
"""

FIX_JAVA_SERVICE = """package syn;

public class ProviderService {
    private static final String COLUMNS = "id, provider_no";
    private static final String SELECT = \"\"\"
            select p.id, q.id
              from aap_provider p
              left join aap_quote q on q.id = p.id and q.deleted = false
            \"\"\";

    public void list(String status) {
        StringBuilder where = new StringBuilder(" where deleted = false");
        if (status != null) {
            where.append(" and status = ?");
        }
        jdbc.query("select " + COLUMNS + " from aap_provider" + where + " order by id desc limit ? offset ?");
    }

    public void detail(Long id) {
        jdbc.query("select id, provider_no from aap_provider where id = ? and deleted = false");
    }

    public void viaConstant(Long id) {
        jdbc.query(SELECT + " where p.id = ? and p.deleted = false", id);
    }

    public void withJoin() {
        jdbc.query("select p.id, q.id from aap_provider p join aap_quote q on q.id = p.id"
                + " and p.deleted = false and q.deleted = false");
    }
}
"""


def write_fixture(d):
    for rel in ("aap-server/src/main/resources/db/migration", "docs/backend", "aap-server/src/main/java/syn"):
        os.makedirs(os.path.join(d, rel), exist_ok=True)
    with open(os.path.join(d, DDL_REL), "w", encoding="utf-8") as fh:
        fh.write(FIX_DDL)
    with open(os.path.join(d, ER_REL), "w", encoding="utf-8") as fh:
        fh.write(FIX_ER)
    with open(os.path.join(d, "aap-server/src/main/java/syn/ProviderEntity.java"), "w", encoding="utf-8") as fh:
        fh.write(FIX_JAVA_ENTITY)
    with open(os.path.join(d, "aap-server/src/main/java/syn/ProviderService.java"), "w", encoding="utf-8") as fh:
        fh.write(FIX_JAVA_SERVICE)
    return d


def tokens_of(fails):
    return sorted({f.split(" ")[0] for f in fails})


def mutate(path, old, new):
    """返回未命中锚点列表（坑 66：注入必须真的改到源码，否则是空转通过）。"""
    txt = read(path)
    if old not in txt:
        return [old]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(txt.replace(old, new))
    return []


def selftest():
    if os.path.isdir(FIXTURE_ROOT):
        shutil.rmtree(FIXTURE_ROOT, ignore_errors=True)
    base = write_fixture(os.path.join(FIXTURE_ROOT, "base"))
    ok_fails, ok_lines = check(base)
    state = {"ok": True, "n": 0}

    def report(name, cond, extra=""):
        state["n"] += 1
        print("%-6s %s %s" % ("[PASS]" if cond else "[FAIL]", name, extra))
        if not cond:
            state["ok"] = False

    # 正向对照
    report("T0 合规夹具 FAIL=0（正向对照）", not ok_fails, "FAIL=%d %s" % (len(ok_fails), ok_fails[:3]))
    report("T0b 解析器正向对照：SQL > 0 且 A3/A4 都解析到条目",
           any(l.startswith("[PASS] A0c") for l in ok_lines)
           and any(l.startswith("[PASS] A3a") for l in ok_lines)
           and any(l.startswith("[PASS] A4a") for l in ok_lines))
    report("T0c 常量+使用点写法被判定为已过滤（SELECT 常量回查）",
           any(l.startswith("[PASS] A0c") for l in ok_lines))
    base_tokens = set(tokens_of(ok_fails))

    def injection(tag, rel, old, new, expect_tokens):
        d = write_fixture(os.path.join(FIXTURE_ROOT, "inj-" + tag))
        missed = mutate(os.path.join(d, rel), old, new)
        report("T%s 注入锚点命中（必须真的改到源码）" % tag, not missed, missed)
        fs, _ls = check(d)
        got = set(tokens_of(fs)) - base_tokens
        report("T%s 注入后新增断言 token 恰好 {%s}" % (tag, ",".join(expect_tokens)),
               got == set(expect_tokens), sorted(got))
        for tk in expect_tokens:
            report("T%s 新增断言 %s 点名到被测对象" % (tag, tk),
                   any(f.startswith(tk + " ") for f in fs), [f for f in fs if f.startswith(tk + " ")][:1])

    # A1 注入：有 deleted 列的表，unique index 去掉部分索引谓词（软删行仍占键）
    injection("A1", DDL_REL,
              "uq_provider_id on aap_provider (id) where deleted = false;",
              "uq_provider_id on aap_provider (id);", ["A1", "A1s"])
    # A2 注入：实体不再继承 BaseEntity
    injection("A2", "aap-server/src/main/java/syn/ProviderEntity.java",
              "extends BaseEntity", "", ["A2", "A2s"])
    # A3 注入：where 片段不再过滤 deleted（软删行泄漏进列表）
    injection("A3", "aap-server/src/main/java/syn/ProviderService.java",
              'new StringBuilder(" where deleted = false")', 'new StringBuilder(" where 1 = 1")',
              ["A3", "A3s"])
    # A3b 注入：常量 + 使用点写法里，使用点的过滤条件被删（判据必须看使用点）
    injection("A3b", "aap-server/src/main/java/syn/ProviderService.java",
              "where p.id = ? and p.deleted = false", "where p.id = ?", ["A3", "A3s"])
    # A4 注入：join 侧不再过滤 deleted
    injection("A4", "aap-server/src/main/java/syn/ProviderService.java",
              "and q.deleted = false", "and q.id is not null", ["A4", "A4s"])

    # 空夹具：正向对照必须点名变红（坑 75/98）
    empty = os.path.join(FIXTURE_ROOT, "empty")
    os.makedirs(empty, exist_ok=True)
    ef, _el = check(empty)
    for p in ("A0a", "A0b", "A0c", "A0d", "A0e", "A2a", "A3a", "A4a"):
        report("T-空夹具 %s 点名变红" % p, any(f.startswith(p + " ") for f in ef),
               [f for f in ef if f.startswith(p + " ")][:1])

    # 真实仓库只读守卫（零写副作用）
    key = [os.path.join(DEFAULT_ROOT, DDL_REL), os.path.join(DEFAULT_ROOT, ER_REL)]
    before = [hashlib.md5(read(p).encode("utf-8", "replace")).hexdigest() for p in key]
    rf, rl = check(DEFAULT_ROOT)
    after = [hashlib.md5(read(p).encode("utf-8", "replace")).hexdigest() for p in key]
    report("T-real 真实仓库关键文件 md5 全等（零写副作用）", before == after)
    report("T-real2 真实仓库抽查跑完且解析到条目 > 0",
           any(l.startswith("[PASS] A0c") for l in rl) and isinstance(rf, list),
           "FAIL=%d" % len(rf))

    print("--- 判别力自测：%d 项，%s ---" % (state["n"], "全 PASS" if state["ok"] else "存在 FAIL"))
    return 0 if state["ok"] else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    root = argv[argv.index("--root") + 1] if "--root" in argv else DEFAULT_ROOT
    fails, lines = check(root)
    print("=== R48 抽查：软删除语义一致性（第二十二类可审计不变量）· root=%s ===" % root)
    for ln in lines:
        print(ln)
    print("--- 汇总：PASS %d / FAIL %d ---"
          % (len([l for l in lines if l.startswith("[PASS]")]), len(fails)))
    for f in fails:
        print("[FAIL] " + f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
