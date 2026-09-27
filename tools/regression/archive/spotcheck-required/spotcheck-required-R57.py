#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R57 抽查 v2：请求体字段「必填性（required vs optional）」跨源一致性 + required 的运行时强制。

第三十一类可审计不变量。为什么两套门禁都看不见：
  * 契约测试把**真实响应**与 JSON Schema 比对（`SchemaAssert`；`json-schema-validator` 是 `<scope>test</scope>`）
    → **请求模型 schema 运行时不参与任何校验**；「schema 说必填 / 实现不校验 / md 没标」这类漂移对全部用例完全不可见；
  * 覆盖门禁只比「方法 + 路径」；openapi 与客户端 TS 不被任何测试执行。

真源：
  M   docs/backend/02-API接口模型清单.md 「请求」列（`?` = 显式可选标记；反引号式 / 花括号式两种写法）
  S   docs/backend/json-schema/requests/*.schema.json（`required` 数组 + 逐属性 type 是否含 "null"）
  D   docs/backend/endpoints.json（request_model 绑定）
  I   aap-server/src/main/java/**/*Controller.java（@RequestBody DTO 分量 + 校验注解）+ 服务层 null 守卫
  R   运行时强制（pom 依赖 scope + main 源码引用点）
  T   aap-server/src/test/java（缺字段 / 显式 null 的用例断言）
  G   aap-server/src/main/resources/db/migration/*.sql（NOT NULL 兜底，信息项）

v2 修复（v1 的真实返工，坑 46/75/98）：
  * v1 把注解名捕获成 `NotBlank` 而白名单写成 `@NotBlank` → 交集恒空 → A3「无强制证据」假发现 8 条、
    **A4 的 PASS 是空转假绿**（「0 发现先怀疑解析器」的又一实例；A0e 的「带必填类注解 0 个」是唯一指纹）；
  * v1 未做 import 解析 → 3 个端点（SaveRequest 在 *Views.java）判「未判定」；
  * v1 的 null 守卫判据不认 record 访问器写法（`req.file_id() == null`）与 `isBlank(x)`。

只读保证：不写任何仓库文件；Z1 用 (mtime_ns, size, md5) 核对全部被读文件未被改动。
用法：python <此脚本> [--root <dir>] [--dump-md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

MD_DOC = "docs/backend/02-API接口模型清单.md"
ENDPOINTS = "docs/backend/endpoints.json"
REQ_DIR = "docs/backend/json-schema/requests"
JAVA_DIR = "aap-server/src/main/java"
TEST_DIR = "aap-server/src/test/java"
POM = "aap-server/pom.xml"
DDL_DIR = "aap-server/src/main/resources/db/migration"

ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-(?:[A-Z]*\d+|[A-Z0-9]+)$")
ANN_RE = re.compile(r"@(NotBlank|NotNull|NotEmpty|Size|Pattern|Min|Max|Valid|Email)\b")
REQUIRED_ANN = ("NotBlank", "NotNull", "NotEmpty")
EVIDENCE_TIERS = {"注解", "守卫(直接)", "守卫(别名·直接)"}


def rel(p, root):
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve())).replace(os.sep, "/")
    except ValueError:
        return str(Path(p).resolve()).replace(os.sep, "/")


def fingerprint(paths):
    out = {}
    for p in paths:
        if not p.exists():
            continue
        st = p.stat()
        out[str(p)] = (st.st_mtime_ns, st.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    return out


def match_paren(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j
    return -1


def match_pair(s, i, op="{", cl="}"):
    """v2 修复（真实返工）：花括号必须用**花括号**配对扫描。

    v1 用 `match_paren`（只数圆括号）去配 `{...}` → 恒返回 -1 → 退化成 `brace[1:]`，
    末尾残留的 `}`/反引号让**最后一个**字段匹配失败 → 实测 `{phone, captcha}` 只解析到 `phone`、
    `{code}` 一个字段都解析不到、`{credential_id, trigger_type?}` 丢掉 `trigger_type?`
    （`A0b 可选 token 6` 是唯一指纹：真实应为 13）。指纹：**多字段花括号只解析到第一个字段**。
    """
    d = 0
    for j in range(i, len(s)):
        if s[j] == op:
            d += 1
        elif s[j] == cl:
            d -= 1
            if d == 0:
                return j
    return -1


def body_start(s, i):
    """从 i 起用括号深度扫描找方法体 `{`（坑 55/63/124；从注解右括号的**下一个**位置起步，坑 124）。"""
    d = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "{":
            if d == 0:
                return j
            d += 1
        elif c == "}":
            d -= 1
        j += 1
    return -1


def norm_key(method, path):
    p = path.replace("/api/v1", "", 1)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if not p.startswith("/"):
        p = "/" + p
    return method.upper(), p


def split_md_row(line):
    cells = re.split(r"(?<!\\)\|", line)
    out = [c.replace("\\|", "|") for c in cells]
    if out and out[0].strip() == "":
        out = out[1:]
    if out and out[-1].strip() == "":
        out = out[:-1]
    return [c.strip() for c in out]


def strip_comments(txt):
    out, i, n = [], 0, len(txt)
    while i < n:
        c = txt[i]
        if c in "\"'":
            q = c
            out.append(c)
            i += 1
            while i < n:
                if txt[i] == "\\":
                    out.append(txt[i:i + 2])
                    i += 2
                    continue
                out.append(txt[i])
                if txt[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if txt.startswith("//", i):
            j = txt.find("\n", i)
            i = n if j < 0 else j
            continue
        if txt.startswith("/*", i):
            j = txt.find("*/", i)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def top_level_parts(inner):
    parts, cur, d = [], "", 0
    for ch in inner:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == "," and d == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    parts.append(cur)
    return parts


