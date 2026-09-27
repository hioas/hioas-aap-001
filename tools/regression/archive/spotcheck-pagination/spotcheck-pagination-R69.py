#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R69 抽查：**分页「总数」与「列表」谓词一致性**（第四十三类可审计不变量）。

为什么两套门禁都看不见：
  契约测试把**真实响应体**与 JSON Schema 比对 —— `total` 只是一个数字，schema 只约束它的类型，
  **不校验它是否等于「同一谓词下的行数」**（也不校验 total >= items 长度、也不校验跨页不重不漏）；
  覆盖门禁只比「方法 + 路径」是否注册；openapi 与客户端 TS 不被任何测试执行。
  → 分页接口的 count 查询与 list 查询若**谓词（WHERE）或参数不同源**，
     `total` 与 `items` 描述的不是同一集合：客户端分页器会显示错误页数 / 出现「翻到最后一页却是空的」，
     而 204 例全绿也完全看不见（用例通常只断言 200 + items 的**形状**）。

真源：
  S = 实现分页站点（**同一方法体内**同时出现 `count(*)` 查询与 `limit ? offset ?` 查询）
  C = count 侧谓词文本（SQL 字面量 ∪ 常量引用 ∪ 拼接表达式，去别名后归一）
  L = list 侧谓词文本（`from <表>` 之后、`order by` 之前的同一套拼接）
  A = 参数来源（count 的实参 vs list 的实参，去掉分页两参数后的前缀）
  R = `total` 的取值来源（必须是 count 查询的结果，不得是 `items.size()`）
  T = 测试源（total 断言计数，作正向对照）

判据：
  A0a..A0d 解析器正向对照（源文件数 / 分页站点数 / count 语句数 / limit-offset 语句数 均须 > 0）
  A1 每个分页站点：count 谓词 ≡ list 谓词（同源）
  A2 每个分页站点：count 参数来源 ≡ list 参数来源（同源；允许 `new ArrayList<>(count 源)` 派生与追加分页两参数）
  A3 每个分页站点：`total` 来自 count 查询结果，且不是 `items.size()`
  A4 返回分页响应的方法必须含 count 查询（否则 total 无来源）
  A5 含 `count(*)` 但**不含** limit/offset 的方法 = 存在性/聚合计数（信息项）
  A6 测试源里 `total` 断言计数（信息项 + 正向对照）

用法：python spotcheck-pagination-R69.py [--root E:/workspaces/hioas/hioas-aap-001] [--src <main 源码目录>]
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path("E:/workspaces/hioas/hioas-aap-001")

CONST_RE = re.compile(r"(?m)^[ \t]*(?:private|protected|public)?\s*static\s+final\s+String\s+(\w+)\s*=")
CLASS_LIT_RE = re.compile(r"^[\w.$]+\.class$")
COUNT_RE = re.compile(r"count\s*\(\s*\*\s*\)", re.I)
PAGE_RE = re.compile(r"limit\s*\?\s*offset\s*\?", re.I)
FROM_RE = re.compile(r"\bfrom\s+([A-Za-z_]\w*)", re.I)
ORDER_RE = re.compile(r"\border\s+by\b", re.I)
SQL_KEYWORDS = {"where", "and", "or", "order", "group", "limit", "offset", "on", "join", "left",
                "right", "inner", "set", "values", "select", "from", "as", "union", "having"}
METHOD_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:public|protected|private|static|final|synchronized|abstract|default|native|strictfp)\s+)+"
    r"([\w.$<>\[\],\s?]+?)\s+(\w+)\s*\(")
ORM_PAGED_RE = re.compile(r"\.paginate\s*\(|Page\.of\(|getTotalRow\s*\(\s*\)")
PAGE_RESP_RE = re.compile(r"PageResult\.of\(|new\s+\w*(?:Page|ListResult)\s*\(")


# --------------------------------------------------------------------------- 基础工具

def strip_comments(src: str) -> str:
    """剥注释，**保留**字符串/字符/文本块字面量（坑 58/140）。"""
    out, i, n = [], 0, len(src)
    while i < n:
        if src[i:i + 3] == '"""':
            j = src.find('"""', i + 3)
            j = n if j < 0 else j + 3
            out.append(src[i:j]); i = j; continue
        c = src[i]
        if c in '"\'':
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2; continue
                if src[j] == c:
                    j += 1; break
                j += 1
            out.append(src[i:j]); i = j; continue
        if src[i:i + 2] == "//":
            j = src.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j; continue
        if src[i:i + 2] == "/*":
            j = src.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in src[i:j])); i = j; continue
        out.append(c); i += 1
    return "".join(out)


