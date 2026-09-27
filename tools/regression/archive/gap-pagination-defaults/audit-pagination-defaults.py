"""R46 抽查（只读，不新增仓库工具）：**分页参数的缺省值与上限（取值域）不变量**。

为什么值得配审计（第二十类「两套门禁都看不见」的契约不变量）：
  - 契约测试只读各模型的 JSON Schema，而 **query 参数不在 schema 里**（schema 描述的是 body/响应）；
  - 覆盖门禁只比「方法 + 路径」注册表；
  - openapi 与客户端 TS 不被任何测试读取/执行。
  → 「page 默认 1 / pageSize 默认 20、上限 200」写错（例如上限写成 2000、缺省写成 10）时，204 例全绿也看不见；
    后果：按 openapi 生成客户端的消费方拿不到缺省值/上限；服务端若不夹取则 pageSize 可无限放大（全表扫描）。

真源：
  M = md `02-API接口模型清单.md` §0 分页行（缺省 1 / 缺省 20 / 上限 200）
  O = `docs/backend/openapi.yaml` 逐端点 `in: query` 的 page/pageSize 参数的 minimum/maximum/default
  I = 实现：`common/PageQuery.java` 常量与夹取表达式 + 控制器/服务方法是否真的经过 `PageQuery.of`
  C = 客户端 `aap-client/src` 分页实参与常量（弱证据：显式传参合法，只校验不越上限）
  T = 测试源里对缺省/上限的断言（信息项：有断言才算被守卫）

断言（FAIL = 契约漂移，INFO = 观察项）：
  A0a/A0b/A0c/A0d 四个源的正向对照（解析到 0 条先怀疑解析器 —— 坑 46/75/98）
  A1 O 的每个参数都声明 default（= M 的缺省值）
  A2 O 的每个 pageSize 参数都声明 maximum（= M 的上限）
  A3 O 的每个参数 minimum = M 的下界 1
  A4 I 的 DEFAULT_PAGE_SIZE/MAX_PAGE_SIZE = M 的缺省/上限，且夹取表达式真的对 pageSize 取 min
  A5 每个分页控制器方法：夹取发生在控制器方法体内，或发生在其直接调用的服务方法体内
  A6 接收**裸** `int pageSize` 的分页服务方法：其全部调用点都传入夹取后的值（`pageSize()`）
  A7 客户端显式分页实参/常量都 <= M 的上限
  A8 测试源存在「缺省 = 20」的断言（> 0 才算被守卫）
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

DEFAULT_ROOT = r"E:/workspaces/hioas/hioas-aap-001"
MAP_ANN = re.compile(r"@(Get|Post|Put|Delete|Patch)Mapping")
PAGE_PARAM = re.compile(r"^\s*- name: (page|pageSize)\s*$")


# ----------------------------------------------------------------- 解析工具
def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def skip_ws(text, i):
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def skip_string(text, i):
    q = text[i]
    i += 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == q:
            return i + 1
        i += 1
    return i


def scan_to_matching(text, i, open_ch, close_ch):
    """从 text[i]（应为 open_ch）起做括号深度扫描，跳过字符串字面量（坑 55：字符串内花括号成对）。"""
    depth = 0
    while i < len(text):
        c = text[i]
        if c in "\"'":
            i = skip_string(text, i)
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def java_files(root, sub):
    base = os.path.join(root, sub)
    out = []
    for dirpath, _dirnames, filenames in os.walk(base):
        for fn in filenames:
            if fn.endswith(".java"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def rel(root, path):
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:  # 跨盘符（坑 34）
        return path.replace("\\", "/")


def class_names(text):
    return re.findall(r"\b(?:public\s+|final\s+|abstract\s+)*(?:class|interface|record|enum)\s+([A-Za-z_$][\w$]*)", text)


def scan_controller_methods(text):
    """解析控制器里的映射方法：类级 @RequestMapping 前缀 + 方法级（允许裸注解，坑 63/87）。"""
    prefix = None
    cls = re.search(r"\bclass\s+[A-Za-z_$][\w$]*", text)
    head = text[:cls.start()] if cls else text
    for m in re.finditer(r"@RequestMapping\s*\(([^)]*)\)", head):
        pm = re.search(r'"([^"]*)"', m.group(1))
        if pm:
            prefix = pm.group(1)
    out = []
    pos = 0
    while True:
        m = MAP_ANN.search(text, pos)
        if not m:
            break
        kind = m.group(1).upper()
        i = m.end()
        ann_path = None
        j = skip_ws(text, i)
        if j < len(text) and text[j] == "(":
            close = scan_to_matching(text, j, "(", ")")
            if close < 0:
                pos = m.end()
                continue
            pm = re.search(r'"([^"]*)"', text[j:close])
            if pm:
                ann_path = pm.group(1)
            i = close + 1
        # 跳过后续注解（本项目写法：映射注解在前、@PreAuthorize 在后 —— 坑 55/63）
        while True:
            j = skip_ws(text, i)
            if j < len(text) and text[j] == "@":
                k = j + 1
                while k < len(text) and (text[k].isalnum() or text[k] in "._$"):
                    k += 1
                j2 = skip_ws(text, k)
                if j2 < len(text) and text[j2] == "(":
                    close = scan_to_matching(text, j2, "(", ")")
                    if close < 0:
                        break
                    i = close + 1
                else:
                    i = k
                continue
            break
        p = text.find("(", skip_ws(text, i))
        if p < 0:
            break
        nm = re.search(r"([A-Za-z_$][\w$]*)\s*$", text[:p])
        if not nm:
            pos = p + 1
            continue
        mname = nm.group(1)
        close_p = scan_to_matching(text, p, "(", ")")
        if close_p < 0:
            pos = p + 1
            continue
        params = text[p + 1:close_p]
        bstart = skip_ws(text, close_p + 1)
        if text[bstart:bstart + 6] == "throws":
            bstart = text.find("{", bstart)
        if bstart < 0 or bstart >= len(text) or text[bstart] != "{":
            pos = close_p + 1
            continue
        bend = scan_to_matching(text, bstart, "{", "}")
        body = text[bstart:bend + 1] if bend > 0 else ""
        full = (prefix or "") + (ann_path or "")
        out.append({"method": kind, "path": full, "name": mname, "params": params, "body": body})
        pos = bend + 1 if bend > 0 else close_p + 1
    return out


def named_method_body(text, mname):
    """按方法名找方法体与形参表（服务层用）。"""
    for m in re.finditer(r"(?<![\w$.])" + re.escape(mname) + r"\s*\(", text):
        p = m.end() - 1
        close = scan_to_matching(text, p, "(", ")")
        if close < 0:
            continue
        params = text[p + 1:close]
        bstart = skip_ws(text, close + 1)
        if text[bstart:bstart + 6] == "throws":
            bstart = text.find("{", bstart)
        if bstart < 0 or bstart >= len(text) or text[bstart] != "{":
            continue
        bend = scan_to_matching(text, bstart, "{", "}")
        if bend < 0:
            continue
        return params, text[bstart:bend + 1]
    return None, None


def raw_int_page_size_methods(text):
    """找「形参含裸 int pageSize（非 Integer）」的方法（排除 record/class 声明 —— 坑 74 同族）。"""
    out = []
    for m in re.finditer(r"\(", text):
        p = m.start()
        close = scan_to_matching(text, p, "(", ")")
        if close < 0:
            continue
        params = text[p + 1:close]
        if not re.search(r"(?<!Integer )\bint\s+pageSize\b", params) or "Integer pageSize" in params:
            continue
        nm = re.search(r"([A-Za-z_$][\w$]*)\s*$", text[:p])
        if not nm:
            continue
        before = text[:nm.start()].rstrip()
        if re.search(r"\b(record|class|interface|new)\s*$", before):
            continue
        out.append((nm.group(1), params))
    return out


# ----------------------------------------------------------------- 四个真源
def parse_md(root, src):
    path = os.path.join(root, "docs/backend/02-API接口模型清单.md")
    if not os.path.exists(path):
        return None
    for line in read(path).splitlines():
        if "分页" in line and "默认" in line and "上限" in line:
            d = [int(x) for x in re.findall(r"默认\s*(\d+)", line)]
            mx = [int(x) for x in re.findall(r"上限\s*(\d+)", line)]
            src["md_line"] = line.strip()[:120]
            return {"defaults": d, "max": mx[0] if mx else None}
    return None


def parse_openapi(root, src):
    path = os.path.join(root, "docs/backend/openapi.yaml")
    if not os.path.exists(path):
        return None
    lines = read(path).splitlines()
    params = []
    cur_path = None
    cur_method = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        mp = re.match(r"^  (/[^:]+):\s*$", ln)
        if mp:
            cur_path, cur_method = mp.group(1), None
            i += 1
            continue
        mm = re.match(r"^    (get|post|put|delete|patch):\s*$", ln)
        if mm:
            cur_method = mm.group(1).upper()
            i += 1
            continue
        pm = PAGE_PARAM.match(ln)
        if pm:
            indent = len(ln) - len(ln.lstrip())
            name = pm.group(1)
            item = {"path": cur_path, "method": cur_method, "name": name,
                    "in": None, "minimum": None, "maximum": None, "default": None}
            j = i + 1
            while j < len(lines):
                l2 = lines[j]
                if not l2.strip():
                    j += 1
                    continue
                ind2 = len(l2) - len(l2.lstrip())
                if ind2 <= indent:
                    break
                b = l2.strip()
                for k in ("in", "minimum", "maximum", "default"):
                    if b.startswith(k + ":"):
                        item[k] = b.split(":", 1)[1].strip()
                j += 1
            params.append(item)
            i = j
            continue
        i += 1
    return params


def parse_impl(root, src):
    path = os.path.join(root, "aap-server/src/main/java/com/hioas/aap/common/PageQuery.java")
    if not os.path.exists(path):
        return None
    t = read(path)
    d = re.search(r"DEFAULT_PAGE_SIZE\s*=\s*(\d+)", t)
    m = re.search(r"MAX_PAGE_SIZE\s*=\s*(\d+)", t)
    clamp = re.search(r"Math\.min\(\s*pageSize\s*,\s*MAX_PAGE_SIZE\s*\)", t)
    lower = re.search(r"pageSize\s*==\s*null\s*\|\|\s*pageSize\s*<\s*1\s*\?\s*DEFAULT_PAGE_SIZE", t)
    return {"default": int(d.group(1)) if d else None, "max": int(m.group(1)) if m else None,
            "clamp_min": bool(clamp), "clamp_lower": bool(lower)}


def parse_client(root, src):
    base = os.path.join(root, "aap-client/src")
    if not os.path.isdir(base):
        return None
    vals = []
    for dirpath, _dn, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith((".ts", ".vue", ".js")):
                continue
            p = os.path.join(dirpath, fn)
            t = read(p)
            for m in re.finditer(r"pageSize\s*:\s*(\d+)", t):
                vals.append((rel(root, p), int(m.group(1)), "实参"))
            for m in re.finditer(r"PAGE_SIZE\s*=\s*(\d+)", t):
                vals.append((rel(root, p), int(m.group(1)), "常量"))
    return vals


def parse_tests(root, src):
    base = os.path.join(root, "aap-server/src/test/java")
    if not os.path.isdir(base):
        return None
    dflt = 0
    upper = 0
    for p in java_files(root, "aap-server/src/test/java"):
        t = read(p)
        dflt += len(re.findall(r'pageSize"\)\.asInt\(\)\)\.isEqualTo\((\d+)\)', t))
        upper += len(re.findall(r"MAX_PAGE_SIZE|pageSize\s*=\s*2[0-9][0-9]\b", t))
    return {"default_asserts": dflt, "upper_asserts": upper}


# ----------------------------------------------------------------- 主审计
def audit(root):
    fails, passes, infos = [], [], []
    src = {}
    md = parse_md(root, src)
    oa = parse_openapi(root, src)
    impl = parse_impl(root, src)
    cli = parse_client(root, src)
    tst = parse_tests(root, src)

    # ---- 正向对照
    if not md or len(md["defaults"]) < 2 or md["max"] is None:
        fails.append("A0a M 解析到 md §0 的缺省值(2 个)与上限(1 个)")
    else:
        passes.append("A0a M md §0 解析到 缺省=%s 上限=%s" % (md["defaults"], md["max"]))
    if not oa:
        fails.append("A0b O 解析到 openapi 的 page/pageSize 参数 > 0")
        oa = []
    else:
        passes.append("A0b O openapi 解析到 page/pageSize 参数 %d 个（page %d / pageSize %d）"
                      % (len(oa), sum(1 for x in oa if x["name"] == "page"),
                         sum(1 for x in oa if x["name"] == "pageSize")))
    if not impl or impl["default"] is None or impl["max"] is None:
        fails.append("A0c I 解析到 PageQuery 的 DEFAULT_PAGE_SIZE 与 MAX_PAGE_SIZE")
        impl = impl or {}
    else:
        passes.append("A0c I 解析到 PageQuery 常量 default=%s max=%s clamp_min=%s clamp_lower=%s"
                      % (impl["default"], impl["max"], impl["clamp_min"], impl["clamp_lower"]))
    ctrls = []
    for p in java_files(root, "aap-server/src/main/java"):
        t = read(p)
        if "pageSize" not in t:
            continue
        for m in scan_controller_methods(t):
            if "Integer pageSize" in m["params"]:
                m["file"] = rel(root, p)
                ctrls.append(m)
    if not ctrls:
        fails.append("A0d 控制器里带 Integer pageSize 的映射方法解析到 > 0")
    else:
        passes.append("A0d 控制器解析到带 pageSize 的映射方法 %d 个（跨 %d 个文件）"
                      % (len(ctrls), len({c["file"] for c in ctrls})))

    # 端点 ID 映射（供 FAIL 文案点名）
    ep_map = {}
    ep_path = os.path.join(root, "docs/backend/endpoints.json")
    if os.path.exists(ep_path):
        try:
            data = json.loads(read(ep_path))
            items = data.get("endpoints", data) if isinstance(data, dict) else data
            for it in items:
                pth = it.get("path", "")
                if pth.startswith("/api/v1"):
                    pth = pth[len("/api/v1"):]
                ep_map[(it.get("method", "").upper(), pth or "/")] = it.get("id")
        except Exception:
            pass

    def ep_of(m):
        # 两侧必须走同一个归一函数（坑 57）：控制器路径带 /api/v1 前缀，endpoints.json 的键已剥前缀
        p = m["path"] or "/"
        if p.startswith("/api/v1"):
            p = p[len("/api/v1"):] or "/"
        return ep_map.get((m["method"], p), "%s %s" % (m["method"], m["path"] or "/"))

    # ---- A1/A2/A3：openapi 逐参数（空作用域必须显式判红 —— 坑 75/98：0 条不能算通过）
    if not oa:
        fails.append("A1 openapi 无 page/pageSize 参数（空作用域，不得判通过）")
        fails.append("A2 openapi 无 pageSize 参数（空作用域，不得判通过）")
        fails.append("A3 openapi 无参数（空作用域，不得判通过）")
    if md and oa:
        d_page, d_size = (md["defaults"] + [None, None])[:2]
        miss_def = [x for x in oa if x["default"] is None]
        if miss_def:
            sample = "、".join("%s(%s)" % (ep_map.get((x["method"], x["path"]), x["path"]), x["name"])
                              for x in miss_def[:5])
            fails.append("A1 openapi 每个 page/pageSize 参数都声明 default：缺失 %d/%d（样例 %s）"
                         % (len(miss_def), len(oa), sample))
        else:
            passes.append("A1 openapi %d/%d 个参数都声明了 default" % (len(oa), len(oa)))
        miss_max = [x for x in oa if x["name"] == "pageSize" and x["maximum"] is None]
        if miss_max:
            fails.append("A2 openapi 每个 pageSize 参数都声明 maximum：缺失 %d/%d"
                         % (len(miss_max), sum(1 for x in oa if x["name"] == "pageSize")))
        else:
            passes.append("A2 openapi pageSize 参数都声明了 maximum")
        bad_min = [x for x in oa if x["minimum"] != "1"]
        if bad_min:
            fails.append("A3 openapi 每个 page/pageSize 参数 minimum = 1：不合 %d/%d" % (len(bad_min), len(oa)))
        else:
            passes.append("A3 openapi %d/%d 个参数 minimum = 1" % (len(oa), len(oa)))

    # ---- A4：实现常量与夹取
    if md and impl:
        d_page, d_size = (md["defaults"] + [None, None])[:2]
        ok = (impl.get("default") == d_size and impl.get("max") == md["max"]
              and impl.get("clamp_min") and impl.get("clamp_lower"))
        if ok:
            passes.append("A4 实现 DEFAULT_PAGE_SIZE=%s/MAX_PAGE_SIZE=%s 与 md 一致且夹取含 Math.min(pageSize,MAX) 与下界兜底"
                          % (impl["default"], impl["max"]))
        else:
            fails.append("A4 实现常量/夹取 = md 缺省 %s 与上限 %s：实际 default=%s max=%s clamp_min=%s clamp_lower=%s"
                         % (d_size, md["max"], impl.get("default"), impl.get("max"),
                            impl.get("clamp_min"), impl.get("clamp_lower")))

    # ---- A5：控制器方法体、或其调用链（≤3 跳）内的服务方法必须出现 PageQuery.of
    svc_index = {}
    for p in java_files(root, "aap-server/src/main/java"):
        t = read(p)
        for cn in class_names(t):
            if cn.endswith("Service"):
                svc_index.setdefault(cn, t)

    BARE_SKIP = {"if", "for", "while", "switch", "return", "new", "Math", "List", "PageResult",
                 "PageQuery", "Page", "String", "Integer", "Long", "Objects", "Map", "Set", "of",
                 "empty", "require", "parseId", "rfc3339", "idText", "super", "this", "catch",
                 "synchronized", "assert", "throw", "log", "auditService", "stringBuilder"}

    def clamps(cls_var, mname, depth=0, seen=None):
        """夹取是否出现在「cls_var.mname」的方法体内或其后继调用链里（≤3 跳）。"""
        if depth > 3:
            return False
        seen = seen or set()
        for cand in (cls_var, cls_var[0].upper() + cls_var[1:]):
            key = (cand, mname)
            if key in seen or cand not in svc_index:
                continue
            seen.add(key)
            _params, body = named_method_body(svc_index[cand], mname)
            if not body:
                continue
            if "PageQuery.of" in body:
                return True
            # 跨类服务链（如 contractService.page(...)）
            for c2, m2 in re.findall(r"([A-Za-z_$][\w$]*Service)\.([A-Za-z_$][\w$]*)\s*\(", body):
                if clamps(c2, m2, depth + 1, seen):
                    return True
            # 同类内私有助手（如 listForProvider → page(...)）—— 不带接收者或 this. 的裸调用
            for m2 in re.findall(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(", body):
                if m2 in BARE_SKIP or m2 == mname:
                    continue
                if clamps(cand, m2, depth + 1, seen):
                    return True
        return False

    unclamped = []
    for c in ctrls:
        if "PageQuery.of" in c["body"]:
            continue
        ok = False
        for cls, mname in re.findall(r"([A-Za-z_$][\w$]*Service)\.([A-Za-z_$][\w$]*)\s*\(", c["body"]):
            if clamps(cls, mname):
                ok = True
                break
        if not ok:
            unclamped.append("%s(%s)" % (ep_of(c), c["file"].split("/")[-1]))
    if unclamped:
        fails.append("A5 每个分页控制器方法的 pageSize 都经 PageQuery.of 夹取（控制器或其所调服务）：未夹取 %d 条 %s"
                     % (len(unclamped), unclamped[:5]))
    elif not ctrls:
        fails.append("A5 空作用域：未解析到任何分页控制器方法（不得判通过）")
    else:
        passes.append("A5 %d 个分页控制器方法的 pageSize 都在控制器或其所调服务方法内经 PageQuery.of 夹取" % len(ctrls))

    # ---- A6：接收裸 int pageSize 的服务方法，其调用点必须传夹取后的值
    raw_sites = []
    all_java = {p: read(p) for p in java_files(root, "aap-server/src/main/java")}
    for p, t in all_java.items():
        for mname, params in raw_int_page_size_methods(t):
            if not mname.endswith("") or mname in ("of", "empty"):
                continue
            callers = []
            for fp, ft in all_java.items():
                for cm in re.finditer(r"\.\s*" + re.escape(mname) + r"\s*\(", ft):
                    pp = cm.end() - 1
                    cl = scan_to_matching(ft, pp, "(", ")")
                    if cl < 0:
                        continue
                    args = ft[pp + 1:cl]
                    if "Integer pageSize" in args:  # 声明，不是调用点
                        continue
                    callers.append((rel(root, fp), args))
            bad = [c for c in callers if "pageSize()" not in c[1]]
            raw_sites.append({"cls": class_names(t)[0] if class_names(t) else rel(root, p),
                              "method": mname, "callers": len(callers), "bad": bad})
    if not raw_sites:
        fails.append("A6 解析到接收裸 int pageSize 的分页服务方法 > 0（正向对照）")
    else:
        bad_all = [s for s in raw_sites if s["bad"] or s["callers"] == 0]
        if bad_all:
            desc = ["%s.%s(调用点 %d，未传夹取值 %d)" % (s["cls"], s["method"], s["callers"], len(s["bad"]))
                    for s in bad_all]
            fails.append("A6 裸 int pageSize 的服务方法其调用点都传夹取后的值：不合 %s" % desc[:5])
        else:
            passes.append("A6 裸 int pageSize 的服务方法 %d 个（%s）其调用点全部传入夹取后的值"
                          % (len(raw_sites), "、".join("%s.%s" % (s["cls"], s["method"]) for s in raw_sites)))

    # ---- A7：客户端
    if cli is None:
        fails.append("A7 解析到客户端分页实参/常量（目录缺失）")
    elif not cli:
        fails.append("A7 客户端分页实参/常量解析到 0 处（空作用域，不得判通过）")
    elif md:
        over = [v for v in cli if v[1] > md["max"]]
        if over:
            fails.append("A7 客户端分页实参/常量 <= 上限 %s：越界 %d 处 %s" % (md["max"], len(over), over[:5]))
        else:
            passes.append("A7 客户端分页实参/常量 %d 处（值集合 %s）全部 <= 上限 %s"
                          % (len(cli), sorted({v[1] for v in cli}), md["max"]))
    # ---- A8：测试守卫
    if tst is None:
        fails.append("A8 解析到测试源（目录缺失）")
    else:
        if tst["default_asserts"] > 0:
            passes.append("A8 测试源有 %d 处「响应 pageSize = 20」的缺省断言" % tst["default_asserts"])
        else:
            fails.append("A8 测试源存在缺省值断言（> 0）")
        if tst["upper_asserts"] == 0:
            infos.append("I1 上限 %s 无任何测试断言（实现夹取逻辑不被用例守卫）" % (md["max"] if md else "?"))
        else:
            passes.append("A8b 测试源有 %d 处上限相关断言" % tst["upper_asserts"])

    # ---- INFO
    if md and cli is not None:
        low = sorted({v[1] for v in cli if v[1] != md["defaults"][1]})
        if low:
            infos.append("I2 客户端显式分页值 %s 与契约缺省 %s 不同（显式传参合法，属观察项）"
                         % (low, md["defaults"][1]))
    if md and oa:
        infos.append("I3 md §0 是唯一声明缺省/上限的真源：openapi 0/%d 声明 default、0/%d 声明 maximum（客户端与测试也不同步）"
                     % (len(oa), sum(1 for x in oa if x["name"] == "pageSize")))
    infos.append("I4 本不变量不被任何测试守卫：契约测试只读 JSON Schema（query 参数不在 schema 里）、覆盖门禁只比方法+路径")
    # I5：机器可读清单（endpoints.json）侧的表达力 —— R41 未查过的第三处真源
    if os.path.exists(ep_path):
        try:
            data = json.loads(read(ep_path))
            items = data.get("endpoints", data) if isinstance(data, dict) else data
            with_q = [it for it in items if any(str(q) in ("page", "pageSize") for q in it.get("query_params", []))]
            flat = json.dumps(data, ensure_ascii=False)
            infos.append("I5 endpoints.json 有 %d 条端点声明 page/pageSize，但 query_params 只记**参数名**"
                         "（含 default/maximum 关键字：%s）→ 机器可读清单侧同样表达不了缺省值与上限"
                         % (len(with_q), "有" if ("default" in flat or "maximum" in flat) else "无"))
        except Exception:
            pass
    return fails, passes, infos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    fails, passes, infos = audit(args.root)
    print("== 分页参数缺省值与上限（取值域）不变量 ==")
    print("仓库根：%s" % args.root)
    print("断言 %d 条：PASS %d，FAIL %d；观察项 %d" % (len(passes) + len(fails), len(passes), len(fails), len(infos)))
    print()
    for p in passes:
        print("  [PASS] " + p)
    for f in fails:
        print("  [FAIL] " + f)
    print()
    print("观察项/信息项：")
    for i in infos:
        print("  [INFO] " + i)
    print()
    print("结论：%s" % ("存在漂移（逐条见上）" if fails else "逐处一致"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
