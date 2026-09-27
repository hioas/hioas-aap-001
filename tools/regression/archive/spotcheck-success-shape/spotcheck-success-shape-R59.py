#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R59 抽查：成功响应的「HTTP 状态码 + 内容类型 / 包络形状」跨源一致性
（第三十三类可审计不变量）—— 只读，不写仓库任何文件。

为什么两套门禁都看不见：
  ① 契约测试把**响应体**与 JSON Schema 比对（`assertModel`），RPT-03 的用例只断言
     status / content-type / body 文本，**从不做 schema 校验** → 非包络成功响应全绿；
  ② 覆盖门禁只比「方法 + 路径」注册表；
  ③ openapi 与客户端 TS 不被任何测试读取 / 执行。
  ⇒ openapi 把 text/html 端点声明成 application/json 包络，204 例全绿也查不出。

真源六处：
  M1 = md §4 码表「`0` | 200 | 成功」行（业务码 0 恒映射 HTTP 200）
  M2 = md §0「响应包体」行（所有接口统一包络 {"code","message","data","traceId"}）
  M3 = md 逐端点「响应」列（声明非 JSON 内容类型，如 `text/html`）
  O  = openapi 逐 operation：成功状态码集合 + 每个状态下的 media type
  I  = 实现：控制器路由的成功返回类型 / `produces` / 是否有非 200 成功包装
  C  = 客户端 http.ts 成功路径判定（`status >= 400` / `typeof body.code !== 'string'` / `code !== '0'`）
       + 客户端对「非包络端点」的调用点
  T  = 测试对成功状态码的断言（双形态，坑 86）

判据纪律：每个源配 > 0 正向对照；注入缺陷必须真的改到源码；空夹具必须转红。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("E:/workspaces/hioas/hioas-aap-001")
MD = ROOT / "docs/backend/02-API接口模型清单.md"
EP = ROOT / "docs/backend/endpoints.json"
OAPI = ROOT / "docs/backend/openapi.yaml"
GEN = ROOT / "tools/gen-backend-models.py"
MAIN = ROOT / "aap-server/src/main/java"
TEST = ROOT / "aap-server/src/test/java"
CLIENT = ROOT / "aap-client/src"

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


def java_files(base):
    return sorted([p for p in base.rglob("*.java") if p.is_file()])


def key_of(method, path):
    """跨源归一：剥 /api/v1 前缀、路径变量折叠为 {}、方法小写。"""
    p = re.sub(r"^/api/v1", "", path or "")
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return (method or "").lower(), p


# --------------------------------------------------------------- M：md 清单
def strip_cell(c):
    c = c.replace("\\|", "|").strip()
    if c.startswith("`") and c.endswith("`") and len(c) > 1:
        c = c[1:-1]
    return c.strip()


def split_row(line):
    return [strip_cell(c) for c in re.split(r"(?<!\\)\|", line)]


def parse_md(text):
    """返回 {id: {method, path, response_cell, ncols}}（兼容 10 列 / 7 列两套表头，坑 48/89）。"""
    rows, header = {}, None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header = None
            continue
        cells = split_row(s)
        # split 后首尾为空串（行首行尾的竖线）
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if cells and cells[0] == "ID":
            header = cells
            continue
        if header is None or len(cells) != len(header):
            continue
        if not re.match(r"^[A-Z]{2,}-[A-Z0-9]+$", cells[0]):
            continue
        # 坑 89：同一文件两套表头（10 列含「响应」/ 7 列含「请求/响应」）→ 先判 7 列，否则 resp_idx 落到错误码列
        if "请求/响应" in header:
            resp_idx = 4
        elif "响应" in header:
            resp_idx = 5
        else:
            resp_idx = None
        rows[cells[0]] = {
            "method": cells[1].strip().upper(),
            "path": cells[2].strip(),
            "response_cell": cells[resp_idx] if resp_idx is not None and resp_idx < len(cells) else "",
            "ncols": len(cells),
        }
    return rows


def md_status_contract(text):
    m = re.search(r"\|\s*`0`\s*\|\s*(\d{3})\s*\|\s*成功\s*\|", text)
    return m.group(1) if m else None


def md_envelope_line(text):
    m = re.search(r"\|\s*响应包体\s*\|(.*?)\|", text)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------- O：openapi