def match_paren(src: str, open_idx: int) -> int:
    depth, i, n = 0, open_idx, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2; continue
                if src[i] == '"':
                    break
                i += 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def match_brace(src: str, open_idx: int) -> int:
    depth, i, n = 0, open_idx, len(src)
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2; continue
                if src[i] == '"':
                    break
                i += 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_body_start(src: str, from_idx: int):
    """从 `)` **之后**（from_idx = close+1，坑 124）括号深度扫描找方法体 `{`。"""
    i, n = from_idx, len(src)
    while i < n:
        c = src[i]
        if c in '"':
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2; continue
                if src[i] == c:
                    break
                i += 1
        elif c == ";":
            return -1, -1
        elif c == "{":
            return i, match_brace(src, i)
        i += 1
    return -1, -1


def split_top_plus(s: str):
    parts, depth, start, i, n = [], 0, 0, 0, len(s)
    while i < n:
        if s[i:i + 3] == '"""':
            j = s.find('"""', i + 3)
            i = n if j < 0 else j + 3
            continue
        c = s[i]
        if c in '"\'':
            i += 1
            while i < n:
                if s[i] == "\\":
                    i += 2; continue
                if s[i] == c:
                    i += 1; break
                i += 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "+" and depth == 0:
            parts.append(s[start:i]); start = i + 1
        i += 1
    parts.append(s[start:])
    return parts


def literal_text(t: str) -> str:
    t = t.strip()
    if t.startswith('"""') and t.endswith('"""') and len(t) >= 6:
        return t[3:-3]
    if t.startswith('"') and t.endswith('"') and len(t) >= 2:
        return t[1:-1]
    return t


def top_args(src: str, open_idx: int):
    """调用实参（**顶层逗号**切分，坑 111-③）。"""
    close = match_paren(src, open_idx)
    if close < 0:
        return []
    inner = src[open_idx + 1:close]
    if not inner.strip():
        return []
    args, depth, start, i, n = [], 0, 0, 0, len(inner)
    while i < n:
        if inner[i:i + 3] == '"""':
            j = inner.find('"""', i + 3); i = n if j < 0 else j + 3; continue
        c = inner[i]
        if c in '"\'':
            i += 1
            while i < n:
                if inner[i] == "\\":
                    i += 2; continue
                if inner[i] == c:
                    break
                i += 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            args.append(inner[start:i]); start = i + 1
        i += 1
    args.append(inner[start:])
    return [a.strip() for a in args]


def collect_consts(src: str):
    """String 常量 → 字面量文本（坑 98/152：SQL 常写成 `static final String X = \"\"\"…\"\"\"`）。"""
    out = {}
    for m in CONST_RE.finditer(src):
        tail = src[m.end():m.end() + 8000].lstrip()
        if tail.startswith('"""'):
            j = tail.find('"""', 3)
            out[m.group(1)] = tail[3:j] if j > 0 else tail[3:]
        elif tail.startswith('"'):
            j = tail.find('"', 1)
            out[m.group(1)] = tail[1:j] if j > 0 else tail[1:]
    return out


def methods_of(src: str):
    """方法表 [(name, body_start, body_end)]（注释已剥；括号深度扫描，坑 63/124）。"""
    out = []
    for m in METHOD_RE.finditer(src):
        open_idx = src.find("(", m.end() - 1)
        if open_idx < 0:
            continue
        close = match_paren(src, open_idx)
        if close < 0:
            continue
        bs, be = find_body_start(src, close + 1)
        if bs < 0 or be < 0:
            continue
        out.append((m.group(2), bs, be))
    return out


# --------------------------------------------------------------------------- 谓词提取

def sql_operands(expr: str, consts):
    """SQL 表达式 → [(kind, text)]，kind ∈ {lit,id,expr}；常量引用回查（坑 99-①）。"""
    out = []
    for op in split_top_plus(expr):
        t = op.strip()
        if not t:
            continue
        if t.startswith('"'):
            out.append(("lit", literal_text(t)))
        elif re.fullmatch(r"[A-Za-z_$][\w$]*", t):
            out.append(("lit", consts[t]) if t in consts else ("id", t))
        else:
            out.append(("expr", t))
    return out


