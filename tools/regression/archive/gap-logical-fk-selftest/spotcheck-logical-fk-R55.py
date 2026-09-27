#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R55 抽查：**逻辑外键（FK*）跨源一致性** —— 第二十九类「两套门禁都看不见」的契约不变量。

为什么两套门禁看不见：
  * 契约测试只把**响应体**与各元素 JSON Schema 比对 —— 引用列的存在性/目标表/写入校验**都不在 schema 里**；
  * 覆盖门禁只比「HTTP 方法 + 路径」注册表 —— 引用校验是服务层行为；
  * openapi 与客户端 TS 不被任何测试读取/执行。
  于是「ER 声明的逻辑外键 ⇔ DDL 真实列」「DB 级 FK 策略声明 ⇔ 实际零 FK」「请求体引用字段的父行存在性校验」
  全部对 204 例全绿不可见。

真源五处：
  E = docs/backend/01-ER数据模型.md      （FK* 声明 + → 目标表；并声明「不建 DB 级 FK」）
  D = db/migration/*.sql                 （列存在性 + DB 级 FK 约束计数）
  R = json-schema/requests/*.json + endpoints.json （请求体引用字段 → 端点）
  I = src/main/java/**                   （写入路径的父行存在性校验）
  T = src/test/java/**                   （「引用不存在」的断言背书）

只读脚本：不写仓库任何文件。
用法：python spotcheck-logical-fk.py [--root <仓库根>] [--selftest]
"""
import argparse
import json
import os
import re
import sys

ROOT_DEFAULT = "E:/workspaces/hioas/hioas-aap-001"

PASS, FAIL, INFO = [], [], []


def ok(tag, msg):
    PASS.append((tag, msg))


def bad(tag, msg):
    FAIL.append((tag, msg))


def info(tag, msg):
    INFO.append((tag, msg))


# ---------------------------------------------------------------- 通用工具
def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def strip_comments_java(s):
    """剥 // 与 /* */ 注释，保留字符串字面量（坑 58：注释里的内容不是调用点）。"""
    out, i, n, instr = [], 0, len(s), False
    while i < n:
        c = s[i]
        if instr:
            if c == "\\":
                out.append(s[i:i + 2])
                i += 2
                continue
            if c == '"':
                instr = False
            out.append(c)
            i += 1
            continue
        if c == '"':
            instr = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def match_paren(s, i):
    """s[i] == '(' → 返回配对的 ')' 下标；用括号深度扫描（坑 63）。"""
    d = 0
    instr = False
    while i < len(s):
        c = s[i]
        if instr:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return i
        i += 1
    return -1


def rmatch_paren(s, i):
    d = 0
    while i >= 0:
        c = s[i]
        if c == ")":
            d += 1
        elif c == "(":
            d -= 1
            if d == 0:
                return i
        i -= 1
    return -1


def find_body_start(s, i):
    """从 i 起找方法体 '{'：括号深度为 0 且不在字符串内（坑 55/63）。"""
    d = 0
    instr = False
    while i < len(s):
        c = s[i]
        if instr:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
        elif c == "{" and d == 0:
            return i
        i += 1
    return -1


def find_body_end(s, i):
    """s[i] == '{' → 配对的 '}'。"""
    d = 0
    instr = False
    while i < len(s):
        c = s[i]
        if instr:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return i
        i += 1
    return -1


def java_files(root, sub):
    base = os.path.join(root, "aap-server", "src", sub, "java")
    out = []
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".java"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def methods_of(src):
    """{方法名: (签名实参文本, 方法体文本)}（同名只留第一处，够用）。"""
    res = {}
    for m in re.finditer(r"\b(?:public|private|protected)\s+[\w<>,\[\]\.\?\s]+\s+(\w+)\s*\(", src):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "catch", "return", "new"):
            continue
        if name in res:
            continue
        po = m.end() - 1
        pc = match_paren(src, po)
        if pc < 0:
            continue
        b0 = find_body_start(src, pc + 1)
        if b0 < 0:
            continue
        b1 = find_body_end(src, b0)
        if b1 < 0:
            continue
        res[name] = (src[po + 1:pc], src[b0:b1 + 1])
    return res


def param_names(sig):
    """从方法实参文本取形参名（跳过泛型与注解；顶层逗号切分）。"""
    out, depth, cur = [], 0, ""
    for ch in sig:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    out.append(cur)
    names = []
    for part in out:
        toks = re.findall(r"[A-Za-z_$][\w$]*", part)
        if toks:
            names.append(toks[-1])
    return [n for n in names if n not in ("final",)]


def camel(field):
    parts = field.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ---------------------------------------------------------------- 解析器
def parse_ddl(root):
    """→ (tables{表名: {列名: 类型}}, fk_count)"""
    tables = {}
    fk_count = 0
    mig = os.path.join(root, "aap-server", "src", "main", "resources", "db", "migration")
    for f in sorted(os.listdir(mig)) if os.path.isdir(mig) else []:
        if not f.endswith(".sql"):
            continue
        sql = read(os.path.join(mig, f))
        low = sql.lower()
        fk_count += len(re.findall(r"\breferences\b", low)) + len(re.findall(r"\bforeign\s+key\b", low))
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([a-z_][a-z0-9_]*)",
                             low, re.MULTILINE):
            name = m.group(1)
            j = m.end()
            while j < len(low) and low[j] in " \t\r\n":
                j += 1
            if j >= len(low) or low[j] != "(":
                tables[name] = {}          # 分区表（partition of …）：无列定义
                continue
            i = match_paren(sql, j)
            if i < 0:
                continue
            body = sql[j + 1:i]
            cols = {}
            for line in body.split("\n"):
                t = line.strip()
                if not t or t.startswith("--"):
                    continue
                mm = re.match(r"([a-z_][a-z0-9_]*)\s+([a-z][a-z0-9_]*(\s*\([^)]*\))?)", t, re.I)
                if not mm:
                    continue
                col = mm.group(1).lower()
                if col in ("constraint", "primary", "unique", "foreign", "check"):
                    continue
                cols[col] = mm.group(2).lower()
            tables[name] = cols
    return tables, fk_count


def parse_er(root):
    """→ (fks[(表, 列, 目标表)], policy_declared:bool)"""
    md = read(os.path.join(root, "docs", "backend", "01-ER数据模型.md"))
    fks = []
    policy = bool(re.search(r"不建\s*DB\s*级\s*FK|逻辑外键", md))
    cur_table = None
    for raw in md.split("\n"):
        line = raw.rstrip()
        m = re.match(r"\*\*([a-z_][a-z0-9_]*)\*\*", line.strip())
        if m:
            cur_table = m.group(1)
        # 表格行形式：| account_id | bigint | FK* | → aap_provider_account |
        if "|" in line and "FK*" in line:
            cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]
            cells = [c for c in cells if c != ""]
            if cells and re.match(r"^[a-z_][a-z0-9_]*$", cells[0]) and cur_table:
                col = cells[0]
                tgt = ""
                tm = re.search(r"→\s*([a-z_][a-z0-9_]*)", line)
                if tm:
                    tgt = tm.group(1)
                fks.append((cur_table, col, tgt))
            continue
        # 紧凑形式：**aap_user_role**：`user_id FK*`、`user_type`…
        if "FK*" in line and cur_table:
            for tm in re.finditer(r"`([a-z_][a-z0-9_]*)\s+FK\*[^`]*`", line):
                fks.append((cur_table, tm.group(1), ""))
    # 去重
    seen, uniq = set(), []
    for t in fks:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq, policy


def norm_key(method, path):
    """跨源统一归一：折叠路径变量 + 剥 /api/v1 前缀（坑 57：两侧必须走同一个 key()）。"""
    p = re.sub(r"\{[^}]*\}", "{}", path or "")
    if p.startswith("/api/v1"):
        p = p[len("/api/v1"):]
    return method.upper() + " " + p


def parse_request_refs(root):
    """→ (refs[(端点ID, 方法, 路径, 字段, 请求模型)], ref_field_count)"""
    ep_path = os.path.join(root, "docs", "backend", "endpoints.json")
    if not os.path.isfile(ep_path):
        return [], 0
    eps = json.load(open(ep_path, encoding="utf-8"))["endpoints"]
    req_dir = os.path.join(root, "docs", "backend", "json-schema", "requests")
    by_model = {}
    total_fields = 0
    for f in sorted(os.listdir(req_dir)) if os.path.isdir(req_dir) else []:
        if not f.endswith(".schema.json"):
            continue
        model = f[: -len(".schema.json")]          # 坑 115：不能用 Path.stem
        try:
            sch = json.load(open(os.path.join(req_dir, f), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        fields = [k for k in (sch.get("properties") or {}) if k.endswith("_id")]
        by_model[model] = sorted(fields)
        total_fields += len(fields)
    refs = []
    for e in eps:
        for fld in by_model.get(e.get("request_model") or "", []):
            refs.append((e["id"], e["method"], e["path"], fld, e["request_model"]))
    return refs, total_fields


MAPPING_ANN = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")


def parse_controllers(root):
    """→ {归一路由: (文件, 方法名, 方法体)}；类级 @RequestMapping 前缀 + 裸注解回落（坑 87）。"""
    routes = {}
    for path in java_files(root, "main"):
        src0 = read(path)
        if "@RequestMapping" not in src0 and not MAPPING_ANN.search(src0):
            continue
        src = strip_comments_java(src0)
        # 类级前缀：class 关键字之前最后一个 @RequestMapping 的字符串
        cls_m = re.search(r"\bclass\s+\w+", src)
        prefix = ""
        if cls_m:
            for rm in re.finditer(r"@RequestMapping\s*\(\s*\"([^\"]*)\"", src[: cls_m.start()]):
                prefix = rm.group(1)
        for m in MAPPING_ANN.finditer(src):
            ann_end = m.end()
            p = ""
            j = ann_end
            while j < len(src) and src[j] in " \t\r\n":
                j += 1
            if j < len(src) and src[j] == "(":
                close = match_paren(src, j)
                if close < 0:
                    continue
                sm = re.search(r"\"([^\"]*)\"", src[j:close])
                p = sm.group(1) if sm else ""
                scan_from = close + 1          # 从注解右括号之后起扫（否则首个 ')' 让深度变负，方法体永远找不到）
            else:
                scan_from = ann_end          # 裸注解：路径回落到类级前缀（坑 87）
            b0 = find_body_start(src, scan_from)
            if b0 < 0:
                continue
            p0 = rmatch_paren(src, src.rfind(")", 0, b0))
            if p0 < 0:
                continue
            nm = re.search(r"(\w+)\s*$", src[:p0])
            if not nm:
                continue
            b1 = find_body_end(src, b0)
            full = prefix + p                       # 方法级路径必须拼类级前缀（坑 87）
            if not full.startswith("/"):
                full = "/" + full
            routes.setdefault(norm_key(m.group(1), full), (path, nm.group(1), src[b0:b1 + 1]))
    return routes


EXISTENCE_PAT = re.compile(
    r"(E_1406|E_1001|不存在|not\s*found|notFound|exists\s*\(|select\s+count\(\*\)|"
    r"\b(require|ensure|assert|check|load|find|resolve)\w*\s*\()", re.I)

# 引用字段 → (父表, 实体关键词)：判据必须**与该引用字段同域**（坑 81：判据范围与语义一致）
REF_PARENT = {
    "file_id": ("aap_file_asset", ["file", "文件", "asset"]),
    "logo_file_id": ("aap_file_asset", ["file", "文件", "asset"]),
    "voucher_file_id": ("aap_file_asset", ["file", "文件", "asset"]),
    "credential_id": ("aap_credential", ["credential", "凭据"]),
    "provider_id": ("aap_provider", ["provider", "供应商"]),
    "contract_id": ("aap_contract", ["contract", "合同"]),
    "item_id": ("aap_quote_item", ["item", "明细"]),
    "batch_id": ("aap_usage_batch", ["batch", "批次"]),
    "account_id": ("aap_provider_account", ["account", "账户"]),
}


def ref_scope(field, tables):
    """引用字段 → (父表, 关键词)。显式映射优先，未知字段按 `_id` 词干回查 DDL。"""
    if field in REF_PARENT:
        return REF_PARENT[field]
    stem = field[:-3] if field.endswith("_id") else field
    for c in (stem, "aap_" + stem, "aap_" + stem + "_asset", "aap_quote_" + stem):
        if c in tables:
            return c, [stem, stem.replace("_", "")]
    return None, [stem, stem.replace("_", "")]


def find_ref_evidence(hay, field, tables):
    """只认「与被引用实体同域」的存在性校验证据（否则 requireProvider() 这类会假判 validated）。"""
    tbl, kws = ref_scope(field, tables)
    ev = []
    if tbl and re.search(r"\b(?:from|join)\s+" + tbl + r"\b", hay, re.I):
        ev.append("查询 %s" % tbl)
    for m in re.finditer(r"\b(require|ensure|assert|check|load|find|resolve)(\w*)\s*\(", hay):
        name = (m.group(1) + m.group(2)).lower()
        if any(k.lower() in name for k in kws):
            ev.append("助手 %s%s()" % (m.group(1), m.group(2)))
    # ORM 式存在性查询：接收者名含实体关键词 且 方法以查询动词开头（如 credentialMapper.selectOneById(…)）
    for m in re.finditer(r"\b(\w+)\s*\.\s*(select|find|query|load|get|exists|count)(\w*)\s*\(", hay):
        recv = m.group(1).lower()
        if any(k.lower() in recv for k in kws if len(k) > 2):
            ev.append("ORM 查询 %s.%s%s()" % (m.group(1), m.group(2), m.group(3)))
    for line in hay.split("\n"):
        low = line.lower()
        if ("不存在" in line or "not found" in low or "notfound" in low):
            if any(k.lower() in low for k in kws):
                ev.append("校验消息：%s" % line.strip()[:60])
                break
    return ev


def judge_validation(root, routes, endpoint_id, method, path, field, tables):
    """→ (判定, 证据)；判定 ∈ {validated, unvalidated, unconsumed, annotation, unknown}

    分级纪律（坑 111）：**「契约声明但实现未接收」与「已接收但未校验」分开**——
    前者多半是生成物侧多声明，后者才是客户端传参被忽略/孤儿引用可写入。
    """
    hit = routes.get(norm_key(method, path))
    if not hit:
        return "unknown", "路由未定位（%s）" % norm_key(method, path)
    cfile, mname, body = hit
    svc = []                     # [(形参名, 方法体)]
    src = read(cfile)
    fields = {v: t for t, v in re.findall(r"(\w+Service)\s+(\w+)\s*[;=]", src)}
    for cm in re.finditer(r"(\w+)\s*\.\s*(\w+)\s*\(", body):
        recv, called = cm.group(1), cm.group(2)
        cls = fields.get(recv)
        if not cls:
            continue
        for p in java_files(root, "main"):
            if os.path.basename(p) != cls + ".java":
                continue
            ms = methods_of(strip_comments_java(read(p)))
            if called in ms:
                sig, b = ms[called]
                svc.append((param_names(sig), b))
    if not svc:
        return "unknown", "服务方法体未能定位（%s#%s）" % (os.path.basename(cfile), mname)
    hay = body + "\n" + "\n".join(b for _p, b in svc)
    cam = camel(field)
    svc_src = "\n".join(b for _p, b in svc)
    # ① 被消费？只认「请求对象/请求形参」的读取：`<request-like>.camel` 或 camel 本身是形参名
    #    （不能用 principal.providerId() / credential.getProviderId() 这类「同名字段」冒充，坑 111-①）
    REQ_HOLDER = re.compile(r"^(command|cmd|body|request|req|payload|form|input|dto|save|create|update|param)s?$", re.I)
    consumed = False
    for params, b in svc:
        if cam in params and re.search(r"\b" + cam + r"\b", b):
            consumed = True
            break
        for p in params:
            if not REQ_HOLDER.match(p):
                continue
            if re.search(r"\b" + re.escape(p) + r"\s*\.\s*" + cam + r"\b", b):
                consumed = True
                break
        if consumed:
            break
    # ② 同域存在性校验证据
    ev = find_ref_evidence(hay, field, tables)
    if ev:
        return "validated", "%s#%s → %s" % (os.path.basename(cfile), mname, " / ".join(ev))
    # ③ 只作为 jsonb/审计快照键写入（`.put("field"` / `Map.of(…"field"`）→ 非引用列，不属引用校验范畴
    if re.search(r"\.\s*put\s*\(\s*\"%s\"" % re.escape(field), svc_src) or \
       re.search(r"Map\.of\w*\([^;]{0,200}?\"%s\"" % re.escape(field), svc_src):
        return "annotation", "%s#%s（仅作为快照/审计键写入，非引用列）" % (os.path.basename(cfile), mname)
    if not consumed:
        return "unconsumed", "%s#%s（请求字段在写入路径零读取 → 实现未接收）" % (os.path.basename(cfile), mname)
    return "unvalidated", "%s#%s（已消费但无与 %s 同域的存在性校验证据）" % (os.path.basename(cfile), mname, field)


def parse_test_evidence(root):
    """→ (引用不存在类断言数, 命中文件列表)"""
    pat = re.compile(r"E-1406|不存在|notFound", re.I)
    hits, files = 0, set()
    for p in java_files(root, "test"):
        t = read(p)
        for line in t.split("\n"):
            if "assert" in line and pat.search(line):
                hits += 1
                files.add(os.path.basename(p))
    return hits, sorted(files)


# ---------------------------------------------------------------- 主流程
def run(root):
    del PASS[:], FAIL[:], INFO[:]
    tables, fk_count = parse_ddl(root)
    fks, policy = parse_er(root)
    refs, ref_field_count = parse_request_refs(root)
    routes = parse_controllers(root)
    t_hits, t_files = parse_test_evidence(root)

    id_cols = sum(1 for t in tables.values() for c in t if c.endswith("_id"))
    # ---- 定位率（坑 87：先看「解析到几条」再看「是否全绿」）
    ep_file = os.path.join(root, "docs", "backend", "endpoints.json")
    ep_keys = set()
    if os.path.isfile(ep_file):
        for e in json.load(open(ep_file, encoding="utf-8"))["endpoints"]:
            ep_keys.add(norm_key(e["method"], e["path"]))
    located = ep_keys & set(routes)
    if ep_keys and len(located) == len(ep_keys):
        ok("A0g", "控制器路由定位率 %d/%d（全清单已定位）" % (len(located), len(ep_keys)))
    else:
        bad("A0g", "控制器路由定位率仅 %d/%d → 未定位：%s"
            % (len(located), len(ep_keys), ", ".join(sorted(ep_keys - set(routes))[:10])))
    # ---- 正向对照（> 0，坑 46/75）
    for tag, n, what in (("A0a", len(tables), "DDL 表"), ("A0b", id_cols, "DDL *_id 列"),
                         ("A0c", len(fks), "ER FK* 声明"), ("A0d", ref_field_count, "请求体 *_id 字段"),
                         ("A0e", len(routes), "控制器路由"), ("A0f", t_hits, "测试引用不存在断言")):
        if n > 0:
            ok(tag, "解析到 %d 个%s（正向对照）" % (n, what))
        else:
            bad(tag, "解析到 0 个%s → 判解析器失效，不得判一致（坑 46）" % what)

    # ---- A1：ER 每条 FK* 列在 DDL 对应表里存在
    missing_col, missing_tbl = [], []
    for tbl, col, tgt in fks:
        if tbl not in tables:
            missing_tbl.append("%s（ER 表未在 DDL 找到）" % tbl)
            continue
        if not tables[tbl]:
            info("A1p", "%s 是分区表（create table … partition of …，无列定义）→ 跳过列存在性检查" % tbl)
            continue
        if col not in tables[tbl]:
            missing_col.append("%s.%s" % (tbl, col))
        if tgt and tgt not in tables:
            missing_tbl.append("%s → %s（目标表未在 DDL 找到）" % (tbl, tgt))
    if missing_col:
        bad("A1", "ER 声明为 FK* 但 DDL 无该列 %d 处：%s" % (len(missing_col), ", ".join(missing_col[:8])))
    else:
        ok("A1", "ER 的 %d 条 FK* 声明在 DDL 对应表里全部存在" % len(fks))
    if missing_tbl:
        bad("A1b", "ER 表/目标表在 DDL 未找到 %d 处：%s" % (len(missing_tbl), ", ".join(missing_tbl[:8])))
    else:
        ok("A1b", "ER 的 FK* 所属表与目标表全部在 DDL 里存在")

    # ---- A2：DB 级 FK 策略：ER 声明「不建 DB 级 FK」⇔ DDL FK 约束 = 0
    if policy and fk_count == 0:
        ok("A2", "ER 声明「逻辑外键，不建 DB 级 FK」且 DDL 实测 FK 约束 = 0（双源一致）")
    elif policy and fk_count > 0:
        bad("A2", "ER 声明不建 DB 级 FK，但 DDL 实测 %d 处 references/foreign key" % fk_count)
    elif not policy:
        bad("A2", "DDL 零 FK 约束，而 ER/设计文档未声明该策略（策略无留痕）")
    else:
        ok("A2", "DDL FK 约束 = 0")

    # ---- A3：请求体引用字段是否在 ER 里有 FK* 声明
    er_pairs = {(t, c) for t, c, _ in fks}
    er_cols = {c for _t, c, _g in fks}
    undeclared = sorted({f for _i, _m, _p, f, _rm in refs if f not in er_cols})
    if undeclared:
        bad("A3", "请求体引用了 %d 个未在 ER 声明为 FK* 的字段：%s" % (len(undeclared), ", ".join(undeclared)))
    else:
        ok("A3", "请求体引用字段 %d 个全部在 ER 有 FK* 声明" % len({f for _i, _m, _p, f, _rm in refs}))
    # 逐端点明细（信息项）
    for eid, m, p, fld, rm in refs:
        info("A3i", "%s %s %s 引用 %s（%s）" % (eid, m, p, fld, rm))

    # ---- A4：写入路径的父行存在性校验
    verdicts = []
    for eid, m, p, fld, _rm in refs:
        v, ev = judge_validation(root, routes, eid, m, p, fld, tables)
        verdicts.append((eid, m, p, fld, v, ev))
        info("A4i", "%s %s %s 字段=%s → %s（%s）" % (eid, m, p, fld, v, ev))
    unv = [v for v in verdicts if v[4] == "unvalidated"]
    unk = [v for v in verdicts if v[4] == "unknown"]
    val = [v for v in verdicts if v[4] == "validated"]
    unc = [v for v in verdicts if v[4] == "unconsumed"]
    ann = [v for v in verdicts if v[4] == "annotation"]
    if unv:
        bad("A4", "%d/%d 处请求体引用字段**已消费但无同域存在性校验**（可写入指向不存在父行的引用）：%s"
            % (len(unv), len(verdicts), ", ".join("%s(%s)" % (v[0], v[3]) for v in unv)))
    else:
        ok("A4", "%d 处已消费的请求体引用字段均有同域存在性校验证据" % len(val))
    if unc:
        info("A4c", "**契约声明但实现未接收** %d 处（分级：生成物/实现侧多声明，非运行时缺陷）：%s"
             % (len(unc), ", ".join("%s(%s)" % (v[0], v[3]) for v in unc)))
    if ann:
        info("A4d", "非引用列（仅作快照/审计键写入）%d 处：%s"
             % (len(ann), ", ".join("%s(%s)" % (v[0], v[3]) for v in ann)))
    if unk:
        info("A4b", "未能静态判定 %d 处：%s" % (len(unk), ", ".join("%s(%s)" % (v[0], v[3]) for v in unk)))

    # ---- A5：测试背书（对「引用不存在」的断言）
    if t_hits > 0:
        ok("A5", "测试对「引用不存在」有 %d 处断言（覆盖 %d 个测试类，正向对照）" % (t_hits, len(t_files)))
    else:
        bad("A5", "测试对「引用不存在」零断言 → 引用校验无测试背书")

    # ---- A6：DDL 里有、ER 未记录的 *_id 列（信息项）
    ddl_id_cols = {(t, c) for t, cols in tables.items() for c in cols if c.endswith("_id")}
    undocumented = sorted({c for _t, c in ddl_id_cols if c not in er_cols})
    info("A6", "DDL 里 ER 未声明为 FK* 的 *_id 列名 %d 个：%s" % (len(undocumented), ", ".join(undocumented)))

    return {
        "tables": len(tables), "id_cols": id_cols, "er_fks": len(fks), "fk_constraints": fk_count,
        "request_refs": len(refs), "routes": len(routes), "test_asserts": t_hits,
        "verdicts": verdicts, "undeclared": undeclared, "policy": policy,
    }


def report(stats, out=sys.stdout):
    for tag, msg in PASS:
        out.write("[PASS] %-5s %s\n" % (tag, msg))
    for tag, msg in FAIL:
        out.write("[FAIL] %-5s %s\n" % (tag, msg))
    for tag, msg in INFO:
        out.write("[INFO] %-5s %s\n" % (tag, msg))
    out.write("\n汇总：PASS %d / FAIL %d / INFO %d\n" % (len(PASS), len(FAIL), len(INFO)))
    out.write("关键计数：DDL 表 %d · *_id 列 %d · DB 级 FK 约束 %d · ER FK* 声明 %d · 请求体引用端点 %d · 路由 %d · 测试断言 %d\n"
              % (stats["tables"], stats["id_cols"], stats["fk_constraints"], stats["er_fks"],
                 stats["request_refs"], stats["routes"], stats["test_asserts"]))
    return len(FAIL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT_DEFAULT)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.root))
    stats = run(a.root)
    n = report(stats)
    sys.exit(1 if n else 0)


# ---------------------------------------------------------------- 负向自测
def selftest(fixdir):
    """每个判定分支一条反例 + 正向对照 + 空夹具变红 + 注入缺陷判别力 + 零写副作用。"""
    res = []

    def check(name, cond):
        res.append((name, bool(cond)))

    def fail_tags(root):
        run(root)
        return [t for t, _m in FAIL]

    good = os.path.join(fixdir, "compliant")
    # --- 正向对照：合规夹具 rc=0 且 FAIL 0
    ft = fail_tags(good)
    check("S1 合规夹具 FAIL 0", ft == [])
    st = run(good)
    check("S2 合规夹具解析到 2 表 / 2 条 ER FK* / 1 个请求体引用",
          st["tables"] == 2 and st["er_fks"] == 2 and st["request_refs"] == 1)
    check("S3 合规夹具判定 validated", st["verdicts"][0][4] == "validated")

    # --- 空夹具必须变红（防空转，坑 98）
    empty = os.path.join(fixdir, "empty")
    et = fail_tags(empty)
    check("S4 空夹具点名 A0a", "A0a" in et)
    check("S5 空夹具点名 A0d", "A0d" in et)

    # --- 注入缺陷（每个分支一条；断言 FAIL 集合恰好新增目标断言，坑 82/90/93/94）
    def mutate(src, old, new, dst):
        t = read(src)
        if old not in t:
            return False
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(t.replace(old, new))
        return True

    import shutil

    def clone(dst):
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(good, dst)

    inj = os.path.join(fixdir, "inj")
    # I1: 改 ER 的 FK* 列名（DDL 无该列）→ A1 转红
    clone(inj)
    anchor_ok = mutate(os.path.join(inj, "docs/backend/01-ER数据模型.md"),
                       "`child_ref FK*`", "`child_ref_renamed FK*`",
                       os.path.join(inj, "docs/backend/01-ER数据模型.md"))
    check("S6 I1 注入锚点命中", anchor_ok)
    nt = fail_tags(inj)
    check("S7 I1 恰好新增 A1", set(nt) - set(ft) == {"A1"})

    # I2: 在 DDL 里加 references → A2 转红
    clone(inj)
    anchor_ok = mutate(os.path.join(inj, "aap-server/src/main/resources/db/migration/V1__baseline.sql"),
                       "child_ref bigint", "child_ref bigint references parent(id)",
                       os.path.join(inj, "aap-server/src/main/resources/db/migration/V1__baseline.sql"))
    check("S8 I2 注入锚点命中", anchor_ok)
    nt = fail_tags(inj)
    check("S9 I2 恰好新增 A2", set(nt) - set(ft) == {"A2"})

    # I3: 移除服务方法里的「父表存在性查询 + 抛出」块 → A4 转红
    # （判据是「同域存在性校验证据」；只删 throw 不够，因为查询本身就是证据）
    clone(inj)
    anchor_ok = mutate(os.path.join(inj, "aap-server/src/main/java/demo/ChildService.java"),
                       '        Long found = jdbc.queryForObject("select id from parent where id = ?", Long.class, parentId);\n'
                       '        if (found == null) {\n'
                       '            throw new ApiException(ErrorCode.E_1406, "父行不存在");\n'
                       '        }\n',
                       '        Long found = null;\n',
                       os.path.join(inj, "aap-server/src/main/java/demo/ChildService.java"))
    check("S10 I3 注入锚点命中", anchor_ok)
    nt = fail_tags(inj)
    check("S11 I3 恰好新增 A4", set(nt) - set(ft) == {"A4"})

    # I4: 请求体新增未声明的引用字段 → A3 转红
    # 锚点必须落在 properties 块内（坑 104：`"parent_id"` 首处是 required 数组 → 注入会破坏 JSON）
    # 注入名必须以 _id 结尾（与判据「引用字段 = *_id」同域，否则注入语义没变 → 空转通过，坑 90）
    clone(inj)
    anchor_ok = mutate(os.path.join(inj, "docs/backend/json-schema/requests/child-create.schema.json"),
                       '    "name": {',
                       '    "ghost_id": {\n      "type": "string"\n    },\n    "name": {',
                       os.path.join(inj, "docs/backend/json-schema/requests/child-create.schema.json"))
    check("S12 I4 注入锚点命中", anchor_ok)
    nt = fail_tags(inj)
    # 注入一个「清单未声明的引用字段」→ A3 转红；该幽灵字段在实现里零读取 → A4 只记 unconsumed（INFO，不判 FAIL）
    check("S13 I4 恰好新增 A3", set(nt) - set(ft) == {"A3"})

    # --- 零写副作用（脚本只读）
    before = {}
    for dirpath, _d, files in os.walk(good):
        for f in files:
            p = os.path.join(dirpath, f)
            before[p] = os.path.getsize(p)
    run(good)
    after = {p: os.path.getsize(p) for p in before}
    check("S14 零写副作用（夹具 size 全等）", before == after)

    npass = sum(1 for _n, c in res if c)
    for n, c in res:
        print("[%s] %s" % ("PASS" if c else "FAIL", n))
    print("\n自测汇总：PASS %d / %d" % (npass, len(res)))
    return 0 if npass == len(res) else 1


if __name__ == "__main__":
    main()
