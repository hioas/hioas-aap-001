#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R72 新增抽查：**出站 HTTP 调用的安全与韧性契约**（第四十五类可审计不变量）。

为什么两套门禁都看不见：
  契约测试只把**响应体**与 JSON Schema 比对 —— 出站调用是否做了 SSRF 守卫/超时/重试/退避/
  响应体上限/重定向限制，全都不在任何 schema 里（上游失败时响应体仍是合法错误包络）；
  覆盖门禁只比「方法 + 路径」；openapi 与客户端 TS 不被任何测试读取/执行。
  → 「重定向目标绕过 SSRF 守卫」「响应体上限在读完整个 body 之后才生效」「声明的指数退避未实现」
    「重试路径零测试背书」对全量 204 例完全不可见。

真源：E 出站入口/调用点（实现）／T 超时设置（连接级 + 请求级）／G SSRF 守卫调用点（同方法内、
  发请求之前）／R 重试（条件、上限、退避）／C 响应体上限（常量值 + **上限生效位置**）／
  D 重定向（显式次数限制 + 目标是否过守卫）／I 中断语义（InterruptedException 是否恢复标志）／
  X 失败映射错误码（ErrorCode + HTTP 状态）／P PRD 声明行（09 检测验证引擎 §安全约束/A1、11 同步）／
  K 测试背书（结构级 vs 数值级；坑 143-①）。

判据纪律：每源配 `> 0` 正向对照（坑 46/75/87/98）；「A 的每一项都要满足 B」先判「A 为空 → 判定不可用」（坑 141/154）；
  解析不到一律记「未能静态判定」并作信息项，不当漂移（坑 55/99）；只读、零写副作用。
"""
import argparse
import re
import sys
from pathlib import Path

FAILS = []
PASSES = []
INFOS = []


def fail(msg):
    FAILS.append("[FAIL ] " + msg)


def ok(msg):
    PASSES.append("[PASS] " + msg)


def info(msg):
    INFOS.append("[INFO] " + msg)


# ---------------------------------------------------------------- 词法：剥注释与字面量（保留长度与换行）

def blank(src: str) -> str:
    out = list(src)
    n = len(src)
    i = 0
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            out[i] = out[i + 1] = " "
            i += 2
            while i < n and not (src[i] == "*" and i + 1 < n and src[i + 1] == "/"):
                if src[i] != "\n":
                    out[i] = " "
                i += 1
            if i < n:
                out[i] = out[i + 1] = " "
                i += 2
            continue
        if c == '"' and src.startswith('"""', i):
            out[i] = out[i + 1] = out[i + 2] = " "
            i += 3
            while i < n and not src.startswith('"""', i):
                if src[i] != "\n":
                    out[i] = " "
                i += 1
            if i < n:
                out[i] = out[i + 1] = out[i + 2] = " "
                i += 3
            continue
        if c == '"' or c == "'":
            quote = c
            out[i] = " "
            i += 1
            while i < n:
                if src[i] == "\\":
                    out[i] = " "
                    if i + 1 < n:
                        if src[i + 1] != "\n":
                            out[i + 1] = " "
                        i += 2
                    continue
                if src[i] == quote:
                    out[i] = " "
                    i += 1
                    break
                if src[i] != "\n":
                    out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def match_brace(text: str, start: int):
    """从 text[start] == '{' 起做括号深度扫描（字符串已剥，花括号必成对）。"""
    depth = 0
    i = start
    n = len(text)
    while i < n:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


METHOD_HEAD = re.compile(
    r"^(?:@[\w.]+(?:\([^)]*\))?\s*)*(?:public|private|protected|static|final|synchronized|abstract|default|native)\b")
KEYWORD_HEAD = re.compile(r"^(?:if|for|while|switch|catch|else|do|try|finally|return|new|record|class|interface|enum)\b")
ANNO_RE = re.compile(r"@[\w.]+(?:\([^)]*\))?")


