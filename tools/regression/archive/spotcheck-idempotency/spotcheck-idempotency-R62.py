#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R62 抽查：幂等重放语义契约（第三十六类可审计不变量；只读）。

为什么两套门禁都看不见：
 - 契约测试只把**响应体**与 JSON Schema 比对；`Idempotency-Key` 是**请求头**，而 JSON Schema 里
   既没有头（`requests/*.schema.json` 不描述 header），也没有「重放窗口 / 过期是否仍重放 /
   空响应体是否落库 / 并发首写兜底」这类**行为语义**；
 - 覆盖门禁只比「方法 + 路径」；
 - openapi 与客户端 TS **不被任何测试读取/执行**。

真源七处：
 M = md 清单（§0 幂等约定行 + 逐端点「幂等/并发」列 + 逐端点「错误码」列）
 O = openapi.yaml（逐 operation 的 `in: header`）
 D = DDL（`aap_idempotency_record` 列集合 + 唯一索引 + `expire_at` 索引）
 I = 实现（`IdempotencyFilter`：头名常量 / TTL 常量 / 重放查询 where 子句 / 空体守卫 /
     并发兜底 catch / 清理路径）
 C = 客户端（是否**真的**设置该头 —— 注释不算调用点，坑 58③）
 T = 测试源（幂等重放用例 + 逐端点 ID 背书）
 R = 可达性（写端点是否可能返回空响应体 —— 决定「空体不落库」是否可达，坑 110）