def first_top_where(s: str) -> str:
    """取**顶层**（括号深度 0，剥离 join/子查询）第一个 `where` 起的文本。

    JOIN 子句（`left join x on … and deleted = false`）与子查询里的 `where` **不是**谓词起点，
    按正则 `search` 会把它们算进来 —— 判据范围必须与「WHERE 谓词」的语义一致（坑 81/140）。
    """
    depth, i, n = 0, 0, len(s)
    while i < n:
        if s[i:i + 3] == '"""':
            j = s.find('"""', i + 3)
            i = n if j < 0 else j + 3
            continue
        c = s[i]
        if c in '"\'':
            i += 1
            while i < n:
                if s[i] == "\\":
                    i += 2; continue
                if s[i] == c:
                    i += 1; break
                i += 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and re.match(r"where\b", s[i:], re.I) and \
                (i == 0 or not (s[i - 1].isalnum() or s[i - 1] == "_")):
            return s[i:]
        i += 1
    return ""


def predicate_of(expr: str, consts):
    """取「顶层 where 之后、order by 之前」的谓词文本（跨拼接链，坑 101/140）。"""
    ops = sql_operands(expr, consts)
    idx, table = None, None
    for i, (kind, text) in enumerate(ops):
        m = FROM_RE.search(text)
        if m:
            idx, table = i, m.group(1)
            break
    if idx is None:
        return None, None
    parts = [t for _k, t in ops[idx + 1:]]
    joined = " ".join(parts)
    pred = first_top_where(joined)
    if pred == "":
        # 谓词可能就写在同一字面量的 where 之后（如 count 侧的单文本块）
        tail = ops[idx][1]
        m = FROM_RE.search(tail)
        pred = first_top_where(tail[m.end():])
    j = ORDER_RE.search(pred)
    if j:
        pred = pred[:j.start()]
    return table, pred


def resolve_var(body: str, var: str) -> str:
    """解析局部谓词变量的取值：初值字面量 + 各 `append` 字面量（非字面量记 `?`）。"""
    parts = []
    m = re.search(r"(?:StringBuilder|String)\s+%s\s*=\s*(?:new\s+(?:StringBuilder|String)\s*\(\s*)?"
                  r"(\"\"\"[\s\S]*?\"\"\"|\"(?:\\.|[^\"])*\")" % re.escape(var), body)
    if m:
        parts.append(literal_text(m.group(1)))
    for am in re.finditer(r"\b%s\s*\.\s*append\s*\(" % re.escape(var), body):
        m2 = re.match(r'\s*("""[\s\S]*?"""|"(?:\\.|[^"])*")', body[am.end():])
        parts.append(literal_text(m2.group(1)) if m2 else "?")
    return " ".join(parts)


def norm_pred(p):
    if p is None:
        return None
    s = p.lower().replace('"', "")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\b[a-z][a-z0-9_]{0,4}\.(?=[a-z_])", "", s)   # 去别名前缀（p.deleted → deleted）
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^where\b", "", s).strip()
    return re.sub(r"\s+", " ", s).strip()


def pids(vals):
    out = []
    for v in vals:
        v = v.strip()
        m = re.fullmatch(r"([A-Za-z_$][\w$]*)\.toArray\(\)", v)
        out.append(m.group(1) if m else v)
    return out


def value_args(args):
    """去掉 SQL(0) / class 字面量 / 方法引用 / lambda，得到取值实参。"""
    out = []
    for a in args[1:]:
        t = a.strip()
        if CLASS_LIT_RE.match(t) or "::" in t or "->" in t:
            continue
        out.append(t)
    return out


def last_return(body: str) -> str:
    ret = ""
    for m in re.finditer(r"\breturn\b", body):
        j = body.find(";", m.end())
        if j > 0:
            ret = body[m.end():j]
    return ret


# --------------------------------------------------------------------------- 主流程