def find_methods(btext: str, src: str):
    """返回 [(cls_name?, name, line, body_text, sig)]；方法体用括号深度扫描（坑 55/63/124）。"""
    out = []
    for m in re.finditer(r"\{", btext):
        pos = m.start()
        i = pos - 1
        while i >= 0 and btext[i] not in ";{}":
            i -= 1
        sig = btext[i + 1:pos]
        if "(" not in sig or ")" not in sig:
            continue
        flat = re.sub(r"\s+", " ", ANNO_RE.sub(" ", sig)).strip()
        if not METHOD_HEAD.match(re.sub(r"\s+", " ", sig).strip()):
            continue
        if KEYWORD_HEAD.match(flat):
            continue
        nm = re.search(r"([A-Za-z_$][\w$]*)\s*\(", flat)
        if not nm:
            continue
        end = match_brace(btext, pos)
        if end < 0:
            continue
        line = btext.count("\n", 0, pos) + 1
        out.append((nm.group(1), line, src[pos + 1:end], flat))
    return out


def enclosing(methods, line):
    cands = [m for m in methods if m[1] <= line]
    if not cands:
        return None
    best = max(cands, key=lambda m: m[1])
    # 方法体行数上限：用 body 行数判断调用行是否落在体内
    body_lines = best[2].count("\n")
    if line <= best[1] + body_lines:
        return best
    return None


# ---------------------------------------------------------------- 解析

def num_value(expr: str):
    """把 `10 * 1024 * 1024` / `1024*1024` / `10` 之类常量表达式求值。"""
    e = expr.strip()
    if not re.fullmatch(r"[0-9_\s*()+\-]+", e):
        return None
    try:
        return int(eval(e.replace("_", "")))  # 仅数字与运算符，安全
    except Exception:
        return None


