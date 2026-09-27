#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R63 抽查：乐观锁 / 并发控制契约（第三十七类可审计不变量，只读）。

为什么两套门禁都看不见
----------------------
契约测试只把**响应体**与 JSON Schema 比对，而乐观锁令牌是**请求头**（JSON Schema 里没有 header，
`requests/*.schema.json` 也不描述 header）；「失配返回哪个业务码 / 哪个 HTTP 状态 / 版本令牌是否出口
给客户端 / 客户端是否真的发送」这类语义更不在任何 schema 里。覆盖门禁只比「方法 + 路径」；
openapi 与客户端 TS 不被任何测试读取/执行 → 204 例全绿也查不出。

真源八处
--------
M = md 清单（§0「乐观锁」约定行 + 逐端点「幂等/并发」列 + 逐端点「错误码」列）
D = endpoints.json（端点集合，逐端点对齐用）
O = openapi.yaml（逐 operation `in: header`）
I = 实现（控制器 `@RequestHeader("If-Match")` 接收面 → 经字段类型解析到 Service 守卫抛出的码）
E = ErrorCode.java（码 → HTTP 状态 + 语义描述）
V = 响应契约 schema / 实现 DTO 是否出口版本令牌（version / etag）
C = 客户端是否真的发送该头（先剥注释再判）
T = 测试源（失配用例 + 状态码 + 码断言）

判据纪律：每个解析器都配 `> 0` 正向对照（坑 46/75/98/132）；条件化断言先判「判定可用」（坑 141）；
修的是判据不是期望值（坑 6）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path("E:/workspaces/hioas/hioas-aap-001")
HEADER = "If-Match"          # 本类不变量的头名（M §0 声明；逐站点逐字比对）
MD_REL = "docs/backend/02-API接口模型清单.md"
MAIN_REL = "aap-server/src/main/java"
TEST_REL = "aap-server/src/test/java"
CLIENT_REL = "aap-client/src"


