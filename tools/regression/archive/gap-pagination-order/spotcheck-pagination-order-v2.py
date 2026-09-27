#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R45 抽查：分页查询「排序确定性」（ORDER BY 必须含唯一键 tie-breaker）不变量。

为什么两套门禁都看不见：
  * 契约测试只校验「元素模型 JSON Schema」——schema 里没有 SQL、没有 ORDER BY、也没有跨页稳定性；
  * 覆盖门禁只比「HTTP 方法 + 路径」是否注册；
  * openapi / 客户端 TS 不被任何测试读取。
后果：分页 SQL 的 ORDER BY 若不含唯一列，并列行在两次查询间顺序不定 ->
      翻页可能「重复行 / 漏行」，而全量 204 例（每例数据量极小）完全看不见。

真源：
  I = 实现 SQL（含 limit/offset 的分页语句的 ORDER BY 列集合 + FROM 表名）
  D = DDL V1__baseline.sql（每表唯一键集合：内联 primary key / 复合 primary key / unique index）
  M = md 冻结清单（是否声明排序规则）
  O = openapi（是否声明 sort/orderBy 查询参数）
  C = 客户端（是否传排序参数）
  T = 测试源（是否有跨页稳定性/重复行断言）

用法： python spotcheck-pagination-order.py [--repo <path>] [--json]
退出码：0 = 无 FAIL；1 = 有 FAIL；9 = 解析器失效（正向对照失败，不等于「零发现」）
"""
import argparse
import hashlib
import json
import os
import re
import sys

RESULTS = []


def emit(tag, name, detail=""):
    RESULTS.append((tag, name, detail))
    line = "[%s] %s" % (tag.ljust(4), name)
    if detail:
        line += "：" + detail
    print(line)


def rel(repo, path):
    try:
        return os.path.relpath(path, repo).replace("\\", "/")
    except ValueError:  # 跨盘符（skill 坑 34）
        return path.replace("\\", "/")


# ----------------------------------------------------------------- 解析器

LIT = re.compile(r'"(?:\\.|[^"\\])*"', re.S)
TEXT_BLOCK = re.compile(r'"""(.*?)"""', re.S)
LIMIT_RE = re.compile(r'\blimit\s+\?\s+offset\s+\?', re.I)


def literals_of(text):
    """返回 [(start, end, 内容)]：三引号文本块优先，再普通字符串字面量。"""
    spans = []
    for m in TEXT_BLOCK.finditer(text):
        spans.append((m.start(), m.end(), m.group(1)))
    for m in LIT.finditer(text):
        if any(s <= m.start() < e for s, e, _ in spans):
            continue
        spans.append((m.start(), m.end(), m.group(0)[1:-1]))
    spans.sort()
    return spans


def concat_chain(text, lits, idx, max_back=12):
    """只沿 `+` 拼接链向后累积（gap 里出现 `;`/`,` 即视为越界 —— skill 坑 44/63）。"""
    parts = [lits[idx][2]]
    k = idx
    ident = re.compile(r'[\s+]*[A-Za-z_][\w.]*\s*(\([^()]*\))?[\s+]*')
    while k > 0 and len(parts) < max_back:
        gap = text[lits[k - 1][1]:lits[k][0]]
        if re.fullmatch(r'[\s+]*', gap) or ident.fullmatch(gap):
            parts.insert(0, lits[k - 1][2])
            k -= 1
        else:
            break
    return "".join(parts)


def parse_order_by(clause):
    """ORDER BY 子句 -> (列集合, 备注)"""
    notes, cols = [], []
    for raw in re.split(r",(?![^()]*\))", clause):
        tok = raw.strip()
        if not tok:
            continue
        tok = re.sub(r'\s+(desc|asc)\b', "", tok, flags=re.I)
        tok = re.sub(r'\s+nulls\s+(last|first)\b', "", tok, flags=re.I).strip()
        if re.fullmatch(r"\d+", tok):
            notes.append("序数 %s（未能静态判定）" % tok)
            continue
        tok = tok.split(".")[-1].strip('"`[] ')          # 去别名前缀 c.id -> id
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok):
            notes.append("非裸列名 %s（未能静态判定）" % tok)
            continue
        cols.append(tok.lower())
    return cols, notes


def find_paginated_statements(impl_files):
    """-> [dict(file, line, order_cols, notes, table, tier)]"""
    found = []
    for path in impl_files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        lits = literals_of(text)
        for idx, (s, _e, body) in enumerate(lits):
            m_lim = LIMIT_RE.search(body)
            if not m_lim:
                continue
            line = text[:s].count("\n") + 1
            chain = concat_chain(text, lits, idx)
            pos = chain.rindex(body) + m_lim.start() if body in chain else m_lim.start()
            acc = chain[:pos]
            ms = list(re.finditer(r'\border\s+by\b', acc, re.I))
            order_clause = acc[ms[-1].end():] if ms else None
            table, tier = None, None
            for cand, t in ((body, "same-literal"), (chain, "stmt-chain")):
                mt = list(re.finditer(r'\bfrom\s+([a-z_][a-z0-9_]*)', cand, re.I))
                if mt:
                    table, tier = mt[-1].group(1).lower(), t
                    break
            if table is None:
                mt = list(re.finditer(r'\bfrom\s+([a-z_][a-z0-9_]*)', text[:s], re.I))
                if mt:
                    table, tier = mt[-1].group(1).lower(), "file-nearest"
            if order_clause is None:
                cols, notes = [], ["未找到 ORDER BY 子句"]
            else:
                cols, notes = parse_order_by(order_clause)
            found.append({"file": path, "line": line, "order_cols": cols, "notes": notes,
                          "table": table, "tier": tier,
                          "order_clause": (order_clause or "").strip()})
    return found


def parse_ddl(ddl_text):
    """-> {table: {'keys': [set(cols),...], 'partial': [bool,...], 'cols': set(all cols)}}"""
    tables = {}
    for m in re.finditer(r'create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)\s*\(', ddl_text, re.I):
        name = m.group(1).lower()
        i = m.end() - 1
        depth, j = 0, i
        while j < len(ddl_text):
            if ddl_text[j] == "(":
                depth += 1
            elif ddl_text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        entry = tables.setdefault(name, {"keys": [], "partial": [], "cols": set()})
        for line in ddl_text[i + 1:j].split(","):
            line = line.strip()
            if re.match(r'^(primary|unique|constraint|check|foreign|partition)\b', line, re.I):
                continue
            head = re.match(r'^(\w+)\s+\S', line)
            if head:
                entry["cols"].add(head.group(1).lower())
            if re.search(r'\bprimary\s+key\b', line, re.I):
                pk = re.search(r'primary\s+key\s*\(([^)]*)\)', line, re.I)
                if pk:
                    cols = {c.strip().strip('"').lower() for c in pk.group(1).split(",") if c.strip()}
                else:
                    h = re.match(r'^(\w+)\b', line)
                    cols = {h.group(1).lower()} if h else set()
                if cols:
                    entry["keys"].append(cols)
                    entry["partial"].append(False)
    for m in re.finditer(
            r'create\s+unique\s+index\s+(?:if\s+not\s+exists\s+)?(\w+)\s+on\s+(\w+)\s*\(([^)]*)\)([^;]*);',
            ddl_text, re.I):
        table = m.group(2).lower()
        cols = {c.strip().strip('"').lower() for c in m.group(3).split(",") if c.strip()}
        entry = tables.setdefault(table, {"keys": [], "partial": [], "cols": set()})
        if cols:
            entry["keys"].append(cols)
            entry["partial"].append(bool(re.search(r'\bwhere\b', m.group(4), re.I)))
    return tables


# ----------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    repo = args.repo

    impl_root = os.path.join(repo, "aap-server", "src", "main", "java")
    test_root = os.path.join(repo, "aap-server", "src", "test", "java")
    ddl_path = os.path.join(repo, "aap-server", "src", "main", "resources", "db", "migration",
                            "V1__baseline.sql")
    md_path = os.path.join(repo, "docs", "backend", "02-API接口模型清单.md")
    oa_path = os.path.join(repo, "docs", "backend", "openapi.yaml")
    client_root = os.path.join(repo, "aap-client", "src")

    impl_files = []
    for root, _dirs, files in os.walk(impl_root):
        for fn in files:
            if fn.endswith(".java"):
                impl_files.append(os.path.join(root, fn))
    impl_files.sort()

    read_files = [ddl_path, md_path, oa_path]
    before = {}
    for p in read_files:
        with open(p, "rb") as fh:
            raw = fh.read()
        before[p] = (hashlib.md5(raw).hexdigest(), len(raw))

    tables = parse_ddl(open(ddl_path, encoding="utf-8").read())
    stmts = find_paginated_statements(impl_files)

    # ---- 正向对照（skill 坑 46/75：0 发现先怀疑解析器）
    emit("PASS" if stmts else "FAIL", "P0 正向对照：解析到含 limit/offset 的分页 SQL 条数 > 0",
         "实测 %d 条" % len(stmts))
    emit("PASS" if tables else "FAIL", "P0b 正向对照：DDL 解析到表定义 > 0",
         "实测 %d 张表、唯一键集合 %d 组" % (len(tables), sum(len(v["keys"]) for v in tables.values())))

    parsed_order = [s for s in stmts if s["order_cols"]]
    emit("PASS" if len(parsed_order) == len(stmts) else "FAIL",
         "P1 每条分页 SQL 的 ORDER BY 列集合都解析到",
         "%d/%d" % (len(parsed_order), len(stmts)))

    known = [s for s in stmts if s["table"] in tables]
    emit("PASS" if len(known) == len(stmts) else "FAIL",
         "P2 每条分页 SQL 的 FROM 表名都能在 DDL 里找到（防解析到错表）",
         "%d/%d；定位档位=%s" % (len(known), len(stmts), sorted({s["tier"] for s in stmts})))

    consistent = [s for s in known if all(c in tables[s["table"]]["cols"] for c in s["order_cols"])]
    emit("PASS" if len(consistent) == len(known) else "FAIL",
         "P2b 表名映射自校验：ORDER BY 列都存在于所解析到的表定义中",
         "%d/%d" % (len(consistent), len(known)))

    # ---- 硬断言：ORDER BY 必须含完整唯一键（tie-breaker）
    fails, passes, info = [], [], []
    for s in stmts:
        tag = "%s:%d" % (rel(repo, s["file"]), s["line"])
        if s["table"] not in tables or not s["order_cols"]:
            info.append("%s 未能静态判定（表=%s 列=%s 备注=%s）"
                        % (tag, s["table"], s["order_cols"], s["notes"]))
            continue
        entry = tables[s["table"]]
        cols = set(s["order_cols"])
        hit = None
        for k, partial in zip(entry["keys"], entry["partial"]):
            if k and k <= cols:
                hit = (k, partial)
                break
        if hit:
            if hit[1]:
                info.append("%s 通过但依据**部分**唯一索引 %s（where 外不保证唯一）"
                            % (tag, sorted(hit[0])))
            passes.append("%s 表=%s order by(%s) ⊇ 唯一键 %s"
                          % (tag, s["table"], s["order_cols"], sorted(hit[0])))
        else:
            near = next((k for k in entry["keys"] if k & cols), None)
            fails.append("%s 表=%s order by(%s) 不含任何完整唯一键；最接近的唯一键=%s（缺 %s）"
                         % (tag, s["table"], s["order_cols"], sorted(near) if near else None,
                            sorted(near - cols) if near else "N/A"))
    for f in fails:
        emit("FAIL", "P3 分页 SQL 的 ORDER BY 必须含完整唯一键（tie-breaker）", f)
    emit("PASS" if not fails else "FAIL", "P3 汇总：分页 SQL 排序确定性",
         "PASS %d / FAIL %d / 未能静态判定 %d" % (len(passes), len(fails), len(info)))
    for p in passes:
        print("      [OK ] " + p)
    for i in info:
        print("      [INFO] " + i)

    # ---- 跨源信息项
    md = open(md_path, encoding="utf-8").read()
    oa = open(oa_path, encoding="utf-8").read()
    md_sort = len(re.findall(r'排序|order\s*by|sort', md, re.I))
    oa_sort = len(re.findall(r'name:\s*(sort|orderBy|order)\b', oa))
    client_sort = 0
    for root, _d, files in os.walk(client_root):
        for fn in files:
            if fn.endswith((".ts", ".vue")):
                t = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
                client_sort += len(re.findall(r'\b(sort|orderBy|order_by)\b', t))
    test_page2, test_stability = 0, 0
    for root, _d, files in os.walk(test_root):
        for fn in files:
            if fn.endswith(".java"):
                t = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
                test_page2 += len(re.findall(r'page=2|"page",\s*2|pageSize[^\n]*\b2\)', t))
                test_stability += len(re.findall(r'跨页|重复行|不重复', t))
    emit("INFO", "I1 md 清单出现排序相关字样处数", "%d" % md_sort)
    emit("INFO", "I2 openapi 声明 sort/orderBy 查询参数处数", "%d" % oa_sort)
    emit("INFO", "I3 客户端出现排序参数标识符处数", "%d" % client_sort)
    emit("INFO", "I4 测试里翻第 2 页的调用点 %d 处；跨页稳定性/重复行断言 %d 处"
         % (test_page2, test_stability))

    after_ok = all(
        (lambda raw: (hashlib.md5(raw).hexdigest(), len(raw)))(open(p, "rb").read()) == before[p]
        for p in read_files)
    emit("PASS" if after_ok else "FAIL", "Z1 三个被读文件指纹未变（抽查脚本零写副作用）",
         "%d 个文件" % len(read_files))

    n_fail = sum(1 for t, _, _ in RESULTS if t == "FAIL")
    n_pass = sum(1 for t, _, _ in RESULTS if t == "PASS")
    n_info = sum(1 for t, _, _ in RESULTS if t == "INFO")
    print("\n合计 %d 条：PASS %d，FAIL %d，INFO %d" % (len(RESULTS), n_pass, n_fail, n_info))
    if args.json:
        print(json.dumps({"pass": n_pass, "fail": n_fail, "info": n_info,
                          "stmts": len(stmts), "tables": len(tables)}, ensure_ascii=False))
    if not stmts or not tables or len(parsed_order) != len(stmts):
        return 9
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