def rel_path(p: Path, root: Path) -> str:
    """仓库外路径兜底（坑 34：Path.relative_to 对仓库外路径抛 ValueError）。"""
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def scan(root: Path, src_dir: Path):
    files = sorted(src_dir.rglob("*.java"))
    sites, count_calls, page_calls, api_counts, page_only = [], [], [], [], []
    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        src = strip_comments(raw)
        consts = collect_consts(src)
        rel = rel_path(f, root)
        for name, bs, be in methods_of(src):
            body = src[bs:be]
            ccalls, pcalls = [], []
            for m in re.finditer(r"\bjdbc\s*\.\s*(query|queryForObject|queryForList)\s*\(", body):
                o = body.find("(", m.end() - 1)
                args = top_args(body, o)
                if not args:
                    continue
                expr = args[0]
                rexpr = resolve_expr(expr, consts)
                if COUNT_RE.search(rexpr):
                    ccalls.append((o, args, expr))
                if PAGE_RE.search(rexpr):
                    pcalls.append((o, args, expr))
                    page_calls.append((rel, name, expr))
                if COUNT_RE.search(rexpr):
                    count_calls.append((rel, name, expr))
            returns_page = bool(PAGE_RESP_RE.search(body))
            orm = bool(ORM_PAGED_RE.search(body))
            if ccalls and pcalls:
                sites.append((str(f), rel, name, body, ccalls, pcalls, orm, returns_page))
            elif ccalls and returns_page:
                # 分页响应 + count，但**没有** limit/offset → 返回全量而 total 只是子集计数
                sites.append((str(f), rel, name, body, ccalls, [], orm, returns_page))
            elif pcalls and returns_page:
                sites.append((str(f), rel, name, body, [], pcalls, orm, returns_page))
            elif ccalls:
                api_counts.append((rel, name))
            elif pcalls:
                page_only.append((rel, name))
            elif returns_page:
                # 既无 count 也无 limit/offset 却返回分页响应：ORM 分页豁免 / 否则判「分页响应来源不明」
                sites.append((str(f), rel, name, body, [], [], orm, returns_page))
    return files, sites, count_calls, page_calls, api_counts, page_only


def resolve_expr(expr: str, consts) -> str:
    """把表达式里引用的 String 常量**回查展开**后再判 `count(*)` / `limit ? offset ?`。

    否则 `jdbc.queryForObject(COUNT_SQL + where, …)` 这类写法会被判成「没有 count 查询」
    → 假 A4（坑 99-①/98：常量引用未回查）。R69 判别力自测的 R1 回归守卫抓出此缺陷。
    """
    extra = [consts[t] for t in re.findall(r"\b[A-Za-z_]\w*\b", expr) if t in consts]
    return expr + " " + " ".join(extra)


def field_names_of(src: str):
    return {m.group(1) for m in re.finditer(
        r"(?m)^[ \t]*(?:private|protected|public)\s+(?:static\s+)?(?:final\s+)?"
        r"[\w.$<>\[\],\s?]+\s+(\w+)\s*(?:=|;)", src)}


