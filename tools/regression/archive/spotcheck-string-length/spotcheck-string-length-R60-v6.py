#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R60 抽查 v4：字符串字段「长度上限 / 下限」跨源一致性（第三十四类可审计不变量）—— 只读。

为什么两套门禁都看不见：
  ① 契约测试把**真实响应**与 JSON Schema 比对；requests/*.schema.json 的 `maxLength`/`minLength`
     在**运行时不参与任何校验**（R57 已取证：json-schema-validator 是 <scope>test</scope>、main 零引用）
     → 「schema 声明长度约束、实现不校验」对全部 204 例不可见；
  ② 覆盖门禁只比「方法 + 路径」注册表；
  ③ openapi 与客户端 TS 不被任何测试读取 / 执行。

真源六处：
  D = DDL `varchar(n)` 列（列名 → 宽度集合 / 列类型 / NOT NULL）  S = requests/*.schema.json 的 maxLength/minLength
  E = endpoints.json 的 request_model → 端点            I = 实现字段级注解 + 服务层同域 length()/isBlank() 检查
  T = 测试超长构造                                       M = md 清单长度措辞（信息项）

判据修正史（v1→v4，**每一条都是判据错、不是期望值错**，逐条人工回查实现源码后改判据）：
  ① `@NotBlank`/`@NotEmpty` ≡ `minLength >= 1` → v1 把 `auth-wechat-login.code(minLength=1)` 误判 FAIL；
  ② DDL 兜底必须分列类型：`text` 列**无**长度上限 → 超长只**静默接受**，只有 `varchar(n)` 才撞库 500；
  ③ 注解实参解析必须**括号配对**（`[^)]*` 被实参内层 `)` 截断 → v2 漏收 3 个 @Size，报出 3 条假 FAIL）；
  ④ 服务层证据必须**同域**（坑 125）：`name.length()` / `name.isEmpty()` 出现在别的 Service 或别的
     局部变量上，不能当 `quote-create.name` 的证据。判据 = 被检查的 token 必须是**所在方法的形参**，
     或**请求对象取值**（`command.x()` / 别名）；否则只记**弱证据**（信息项），不计入覆盖。

已知限制（诚实标注）：实现侧字段名多为 camelCase（`overrideReason`）而 schema 为 snake_case
（`override_reason`）→ 按名字匹配**收不到** camelCase 别名的长度校验（只会造成「多报 FAIL」方向，不会漏报）；
每条 FAIL 均已人工回查实现源码确认。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("E:/workspaces/hioas/hioas-aap-001")
MIG = ROOT / "aap-server/src/main/resources/db/migration"
REQ = ROOT / "docs/backend/json-schema/requests"
MOD = ROOT / "docs/backend/json-schema/models"
EPF = ROOT / "docs/backend/endpoints.json"
MAIN = ROOT / "aap-server/src/main/java"
TEST = ROOT / "aap-server/src/test/java"
MD = ROOT / "docs/backend/02-API接口模型清单.md"

GENERIC = {"code", "name", "type", "status", "title", "remark", "content", "key", "value", "note"}
REQ_RECV = ("command", "request", "body", "cmd", "payload", "form", "dto", "input", "req")
CONTROL = {"if", "while", "for", "switch", "catch", "synchronized", "try", "else", "do", "return", "assert"}

fails, infos, passes = [], [], []


def fail(tag, msg):
    fails.append("[FAIL] %s %s" % (tag, msg))


def info(tag, msg):
    infos.append("[INFO] %s %s" % (tag, msg))


def ok(tag, msg):
    passes.append("[PASS] %s %s" % (tag, msg))


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(p):
    t = read(p)
    if not t.strip():
        return None
    try:
        return json.loads(t)
    except ValueError:
        return None


def match_paren(text, i):
    if i >= len(text) or text[i] != "(":
        return -1
    depth, j = 0, i
    while j < len(text):
        c = text[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def match_paren_back(text, j):
    """text[j] == ')' → 返回配对 '(' 的下标（向后扫描，坑 55/63）。"""
    if j >= len(text) or text[j] != ")":
        return -1
    depth, k = 0, j
    while k >= 0:
        c = text[k]
        if c == ")":
            depth += 1
        elif c == "(":
            depth -= 1
            if depth == 0:
                return k
        k -= 1
    return -1


def split_top(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "(<[":
            depth += 1
        elif ch in ")>]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def method_params_at(src, idx):
    """返回 idx 所在**方法体**的形参名集合（括号配对 + 花括号配对；排除 if/while 等控制块）。"""
    depth, stack = 0, []
    i = 0
    while i < len(src) and i <= idx:
        c = src[i]
        if c == "{":
            stack.append(i)
        elif c == "}" and stack:
            stack.pop()
        i += 1
    if not stack:
        return set()
    body = stack[-1]
    k = body - 1
    while k >= 0 and src[k] in " \t\r\n":
        k -= 1
    # 跳过 throws ...
    tail = src[max(0, body - 200):body]
    tm = re.search(r"throws\s+[\w,.\s]+$", tail)
    if tm:
        k = max(0, body - 200) + tm.start() - 1
        while k >= 0 and src[k] in " \t\r\n":
            k -= 1
    if k < 0 or src[k] != ")":
        return set()
    open_i = match_paren_back(src, k)
    if open_i < 0:
        return set()
    # 方法名前的词不能是控制关键字
    name_m = re.search(r"([A-Za-z_]\w*)\s*$", src[:open_i])
    if not name_m or name_m.group(1) in CONTROL:
        return set()
    names = set()
    for p in split_top(src[open_i + 1: k]):
        ids = re.findall(r"[A-Za-z_]\w*", p)
        if ids:
            names.add(ids[-1])
    return names


LEN_CHECK = re.compile(r"([a-zA-Z_][\w.]*)\s*(?:\.\s*trim\s*\(\s*\))?\s*\.\s*length\s*\(\s*\)\s*"
                       r"([<>]=?)\s*([A-Za-z_][A-Za-z0-9_]*|\d+)")
BLANK_CHECK = re.compile(r"([a-zA-Z_][\w.]*)\s*\.\s*(isBlank|isEmpty)\s*\(\s*\)")
REQ_REF = re.compile(r"\b(%s)\.([a-z_][a-z0-9_]*)\s*\(\s*\)" % "|".join(REQ_RECV))
ALIAS = re.compile(r"(?:String|var)\s+([a-z_][a-z0-9_]*)\s*=\s*\b(%s)\.([a-z_][a-z0-9_]*)\s*\(\s*\)"
                   % "|".join(REQ_RECV))


# ---------------------------------------------------------------- D
def parse_ddl():
    tables, notnull, widths, kinds = {}, {}, {}, {}
    for f in sorted(MIG.glob("*.sql")) if MIG.is_dir() else []:
        src = read(f)
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)\s*\((.*?)\n\s*\)\s*;",
                             src, re.S | re.I):
            tbl, body = m.group(1).lower(), m.group(2)
            cols = tables.setdefault(tbl, {})
            nn = notnull.setdefault(tbl, set())
            for line in body.splitlines():
                line = line.split("--")[0].strip().rstrip(",")
                cm = re.match(r"^([a-z_][a-z0-9_]*)\s+(.*)$", line, re.I)
                if not cm:
                    continue
                col, rest = cm.group(1).lower(), cm.group(2)
                vm = re.search(r"(?:varchar|character\s+varying)\s*\(\s*(\d+)\s*\)", rest, re.I)
                if vm:
                    cols[col] = int(vm.group(1))
                    widths.setdefault(col, set()).add(int(vm.group(1)))
                    kinds[col] = "varchar"
                elif re.match(r"^text\b", rest, re.I):
                    kinds.setdefault(col, "text")
                if re.search(r"\bnot\s+null\b", rest, re.I):
                    nn.add(col)
        for m in re.finditer(r"alter\s+table\s+(\w+)\s+add\s+column\s+(?:if\s+not\s+exists\s+)?"
                             r"(\w+)\s+(?:varchar|character\s+varying)\s*\(\s*(\d+)\s*\)", src, re.I):
            tbl, col, w = m.group(1).lower(), m.group(2).lower(), int(m.group(3))
            tables.setdefault(tbl, {})[col] = w
            widths.setdefault(col, set()).add(w)
            kinds[col] = "varchar"
    return tables, notnull, widths, kinds


# ---------------------------------------------------------------- S
def parse_schema_file(path, seen=None):
    seen = seen or set()
    out = []
    data = read_json(path)
    if not isinstance(data, dict):
        return out
    props = data.get("properties")
    if not isinstance(props, dict):
        return out
    for name, spec in props.items():
        if not isinstance(spec, dict):
            continue
        mx, mn = spec.get("maxLength"), spec.get("minLength")
        if mx is not None or mn is not None:
            out.append((name, mx, mn))
        ref = None
        if isinstance(spec.get("items"), dict):
            ref = spec["items"].get("$ref")
        elif "$ref" in spec:
            ref = spec.get("$ref")
        if ref and not str(ref).startswith("#"):
            tgt = (Path(path).parent / str(ref)).resolve()
            if tgt not in seen and tgt.exists():
                seen.add(tgt)
                for sub in parse_schema_file(tgt, seen):
                    out.append(("%s.%s" % (name, sub[0]), sub[1], sub[2]))
    return out


def parse_requests():
    res = {}
    for f in sorted(REQ.glob("*.schema.json")) if REQ.is_dir() else []:
        res[f.name[: -len(".schema.json")]] = parse_schema_file(f, {f.resolve()})
    return res


def parse_models_maxlength():
    n, files = 0, 0
    for f in sorted(MOD.glob("*.schema.json")) if MOD.is_dir() else []:
        c = len(re.findall(r'"maxLength"', read(f)))
        if c:
            files += 1
        n += c
    return n, files


# ---------------------------------------------------------------- E
def parse_endpoints():
    data = read_json(EPF) or {}
    eps = data.get("endpoints") or []
    by_model = {}
    for e in eps:
        if isinstance(e, dict) and e.get("request_model"):
            by_model.setdefault(e["request_model"], []).append(e.get("id") or "?")
    return by_model, len(eps)


# ---------------------------------------------------------------- I
def java_sources(base):
    return sorted([p for p in base.rglob("*.java") if p.is_file()]) if base.is_dir() else []


def parse_impl():
    size_max, size_min, pattern_len, ann_fields = {}, {}, {}, {}
    size_max_files, size_min_files, pattern_len_files, nb_files = {}, {}, {}, {}
    n_notblank, consts = 0, {}
    per_file = {}
    for p in java_sources(MAIN):
        src = read(p)
        for m in re.finditer(r"([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*;", src):
            consts.setdefault(m.group(1), int(m.group(2)))
        for m in re.finditer(r"@(\w+)", src):
            ann, j = m.group(1), m.end()
            args = ""
            while j < len(src) and src[j] in " \t\r\n":
                j += 1
            if j < len(src) and src[j] == "(":
                close = match_paren(src, j)
                if close < 0:
                    continue
                args, j = src[j + 1: close], close + 1
            k = j
            while True:
                while k < len(src) and src[k] in " \t\r\n":
                    k += 1
                if k < len(src) and src[k] == "@":
                    nm = re.match(r"@(\w+)", src[k:])
                    if not nm:
                        break
                    k += nm.end()
                    while k < len(src) and src[k] in " \t\r\n":
                        k += 1
                    if k < len(src) and src[k] == "(":
                        cl = match_paren(src, k)
                        if cl < 0:
                            break
                        k = cl + 1
                    continue
                break
            fm = re.match(r"String\s+([a-z_][a-z0-9_]*)", src[k:])
            if not fm:
                continue
            field = fm.group(1)
            ann_fields.setdefault(field, set()).add(ann)
            if ann == "Size":
                mx = re.search(r"max\s*=\s*(\d+)", args)
                mn = re.search(r"min\s*=\s*(\d+)", args)
                if mx:
                    size_max[field] = int(mx.group(1))
                    size_max_files.setdefault(field, []).append((str(p), int(mx.group(1))))
                if mn:
                    size_min[field] = int(mn.group(1))
                    size_min_files.setdefault(field, []).append((str(p), int(mn.group(1))))
            elif ann == "Pattern":
                qs = [int(x) for x in re.findall(r"\{(\d+)(?:,\d*)?\}", args)]
                if qs:
                    pattern_len[field] = max(qs)
                    pattern_len_files.setdefault(field, []).append((str(p), max(qs)))
            elif ann in ("NotBlank", "NotEmpty"):
                n_notblank += 1
                nb_files.setdefault(field, []).append(str(p))
        refs = set(m.group(2) for m in REQ_REF.finditer(src))
        alias_map = {}
        for m in ALIAS.finditer(src):
            refs.add(m.group(3))
            alias_map[m.group(1)] = m.group(3)
        checks, blanks = [], []
        for m in LEN_CHECK.finditer(src):
            raw, op, bound = m.group(1), m.group(2), m.group(3)
            token = raw.split(".")[-1]
            val = int(bound) if bound.isdigit() else consts.get(bound)
            checks.append((token, op, val, m.start(), raw))
        for m in BLANK_CHECK.finditer(src):
            raw = m.group(1)
            blanks.append((raw.split(".")[-1], m.start(), raw))
        per_file[str(p)] = dict(refs=refs, alias_map=alias_map, checks=checks, blanks=blanks, src=src)
    return dict(size_max=size_max, size_min=size_min, pattern_len=pattern_len,
                ann_fields=ann_fields, n_notblank=n_notblank, per_file=per_file,
                size_max_files=size_max_files, size_min_files=size_min_files,
                pattern_len_files=pattern_len_files, nb_files=nb_files)


STOP_TOKENS = {"create", "update", "save", "release", "approve", "reject", "send", "login",
               "config", "list", "detail", "item", "profile", "fetch", "get"}


def domain_of(model):
    """请求模型 → 归属域关键词（用于把证据限制在**同一域**的文件里，坑 125）。"""
    toks = [t for t in model.split("-") if t not in STOP_TOKENS]
    return toks[0] if toks else (model.split("-")[0] if model else None)


def dom_ok(fname, domain):
    if not domain:
        return True
    return domain in Path(fname).name.lower().replace("_", "")


def _scoped(src, alias_map, raw, pos):
    """按**检查表达式自身**的接收者定作用域（坑 125 同域纪律；v4 的「字段名在文件里出现过」判据
    会把别的局部变量 `name.isEmpty()` 当成 `quote-create.name` 的证据 → 假 PASS）：

      'req'     = 表达式接收者是请求对象（`command.name`）或请求取值别名（`String x = command.name()`）
      'param'   = 表达式是所在方法的形参（`validate(String title, …)` 内的 `title.length()`）
      'foreign' = 其它（局部变量从别处赋值 / 别的实体 getter）→ 不计入覆盖
    """
    if "." in raw and raw.split(".")[0] in REQ_RECV:
        return "req"
    last = raw.split(".")[-1]
    if last in alias_map:
        return "req"
    if last in method_params_at(src, pos):
        return "param"
    return "foreign"


def covers_max(field, limit, impl, domain=None):
    strong, weak = [], []
    for f, v in impl["size_max_files"].get(field, []):
        if v == limit:
            x = "@Size(max=%d)@%s" % (limit, Path(f).name)
            (strong if dom_ok(f, domain) else weak).append(x if dom_ok(f, domain) else "弱:" + x)
    for f, v in impl["pattern_len_files"].get(field, []):
        if v == limit:
            x = "@Pattern 量词 %d@%s" % (limit, Path(f).name)
            (strong if dom_ok(f, domain) else weak).append(x if dom_ok(f, domain) else "弱:" + x)
    for f, d in impl["per_file"].items():
        for token, op, val, pos, raw in d["checks"]:
            if token == field and op in (">", ">=") and val == limit:
                sc = _scoped(d["src"], d["alias_map"], raw, pos)
                (strong if (sc != "foreign" and dom_ok(f, domain)) else weak).append(
                    "%s%s length(%s) %s %s" % ("弱:" if (sc == "foreign" or not dom_ok(f, domain)) else "",
                                               Path(f).name, sc, token, op))
    return (bool(strong), "; ".join(sorted(set(strong + weak))), bool(strong))


def covers_min(field, limit, impl, domain=None):
    strong, weak = [], []
    for f, v in impl["size_min_files"].get(field, []):
        if v == limit:
            x = "@Size(min=%d)@%s" % (limit, Path(f).name)
            (strong if dom_ok(f, domain) else weak).append(x if dom_ok(f, domain) else "弱:" + x)
    if limit <= 1:
        for f in impl["nb_files"].get(field, []):
            x = "@NotBlank@%s" % Path(f).name
            (strong if dom_ok(f, domain) else weak).append(x if dom_ok(f, domain) else "弱:" + x)
    for f, d in impl["per_file"].items():
        if limit <= 1:
            for token, pos, raw in d["blanks"]:
                if token == field:
                    sc = _scoped(d["src"], d["alias_map"], raw, pos)
                    (strong if (sc != "foreign" and dom_ok(f, domain)) else weak).append(
                        "%s%s blank(%s) %s" % ("弱:" if (sc == "foreign" or not dom_ok(f, domain)) else "",
                                               Path(f).name, sc, token))
        for token, op, val, pos, raw in d["checks"]:
            if token == field and op in ("<", "<=") and val == limit:
                sc = _scoped(d["src"], d["alias_map"], raw, pos)
                (strong if (sc != "foreign" and dom_ok(f, domain)) else weak).append(
                    "%s%s length(%s) %s %s" % ("弱:" if (sc == "foreign" or not dom_ok(f, domain)) else "",
                                               Path(f).name, sc, token, op))
    return (bool(strong), "; ".join(sorted(set(strong + weak))), bool(strong))


def has_any_length_constraint(field, impl):
    if impl["size_max"].get(field) is not None or impl["pattern_len"].get(field) is not None:
        return True
    if impl["ann_fields"].get(field, set()) & {"Size", "Pattern", "NotBlank", "NotEmpty"}:
        return True
    for _f, d in impl["per_file"].items():
        if any(t == field for t, _p, _r in d["blanks"]) or any(t == field for t, _o, _v, _p, _r in d["checks"]):
            return True
    return False


# ---------------------------------------------------------------- T
def parse_tests():
    n, hits = 0, []
    for p in java_sources(TEST):
        src = read(p)
        for m in re.finditer(r'"(?:[^"\\]|\\.)*"\s*\.\s*repeat\s*\(\s*(\d+)\s*\)', src):
            n += 1
            hits.append("%s:%d repeat(%s)" % (p.name, src[: m.start()].count("\n") + 1, m.group(1)))
    return n, hits


# ---------------------------------------------------------------- main
def main():
    tables, notnull, widths, kinds = parse_ddl()
    reqs = parse_requests()
    by_model, ep_count = parse_endpoints()
    impl = parse_impl()
    mdl_n, mdl_files = parse_models_maxlength()
    t_n, t_hits = parse_tests()
    md_txt = read(MD)

    ddl_cols = sum(len(v) for v in tables.values())
    maxl = [(m, f, mx, mn) for m, fl in reqs.items() for (f, mx, mn) in fl]

    if ddl_cols > 0:
        ok("A0a", "DDL 解析到 %d 张表 / %d 个 varchar 列（宽度种类 %d）" % (len(tables), ddl_cols, len(widths)))
    else:
        fail("A0a", "DDL 解析到 0 个 varchar 列 —— 解析器失效或夹具缺失（坑 46）")
    if maxl:
        ok("A0b", "request schema 解析到 %d 个带长度约束字段（maxLength %d / minLength %d，%d 个模型，含 $ref 跟进）"
           % (len(maxl), len([1 for _m, _f, x, _y in maxl if x is not None]),
              len([1 for _m, _f, _x, y in maxl if y is not None]), len([m for m in reqs if reqs[m]])))
    else:
        fail("A0b", "request schema 解析到 0 个 maxLength/minLength 字段 —— 解析器失效或夹具缺失")
    if impl["size_max"] and impl["size_min"]:
        ok("A0c", "实现解析到 @Size(max) %d / @Size(min) %d / @Pattern 量词 %d / 含长度检查文件 %d"
           % (len(impl["size_max"]), len(impl["size_min"]), len(impl["pattern_len"]),
              len([1 for _f, d in impl["per_file"].items() if d["checks"]])))
    else:
        fail("A0c", "实现 @Size(max)=%d / @Size(min)=%d —— 注解解析器失效（v2 曾在此漏收）"
             % (len(impl["size_max"]), len(impl["size_min"])))
    if impl["n_notblank"] > 0:
        ok("A0f", "实现解析到 @NotBlank/@NotEmpty %d 处（minLength>=1 的等价证据源）" % impl["n_notblank"])
    else:
        fail("A0f", "实现解析到 0 处 @NotBlank/@NotEmpty —— 下限判据的证据源失效（v1 假 FAIL 的根因）")
    n_param_scoped = sum(1 for _f, d in impl["per_file"].items()
                         for _t, _o, _v, pos, raw in d["checks"]
                         if _scoped(d["src"], d["alias_map"], raw, pos) == "param")
    if n_param_scoped > 0:
        ok("A0g", "服务层长度检查中 %d 处被判定为「所在方法形参」（同域强证据源）" % n_param_scoped)
    else:
        fail("A0g", "0 处长度检查被判定为形参作用域 —— 同域判据失效（坑 125）")
    if ep_count > 0:
        ok("A0d", "endpoints.json 解析到 %d 条端点（%d 条声明 request_model）" % (ep_count, len(by_model)))
    else:
        fail("A0d", "endpoints.json 解析到 0 条端点 —— 解析器失效或夹具缺失")
    if t_n > 0:
        ok("A0e", "测试源解析到 %d 处超长/边界长度构造（repeat(N)）" % t_n)
    else:
        fail("A0e", "测试源解析到 0 处超长构造 —— 解析器失效或夹具缺失")

    # ---- A1/A2
    eq, ambiguous, over_wide, compared = [], [], [], 0
    for model, field, mx, mn in maxl:
        if mx is None or field not in widths:
            continue
        compared += 1
        ws = widths[field]
        if mx > max(ws):
            over_wide.append((model, field, mx, sorted(ws)))
        elif len(ws) == 1:
            (eq if mx == max(ws) else over_wide).append((model, field, mx, sorted(ws)))
        else:
            ambiguous.append((model, field, mx, sorted(ws)))
    if eq:
        ok("A1", "schema maxLength 与 DDL 同名列宽度**逐字段相等** %d 处：%s"
           % (len(eq), ", ".join("%s.%s=%d" % (m, f, x) for m, f, x, _w in eq)))
    if ambiguous:
        info("A1b", "DDL 同名列存在多宽度（归属不明，不作强断言）%d 处：%s"
             % (len(ambiguous), ", ".join("%s.%s(max=%d,DDL%s)" % (m, f, x, w) for m, f, x, w in ambiguous[:6])))
    if over_wide:
        for model, field, mx, ws in over_wide:
            fail("A2", "%s.%s 声明 maxLength=%d > DDL 同名列宽度 %s → 客户端可提交被库拒绝的值"
                 % (model, field, mx, ws))
    else:
        ok("A2", "无「schema maxLength > DDL 宽度」的越界放行（正向对照：已比对 %d 个同名 DDL 列）" % compared)

    # ---- A3
    enforced, hard, soft, weak_only = [], [], [], []
    for model, field, mx, mn in maxl:
        if mx is None:
            continue
        cov, ev, strong = covers_max(field, mx, impl, domain_of(model))
        if cov:
            (enforced if strong else weak_only).append((model, field, mx, ev))
            continue
        eps = ",".join(by_model.get(model, ["-"])[:3]) or "-"
        ws = widths.get(field)
        (hard if ws else soft).append((model, field, mx, min(ws) if ws else kinds.get(field, "无同名列"), eps))
    if enforced:
        ok("A3a", "schema 声明 maxLength 的字段中 **%d 个有同域强证据强制**：%s"
           % (len(enforced), ", ".join("%s.%s=%d(%s)" % (m, f, x, e) for m, f, x, e in enforced)))
    if weak_only:
        info("A3a2", "弱证据（同文件有检查但作用域非形参/请求取值，不计入覆盖）%d 个：%s"
             % (len(weak_only), ", ".join("%s.%s=%d(%s)" % (m, f, x, e) for m, f, x, e in weak_only)))
    for model, field, mx, w, eps in hard:
        fail("A3b", "%s.%s 声明 maxLength=%d 但实现侧零强制，且 DDL 同名列是 varchar(%d) → 超长(>%d) 撞库为 "
                    "**500 E-2001**，而契约承诺 400 E-1001（端点 %s）" % (model, field, mx, w, w, eps))
    for model, field, mx, kind, eps in soft:
        fail("A3c", "%s.%s 声明 maxLength=%d 但实现侧零强制，DDL 侧为 %s（无长度上限）→ 超长输入被**静默接受**，"
                    "契约声明的上限无效（端点 %s）" % (model, field, mx, kind, eps))
    if not hard and not soft:
        ok("A3d", "无「schema 声明 maxLength 而实现零强制」的字段")

    # ---- A4
    a4 = 0
    for field, n in sorted(impl["size_max"].items()):
        ws = widths.get(field)
        if ws and n > max(ws):
            fail("A4", "@Size(max=%d) 的字段 %s 对应 DDL 宽度 %s → 实现放行而库拒绝（500）" % (n, field, sorted(ws)))
        elif ws:
            a4 += 1
    ok("A4b", "实现 @Size(max=) 的字段中 %d 个对应 DDL 列宽 >= 声明上限（正向对照：有 DDL 同名列的 %d 个）"
       % (a4, len([1 for f in impl["size_max"] if f in widths])))

    # ---- A5
    min_declared, min_ok, min_bad = 0, [], []
    for model, field, mx, mn in maxl:
        if mn is None:
            continue
        min_declared += 1
        cov, ev, strong = covers_min(field, mn, impl, domain_of(model))
        (min_ok if cov else min_bad).append((model, field, mn, ev))
    if min_declared:
        if min_ok:
            ok("A5a", "schema 声明的 minLength 中 %d 个有实现侧下限校验：%s"
               % (len(min_ok), ", ".join("%s.%s>=%d(%s)" % (m, f, x, e) for m, f, x, e in min_ok)))
        for model, field, mn, _e in min_bad:
            fail("A5b", "%s.%s 声明 minLength=%d 但实现侧零下限校验 → 过短输入被接受（契约与实现不一致）"
                 % (model, field, mn))
    else:
        info("A5c", "request schema 未声明任何 minLength（无可判项）")

    # ---- A6
    req_names = {f.split(".")[-1]: (m, mx, mn) for m, fl in reqs.items() for (f, mx, mn) in fl}
    surface, collisions = [], []
    for tbl, cols in sorted(tables.items()):
        for col, w in sorted(cols.items()):
            if col not in req_names:
                continue
            _m, mx, _mn = req_names[col]
            if mx is not None or has_any_length_constraint(col, impl):
                continue
            rec = (tbl, col, w, _m, col in notnull.get(tbl, set()))
            (collisions if col in GENERIC else surface).append(rec)
    if surface:
        info("A6", "DDL varchar 列名命中请求字段、两侧均无长度约束 %d 处（弱证据·名字映射，超长 → 500 的潜在面）：%s"
             % (len(surface), ", ".join("%s.%s(%d%s←%s)" % (t, c, w, ",NN" if nn else "", m)
                                        for t, c, w, m, nn in surface[:8])))
    else:
        ok("A6b", "DDL varchar 列名命中请求字段的条目全部有长度约束（正向对照：请求字段名 %d 个）" % len(req_names))
    if collisions:
        info("A6c", "同名碰撞（通用列名，不判为漂移）%d 处：%s"
             % (len(collisions), ", ".join("%s.%s(%d←%s)" % (t, c, w, m) for t, c, w, m, _nn in collisions[:6])))

    # ---- A7/A8
    info("A7", "models/*.schema.json（响应侧）maxLength 共 %d 处 / %d 个文件 → 响应侧不声明长度上限"
         % (mdl_n, mdl_files))
    info("A8", "md 清单出现长度约束措辞 %d 处（信息项）"
         % len(re.findall(r"最多\s*\d+\s*[字符]|长度不得超过|maxLength", md_txt)))

    # ---- A9
    if t_n:
        ok("A9", "该不变量有测试守卫：超长构造 %d 处（%s）" % (t_n, ", ".join(t_hits[:5])))
    else:
        info("A9b", "测试源无超长构造 → 长度约束不被任何用例守卫（信息项）")

    print("=== R60 抽查：字符串长度约束跨源一致性（第三十四类可审计不变量）===")
    print("-- 解析计数 --")
    print("DDL: %d 表 / %d varchar 列 / %d 宽度种类" % (len(tables), ddl_cols, len(widths)))
    print("request schema: %d 模型 / %d 带长度约束字段" % (len(reqs), len(maxl)))
    print("实现: @Size(max) %d / @Size(min) %d / @Pattern 量词 %d / @NotBlank %d / 含长度检查文件 %d / 形参域检查 %d"
          % (len(impl["size_max"]), len(impl["size_min"]), len(impl["pattern_len"]), impl["n_notblank"],
             len([1 for _f, d in impl["per_file"].items() if d["checks"]]), n_param_scoped))
    print("端点: %d 条（%d 条带 request_model）" % (ep_count, len(by_model)))
    print("测试: %d 处 repeat(N)" % t_n)
    print()
    for line in passes:
        print(line)
    for line in infos:
        print(line)
    for line in fails:
        print(line)
    print()
    print("汇总：PASS %d / FAIL %d / INFO %d" % (len(passes), len(fails), len(infos)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
