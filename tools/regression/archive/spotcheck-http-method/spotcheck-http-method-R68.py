#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R68 抽查：**HTTP 方法语义 —— 读端点（GET）不得有写副作用**（第四十二类可审计不变量）。

为什么两套门禁都看不见：
  契约测试只把**响应体**与 JSON Schema 比对 ——「一个 GET 请求是否改了库」既不在任何 schema 里，
  也不体现在响应形状上（GET 改了库照样返回 200 + 合法 schema）；覆盖门禁只比「方法 + 路径」；
  openapi 与客户端 TS 不被任何测试读取/执行。
  → 204 例全绿也查不出「GET 顺手写了一条留痕/刷了一次缓存/推进了某个状态」，
     而 GET 会被浏览器预取、代理重放、客户端重试 → 写副作用会被重复触发（非幂等读）。

真源：
  E = 实现控制器映射注解（@GetMapping/@PostMapping/@PutMapping/@DeleteMapping/@PatchMapping）
  W = 实现写调用点（JdbcTemplate 写语句〔含**常量引用**的 SQL〕+ ORM mapper 写方法）
  C = 调用链（深度 ≤3，**接收者类型感知** + **按实参个数选重载** 解析）累计写次数
  M = docs/backend/endpoints.json 方法分布（跨源对照）
  T = 测试源（方法语义类用例的调用点计数，作正向对照）

判据：
  A1 读端点（GET）：链上累计写调用点必须 = 0（豁免类须有依据注释 + 条数上限 1）
  A2 写端点（POST/PUT/PATCH/DELETE）：链上累计写调用点必须 ≥ 1（否则「声明写却不落库」）
     —— 调用链未能解析（节点数 = 1）的降级为「未能静态判定」信息项，并设上限
  A3 实现方法分布 vs 清单方法分布（跨源，已知超出契约的 1 条调试路由单列）

用法：python spotcheck-http-method-R68.py [--root E:/workspaces/hioas/hioas-aap-001] [--src <main 源码目录>]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

WRITE_VERB = re.compile(r"\b(insert\s+into|update\s+\w+\s+set|delete\s+from)\b", re.I)
JDBC_WRITE = re.compile(r"\b\w*jdbc\w*\.(?:update|execute)\s*\(")
ORM_WRITE = re.compile(r"\b(\w*[Mm]apper)\s*\.\s*(insert|update|delete|insertBatch|updateById|deleteById|deleteByQuery)\w*\s*\(")
MAPPING_ANNOS = ("GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping")
METHOD_OF = {"GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
             "DeleteMapping": "DELETE", "PatchMapping": "PATCH"}
READ_METHODS = ("GET",)
CALL_RE = re.compile(r"(?:(?<![\w])(\w+)\s*\.\s*)?(?<![\w])(\w+)\s*\(")
FIELD_RE = re.compile(r"(?m)^[ \t]*(?:private|protected|public)\s+(?:static\s+)?(?:final\s+)?"
                      r"([\w.$]+(?:\s*<[^;=]*>)?)\s+(\w+)\s*(?:=|;)")
METHOD_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:public|protected|private|static|final|synchronized|abstract|default|native)\s+)+"
    r"([\w.$<>\[\],\s?]+?)\s+(\w+)\s*\(")
CONST_RE = re.compile(r"(?m)^[ \t]*(?:private|protected|public)?\s*static\s+final\s+String\s+(\w+)\s*=")
EXEMPT_DOC = re.compile(r"(缓存|留痕|审计|刷新|幂等读|预取|后台任务|调度)")
# 写方法却**声明为只读语义**（如 POST 试算/预览）：须有 javadoc 依据 + 条数上限（坑 57/68/152）
EXEMPT_WRITE_DOC = re.compile(r"(只算不落库|不落库|仅计算|只读|试算|预览（不|dry-?run)")


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


