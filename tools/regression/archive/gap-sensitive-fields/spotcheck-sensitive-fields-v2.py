#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R53 抽查 v2（只读）：**敏感字段（明文/密文/掩码）对外键集合** 跨源一致性 —— 第二十七类可审计不变量。

为什么两套门禁都看不见：
  * 契约测试把真实响应与 JSON Schema 比对 —— **多出的键**在 `additionalProperties` 未收紧时一律放行，
    **未出口的键**只要不在 `required` 里也一律放行 → 「实现出口了契约未声明的键」与
    「契约声明了实现永不出口的键」两个方向**全量用例全绿也看不见**（skill 坑 100 同族）；
  * 覆盖门禁只比「方法 + 路径」；客户端 TS 不被任何测试执行 → 客户端按**错的键名**读取时
    `raw.x` 恒为 `undefined`，静默落到兜底分支（坑 1）。

真源（六处）：
  V = 服务端响应出口键：`@JsonProperty("k")` ＋ **无注解 getter 的默认 Jackson 键名**（坑 46：漏了它会把
      `LoginResult.getToken()` 判成「服务端不出口 token」的假发现）＋ `Map.put/of("k", …)`
  S = 契约声明键：`docs/backend/json-schema/**/*.schema.json` 属性名
  C = 客户端读取键：`aap-client/src/**/*.{ts,vue}` 属性访问（区分「直接读取」与「容错候选」）
  D = DDL 敏感列（`*_cipher` / `*_hash` / `*_fingerprint` / `*_mask(ed)`）
  I = 掩码实现（`CryptoService.maskPhone/maskApiKey` 形状与调用点）
  T = 测试背书（信息项）

断言：A0a…A0g 正向对照；A1 客户端契约形态键 ⊆ V；A2 V ⊆ S；A2c **逐端点**「响应 DTO 的敏感键 ⇔ 该端点
response_model schema 的敏感键」（双向）；A3 密文/指纹列不得出口；A4 明文出口必须有实现依据；A5 内联掩码为 0；
A6 掩码形状与 javadoc 一致；A7 测试背书（信息项）。

用法：python spotcheck-sensitive-fields-v2.py [--root DIR]
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

SENS = re.compile(r"(api_key|phone|mobile|secret|password|pwd|token|credential|openid|uscc)", re.I)
JP_RE = re.compile(r'@JsonProperty\("([^"]+)"\)')
MAP_RE = re.compile(r'\b(?:put|of)\(\s*"([^"]+)"')
GETTER_RE = re.compile(r"public\s+(?:String|Integer|Long|Boolean|boolean|int|long|BigDecimal|List<[^>]*>|Map<[^>]*>|OffsetDateTime|Object)\s+(get|is)([A-Z]\w*)\s*\(\s*\)")
CIPHER = re.compile(r"(cipher|_hash|fingerprint)", re.I)
MASK_COL = re.compile(r"(mask|masked)", re.I)
PLAINTEXT_KEYS = {"api_key", "password", "secret", "pwd"}
MASK_INLINE_RE = re.compile(r'substring\(\s*\d+\s*,\s*\d+\s*\)\s*\+\s*"\*+"')
CLIENT_ACCESS = re.compile(r"[.?\[]\s*[\"']?([a-zA-Z_][a-zA-Z0-9_]*)[\"']?\s*(?=[?:.,)\]])")
CAND_FN = re.compile(r"\b(first|firstStr|firstOf|firstOfStr|pick)\s*\(")
DTO_FILE = re.compile(r"(Views|Response|Result|Dto|Payload)\.java$")

problems, infos = [], []


def result(name, ok, msg):
    print("%s %s %s" % ("[PASS]" if ok else "[FAIL]", name, msg))
    if not ok:
        problems.append(name)


def info(name, msg):
    print("[INFO] %s %s" % (name, msg))
    infos.append(name)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def decamel(name):
    return name[:1].lower() + name[1:]