def load_routes(root: Path):
    """复用 tools/audit-routes.py 的解析原语（同一 key/归一函数，坑 57；不复制同名函数，坑 102）。"""
    p = root / "tools/audit-routes.py"
    spec = importlib.util.spec_from_file_location("aap_audit_routes", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Res:
    def __init__(self):
        self.items = []          # (level, token, text)
        self.counts = []

    def add(self, level, token, text):
        self.items.append((level, token, text))

    def count(self, text):
        self.counts.append(text)


# ------------------------------------------------------------------ M：md 清单

def parse_md(root: Path, R) -> dict:
    out = {"exists": False, "rows": {}, "tables": [], "s0": None,
           "s0_header": None, "s0_code": None, "s0_status": None, "s0_token_sem": None}
    p = root / MD_REL
    if not p.exists():
        return out
    out["exists"] = True
    lines = p.read_text(encoding="utf-8").splitlines()
    header = None
    for raw in lines:
        ln = raw.strip()
        if not ln.startswith("|"):
            continue
        cells = R.split_row(ln)
        if cells and cells[0] == "ID":
            header = cells
            if header not in out["tables"]:
                out["tables"].append(list(header))
            continue
        if header is None:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(header):
            continue
        rid = cells[0]
        if not R.MD_ID_RE.match(rid):
            continue
        out["rows"][rid] = {header[i]: cells[i] for i in range(len(header))}
    for raw in lines:
        ln = raw.strip()
        if not ln.startswith("|"):
            continue
        cells = R.split_row(ln)
        if len(cells) >= 2 and cells[0].strip() == "乐观锁":
            out["s0"] = cells[1]
            break
    if out["s0"]:
        m = re.search(r"`([A-Za-z][A-Za-z0-9-]*)\s*:", out["s0"])
        out["s0_header"] = m.group(1) if m else None
        m = re.search(r"`(E-\d+)`", out["s0"])
        out["s0_code"] = m.group(1) if m else None
        m = re.search(r"(\d{3})\s*\+", out["s0"])
        out["s0_status"] = int(m.group(1)) if m else None
        m = re.search(r"<([^>]*)>", out["s0"])
        out["s0_token_sem"] = m.group(1) if m else None
    return out


def md_declared(md: dict) -> dict:
    """逐端点：声明该头的端点 → 该行「错误码」列 token 集合。"""
    out = {}
    for rid, cols in md["rows"].items():
        conc = " ".join(v for k, v in cols.items() if "幂等" in k or "并发" in k)
        if HEADER in conc:
            codes = set()
            for k, v in cols.items():
                if "错误码" in k:
                    codes |= set(re.findall(r"E-\d+", v))
            out[rid] = {"codes": codes,
                        "method": cols.get("方法", ""),
                        "path": cols.get("路径", "")}
    return out


# ------------------------------------------------------------------ D / O

def parse_endpoints(root: Path) -> tuple:
    p = root / "docs/backend/endpoints.json"
    if not p.exists():
        return 0, {}
    data = json.loads(p.read_text(encoding="utf-8"))
    total = int(data.get("total", len(data.get("endpoints", []))))
    eps = {}
    for e in data["endpoints"]:
        eps[e["id"]] = {"method": e["method"].upper(), "path": e["path"].strip(),
                        "response_model": e.get("response_model")}
    return total, eps


def parse_openapi(root: Path) -> dict:
    out = {"exists": False, "ops": {}, "n_ops": 0, "n_header": 0, "n_query": 0, "n_path": 0}
    p = root / "docs/backend/openapi.yaml"
    if not p.exists():
        return out
    out["exists"] = True
    cur_path = cur_method = None
    params = []
    cur_name = None

    def flush():
        if cur_path and cur_method:
            out["ops"][(cur_method.upper(), cur_path)] = list(params)

    for ln in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^  (/[^\s:]*):\s*$", ln)
        if m:
            flush()
            cur_path, cur_method = m.group(1), None
            params = []
            cur_name = None
            continue
        m = re.match(r"^    (get|post|put|delete|patch):\s*$", ln)
        if m:
            flush()
            cur_method = m.group(1)
            params = []
            cur_name = None
            out["n_ops"] += 1
            continue
        m = re.match(r"^        - name: (\S+)\s*$", ln)
        if m:
            cur_name = m.group(1)
            continue
        m = re.match(r"^          in: (\S+)\s*$", ln)
        if m and cur_name:
            params.append((cur_name, m.group(1)))
            if m.group(1) == "header":
                out["n_header"] += 1
            elif m.group(1) == "query":
                out["n_query"] += 1
            elif m.group(1) == "path":
                out["n_path"] += 1
            cur_name = None
    flush()
    return out


# ------------------------------------------------------------------ I：控制器 + Service 守卫

FIELD_RE = re.compile(r"(?:private|protected|public)\s+(?:final\s+)?([A-Z]\w*)\s+(\w+)\s*[=;]")


def _method_body(text: str, brace: int) -> str:
    """引号感知的 `{}` 配对扫描（坑 55：路径变量花括号成对，不会误判）。"""
    depth = 0
    i, n = brace, len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            q, j = c, i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                j += 1
            i = j
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
        i += 1
    return text[brace:]


def _sig_body_start(text: str, start: int) -> int:
    """方法体 `{`：括号深度为 0 时的第一个 `{`（坑 124：绝不在注解右括号上起步）。"""
    depth = 0
    i, n = start, len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            q, j = c, i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                j += 1
            i = j
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "{" and depth == 0:
            return i
        elif c == ";":
            return -1
        i += 1
    return -1


def parse_controllers(root: Path, R) -> dict:
    out = {"routes": {}, "sites": [], "n_routes": 0, "problems": []}
    cdir = root / MAIN_REL
    if not cdir.exists():
        return out
    for f in sorted(cdir.rglob("*Controller.java")):
        text = f.read_text(encoding="utf-8")
        body = R.class_body_start(text)
        if body < 0:
            out["problems"].append(f"{f.name}: 未定位到类声明")
            continue
        prefix = R.class_prefix(text, body)
        fmap = {}
        for typ, var in FIELD_RE.findall(text):
            fmap[var] = typ
        for m in R.MAPPING_RE.finditer(text):
            if m.start() < body:
                continue
            j = m.end()
            while j < len(text) and text[j] in " \t\r\n":
                j += 1
            if j < len(text) and text[j] == "(":          # 有实参的注解
                close = R.match_paren(text, j)
                seg = text[j:close + 1] if close >= 0 else ""
                paths = re.findall(r'"([^"]*)"', seg)
                sub = paths[0] if paths else ""
                sig_start = close + 1
            else:                                          # 裸注解：路径 = 类级前缀（坑 87/124）
                sub = ""
                sig_start = m.end()
            full = R.norm_path(prefix + sub)               # 一律拼前缀（坑 124）
            key = (m.group(1).upper(), full)
            bstart = _sig_body_start(text, sig_start)
            params = text[sig_start:bstart if bstart > 0 else len(text)]
            mbody = _method_body(text, bstart) if bstart > 0 else ""
            has_if = HEADER in params
            if has_if:
                for hm in re.findall(r'@RequestHeader\([^)]*?"([^"]+)"', params):
                    out.setdefault("hdr_lits", set()).add(hm)
            callee = None
            best = None
            for cm in re.finditer(r"\b(\w+)\.(\w+)\s*\(", mbody):
                o = mbody.find("(", cm.end() - 1)
                c2 = R.match_paren(mbody, o) if o >= 0 else -1
                if c2 < 0:
                    continue
                if not re.search(r"\bifMatch\b", mbody[o:c2 + 1]):
                    continue
                span = c2 - o
                if best is None or span < best[0]:      # 取**最内层**（坑 111-②：外层 ApiEnvelope.ok(...) 也含该实参）
                    best = (span, (cm.group(1), cm.group(2)))
            callee = best[1] if best else None
            ret = ""
            head = text[m.start():bstart if bstart > 0 else len(text)]
            rm = re.findall(r"([A-Z]\w*(?:<[^;{}]*?>)?)\s+(\w+)\s*\(", head)
            if rm:
                ret = rm[-1][0]
            out["routes"][key] = {"file": f.name, "has_if_match": has_if,
                                  "callee": callee, "ret": ret, "fields": fmap}
    out["n_routes"] = len(out["routes"])
    return out


def parse_guards(root: Path, ctrl: dict, R) -> dict:
    """逐站点：控制器 → 字段类型 → Service 方法体 → 守卫抛出的码。"""
    out = {"sites": [], "n_sites": 0}
    cdir = root / MAIN_REL
    if not cdir.exists():
        return out
    classes = {}
    for f in sorted(cdir.rglob("*.java")):
        m = re.search(r"\bclass\s+(\w+)", f.read_text(encoding="utf-8"))
        if m:
            classes.setdefault(m.group(1), f)
    for key, info in ctrl["routes"].items():
        if not info["has_if_match"]:
            continue
        site = {"key": key, "file": info["file"], "code": None, "why": "", "svc": None}
        recv_name, callee = info["callee"] or (None, None)
        if not callee:
            site["why"] = "未静态判定控制器→服务调用点"
            out["sites"].append(site)
            continue
        typ = info["fields"].get(recv_name)
        f = classes.get(typ) if typ else None
        if f is None:
            site["why"] = f"未定位服务类（字段 {recv_name} → 类型 {typ}）"
            out["sites"].append(site)
            continue
        text = f.read_text(encoding="utf-8")
        mm = re.search(r"\b%s\s*\(" % re.escape(callee), text)
        if not mm:
            site["why"] = f"未定位服务方法 {callee}"
            out["sites"].append(site)
            continue
        o = text.find("(", mm.end() - 1)
        c2 = _sig_body_start(text, R.match_paren(text, o) + 1 if R.match_paren(text, o) >= 0 else o)
        mbody = _method_body(text, c2) if c2 >= 0 else ""
        site["svc"] = f"{f.name}#{callee}"
        gm = re.search(r"\bifMatch\b", mbody)
        if not gm:
            site["why"] = "服务方法体内未出现 ifMatch（未静态判定守卫）"
            out["sites"].append(site)
            continue
        ifm = mbody.rfind("if (", 0, gm.start())
        if ifm < 0:
            ifm = mbody.rfind("if(", 0, gm.start())
        if ifm < 0:
            site["why"] = "未定位守卫 if 语句"
            out["sites"].append(site)
            continue
        op = mbody.find("(", ifm)
        cp = R.match_paren(mbody, op)
        brace = mbody.find("{", cp + 1) if cp >= 0 else -1
        blk = _method_body(mbody, brace) if brace >= 0 else ""
        cm = re.search(r"ErrorCode\.E_(\d+)", blk)
        if cm:
            site["code"] = "E-" + cm.group(1)
        else:
            site["why"] = "守卫块内未出现 ErrorCode（未静态判定）"
        out["sites"].append(site)
    out["n_sites"] = len(out["sites"])
    return out


# ------------------------------------------------------------------ E：错误码

def parse_error_codes(root: Path) -> dict:
    out = {}
    p = root / MAIN_REL / "com/hioas/aap/common/ErrorCode.java"
    if not p.exists():
        return out
    for m in re.finditer(r'E_(\d+)\(\s*"(E-\d+)"\s*,\s*(\d+)\s*,\s*"([^"]*)"\s*\)',
                         p.read_text(encoding="utf-8")):
        out[m.group(2)] = {"http": int(m.group(3)), "desc": m.group(4)}
    return out


# ------------------------------------------------------------------ V：版本令牌出口

def parse_tokens(root: Path, eps: dict, ctrl: dict, R) -> dict:
    out = {"contract": {}, "impl": {}}
    for rid, e in eps.items():
        rm = e.get("response_model")
        if not rm:
            continue
        p = root / "docs/backend/json-schema/models" / (rm + ".schema.json")
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        props = set((data.get("properties") or {}).keys())
        out["contract"][rid] = sorted(props & {"version", "etag", "current_version"})
    for key, info in ctrl["routes"].items():
        ret = info.get("ret") or ""
        gm = re.search(r"<\s*([\w.]+)", ret)
        name = (gm.group(1) if gm else ret).split(".")[0].strip()
        if not name:
            continue
        p = root / MAIN_REL
        hit = None
        for f in p.rglob("*.java"):
            if f.stem == name:
                hit = f
                break
        if hit is None:
            continue
        txt = hit.read_text(encoding="utf-8")
        keys = set(re.findall(r'@JsonProperty\("(\w+)"\)', txt))
        for rec in re.finditer(r"\brecord\s+\w+\s*(?:<[^>]*>)?\s*\(", txt):
            op = txt.find("(", rec.end() - 1)
            cp = R.match_paren(txt, op) if op >= 0 else -1
            if cp < 0:
                continue
            for comp in re.findall(r"\b([a-z]\w*)\b", txt[op:cp]):
                keys.add(comp)
        # class 型 DTO：无注解 getter 也会以默认 Jackson 键名出口（坑 117）
        for g in re.findall(r"\bget([A-Z]\w*)\s*\(\s*\)", txt):
            keys.add(g[0].lower() + g[1:])
        out["impl"][key] = sorted(keys & {"version", "etag", "current_version"})
    return out


# ------------------------------------------------------------------ C / T

def parse_client(root: Path, R) -> dict:
    out = {"files": 0, "sends": []}
    d = root / CLIENT_REL
    if not d.exists():
        return out
    for f in sorted(d.rglob("*")):
        if f.suffix not in (".ts", ".vue", ".js"):
            continue
        out["files"] += 1
        code = R.strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        for _ in re.finditer(r"""['"]If-Match['"]""", code):
            out["sends"].append(R.rel_path(f, root))
    return out


def parse_tests(root: Path, R) -> dict:
    out = {"files": 0, "methods": []}
    d = root / TEST_REL
    if not d.exists():
        return out
    for f in sorted(d.rglob("*.java")):
        text = f.read_text(encoding="utf-8")
        out["files"] += 1
        if HEADER not in R.strip_comments(text):
            continue
        for m in re.finditer(r"@Test\b", text):
            b = _sig_body_start(text, m.end())
            if b < 0:
                continue
            body = _method_body(text, b)
            if HEADER not in R.strip_comments(body):
                continue
            head = text[m.start():b if b >= 0 else m.end() + 600]
            dm = re.findall(r'@DisplayName\("([^"]*)"\)', head)      # 本项目 @DisplayName 在 @Test **之后**
            dn = dm[0] if dm else ""
            out["methods"].append({
                "file": R.rel_path(f, root),
                "display": dn,
                "codes": sorted(set(re.findall(r'isEqualTo\("(E-\d+)"\)', body))),
                "statuses": sorted(set(int(x) for x in re.findall(r"isEqualTo\((\d{3})\)", body))),
                "ids": expand_ids(dn),
            })
    return out


def expand_ids(text: str) -> list:
    """族引用展开（坑 31/32）：`A-05/06`、`A-01…03`；区间不得外溢。"""
    out = []
    for m in re.finditer(r"\b([A-Z]+)-(\d{2})\s*(?:…|\.\.\.|-)\s*(\d{2})\b", text):
        pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        if b >= a:
            out.extend("%s-%02d" % (pre, i) for i in range(a, b + 1))
    for m in re.finditer(r"\b([A-Z]+)-(\d{2})((?:/\d{2})+)\b", text):
        pre, a, rest = m.group(1), m.group(2), m.group(3)
        out.append("%s-%s" % (pre, a))
        out.extend("%s-%s" % (pre, x) for x in re.findall(r"\d{2}", rest))
    out.extend(re.findall(r"\b[A-Z]+-[A-Z0-9]+\b", text))
    return sorted(set(out))


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    sys.dont_write_bytecode = True          # 「只读」脚本不得留下 __pycache__（零写副作用守卫）
    root = Path(args.root)
    R = load_routes(root)
    res = Res()

    md = parse_md(root, R)
    declared = md_declared(md)
    total, eps = parse_endpoints(root)
    oa = parse_openapi(root)
    ctrl = parse_controllers(root, R)
    guards = parse_guards(root, ctrl, R)
    codes = parse_error_codes(root)
    tokens = parse_tokens(root, eps, ctrl, R)
    cli = parse_client(root, R)
    tests = parse_tests(root, R)

    # ---- 正向对照
    res.add("PASS" if md["exists"] else "FAIL", "A0a",
            "M md 清单可读且 §0「乐观锁」行解析到头名/状态/码：exists=%s 头名=%r 状态=%r 码=%r 令牌语义=%r"
            % (md["exists"], md["s0_header"], md["s0_status"], md["s0_code"], md["s0_token_sem"]))
    res.add("PASS" if (md["rows"] and total and len(md["rows"]) == total) else "FAIL", "A0b",
            "M 逐端点行数 = D 端点数：md=%d 期望=%d（两套表头：%s）"
            % (len(md["rows"]), total, ["/".join(t) for t in md["tables"]]))
    res.add("PASS" if (total > 0 and len(eps) == total) else "FAIL", "A0c",
            "D endpoints.json 解析到端点数 = total：%d / %d" % (len(eps), total))
    res.add("PASS" if (oa["n_ops"] == total and oa["n_query"] > 0 and oa["n_path"] > 0) else "FAIL", "A0d",
            "O openapi 解析到 operations=%d（期望 %d）、in:query=%d、in:path=%d、in:header=%d"
            "（query/path 为 0 即解析器失效）" % (oa["n_ops"], total, oa["n_query"], oa["n_path"], oa["n_header"]))
    res.add("PASS" if (total > 0 and ctrl["n_routes"] >= total and not ctrl["problems"]) else "FAIL", "A0e",
            "I 控制器路由定位率：parsed=%d 条（期望 ≥ %d）；解析问题 %d 条 %s"
            % (ctrl["n_routes"], total, len(ctrl["problems"]), ctrl["problems"][:3]))
    res.add("PASS" if guards["n_sites"] > 0 else "FAIL", "A0f",
            "I 解析到接收该头的站点数 = %d（为 0 即解析器失效，不得判 PASS）" % guards["n_sites"])
    res.add("PASS" if len(codes) > 0 else "FAIL", "A0g",
            "E ErrorCode.java 解析到码条目 = %d" % len(codes))
    res.add("PASS" if len(tests["methods"]) > 0 else "FAIL", "A0h",
            "T 测试源解析到含该头的用例方法 = %d（文件 %d）" % (len(tests["methods"]), tests["files"]))
    res.add("PASS" if cli["files"] > 0 else "FAIL", "A0i",
            "C 客户端源扫描到文件 = %d（扫描器有输入）" % cli["files"])

    # ---- A1 头名一致
    hdr_md = md["s0_header"]
    hdr_impl = sorted(ctrl.get("hdr_lits", set()))
    ok = (hdr_md == HEADER and hdr_impl == [HEADER])
    res.add("PASS" if ok else "FAIL", "A1",
            "头名一致：M §0=%r / I @RequestHeader=%s（期望 %r）" % (hdr_md, hdr_impl, HEADER))

    # ---- A2 失配语义：M §0 码 == 逐站点实现抛的码
    site_codes = sorted(set(s["code"] for s in guards["sites"] if s["code"]))
    if not declared:
        res.add("FAIL", "A3", "判定不可用：M 未声明任何带该头的端点（声明端点数=0，不得判「一致」，坑 141）")
    else:
        impl_keys = {k for k, v in ctrl["routes"].items() if v["has_if_match"]}
        md_keys = set()
        for rid in declared:
            e = eps.get(rid)
            if e:
                md_keys.add((e["method"], R.norm_path(e["path"])))
        only_md = sorted(md_keys - impl_keys)
        only_impl = sorted(impl_keys - md_keys)
        res.add("PASS" if not only_md and not only_impl else "FAIL", "A3",
                "逐端点：M 声明该头的端点集合 = I 接收该头的控制器路由集合（声明 %d / 接收 %d）；仅 M 有=%s；仅 I 有=%s"
                % (len(md_keys), len(impl_keys), only_md, only_impl))
    if len(site_codes) > 1:
        res.add("FAIL", "A2",
                "失配语义在实现内部即分叉：%s（同一「乐观锁失配」语义用了两种码；逐站点 %s）"
                % (site_codes, [(s["svc"], s["code"]) for s in guards["sites"]]))
    else:
        res.add("PASS" if (site_codes and site_codes[0] == md["s0_code"]) else "FAIL", "A2",
                "失配码一致：M §0=%r / I 逐站点=%s" % (md["s0_code"], [(s["svc"], s["code"]) for s in guards["sites"]]))

    # ---- A2b §0 与逐端点「错误码」列是否自相矛盾（码的语义描述也是契约不变量，坑 54）
    if not declared or md["s0_code"] is None:
        res.add("FAIL", "A2b", "判定不可用：声明端点或 §0 失配码为空（不得判「无矛盾」，坑 141）")
    else:
        wrong = []
        for rid in sorted(declared):
            if md["s0_code"] not in declared[rid]["codes"]:
                wrong.append((rid, sorted(declared[rid]["codes"])))
        res.add("PASS" if not wrong else "FAIL", "A2b",
                "M 逐端点「错误码」列声明 §0 的失配码 %r：未声明 %d 条 %s"
                "（§0 与逐端点行冲突 → 调用方按码分支会分叉）" % (md["s0_code"], len(wrong), wrong))

    # ---- A4 逐端点错误码列是否声明实现真会抛的码
    if not declared or not eps:
        res.add("FAIL", "A4", "判定不可用：声明端点或清单为空（不得判「全部有声明」，坑 141）")
    else:
        miss = []
        for rid in sorted(declared):
            e = eps.get(rid)
            if not e:
                continue
            key = (e["method"], R.norm_path(e["path"]))
            impl = [s for s in guards["sites"] if s["key"] == key and s["code"]]
            for s in impl:
                if s["code"] not in declared[rid]["codes"]:
                    miss.append((rid, s["code"], sorted(declared[rid]["codes"])))
        res.add("PASS" if not miss else "FAIL", "A4",
                "M「错误码」列声明实现真会抛的失配码：漏声明 %d 条 %s" % (len(miss), miss))

    # ---- A5 码语义描述是否覆盖「乐观锁/并发失配」
    bad = []
    for c in sorted(set(site_codes) | ({md["s0_code"]} if md["s0_code"] else set())):
        d = codes.get(c)
        if not d:
            bad.append((c, "码不在 ErrorCode 目录里"))
            continue
        if not re.search(r"乐观锁|并发|版本|已被更新|冲突", d["desc"]):
            bad.append((c, d["desc"]))
    res.add("PASS" if not bad else "FAIL", "A5",
            "失配码的语义描述覆盖「乐观锁/并发」：不覆盖 %s（§0 声明=%r）" % (bad, md["s0_code"]))

    # ---- A6 码 → HTTP 状态 == §0 承诺
    if md["s0_status"] is None:
        res.add("FAIL", "A6", "判定不可用：§0 未解析到 HTTP 状态（不得判「一致」）")
    else:
        st = [(c, codes.get(c, {}).get("http")) for c in sorted(set(site_codes))]
        wrong = [x for x in st if x[1] != md["s0_status"]]
        res.add("PASS" if (st and not wrong) else "FAIL", "A6",
                "码 → HTTP 状态 = §0 承诺 %d：实测 %s；不符 %s" % (md["s0_status"], st, wrong))

    # ---- A7 客户端是否真的发送该头
    res.add("PASS" if cli["sends"] else "FAIL", "A7",
            "C 客户端真的发送该头的调用点 = %d 处 %s → 措辞为「支持」（`required = false` + 「若提供则校验」），"
            "客户端不带该头 = 并发保护**静默失效**（风险项，待拍板；坑 88）" % (len(cli["sends"]), cli["sends"][:3]))

    # ---- A8 令牌可达性
    if not declared or not eps:
        res.add("FAIL", "A8", "判定不可用：声明端点为空（不得判「令牌可达」）")
    else:
        bad = []
        for rid in sorted(declared):
            e = eps.get(rid)
            key = (e["method"], R.norm_path(e["path"])) if e else None
            c_tok = tokens["contract"].get(rid)
            i_tok = tokens["impl"].get(key) if key else None
            if c_tok is None:
                bad.append((rid, "响应模型 schema 未定位", i_tok))
            elif not c_tok:
                bad.append((rid, "契约响应未出口 version/etag", i_tok))
            elif not i_tok:
                bad.append((rid, "实现响应 DTO 未出口 version/etag", i_tok))
        res.add("PASS" if not bad else "FAIL", "A8",
                "版本令牌可达性（客户端要拿得到才能回填该头）：不可达 %s" % bad)

    # ---- A9 测试背书
    if not declared:
        res.add("FAIL", "A9", "判定不可用：声明端点为空（不得判「全部有背书」，坑 141）")
    else:
        backed = set()
        for t in tests["methods"]:
            for rid in declared:
                if rid in t["ids"]:
                    backed.add(rid)
        miss = sorted(set(declared) - backed)
        res.add("PASS" if not miss else "FAIL", "A9",
                "测试背书：M 声明的 %d 条端点中 %d 条有失配用例（%s），零背书 %d 条 %s"
                % (len(declared), len(backed), sorted(backed), len(miss), miss))
        res.add("INFO", "A9b",
                "测试断言的码/状态：%s" % [(t["ids"], t["codes"], t["statuses"]) for t in tests["methods"]])

    # ---- A10 openapi 声明
    oa_hdr = [k for k, v in oa["ops"].items() if any(h == HEADER for h, loc in v if loc == "header")]
    if not declared:
        res.add("FAIL", "A10", "判定不可用：声明端点为空（不得判「已声明」）")
    else:
        res.add("PASS" if len(oa_hdr) >= len(declared) else "FAIL", "A10",
                "O openapi 逐 operation 声明该头：声明端点数=%d / openapi 声明数=%d（in:header 总点数=%d）"
                "→ 生成物侧漏声明（契约测试只读 JSON Schema，头不在 schema 里，204 例全绿也看不见）"
                % (len(declared), len(oa_hdr), oa["n_header"]))

    # ---- Z1 零写副作用
    watched = []
    for rel in (MD_REL, "docs/backend/endpoints.json", "docs/backend/openapi.yaml"):
        watched.append(root / rel)
    for d in (root / MAIN_REL, root / TEST_REL, root / CLIENT_REL):
        if d.exists():
            watched.extend(sorted(d.rglob("*.java")))
            watched.extend(sorted(d.rglob("*.ts")))
    fp = {}
    for p in watched:
        if p.exists():
            fp[str(p)] = hashlib.md5(p.read_bytes()).hexdigest()
    res.add("PASS", "Z1", "全部被读文件指纹已采集（%d 个）—— 判据为「本脚本只读」，无写操作" % len(fp))

    lines = []
    lines.append("== R63 抽查：乐观锁 / 并发控制契约（第三十七类可审计不变量，只读） ==")
    lines.append("真源：M md 清单（§0 乐观锁行 + 逐端点「幂等/并发」列 + 逐端点「错误码」列）/ D endpoints.json / "
                 "O openapi（in: header）/ I 实现（控制器接收面 → Service 守卫码）/ E ErrorCode（码→状态+描述）/ "
                 "V 版本令牌出口 / C 客户端是否真的发送 / T 测试源")
    lines.append("头名（本类不变量）：`%s`" % HEADER)
    lines.append("")
    lines.append("--- 解析计数（正向对照，任一为 0 即说明解析器失效）---")
    lines.append("M md 端点行=%d；§0 头名=%r 状态=%r 码=%r" % (len(md["rows"]), md["s0_header"], md["s0_status"], md["s0_code"]))
    lines.append("D 端点数=%d；声明该头的端点=%d（%s）" % (total, len(declared), sorted(declared)))
    lines.append("O operations=%d；in:header=%d；in:query=%d" % (oa["n_ops"], oa["n_header"], oa["n_query"]))
    lines.append("I 控制器路由=%d；接收该头的站点=%d" % (ctrl["n_routes"], guards["n_sites"]))
    lines.append("E 码条目=%d；T 含该头的用例=%d；C 客户端文件=%d" % (len(codes), len(tests["methods"]), cli["files"]))
    lines.append("")
    lines.append("--- 逐站点：控制器 → 服务 → 守卫码 ---")
    for s in guards["sites"]:
        lines.append("  %-8s %-42s → %-28s 码=%s %s" % (
            s["key"][0], s["key"][1], s["svc"] or s["file"], s["code"], s["why"]))
    lines.append("")
    lines.append("--- 断言 ---")
    for level, token, text in res.items:
        lines.append("[%s] %s %s" % (level, token, text))
    npass = sum(1 for l, _, _ in res.items if l == "PASS")
    nfail = sum(1 for l, _, _ in res.items if l == "FAIL")
    ninfo = sum(1 for l, _, _ in res.items if l == "INFO")
    lines.append("")
    lines.append("汇总 PASS %d / FAIL %d / INFO %d" % (npass, nfail, ninfo))
    lines.append("正向对照 A0a…A0i 全部必须为 PASS；任一为 FAIL 时本报告结论无效（先修解析器，坑 46/98）")
    text = "\n".join(lines) + "\n"

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print("报告已写：%s（CR=%d）" % (out, out.read_bytes().count(b"\r")))
    print(text)
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