class Outbound:
    def __init__(self, root: Path):
        self.root = root
        self.main_files = sorted((root / "aap-server/src/main/java").rglob("*.java"))
        self.test_files = sorted((root / "aap-server/src/test/java").rglob("*.java"))
        self.prd_files = sorted((root / ".calicat/prd").glob("*.md"))
        self.main = {}
        self.tests = {}
        self.prds = {}
        for p in self.main_files:
            self.main[str(p)] = p.read_text(encoding="utf-8", errors="replace")
        for p in self.test_files:
            self.tests[str(p)] = p.read_text(encoding="utf-8", errors="replace")
        for p in self.prd_files:
            self.prds[p.name] = p.read_text(encoding="utf-8", errors="replace")
        self.err = self.main.get(str(root / "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java"), "")

    # ---- 出站入口（真正发请求的公开方法）
    def entries(self):
        """[(file, cls, name, line, body, class_text)]"""
        res = []
        for f, src in self.main.items():
            b = blank(src)
            if "httpClient.send(" not in b and ".send(request" not in b:
                continue
            methods = find_methods(b, src)
            send_names = {m[0] for m in methods if "httpClient.send(" in m[2] or ".send(request" in m[2]}
            cls = Path(f).stem
            for name, line, body, sig in methods:
                pub = sig.startswith("public")
                if not pub:
                    continue
                if "httpClient.send(" in body or any(re.search(r"\b%s\s*\(" % re.escape(s), body) for s in send_names):
                    res.append((f, cls, name, line, body, src))
        return res

    def call_sites(self):
        """出站入口的调用点 [(file, caller, line, text)]，按「接收者变量名 → 入口方法名」匹配。"""
        entries = self.entries()
        by_cls = {}
        for f, cls, name, line, body, src in entries:
            by_cls.setdefault(cls, set()).add(name)
        # 字段名 → 类型（private final Type name;）
        sites = []
        for f, src in self.main.items():
            b = blank(src)
            methods = find_methods(b, src)
            fields = {}
            for fm in re.finditer(r"(?:private|protected|public)?\s*(?:static\s+)?(?:final\s+)?([A-Za-z_$][\w$]*)\s+([A-Za-z_$][\w$]*)\s*;", b):
                fields[fm.group(2)] = fm.group(1)
            for cls, names in by_cls.items():
                # 字段名 → 类型（fields: name -> type）；接收者变量名 = 类型为该入口类的字段名
                recv_names = {k for k, v in fields.items() if v == cls}
                for name in names:
                    for rm in re.finditer(r"([A-Za-z_$][\w$]*)\s*\.\s*%s\s*\(" % re.escape(name), b):
                        recv = rm.group(1)
                        if recv not in recv_names:
                            continue
                        line = b.count("\n", 0, rm.start()) + 1
                        m = enclosing(methods, line)
                        sites.append((f, m[0] if m else "(未能静态判定)", line, rm.group(0), cls, name))
        return sites, len(by_cls)

    def prd_lines(self, pattern):
        out = []
        for name, text in self.prds.items():
            for ln in text.replace("\r\n", "\n").split("\n"):
                if re.search(pattern, ln):
                    out.append((name, ln.strip()))
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    args = ap.parse_args()
    root = Path(args.root)
    ob = Outbound(root)

    entries = ob.entries()
    sites, n_entry_cls = ob.call_sites()

    # ------------------------------------------------------------ A0 正向对照
    if not entries:
        fail("A0a 解析到出站入口方法 = 0（期望 > 0）→ 解析器失效或实现已改，判定不可用（坑 46）")
    else:
        ok("A0a 解析到出站入口方法 = %d（%s）" % (
            len(entries), ", ".join("%s.%s" % (e[1], e[2]) for e in entries)))
    if not sites:
        fail("A0b 解析到出站调用点 = 0（期望 > 0）→ 判定不可用")
    else:
        ok("A0b 解析到出站调用点 = %d" % len(sites))
    timeout_hits = sum(len(re.findall(r"\.timeout\(", blank(s))) for s in ob.main.values())
    conn_hits = sum(len(re.findall(r"connectTimeout\(", blank(s))) for s in ob.main.values())
    if timeout_hits + conn_hits == 0:
        fail("A0c 解析到超时设置点 = 0（期望 > 0）→ 判定不可用")
    else:
        ok("A0c 解析到超时设置点 = %d（请求级 %d / 连接级 %d）" % (timeout_hits + conn_hits, timeout_hits, conn_hits))
    p_redirect = ob.prd_lines(r"重定向\s*[≤<=]")
    p_body = ob.prd_lines(r"响应体\s*[≤<=]")
    p_retry = ob.prd_lines(r"重试\s*\d*\s*次|指数退避|鉴权失败不重试")
    p_ssrf = ob.prd_lines(r"SSRF|内网|环回|元数据")
    if not (p_redirect and p_body and p_retry):
        fail("A0d PRD 声明行解析数 = 0（重定向 %d / 响应体 %d / 重试 %d）→ 判定不可用（先怀疑解析器，坑 168）"
             % (len(p_redirect), len(p_body), len(p_retry)))
    else:
        ok("A0d PRD 声明行解析到：重定向 %d / 响应体上限 %d / 重试 %d / SSRF %d"
           % (len(p_redirect), len(p_body), len(p_retry), len(p_ssrf)))
    test_text = "\n".join(ob.tests.values())
    t_stub = len(re.findall(r"HttpServer", test_text))
    t_codes = len(re.findall(r"E-1101|E_1101|E-1501|E_1501", test_text))
    if t_stub == 0 or t_codes == 0:
        fail("A0e 测试背书写证据解析数 = 0（stub %d / 码断言 %d）→ 判定不可用" % (t_stub, t_codes))
    else:
        ok("A0e 测试背书解析到：HttpServer 桩 %d 处、失败码断言 %d 处" % (t_stub, t_codes))

    # ------------------------------------------------------------ A1 SSRF 守卫覆盖
    guard_re = re.compile(r"\b(?:urlGuard|outboundUrlGuard|guard)\s*\.\s*verify\s*\(")
    resolved, unguarded = 0, []
    for f, caller, line, text, callee_cls, callee_name in sites:
        b = blank(ob.main[f])
        methods = find_methods(b, ob.main[f])
        m = enclosing(methods, line)
        if m is None:
            info("A1 未能静态判定：%s:%d 调用点无法定位所属方法" % (Path(f).name, line))
            continue
        body = m[2]
        g = guard_re.search(body)
        if g and g.start() < body.find(text):
            resolved += 1
        else:
            # 入口自带守卫（**被调用方**类内部 verify 先于 send）——按接收者类型定位被调类
            ent = [e for e in entries if e[1] == callee_cls and e[2] == callee_name]
            if ent and guard_re.search(ent[0][4]):
                resolved += 1
            else:
                unguarded.append("%s:%d %s（调用者 %s）" % (Path(f).name, line, text, m[0]))
    if resolved == 0:
        fail("A1 SSRF 守卫覆盖：已定位且带守卫的出站调用点 = 0 → 判定不可用（坑 98/141）")
    elif unguarded:
        fail("A1 出站调用点未发现 SSRF 守卫证据 = %d 处：%s" % (len(unguarded), "; ".join(unguarded)))
    else:
        ok("A1 全部 %d 个出站调用点都在发请求之前有 SSRF 守卫证据（同方法内 verify 先于调用，或入口自带）" % resolved)

    # ------------------------------------------------------------ A2 超时
    no_req_timeout, no_conn = [], []
    for f, cls, name, line, body, src in entries:
        bsrc = blank(src)
        if ".timeout(" not in body:
            no_req_timeout.append("%s.%s" % (cls, name))
        if "connectTimeout(" not in bsrc:
            no_conn.append(cls)
    if no_req_timeout or no_conn:
        fail("A2 缺超时：请求级缺 %s；连接级缺 %s" % (no_req_timeout or "无", sorted(set(no_conn)) or "无"))
    else:
        ok("A2 每个出站入口都有请求级超时（.timeout）+ 其 HttpClient 有连接级超时（connectTimeout）")

    # ------------------------------------------------------------ A3 重试：上限 / 401 不重试 / 退避
    retry_entries = [e for e in entries if re.search(r"while\s*\(", e[4]) and "attempts" in e[4]]
    if not retry_entries:
        info("A3 未解析到带重试循环的出站入口（若实现已改为调度式重试属正常，需人工核对）")
    for f, cls, name, line, body, src in retry_entries:
        bounded = bool(re.search(r"attempts\s*(?:<=|<)\s*[A-Z_0-9]+", body)) or "MAX_RETRY" in body
        if not bounded:
            fail("A3 %s.%s 重试循环未发现次数上限判定（可能无界重试）" % (cls, name))
        else:
            ok("A3 %s.%s 重试有次数上限（%s）" % (cls, name, re.search(r"attempts\s*<=?\s*[A-Z_0-9]+", body).group(0)))
        auth_noretry = bool(re.search(r"status\s*==\s*401\s*\|\|\s*status\s*==\s*403", body)) and \
            body.find("401") < body.find("continue")
        if auth_noretry:
            ok("A3b %s.%s 鉴权类（401/403）在重试分支之前 return（不重试）" % (cls, name))
        else:
            fail("A3b %s.%s 未发现「401/403 不重试」的守卫（PRD 声明鉴权失败不重试）" % (cls, name))
        backoff = bool(re.search(r"Thread\.sleep|TimeUnit\.|\.plus\(|nextRetry|next_retry|schedule", body))
        if backoff:
            ok("A3c %s.%s 重试路径有退避证据" % (cls, name))
        else:
            info("A3c %s.%s 重试路径无退避证据（立即重试）——PRD 09 §检测执行声明「网络失败重试 2 次（指数退避）」，"
                 "而本项目设计文档（00-设计总览 §实现清单）对本入口只声明「5xx/网络错误 ≤2 次」"
                 "（同步路径的退避是调度式 next_retry_at，与本入口无关）→ 两份文档口径不一致 + 「指数退避」"
                 "在预检路径零实现，列**文档一致性项（待拍板）**，不判 FAIL（不把 PRD 的检测项执行声明硬套到凭证预检）"
                 % (cls, name))

    # ------------------------------------------------------------ A4 响应体上限
    cap_decls = []
    for f, src in ob.main.items():
        b = blank(src)
        for m in re.finditer(r"([A-Z_]*BODY[A-Z_]*BYTES[A-Z_]*)\s*=\s*([^;]+);", b):
            v = num_value(m.group(2))
            cap_decls.append((Path(f).stem, m.group(1), v, src))
    if not cap_decls:
        fail("A4 未解析到响应体上限常量 = 0 → 判定不可用")
    else:
        for cls, name, v, src in cap_decls:
            mb = (v / 1024 / 1024) if v else None
            if mb is None:
                info("A4 %s.%s 上限表达式无法求值（未能静态判定）" % (cls, name))
            elif mb <= 10:
                ok("A4 %s.%s = %.0f MiB ≤ 声明上限 10 MB" % (cls, name, mb))
            else:
                fail("A4 %s.%s = %.0f MiB 超出声明上限 10 MB" % (cls, name, mb))
    readers = [Path(f).stem for f, src in ob.main.items() if "BodyHandlers.ofByteArray()" in blank(src)]
    if readers:
        fail("A4b 响应体上限**在读入之后**才生效：%s 用 BodyHandlers.ofByteArray() 先全量读入内存再截断 → "
             "PRD 声明「响应体≤10MB」的防护在超大响应下不成立（应先按 Content-Length/限流流式读取）"
             % ", ".join(sorted(set(readers))))
    else:
        ok("A4b 无「先全量读入再截断」的响应体读取点")

    # ------------------------------------------------------------ A5 重定向
    redirs = [(Path(f).stem, m.group(1)) for f, src in ob.main.items()
              for m in re.finditer(r"followRedirects\(\s*HttpClient\.Redirect\.(\w+)\s*\)", blank(src))]
    limit_ok = any(re.search(r"redirect", blank(src), re.I) and re.search(r"REDIRECT\w*\s*=\s*[0-9]+", blank(src))
                   for src in ob.main.values())
    if not redirs:
        info("A5 未解析到 followRedirects 设置点（默认不跟随重定向）")
    else:
        follows = [r for r in redirs if r[1] != "NEVER"]
        if not follows:
            ok("A5 不跟随重定向（%s）→ 声明「重定向≤3」自动满足"
               % ", ".join("%s.Redirect.%s" % r for r in redirs))
        elif limit_ok:
            ok("A5 重定向次数有显式上限常量")
        else:
            fail("A5 重定向次数无显式上限：%s，PRD 声明「重定向≤3」未落地"
                 "（依赖 JDK 内部默认上限，且不可配置为 3）"
                 % ", ".join("%s.Redirect.%s" % r for r in redirs))
        if follows:
            fail("A5b 重定向目标不过 SSRF 守卫：%s 跟随重定向（%s），而 OutboundUrlGuard 只校验初始 base_url，"
                 "重定向由 JDK 客户端内部完成 → 上游可用 302 把请求引向内网/环回/元数据地址，"
                 "PRD 声明「禁内网/环回/元数据」在重定向路径上不成立"
                 % (", ".join(r[0] for r in follows), follows[0][1]))

    # ------------------------------------------------------------ A6 失败映射错误码
    codes_used = set()
    for f, src in ob.main.items():
        if Path(f).stem not in ("UpstreamProbe", "NewApiSyncClient"):
            continue
        # 两种写法都要收：ErrorCode.E_1101 与 字符串字面量 "E-1101"（本实现用后者）
        for m in re.finditer(r"ErrorCode\.(E_\d+)", src):
            codes_used.add(m.group(1))
        for m in re.finditer(r'"(E-\d{4})"', src):
            codes_used.add(m.group(1).replace("E-", "E_"))
    if not codes_used:
        fail("A6 出站失败映射码解析数 = 0 → 判定不可用")
    else:
        for c in sorted(codes_used):
            if re.search(r"\b%s\s*\(" % c, ob.err) or ('"%s"' % c.replace("E_", "E-")) in ob.err:
                ok("A6 出站失败码 %s 在 ErrorCode.java 声明（HTTP 状态由枚举构造参数给出）" % c.replace("E_", "E-"))
            else:
                fail("A6 出站失败码 %s 未在 ErrorCode.java 声明" % c.replace("E_", "E-"))

    # ------------------------------------------------------------ A7 中断语义
    for f, cls, name, line, body, src in entries:
        if "InterruptedException" not in blank(src) and "catch (Exception" not in body:
            continue
        if "catch (InterruptedException" in body:
            if "interrupt()" in body:
                ok("A7 %s.%s catch(InterruptedException) 后恢复了中断标志" % (cls, name))
            else:
                fail("A7 %s.%s catch(InterruptedException) 未恢复中断标志（Thread.currentThread().interrupt()）" % (cls, name))
        elif re.search(r"catch\s*\(\s*Exception", body) and "httpClient.send(" in body.replace("\n", ""):
            if "interrupt()" in body or "interrupt()" in blank(src):
                ok("A7 %s.%s catch(Exception) 路径也恢复了中断标志" % (cls, name))
            else:
                fail("A7 %s.%s 用 catch(Exception) 兜底且其中含 httpClient.send（可抛 InterruptedException），"
                     "但全类无 Thread.currentThread().interrupt() → 中断/优雅停机信号被吞（同类 NewApiSyncClient 已正确处理）"
                     % (cls, name))

    # ------------------------------------------------------------ A8 测试背书（结构级 / 数值级）
    retry_decl = None
    for name, ln in p_retry:
        m = re.search(r"重试\s*(\d+)\s*次", ln)
        if m:
            retry_decl = int(m.group(1))
    if t_stub > 0:
        ok("A8a 出站失败路径有进程内 stub 用例（HttpServer %d 处）" % t_stub)
    else:
        fail("A8a 出站失败路径零 stub 用例")
    if re.search(r"upstreamCalls\s*\)\s*\.as\([^)]*\)\.isEqualTo\(1\)|upstreamCalls\.get\(\)\)\.as\([^)]*\)\.isEqualTo\(1\)", test_text):
        ok("A8b 「鉴权失败不重试」有**数值级**背书（断言上游调用次数 = 1）")
    else:
        fail("A8b 「鉴权失败不重试」缺数值级背书")
    stubs = sorted({int(m.group(1)) for m in re.finditer(r"startUpstream\((\d{3})\)", test_text)})
    if retry_decl is None:
        info("A8c 未能从 PRD 解析到「重试 N 次」声明（未能静态判定）")
    elif not any(s >= 500 for s in stubs):
        fail("A8c PRD 声明「网络失败重试 %d 次」，但测试桩只覆盖状态 %s —— **5xx/网络错误的重试路径零用例背书**"
             "（重试分支从未被执行，204 例全绿也看不见；坑 143-① 数值背书缺失）" % (retry_decl, stubs))
    else:
        ok("A8c 5xx 重试路径有用例覆盖（桩状态 %s）" % stubs)

    # ------------------------------------------------------------ 信息项
    hard = [(Path(f).stem, m.group(0)) for f, src in ob.main.items()
            for m in re.finditer(r"Duration\.ofSeconds\(\s*\d+\s*\)", blank(src))
            if Path(f).stem in ("UpstreamProbe", "NewApiSyncClient")]
    info("硬编码出站超时字面量（无 yml 配置项；probe 的请求超时来自 app.detection.probe-timeout-seconds，"
         "该键未在 application.yml 声明 → 已知 R54 A1b 项）：%s" % ", ".join("%s:%s" % h for h in hard))
    info("PRD 声明行：%s" % "; ".join("%s → %s" % (n, l[:60]) for n, l in (p_redirect + p_body)[:2]))
    if p_ssrf:
        info("SSRF 声明行（%d 条）：%s" % (len(p_ssrf), p_ssrf[0][1][:80]))

    # ------------------------------------------------------------ 汇总
    for ln in PASSES:
        print(ln)
    for ln in INFOS:
        print(ln)
    for ln in FAILS:
        print(ln)
    print("")
    print("断言 %d 条：PASS %d，FAIL %d；信息项 %d 条" % (len(PASSES) + len(FAILS), len(PASSES), len(FAILS), len(INFOS)))
    print("结论：%s" % ("存在出站调用契约漂移/风险点（见 FAIL）" if FAILS else "未发现出站调用契约漂移"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
