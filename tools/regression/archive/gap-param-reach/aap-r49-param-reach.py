"""R49 抽查：请求参数「可达性」一致性 —— 第二十三类可审计不变量。

不变量：**契约（md 清单 / endpoints.json）为每个端点声明的查询参数，
必须在实现的调用链上真的被使用**（控制器方法体 → 可达服务方法体，按位置映射形参名，≤2 跳下游）。

为什么两套门禁都看不见：
  * 契约测试只校验**响应体**与 JSON Schema（schema 里没有 query 参数，query 不是 body）；
  * 覆盖门禁只比「HTTP 方法 + 路径」注册表，参数是否被用与路由注册无关；
  * openapi 与客户端 TS 不被任何测试读取或执行。
  → 控制器声明了 `status` 却从不把它传下去（或传下去但服务方法忽略它）时，
    客户端筛选**静默失效**（后端返回全量），204 例全绿也完全看不见。

真源：
  M = docs/backend/endpoints.json 的 query_params（名字集合已由 audit-query-params 与 md/openapi 对齐）
  I = aap-server/src/main/java/**/*Controller.java（@RequestParam 形参）＋ 可达服务方法体

用法: python aap-r49-param-reach.py [--src-root DIR] [--endpoints FILE] [--out FILE]
只读：不写任何仓库文件（脚本内含真实仓库关键文件 md5 前后比对）。
"""
import argparse
import hashlib
import json
import os
import re
import sys

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MAPPING = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping\b")
CLASS_REQ = re.compile(r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]*)\"")
FIELD = re.compile(r"(?:private|protected|public)\s+(?:final\s+)?([A-Z][A-Za-z0-9_]*)\s+([a-z][A-Za-z0-9_]*)\s*(?:=[^;]*)?;")
PARAM_DECL = re.compile(
    r"@(RequestParam|PathVariable|RequestHeader|AuthenticationPrincipal)\s*"
    r"(\([^)]*\))?\s+"
    r"([A-Za-z0-9_.$<>,\[\]\s]+?)\s+([a-zA-Z_][A-Za-z0-9_]*)\s*(?=[,)])"
)


def strip_comments(text):
    """剥离注释（用空格替换以保行号），保留字符串字面量内容。"""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            out.append(text[i:j + 1])
            i = j + 1
        elif c == "'":
            j = text.find("'", i + 1)
            if j == -1:
                out.append(c)
                i += 1
            else:
                out.append(text[i:j + 1])
                i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i)
            j = n if j == -1 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_paren(text, open_idx):
    """open_idx 指向 '('，返回匹配 ')' 的下标；失败返回 -1（字符串内括号成对，不会误判）。"""
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_body(text, start):
    """括号深度扫描找方法体 '{'（坑 55/63：无实参注解后面直接跟签名）。"""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "{" and depth == 0:
            return i
        elif ch == ";" and depth == 0:
            return -1
        i += 1
    return -1