def collect_export(root):
    """V = 服务端出口键 → {key: set(文件)}；含无注解 getter 的默认键名。"""
    v, unannotated = {}, {}
    files = sorted((root / "aap-server/src/main/java").rglob("*.java"))
    for f in files:
        rel = str(f.relative_to(root)).replace("\\", "/")
        if not DTO_FILE.search(f.name) and "/dto/" not in rel:
            continue
        txt = read(f)
        annotated_lines = set()
        for m in JP_RE.finditer(txt):
            annotated_lines.add(txt[:m.start()].count("\n"))
        for m in MAP_RE.finditer(txt):
            k = m.group(1)
            if SENS.search(k):
                v.setdefault(k, set()).add(rel)
        for m in JP_RE.finditer(txt):
            k = m.group(1)
            if SENS.search(k):
                v.setdefault(k, set()).add(rel)
        # 无注解 getter：默认 Jackson 键名（camelCase）——只取「getter 上一行不是 @JsonProperty」的
        for m in GETTER_RE.finditer(txt):
            line_no = txt[:m.start()].count("\n")
            prev = txt.splitlines()[line_no - 1].strip() if line_no else ""
            if prev.startswith("@JsonProperty"):
                continue
            k = decamel(m.group(2))
            if SENS.search(k):
                v.setdefault(k, set()).add(rel)
                unannotated.setdefault(k, set()).add(rel)
    return v, unannotated, len(files)


def collect_schema(root):
    s, per_model = {}, {}
    n = 0
    for f in sorted((root / "docs/backend/json-schema").rglob("*.schema.json")):
        d = json.loads(read(f))
        n += 1
        buckets = [d.get("properties") or {}]
        for sub in ("definitions", "$defs"):
            for _name, node in (d.get(sub) or {}).items():
                buckets.append(node.get("properties") or {})
        top = set()
        for b in buckets:
            for k in b:
                if SENS.search(k):
                    s.setdefault(k, set()).add(f.stem)
                    top.add(k)
        # 坑：Path.stem 对 `x.schema.json` 得到 `x.schema`，按模型名查表会全落空 → 必须显式剥离双后缀
        name = f.name[:-len(".schema.json")] if f.name.endswith(".schema.json") else f.stem
        per_model[name] = top
    return s, per_model, n


def collect_client(root):
    direct, cand, n = {}, {}, 0
    pats = list((root / "aap-client/src").rglob("*.ts")) + list((root / "aap-client/src").rglob("*.vue"))
    for f in sorted(pats):
        n += 1
        rel = str(f.relative_to(root)).replace("\\", "/")
        for i, line in enumerate(read(f).splitlines(), 1):
            st = line.strip()
            if st.startswith("*") or st.startswith("//") or st.startswith("/*"):
                continue
            for m in CLIENT_ACCESS.finditer(line):
                k = m.group(1)
                if not SENS.search(k) or not re.search(r"[a-z_]", k) or k.isupper():
                    continue
                if k in ("phone", "mobile") and not re.search(r"\.%s\b" % k, line):
                    continue
                tgt = cand if (CAND_FN.search(line) or "??" in line) else direct
                tgt.setdefault(k, set()).add("%s:%d" % (rel, i))
    return direct, cand, n


def collect_ddl(root):
    ciph, mask, n = {}, {}, 0
    for f in sorted((root / "aap-server/src/main/resources/db/migration").glob("*.sql")):
        n += 1
        for line in read(f).splitlines():
            m = re.match(r"\s+([a-z_][a-z0-9_]*)\s+(text|varchar|char|jsonb|bigint|integer|boolean|numeric)", line)
            if not m or not SENS.search(m.group(1)):
                continue
            col = m.group(1)
            if CIPHER.search(col):
                ciph[col] = True
            elif MASK_COL.search(col):
                mask[col] = True
    return ciph, mask, n