# ------------------------------------------------------------------ M
def parse_md(root, eps=None):
    p = root / MD_DOC
    data, read = {}, []
    if not p.exists():
        return data, read
    read.append(p)
    eps = eps or {}
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    col = None
    for ln in lines:
        if not ln.lstrip().startswith("|"):
            continue
        cells = split_md_row(ln)
        if len(cells) < 6:
            continue
        if cells[0] == "ID" and ("请求" in cells or "请求/响应" in cells):
            col = cells.index("请求") if "请求" in cells else cells.index("请求/响应")
            continue
        if col is None or len(cells) <= col:
            continue
        eid = cells[0]
        if not ID_RE.match(eid):
            continue
        cell = cells[col]
        method = eps.get(eid, {}).get("method")
        if "q：" in cell or cell.startswith("q"):
            continue
        if method == "GET" and "body" not in cell:
            continue                      # GET 的「请求」列承载查询参数（坑 62/65：QT-11 裸 `page/pageSize`）
        body = cell.split("→")[0].strip() if "→" in cell else cell.strip()
        if body in ("", "—", "-", "无", "同上", "—（无请求体）"):
            continue
        if body.startswith("同") or "同 " in body:
            data[eid] = {"req": set(), "opt": set(), "mode": "引用式（未能静态判定）", "raw": body[:40]}
            continue
        req, opt, residual = set(), set(), body
        if "{" in body:
            brace = body[body.find("{"):]
            e = match_pair(brace, 0)          # v2：花括号配对（v1 用 match_paren → 只解析到第一个字段）
            inner = brace[1:e] if e > 0 else brace[1:]
            residual = body[:body.find("{")].strip()
            for part in top_level_parts(inner):
                s = part.strip()
                if not s:
                    continue
                m = re.match(r"^([A-Za-z_]\w*)\s*(\?)?\s*(?::|$)", s)
                if not m:
                    residual += " " + s
                    continue
                (opt if m.group(2) else req).add(m.group(1))
                if "[" in s and "{" in s:
                    residual += " [nested]"
        for name, q in re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)(\?)?`", body):
            (opt if q else req).add(name)
        text = body[4:] if body.startswith("body") else body
        text = re.sub(r"`[^`]*`", " ", text)
        text = re.sub(r"\{[^{}]*\}", " ", text)
        text = re.sub(r"[+、,，()（）\[\]:：*]", " ", text)
        text = re.sub(r"(八大单价|同上|同|必填|可选|无请求体)", " ", text)
        words = [w for w in text.split() if re.search(r"[\u4e00-\u9fa5A-Za-z]", w)]
        data[eid] = {"req": req, "opt": opt,
                     "mode": "完整" if not words else "部分（描述式残留 " + ",".join(words[:3]) + "）",
                     "raw": body[:60]}
    return data, read


# ------------------------------------------------------------------ S / D
def parse_schemas(root):
    base = root / REQ_DIR
    out, read = {}, []
    if not base.exists():
        return out, read
    for f in sorted(base.glob("*.schema.json")):
        read.append(f)
        name = f.name[: -len(".schema.json")]        # 坑 115
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as ex:                       # noqa: BLE001
            out[name] = {"err": str(ex), "required": set(), "props": set(), "nullable": set()}
            continue
        props = d.get("properties", {}) or {}
        nullable = set()
        for k, v in props.items():
            t = v.get("type")
            if (isinstance(t, list) and "null" in t) or t == "null":
                nullable.add(k)
        out[name] = {"required": set(d.get("required", []) or []), "props": set(props), "nullable": nullable}
    return out, read


def parse_endpoints(root):
    p = root / ENDPOINTS
    if not p.exists():
        return {}, []
    d = json.loads(p.read_text(encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("endpoints", [])
    return {e.get("id"): {"method": e.get("method"), "path": e.get("path"),
                          "request_model": e.get("request_model")} for e in items}, [p]


# ------------------------------------------------------------------ I
def parse_controllers(root):
    """→ ({(方法,归一路径): (控制器文件名, DTO 类型)}, DTO 表, 读过的文件)。"""
    base = root / JAVA_DIR
    routes, read = {}, []
    if not base.exists():
        return routes, {"by_file": {}, "global": {}}, read
    files = sorted(base.rglob("*Controller.java"))
    for f in files:
        read.append(f)
    for f in files:
        t = f.read_text(encoding="utf-8", errors="replace")
        bm = re.search(r'@RequestMapping\("([^"]+)"\)', t)
        bpath = bm.group(1) if bm else ""
        for m in re.finditer(r"@(Get|Post|Put|Patch|Delete)Mapping", t):
            http = m.group(1).upper()
            k = m.end()
            path = ""
            if k < len(t) and t[k] == "(":
                e = match_paren(t, k)
                if e < 0:
                    continue
                pm = re.search(r'"([^"]*)"', t[k + 1:e])
                path = pm.group(1) if pm else ""
                k = e + 1
            bs = body_start(t, k)
            if bs < 0:
                continue
            sig = t[k:bs]
            if "@RequestBody" not in sig:
                continue
            rb = re.search(r"@RequestBody", sig)
            rest = sig[rb.end():]
            if rest.startswith("("):
                e2 = match_paren(rest, 0)
                rest = rest[e2 + 1:] if e2 >= 0 else rest
            rest = re.sub(r"^\s*(?:(?:public|private|protected|static|final)\s+)+", "", rest)
            tm = re.match(r"\s*(?:@\w+(?:\([^)]*\))?\s+)*([A-Za-z_][\w.]*(?:\s*<[^>]*>)?)\s+(\w+)", rest)
            if not tm:
                continue
            routes[norm_key(http, bpath + path)] = (f.name, re.sub(r"\s+", "", tm.group(1)))
    # DTO record 分量（注解统一存成 `@NotBlank` 形式，v1 的返工点）
    by_file, seen = {}, {}
    for f in sorted(base.rglob("*.java")):
        if f not in read:
            read.append(f)
        t = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\brecord\s+([A-Z]\w*)\s*(<[^>(]*>)?\s*\(", t):
            name = m.group(1)
            e = match_paren(t, m.end() - 1)
            if e < 0:
                continue
            comps = {}
            for part in top_level_parts(t[m.end():e]):
                s = part.strip()
                if not s:
                    continue
                jp = re.search(r'@JsonProperty\("([^"]+)"\)', s)
                nm = re.findall(r"([A-Za-z_]\w*)\s*$", s)
                if not nm:
                    continue
                key = jp.group(1) if jp else nm[0]
                comps[key] = {"@" + a for a in ANN_RE.findall(s)}
            by_file.setdefault(f.name, {})[name] = comps
            seen[name] = seen.get(name, 0) + 1
    glob = {}
    for fname, recs in by_file.items():
        for name, comps in recs.items():
            glob[name] = None if seen[name] > 1 else comps
    return routes, {"by_file": by_file, "global": glob}, read


def resolve_dto(root, ctrl_file, typ, dtos):
    """同文件优先 → import 候选文件（坑 74/115 族）。"""
    simple = typ.split("<")[0].split(".")[-1]
    if ctrl_file and simple in dtos["by_file"].get(ctrl_file, {}):
        return dtos["by_file"][ctrl_file][simple], f"{ctrl_file}:{simple}"
    p = root / JAVA_DIR
    for f in p.rglob(f"{simple}.java"):
        if f.name in dtos["by_file"] and simple in dtos["by_file"][f.name]:
            return dtos["by_file"][f.name][simple], f"{f.name}:{simple}"
    if ctrl_file:
        ct = (p / ctrl_file)
        for cand in p.rglob("*.java"):
            if cand.name == ctrl_file:
                ct = cand
                break
        if ct.exists():
            t = ct.read_text(encoding="utf-8", errors="replace")
            for im in re.finditer(r"^\s*import\s+([\w.]+)\s*;", t, re.M):
                segs = im.group(1).split(".")
                if segs[-1] == simple and len(segs) >= 2:
                    fn = segs[-2] + ".java"
                    if simple in dtos["by_file"].get(fn, {}):
                        return dtos["by_file"][fn][simple], f"{fn}:{simple}"
    g = dtos["global"].get(simple)
    if g is not None:
        return g, f"(全局唯一){simple}"
    return None, simple


def parse_runtime(root):
    read, refs, scopes = [], 0, []
    p = root / POM
    if p.exists():
        read.append(p)
        t = p.read_text(encoding="utf-8", errors="replace")
        scopes = re.findall(r"<artifactId>json-schema-validator</artifactId>\s*<version>[^<]*</version>\s*<scope>(\w+)</scope>", t)
    for f in (root / JAVA_DIR).rglob("*.java"):
        read.append(f)
        if "com.networknt" in f.read_text(encoding="utf-8", errors="replace"):
            refs += 1
    return {"scopes": scopes, "main_refs": refs}, read


def parse_ddl(root):
    read, notnull = [], {}
    base = root / DDL_DIR
    if not base.exists():
        return notnull, read
    for f in sorted(base.glob("*.sql")):
        read.append(f)
        txt = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)\s*\(", txt, re.I):
            e = match_paren(txt, m.end() - 1)
            if e < 0:
                continue
            body = txt[m.end():e]
            for line in body.splitlines():
                s = line.strip().rstrip(",")
                if not s or s.lower().startswith(("primary key", "unique", "constraint", "check", "foreign")):
                    continue
                cm = re.match(r"^(\w+)\s+\S", s)
                if cm and re.search(r"\bnot\s+null\b", s, re.I):
                    notnull.setdefault(cm.group(1), set()).add(m.group(1))
    return notnull, read


def parse_tests(root):
    read, miss, nulls, ctors = [], 0, 0, 0
    base = root / TEST_DIR
    if not base.exists():
        return {"miss": 0, "null": 0, "body": 0, "files": 0, "missing_400": []}, read
    for f in sorted(base.rglob("*.java")):
        read.append(f)
        t = strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        ctors += len(re.findall(r"Map\.of\(|body\s*=\s*\"", t))
        miss += len(re.findall(r"缺少|未提供|missing", t))
        nulls += len(re.findall(r"put\(\s*\"\w+\"\s*,\s*null\s*\)|:\s*null\s*[,}]", t))
    return {"miss": miss, "null": nulls, "body": ctors, "files": len(read)}, read


# ------------------------------------------------------------------ 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--dump-md", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    md, r1 = parse_md(root, None)
    sch, r2 = parse_schemas(root)
    eps, r3 = parse_endpoints(root)
    md, _ = parse_md(root, eps)          # v2：md 解析需要端点方法（GET 的「请求」列是查询参数）
    routes, dtos, r4 = parse_controllers(root)
    rt, r5 = parse_runtime(root)
    ddl, r6 = parse_ddl(root)
    tt, r7 = parse_tests(root)
    read = r1 + r2 + r3 + r4 + r5 + r6 + r7
    snap = fingerprint(read)

    out, npass, nfail = [], 0, 0

    def chk(name, ok, detail=""):
        nonlocal npass, nfail
        if ok:
            npass += 1
        else:
            nfail += 1
        out.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"：{detail}" if detail else ""))
        return ok

    def info(t):
        out.append(t)

    out.append("== 请求体字段「必填性（required vs optional）」跨源一致性抽查（第三十一类不变量，只读） ==")
    out.append(f"仓库根：{root}")
    out.append("")
    out.append("--- A0 正向对照（每个源都必须真的解析到条目；任一为 0 先怀疑解析器，坑 46/75/98）---")
    n_body = sum(1 for v in md.values() if v["req"] or v["opt"])
    n_opt = sum(len(v["opt"]) for v in md.values())
    n_req = sum(len(v["req"]) for v in md.values())
    n_comp = sum(len(c) for c in dtos["global"].values() if c)
    n_ann = sum(1 for c in dtos["global"].values() if c for a in c.values() if a & {"@" + x for x in REQUIRED_ANN})
    chk("A0a M 解析到「有请求体」的端点 > 0", n_body > 0, f"{n_body} 个端点（md 解析行 {len(md)}）")
    chk("A0b M 解析到「显式可选（?）」token > 0（否则 `?` 解析器失效）", n_opt > 0,
        f"可选 token {n_opt}；必填候选 token {n_req}")
    chk("A0c S 解析到带 required 的请求模型 > 0", sum(1 for v in sch.values() if v.get("required")) > 0,
        f"请求模型 {len(sch)} 个，带 required {sum(1 for v in sch.values() if v.get('required'))} 个")
    chk("A0d S 解析到请求模型属性 > 0", sum(len(v.get("props", ())) for v in sch.values()) > 0,
        f"属性 {sum(len(v.get('props', ())) for v in sch.values())} 个")
    chk("A0e I 解析到控制器 DTO 分量 > 0", n_comp > 0, f"DTO 分量 {n_comp} 个")
    chk("A0f I 解析到带必填类注解的分量 > 0（v1 的返工点：注解名格式不一致 → 交集恒空）", n_ann > 0,
        f"带必填类注解 {n_ann} 个")
    chk("A0g I 解析到 @RequestBody 路由 > 0", len(routes) > 0, f"{len(routes)} 条路由带 @RequestBody")
    chk("A0h R 运行时强制证据已取证（必须真的读到 pom 依赖 scope；空输入不得空转判 PASS）",
        bool(rt["scopes"]) and rt["main_refs"] == 0,
        f"json-schema-validator scope={rt['scopes']}；main 源码引用点 {rt['main_refs']} 处")
    chk("A0i T 解析到测试请求体构造点 > 0", tt["body"] > 0, f"构造点 {tt['body']} 处（{tt['files']} 个测试文件）")
    chk("A0j G 解析到 DDL 的 NOT NULL 列 > 0", len(ddl) > 0, f"NOT NULL 列 {len(ddl)} 个")
    info("")
    if args.dump_md:
        info("--- [dump] M 逐端点解析结果 ---")
        for eid, v in sorted(md.items()):
            info(f"      · {eid} mode={v['mode']} req={sorted(v['req'])} opt={sorted(v['opt'])} raw={v['raw']!r}")
        info("")

    # A1
    drift1 = []
    for eid, v in sorted(md.items()):
        if not v["opt"]:
            continue
        m = eps.get(eid, {}).get("request_model")
        if not m or m not in sch:
            drift1.append((eid, f"md 标可选 {sorted(v['opt'])}，但清单无 request_model/模型缺失（{m}）"))
            continue
        bad = sorted(set(v["opt"]) & sch[m].get("required", set()))
        if bad:
            drift1.append((eid, f"{m}: md 标 {bad} 可选，而 schema.required 含之"))
    out.append("--- A1 md 显式可选（?）⊄ schema.required（逐端点，单向硬断言）---")
    chk("A1 md 标可选的字段都未出现在 schema.required", not drift1, f"不一致 {len(drift1)} 条")
    for eid, d in drift1[:12]:
        info(f"      · {eid}: {d}")
    info("")

    # A2
    drift2 = [(n, sorted(v.get("required", ()) & v.get("nullable", ())))
              for n, v in sorted(sch.items()) if v.get("required", set()) & v.get("nullable", set())]
    out.append("--- A2 schema.required 字段不得允许 null（required ∧ nullable = 校验放行 null）---")
    chk("A2 无「必填同时可空」的自相矛盾属性", not drift2,
        f"矛盾模型 {len(drift2)} 个：{ {n: b for n, b in drift2} }")
    info("")

    # A3 / A9
    main_txt = {}
    for f in (root / JAVA_DIR).rglob("*.java"):
        main_txt[f.name] = strip_comments(f.read_text(encoding="utf-8", errors="replace"))
    # 同包（同一目录）文件集合：守卫搜索范围按语义收窄（坑 81）
    pkg_files: dict[str, set] = {}
    for f in (root / JAVA_DIR).rglob("*.java"):
        pkg_files.setdefault(f.name, set()).update(
            g.name for g in f.parent.glob("*.java") if g.name != f.name)

    def guards(field, ctrl_file):
        """→ (tier, detail)。分级：注解 / 守卫(直接) / 守卫(别名) / 守卫(跨包) / 无。

        v3 修复（v2 的真实返工 = 1 条假发现）：`SyncAdminService.validateTargetStatus` 的写法是
        `String raw = request == null ? null : request.targetStatus(); if (raw == null || raw.isBlank()) …`
        —— 字段值被赋给**局部变量**后再判空，v2 只认「字段名本身 == null」→ 把 ADM-S05 判成「无强制」
        （指纹：报告说「实现零校验」而实现里 grep 得到 `targetStatus()` 与 `raw == null`）。
        规则：**回查别名**（坑 107 的正当做法），并在同包优先的范围内搜索（坑 81：判据范围与语义一致）。
        """
        camel = re.sub(r"_(\w)", lambda m: m.group(1).upper(), field)
        direct = [rf"(?:\w+\.)?{re.escape(camel)}\(\)\s*==\s*null",
                  rf"null\s*==\s*(?:\w+\.)?{re.escape(camel)}\(\)",
                  rf"Objects\.requireNonNull\(\s*(?:\w+\.)?{re.escape(camel)}",
                  rf"\b{re.escape(camel)}\s*==\s*null", rf"null\s*==\s*\b{re.escape(camel)}\b",
                  rf"\b{re.escape(field)}\s*==\s*null",
                  rf"isBlank\(\s*(?:\w+\.)?{re.escape(camel)}\(\)?",
                  rf"isBlank\(\s*\b{re.escape(field)}\b",
                  rf"缺少[^\"\n]{{0,12}}{re.escape(field)}"]
        pkg = ctrl_file
        same, other = {}, {}
        for fn, t in main_txt.items():
            (same if fn == ctrl_file or fn in pkg_files.get(ctrl_file, set()) else other)[fn] = t
        # 别名：`X = … field …` → 查 X 的判空
        alias_re = re.compile(rf"\b(\w+)\s*=\s*[^;\n]{{0,140}}?(?:\b{re.escape(camel)}\(\)|\b{re.escape(camel)}\b)")
        for fn, t in same.items():
            if any(re.search(p, t) for p in direct):
                return ("守卫(直接)", fn)
            for m in alias_re.finditer(t):
                a = m.group(1)
                if a == camel or a == field:
                    continue
                if re.search(rf"\b{re.escape(a)}\s*==\s*null|isBlank\(\s*\b{re.escape(a)}\b|null\s*==\s*\b{re.escape(a)}\b", t):
                    return ("守卫(别名·直接)", f"{fn}#{a}")
        # 跨包只作**弱证据**（坑 125-③：别的包里同名**形参**的判空不是对请求字段的校验 ——
        # 真实返工：`CryptoService.maskApiKey(String apiKey)` 的 `apiKey == null` 曾把
        # CRED-02 的 `api_key` 判成「已校验」，而 `encrypt(null)` 返回 null → 库 NOT NULL 违约 → 500）
        for fn, t in other.items():
            if any(re.search(p, t) for p in direct):
                return ("弱证据(跨包同名形参，不作数)", fn)
        return ("无", "")

    rows, no_force, undecided = [], [], []
    for eid, e in sorted(eps.items()):
        model = e.get("request_model")
        if not model or model not in sch:
            continue
        key = norm_key(e.get("method"), e.get("path"))
        ctrl = routes.get(key)
        if not ctrl:
            undecided.append((eid, "实现无 @RequestBody（或路由未定位）"))
            continue
        comps, where = resolve_dto(root, ctrl[0], ctrl[1], dtos)
        if comps is None:
            undecided.append((eid, f"DTO 未静态判定（{where}）"))
            continue
        for fld in sorted(sch[model].get("required", ())):
            anns = comps.get(fld, set())
            ok_ann = bool(anns & {"@" + x for x in REQUIRED_ANN})
            tier, where = guards(fld, ctrl[0])
            tier = "注解" if ok_ann else tier
            ddl_cols = ddl.get(fld, {})
            ddl_narrow = sorted(t for t in ddl_cols
                                if any(tok and tok in t for tok in model.split("-")))
            rows.append((eid, model, fld, tier, sorted(anns), where,
                         sorted(ddl_cols), ddl_narrow))
            if tier not in EVIDENCE_TIERS:
                no_force.append((eid, fld, sorted(ddl_cols), ddl_narrow, tier))
    out.append("--- A3 schema.required 字段的运行时强制（DTO 必填注解 / 服务层 null 守卫）---")
    chk("A3 每个 schema.required 字段都能找到实现侧强制证据（注解 / 守卫 / 别名守卫）", not no_force,
        f"无强制证据 {len(no_force)} 个：{[n[:3] for n in no_force]}")
    tiers = {}
    for r in rows:
        tiers[r[3]] = tiers.get(r[3], 0) + 1
    info(f"      · 分级：{tiers}；未能比对端点 {len(undecided)} 个（{undecided}）")
    for r in rows:
        if r[3] not in ("注解",):
            info(f"        - {r[0]} {r[2]}：{r[3]}（注解 {r[4]}，命中 {r[5]}，DDL 同名列 {r[6]}，"
                 f"模型名窄化后 {r[7]}）")
    info("")
    out.append("--- A3b 分级发现：schema.required 但**实现侧零校验**（省略该字段 → 库约束/空值，不是 400）---")
    info(f"      · 共 {len(no_force)} 条：")
    for eid, fld, cols, narrow, tier in no_force:
        info(f"        - {eid} {fld}（判据分级：{tier}）：DDL 同名列 {cols or '（无同名列，列名不同形）'}"
             f"；模型名窄化后 {narrow or '（无）'}")
    info("")
    out.append("--- A9 信息项：schema.required 字段的 DDL NOT NULL 兜底（列名同名映射）---")
    nn = [(r[0], r[2], r[7]) for r in rows if r[7]]
    info(f"      · 同名 NOT NULL 列命中 {len(nn)} 个：{nn[:10]}")
    info("")

    # A4 反向
    drift4 = []
    for eid, e in sorted(eps.items()):
        model = e.get("request_model")
        if not model or model not in sch:
            continue
        key = norm_key(e.get("method"), e.get("path"))
        ctrl = routes.get(key)
        if not ctrl:
            continue
        comps, _ = resolve_dto(root, ctrl[0], ctrl[1], dtos)
        if not comps:
            continue
        for fld, anns in comps.items():
            if not (anns & {"@" + x for x in REQUIRED_ANN}):
                continue
            if fld not in sch[model].get("props", set()):
                drift4.append((eid, f"{model}: 实现 {sorted(anns)} 声明必填 {fld}，schema 无该属性"))
            elif fld not in sch[model].get("required", set()):
                drift4.append((eid, f"{model}: 实现声明必填 {fld}，schema.required 未声明"))
    out.append("--- A4 实现必填注解 ⊆ schema.required（反向漂移：契约漏声明必填）---")
    chk("A4 实现声明必填的字段都在 schema.required 里", not drift4, f"不一致 {len(drift4)} 条")
    for eid, d in drift4[:12]:
        info(f"      · {eid}: {d}")
    info("")

    # A5 信息项
    notnull_opt = [f"{n}.{f}" for n, v in sorted(sch.items())
                   for f in sorted(v.get("props", set()) - v.get("required", set()) - v.get("nullable", set()))]
    out.append("--- A5 信息项：「非必填但不可空」字段（显式传 null 与 schema 冲突）---")
    info(f"      · 共 {len(notnull_opt)} 个：{notnull_opt}")
    info("      · 运行时不做 schema 校验（A0h）→ 只影响把 schema 当客户端契约的一方；与 §0「缺字段一律 null 或省略」并存 → 契约完备性项")
    info("")

    # A6 信息项/待拍板
    unmarked = []
    for eid, v in sorted(md.items()):
        m = eps.get(eid, {}).get("request_model")
        if not m or m not in sch or v["mode"] != "完整":
            continue
        f = sorted((v["req"] & sch[m].get("props", set())) - sch[m].get("required", set()))
        if f:
            unmarked.append((eid, m, f))
    out.append("--- A6 信息项/待拍板：md 未标 ? 而 schema 非 required（§0 未定义必填性标注规则）---")
    info(f"      · 端点 {len(unmarked)} 个、字段 {sum(len(u[2]) for u in unmarked)} 个")
    for eid, m, f in unmarked:
        info(f"        - {eid}（{m}）{len(f)} 个：{f[:6]}{' …' if len(f) > 6 else ''}")
    info("")

    # A7 信息项
    coal = sum(len(re.findall(r"coalesce\s*\(", t, re.I)) for t in main_txt.values())
    coal_files = [fn for fn, t in main_txt.items() if re.search(r"coalesce\s*\(", t, re.I)]
    out.append("--- A7 信息项：可选字段的「省略=保持」写路径（坑 21 的正面处置）---")
    info(f"      · 实现 coalesce(...) {coal} 处（{len(coal_files)} 个文件）")
    info("")

    # A8 信息项
    out.append("--- A8 信息项：测试背书计数 ---")
    info(f"      · 测试源「缺少/未提供/missing」字样 {tt['miss']} 处；显式 null 构造 {tt['null']} 处")

    out.append("")
    out.append("--- Z1 零写副作用自检 ---")
    after = fingerprint(read)
    changed = [k for k in snap if snap.get(k) != after.get(k)]
    chk("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed, f"被改写 {len(changed)} 个：{changed[:5]}")

    out.append("")
    out.append(f"== 断言：PASS {npass} / FAIL {nfail}（读文件 {len(read)} 个）==")
    print("\n".join(out))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
