#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R67 抽查：**写路径的事务边界（多写原子性 + 事务内外部 I/O）**（第四十一类可审计不变量）。

为什么两套门禁都看不见：
  契约测试只把**响应体**与 JSON Schema 比对 ——「同一次请求里的多个写是否在同一事务内」「事务里有没有做外部 HTTP 调用」
  既不在任何 schema 里，也不体现在响应形状上（部分失败时响应仍可能是 200 + 合法 schema，或返回业务码但已落库半截数据）；
  覆盖门禁只比「方法 + 路径」；openapi 与客户端 TS 不被任何测试读取/执行。
  → 204 例全绿也查不出「两次写之间抛异常 → 第一笔已提交」。

真源：
  W = 实现写调用点（JdbcTemplate 写语句 + ORM mapper 写方法）
  T = 事务边界载体（方法级 / 类级 @Transactional）
  P = 传播语义（REQUIRES_NEW = 故意独立事务 → 豁免类，须有依据注释 + 条数上限）
  C = 调用链（方法自身非事务，但**全部调用点**都在事务方法内 → 实际处于事务中，豁免类 + 条数上限）
  I = 外部 I/O 调用点（httpClient.send / upstreamProbe.probe / newApiSyncClient.get|put）—— 落在事务边界内 = 长事务风险
  E = 控制器入口（映射注解方法）→ 调用链（深度 ≤3，**接收者类型感知**解析）累计写次数：跨方法多写且链上无事务边界 → 风险项
  A = 测试背书（原子性/回滚型断言）

用法：python spotcheck-tx-boundary-R67.py [--root E:/workspaces/hioas/hioas-aap-001] [--src <main 源码目录>]
"""
import argparse
import re
import sys
from pathlib import Path

WRITE_VERB = re.compile(r"\b(insert\s+into|update\s+\w+\s+set|delete\s+from)\b", re.I)
JDBC_WRITE = re.compile(r"\b\w*jdbc\w*\.(?:update|execute)\s*\(")
ORM_WRITE = re.compile(r"\b(\w*[Mm]apper)\s*\.\s*(insert|update|delete|insertBatch|updateById|deleteById|deleteByQuery)\w*\s*\(")
IO_CALL = re.compile(r"\b(httpClient|upstreamProbe|newApiSyncClient)\s*\.\s*(probe|send|get|put|post|exchange)\s*\(")
MAPPING_ANNOS = ("GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping")
CALL_RE = re.compile(r"(?:(?<![\w])(\w+)\s*\.\s*)?(?<![\w])(\w+)\s*\(")
FIELD_RE = re.compile(r"(?m)^[ \t]*(?:private|protected|public)\s+(?:static\s+)?(?:final\s+)?"
                      r"([\w.$]+(?:\s*<[^;=]*>)?)\s+(\w+)\s*(?:=|;)")

METHOD_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:public|protected|private|static|final|synchronized|abstract|default|native)\s+)+"
    r"([\w.$<>\[\],\s?]+?)\s+(\w+)\s*\(")


def strip_comments(src: str) -> str:
    """剥注释，**保留**字符串/字符/文本块字面量（坑 58/140）。"""
    out, i, n = [], 0, len(src)
    while i < n:
        if src[i:i + 3] == '"""':
            j = src.find('"""', i + 3)
            j = n if j < 0 else j + 3
            out.append(src[i:j])
            i = j
            continue
        c = src[i]
        if c in '"\'':
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c:
                    j += 1
                    break
                j += 1
            out.append(src[i:j])
            i = j
            continue
        if src[i:i + 2] == "//":
            j = src.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        if src[i:i + 2] == "/*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in src[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def anno_window(src: str, sig_start: int) -> str:
    """签名之前**紧邻的注解串**（行级向上走；遇非注解/非空行即停）。

    不要用「上一个 `;`/`{`/`}` 之后」的朴素切法：字符串/文本块里的花括号会让它整体错位（坑 55/63/124 族）。
    """
    lines = src[:sig_start].split("\n")
    buf, i = [], len(lines) - 1
    while i >= 0:
        t = lines[i].strip()
        if t == "":
            if buf:
                break
            i -= 1
            continue
        if t.startswith("@"):
            buf.append(t)
            while buf and buf[0].count("(") > buf[0].count(")"):
                i -= 1
                if i < 0:
                    break
                buf.insert(0, lines[i].strip())
            i -= 1
            continue
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
                    i += 2
                    continue
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
                    i += 2
                    continue
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
                    i += 2
                    continue
                if src[i] == c:
                    break
                i += 1
        elif c == ";":
            return -1, -1
        elif c == "{":
            return i, match_brace(src, i)
        i += 1
    return -1, -1