def anno_window(src: str, sig_start: int) -> str:
    """签名之前**紧邻的注解串**（行级向上走；遇非注解/非空行即停，坑 55/63/124）。"""
    lines = src[:sig_start].split("\n")
    buf, i = [], len(lines) - 1
    while i >= 0:
        t = lines[i].strip()
        if t == "":
            if buf:
                break
            i -= 1; continue
        if t.startswith("@"):
            buf.append(t)
            while buf and buf[0].count("(") > buf[0].count(")"):
                i -= 1
                if i < 0:
                    break
                buf.insert(0, lines[i].strip())
            i -= 1; continue
        break
    return "\n".join(buf)


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
    """从 from_idx 起（**注解右括号之后**，坑 124）用括号深度扫描找方法体 `{`。"""
    i, n = from_idx, len(src)
    while i < n:
        c = src[i]
        if c in '"\'':
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


def first_arg(src: str, open_idx: int):
    """取调用的**第一个实参文本**（顶层逗号/右括号为界）。"""
    depth, i, n = 1, open_idx + 1, len(src)
    start = i
    while i < n:
        c = src[i]
        if c in '"\'':
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2; continue
                if src[i] == c:
                    break
                i += 1
        elif c == "(":
            depth += 1
        elif c in "),":
            depth -= 1
            if depth == 0:
                return src[start:i].strip()
        i += 1
    return ""


def arg_count(src: str, open_idx: int) -> int:
    """**顶层逗号**数 + 1（空实参表 → 0）。"""
    if open_idx < 0:
        return 0
    close = match_paren(src, open_idx)
    if close < 0:
        return 0
    inner = src[open_idx + 1:close]
    if not inner.strip():
        return 0
    depth, cnt, i, n = 0, 1, 0, len(inner)
    while i < n:
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
            cnt += 1
        i += 1
    return cnt


def collect_consts(src: str):
    """String 常量 → 字面量文本（坑 98/152：SQL 常写成 `static final String X = \"\"\"…\"\"\"`）。"""
    out = {}
    for m in CONST_RE.finditer(src):
        tail = src[m.end():m.end() + 6000]
        if tail.lstrip().startswith('"""'):
            j = tail.find('"""', tail.find('"""') + 3)
            out[m.group(1)] = tail[:j] if j > 0 else tail[:2000]
        else:
            j = tail.find(";")
            out[m.group(1)] = tail[:j] if j > 0 else tail[:2000]
    return out


def write_kind(sql_text: str):
    m = WRITE_VERB.search(sql_text)
    return m.group(1).split()[0].lower() if m else None


def simple_type(typ: str) -> str:
    """`com.hioas.aap.compile.CompilationService` → `CompilationService`（坑 98/57：跨源先归一）。"""
    return typ.split(".")[-1].strip()


def method_of(win: str):
    for a in MAPPING_ANNOS:
        if re.search(r"@" + a + r"\b", win):
            return METHOD_OF[a]
    m = re.search(r"@RequestMapping\b[^)]*method\s*=\s*(?:RequestMethod\.)?(\w+)", win)
    if m:
        return m.group(1).upper()
    return None


def _strip_literals(t: str) -> str:
    """剥掉字符串/字符字面量（注解实参里的**路径变量花括号**会误判，坑 55/124）。"""
    out, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c in '"\'':
            i += 1
            while i < n and t[i] != c:
                i += 2 if t[i] == "\\" else 1
            i += 1
            out.append(" ")
            continue
        out.append(c)
        i += 1
    return "".join(out)


def javadoc_before(raw: str, sig_start: int) -> str:
    """签名**紧邻**的 javadoc（只有注解/空白分隔时才认，坑 81/140：固定回看窗口会把上一个方法的 javadoc 吞进来）。"""
    end = raw.rfind("*/", 0, sig_start)
    if end < 0:
        return ""
    start = raw.rfind("/**", 0, end)
    if start < 0:
        return ""
    gap = _strip_literals(raw[end + 2:sig_start])
    if any(ch in gap for ch in ";}"):
        return ""
    return raw[start:end + 2]