def parse_openapi(path):
    """返回 {(method, path): {'statuses': [...], 'media': {status: [mt]}, 'envelope': {status: bool}}}"""
    try:
        import yaml
    except ImportError:
        return None, "本机无 PyYAML —— 解析器缺失（显式失败，不得判绿）"
    txt = read(path)
    if not txt.strip():
        return {}, ""
    doc = yaml.safe_load(txt) or {}
    out = {}
    for p, item in (doc.get("paths") or {}).items():
        for m, op in (item or {}).items():
            if m not in ("get", "post", "put", "delete", "patch"):
                continue
            responses = (op or {}).get("responses") or {}
            statuses, media, env = [], {}, {}
            for st, r in responses.items():
                sts = str(st)
                if not re.match(r"^2\d\d$", sts):
                    continue
                statuses.append(sts)
                cts = list(((r or {}).get("content") or {}).keys())
                media[sts] = cts
                blob = json.dumps((r or {}).get("content") or {}, ensure_ascii=False)
                env[sts] = ("Envelope" in blob)
            out[key_of(m, p)] = {"statuses": statuses, "media": media, "envelope": env, "raw_path": p}
    return out, ""


# --------------------------------------------------------------- I：控制器
MAPPING = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")
MODIFIERS = {"public", "private", "protected", "static", "final", "abstract", "synchronized", "default"}


def parse_controller(text):
    """返回 [(http_method, full_path, return_type, produces, line_no)]（坑 55/63/87/124）。"""
    cls = re.search(r"\b(?:public\s+)?(?:final\s+)?class\s+\w+", text)
    prefix = ""
    for m in re.finditer(r"@RequestMapping\s*\(", text):
        if cls and m.start() > cls.start():
            break
        close = match_paren(text, m.end() - 1)
        if close < 0:
            continue
        arg = text[m.end():close]
        s = re.search(r"\"([^\"]*)\"", arg)
        if s:
            prefix = s.group(1)
    out = []
    for m in MAPPING.finditer(text):
        http = m.group(1).upper()
        i = m.end()
        j = i
        while j < len(text) and text[j] in " \t\r\n":
            j += 1
        produces = ""
        if j < len(text) and text[j] == "(":
            close = match_paren(text, j)
            if close < 0:
                continue
            arg = text[j + 1:close]
            sig_start = close + 1          # 坑 124：不能从注解的右括号起扫
            s = re.search(r"\"([^\"]*)\"", arg)
            seg = arg
            if s:
                if "value" in arg[:s.start()] or "path" in arg[:s.start()]:
                    seg = arg[s.start():]
                p = s.group(1)
            else:
                p = ""
            pm = re.search(r"produces\s*=\s*([^,)]+)", arg)
            if pm:
                produces = pm.group(1).strip()
        else:
            p = ""
            sig_start = m.end()            # 裸注解：路径回落类级前缀
        tail = text[sig_start:sig_start + 600]
        mm = re.match(r"\s*(?:@\w+(?:\([^)]*\))?\s*)*((?:[\w.<>\[\],?]+\s+)+?)(\w+)\s*\(", tail)
        rtype = " ".join(mm.group(1).split()) if mm else ""
        toks = [t for t in rtype.replace("<", " <").split() if t not in MODIFIERS]
        rtype = " ".join(toks).replace(" <", "<")
        full = prefix + p if p else prefix
        out.append((http, full, rtype, produces, text[:m.start()].count("\n") + 1))
    return out


def all_routes():
    routes = []
    for p in java_files(MAIN):
        t = read(p)
        if not t or "@" not in t:
            continue
        if not MAPPING.search(t):
            continue
        for http, path, rtype, produces, ln in parse_controller(t):
            routes.append({"file": p, "http": http, "path": path, "returns": rtype,
                           "produces": produces, "line": ln})
    return routes


def produces_type(raw):
    if not raw:
        return "application/json"
    if "TEXT_HTML" in raw:
        return "text/html"
    if "APPLICATION_JSON" in raw or "JSON" in raw:
        return "application/json"
    s = re.search(r"\"([^\"]+)\"", raw)
    return s.group(1) if s else raw


def non_200_success(routes):
    """成功路径里的非 200 包装（排除 GlobalExceptionHandler 错误路径）。"""
    hits = []
    for p in java_files(MAIN):
        t = read(p)
        if not t:
            continue
        name = p.name
        if name == "GlobalExceptionHandler.java":
            continue
        for m in re.finditer(r"@ResponseStatus\s*\(\s*(?:value\s*=\s*)?HttpStatus\.(\w+)", t):
            if m.group(1) not in ("OK",):
                hits.append("%s: 注解 @ResponseStatus(HttpStatus.%s)" % (name, m.group(1)))
        for m in re.finditer(r"ResponseEntity\.status\s*\(\s*(?:HttpStatus\.(\w+)|(\d{3}))", t):
            code = m.group(1) or m.group(2)
            if code not in ("OK", "200"):
                hits.append("%s: ResponseEntity.status(%s)" % (name, code))
    return hits


