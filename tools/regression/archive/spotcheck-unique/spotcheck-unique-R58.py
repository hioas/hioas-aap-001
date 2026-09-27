#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R58 抽查 v3：唯一性约束 ⇔ 冲突语义（第三十二类可审计不变量）—— 只读。

真源：
  U = DDL 唯一键（create unique index ... on <表> (<列>) [where <谓词>]；内联 primary key 单列信息项）
  I = 实现处置（① upsert: on conflict (...) ② 捕获: DuplicateKeyException/DataIntegrityViolationException
                 ③ 预查: 同方法内对该表唯一列做谓词查询 ④ 零处置）
  G = 全局兜底（GlobalExceptionHandler 是否映射唯一冲突）
  C = 契约可触发表面（requests/*.schema.json 属性 ∪ 路径变量 ∪ 查询参数，归一化）
  T = 测试背书（测试源对冲突业务码的断言）
分层（诚实分级，坑 81/125）：
  P = 实现有处置证据的唯一键（可机器判定处置方式：upsert / 捕获 / 仅预查）
  N = 零处置（无任何处置证据）；其中「唯一列名命中契约表面」仅作**弱证据**列出，需人工复核（存在同名碰撞，
      如 aap_role.code 与短信验证码 code 同名），不作硬断言。
只读：不写仓库任何文件。
"""
import re
import sys
import json
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("E:/workspaces/hioas/hioas-aap-001")
DDL = ROOT / "aap-server/src/main/resources/db/migration/V1__baseline.sql"
MD = ROOT / "docs/backend/02-API接口模型清单.md"
EP = ROOT / "docs/backend/endpoints.json"
REQ = ROOT / "docs/backend/json-schema/requests"
MAIN = ROOT / "aap-server/src/main/java"
TEST = ROOT / "aap-server/src/test/java"

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


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


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


def parse_ddl(text):
    keys = []
    for m in re.finditer(r"create\s+unique\s+index(?:\s+if\s+not\s+exists)?\s+(\w+)\s+on\s+(\w+)\s*\(", text, re.I):
        close = match_paren(text, m.end() - 1)
        if close < 0:
            continue
        cols = [c.strip() for c in text[m.end():close].split(",") if c.strip()]
        tail = text[close + 1: text.find(";", close)]
        pm = re.search(r"where\s+(.*)$", tail, re.S | re.I)
        pred = " ".join(pm.group(1).split()) if pm else ""
        keys.append({"name": m.group(1), "table": m.group(2), "cols": cols, "pred": pred, "kind": "unique index"})
    for m in re.finditer(r"create\s+table(?:\s+if\s+not\s+exists)?\s+(\w+)\s*\(", text, re.I):
        close = match_paren(text, m.end() - 1)
        if close < 0:
            continue
        tbl, body = m.group(1), text[m.end():close]
        for pk in re.finditer(r"^\s*(\w+)\s+[\w()\s]*?primary\s+key\b", body, re.M | re.I):
            c = pk.group(1)
            if c.lower() in ("create", "constraint", "primary"):
                continue
            keys.append({"name": "pk:%s.%s" % (tbl, c), "table": tbl, "cols": [c], "pred": "",
                         "kind": "inline primary key"})
        for cpk in re.finditer(r"primary\s+key\s*\(([^)]*)\)", body, re.I):
            cols = [c.strip() for c in cpk.group(1).split(",") if c.strip()]
            keys.append({"name": "pk:%s(%s)" % (tbl, ",".join(cols)), "table": tbl, "cols": cols, "pred": "",
                         "kind": "table primary key"})
    return keys


def java_files(base):
    return sorted([p for p in base.rglob("*.java") if p.is_file()])


def snake_to_pascal(t):
    if t.startswith("aap_"):
        t = t[4:]
    return "".join(p.capitalize() for p in t.split("_"))


def methods_of(text):
    """按行首修饰符定位方法签名（限定同一行内，避免跨行贪婪吞掉整份文件），再用括号深度扫描方法体。"""
    out = []
    for m in re.finditer(r"^[ \t]*(?:public|private|protected)[ \t]+([^\n(]*?)\b(\w+)[ \t]*\(",
                         text, re.M):
        name = m.group(2)
        i = m.end() - 1
        depth, j = 0, i
        while j < len(text):
            ch = text[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        b = text.find("{", j + 1)
        if b < 0:
            continue
        depth, k = 0, b
        while k < len(text):
            ch = text[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append((name, m.start(), k + 1))
    return out


def build_index(files):
    idx = []
    for p in files:
        t = read(p)
        if t:
            idx.append({"path": p, "text": t, "methods": methods_of(t)})
    return idx


def table_tokens(idx, table):
    """该表在实现里的引用 token：@Table 实体类名 / 其 Mapper 接口名 / 表字面量。
    Mapper↔表 的关联走「BaseMapper<X> 的 X → @Table 声明的表名」映射（不靠命名猜测）。"""
    toks = {table}
    entity2table = {}
    for e in idx:
        for m in re.finditer(r"@Table\(\s*value\s*=\s*\"(\w+)\"", e["text"]):
            cm = re.search(r"(?:public\s+)?(?:class|record)\s+(\w+)", e["text"][m.end(): m.end() + 400])
            if cm:
                entity2table[cm.group(1)] = m.group(1)
    for e in idx:
        for m in re.finditer(r"interface\s+(\w+Mapper)\b", e["text"]):
            seg = e["text"][m.start(): m.start() + 400]
            bm = re.search(r"BaseMapper\s*<\s*(\w+)", seg)
            if bm and entity2table.get(bm.group(1)) == table:
                toks.add(m.group(1))
        for m in re.finditer(r"@Table\(\s*value\s*=\s*\"%s\"" % re.escape(table), e["text"]):
            cm = re.search(r"(?:public\s+)?(?:class|record)\s+(\w+)", e["text"][m.end(): m.end() + 400])
            if cm:
                toks.add(cm.group(1))
    toks |= {lower_camel(t) for t in list(toks) if t[:1].isupper()}
    return toks


def refs_table(text, toks):
    return any(re.search(r"\b%s\b" % re.escape(t), text) for t in toks)


def lower_camel(t):
    return t[0].lower() + t[1:] if t and t[0].isupper() else t


def precheck_methods(idx, table, cols, toks):
    """返回 [(file#method, strong)]；strong = 方法体内含存在性/计数上下文（selectCount/count(/exists）。"""
    hits = []
    for e in idx:
        if not refs_table(e["text"], toks):
            continue
        for name, s, en in e["methods"]:
            body = e["text"][s:en]
            if not refs_table(body, toks):
                continue
            if not re.search(r"select|count|Query|exists", body, re.I):
                continue
            if all(re.search(r"\b%s\b\s*(?:=|is\s+not\s+null|in\s*\()" % re.escape(c), body, re.I) for c in cols):
                strong = bool(re.search(r"selectCount|count\s*\(|exists", body, re.I))
                hits.append(("%s#%s" % (e["path"].name, name), strong))
    return hits


def catch_files(idx, table, toks):
    """捕获证据 = 真的出现 catch 子句（只 import 不算，否则「删掉捕获」的注入判不出来）。"""
    return [e["path"].name for e in idx
            if refs_table(e["text"], toks)
            and re.search(r"catch\s*\(\s*(DuplicateKeyException|DataIntegrityViolationException)", e["text"])]


def upsert_hits(idx, table, cols):
    want = ",".join(c.lower() for c in cols)
    hits = []
    for e in idx:
        for m in re.finditer(r"on\s+conflict\s*\(([^)]*)\)", e["text"], re.I):
            got = ",".join(x.strip().lower() for x in m.group(1).split(",") if x.strip())
            if got == want and table in e["text"]:
                hits.append(e["path"].name)
    return hits


def jload(p, default):
    try:
        return json.loads(read(p))
    except ValueError:
        return default


def contract_surface():
    surface = set()
    for p in sorted(REQ.glob("*.schema.json")):
        d = jload(p, {})
        for k in (d.get("properties") or {}):
            surface.add(norm(k))
    ep = jload(EP, {})
    n_path = n_query = 0
    for e in ep.get("endpoints", []):
        for v in re.findall(r"\{(\w+)\}", e.get("path", "")):
            surface.add(norm(v))
            n_path += 1
        for q in e.get("query_params") or []:
            surface.add(norm(q))
            n_query += 1
    return surface, len(ep.get("endpoints", [])), n_path, n_query


def name_hit(cols, surface):
    for c in cols:
        n = norm(c)
        if n in surface:
            return True
        for s in surface:
            if s and n.startswith(s) and len(n) > len(s):
                return True
    return False


def main():
    keys = parse_ddl(read(DDL))
    idx = build_index(java_files(MAIN))
    tsrc = "\n".join(read(p) for p in java_files(TEST))
    md = read(MD)
    surface, n_ep, n_path, n_query = contract_surface()

    print("== R58 抽查：唯一性约束 ⇔ 冲突语义（第三十二类可审计不变量）==")
    print("真源：U=DDL 唯一键 / I=实现处置 / G=全局兜底 / C=契约可触发表面 / T=测试背书")
    print()
    print("== 正向对照 ==")
    uidx = [k for k in keys if k["kind"] == "unique index"]
    pk = [k for k in keys if k["kind"] != "unique index"]
    if uidx:
        ok("A0a", "DDL 解析到唯一键 %d 条（unique index %d + inline primary key %d）" % (len(keys), len(uidx), len(pk)))
    else:
        fail("A0a", "DDL 未解析到唯一索引 —— 解析器失效")
    ok("A0b", "实现源文件 %d 个 / 方法 %d 个" % (len(idx), sum(len(e["methods"]) for e in idx)))
    if surface and n_ep:
        ok("A0c", "契约可触发表面：请求体属性 %d 名 ·端点 %d·路径变量 %d·查询参数 %d" %
           (len(surface), n_ep, n_path, n_query))
    else:
        fail("A0c", "契约可触发表面为空 —— 解析器失效")

    geh = read(MAIN / "com/hioas/aap/common/GlobalExceptionHandler.java")
    if not re.search(r"@ExceptionHandler\([^)]*(DuplicateKeyException|DataIntegrityViolationException)", geh):
        info("A0d", "GlobalExceptionHandler 无 DuplicateKeyException/DataIntegrityViolationException 分支"
                    " → 未被捕获的唯一冲突落 Exception 分支 = 500 E-2001")
    else:
        ok("A0d", "全局兜底已映射唯一冲突")

    rows = []
    for k in uidx:
        toks = table_tokens(idx, k["table"])
        rows.append({"key": k,
                     "pre": precheck_methods(idx, k["table"], k["cols"], toks),
                     "catch": catch_files(idx, k["table"], toks),
                     "upsert": upsert_hits(idx, k["table"], k["cols"])})
    handled = [r for r in rows if r["pre"] or r["catch"] or r["upsert"]]
    unhandled = [r for r in rows if not (r["pre"] or r["catch"] or r["upsert"])]
    if handled:
        ok("A0e", "唯一索引 %d 条：实现有处置证据 %d 条 / 零处置 %d 条" % (len(rows), len(handled), len(unhandled)))
    else:
        fail("A0e", "无任何处置证据 —— 解析器失效（先怀疑解析器，坑 46）")
    n_pre = sum(1 for r in rows if r["pre"])
    n_up = sum(1 for r in rows if r["upsert"])
    n_ca = sum(1 for r in rows if r["catch"])
    ok("A0f", "处置证据计数：预查 %d / upsert %d / 捕获 %d（含重复计数）" % (n_pre, n_up, n_ca))

    print()
    print("== A1 逐唯一索引处置 ==")
    strong_only, weak_only = [], []
    for r in rows:
        k = r["key"]
        how = "upsert" if r["upsert"] else ("捕获" if r["catch"] else ("仅预查" if r["pre"] else "零处置"))
        r["how"] = how
        r["strong"] = any(s for _, s in r["pre"])
        if how == "仅预查":
            (strong_only if r["strong"] else weak_only).append(k["name"])
        print("  %-30s %-28s cols=%-40s pred=%-46s → %s" %
              (k["name"], k["table"], ",".join(k["cols"]), k["pred"] or "-", how))
        if r["pre"]:
            names = sorted(set(n for n, _ in r["pre"]))
            nstrong = len([1 for _, s in r["pre"] if s])
            print("      预查证据（%d 处，其中强证据 %d）：%s" % (len(names), nstrong, "; ".join(names[:4])))
        if r["catch"]:
            print("      捕获证据：%s" % "; ".join(sorted(set(r["catch"]))))

    hit_strong = [n for n in strong_only
                  if name_hit(dict((r["key"]["name"], r) for r in rows)[n]["key"]["cols"], surface)]
    if hit_strong:
        fail("A2", "「仅靠强预查（查重后插入）、无捕获、无 upsert」且唯一列名命中契约表面 %d 条 —— "
                   "预查与写入之间无锁，并发重复提交撞唯一索引 → 500 E-2001，而契约承诺 409 业务码：%s"
             % (len(hit_strong), ",".join(hit_strong)))
    else:
        ok("A2", "「仅靠强预查 ∧ 契约表面命中」的唯一索引 = 0")
    # 人工核对补录（每条必须同时被机器判据命中；上限 6，防止「人工豁免」把规则架空，坑 57/68）
    MANUAL = {
        "uq_provider_uscc": "ProviderService.updateProfile → ensureUsccUnique(selectCount) → 写库；无捕获",
        "uq_credential_fingerprint": "CredentialService.create → ensureFingerprintUnique(selectCount) → insert；无捕获",
        "uq_credential_primary": "CredentialService.create:124-126 → demoteExistingPrimary(改旧主) → insert；无查重、无捕获",
        "uq_job_active": "DetectionService.createJob → hasActiveJob(selectCount) → enqueue(insert)；无捕获",
        "uq_quote_item_model": "QuoteService.setItems → selectOne(quote_id,model_name) 为空则 insert（check-then-insert）；无捕获",
    }
    unknown = [k for k in MANUAL if k in {r["key"]["name"] for r in rows} and k not in hit_strong]
    if unknown:
        fail("A2m", "人工补录项未被机器判据命中（补录不能凭空发明）：%s" % ",".join(unknown))
    else:
        ok("A2m", "人工补录 %d 条全部同时被机器判据命中（上限 6）" % len(MANUAL))
    if len(MANUAL) <= 6:
        ok("A2n", "人工补录条数 %d ≤ 上限 6（豁免不得把规则架空）" % len(MANUAL))
    else:
        fail("A2n", "人工补录 %d 条 > 上限 6" % len(MANUAL))
    for n in hit_strong:
        info("A2e", "%s 机制：%s" % (n, MANUAL.get(n, "（未人工核对）")))
    info("A2b", "仅靠强预查但列名未命中契约表面（服务端派生值，重复即代码缺陷）%d 条：%s" %
         (len(strong_only) - len(hit_strong),
          ",".join(n for n in strong_only if n not in hit_strong) or "-"))
    if weak_only:
        info("A2c", "预查证据为弱（方法内无计数/存在性上下文，可能只是按该列查询而非查重）%d 条：%s" %
             (len(weak_only), ",".join(weak_only)))

    hit_n = [r for r in unhandled if name_hit(r["key"]["cols"], surface)]
    if unhandled:
        info("A3", "零处置唯一索引 %d 条；其中「唯一列名命中契约表面」%d 条（弱证据，含同名碰撞需人工复核）：%s" %
             (len(unhandled), len(hit_n), ",".join(r["key"]["name"] for r in hit_n) or "-"))
        info("A3b", "零处置且列名未命中契约表面 %d 条：%s" %
             (len(unhandled) - len(hit_n),
              ",".join(r["key"]["name"] for r in unhandled if r not in hit_n) or "-"))
    else:
        ok("A3", "零处置唯一索引 = 0")

    print()
    print("== A4 部分唯一索引谓词（软删 / 可空）与主键信息项 ==")
    soft = [k for k in uidx if "deleted = false" in k["pred"].lower()]
    nullable = [k for k in uidx if "is not null" in k["pred"].lower()]
    flagpred = [k for k in uidx if re.search(r"(active_flag|primary_flag)\s*=\s*true", k["pred"], re.I)]
    if soft:
        ok("A4a", "带 `deleted = false` 谓词的部分唯一索引 %d 条；带 `is not null` %d 条；带 flag 谓词 %d 条（%s）" %
           (len(soft), len(nullable), len(flagpred), ",".join(k["name"] for k in flagpred) or "-"))
    else:
        fail("A4a", "未解析到任何部分唯一索引 —— 解析器失效")
    info("A4b", "ORM 预查（QueryWrapper/selectCountByQuery）的逻辑删除过滤由全局配置自动追加"
                "（mybatis-flex.global-config.logic-delete-column=deleted，application.yml:38）"
                "→ 与索引谓词 `deleted = false` 一致；jdbc 裸 SQL 预查需另核")
    info("A4c", "内联 primary key %d 条（id 由雪花/序列生成，重复即生成器缺陷，非业务冲突场景 → 不参与 A2/A3 判定）" % len(pk))

    print()
    print("== A5 测试背书 / 契约声明 ==")
    codes = sorted(set(re.findall(r"E-1[0-9]{3}", tsrc)))
    if codes:
        ok("A5a", "测试源出现业务码 %d 种：%s" % (len(codes), ",".join(codes)))
    else:
        fail("A5a", "测试源未出现任何业务码 —— 判据失效")
    md_conf = re.findall(r"\|\s*`(E-\d+)`\s*\|\s*(\d+)\s*\|\s*([^|]*(?:唯一|冲突)[^|]*)\|", md)
    if md_conf:
        ok("A5b", "md §4 码表「唯一/冲突」语义行 %d 条：%s" %
           (len(md_conf), "; ".join("%s→%s" % (a, b) for a, b, _ in md_conf)))
    else:
        fail("A5b", "md §4 未解析到唯一/冲突语义码 —— 解析器失效")
    ep = jload(EP, {})
    ep_conf = [(e["id"], [c for c in (e.get("error_codes") or []) if c in ("E-1104", "E-1301", "E-1402")])
               for e in ep.get("endpoints", [])]
    ep_conf = [x for x in ep_conf if x[1]]
    if ep_conf:
        ok("A5c", "endpoints.json 声明冲突类码的端点 %d 条：%s" %
           (len(ep_conf), "; ".join("%s:%s" % (i, ",".join(c)) for i, c in ep_conf)))
    else:
        fail("A5c", "endpoints.json 无端点声明冲突类码 —— 解析器失效或零声明")
    backed = [r for r in rows if any(re.search(r"\b%s\b" % re.escape(c), tsrc) for c in r["key"]["cols"])]
    if backed:
        ok("A5d", "唯一索引 %d 条中，唯一列名在测试源出现的 %d 条（弱证据）" % (len(rows), len(backed)))
    else:
        fail("A5d", "唯一列名在测试源零出现 —— 判据失效")
    # 冲突码是否有真实 HTTP 断言
    code_asserts = len(re.findall(r"E-1104|E-1301|E-1402", tsrc))
    ok("A5e", "测试源中冲突类码出现 %d 处（含断言与夹具）" % code_asserts)

    print()
    print("== 汇总 ==")
    for x in passes:
        print(x)
    for x in fails:
        print(x)
    for x in infos:
        print(x)
    print("汇总：PASS=%d FAIL=%d INFO=%d" % (len(passes), len(fails), len(infos)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
