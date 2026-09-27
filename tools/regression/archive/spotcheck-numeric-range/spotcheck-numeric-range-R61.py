#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R61 抽查：数值字段「取值范围（minimum/maximum）」+ 声明模型可达性（第三十五类可审计不变量）—— 只读。

为什么两套门禁都看不见：
  ① 契约测试把**真实响应**与 JSON Schema 比对，而 requests/*.schema.json 的 `minimum`/`maximum`
     在**运行时不参与任何校验**（R57 已取证：json-schema-validator 是 <scope>test</scope>、main 零引用）
     → 「schema 声明数值范围、实现不校验」对全部 204 例不可见；
  ② 覆盖门禁只比「方法 + 路径」注册表；
  ③ openapi 与客户端 TS 不被任何测试读取 / 执行。

真源七处：
  S = requests/*.schema.json 的 minimum/maximum/exclusiveMinimum/exclusiveMaximum（含 $ref 跟进）
  E = endpoints.json 的 request_model → 端点（可达性）
  G = tools/gen-backend-models.py 的 REQUESTS 注册表（哪些模型被注册、却零端点引用）
  D = DDL 列类型（numeric(p,s) / int / bigint）与 CHECK 约束
  I = 实现：字段级范围注解（@Min/@Max/@DecimalMin/@DecimalMax/@Positive…）+ 服务层同域范围检查 + @Valid 激活点
  T = 测试越界构造      M = md 清单范围措辞（信息项）

判据纪律（照抄 R60 的返工教训，一律「先怀疑判据」）：
  ① 注解实参必须**括号配对**解析（坑 63）：`@Min(value = 1, message = "…")` 的实参里有括号/逗号；
  ② 服务层证据必须**同域**（坑 125）：被检查 token 必须与字段同形（snake/camel 两种），
     且同行出现范围算子；否则只记**弱证据**（信息项），不计入覆盖 —— 不得拿「同文件有范围检查」冒充；
  ③ 每个源都要有 `> 0` 正向对照（坑 46/75/98）；没有正向对照的「0 发现」不可信。
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
GEN = ROOT / "tools/gen-backend-models.py"
MAIN = ROOT / "aap-server/src/main/java"
TEST = ROOT / "aap-server/src/test/java"
MD = ROOT / "docs/backend/02-API接口模型清单.md"

RANGE_KEYWORDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
RANGE_ANNOT = ("Min", "Max", "DecimalMin", "DecimalMax", "Positive", "PositiveOrZero",
               "Negative", "NegativeOrZero", "Digits", "Range")
ANNOT_RE = re.compile(r"@(?:javax\.validation\.|jakarta\.validation\.)?(%s)\b" % "|".join(RANGE_ANNOT))
NUM_OP_RE = re.compile(r"(<|>|<=|>=|signum\s*\(\s*\)|compareTo\s*\(|MAX_|MIN_)")
INTEGRAL = {"int", "integer", "int2", "int4", "int8", "bigint", "smallint", "serial", "bigserial"}

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
    """text[i] == '(' → 返回配对 ')' 下标（括号配对，坑 63）。"""
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


def camel(snake):
    parts = snake.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


# ---------------------------------------------------------------- S：schema 数值约束
def collect_numeric(props, model, prefix, seen_refs, out):
    """递归收集 properties 里的数值约束（含 $ref 跟进；坑 92：按目标路径反查）。"""
    if not isinstance(props, dict):
        return
    for name, spec in props.items():
        if not isinstance(spec, dict):
            continue
        ref = spec.get("$ref")
        if ref:
            target = (MOD / Path(ref).name)
            key = str(target)
            if key not in seen_refs:
                seen_refs.add(key)
                sub = read_json(target)
                if sub is not None:
                    collect_numeric(sub.get("properties", {}), model,
                                    prefix + name + ".", seen_refs, out)
            continue
        for one in spec.get("oneOf", []) or []:
            if isinstance(one, dict) and one.get("$ref"):
                target = (MOD / Path(one["$ref"]).name)
                key = str(target)
                if key not in seen_refs:
                    seen_refs.add(key)
                    sub = read_json(target)
                    if sub is not None:
                        collect_numeric(sub.get("properties", {}), model,
                                        prefix + name + ".", seen_refs, out)
        typ = spec.get("type")
        if isinstance(typ, list):
            typ = [t for t in typ if t != "null"]
            typ = typ[0] if typ else None
        keys = [k for k in RANGE_KEYWORDS if k in spec]
        if keys:
            out.append({"model": model, "field": prefix + name, "leaf": name, "type": typ,
                        "min": spec.get("minimum"), "max": spec.get("maximum"),
                        "emin": spec.get("exclusiveMinimum"), "emax": spec.get("exclusiveMaximum")})
        if typ == "array" and "minItems" in spec:
            out.append({"model": model, "field": prefix + name, "leaf": name, "type": "array",
                        "min_items": spec["minItems"]})


def load_schemas():
    rows, n_files = [], 0
    for p in sorted(REQ.glob("*.schema.json")):
        doc = read_json(p)
        if doc is None:
            continue
        n_files += 1
        collect_numeric(doc.get("properties", {}), p.name[:-len(".schema.json")], "", set(), rows)
    return rows, n_files


# ---------------------------------------------------------------- E：endpoints
def load_endpoints():
    doc = read_json(EPF)
    if doc is None:
        return [], {}, []
    eps = doc.get("endpoints", doc) if isinstance(doc, dict) else doc
    if not isinstance(eps, list):
        return [], {}, []
    by_model, ids = {}, []
    for e in eps:
        if not isinstance(e, dict):
            continue
        ids.append(e.get("id"))
        rm = e.get("request_model")
        if rm:
            by_model.setdefault(rm, []).append(e.get("id"))
    return eps, by_model, ids


# ---------------------------------------------------------------- G：生成器注册表
def load_registry():
    txt = read(GEN)
    m = re.search(r"^REQUESTS[^=]*=\s*\{", txt, re.M)
    if not m:
        return []
    i = txt.index("{", m.start())
    depth, j = 0, i
    while j < len(txt):
        if txt[j] == "{":
            depth += 1
        elif txt[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    block = txt[i:j + 1]
    return re.findall(r'^\s{4}"([a-z0-9-]+)"\s*:', block, re.M)


# ---------------------------------------------------------------- D：DDL
def load_ddl():
    cols = {}   # table -> {col: (base, p, s, notnull)}
    tables = 0
    checks = 0
    for p in sorted(MIG.glob("*.sql")):
        sql = read(p)
        checks += len(re.findall(r"\bcheck\s*\(", sql, re.I))
        for m in re.finditer(r"create\s+table(?:\s+if\s+not\s+exists)?\s+([a-z_][a-z0-9_]*)\s*\(",
                             sql, re.I):
            table = m.group(1)
            i = sql.index("(", m.start())
            depth, j = 0, i
            while j < len(sql):
                if sql[j] == "(":
                    depth += 1
                elif sql[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = sql[i + 1:j]
            tables += 1
            d = cols.setdefault(table, {})
            for line in body.splitlines():
                cm = re.match(r"\s*([a-z_][a-z0-9_]*)\s+([a-z][a-z0-9]*)"
                              r"(?:\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\))?", line, re.I)
                if not cm:
                    continue
                cname, base = cm.group(1).lower(), cm.group(2).lower()
                if base in ("primary", "unique", "foreign", "constraint", "check", "references"):
                    continue
                d[cname] = (base, int(cm.group(3)) if cm.group(3) else None,
                            int(cm.group(4)) if cm.group(4) else None,
                            bool(re.search(r"\bnot\s+null\b", line, re.I)))
    return cols, tables, checks


# ---------------------------------------------------------------- I：实现
def load_impl():
    ann_sites = []      # (tag, file, token, argtext)
    check_lines = []    # (file, lineno, text)
    files = sorted(MAIN.rglob("*.java"))
    for p in files:
        src = read(p)
        for m in ANNOT_RE.finditer(src):
            k = m.end()
            arg = ""
            while k < len(src) and src[k] in " \t":
                k += 1
            if k < len(src) and src[k] == "(":
                close = match_paren(src, k)
                if close > 0:
                    arg = src[k:close + 1]
                    k = close + 1
            # 跳过同一段注解串（`@Min(...) @Max(...)`）与修饰符，取**被注解的声明名**（坑 63/124）
            tail = src[k:k + 400]
            tm = re.search(r"(?:@[A-Za-z_][A-Za-z0-9_.]*\s*(?:\([^)]*\))?\s*|"
                           r"(?:public|private|protected|static|final|volatile|transient)\s+)*"
                           r"(?:[A-Za-z_][A-Za-z0-9_<>\[\],.\s?]*?\s+)?"
                           r"([A-Za-z_][A-Za-z0-9_]*)\s*(?=[,);=])", tail)
            token = tm.group(1) if tm else ""
            ann_sites.append((m.group(1), str(p), token, arg))
        for ln, line in enumerate(src.splitlines(), 1):
            s = line.strip()
            if s.startswith("*") or s.startswith("//") or s.startswith("/*"):
                continue  # 注释行不是证据（本轮真实返工：javadoc 被当成强证据）
            if (NUM_OP_RE.search(line) and re.search(r"\d|BigDecimal\.ZERO|signum|MAX_|MIN_", line)) \
                    or re.search(r"ApiErrorDetail\(|\.field\(|errors\.add\(", line):
                check_lines.append((str(p), ln, s))
    return ann_sites, check_lines, len(files)


def tokens_of(field):
    leaf = field.split(".")[-1]
    return {leaf, camel(leaf)}


def token_present(line, token):
    """token 是否**真的**出现在该行：剥掉字符串字面量后再判；
    另允许「字段名作为 ApiErrorDetail/field( 的首个字符串实参」这一形态
    （`new ApiErrorDetail("items", …)` 是字段名证据，不是路径拼接）。"""
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
    if re.search(r"\b%s\b" % re.escape(token), stripped):
        return True
    return bool(re.search(r'(?:ApiErrorDetail|field)\(\s*"%s"' % re.escape(token), line))


def _reject_context(lines, ln, window=3):
    """该行 ±window 行内是否出现**拒绝性**上下文（throw / errors.add / ApiException / field(）。
    V5 之类的 warnings.add 不算 → 警告式比较不计入覆盖（坑 81 判据范围与语义不符）。"""
    lo, hi = max(0, ln - 1 - window), min(len(lines), ln + window)
    blob = "\n".join(lines[lo:hi])
    return bool(re.search(r"\bthrow\b|errors\.add\(|ApiException|\.field\(", blob))


def evidence_for(field, ann_sites, check_lines):
    toks = tokens_of(field)
    strong, weak = [], []
    for tag, path, token, arg in ann_sites:
        if token and token in toks:
            strong.append("%s %s @%s(%s)" % (Path(path).name, token,
                                             tag, arg.strip("()")[:26]))
    # 按文件分组，便于取 ±window 行做拒绝性上下文判定
    per_file = {}
    for path, ln, text in check_lines:
        per_file.setdefault(path, []).append((ln, text))
    for path, hits in per_file.items():
        lines = read(path).splitlines()
        for ln, text in hits:
            if not any(token_present(text, t) for t in toks):
                continue
            if _reject_context(lines, ln):
                strong.append("%s:%d %s" % (Path(path).name, ln, text[:72]))
    if not strong:
        for path, hits in per_file.items():
            src = read(path)
            if any(t in src for t in toks):
                weak.append("%s:%d" % (Path(path).name, hits[0][0]))
    return strong, weak


# ---------------------------------------------------------------- T：测试越界构造
def load_tests(fields):
    hits = {}
    for p in sorted(TEST.rglob("*.java")):
        src = read(p)
        for ln, line in enumerate(src.splitlines(), 1):
            for f in fields:
                for t in tokens_of(f):
                    if not re.search(r"\b%s\b" % re.escape(t), line):
                        continue
                    if re.search(r"[:=]\s*-?\d", line) or re.search(r'":\s*-?\d', line):
                        hits.setdefault(f, []).append("%s:%d" % (Path(p).name, ln))
    return hits


def main():
    numeric, n_schema_files = load_schemas()
    eps, by_model, ep_ids = load_endpoints()
    registry = load_registry()
    cols, n_tables, n_checks = load_ddl()
    ann_sites, check_lines, n_main_files = load_impl()

    # ---------------- 正向对照
    if numeric:
        ok("A0a", "request schema 解析到数值/数组约束字段 %d 个 / %d 个模型文件（正向对照）"
           % (len(numeric), n_schema_files))
    else:
        fail("A0a", "解析到 0 个数值约束字段 → 先怀疑解析器（空夹具/路径错）")
    if by_model:
        ok("A0b", "endpoints.json 解析到 %d 条端点、%d 个被引用的 request_model（正向对照）"
           % (len(ep_ids), len(by_model)))
    else:
        fail("A0b", "解析到 0 个被引用的 request_model → 先怀疑解析器")
    if registry:
        ok("A0c", "生成器 REQUESTS 注册表解析到 %d 个请求模型（正向对照）" % len(registry))
    else:
        fail("A0c", "解析到 0 个注册模型 → 先怀疑解析器")
    ddl_numeric = sum(1 for t, d in cols.items() for c, v in d.items()
                      if v[0] in INTEGRAL or v[0] in ("numeric", "decimal", "real", "double"))
    if ddl_numeric:
        ok("A0d", "DDL 解析到 %d 表 / %d 个数值列（正向对照）" % (n_tables, ddl_numeric))
    else:
        fail("A0d", "解析到 0 个数值列 → 先怀疑解析器")
    if ann_sites or check_lines:
        ok("A0e", "实现解析到字段级范围注解 %d 处、范围检查行 %d 处（%d 个主源码文件；正向对照）"
           % (len(ann_sites), len(check_lines), n_main_files))
    else:
        fail("A0e", "实现解析到 0 处范围校验 → 先怀疑解析器")

    # ---------------- A4：孤儿请求模型（可达性）
    referenced = set(by_model)
    orphans = sorted(set(registry) - referenced)
    if orphans:
        for o in orphans:
            fail("A4", "孤儿请求模型 `%s`：生成器注册表有、endpoints.json 零端点引用 → "
                       "契约产物不可达（死产物；补端点或删注册项都属契约变更，待拍板）" % o)
    else:
        ok("A4b", "注册表 %d 个请求模型全部被至少一条端点引用（无孤儿）" % len(registry))
    if registry and not referenced:
        info("A4c", "反向对照：被引用模型 %d 个（>0 时 A4 才有判别力）" % len(referenced))

    # ---------------- A1：逐字段范围强制
    strong_n = weak_n = none_n = 0
    strong_list, weak_list, none_list = [], [], []
    for row in numeric:
        model, field = row["model"], row["field"]
        if model not in referenced:
            continue
        strong, weak = evidence_for(field, ann_sites, check_lines)
        label = "%s.%s" % (model, field)
        if strong:
            strong_n += 1
            strong_list.append("%s→%s" % (label, strong[0]))
        elif weak:
            weak_n += 1
            weak_list.append("%s(%s)" % (label, weak[0]))
        else:
            none_n += 1
            none_list.append(label)
    if none_list:
        fail("A1", "契约声明数值范围、实现零证据 %d 个：%s" % (len(none_list), ", ".join(none_list)))
    else:
        ok("A1b", "被引用模型的数值约束字段全部有实现证据（强 %d / 弱 %d）" % (strong_n, weak_n))
    if weak_list:
        info("A1c", "弱证据 %d 个（同文件有范围检查但非同域同行 → 可能为通用校验，不计入覆盖）：%s"
             % (len(weak_list), ", ".join(weak_list)))
    if strong_list:
        info("A1d", "同域强证据 %d 个：%s" % (len(strong_list), ", ".join(strong_list[:12])))

    # ---------------- A2：schema 类型 ⇔ DDL 列类型
    mism, compared = [], 0
    for row in numeric:
        leaf = row["leaf"]
        typ = row["type"]
        if typ not in ("integer", "number"):
            continue
        for t, d in cols.items():
            if leaf in d:
                base = d[leaf][0]
                compared += 1
                if typ == "integer" and base not in INTEGRAL:
                    mism.append("%s.%s schema=integer ↔ %s.%s=%s" % (row["model"], leaf, t, leaf, base))
                if typ == "number" and base in INTEGRAL:
                    mism.append("%s.%s schema=number ↔ %s.%s=%s" % (row["model"], leaf, t, leaf, base))
    if mism:
        fail("A2", "schema 数值类型与 DDL 列类型不一致 %d 处：%s" % (len(mism), ", ".join(mism)))
    elif compared:
        ok("A2b", "schema 数值类型与 DDL 同名列类型逐条一致（已比对 %d 条）" % compared)
    else:
        fail("A2c", "未比对到任何同名 DDL 列 → 先怀疑列名映射（不得据此判一致）")

    # ---------------- A3：DDL CHECK 约束
    if n_checks:
        ok("A3", "DDL 有 CHECK 约束 %d 处（库级兜底存在）" % n_checks)
    else:
        info("A3b", "DDL CHECK 约束 0 处 → 数值范围**只由应用层强制**（库层无兜底；"
                    "绕过应用层写库即越界，属设计取舍）")

    # ---------------- A3c：schema 上限 vs numeric(p,s) 可表达上限
    over, scale_undeclared = [], []
    for row in numeric:
        leaf, mx = row["leaf"], row.get("max")
        for t, d in cols.items():
            if leaf not in d:
                continue
            base, pp, ss, _nn = d[leaf]
            if base in ("numeric", "decimal") and pp:
                cap = 10 ** (pp - (ss or 0)) - 10 ** (-(ss or 0))
                if mx is not None and mx > cap:
                    over.append("%s.%s max=%s > %s.%s numeric(%s,%s) 上限 %s"
                                % (row["model"], leaf, mx, t, leaf, pp, ss, cap))
                elif ss:
                    scale_undeclared.append("%s.%s←%s.%s numeric(%s,%s)"
                                            % (row["model"], leaf, t, leaf, pp, ss))
    if over:
        fail("A3c", "契约上限超出 DDL numeric(p,s) 可表达范围 %d 处（越界值被 PG 静默收窄/报错）：%s"
             % (len(over), ", ".join(over)))
    else:
        ok("A3d", "契约声明上限均未超出 DDL numeric(p,s) 可表达范围（已比对）")
    if scale_undeclared:
        info("A3e", "契约未声明精度（scale）而 DDL 有小数位 %d 处 → 超精度入参被 PG 静默四舍五入"
                    "（客户端按入参回显会与响应不一致）：%s"
             % (len(scale_undeclared), ", ".join(scale_undeclared[:8])))

    # ---------------- A5：测试背书
    hitmap = load_tests([r["field"] for r in numeric if r["model"] in referenced])
    guarded = sorted(hitmap)
    if guarded:
        ok("A5", "数值范围有测试越界构造守卫 %d 个字段：%s"
           % (len(guarded), ", ".join("%s(%s)" % (g, hitmap[g][0]) for g in guarded[:8])))
    else:
        info("A5b", "测试源未解析到越界构造 → 数值范围无用例守卫（信息项）")
    unguarded = [r["field"] for r in numeric if r["model"] in referenced and r["field"] not in hitmap]
    if unguarded:
        info("A5c", "无越界构造的字段 %d 个：%s" % (len(unguarded), ", ".join(sorted(set(unguarded)))))

    # ---------------- A6：md 措辞（信息项）
    md_n = len(re.findall(r"范围|之间|不超过\s*\d+|0\s*~\s*100", read(MD)))
    info("A6", "md 清单出现范围类措辞 %d 处（数值范围真源只在 schema 与实现）" % md_n)

    print("=== R61 抽查：数值字段取值范围 + 声明模型可达性（第三十五类可审计不变量）===")
    print("-- 解析计数 --")
    print("schema: %d 模型文件 / %d 个数值约束字段" % (n_schema_files, len(numeric)))
    print("endpoints: %d 条 / %d 个被引用 request_model" % (len(ep_ids), len(by_model)))
    print("生成器注册表: %d 个模型 / 孤儿 %d" % (len(registry), len(orphans)))
    print("DDL: %d 表 / %d 数值列 / CHECK %d 处" % (n_tables, ddl_numeric, n_checks))
    print("实现: 范围注解 %d / 范围检查行 %d / 主源码文件 %d" % (len(ann_sites), len(check_lines), n_main_files))
    print("逐字段强制: 强证据 %d / 弱证据 %d / 无证据 %d" % (strong_n, weak_n, none_n))
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