# --------------------------------------------------------------- C：客户端
def strip_comments(ts):
    """剥注释（保留字符串/模板字面量，坑 58）。"""
    out, i, n = [], 0, len(ts)
    while i < n:
        c = ts[i]
        if c in "\"'`":
            q = c
            out.append(c)
            i += 1
            while i < n:
                if ts[i] == "\\":
                    out.append(ts[i:i + 2])
                    i += 2
                    continue
                out.append(ts[i])
                if ts[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if ts.startswith("//", i):
            j = ts.find("\n", i)
            i = n if j < 0 else j
            continue
        if ts.startswith("/*", i):
            j = ts.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def client_http():
    p = CLIENT / "api/http.ts"
    t = read(p)
    return {
        "has_401": "status === 401" in t,
        "has_4xx": bool(re.search(r"status\s*>=\s*400", t)),
        "requires_envelope": bool(re.search(r"typeof\s+body\.code\s*!==\s*'string'|typeof\s+body\.code\s*!==\s*\"string\"", t)),
        "code_ok": bool(re.search(r"body\.code\s*!==\s*'0'|body\.code\s*!==\s*\"0\"", t)),
        "text": t,
    }


def client_call_sites():
    """返回 [(file, raw_arg, normalized_path)]；解析 http<T>(arg, ...) 调用点 + 文件内路径助手。"""
    sites = []
    for p in sorted(CLIENT.rglob("*")):
        if p.suffix not in (".ts", ".vue") or not p.is_file():
            continue
        raw = read(p)
        if not raw or "http" not in raw:
            continue
        t = strip_comments(raw)
        helpers = {}
        for m in re.finditer(r"const\s+(\w+)\s*=\s*(?:\([^)]*\)|\w+)\s*=>\s*`([^`]*)`", t):
            helpers[m.group(1)] = m.group(2)
        for m in re.finditer(r"(?<![\w.])http\s*(?:<[^>(]*>)?\s*\(", t):
            pre = t[max(0, m.start() - 40):m.start()]
            if re.search(r"function\s*$", pre):
                continue                      # 坑 58-①：声明与调用同形
            i = t.find("(", m.start())
            close = match_paren(t, i)
            if close < 0:
                continue
            arg = t[i + 1:close].split(",")[0].strip()
            lit = None
            s = re.match(r"`([^`]*)`", arg) or re.match(r"'([^']*)'", arg) or re.match(r"\"([^\"]*)\"", arg)
            if s:
                lit = s.group(1)
            else:
                hm = re.match(r"\$\{(\w+)\(", arg)
                if hm and hm.group(1) in helpers:
                    lit = helpers[hm.group(1)] + arg[arg.index("}") + 1:]
            if lit is None:
                sites.append((p.name, arg, None))
                continue
            norm = re.sub(r"\$\{[^}]*\}", "{}", lit)
            norm = re.sub(r"^/api/v1", "", norm)
            sites.append((p.name, arg, norm))
    return sites


def norm_client_path(p):
    if p is None:
        return None
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p


# --------------------------------------------------------------- T：测试
def test_status_asserts():
    """双形态 × 双接收者（坑 86：状态值在 isEqualTo 实参里，不在 statusCode() 实参里）。"""
    ta_code = tb_code = ta_st = tb_st = 0
    values = []
    for p in java_files(TEST):
        t = read(p)
        for m in re.finditer(r"\.statusCode\(\)\s*\)\s*\.isEqualTo\(\s*(\d{3})\s*\)", t):
            ta_code += 1
            values.append(int(m.group(1)))
        for m in re.finditer(r"\.statusCode\(\s*\)\s*,\s*(\d{3})\s*\)", t):
            tb_code += 1
            values.append(int(m.group(1)))
        for m in re.finditer(r"\.status\(\)\s*\)\s*\.isEqualTo\(\s*(\d{3})\s*\)", t):
            ta_st += 1
            values.append(int(m.group(1)))
        for m in re.finditer(r"\.status\(\)\s*,\s*(\d{3})\s*\)", t):
            tb_st += 1
            values.append(int(m.group(1)))
    return ta_code, tb_code, ta_st, tb_st, values


# --------------------------------------------------------------- 主流程
def main():
    md_txt = read(MD)
    md_rows = parse_md(md_txt)
    md_status = md_status_contract(md_txt)
    md_env = md_envelope_line(md_txt)
    oapi, oerr = parse_openapi(OAPI)
    routes = all_routes()
    c = client_http()
    sites = client_call_sites()
    ta_code, tb_code, ta_st, tb_st, tvals = test_status_asserts()
    ta = ta_code + ta_st
    tb = tb_code + tb_st

    print("== R59 抽查：成功响应「HTTP 状态码 + 内容类型/包络形状」跨源一致性（第三十三类可审计不变量）==")
    print("真源：M=md（§4 码表/§0 响应包体/逐端点响应列）/ O=openapi / I=实现控制器 / C=客户端 http.ts+调用点 / T=测试断言")
    print()

    print("== 正向对照 ==")
    if md_rows:
        ok("A0a", "md 逐端点表解析到 %d 条（10 列表头行 + 7 列表头行合计）" % len(md_rows))
    else:
        fail("A0a", "md 未解析到任何端点行 —— 解析器失效（先怀疑解析器，坑 46/89）")
    if oapi is None:
        fail("A0b", "openapi 解析失败：%s" % oerr)
    elif oapi:
        with200 = [k for k, v in oapi.items() if v["statuses"]]
        ok("A0b", "openapi 解析到 %d 个 operation，其中声明了 2xx 成功响应的 %d 个" % (len(oapi), len(with200)))
    else:
        fail("A0b", "openapi 未解析到任何 operation —— 解析器失效")
    ctrl = [r for r in routes if r["file"].name.endswith("Controller.java")]
    md_keys_all = set(key_of(r["method"], r["path"]) for r in md_rows.values())
    ctrl_keys = set(key_of(r["http"], r["path"]) for r in ctrl)
    if ctrl:
        located = len(md_keys_all & ctrl_keys)
        ok("A0c", "控制器路由定位到清单端点 %d/%d（控制器路由总数 %d，Controller 文件 %d 个）"
           % (located, len(md_keys_all), len(ctrl), len({r["file"] for r in ctrl})))
    else:
        fail("A0c", "控制器路由定位 0 条 —— 解析器失效（坑 87/124）")
    extra = sorted(ctrl_keys - md_keys_all)
    if extra:
        info("A0c2", "控制器已注册但清单无声明的路由 %d 条（实现超出冻结契约，坑 61 已登记项）：%s"
             % (len(extra), "; ".join("%s %s" % (k[0].upper(), k[1]) for k in extra)))
    if ta + tb > 0:
        ok("A0d", "测试成功状态断言解析到 %d 处（`.statusCode()` 形态 %d 处 / `.status()` 形态 %d 处；"
                  "显式 `.isEqualTo(N)` 形态 %d 处 / 实参形态 %d 处，坑 86）"
           % (ta + tb, ta_code + tb_code, ta_st + tb_st, ta_code + ta_st, tb_code + tb_st))
    else:
        fail("A0d", "测试成功状态断言 0 处 —— 解析器失效（0 发现先怀疑解析器）")
    if c["code_ok"] and c["requires_envelope"] and c["has_4xx"]:
        ok("A0e", "客户端成功路径判定分支解析到（401 分支=%s / >=400 分支=%s / 包络形状校验=%s / 业务码判定=%s）"
           % (c["has_401"], c["has_4xx"], c["requires_envelope"], c["code_ok"]))
    else:
        fail("A0e", "客户端 http.ts 判定分支解析不全（401=%s / 4xx=%s / 包络=%s / code=%s）"
             % (c["has_401"], c["has_4xx"], c["requires_envelope"], c["code_ok"]))
    if sites:
        ok("A0f", "客户端调用点解析到 %d 处（其中可静态判定路径 %d 处）"
           % (len(sites), len([s for s in sites if s[2]])))
    else:
        fail("A0f", "客户端调用点 0 处 —— 解析器失效（坑 58）")

    print()
    print("== A1 实现侧：成功路径是否恒 200（md §4「0 | %s | 成功」）==" % md_status)
    if md_status:
        ok("A1a", "md §4 码表成功行：业务码 `0` → HTTP %s" % md_status)
    else:
        fail("A1a", "md §4 未解析到「`0` | 200 | 成功」行 —— 解析器失效")
    if md_env:
        ok("A1b", "md §0「响应包体」行解析到：%s" % md_env[:80])
    else:
        fail("A1b", "md §0 未解析到「响应包体」行 —— 解析器失效")
    bad200 = non_200_success(routes)
    if bad200:
        fail("A1c", "成功路径出现非 200 返回 %d 处（与 md §4 的「0→200」冲突）：%s" % (len(bad200), "; ".join(bad200[:5])))
    else:
        ok("A1c", "成功路径非 200 返回 = 0 处（%d 条控制器路由全部走默认 200）" % len(ctrl))
    resp_ret = [r for r in ctrl if r["returns"].startswith("ResponseEntity")]
    info("A1d", "控制器成功返回类型：ApiEnvelope 包装 %d 条 / ResponseEntity 包装 %d 条（%s）"
         % (len(ctrl) - len(resp_ret), len(resp_ret),
            "; ".join("%s %s → %s" % (r["http"], r["path"], r["returns"]) for r in resp_ret) or "-"))

    print()
    print("== A2 openapi 逐端点成功 media type ⇔ 实现 produces ==")
    impl_produces = {}
    for r in routes:
        impl_produces.setdefault(key_of(r["http"], r["path"]), produces_type(r["produces"]))
    drift, located = [], 0
    for k, v in (oapi or {}).items():
        if not v["statuses"]:
            continue
        if k not in impl_produces:
            continue
        located += 1
        impl_mt = impl_produces[k]
        declared = set()
        for st in v["statuses"]:
            declared |= set(v["media"].get(st) or [])
        if impl_mt not in declared:
            drift.append("%s %s：openapi 声明 %s，实现 produces=%s" %
                         (k[0].upper(), k[1], ",".join(sorted(declared)) or "(无)", impl_mt))
    if located:
        ok("A2a", "openapi 与实现逐端点定位到 %d 条（正向对照 > 0）" % located)
    else:
        fail("A2a", "openapi ⇔ 实现 逐端点定位 0 条 —— 两侧 key 归一失效（坑 57）")
    if drift:
        fail("A2b", "openapi 成功响应 media type 与实现不一致 %d 条（生成物侧漂移，两套门禁都看不见）：%s"
             % (len(drift), " | ".join(drift)))
    else:
        ok("A2b", "openapi 成功响应 media type 与实现逐端点一致（%d 条已定位全部通过）" % located)

    print()
    print("== A3 md 声明的非包络端点 ⇔ 实现 produces 非 JSON ==")
    md_nonjson = {}
    for eid, r in md_rows.items():
        cell = r["response_cell"]
        m = re.search(r"(text/html|text/plain|application/octet-stream|attachment)", cell)
        if m:
            md_nonjson[eid] = (m.group(1), r)
    impl_nonjson = {k: v for k, v in impl_produces.items() if v != "application/json"}
    md_keys = set()
    for eid, (mt, r) in md_nonjson.items():
        md_keys.add(key_of(r["method"], r["path"]))
    if md_nonjson or impl_nonjson:
        if md_keys == set(impl_nonjson):
            ok("A3a", "md 声明非包络端点 %d 条 ⇔ 实现 produces 非 JSON %d 条（双向一致：%s）"
               % (len(md_keys), len(impl_nonjson),
                  ", ".join("%s %s→%s" % (k[0].upper(), k[1], impl_nonjson[k]) for k in sorted(impl_nonjson)) or "-"))
        else:
            only_md = md_keys - set(impl_nonjson)
            only_impl = set(impl_nonjson) - md_keys
            fail("A3a", "md ⇔ 实现 非包络端点不一致：仅 md %s / 仅实现 %s"
                 % (sorted(only_md) or "-", sorted(only_impl) or "-"))
    else:
        info("A3a", "md 与实现均无非包络成功响应（若真实仓库解析到 0 条，先核对解析器）")

    print()
    print("== A4 客户端是否消费「非包络端点」（消费即必判 E-2001 响应格式非法）==")
    nonjson_norm = {norm_client_path(k[1]): k for k in impl_nonjson}
    consumed = []
    for f, arg, norm in sites:
        if norm is None:
            continue
        if norm in nonjson_norm:
            consumed.append("%s: %s" % (f, arg))
    if nonjson_norm and not consumed:
        ok("A4a", "客户端对非包络端点（%s）调用点 = 0 处（正向对照：已解析调用点 %d 处）"
           % (", ".join("%s %s" % (k[0].upper(), k[1]) for k in impl_nonjson), len(sites)))
    elif consumed:
        fail("A4a", "客户端消费非包络端点 %d 处 → 客户端 http.ts 会判「响应格式非法 E-2001」：%s"
             % (len(consumed), "; ".join(consumed)))
    else:
        info("A4a", "无非包络端点，A4 不适用")
    if c["requires_envelope"]:
        info("A4b", "客户端成功路径要求包络（`typeof body.code !== 'string'` → reject E-2001「响应格式非法」）"
                    "→ 非包络端点一旦被消费必失败（当前零消费）")
    else:
        info("A4b", "客户端未做包络形状校验（与本项目实现不符，请核对）")

    print()
    print("== A5 测试对成功状态码的断言值域 ==")
    if tvals:
        n2xx = [v for v in tvals if 200 <= v < 300]
        nerr = [v for v in tvals if v >= 400]
        ok("A5a", "状态断言取值集合 = %s（共 %d 处：2xx %d 处 / 4xx-5xx %d 处）"
           % (sorted(set(tvals)), len(tvals), len(n2xx), len(nerr)))
        non200 = [v for v in n2xx if v != 200]
        if non200:
            info("A5b", "出现非 200 的 2xx 断言值 %s（与 md「0→200」并存，需人工确认是否另有端点）" % sorted(set(non200)))
        else:
            ok("A5b", "2xx 断言 %d 处全部 = 200（无非 200 的 2xx 值）→ 与「成功恒 200」一致" % len(n2xx))
    else:
        fail("A5a", "无成功状态断言 —— 判据失效")

    print()
    print("== A6 openapi 成功状态码集合 ==")
    sets = {}
    for k, v in (oapi or {}).items():
        sets.setdefault(tuple(sorted(v["statuses"])), []).append(k)
    if sets:
        ok("A6a", "openapi 成功状态码集合分布：%s"
           % "; ".join("%s×%d" % (list(s), len(v)) for s, v in sorted(sets.items())))
    else:
        fail("A6a", "openapi 未解析到任何 2xx 状态 —— 解析器失效")
    if md_status:
        odd = [k for s, v in sets.items() for k in v if list(s) != [md_status]]
        if odd:
            fail("A6b", "openapi 声明非 %s 成功状态 %d 条：%s" % (md_status, len(odd), odd[:5]))
        else:
            ok("A6b", "openapi 全部 %d 条 operation 的成功状态码 = {%s}（与 md §4 一致）" % (len(oapi or {}), md_status))

    print()
    print("== A7 根因定位：生成器是否具备「非 JSON 响应」表达能力 ==")
    gen = read(GEN)
    if not gen.strip():
        info("A7a", "生成器源码不可读，跳过根因定位")
    else:
        n_json = gen.count("application/json")
        n_html = gen.count("text/html")
        caller = re.search(r'op\["responses"\]\s*=\s*\{(.{0,400}?)\n\s*\}', gen, re.S)
        caller_txt = " ".join(caller.group(1).split()) if caller else ""
        if n_json:
            ok("A7a1", "生成器源码出现 `application/json` %d 处（正向对照 > 0，说明根因判据真的读到了生成器）" % n_json)
        else:
            fail("A7a1", "生成器源码未出现 `application/json` —— 判据失效")
        if n_html == 0:
            info("A7a", "生成器全文出现 `text/html` 0 处 + 无 `produces` 支持；成功响应在 `op[\"responses\"]` 处恒写 "
                        "`application/json` → **生成器不具备「非 JSON 成功响应」表达能力**，RPT-03 这类端点必然被错声明")
        else:
            ok("A7a", "生成器已出现 `text/html` %d 处（具备非 JSON 响应表达能力）" % n_html)
        info("A7a2", "生成器成功响应装配片段：%s" % (caller_txt[:160] or "-"))
        info("A7b", "生成器 PATHS 的 RPT-03 行：%s"
             % (re.search(r'\("RPT-03".*', gen).group(0).strip() if re.search(r'\("RPT-03".*', gen) else "-"))
    ep = {}
    try:
        ep = json.loads(read(EP)) or {}
    except ValueError:
        ep = {}
    n_null = len([e for e in (ep.get("endpoints") or []) if not e.get("response_model")])
    if n_null:
        info("A7c", "endpoints.json 中 response_model 为 null 的端点 %d 条（openapi 对这些端点统一输出通用 Envelope，"
                    "无法区分「真包络」与「非 JSON 响应」）" % n_null)
    if ep.get("endpoints"):
        ok("A7d", "endpoints.json 解析到 %d 条端点（正向对照 > 0）" % len(ep["endpoints"]))
    else:
        fail("A7d", "endpoints.json 未解析到端点 —— 解析器失效")

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