def parse_file(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    src = strip_comments(raw)
    consts = collect_consts(src)
    cm = re.search(r"(?m)^[ \t]*(?:public\s+|final\s+|abstract\s+)*class\s+(\w+)", src)
    cls = cm.group(1) if cm else path.stem
    class_anno, class_doc = None, ""
    if cm:
        head = src[:cm.start()]
        hits = list(re.finditer(r"@Transactional\b", head))
        if hits:
            class_anno = hits[-1].group(0)
        raw_head = raw[:raw.find(cls)] if cls in raw else ""
        class_doc = raw_head[-1500:]
    fields = {}
    for fm in FIELD_RE.finditer(src):
        fields[fm.group(2)] = simple_type(re.sub(r"<.*", "", fm.group(1).strip()))
    methods = []
    for mm in METHOD_RE.finditer(src):
        name = mm.group(2)
        win = anno_window(src, mm.start())
        txm = re.search(r"@Transactional\s*(\([^)]*\))?", win)
        oi = src.find("(", mm.end() - 1)
        ci = match_paren(src, oi)
        if ci < 0:
            continue
        b, e = find_body_start(src, ci + 1)
        if b < 0:
            continue
        n_params = arg_count(src, oi)
        body = src[b:e + 1]
        writes, wdetail, unresolved = 0, [], []
        for wm in JDBC_WRITE.finditer(body):
            boi = body.find("(", wm.end() - 1)
            arg = first_arg(body, boi) if boi >= 0 else ""
            kind = write_kind(consts.get(arg, arg) if arg else "")
            if kind:
                writes += 1
                wdetail.append("jdbc:" + kind + ("(%s)" % arg if arg in consts else ""))
            else:
                unresolved.append("jdbc:" + (arg[:40] or "?"))
        for om in ORM_WRITE.finditer(body):
            writes += 1
            wdetail.append("orm:%s.%s" % (om.group(1), om.group(2)))
        calls = []
        for cmm in CALL_RE.finditer(body):
            coi = body.find("(", cmm.end() - 1)
            calls.append((cmm.group(1) or "", cmm.group(2), arg_count(body, coi)))
        methods.append({
            "cls": cls, "file": str(path), "name": name,
            "line": src[:b].count("\n") + 1,
            "tx": txm.group(0) if txm else None,
            "annos": re.findall(r"@(\w+)", win),
            "http": method_of(win),
            "doc": javadoc_before(raw, mm.start()),
            "writes": writes, "wdetail": wdetail, "unresolved": unresolved,
            "params": n_params,
            "calls": calls, "body": body,
        })
    return {"cls": cls, "path": path, "class_anno": class_anno, "class_doc": class_doc,
            "fields": fields, "methods": methods, "src": src}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--src", default=None)
    ap.add_argument("--show-all", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    base = Path(args.src) if args.src else root / "aap-server/src/main/java"
    testdir = root / "aap-server/src/test/java"
    manifest = root / "docs/backend/endpoints.json"

    fails, passes, infos = [], [], []
    def fail(t): fails.append("[FAIL] " + t)
    def ok(t): passes.append("[PASS] " + t)
    def info(t): infos.append("[INFO] " + t)

    parsed = [parse_file(p) for p in sorted(base.rglob("*.java"))]
    allm, by_name, by_cls = [], {}, {}
    for d in parsed:
        for mm in d["methods"]:
            mm["class_anno"] = d["class_anno"]
            mm["class_doc"] = d["class_doc"]
            mm["fields"] = d["fields"]
            allm.append(mm)
            by_name.setdefault(mm["name"], []).append(mm)
            by_cls.setdefault(mm["cls"], []).append(mm)

    def param_count(m):
        return m["params"]

    def resolve(recv, name, arity, caller):
        """接收者类型感知（坑 111-⑤/156）+ **按实参个数选重载**（重载被丢弃会让链断掉）。"""
        if recv:
            typ = caller["fields"].get(recv)
            if typ and typ in by_cls:
                sub = [m for m in by_cls[typ] if m["name"] == name]
            elif recv == "this":
                sub = [m for m in by_cls.get(caller["cls"], []) if m["name"] == name]
            else:
                return None
        else:
            sub = [m for m in by_cls.get(caller["cls"], []) if m["name"] == name]
            if not sub:
                cands = by_name.get(name, [])
                sub = cands if len(cands) == 1 else []
        if not sub:
            return None
        if len(sub) == 1:
            return sub[0]
        exact = [m for m in sub if param_count(m) == arity]
        if len(exact) == 1:
            return exact[0]
        return None

    for mm in allm:
        mm["callers"] = []
    resolved_pairs = 0
    for caller in allm:
        for recv, nm, arity in caller["calls"]:
            t = resolve(recv, nm, arity, caller)
            if t is not None and t is not caller:
                caller.setdefault("callees", []).append(t)
                t["callers"].append(caller)
                resolved_pairs += 1

    eps = [mm for mm in allm if mm["http"]]
    rows = []
    for ep in eps:
        seen, frontier, total, depth, detail, unres = set(), [ep], 0, 0, [], []
        while frontier and depth <= 3:
            nxt = []
            for node in frontier:
                key = (node["cls"], node["line"], node["name"])
                if key in seen:
                    continue
                seen.add(key)
                total += node["writes"]
                unres.extend("%s:%d %s(%s)" % (node["cls"], node["line"], node["name"], u)
                             for u in node.get("unresolved", []))
                if node["writes"]:
                    detail.append("%s:%d %s(%s)" % (node["cls"], node["line"], node["name"],
                                                    ",".join(node["wdetail"])))
                nxt.extend(node.get("callees", []))
            frontier = nxt
            depth += 1
        rows.append({"ep": ep, "writes": total, "nodes": len(seen), "detail": detail, "unres": unres})

    n_writes = sum(mm["writes"] for mm in allm)
    gets = [r for r in rows if r["ep"]["http"] in READ_METHODS]
    wr_eps = [r for r in rows if r["ep"]["http"] not in READ_METHODS]
    dist = Counter(r["ep"]["http"] for r in rows)

    # ---------------- A0*：正向对照（每条 > 0，坑 46/75/98/132） ----------------
    if parsed:
        ok("A0a 解析到 main 源码文件 %d 个" % len(parsed))
    else:
        fail("A0a 解析到 main 源码文件 0 个 → 判定不可用（坑 46/98/132）")
    if allm:
        ok("A0b 解析到方法 %d 个" % len(allm))
    else:
        fail("A0b 解析到方法 0 个 → 解析器失效")
    if eps:
        ok("A0c 解析到控制器映射方法 %d 个（清单端点 90）" % len(eps))
    else:
        fail("A0c 映射方法 0 个 → 解析器失效")
    if gets:
        ok("A0d 解析到读端点（GET）%d 个" % len(gets))
    else:
        fail("A0d 读端点 0 个 → 判定不可用")
    if wr_eps:
        ok("A0e 解析到写端点（POST/PUT/PATCH/DELETE）%d 个" % len(wr_eps))
    else:
        fail("A0e 写端点 0 个 → 判定不可用")
    if n_writes:
        ok("A0f 解析到写调用点 %d 处（含常量引用 SQL）" % n_writes)
    else:
        fail("A0f 写调用点 0 处 → 解析器失效")
    if resolved_pairs:
        ok("A0g 调用点解析成功 %d 对（接收者类型感知 + 实参个数选重载）" % resolved_pairs)
    else:
        fail("A0g 调用点解析 0 对 → 调用图失效")
    deep = [r for r in rows if r["nodes"] >= 2]
    if deep:
        ok("A0h 调用链解析到 ≥2 个节点的端点 %d 个" % len(deep))
    else:
        fail("A0h 调用链解析 0 个（定位率塌陷 → 全部断言空转，坑 87/111）")

    # ---------------- A1：读端点不得有写副作用 ----------------
    bad_get = [r for r in gets if r["writes"] > 0]
    exempt = [r for r in bad_get if EXEMPT_DOC.search(r["ep"]["doc"] or "")]
    if not gets:
        fail("A1 判定不可用：读端点集合为空（坑 98/141）")
    elif not bad_get:
        ok("A1 全部 %d 个读端点（GET）链上累计写调用点 = 0（读语义无副作用）" % len(gets))
    else:
        for r in bad_get:
            tag = "（豁免：依据注释命中 %s）" % EXEMPT_DOC.search(r["ep"]["doc"]).group(1) if r in exempt else ""
            fail("A1 读端点链上有写副作用%s：%s.%s:%d（累计写 %d：%s）"
                 % (tag, r["ep"]["cls"], r["ep"]["name"], r["ep"]["line"], r["writes"], "; ".join(r["detail"])))
    if len(exempt) > 1:
        fail("A1b 读端点写副作用豁免 %d 条超上限 1 → 豁免被架空（坑 57/68）" % len(exempt))
    else:
        ok("A1b 读端点写副作用豁免 %d 条 ≤ 上限 1" % len(exempt))

    # ---------------- A2：写端点必须有写调用点 ----------------
    zero_w = [r for r in wr_eps if r["writes"] == 0]
    unresolved_w = [r for r in zero_w if r["nodes"] == 1]
    # 豁免类：**写方法但 javadoc 声明只读语义**（POST 试算/预览），须有依据 + 上限（坑 57/68/152）
    exempt_w = [r for r in zero_w if r["nodes"] > 1 and EXEMPT_WRITE_DOC.search(r["ep"]["doc"] or "")]
    real_zero = [r for r in zero_w if r["nodes"] > 1 and r not in exempt_w]
    if not wr_eps:
        fail("A2 判定不可用：写端点集合为空（坑 98/141）")
    elif not real_zero:
        ok("A2 全部 %d 个写端点在已解析的调用链上都有写调用点（≥1；豁免 %d 条：javadoc 声明只读语义，见 A2e）"
           % (len(wr_eps) - len(unresolved_w) - len(exempt_w), len(exempt_w)))
    else:
        for r in real_zero:
            fail("A2 写端点调用链上零写调用点（声明写却不落库，或写入路径未被解析）：%s.%s:%s:%d（节点 %d，未能静态判定 %d）"
                 % (r["ep"]["cls"], r["ep"]["name"], r["ep"]["http"], r["ep"]["line"], r["nodes"], len(r["unres"])))
    if len(exempt_w) > 2:
        fail("A2e 只读语义豁免 %d 条超上限 2 → 豁免被架空（坑 57/68）" % len(exempt_w))
    else:
        ok("A2e 只读语义豁免 %d 条 ≤ 上限 2" % len(exempt_w))
    for r in exempt_w:
        info("A2f 写端点按 javadoc 声明为只读语义（豁免，链上 0 写；依据关键词命中）：%s.%s:%s:%d"
             % (r["ep"]["cls"], r["ep"]["name"], r["ep"]["http"], r["ep"]["line"]))
    if len(unresolved_w) > 2:
        fail("A2b 「未能静态判定」的写端点 %d 条超上限 2 → 该豁免把规则架空（坑 57/68/98）" % len(unresolved_w))
    else:
        ok("A2b 「未能静态判定」的写端点 %d 条 ≤ 上限 2" % len(unresolved_w))
    for r in unresolved_w:
        info("A2c 写端点调用链未能解析（节点数=1）：%s.%s:%s:%d"
             % (r["ep"]["cls"], r["ep"]["name"], r["ep"]["http"], r["ep"]["line"]))
    for r in rows:
        for u in r["unres"]:
            info("A2d 写调用点未能静态判定（实参非字面量/非常量）：%s.%s → %s"
                 % (r["ep"]["cls"], r["ep"]["name"], u))

    # ---------------- A3：方法分布跨源对照（清单 vs 实现） ----------------
    mdist = Counter()
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        items = data["endpoints"] if isinstance(data, dict) and "endpoints" in data else data
        mdist = Counter(str(e.get("method", "")).upper() for e in items)
    if not mdist:
        fail("A3 判定不可用：清单方法分布为空（文件缺失或解析失效）")
    else:
        diffs = []
        for meth in sorted(set(dist) | set(mdist)):
            if dist.get(meth, 0) != mdist.get(meth, 0):
                diffs.append("%s 实现 %d / 清单 %d" % (meth, dist.get(meth, 0), mdist.get(meth, 0)))
        if not diffs:
            ok("A3 实现方法分布与清单逐方法一致（%s）" % dict(sorted(dist.items())))
        else:
            extra = sum(max(0, dist.get(m, 0) - mdist.get(m, 0)) for m in set(dist) | set(mdist))
            if extra <= 1 and all(dist.get(m, 0) >= mdist.get(m, 0) for m in set(dist) | set(mdist)):
                ok("A3 实现方法分布 ⊇ 清单（差异：%s；已知 1 条超出冻结契约的 GET 调试路由，坑 61）" % "; ".join(diffs))
            else:
                for d in diffs:
                    fail("A3 实现方法分布与清单不一致（方法语义漂移）：%s" % d)

    # ---------------- A4：测试背书（方法语义类用例） ----------------
    tsrc = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in sorted(testdir.rglob("*.java"))) if testdir.exists() else ""
    get_calls = len(re.findall(r"\.get\(\"", tsrc)) + len(re.findall(r"get\(\s*\"/", tsrc))
    if not tsrc:
        fail("A4 判定不可用：测试源为空")
    elif get_calls == 0:
        fail("A4 测试源零 GET 调用点 → 读端点无语义用例（判定不可用）")
    else:
        ok("A4 测试源存在 GET 调用点 %d 处（读端点有真实 HTTP 用例的结构级背书）" % get_calls)

    print("== R68 抽查：HTTP 方法语义（读端点写副作用） ==")
    print("扫描目录：%s（%d 个 .java）" % (base, len(parsed)))
    print("方法 %d 个；写调用点 %d 处；映射方法 %d 个；方法分布 %s；调用点解析成功 %d 对"
          % (len(allm), n_writes, len(eps), dict(sorted(dist.items())), resolved_pairs))
    print("读端点 %d 个（链上写 > 0 者 %d）；写端点 %d 个（链上写 = 0 者 %d，其中未能解析 %d）"
          % (len(gets), len(bad_get), len(wr_eps), len(zero_w), len(unresolved_w)))
    print()
    print("-- 读端点链上写副作用明细（应全为 0） --")
    for r in sorted(gets, key=lambda x: -x["writes"]):
        if r["writes"] or args.show_all:
            print("    %-28s %-24s L%-5d 节点=%-3d 写=%d" % (r["ep"]["cls"], r["ep"]["name"], r["ep"]["line"], r["nodes"], r["writes"]))
            for d in r["detail"]:
                print("        %s" % d)
    print()
    print("-- 写端点链上零写明细 --")
    for r in sorted(zero_w, key=lambda x: x["ep"]["cls"]):
        print("    %-28s %-24s %-6s L%-5d 节点=%-3d 未能静态判定=%d"
              % (r["ep"]["cls"], r["ep"]["name"], r["ep"]["http"], r["ep"]["line"], r["nodes"], len(r["unres"])))
    print()
    for ln in passes:
        print(ln)
    for ln in infos:
        print(ln)
    for ln in fails:
        print(ln)
    print()
    print("PASS %d / FAIL %d / INFO %d" % (len(passes), len(fails), len(infos)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