def collect_masks(root):
    impl, inline, calls = {}, [], []
    for f in sorted((root / "aap-server/src/main/java").rglob("*.java")):
        rel = str(f.relative_to(root)).replace("\\", "/")
        txt = read(f)
        for m in re.finditer(r"public\s+String\s+(mask\w+)\s*\(", txt):
            impl[m.group(1)] = (rel, txt)
        for m in MASK_INLINE_RE.finditer(txt):
            if "CryptoService" not in rel:
                inline.append("%s:%d" % (rel, txt[:m.start()].count("\n") + 1))
        for m in re.finditer(r"\b(maskPhone|maskApiKey)\s*\(", txt):
            ln = txt[:m.start()].count("\n") + 1
            if "public String" not in txt.splitlines()[ln - 1]:
                calls.append("%s:%d" % (rel, ln))
    return impl, inline, calls


def collect_tests(root):
    shape, neg = 0, 0
    for f in sorted((root / "aap-server/src/test/java").rglob("*.java")):
        txt = read(f)
        shape += len(re.findall(r'"[^"]*\*{3,}[^"]*"', txt))
        neg += len(re.findall(r"不得|永不|never|明文", txt))
    return shape, neg


def load_response_shape(root):
    p = root / "tools/audit-response-shape.py"
    spec = importlib.util.spec_from_file_location("ars", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def match_paren(text, i):
    depth = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def record_keys(root, type_str):
    """→ (keys, note)：解析返回类型最内层 DTO 的出口键。"""
    t = type_str.strip()
    if "Map<" in t:
        return set(), "返回 Map（键在 Service 里拼装，静态不可判定）"
    for _ in range(4):
        m = re.search(r"<\s*([A-Za-z_][\w.]*)\s*>$", t)
        if m and "<" in t:
            t = m.group(1)
        else:
            break
    if "<" in t:
        return set(), "未能静态判定（泛型嵌套 %s）" % type_str
    cls, _, rec = t.partition(".")
    cands = [f for f in (root / "aap-server/src/main/java").rglob("%s.java" % cls)]
    if not cands:
        return set(), "未找到 %s.java" % cls
    txt = read(cands[0])
    body = txt
    if rec:
        rm = re.search(r"\brecord\s+%s\s*\(" % re.escape(rec), txt)
        if not rm:
            return set(), "未找到 record %s" % rec
        close = match_paren(txt, rm.end() - 1)
        body = txt[rm.end():close]
    keys = set()
    # 只有 record 才按「记录体跨度」取 @JsonProperty；class DTO 必须只取**外层类自身**的 getter，
    # 否则内层嵌套 record 的 @JsonProperty 会被误当成顶层出口键（真实返工：ProviderProfileResponse
    # 的 AccountInfo/contact 内层 `phone_masked` 被算成顶层键 → 4 条「实现出口未声明」假发现）
    if rec:
        for m in JP_RE.finditer(body):
            keys.add(m.group(1))
    else:
        for m in GETTER_RE.finditer(txt):
            ln = txt[:m.start()].count("\n")
            prev = txt.splitlines()[ln - 1].strip() if ln else ""
            if prev.startswith("@JsonProperty"):
                match = JP_RE.search(prev)
                if match:
                    keys.add(match.group(1))
                continue
            keys.add(decamel(m.group(2)))
        return keys, ""
    if rec and "record" in txt[:len(txt) // 2] + txt:
        # record 分量无注解 → 分量名
        rm = re.search(r"\brecord\s+%s\s*\(" % re.escape(rec), txt)
        if rm:
            close = match_paren(txt, rm.end() - 1)
            seg = txt[rm.end():close]
            depth = 0
            cur = ""
            parts = []
            for ch in seg:
                if ch in "<([{":
                    depth += 1
                elif ch in ">)]}":
                    depth -= 1
                if ch == "," and depth == 0:
                    parts.append(cur)
                    cur = ""
                else:
                    cur += ch
            parts.append(cur)
            for p in parts:
                if "@JsonProperty" in p:
                    continue
                ids = re.findall(r"[A-Za-z_]\w*", p)
                if ids:
                    keys.add(ids[-1])
    else:
        for m in GETTER_RE.finditer(txt):
            ln = txt[:m.start()].count("\n")
            prev = txt.splitlines()[ln - 1].strip() if ln else ""
            if prev.startswith("@JsonProperty"):
                continue
            keys.add(decamel(m.group(2)))
    return keys, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    args = ap.parse_args()
    root = Path(args.root)

    V, unannotated, n_java = collect_export(root)
    S, per_model, n_schema = collect_schema(root)
    C_direct, C_cand, n_client = collect_client(root)
    D_ciph, D_mask, n_ddl = collect_ddl(root)
    impl, inline, calls = collect_masks(root)
    shape_asserts, neg_asserts = collect_tests(root)

    print("== R53 抽查：敏感字段对外键集合跨源一致性（只读） ==")
    print("root = %s" % root)
    print("")

    result("A0a 服务端出口敏感键 > 0", len(V) > 0, "解析到 %d 键（%d 个 java 文件；其中无注解 getter 贡献 %d 键）"
           % (len(V), n_java, len(unannotated)))
    result("A0b 契约声明敏感键 > 0", len(S) > 0, "解析到 %d 键（%d 个 schema 文件）" % (len(S), n_schema))
    result("A0c 客户端敏感读取键 > 0", len(C_direct) + len(C_cand) > 0,
           "直接 %d 键 / 候选 %d 键（%d 个客户端源文件）" % (len(C_direct), len(C_cand), n_client))
    result("A0d DDL 密文列 > 0", len(D_ciph) > 0, "%d 个密文/指纹列（%d 个迁移文件）" % (len(D_ciph), n_ddl))
    result("A0e 掩码实现 > 0", len(impl) > 0, "解析到 %s" % sorted(impl))
    result("A0f 掩码调用点 > 0", len(calls) > 0, "解析到 %d 个调用点" % len(calls))

    # ---- A1：客户端「契约形态键」⊆ V ----
    contract_form = {k for k in C_direct if "_" in k or k in S}
    local_keys = sorted(k for k in C_direct if k not in contract_form)
    missing = sorted(k for k in contract_form if k not in V)
    result("A1 客户端读取的契约形态键 ⊆ 服务端出口键", not missing and len(contract_form) > 0,
           "契约形态键 %d 个，未在服务端出口集合中：%s" % (len(contract_form), missing or "无"))
    for k in missing:
        print("      [FAIL] A1 键 `%s` 客户端读取点：%s" % (k, sorted(C_direct[k])[:3]))
    for k in sorted(contract_form):
        if k in V:
            print("      [PASS] A1 键 `%s` 客户端 %d 处读取点，服务端出口于 %s" % (k, len(C_direct[k]), sorted(V[k])[0]))
    info("A1b 客户端本地视图模型键（camelCase/无下划线且契约未声明，不作契约比对，坑 81）",
         "%d 键：%s" % (len(local_keys), local_keys))
    info("A1c 容错候选键（`first(...)`/`??` 链，缺失属设计容忍）",
         "%d 键：%s" % (len(C_cand), sorted(C_cand)))

    # ---- A2：V ⊆ S ----
    undeclared = sorted(k for k in V if k not in S)
    result("A2 服务端出口的敏感键 ⊆ 契约声明键", not undeclared,
           "出口 %d 键，契约未声明：%s" % (len(V), undeclared or "无"))
    for k in undeclared:
        print("      [FAIL] A2 键 `%s` 出口文件：%s（契约从未声明）" % (k, sorted(V[k])))
    info("A2b 契约声明但全局零出口的敏感键", "%d 键：%s" % (len([k for k in S if k not in V]), sorted(k for k in S if k not in V)))

    # ---- A2c：逐端点 响应 DTO 敏感键 ⇔ 该端点 response_model schema 敏感键 ----
    ars = load_response_shape(root)
    ctrls, ctrl_problems = ars.parse_controllers(root / "aap-server/src/main/java/com/hioas/aap")
    manifest = json.loads(read(root / "docs/backend/endpoints.json"))
    checked, skipped, dead, extra = 0, [], [], []
    for ep in manifest["endpoints"]:
        model = ep.get("response_model")
        key = ars.key_of(ep["method"], ep["path"])
        c = ctrls.get(key)
        if not model or not c:
            skipped.append("%s: 未定位控制器" % ep["id"])
            continue
        keys, note = record_keys(root, c["ret"])
        if not keys:
            skipped.append("%s: %s" % (ep["id"], note or "无键"))
            continue
        dto_sens = {k for k in keys if SENS.search(k)}
        sch = per_model.get(model, set())
        d = sorted(sch - dto_sens)
        e = sorted(dto_sens - sch)
        if d or e:
            dead.extend("%s(%s) 契约声明未出口=%s" % (ep["id"], model, d) for _ in [0] if d)
            extra.extend("%s(%s) 实现出口未声明=%s" % (ep["id"], model, e) for _ in [0] if e)
        checked += 1
    result("A2c 逐端点响应 DTO 敏感键 ⇔ response_model schema（已定位的端点全部一致）", not dead and not extra,
           "已定位 %d 个端点（跳过 %d：%s）；契约声明未出口 %d 条、实现出口未声明 %d 条"
           % (checked, len(skipped), "; ".join(skipped[:4]) or "无", len(dead), len(extra)))
    for x in dead:
        print("      [FAIL] A2c 死字段：%s" % x)
    for x in extra:
        print("      [FAIL] A2c 超集字段：%s" % x)

    # ---- A3：密文/指纹列不得出口 ----
    leaked = []
    for col in D_ciph:
        camel = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), col)
        for form in {col, camel}:
            if form in V:
                leaked.append((form, col, sorted(V[form])))
    result("A3 密文/指纹列名不得出现在响应出口键", not leaked,
           "密文列 %d 个，出口泄漏：%s" % (len(D_ciph), [x[0] for x in leaked] or "无"))
    for form, col, files in leaked:
        print("      [FAIL] A3 `%s`（DDL 列 `%s`）出现在出口：%s" % (form, col, files))
    info("A3b DDL 掩码列（列名 vs 对外键名允许不同形）", "%d 列：%s" % (len(D_mask), sorted(D_mask)))

    # ---- A4：明文敏感键出口必须有实现依据 ----
    hits = []
    for k in sorted(PLAINTEXT_KEYS & set(V)):
        for rel in sorted(V[k]):
            hits.append((k, rel, "明文" in read(root / rel)))
    bad = [h for h in hits if not h[2]]
    result("A4 明文敏感键出口必须带实现依据（注释含「明文」）且处数 ≤ 2", not bad and 0 < len(hits) <= 2,
           "出口明文键 %d 处（上限 2）：%s" % (len(hits), ["%s@%s" % (a, b) for a, b, _ in hits] or "无"))
    for k, rel, ok in hits:
        print("      [%s] A4 `%s` @ %s 依据注释=%s" % ("PASS" if ok else "FAIL", k, rel, ok))

    # ---- A5 / A6 ----
    result("A5 内联掩码实现（CryptoService 之外）必须为 0 处", not inline,
           "命中 %d 处：%s；掩码实现 %d 个、调用点 %d 个" % (len(inline), inline or "无", len(impl), len(calls)))
    shape_ok, detail = True, []
    for name, need in (("maskPhone", 'substring(0, 3) + "****"'), ("maskApiKey", 'substring(0, 4) + "***"')):
        if name not in impl:
            shape_ok = False
            detail.append("%s 未找到实现" % name)
            continue
        body = impl[name][1].split("public String %s(" % name, 1)[1][:400]
        hit = need in body
        detail.append("%s %s" % (name, "形状一致" if hit else "形状与声明不符"))
        shape_ok = shape_ok and hit
    result("A6 掩码实现形状与 javadoc 声明一致（手机 3+4 / api_key 4+4）", shape_ok, "；".join(detail))

    info("A7 测试背书", "掩码形态字符串断言 %d 处；含「明文/不得/永不」字样的断言 %d 处" % (shape_asserts, neg_asserts))

    print("")
    print("== 汇总 ==")
    print("断言 FAIL 数 = %d（%s）" % (len(problems), ", ".join(problems) or "无"))
    print("信息项 = %d" % len(infos))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