def cross_method_count(root: Path, src_dir: Path):
    """跨方法组合：同一方法体内对**同一接收者**同时调用 `list(...)` 与 `count(...)`
    时，`count` 的实参必须覆盖 `list` 的**非分页**实参（否则 total 与 items 不同源）。

    为什么必须单独查：这类漂移**不在同一个方法体里**（count 与 list 分处两个方法），
    单方法站点判据完全看不见（本项目实测：ReportController#list 的 total 来自 `reportService.count(principal)`，
    而 items 来自 `reportService.list(principal, page, pageSize, result)` —— 带 `result` 筛选时 total 是全量）。
    """
    out = []
    for f in sorted(src_dir.rglob("*.java")):
        src = strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        for name, bs, be in methods_of(src):
            body = src[bs:be]
            by_recv = {}
            for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\.\s*(list|count)\s*\(", body):
                o = body.find("(", m.end() - 1)
                by_recv.setdefault(m.group(1), {})[m.group(2)] = top_args(body, o)
            for recv, calls in by_recv.items():
                if "list" not in calls or "count" not in calls:
                    continue
                largs = [a for a in calls["list"] if not re.search(r"\b(page|pageSize)\b", a)]
                cargs = calls["count"]
                missing = [a for a in largs if a not in cargs]
                out.append((rel_path(f, root), name, recv, largs, cargs, missing))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--src", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    src_dir = Path(a.src) if a.src else root / "aap-server/src/main/java"
    lines, fails = [], []

    def emit(tag, ok, msg):
        prefix = "PASS" if ok else "FAIL"
        lines.append("[%s] %s %s" % (prefix, tag, msg))
        if not ok:
            fails.append(tag)

    if not src_dir.exists():
        lines.append("[INFO] 源码目录不存在：%s" % src_dir)
        files, sites, count_calls, page_calls, api_counts, page_only = [], [], [], [], [], []
    else:
        files, sites, count_calls, page_calls, api_counts, page_only = scan(root, src_dir)

    lines.append("== R69 抽查：分页「总数」与「列表」谓词一致性（第四十三类可审计不变量） ==")
    lines.append("解析计数：main 源文件 %d · 分页站点 %d · count 语句 %d · limit-offset 语句 %d · "
                 "非分页 count 方法 %d" % (len(files), len(sites), len(count_calls), len(page_calls),
                                        len(api_counts)))
    lines.append("")

    # A0 正向对照（坑 46/75/132：缺一条则「0 发现」不可信）
    emit("A0a", len(files) > 0, "解析到 main 源文件 %d（须 > 0）" % len(files))
    emit("A0b", len(sites) > 0, "解析到分页站点 %d（须 > 0）" % len(sites))
    emit("A0c", len(count_calls) > 0, "解析到 count(*) 语句 %d（须 > 0）" % len(count_calls))
    emit("A0d", len(page_calls) > 0, "解析到 limit ? offset ? 语句 %d（须 > 0）" % len(page_calls))

    # 合并同一方法内的多个 count/limit 调用（取第一条为基准）
    n_eval, n_unres, n_a2, n_a3, n_skip = 0, 0, 0, 0, 0
    for fpath, rel, name, body, ccalls, pcalls, orm, returns_page in sites:
        loc = "%s#%s" % (rel, name)
        src = strip_comments(Path(fpath).read_text(encoding="utf-8", errors="replace"))
        consts = collect_consts(src)
        if not ccalls and not pcalls:
            delegated = any(re.search(r"\b%s\s*\." % re.escape(fn), body)
                            for fn in field_names_of(src))
            if not orm and not delegated:
                n_skip += 1
                emit("A6b", False, "%s 返回分页响应但既无 count(*) 也无 limit/offset，且非 ORM 分页、无委托调用 → 分页来源不明" % loc)
                continue
            n_skip += 1
            lines.append("[INFO] A6b %s %s → 豁免（total 同源由 A6c 判）" % (
                loc, "ORM 分页（`.paginate(Page.of(...))` + getTotalRow）" if orm else "分页由被调方提供（委托调用）"))
            continue
        if pcalls and not ccalls:
            n_skip += 1
            emit("A4", False, "%s 返回分页响应但**没有 count(*) 查询** → total 无来源" % loc)
            continue
        if ccalls and not pcalls:
            if orm:
                n_skip += 1
                lines.append("[INFO] A4b %s 含 count 与 ORM 分页（`.paginate(Page.of(...))`）→ 豁免" % loc)
                continue
            n_skip += 1
            emit("A5b", False, "%s 返回分页响应但没有 limit ? offset ? → 返回全量而 total 只是子集计数" % loc)
            continue
        # 常量表已按文件级解析
        ctab, cpred = predicate_of(ccalls[0][2], consts)
        ltab, lpred = predicate_of(pcalls[0][2], consts)
        if cpred is None or lpred is None:
            n_unres += 1
            lines.append("[INFO] A1 %s 未能静态判定谓词（count 表=%s list 表=%s）" % (loc, ctab, ltab))
        else:
            # 谓词写成局部变量（StringBuilder/String）时必须**解析出真实内容**，
            # 否则「where == where」是**空转假绿**（坑 98/75：只比标识符等于什么都没比）。
            cvar = cpred.strip() if re.fullmatch(r"[A-Za-z_$][\w$]*", cpred.strip()) else None
            lvar = lpred.strip() if re.fullmatch(r"[A-Za-z_$][\w$]*", lpred.strip()) else None
            ctext = resolve_var(body, cvar) if cvar else cpred
            ltext = resolve_var(body, lvar) if lvar else lpred
            if cvar and lvar and cvar == lvar:
                # 同一变量 ⇒ 值只算一次（最强同源）；但仍须证明两次查询之间**未被改写**（坑 44）
                lo, hi = min(ccalls[0][0], pcalls[0][0]), max(ccalls[0][0], pcalls[0][0])
                mid = [m for m in re.finditer(r"\b%s\s*\.\s*append\s*\(" % re.escape(cvar), body)
                       if lo < m.start() < hi]
                if mid:
                    emit("A1c", False, "%s 谓词变量 %s 在 count 与 list 查询之间被 append %d 处 → total 与 items 不同源"
                         % (loc, cvar, len(mid)))
            cn, ln = norm_pred(ctext), norm_pred(ltext)
            n_eval += 1
            if cn != ln:
                emit("A1", False, "%s count 谓词 ≠ list 谓词：[%s] vs [%s]" % (loc, cn, ln))
            lines.append("[INFO] A1 %s 表=%s 谓词=[%s]%s（count/list 归一后%s）"
                         % (loc, ctab or ltab, cn or "(空)",
                            "（同一变量 %s）" % cvar if cvar and cvar == lvar else "",
                            "一致" if cn == ln else "不一致"))
        if ctab and ltab and ctab.lower() != ltab.lower():
            emit("A1b", False, "%s count 表 %s ≠ list 表 %s" % (loc, ctab, ltab))
        # A2 参数来源同源
        n_a2 += 1
        pc = pids(value_args(ccalls[0][1]))
        pl = pids(value_args(pcalls[0][1]))
        ok = False
        if pc == pl:
            ok = True
        elif pc and len(pl) > len(pc) and pl[:len(pc)] == pc and \
                all(("pagesize" in v.lower() or "offset" in v.lower()) for v in pl[len(pc):]):
            ok = True
        elif pl and pc and len(pl) == 1:
            # 必须证明「**pl[0] 就是**由 pc[0] 派生」（只查文件里出现过 `new ArrayList<>(pc[0])` 太宽，坑 81）
            ok = re.search(r"(?:StringBuilder|String|List<[^>]*>|var)\s+%s\s*=\s*new\s+ArrayList<[^>]*>\s*\(\s*%s\s*\)"
                           % (re.escape(pl[0]), re.escape(pc[0])), src) is not None
        elif not pc and pl and all(("pagesize" in v.lower() or "offset" in v.lower()) for v in pl):
            ok = True
        if not ok:
            emit("A2", False, "%s count 参数来源 %s ≠ list 参数来源 %s（非同源）" % (loc, pc, pl))
        # A3 total 来源
        n_a3 += 1
        m = re.search(r"Long\s+(\w+)\s*=\s*jdbc\s*\.\s*queryForObject\s*\(", body)
        ret = last_return(body)
        if "items.size()" in ret:
            emit("A3", False, "%s total 取自 items.size()（不是同一集合的 count 结果）" % loc)
        elif m and m.group(1) not in ret:
            emit("A3", False, "%s count 结果变量 %s 未出现在返回构造里（total 来源不明）" % (loc, m.group(1)))

    a1 = [x for x in fails if x == "A1"]
    lines.append("")
    emit("A0e", n_eval > 0 and n_eval == len(sites) - n_skip,
         "已判定 A1 的分页站点 %d / %d（未解析 %d，豁免/跳过 %d）—— 定位率不足时不得判「全部通过」（坑 87）"
         % (n_eval, len(sites) - n_skip, n_unres, n_skip))
    emit("A0f", n_a2 > 0 and n_a3 > 0, "已判定 A2 的站点 %d、A3 的站点 %d（均须 > 0）" % (n_a2, n_a3))
    pairs = cross_method_count(root, src_dir)
    emit("A0g", len(pairs) > 0, "解析到「同接收者 list+count 组合」%d 处（须 > 0，否则 A6c 空转）" % len(pairs))
    for rel, name, recv, largs, cargs, missing in pairs:
        if missing:
            emit("A6c", False, "%s#%s 的 total 来自 %s.count(%s)，但 items 来自 %s.list(%s) → "
                              "count 缺少筛选实参 %s（total 与 items 不同源）"
                 % (rel, name, recv, ", ".join(cargs), recv, ", ".join(largs), missing))
        else:
            lines.append("[INFO] A6c %s#%s %s.count(%s) 覆盖 %s.list 的非分页实参 %s（同源）"
                         % (rel, name, recv, ", ".join(cargs), recv, ", ".join(largs)))
    lines.append("[INFO] A5c 含 limit/offset 但无分页响应的方法 %d 个（纯列表查询）：%s"
                 % (len(page_only), ", ".join(sorted({"#".join(t) for t in page_only})[:6]) or "（无）"))
    lines.append("[INFO] A5 含 count(*) 但不含 limit/offset 的方法 %d 个（存在性/聚合计数，非分页）：%s"
                 % (len(api_counts), ", ".join(sorted({"%s#%s" % t for t in api_counts})[:8]) or "（无）"))

    # A6 测试源正向对照
    tsrc = root / "aap-server/src/test/java"
    n_total = 0
    if tsrc.exists():
        for f in tsrc.rglob("*.java"):
            n_total += len(re.findall(r'path\("total"\)', f.read_text(encoding="utf-8", errors="replace")))
    lines.append("[INFO] A6 测试源 path(\"total\") 断言点 %d 处（正向对照）" % n_total)

    lines.append("")
    lines.append("== 汇总：FAIL %d 条 %s ==" % (len(fails), sorted(set(fails))))
    print("\n".join(lines))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