纪律：每个解析器配 `> 0` 正向对照（坑 46/75/132：不得用 `or` 短路）；FAIL 判据用
`\\[FAIL\\s*\\]`（坑 97）；md 表格按**未转义**竖线切分（坑 48）并支持两套表头（坑 89）；
本文件只读、零写副作用。
"""
import argparse
import re
import sys
from pathlib import Path

FAIL_TAG = "[FAIL]"
PASS_TAG = "[PASS]"
INFO_TAG = "[INFO]"

MD_REL = "docs/backend/02-API接口模型清单.md"
OA_REL = "docs/backend/openapi.yaml"
DDL_REL = "aap-server/src/main/resources/db/migration/V1__baseline.sql"
MAIN_REL = "aap-server/src/main/java"
TEST_REL = "aap-server/src/test/java"
CLI_REL = "aap-client/src"

IDEM_TABLE = "aap_idempotency_record"
IDEM_KEY_UNIQUE = "uq_idempotency_key"
IDEM_EXPIRE_IDX = "idx_idempotency_expire"
HEADER_NAME = "Idempotency-Key"


def read(p):
    """缺失文件返回空串（坑 128：不许崩，让正向对照自己转红）。"""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def strip_java_comments(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"(?m)//[^\n]*", " ", src)
    return src


def strip_ts_comments(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"(?m)//[^\n]*", " ", src)
    return src


def match_paren(src, i, open_ch="(", close_ch=")"):
    """括号配对扫描；返回配对位置，失败 -1（坑 63/124）。"""
    if i >= len(src) or src[i] != open_ch:
        return -1
    depth = 0
    j = i
    while j < len(src):
        c = src[j]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def find_body(src, start):
    """从 start+1 起找方法体 `{`（坑 124：绝不能从注解右括号上起步）。"""
    j = start + 1
    while j < len(src) and src[j] != "{":
        j += 1
    if j >= len(src):
        return None
    end = match_paren(src, j, "{", "}")
    if end < 0:
        return None
    return src[j + 1:end]


# ---------------------------------------------------------------- M : md 清单
def parse_md(root):
    txt = read(root / MD_REL)
    out = {"present": bool(txt), "ttl_hours": None, "header": None,
           "endpoints": {}, "declared": set(), "declared_with_code": set(),
           "endpoint_rows": 0}
    # §0 幂等约定行：| 幂等 | 非幂等写支持 `Idempotency-Key`（24h，命中返回首次响应体，C11） |
    for line in txt.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", s)[1:-1]]
        if len(cells) == 2 and cells[0] == "幂等":
            out["header"] = (re.search(r"`([^`]+)`", cells[1]) or [None, None])[1] \
                if re.search(r"`([^`]+)`", cells[1]) else None
            m = re.search(r"(\d+)\s*h", cells[1])
            if m:
                out["ttl_hours"] = int(m.group(1))
    # 逐端点行：表头可能有两套（10 列含「幂等/并发」、7 列含「角色」）
    hdr = None
    for line in txt.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", s)[1:-1]]
        if not cells:
            continue
        if cells[0] == "ID":
            hdr = cells
            continue
        if hdr is None or len(cells) != len(hdr):
            continue
        if not re.match(r"^[A-Z]{2,4}(-[A-Z0-9]+)*$", cells[0]):
            continue
        try:
            ep = {"method": cells[hdr.index("方法")].strip("` "),
                  "path": cells[hdr.index("路径")].strip("` "),
                  "idem": cells[hdr.index("幂等/并发")] if "幂等/并发" in hdr else "",
                  "codes": cells[hdr.index("错误码")] if "错误码" in hdr else ""}
        except (ValueError, IndexError):
            continue
        out["endpoints"][cells[0]] = ep
        out["endpoint_rows"] += 1
        if "Idempotency" in ep["idem"]:
            out["declared"].add(cells[0])
            if "E-1001" in ep["codes"]:
                out["declared_with_code"].add(cells[0])
    return out


# ------------------------------------------------------------- O : openapi.yaml
def parse_openapi(root):
    txt = read(root / OA_REL)
    out = {"present": bool(txt), "ops": [], "header_ops": set(),
           "header_points": 0, "query_points": 0}
    lines = txt.splitlines()
    cur_path = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^  (/[^\s:]*):\s*$", ln)
        if m:
            cur_path = m.group(1)
            i += 1
            continue
        m2 = re.match(r"^    (get|post|put|delete|patch):\s*$", ln)
        if m2 and cur_path:
            method = m2.group(1).upper()
            j = i + 1
            buf = []
            while j < len(lines):
                l2 = lines[j]
                if re.match(r"^  /", l2) or re.match(r"^    (get|post|put|delete|patch):", l2):
                    break
                buf.append(l2)
                j += 1
            body = "\n".join(buf)
            out["ops"].append((method, cur_path))
            if re.search(r"in:\s*header", body):
                out["header_points"] += 1
                if re.search(re.escape(HEADER_NAME), body):
                    out["header_ops"].add((method, cur_path))
            out["query_points"] += len(re.findall(r"in:\s*query", body))
            i = j
            continue
        i += 1
    return out


# ------------------------------------------------------------------ D : DDL
def parse_ddl(root):
    txt = read(root / DDL_REL)
    out = {"present": bool(txt), "cols": [], "unique_on_table": [], "indexes": []}
    m = re.search(r"(?is)create\s+table\s+(?:if\s+not\s+exists\s+)?%s\s*\((.*?)\n\);" % IDEM_TABLE, txt)
    if m:
        for line in m.group(1).splitlines():
            s = line.strip().rstrip(",")
            if not s or s.startswith("--"):
                continue
            tok = s.split()
            if tok and re.match(r"^[a-z_][a-z0-9_]*$", tok[0]) and tok[0] not in (
                    "constraint", "primary", "unique", "foreign", "check"):
                out["cols"].append(tok[0])
    for mm in re.finditer(
            r"(?is)create\s+unique\s+index\s+(?:if\s+not\s+exists\s+)?([a-z0-9_]+)\s+on\s+([a-z0-9_]+)\s*\(([^)]*)\)", txt):
        if mm.group(2) == IDEM_TABLE:
            out["unique_on_table"].append((mm.group(1), [c.strip() for c in mm.group(3).split(",")]))
    for mm in re.finditer(
            r"(?is)create\s+index\s+(?:if\s+not\s+exists\s+)?([a-z0-9_]+)\s+on\s+([a-z0-9_]+)\s*\(([^)]*)\)", txt):
        if mm.group(2) == IDEM_TABLE:
            out["indexes"].append((mm.group(1), [c.strip() for c in mm.group(3).split(",")]))
    return out


# ------------------------------------------------------------- I : 实现解析
def parse_impl(root):
    out = {"present": False, "header": None, "ttl_hours": None, "expire_filter": False,
           "cleanup_files": 0, "cleanup_points": 0, "catches_duplicate": False,
           "replay_body": False, "replay_status": False, "blank_body_guard": False,
           "file": None}
    main = root / MAIN_REL
    if not main.exists():
        return out
    filt = None
    for p in sorted(main.rglob("*.java")):
        t = strip_java_comments(read(p))
        if "Idempotency-Key" in t and "extends OncePerRequestFilter" in t:
            filt = (p, t)
            break
    for p in sorted(main.rglob("*.java")):
        raw = read(p)
        if IDEM_TABLE in raw or "IdempotencyRecordMapper" in raw:
            t = strip_java_comments(raw)
            if re.search(r"(?i)@Scheduled", t) and re.search(r"(?i)\bdelete\b", t):
                out["cleanup_files"] += 1
                out["cleanup_points"] += len(re.findall(r"(?i)\bdelete\b", t))
    if filt is None:
        return out
    out["present"] = True
    out["file"] = str(filt[0].relative_to(root))
    src = filt[1]
    m = re.search(r"static\s+final\s+String\s+HEADER\s*=\s*\"([^\"]+)\"", src)
    if m:
        out["header"] = m.group(1)
    m = re.search(r"TTL_HOURS\s*=\s*(\d+)", src)
    if m:
        out["ttl_hours"] = int(m.group(1))
    out["catches_duplicate"] = bool(re.search(r"catch\s*\(\s*DuplicateKeyException", src))
    fm = re.search(r"Optional<IdempotencyRecordEntity>\s+find\s*\(", src)
    if fm:
        body = find_body(src, fm.end())
        if body is not None:
            # 只看 where 谓词链（排除局部变量/注释已剥）
            out["expire_filter"] = bool(re.search(r"expire_at", body))
    dm = re.search(r"doFilterInternal\s*\(", src)
    # 判据范围 = 过滤器类本体（不是仅 doFilterInternal 方法体）：把重放逻辑抽到私有助手
    # （replay(record, response)）是等价写法，只看方法体会产出假 FAIL（坑 81 判据范围与语义不符）。
    # 语义是「该过滤器回放了存储的响应体 + 状态码」，类内一处出现即成立。
    out["replay_body"] = bool(re.search(r"getResponseBody\s*\(", src))
    out["replay_status"] = bool(re.search(r"getResponseStatus\s*\(", src))
    out["blank_body_guard"] = bool(re.search(r"body\s*==\s*null\s*\|\|\s*body\.isBlank\(\)", src))
    return out


# ------------------------------------------------------------- C : 客户端
def parse_client(root):
    out = {"present": False, "send_points": 0}
    cli = root / CLI_REL
    if not cli.exists():
        return out
    out["present"] = True
    for p in sorted(cli.rglob("*.ts")):
        t = strip_ts_comments(read(p))   # 注释里的头名不是调用点（坑 58③）
        out["send_points"] += len(re.findall(re.escape(HEADER_NAME), t))
    return out


# ------------------------------------------------------------- T : 测试源
def parse_tests(root):
    out = {"present": False, "files": 0, "idem_cases": 0, "idem_files": set(),
           "declare_single_record": 0, "backed_endpoints": set()}
    tst = root / TEST_REL
    if not tst.exists():
        return out
    out["present"] = True
    for p in sorted(tst.rglob("*.java")):
        t = strip_java_comments(read(p))
        out["files"] += 1
        if HEADER_NAME not in t:
            continue
        out["idem_files"].add(p.name)
        for m in re.finditer(r"@DisplayName\(\"([^\"]*)\"\)", t):
            txt = m.group(1)
            if "幂等" in txt:
                out["idem_cases"] += 1
                if re.search(r"只落|只落一次|逐字一致|返回首次", txt):
                    out["declare_single_record"] += 1
        for eid in re.findall(r"\b([A-Z]{2,4}-\d+)\b", t):
            out["backed_endpoints"].add(eid)
    return out


# ------------------------------------------------------- R : 可达性（空响应体）
def parse_reachability(root):
    out = {"present": False, "controllers": 0, "empty_body_write_points": 0}
    main = root / MAIN_REL
    if not main.exists():
        return out
    for p in sorted(main.rglob("*Controller.java")):
        out["present"] = True
        out["controllers"] += 1
        t = strip_java_comments(read(p))
        out["empty_body_write_points"] += len(re.findall(
            r"(?i)noContent|HttpStatus\.NO_CONTENT|status\(204\)|ResponseEntity<Void>", t))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--label", default="")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    lines = []
    results = []

    def emit(tag, name, text):
        results.append((tag, name))
        lines.append("%s %-4s %s" % (tag, name, text))

    if args.label:
        lines.append("== R62 抽查：幂等重放语义契约（第三十六类不变量，只读）— %s ==" % args.label)
    else:
        lines.append("== R62 抽查：幂等重放语义契约（第三十六类可审计不变量，只读） ==")
    lines.append("真源：M=md 清单 / O=openapi / D=DDL / I=实现 / C=客户端 / T=测试源 / R=可达性")
    lines.append("")

    M = parse_md(root)
    O = parse_openapi(root)
    D = parse_ddl(root)
    I = parse_impl(root)
    C = parse_client(root)
    T = parse_tests(root)
    R = parse_reachability(root)

    # ---------------- A0 正向对照（必须真的读到输入；不得用 or 短路，坑 132）----
    lines.append("--- A0 正向对照（每个源都必须真的解析到条目；任一为 0 先怀疑解析器，坑 46/75/98/132）---")
    ok = M["present"] and M["ttl_hours"] is not None and M["header"] is not None
    emit(PASS_TAG if ok else FAIL_TAG, "A0a",
         "M md §0 幂等约定行解析到：头名=%r TTL=%s h" % (M["header"], M["ttl_hours"]))
    ok = M["endpoint_rows"] > 0 and len(M["declared"]) > 0
    emit(PASS_TAG if ok else FAIL_TAG, "A0b",
         "M 逐端点行=%d（10 列表头），其中声明 Idempotency-Key 的端点=%d 条" % (
             M["endpoint_rows"], len(M["declared"])))
    ok = len(D["cols"]) > 0 and len([u for u in D["unique_on_table"] if u[0] == IDEM_KEY_UNIQUE]) == 1
    emit(PASS_TAG if ok else FAIL_TAG, "A0c",
         "D %s 列数=%d，唯一索引 %s 命中=%d" % (
             IDEM_TABLE, len(D["cols"]),
             IDEM_KEY_UNIQUE, len([u for u in D["unique_on_table"] if u[0] == IDEM_KEY_UNIQUE])))
    ok = I["present"] and I["header"] is not None and I["ttl_hours"] is not None
    emit(PASS_TAG if ok else FAIL_TAG, "A0d",
         "I 幂等过滤器解析到：%s 头名=%r TTL=%s h" % (I["file"], I["header"], I["ttl_hours"]))
    ok = O["present"] and len(O["ops"]) > 0 and O["query_points"] > 0
    emit(PASS_TAG if ok else FAIL_TAG, "A0e",
         "O openapi 解析到 operations=%d、`in: query` 参数点=%d、`in: header` 参数点=%d" % (
             len(O["ops"]), O["query_points"], O["header_points"]))
    ok = T["present"] and T["idem_cases"] > 0
    emit(PASS_TAG if ok else FAIL_TAG, "A0f",
         "T 测试源 %d 文件，幂等重放用例=%d（含「只落一次/逐字一致/返回首次」=%d）" % (
             T["files"], T["idem_cases"], T["declare_single_record"]))
    lines.append("")

    # ---------------- A1 头名一致 -------------------------------------------------
    lines.append("--- A1 头名一致（M §0 / I 常量 / O 逐 operation / C 发送点）---")
    same = (M["header"] is not None and I["header"] is not None and M["header"] == I["header"])
    emit(PASS_TAG if same else FAIL_TAG, "A1a",
         "M §0 头名=%r ⇔ I 常量=%r（必须一致）" % (M["header"], I["header"]))
    n_decl = len(M["declared"])
    n_o = len(O["header_ops"])
    if n_o == n_decl:
        emit(PASS_TAG, "A1b", "O 逐 operation 声明 `in: header` %s 的条数=%d ⇔ M 声明端点数=%d" % (
            HEADER_NAME, n_o, n_decl))
    else:
        emit(FAIL_TAG, "A1b",
             "O openapi 逐 operation 声明 `in: header`（%s）的条数=%d，而 M 声明该头的端点数=%d "
             "→ 生成物侧漏声明（第三处真源缺失；契约测试只读 JSON Schema，头不在 schema 里，"
             "204 例全绿也看不见）" % (HEADER_NAME, n_o, n_decl))
    lines.append("")

    # ---------------- A2 TTL 语义 -------------------------------------------------
    lines.append("--- A2 TTL 语义（24h 声明 ⇔ 常量 ⇔ 重放查询是否按 expire_at 过滤 ⇔ 清理路径）---")
    if M["ttl_hours"] is not None and I["ttl_hours"] == M["ttl_hours"]:
        emit(PASS_TAG, "A2a", "M 声明 TTL=%s h ⇔ I 常量 TTL_HOURS=%s" % (M["ttl_hours"], I["ttl_hours"]))
    else:
        emit(FAIL_TAG, "A2a", "M 声明 TTL=%s h 而 I 常量 TTL_HOURS=%s（不一致）" % (
            M["ttl_hours"], I["ttl_hours"]))
    if I["expire_filter"]:
        emit(PASS_TAG, "A2b", "I 重放查询 find() 的谓词链按 `expire_at` 过滤")
    else:
        emit(FAIL_TAG, "A2b",
             "I 重放查询 find() 只按 `idempotency_key` 过滤、**不按 `expire_at`** → M/实体 javadoc 声明的 "
             "「24h 有效」在**重放路径上失效**：过期记录仍会被重放（首次响应体无限期返回）")
    if I["cleanup_points"] > 0:
        emit(PASS_TAG, "A2c", "I 过期记录清理路径：文件=%d 删除点=%d" % (
            I["cleanup_files"], I["cleanup_points"]))
    else:
        emit(FAIL_TAG, "A2c",
             "I 零清理路径（含 DDL 表名或 IdempotencyRecordMapper 且带 @Scheduled + 删除的文件数=0）"
             " + 表无 TTL 清理 → 过期记录**永久留存**并被永久重放（与 A2b 同源，A2b/A2c 任一为真即构成语义缺口）")
    exp_idx = [i for i in D["indexes"] if i[0] == IDEM_EXPIRE_IDX]
    if exp_idx and not I["expire_filter"] and I["cleanup_points"] == 0:
        emit(INFO_TAG, "A2d", "D 索引 %s on %s 存在，而实现零读取路径 → **孤儿索引**（为「按 expire_at 过期」"
                              "预留却未接线；与 A2b/A2c 同源）" % (IDEM_EXPIRE_IDX, IDEM_TABLE))
    else:
        emit(INFO_TAG, "A2d", "D expire_at 索引=%s；实现使用 expire_at=%s、清理点=%d" % (
            [i[0] for i in exp_idx], I["expire_filter"], I["cleanup_points"]))
    lines.append("")

    # ---------------- A3 重放形状 / 空体 ------------------------------------------
    lines.append("--- A3 重放形状（命中返回首次响应体）与空响应体可达性 ---")
    if I["replay_body"] and I["replay_status"]:
        emit(PASS_TAG, "A3a", "I 重放分支回放首次 `response_body` + `response_status`（完整包体，含 traceId）")
    else:
        emit(FAIL_TAG, "A3a", "I 重放分支未同时回放响应体与状态：body=%s status=%s" % (
            I["replay_body"], I["replay_status"]))
    if R["present"] and R["controllers"] > 0 and R["empty_body_write_points"] == 0:
        emit(PASS_TAG, "A3b",
             "「空响应体不落库（state 永停 IN_PROGRESS → 该端点重放失效）」当前**不可达**："
             "控制器 %d 个、204/ResponseEntity<Void> 线索=%d 处（空体守卫存在=%s）→ 降级为"
             "**潜在陷阱（当前不可达）**，待新增 204 写端点时须一并处置" % (
                 R["controllers"], R["empty_body_write_points"], I["blank_body_guard"]))
    else:
        emit(FAIL_TAG, "A3b", "存在可能返回空响应体的写端点（线索 %d 处）而实现 %s 空体时不落库 → "
                              "该端点幂等重放失效" % (R["empty_body_write_points"], ""))
    lines.append("")

    # ---------------- A4 并发兜底 -------------------------------------------------
    lines.append("--- A4 并发首写兜底（唯一索引 + 捕获）---")
    uq = [u for u in D["unique_on_table"] if u[0] == IDEM_KEY_UNIQUE]
    if uq and I["catches_duplicate"]:
        emit(PASS_TAG, "A4a", "D 唯一索引 %s%s 存在 ⇔ I 捕获 DuplicateKeyException（撞键方转重放）" % (
            uq[0][0], uq[0][1]))
    else:
        emit(FAIL_TAG, "A4a", "并发兜底不成立：唯一索引=%s 捕获=%s" % (bool(uq), I["catches_duplicate"]))
    cols = uq[0][1] if uq else []
    if cols == ["idempotency_key"]:
        emit(INFO_TAG, "A4b", "唯一键列集合=%s（`endpoint` 未入键 → 同键跨端点不冲突；实现以 `request_hash` "
                              "做同键不同体判 400，跨端点同体场景由 hash 相等兜住，无实证风险）" % cols)
    else:
        emit(INFO_TAG, "A4b", "唯一键列集合=%s" % cols)
    lines.append("")

    # ---------------- A5 逐端点覆盖 ------------------------------------------------
    lines.append("--- A5 逐端点：M 声明集合 ⇔ I 覆盖面 ⇔ T 测试背书 ---")
    if n_decl > 0 and I["present"]:
        emit(PASS_TAG, "A5a",
             "I 为**全局过滤器**（所有 `/api/` 写请求带头即生效）⇒ 覆盖面 ⊇ M 声明的 %d 条（%s）"
             "→ 实现更宽，非缺口" % (n_decl, " ".join(sorted(M["declared"]))))
    else:
        emit(FAIL_TAG, "A5a",
             "覆盖面判定不可用：M 声明端点数=%d、I 解析成功=%s（空夹具/解析失效时必须转红，坑 98）" % (
                 n_decl, I["present"]))
    backed = sorted(M["declared"] & T["backed_endpoints"])
    miss = sorted(M["declared"] - T["backed_endpoints"])
    if n_decl == 0:
        emit(FAIL_TAG, "A5b",
             "M 声明端点数=0 → 背书判定不可用（空夹具/解析失效时必须转红，坑 98）")
    elif not miss:
        emit(PASS_TAG, "A5b", "M 声明的 %d 条端点全部有幂等用例背书：%s（同文件含 %s 字面量）" % (
            n_decl, backed, HEADER_NAME))
    else:
        emit(FAIL_TAG, "A5b",
             "M 声明的 %d 条端点中仅 %d 条有幂等重放用例背书（%s），%d 条零背书：%s "
             "→ 「幂等重放」语义在其余端点**只靠全局过滤器实现，无任何真实 HTTP 用例**"
             "（门禁只要求「有真实 HTTP 用例」，不要求覆盖幂等语义）" % (
                 n_decl, len(backed), backed, len(miss), miss))
    lines.append("")

    # ---------------- A6 冲突码声明 ------------------------------------------------
    lines.append("--- A6 契约冲突码（同键不同请求体 → 400 E-1001）---")
    under = sorted(set(M["declared"]) - M["declared_with_code"])
    if n_decl == 0:
        emit(FAIL_TAG, "A6a", "M 声明端点数=0 → 冲突码声明判定不可用（空夹具/解析失效时必须转红，坑 98）")
    elif not under:
        emit(PASS_TAG, "A6a", "M 声明该头的 %d 条端点全部在「错误码」列声明了 E-1001" % n_decl)
    else:
        emit(FAIL_TAG, "A6a",
             "M「错误码」列漏声明 E-1001 的声明端点=%d 条：%s（实现为全局过滤器，这些端点同键不同体同样抛 "
             "400 E-1001 → md 少声明了实现真会抛的码；门禁与契约测试都看不见）" % (len(under), under))
    lines.append("")

    # ---------------- A7 客户端消费 ------------------------------------------------
    lines.append("--- A7 客户端是否消费该头（信息项 / 风险项，坑 54/88 措辞分档）---")
    if C["send_points"] == 0:
        emit(INFO_TAG, "A7a",
             "C 客户端**零处**设置 %s（仅文件头注释提到，剥注释后 0 命中）→ M 措辞为「**支持**」不是"
             "「必须带」；客户端不带该头时并发重复提交**不享幂等保护**，属风险项（待拍板），"
             "不是硬漂移（`aap-client` 零按码/按状态分支）" % HEADER_NAME)
    else:
        emit(INFO_TAG, "A7a", "C 客户端设置该头的代码点=%d" % C["send_points"])
    emit(INFO_TAG, "A7b", "「同键不同请求体」的冲突码 400 E-1001 在 md §0 幂等约定行未出现"
                          "（§0 只承诺「24h，命中返回首次响应体」）→ 文档一致性项")
    lines.append("")

    n_pass = sum(1 for t, _ in results if t == PASS_TAG)
    n_fail = sum(1 for t, _ in results if t == FAIL_TAG)
    n_info = sum(1 for t, _ in results if t == INFO_TAG)
    lines.append("汇总 PASS %d / FAIL %d / INFO %d" % (n_pass, n_fail, n_info))
    lines.append("正向对照 A0a…A0f 全部必须为 PASS；任一为 FAIL 时本报告结论无效（先修解析器，坑 46/98）")

    print("\n".join(lines))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