def parse_file(path: Path, base: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    src = strip_comments(raw)
    cm = re.search(r"(?m)^[ \t]*(?:public\s+|final\s+|abstract\s+)*class\s+(\w+)", src)
    cls = cm.group(1) if cm else path.stem
    class_anno, class_doc = None, ""
    if cm:
        head = src[:cm.start()]
        hits = list(re.finditer(r"@Transactional\b", head))
        if hits:
            class_anno = hits[-1].group(0)
        # 类级 javadoc 取**原始**文本（注释已被剥，依据说明写在注释里，坑 81/140）
        raw_head = raw[:raw.find(cls)] if cls in raw else ""
        class_doc = raw_head[-1500:]
    fields = {}
    for fm in FIELD_RE.finditer(src):
        typ = fm.group(1).strip()
        typ = re.sub(r"<.*", "", typ).strip()
        fields[fm.group(2)] = typ
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
        body = src[b:e + 1]
        writes, wdetail = 0, []
        for wm in JDBC_WRITE.finditer(body):
            vm = WRITE_VERB.search(body[wm.end():wm.end() + 500])
            if vm:
                writes += 1
                wdetail.append("jdbc:" + vm.group(1).split()[0].lower())
        for om in ORM_WRITE.finditer(body):
            writes += 1
            wdetail.append("orm:%s.%s" % (om.group(1), om.group(2)))
        methods.append({
            "cls": cls, "file": str(path), "name": name,
            "line": src[:b].count("\n") + 1,
            "tx": txm.group(0) if txm else None,
            "annos": re.findall(r"@(\w+)", win),
            "writes": writes, "wdetail": wdetail,
            "io": len(IO_CALL.findall(body)),
            "iocalls": [c.group(0).strip() for c in IO_CALL.finditer(body)],
            "calls": [(recv, nm) for recv, nm in CALL_RE.findall(body)],
            "body": body, "start": b, "end": e,
        })
    return {"cls": cls, "path": path, "class_anno": class_anno, "class_doc": class_doc,
            "fields": fields, "methods": methods, "src": src}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--src", default=None)
    args = ap.parse_args()
    root = Path(args.root)
    base = Path(args.src) if args.src else root / "aap-server/src/main/java"
    testdir = root / "aap-server/src/test/java"

    fails, passes, infos = [], [], []
    def fail(t): fails.append("[FAIL] " + t)
    def ok(t): passes.append("[PASS] " + t)
    def info(t): infos.append("[INFO] " + t)

    parsed = [parse_file(p, base) for p in sorted(base.rglob("*.java"))]
    allm, by_name, by_cls = [], {}, {}
    for d in parsed:
        for mm in d["methods"]:
            mm["class_anno"] = d["class_anno"]
            mm["class_doc"] = d["class_doc"]
            mm["fields"] = d["fields"]
            mm["rel"] = d["cls"]
            allm.append(mm)
            by_name.setdefault(mm["name"], []).append(mm)
            by_cls.setdefault(mm["cls"], []).append(mm)

    def resolve(recv, name, caller):
        cands = by_name.get(name, [])
        if recv:
            typ = caller["fields"].get(recv)
            if typ and typ in by_cls:
                sub = [m for m in by_cls[typ] if m["name"] == name]
                if len(sub) == 1:
                    return sub[0]
                if sub:
                    return None
                return None
            if recv == "this":
                sub = [m for m in by_cls.get(caller["cls"], []) if m["name"] == name]
                return sub[0] if len(sub) == 1 else None
            return None
        sub = [m for m in by_cls.get(caller["cls"], []) if m["name"] == name]
        if len(sub) == 1:
            return sub[0]
        if len(sub) > 1:
            return None
        return cands[0] if len(cands) == 1 else None

    for mm in allm:
        mm["callers"] = []
    resolved_pairs = 0
    for d in parsed:
        for caller in d["methods"]:
            for recv, nm in caller["calls"]:
                t = resolve(recv, nm, caller)
                if t is not None and t is not caller:
                    caller.setdefault("callees", []).append(t)
                    t["callers"].append(caller)
                    resolved_pairs += 1

    n_tx_method = sum(1 for mm in allm if mm["tx"])
    n_tx_class = sum(1 for d in parsed if d["class_anno"])
    n_writes = sum(mm["writes"] for mm in allm)
    io_methods = [mm for mm in allm if mm["io"]]
    eps = [mm for mm in allm if any(a in MAPPING_ANNOS for a in mm["annos"])]
    multi = [mm for mm in allm if mm["writes"] >= 2]

    # ---------------- A0*：正向对照 ----------------
    if parsed:
        ok("A0a 解析到 main 源码文件 %d 个" % len(parsed))
    else:
        fail("A0a 解析到 main 源码文件 0 个 → 判定不可用（坑 46/98/132）")
    if n_tx_method + n_tx_class:
        ok("A0b 解析到事务边界载体（方法级 %d ∪ 类级 %d）" % (n_tx_method, n_tx_class))
    else:
        fail("A0b 事务边界载体 0 个 → 解析器可能失效")
    if n_tx_class == 0:
        info("A0b-1 类级事务注解 0 个（本项目一律方法级声明，非解析失效）")
    if allm:
        ok("A0c 解析到方法 %d 个" % len(allm))
    else:
        fail("A0c 解析到方法 0 个 → 解析器失效")
    if n_writes:
        ok("A0d 解析到写调用点 %d 处" % n_writes)
    else:
        fail("A0d 写调用点 0 处 → 解析器失效")
    if multi:
        ok("A0e 多写（≥2 写调用）方法 %d 个" % len(multi))
    else:
        fail("A0e 多写方法 0 个 → 判定不可用")
    if eps:
        ok("A0f 解析到控制器映射方法 %d 个（清单端点 90）" % len(eps))
    else:
        fail("A0f 映射方法 0 个 → 解析器失效")
    if io_methods:
        ok("A0g 解析到外部 I/O 调用点所在方法 %d 个" % len(io_methods))
    else:
        fail("A0g 外部 I/O 调用点 0 处 → 判定不可用")
    if resolved_pairs:
        ok("A0h 调用点解析成功 %d 对（接收者类型感知；解析不出的降级为「未能静态判定」）" % resolved_pairs)
    else:
        fail("A0h 调用点解析 0 对 → 调用图失效")

    # ---------------- A1：多写方法的事务边界 ----------------
    self_tx, caller_tx, bad_tx, no_caller = [], [], [], []
    for mm in multi:
        if mm["tx"] or mm["class_anno"]:
            self_tx.append(mm)
        elif mm["callers"]:
            (caller_tx if all(c["tx"] or c["class_anno"] for c in mm["callers"]) else bad_tx).append(mm)
        else:
            no_caller.append(mm)
    if not multi:
        fail("A1 判定不可用：多写方法集合为空（坑 98/141）")
    elif not bad_tx:
        ok("A1 全部 %d 个多写方法都有事务边界证据（自身/类级 %d、调用链 %d）"
           % (len(multi), len(self_tx), len(caller_tx)))
    else:
        for mm in bad_tx:
            fail("A1 多写方法无事务边界且存在非事务调用点：%s:%d %s（写 %d 处：%s）"
                 % (mm["file"], mm["line"], mm["name"], mm["writes"], ",".join(mm["wdetail"])))
    if len(caller_tx) > 8:
        fail("A1b 调用链豁免 %d 条超上限 8 → 豁免被架空（坑 57/68）" % len(caller_tx))
    else:
        ok("A1b 调用链豁免 %d 条 ≤ 上限 8" % len(caller_tx))
    for mm in no_caller:
        info("A1c 多写方法零调用点（可能由框架/测试调用，不判 FAIL）：%s:%d %s"
             % (mm["file"], mm["line"], mm["name"]))

    # ---------------- A2：REQUIRES_NEW 豁免 ----------------
    rn = [mm for mm in allm if mm["tx"] and "REQUIRES_NEW" in mm["tx"]]
    rn_bad = [mm for mm in rn
              if not re.search(r"(失败|留痕|独立|预检|重试|回滚)", mm["body"] + mm["tx"] + mm["class_doc"])]
    if not rn:
        fail("A2 判定不可用：REQUIRES_NEW 集合为空（坑 98）")
    elif not rn_bad:
        ok("A2 %d 处 REQUIRES_NEW 独立事务均带依据说明（方法体 ∪ 类级 javadoc）" % len(rn))
    else:
        for mm in rn_bad:
            fail("A2 REQUIRES_NEW 无依据说明：%s:%d %s" % (mm["file"], mm["line"], mm["name"]))
    if len(rn) > 6:
        fail("A2b REQUIRES_NEW 条数 %d 超上限 6 → 豁免被架空（坑 57/68）" % len(rn))
    else:
        ok("A2b REQUIRES_NEW 条数 %d ≤ 上限 6" % len(rn))

    # ---------------- A3：事务边界内的外部 I/O ----------------
    io_bad = []
    for mm in io_methods:
        if mm["tx"] or mm["class_anno"]:
            io_bad.append((mm, "自身/类级事务"))
        elif mm["callers"] and all(c["tx"] or c["class_anno"] for c in mm["callers"]):
            io_bad.append((mm, "全部调用点在事务方法内"))
    if not io_methods:
        fail("A3 判定不可用：外部 I/O 调用点集合为空（坑 98）")
    elif not io_bad:
        ok("A3 全部 %d 个外部 I/O 调用点都不在事务边界内（无长事务风险）" % len(io_methods))
    else:
        for mm, why in io_bad:
            fail("A3 事务边界内做外部 I/O（长事务风险）：%s:%d %s（%s；I/O %d 处：%s）"
                 % (mm["file"], mm["line"], mm["name"], why, mm["io"], ",".join(mm["iocalls"])))

    # ---------------- A4：控制器链路上累计多写 vs 事务边界 ----------------
    chain_rows = []
    for ep in eps:
        seen, frontier, total, txany, depth = set(), [ep], 0, bool(ep["tx"] or ep["class_anno"]), 0
        while frontier and depth <= 3:
            nxt = []
            for node in frontier:
                key = (node["cls"], node["line"], node["name"])
                if key in seen:
                    continue
                seen.add(key)
                total += node["writes"]
                txany = txany or bool(node["tx"] or node["class_anno"])
                nxt.extend(node.get("callees", []))
            frontier = nxt
            depth += 1
        chain_rows.append({"ep": ep, "writes": total, "tx": txany, "nodes": len(seen)})
    multi_chain = [r for r in chain_rows if r["writes"] >= 2]
    if not chain_rows:
        fail("A4 判定不可用：控制器映射方法集合为空（坑 98）")
    elif not multi_chain:
        fail("A4 判定不可用：「链上累计多写」端点 0 个（定位率 0/%d → 调用图失效，坑 46/87）" % len(chain_rows))
    else:
        bad_chain = [r for r in multi_chain if not r["tx"]]
        info("A4c 调用链定位率：%d/%d 个端点链上累计写 ≥2（未定位的多为读路径或未解析的调用）"
             % (len(multi_chain), len(chain_rows)))
        if not bad_chain:
            ok("A4 已定位的 %d 个「链上累计多写」端点全部落在事务边界内" % len(multi_chain))
        else:
            for r in bad_chain:
                fail("A4 端点调用链上累计 %d 次写但**链上无任何事务边界**（部分失败会留半截数据）：%s.%s:%d"
                     % (r["writes"], r["ep"]["cls"], r["ep"]["name"], r["ep"]["line"]))
            ok("A4b 其余 %d 个「链上累计多写」端点落在事务边界内"
               % (len(multi_chain) - len(bad_chain)))

    # ---------------- A5：测试背书 ----------------
    tsrc = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in sorted(testdir.rglob("*.java"))) if testdir.exists() else ""
    backed = re.findall(r"(truncateAll|rollback|回滚|原子|不得留痕|isEqualTo\(0\))", tsrc)
    if not tsrc:
        fail("A5 判定不可用：测试源为空")
    elif not backed:
        fail("A5 多写路径零原子性/回滚型测试背书（%d 个多写端点）" % len(multi_chain))
    else:
        ok("A5 测试源存在原子性/回滚型断言痕迹 %d 处（结构级背书）" % len(backed))

    # ---------------- 输出 ----------------
    print("== R67 抽查：写路径事务边界（多写原子性 + 事务内外部 I/O） ==")
    print("扫描目录：%s（%d 个 .java）" % (base, len(parsed)))
    print("方法 %d 个；事务方法 %d 个（类级 %d）；写调用点 %d 处；多写方法 %d 个；控制器映射方法 %d 个；外部 I/O 方法 %d 个"
          % (len(allm), n_tx_method, n_tx_class, n_writes, len(multi), len(eps), len(io_methods)))
    print()
    print("-- 多写方法分档 --")
    print("  自身/类级事务 %d 个；调用链豁免 %d 个；零调用点 %d 个；**无边界且存在非事务调用点 %d 个**"
          % (len(self_tx), len(caller_tx), len(no_caller), len(bad_tx)))
    for mm in caller_tx:
        print("    [调用链] %s:%d %s（写 %d：%s；调用点 %d 个，全部在事务方法内）"
              % (mm["file"], mm["line"], mm["name"], mm["writes"], ",".join(mm["wdetail"]), len(mm["callers"])))
    print()
    print("-- 链上累计多写的端点（接收者类型感知解析） --")
    for r in sorted(multi_chain, key=lambda x: -x["writes"]):
        print("    %-30s %-26s L%-5d 累计写=%d 链上事务=%s 节点=%d"
              % (r["ep"]["cls"], r["ep"]["name"], r["ep"]["line"], r["writes"], r["tx"], r["nodes"]))
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