def split_top(text):
    """按顶层逗号切分实参列表。"""
    parts, depth, cur, i, n = [], 0, [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            cur.append(text[i:j + 1])
            i = j + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def norm_path(p):
    p = p or ""
    p = re.sub(r"\{[^}]*\}", "{}", p)
    if p and not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/") or "/"


def parse_java(path):
    """解析一个 java 文件：类名、类级 @RequestMapping 前缀、方法列表。"""
    raw = open(path, encoding="utf-8", errors="replace").read()
    code = strip_comments(raw)
    cm = re.search(r"\bclass\s+([A-Za-z0-9_]+)", code)
    cls = cm.group(1) if cm else os.path.basename(path)[:-5]
    prefix = ""
    cmr = list(CLASS_REQ.finditer(code))
    class_pos = cm.start() if cm else len(code)
    for m in cmr:
        if m.start() < class_pos:
            prefix = m.group(1)
    methods = []
    for m in MAPPING.finditer(code):
        verb = m.group(1).upper()
        after = m.end()
        seg = code[after:after + 400]
        path_arg = None
        if seg.lstrip().startswith("("):
            oi = after + len(seg) - len(seg.lstrip())
            ci = match_paren(code, oi)
            if ci == -1:
                continue
            inner = code[oi + 1:ci]
            sm = re.search(r"\"([^\"]*)\"", inner)
            path_arg = sm.group(1) if sm else ""
            sig_start = ci + 1
        else:
            path_arg = ""          # 裸注解：路径 = 类级前缀（坑 87）
            sig_start = after
        body_open = find_body(code, sig_start)
        if body_open == -1:
            continue
        body_close = match_paren(code, body_open) if False else None
        # 方法体用花括号扫描
        depth = 0
        i = body_open
        n = len(code)
        end = -1
        while i < n:
            ch = code[i]
            if ch == '"':
                i += 1
                while i < n:
                    if code[i] == "\\":
                        i += 2
                        continue
                    if code[i] == '"':
                        break
                    i += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1
        if end == -1:
            continue
        sig = code[sig_start:body_open]
        params = []
        for pm in PARAM_DECL.finditer(sig):
            kind = pm.group(1)
            if kind == "RequestParam":
                params.append({"kind": "query", "name": pm.group(4)})
            elif kind == "PathVariable":
                params.append({"kind": "path", "name": pm.group(4)})
            else:
                params.append({"kind": "other", "name": pm.group(4)})
        nm = re.search(r"([A-Za-z0-9_]+)\s*\(", sig)
        fields = {v: t for t, v in FIELD.findall(code)}
        methods.append({
            "file": path, "cls": cls, "verb": verb,
            "path": norm_path((prefix + (path_arg or ""))),
            "name": nm.group(1) if nm else "?",
            "params": params,
            "fields": fields,
            "body": code[body_open + 1:end],
            "body_start_line": code[:body_open].count("\n") + 1,
        })
    return {"file": path, "cls": cls, "prefix": prefix, "code": code,
            "fields": {v: t for t, v in FIELD.findall(code)}, "methods": methods}


def build_repo(src_root):
    controllers, by_class, all_classes = [], {}, {}
    for dirpath, _d, files in os.walk(src_root):
        for fn in files:
            if not fn.endswith(".java"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                info = parse_java(p)
            except Exception as e:  # noqa
                print("WARN 解析失败 %s: %s" % (p, e))
                continue
            all_classes[info["cls"]] = info
            if fn.endswith("Controller.java"):
                controllers.append(info)
            by_class[info["cls"]] = info
    return controllers, all_classes


CALL = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# 无接收者的同类调用（parseId(x)、page(...) 等）：不能漏，否则实参追踪会退化成「弱证据」（坑 63/87 同族）
BARE_CALL = re.compile(r"(?<![.\w])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "synchronized",
            "assert", "throw", "try", "do", "else", "case"}


def call_arg_spans(body):
    """返回 [(span_start, span_end, receiver|None, method, args)]；同类调用 receiver=None。"""
    out = []
    seen = set()
    for m in CALL.finditer(body):
        oi = body.find("(", m.end() - 1)
        if oi == -1:
            continue
        ci = match_paren(body, oi)
        if ci == -1:
            continue
        out.append((oi + 1, ci, m.group(1), m.group(2), split_top(body[oi + 1:ci])))
        seen.add(oi)
    for m in BARE_CALL.finditer(body):
        name = m.group(1)
        if name in KEYWORDS:
            continue
        oi = m.end() - 1
        if oi in seen:
            continue
        ci = match_paren(body, oi)
        if ci == -1:
            continue
        out.append((oi + 1, ci, None, name, split_top(body[oi + 1:ci])))
    return out


def count_top_commas(text):
    """数顶层逗号（坑 64：只在顶层认分隔符）。"""
    depth, cnt, i, n = 0, 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            cnt += 1
        i += 1
    return cnt


def reach(body, name, all_classes, owner, depth, seen):
    """跟踪 name 在该方法体里是否被使用；返回 (status, path_desc)。
    status: USED_DIRECT / USED_DOWNSTREAM / WEAK_UNRESOLVED / NOT_USED
    """
    key = (owner["cls"], name, depth)
    if key in seen or depth > 3:      # 调用链 ≤3 跳下游（控制器体 → 服务 → 私有助手 → 工具类）
        return None, None
    seen.add(key)
    spans = call_arg_spans(body)
    occ = [m.start() for m in re.finditer(r"\b%s\b" % re.escape(name), body)]
    if not occ:
        return "NOT_USED", None
    weak = False
    for pos in occ:
        # 取**最内层**包含该位置的实参跨度：外层调用的跨度也包含它，选错会退化成弱证据
        in_arg = None
        for span in spans:
            s, e = span[0], span[1]
            if s <= pos < e:
                if in_arg is None or (e - s) < (in_arg[1] - in_arg[0]):
                    in_arg = span
        if in_arg is None:
            return "USED_DIRECT", "%s.%s" % (owner["cls"], owner["name"])
        # 落在某个调用的实参列表里 → 追下游
        s, e, recv, meth, args = in_arg
        idx = count_top_commas(body[s:pos])
        if idx >= len(args):
            weak = True
            continue
        arg_text = args[idx]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", arg_text):
            # 表达式实参（如 status.trim()、parseId(x)）→ 该值在本层被消费
            return "USED_DIRECT", "%s.%s" % (owner["cls"], owner["name"])
        if recv is None:
            tgt = all_classes.get(owner["cls"])
        elif recv == "this":
            tgt = all_classes.get(owner["cls"])
        elif recv in owner["fields"]:
            tgt = all_classes.get(owner["fields"][recv])
        else:
            tgt = all_classes.get(recv[:1].upper() + recv[1:])
        if tgt is None:
            weak = True
            continue
        callee = None
        for cm2 in tgt["methods"]:
            if cm2["name"] == meth:
                callee = cm2
                break
        if callee is None:
            # 尝试匹配同文件任意方法（含无映射注解的私有方法）
            callee = find_plain_method(tgt["code"], meth, tgt["fields"], tgt["cls"])
        if callee is None:
            weak = True
            continue
        pnames = [p["name"] for p in callee["params"]]
        if idx >= len(pnames):
            weak = True
            continue
        st, desc = reach(callee["body"], pnames[idx], all_classes, callee, depth + 1, seen)
        if st in ("USED_DIRECT", "USED_DOWNSTREAM"):
            return "USED_DOWNSTREAM", "%s.%s(%s)" % (tgt["cls"], meth, pnames[idx])
        if st == "WEAK_UNRESOLVED":
            weak = True
    return ("WEAK_UNRESOLVED", None) if weak else ("NOT_USED", None)


PLAIN_METHOD = re.compile(r"\b([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{")


def find_plain_method(code, name, fields=None, cls="?"):
    for m in PLAIN_METHOD.finditer(code):
        if m.group(1) != name:
            continue
        oi = code.find("(", m.start(1))
        ci = match_paren(code, oi)
        if ci == -1:
            continue
        body_open = find_body(code, ci + 1)
        if body_open == -1:
            continue
        depth, i, n, end = 0, body_open, len(code), -1
        while i < n:
            ch = code[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1
        if end == -1:
            continue
        sig = code[m.start(1):body_open]
        params = []
        for pm in PARAM_DECL.finditer(sig):
            params.append({"kind": pm.group(1), "name": pm.group(4)})
        if not params:
            raw = code[oi + 1:ci]
            for tok in split_top(raw):
                tm = re.fullmatch(r"(?:final\s+)?[A-Za-z0-9_.$<>,\[\]\s]+?\s+([a-zA-Z_][A-Za-z0-9_]*)", tok)
                if tm:
                    params.append({"kind": "plain", "name": tm.group(1)})
        return {"file": None, "cls": cls, "name": name, "params": params,
                "fields": fields or {},
                "body": code[body_open + 1:end], "path": "", "verb": ""}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-root", default=os.path.join(ROOT, "aap-server/src/main/java"))
    ap.add_argument("--endpoints", default=os.path.join(ROOT, "docs/backend/endpoints.json"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    watch = [
        os.path.join(ROOT, "aap-server/src/main/java/com/hioas/aap/contract/ContractController.java"),
        os.path.join(ROOT, "aap-server/src/main/java/com/hioas/aap/contract/ContractService.java"),
        os.path.join(ROOT, "docs/backend/endpoints.json"),
    ]
    before = {f: hashlib.md5(open(f, "rb").read()).hexdigest() for f in watch if os.path.exists(f)}

    data = json.load(open(args.endpoints, encoding="utf-8"))
    eps = data["endpoints"] if isinstance(data, dict) else data
    controllers, all_classes = build_repo(args.src_root)
    index = {}
    for c in controllers:
        for m in c["methods"]:
            index[(m["verb"], m["path"])] = (c, m)

    lines = []
    lines.append("== R49 抽查：请求参数可达性一致性 —— 第二十三类可审计不变量 ==")
    lines.append("不变量：契约声明的每个查询参数，必须在实现调用链上真的被使用（控制器体 → 可达服务方法，≤3 跳下游）")
    lines.append("真源：M=docs/backend/endpoints.json 的 query_params ⇔ I=控制器 @RequestParam 形参及其调用链")
    lines.append("")

    withq = [e for e in eps if e.get("query_params")]
    n_params = sum(len(e["query_params"]) for e in withq)
    located, unlocated = [], []
    results = []
    for e in withq:
        # 跨源比对两侧必须走同一个归一函数（坑 57：前缀/{} 折叠不一致会报出全量假发现）
        key = (e["method"].upper(), norm_path(e["path"]))
        hit = index.get(key)
        if hit is None:
            unlocated.append(e["id"])
            continue
        c, m = hit
        located.append(e["id"])
        decl = {p["name"] for p in m["params"] if p["kind"] == "query"}
        for qp in e["query_params"]:
            if qp not in decl:
                results.append((e["id"], qp, "NOT_DECLARED", None))
                continue
            st, desc = reach(m["body"], qp, all_classes, m, 0, set())
            results.append((e["id"], qp, st or "NOT_USED", desc))

    n_direct = sum(1 for r in results if r[2] == "USED_DIRECT")
    n_down = sum(1 for r in results if r[2] == "USED_DOWNSTREAM")
    n_weak = sum(1 for r in results if r[2] == "WEAK_UNRESOLVED")
    n_bad = [r for r in results if r[2] in ("NOT_USED", "NOT_DECLARED")]

    lines.append("解析：控制器文件 %d 个、控制器方法 %d 条；带查询参数的端点 %d 条（查询参数共 %d 个）"
                 % (len(controllers), sum(len(c["methods"]) for c in controllers), len(withq), n_params))
    lines.append("定位：已定位端点 %d / %d；未定位 %d（%s）"
                 % (len(located), len(withq), len(unlocated), ", ".join(unlocated) or "无"))
    lines.append("")
    # 正向对照（坑 46/75/98）
    n_methods = sum(len(c["methods"]) for c in controllers)
    lines.append("  [%s] A0a 解析到控制器方法数 > 0（正向对照） | %d"
                 % ("PASS" if n_methods > 0 else "FAIL ", n_methods))
    lines.append("  [%s] A0b 解析到带查询参数的端点 > 0（正向对照） | %d"
                 % ("PASS" if len(withq) > 0 else "FAIL ", len(withq)))
    lines.append("  [%s] A0c 解析到查询参数总数 > 0（正向对照） | %d"
                 % ("PASS" if n_params > 0 else "FAIL ", n_params))
    lines.append("  [%s] A0d 端点定位率 ≥ 90%% | 已定位 %d/%d"
                 % ("PASS" if withq and len(located) >= 0.9 * len(withq) else "FAIL ", len(located), len(withq)))
    lines.append("  [%s] A0e 下游解析分支真的走到（downstream > 0；direct 分支由夹具自测覆盖——真实仓库控制器多为纯转发） | direct=%d downstream=%d"
                 % ("PASS" if n_down > 0 else "FAIL ", n_direct, n_down))
    lines.append("")
    n_notused = [r for r in results if r[2] == "NOT_USED"]
    n_notdecl = [r for r in results if r[2] == "NOT_DECLARED"]
    lines.append("  [%s] A1 控制器已接收的查询参数在调用链上可达 | 可达 %d / 未可达 %d / 参与判定 %d"
                 % ("PASS" if (results and not n_notused) else "FAIL ",
                    len(results) - len(n_notused) - len(n_notdecl), len(n_notused), len(results)))
    if not results:
        lines.append("  [FAIL ] A1 参与判定的查询参数为 0 → 判「解析器失效」，不得据此判「全部可达」（坑 46/98）")
    for eid, qp, st, _ in n_notused:
        lines.append("  [FAIL ] A1 %s 查询参数 `%s`：控制器已声明接收，但调用链上**未被使用**"
                     "（客户端传参会静默失效，坑 62 同族）" % (eid, qp))
    lines.append("  [%s] A2 契约声明的查询参数控制器侧都接收（@RequestParam 集合) | 未接收 %d 条"
                 % ("PASS" if not n_notdecl else "FAIL ", len(n_notdecl)))
    for eid, qp, st, _ in n_notdecl:
        lines.append("  [FAIL ] A2 %s 查询参数 `%s`：契约(endpoints.json/openapi)声明，但实现控制器**未接收**"
                     "（生成物侧多声明；与 audit-query-params 的 A1/A3b 同源）" % (eid, qp))
    lines.append("  [INFO] A1b 弱证据（已传入但下游不可静态解析）条数（信息项，非漂移） | %d" % n_weak)
    for r in results:
        if r[2] == "WEAK_UNRESOLVED":
            lines.append("  [INFO] A1b %s 查询参数 `%s`：实参已传入下游，但下游方法/类型不可静态解析" % (r[0], r[1]))
    lines.append("")
    lines.append("== 逐端点结果 ==")
    for eid, qp, st, desc in results:
        lines.append("  %-10s %-14s %-16s %s" % (eid, qp, st, desc or "-"))
    lines.append("")
    lines.append("== 零写副作用守卫 ==")
    after = {f: hashlib.md5(open(f, "rb").read()).hexdigest() for f in watch if os.path.exists(f)}
    same = before == after
    lines.append("  比对文件 %d 个，md5 全等：%s" % (len(before), same))
    lines.append("")

    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0 if (not n_bad and same) else 1


if __name__ == "__main__":
    sys.exit(main())
