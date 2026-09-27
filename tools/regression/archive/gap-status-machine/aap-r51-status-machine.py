"""R51 抽查 v2：状态机「取值域 + 迁移守卫」跨源一致性（第二十五类可审计不变量）。

为什么两套门禁都看不见：
  - 契约测试只校验**响应体**与 JSON Schema；而 schema 里的 status enum 只约束取值域、完全不表达「谁能转到谁」；
    更关键的是：**状态写入点不是任何响应的一部分**，且部分状态类响应压根没被 `assertModel` 覆盖 →
    实现写出「契约声明域之外的状态」时，204 例全绿也看不见。
  - 覆盖门禁只比「HTTP 方法 + 路径」；openapi 与客户端 TS 不被任何测试读取/执行。

真源：
  M = md 清单 02-API接口模型清单.md：端点说明列显式声明的 `FROM→TO` 迁移 + 错误码列的状态类码
  I = 实现：① SQL 文本块/拼接串的 `set <col> = 'X'`（含 where 的 from 守卫）
                ② ORM 实体 setter（`entity.setStatus("X")`，回查实体声明得到表名 —— 坑 107 的「先回查定义」）
  E = ER 文档 01-ER数据模型.md：每张表每个 status 列的取值域（3 列/4 列表格行 + 行内两种写法）
  S = JSON Schema 模型 status 列 enum（生成器产物；单一事实源是 tools/gen-backend-models.py）
  G = 生成器的状态目录（LIST/枚举常量）—— 用于「实现写的状态是否在生成物声明域内」的裁判

用法：
  python aap-r51-status-machine.py                 # 真实仓库（只读）
  python aap-r51-status-machine.py --root <夹具根>  # 夹具（自测用）
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

COLUMNS = ["status", "detection_status", "gate_status", "compile_status",
           "before_status", "after_status", "cache_parse_status"]
SETTER_COL = {
    "setStatus": "status", "setDetectionStatus": "detection_status",
    "setGateStatus": "gate_status", "setCompileStatus": "compile_status",
    "setBeforeStatus": "before_status", "setAfterStatus": "after_status",
    "setCacheParseStatus": "cache_parse_status",
}
STATE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
NOISE = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRUE", "FALSE", "NULL"}


class Result:
    def __init__(self):
        self.pass_n = 0
        self.fail_n = 0
        self.lines = []

    def ok(self, n, m):
        self.pass_n += 1
        self.lines.append("[PASS] %s %s" % (n, m))

    def bad(self, n, m):
        self.fail_n += 1
        self.lines.append("[FAIL] %s %s" % (n, m))

    def info(self, m):
        self.lines.append("[INFO] %s" % m)


def read(p):
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read().replace("\r\n", "\n").replace("\r", "\n")


def match_paren(s, i):
    """从 s[i]（应为 '('）起做括号深度扫描，返回配对 ')' 的下标；失败返回 -1（坑 63）。"""
    if i >= len(s) or s[i] != "(":
        return -1
    d = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return i
        i += 1
    return -1


# --------------------------------------------------------------- M: md 清单
def parse_md(root):
    p = os.path.join(root, "docs/backend/02-API接口模型清单.md")
    if not os.path.exists(p):
        return [], []
    txt = read(p)
    mig, codes = [], []
    for i, ln in enumerate(txt.splitlines(), 1):
        for m in re.finditer(r"([A-Z][A-Z_]{2,})\s*→\s*([A-Z][A-Z_]{2,})", ln):
            mig.append((i, m.group(1), m.group(2)))
        cells = re.split(r"(?<!\\)\|", ln)
        if len(cells) >= 3 and re.fullmatch(r"\s*[A-Z]{2,}-[A-Z0-9]+\s*", cells[1]):
            found = sorted(set(re.findall(r"E-\d{4}", ln)))
            if found:
                codes.append((i, cells[1].strip(), found))
    return mig, codes


# --------------------------------------------------------------- E: ER 文档
INLINE_DOM = re.compile(r"`?((?:before_|after_|detection_|gate_|compile_|cache_parse_)?status)`?\s*\(([A-Z][A-Z0-9_/]+)\)")
CELL_DOM = re.compile(r"^\|\s*(\w*status\w*)\s*\|[^|]*\|(?:[^|]*\|)?\s*`?([A-Z][A-Z0-9_]*(?:/[A-Z][A-Z0-9_]*)+)`?")
HEAD = re.compile(r"^\*\*(aap_\w+)\*\*")
DDL_STATUS_DEFAULT = re.compile(r"^\s*(\w*status\w*)\s+varchar\(\d+\)([^,\n]*)", re.M | re.I)


def parse_ddl_defaults(root):
    """DDL 里 status 列的 default 值（默认值也是「实现会产出的状态」，A6 不能把它当孤儿）。"""
    p = os.path.join(root, "aap-server/src/main/resources/db/migration/V1__baseline.sql")
    if not os.path.exists(p):
        return {}
    ddl = read(p)
    out = defaultdict(dict)
    for m in re.finditer(r"create table (?:if not exists )?(\w+)\s*\((.*?)\n\);", ddl, re.S | re.I):
        table, body = m.group(1), m.group(2)
        for cm in DDL_STATUS_DEFAULT.finditer(body):
            d = re.search(r"default\s+'([^']+)'", cm.group(2), re.I)
            if d:
                out[table][cm.group(1).lower()] = d.group(1)
    return {t: dict(c) for t, c in out.items()}


def parse_er(root):
    p = os.path.join(root, "docs/backend/01-ER数据模型.md")
    if not os.path.exists(p):
        return {}
    dom = defaultdict(dict)
    cur = None
    for ln in read(p).splitlines():
        h = HEAD.match(ln.strip())
        if h:
            cur = h.group(1)
        m = CELL_DOM.match(ln.strip())
        if m and cur:
            dom[cur][m.group(1)] = set(m.group(2).split("/"))
            continue
        if cur and ("status" in ln):
            for mm in INLINE_DOM.finditer(ln):
                dom[cur][mm.group(1).lower()] = set(mm.group(2).split("/"))
    return {t: dict(c) for t, c in dom.items()}


# --------------------------------------------------------------- S: schema
def parse_schema(root):
    sd = os.path.join(root, "docs/backend/json-schema/models")
    out = {}
    if not os.path.isdir(sd):
        return out
    for fn in sorted(os.listdir(sd)):
        if not fn.endswith(".json"):
            continue
        try:
            j = json.loads(read(os.path.join(sd, fn)))
        except Exception:
            continue
        for col in COLUMNS:
            v = j.get("properties", {}).get(col)
            if isinstance(v, dict) and v.get("enum"):
                out["%s#%s" % (fn, col)] = set(x for x in v["enum"] if x)
    return out


# --------------------------------------------------------------- G: 生成器状态目录
def parse_generator(root):
    p = os.path.join(root, "tools/gen-backend-models.py")
    if not os.path.exists(p):
        return {}
    out = {}
    for m in re.finditer(r'"(\w*Status)":\s*\[([^\]]*)\]', read(p)):
        out[m.group(1)] = set(re.findall(r'"([A-Z][A-Z0-9_]*)"', m.group(2)))
    return out


# --------------------------------------------------------------- I: 实现
TEXTBLOCK = re.compile(r'"""(.*?)"""', re.S)
STRING_LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def sql_blocks(src):
    blocks = [m.group(1) for m in TEXTBLOCK.finditer(src)]
    lits = list(STRING_LIT.finditer(src))
    run = []
    for i, m in enumerate(lits):
        if run:
            gap = src[lits[i - 1].end():m.start()]
            if not re.fullmatch(r"[\s+()]*", gap):
                blocks.append("".join(run))
                run = []
        run.append(m.group(1))
    if run:
        blocks.append("".join(run))
    return blocks


def entity_tables(root):
    """实体类名 -> 表名（回查 @Table 声明，坑 107）。"""
    m = {}
    impl = os.path.join(root, "aap-server/src/main/java")
    for dirpath, _dn, fns in os.walk(impl):
        for fn in fns:
            if not fn.endswith(".java"):
                continue
            src = read(os.path.join(dirpath, fn))
            cm = re.search(r"public\s+class\s+(\w+)", src)
            tm = re.search(r"@Table\(\s*(?:value\s*=\s*)?\"(aap_\w+)\"", src)
            if cm and tm:
                m[cm.group(1)] = tm.group(1)
    return m


def parse_impl(root):
    impl = os.path.join(root, "aap-server/src/main/java")
    e2t = entity_tables(root)
    sql_writes, orm_writes, unresolved = [], [], []
    throws = defaultdict(set)
    all_lits = set()
    # 「全仓库出现」的扫描范围：实现 + 客户端 + 生成器（**不含 ER 文档**，否则 ER 自己声明的状态必然出现）
    for scope in ("aap-server/src/main/java", "aap-client/src", "tools"):
        for dirpath, _dn, fns in os.walk(os.path.join(root, scope)):
            for fn in fns:
                if not fn.endswith((".java", ".ts", ".tsx", ".py")):
                    continue
                src = read(os.path.join(dirpath, fn))
                for m in re.finditer(r'["\'`]([A-Z][A-Z0-9_]{1,})["\'`]', src):
                    if m.group(1) not in NOISE:
                        all_lits.add(m.group(1))
    for dirpath, _dn, fns in os.walk(impl):
        for fn in fns:
            if not fn.endswith(".java"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace("\\", "/")
            src = read(p)
            for m in re.finditer(r"ErrorCode\.(E_\d{4})", src):
                throws[m.group(1).replace("_", "-")].add(rel)

            # ---- SQL 写入面（每个块内自洽地关联 set 与 where，绝不跨块覆盖）
            for blk in sql_blocks(src):
                if not re.search(r"\bupdate\b", blk, re.I):
                    continue
                um = re.search(r"\bupdate\s+([a-z_][a-z0-9_]*)", blk, re.I)
                if not um:
                    continue
                table = um.group(1).lower()
                sm = re.search(r"\bset\b(.*?)\bwhere\b", blk, re.S | re.I)
                setpart = sm.group(1) if sm else blk
                wherepart = blk[sm.end():] if sm else ""
                frm, excl = set(), set()
                for cm in re.finditer(r"\b(\w*status\w*)\s*=\s*'([A-Z][A-Z0-9_]*)'", wherepart, re.I):
                    frm.add(cm.group(2))
                for cm in re.finditer(r"\b(\w*status\w*)\s+in\s*\(([^)]*)\)", wherepart, re.I):
                    frm |= set(re.findall(r"'([A-Z][A-Z0-9_]*)'", cm.group(2)))
                for cm in re.finditer(r"\b(\w*status\w*)\s*<>\s*'([A-Z][A-Z0-9_]*)'", wherepart, re.I):
                    excl.add(cm.group(2))
                for cm in re.finditer(r"\b(\w*status\w*)\s*=\s*'([A-Z][A-Z0-9_]*)'", setpart, re.I):
                    sql_writes.append(dict(table=table, col=cm.group(1).lower(), target=cm.group(2),
                                           frm=set(frm), excl=set(excl), file=rel, form="SQL"))
                for cm in re.finditer(r"\b(\w*status\w*)\s*=\s*\?", setpart, re.I):
                    sql_writes.append(dict(table=table, col=cm.group(1).lower(), target=None,
                                           frm=set(frm), excl=set(excl), file=rel, form="SQL-参数化"))

            # ---- ORM setter 写入面（回查接收者声明类型 → @Table）
            for m in re.finditer(r"(\w+)\.(%s)\s*\(" % "|".join(SETTER_COL), src):
                var, setter = m.group(1), m.group(2)
                op = src.index("(", m.end() - 1)
                cp = match_paren(src, op)
                if cp < 0:
                    unresolved.append((rel, setter, var, "括号未配对"))
                    continue
                argspan = src[op:cp + 1]
                # 剥掉 switch 的 case 标签（`case "PASS" ->` 是匹配标签，不是写入值 —— 坑 64 同族）
                argspan = re.sub(r'\bcase\s*"[^"]*"\s*->', "case ->", argspan)
                vals = set(re.findall(r'"([A-Z][A-Z0-9_]{1,})"', argspan)) - NOISE
                tm = re.search(r"(?:(\w+)\s+)?\b%s\b\s*[=;]" % re.escape(var), src)
                cls = None
                if tm and tm.group(1):
                    cls = tm.group(1)
                if cls is None:
                    nm = re.search(r"\b%s\s*=\s*new\s+(\w+)\s*\(" % re.escape(var), src)
                    if nm:
                        cls = nm.group(1)
                table = e2t.get(cls) if cls else None
                col = SETTER_COL[setter]
                if not vals:
                    unresolved.append((rel, setter, var, "实参非字面量"))
                    continue
                if table is None:
                    unresolved.append((rel, setter, var, "接收者类型未能解析(cls=%s)" % cls))
                    continue
                orm_writes.append(dict(table=table, col=col, target=sorted(vals), file=rel,
                                       form="ORM", cls=cls))
    return sql_writes, orm_writes, unresolved, throws, all_lits


# --------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"E:/workspaces/hioas/hioas-aap-001")
    args = ap.parse_args()
    root = args.root
    r = Result()
    r.lines.append("== R51 抽查：状态机「取值域 + 迁移守卫」跨源一致性（第二十五类可审计不变量） ==")
    r.lines.append("真源：M=md 清单迁移声明/状态码 ⇔ I=实现状态写入点（SQL set + ORM setter，回查 @Table）")
    r.lines.append("      ⇔ E=ER 文档 status 取值域 ⇔ S=JSON Schema status enum ⇔ G=生成器状态目录")
    r.lines.append("")

    mig, codes = parse_md(root)
    er = parse_er(root)
    sc = parse_schema(root)
    gen = parse_generator(root)
    sql_w, orm_w, unresolved, throws, all_lits = parse_impl(root)

    r.lines.append("== 解析结果（每个源都必须 > 0，否则判解析器失效） ==")
    r.lines.append("M  md 显式迁移声明 = %d 条；端点错误码行 = %d 条" % (len(mig), len(codes)))
    r.lines.append("E  ER 取值域 = %d 张表 / %d 个 status 列" % (len(er), sum(len(v) for v in er.values())))
    r.lines.append("S  schema status enum = %d 处" % len(sc))
    r.lines.append("G  生成器状态目录 = %d 个（%s）" % (len(gen), ", ".join(sorted(gen))))
    r.lines.append("I  SQL 状态写入点 = %d（其中字面量 %d / 参数化 %d）"
                   % (len(sql_w), sum(1 for w in sql_w if w["target"]), sum(1 for w in sql_w if not w["target"])))
    r.lines.append("I  ORM setter 写入点 = %d（涉及 %d 张表）"
                   % (len(orm_w), len(set(w["table"] for w in orm_w))))
    r.lines.append("I  未能静态判定的写入点 = %d" % len(unresolved))
    r.lines.append("I  全仓库状态字面量 = %d 个" % len(all_lits))
    r.lines.append("")

    for tag, n in (("A0a", len(mig)), ("A0b", len(sql_w) + len(orm_w)), ("A0c", sum(len(v) for v in er.values())),
                   ("A0d", len(sc)), ("A0e", len(gen))):
        (r.ok if n > 0 else r.bad)(tag, "正向对照：解析到 %d 条（要求 > 0）" % n)

    def er_dom(table, col):
        cols = er.get(table)
        if not cols:
            return None
        if col in cols:
            return cols[col]
        return None

    # ---- A1：实现写入的状态必须落在「该表该列」的声明取值域内（SQL + ORM 两条写入面）
    sites = []
    for w in sql_w:
        if w["target"]:
            sites.append((w["file"], w["table"], w["col"], [w["target"]], w["form"]))
    for w in orm_w:
        sites.append((w["file"], w["table"], w["col"], w["target"], w["form"]))
    judged = 0
    for (f, t, col, tgt, form) in sites:
        dom = er_dom(t, col)
        if dom is None:
            r.info("A1 未能静态判定（ER 无 %s.%s 取值域）：%s target=%s" % (t, col, f, tgt))
            continue
        judged += 1
        over = sorted(s for s in tgt if s not in dom)
        if over:
            r.bad("A1", "实现写入状态越出 ER 声明取值域：%s %s.%s 写入=%s 越界=%s（ER=%s）[%s]"
                  % (f, t, col, tgt, over, sorted(dom), form))
        else:
            r.ok("A1", "写入状态在声明域内：%s %s.%s = %s" % (f, t, col, tgt))
    (r.ok if judged > 0 else r.bad)("A1g", "A1 判定覆盖率 %d/%d（> 0，否则断言被架空）" % (judged, len(sites)))

    # ---- A1b：实现写入的状态必须落在「最匹配的生成器状态目录」内（契约声明域；按最大重合选目录，避免错配）
    written_by_tc = defaultdict(set)
    for w in orm_w:
        written_by_tc[(w["table"], w["col"])] |= set(w["target"])
    for w in sql_w:
        if w["target"]:
            written_by_tc[(w["table"], w["col"])].add(w["target"])
    ab_judged = 0
    ab_skipped = []
    for (t, col), written in sorted(written_by_tc.items()):
        best, ov = None, 0
        for k, en in gen.items():
            n = len(written & en)
            if n > ov:
                best, ov = k, n
        # 要求「几乎完全覆盖」：最多允许 1 个越界值，且至少重合 2 个 —— 否则「最匹配目录」只是别族枚举（错配→假发现）
        if best is None or ov < 2 or ov < len(written) - 1:
            ab_skipped.append((t, col, sorted(written), best))
            continue
        ab_judged += 1
        over = sorted(written - gen[best])
        if over:
            r.bad("A1b", "实现写入的状态不在生成器声明域内：%s.%s 写入=%s 越界=%s（最匹配目录 %s=%s）"
                  % (t, col, sorted(written), over, best, sorted(gen[best])))
        else:
            r.ok("A1b", "生成器域覆盖：%s.%s 写入=%s ⊆ %s" % (t, col, sorted(written), best))
    (r.ok if ab_judged > 0 else r.bad)("A1bg", "A1b 判定条数 = %d（> 0，否则断言被架空）" % ab_judged)
    for (t, col, written, best) in ab_skipped:
        r.info("A1b 未能静态判定（无对应生成器状态目录，最匹配=%s）：%s.%s 写入=%s" % (best, t, col, written))

    # ---- A2：SQL 条件 UPDATE 的 from 守卫必须落在声明域内
    gfrm = 0
    for w in sql_w:
        if not (w["frm"] or w["excl"]):
            continue
        dom = er_dom(w["table"], w["col"])
        if dom is None:
            continue
        gfrm += 1
        over = sorted(s for s in w["frm"] if s not in dom)
        if over:
            r.bad("A2", "from 守卫越出声明域：%s %s.%s from=%s 越界=%s"
                  % (w["file"], w["table"], w["col"], sorted(w["frm"]), over))
        else:
            r.ok("A2", "from 守卫在声明域内：%s %s.%s from=%s" % (w["file"], w["table"], w["col"], sorted(w["frm"])))
    (r.ok if gfrm > 0 else r.bad)("A2g", "A2 判定条数 = %d（> 0）" % gfrm)

    # ---- A3：md 显式 FROM→TO 迁移必须在实现里有对应写入 + from 约束
    found = 0
    for (ln, frm, to) in mig:
        guard = [w for w in sql_w if w["target"] == to and (frm in w["frm"] or frm in w["excl"])]
        plain = [w for w in sql_w if w["target"] == to] + [w for w in orm_w if to in w["target"]]
        if guard:
            found += 1
            r.ok("A3", "md L%d %s→%s 有条件守卫（%s %s）" % (ln, frm, to, guard[0]["file"], guard[0]["table"]))
        elif plain:
            r.bad("A3", "md L%d %s→%s 缺 from 守卫：实现写 %s 但无 %s 约束（%s %s）"
                  % (ln, frm, to, to, frm, plain[0]["file"], plain[0]["table"]))
        else:
            r.bad("A3", "md L%d %s→%s 在实现里无任何写入点（目标状态 %s 零处）" % (ln, frm, to, to))
    # A3g 不得在「md 无迁移声明」时空转判绿（坑 98）
    (r.ok if (mig and found == len(mig)) else r.bad)("A3g", "md 迁移声明定位率 %d/%d（要求全部定位且 > 0）" % (found, len(mig)))

    # ---- A4：md 声明的状态类码必须在实现里有抛点
    STATUS_CODES = {"E-1102", "E-1303", "E-1305", "E-1407", "E-1601", "E-1701"}
    declared = set()
    for (_l, _e, cs) in codes:
        declared |= (set(cs) & STATUS_CODES)
    (r.ok if declared else r.bad)("A4g", "md 声明的状态类码 = %s" % sorted(declared))
    for c in sorted(declared):
        (r.ok if c in throws else r.bad)("A4", "%s %s" % (c, "有实现抛点（%d 文件）" % len(throws[c]) if c in throws
                                                          else "md 有声明但实现零处抛出（孤儿码）"))

    # ---- A5：SQL 状态写入无 from 守卫（仅对 md 声明过迁移的表判 FAIL，其余信息项）
    machine_tables = set()
    for (_l, _f, to) in mig:
        for w in sql_w + orm_w:
            if w["target"] == to or to in (w["target"] or []):
                machine_tables.add(w["table"])
    unguarded = [w for w in sql_w if w["form"] == "SQL" and not (w["frm"] or w["excl"])]
    hard = [w for w in unguarded if w["table"] in machine_tables]
    for w in hard:
        r.bad("A5", "状态机表出现无条件状态写：%s %s.%s=%s（md 已声明该表迁移，必须有 from 守卫）"
              % (w["file"], w["table"], w["col"], w["target"]))
    soft = [w for w in unguarded if w["table"] not in machine_tables]
    for w in soft:
        r.info("A5 非用户驱动状态机的无条件写（信息项，需人工确认）：%s %s.%s=%s"
               % (w["file"], w["table"], w["col"], w["target"]))
    (r.ok if not hard else r.bad)("A5g", "状态机表无条件写 = %d 条（要求 0）；信息项 = %d 条" % (len(hard), len(soft)))

    # ---- A6：孤儿状态（ER 声明、全仓库零出现 = 真孤儿；DDL 默认值/出现但未定位 = 信息项）
    ddl_def = parse_ddl_defaults(root)
    # 表在实现里是否有任何引用（用于区分「真孤儿状态」与「整表未接线」）
    impl = os.path.join(root, "aap-server/src/main/java")
    impl_txt = ""
    for dirpath, _dn, fns in os.walk(impl):
        for fn in fns:
            if fn.endswith(".java"):
                impl_txt += read(os.path.join(dirpath, fn))
    true_orphan, unwritten, unwired = [], [], []
    for t, cols in sorted(er.items()):
        if t not in impl_txt:
            for col, dom in sorted(cols.items()):
                unwired.append((t, col, sorted(dom)))
            continue
        for col, dom in sorted(cols.items()):
            written = set()
            for w in orm_w:
                if w["table"] == t and w["col"] == col:
                    written |= set(w["target"])
            for w in sql_w:
                if w["table"] == t and w["col"] == col and w["target"]:
                    written.add(w["target"])
            default = ddl_def.get(t, {}).get(col)
            for s in sorted(dom):
                if s in written or s == default:
                    continue
                if s in all_lits:
                    unwritten.append((t, col, s))
                else:
                    true_orphan.append((t, col, s))
    for (t, col, dom) in unwired:
        r.info("A6 整表未接线（ER 声明 %s.%s，实现零引用；DDL 已建表）：域=%s" % (t, col, dom))
    for (t, col, s) in true_orphan:
        r.bad("A6", "真孤儿状态：ER 声明 %s.%s 含 %s，全仓库零出现且非 DDL 默认值" % (t, col, s))
    for (t, col, s) in unwritten:
        r.info("A6 ER 声明 %s.%s 的 %s 未在已定位写入面出现（可能是比较/过滤用法或未静态判定）" % (t, col, s))
    r.info("A6 汇总：真孤儿 = %d，未定位写入 = %d，整表未接线 = %d" % (len(true_orphan), len(unwritten), len(unwired)))

    # ---- A7：schema enum ↔ ER 声明域（逐列）
    exact = sub = 0
    for key, enum in sorted(sc.items()):
        fn, col = key.split("#")
        cands = [(t, cols[col]) for t, cols in er.items() if col in cols and cols[col] == enum]
        if cands:
            exact += 1
            r.ok("A7", "schema %s 的 %s enum 与 ER %s 逐值一致（%d 值）" % (fn, col, cands[0][0], len(enum)))
            continue
        supers = [(t, cols[col]) for t, cols in er.items() if col in cols and enum < cols[col]]
        if supers:
            sub += 1
            t, dom = supers[0]
            r.bad("A7", "schema %s 的 %s enum 比 ER %s 少声明：缺 %s（客户端类型/运行时校验会判为非法值）"
                  % (fn, col, t, sorted(dom - enum)))
        else:
            r.info("A7 schema %s 的 %s enum 与任何 ER 取值域都无子集关系（模型可能是跨表视图，未能静态判定）" % (fn, col))
    (r.ok if (exact + sub) > 0 else r.bad)("A7g", "A7 判定条数 = %d（> 0）" % (exact + sub))

    # ---- A8：未能静态判定必须受上限约束（否则规则被架空，坑 57/68）
    r.info("A8 未能静态判定的 ORM 写入点 = %d 条" % len(unresolved))
    for (f, s, v, why) in unresolved:
        r.info("   %s %s.%s(%s)" % (f, v, s, why))
    (r.ok if len(unresolved) <= 30 else r.bad)("A8g", "未能静态判定条数 %d ≤ 上限 30" % len(unresolved))

    print("\n".join(r.lines))
    print("")
    print("汇总：PASS %d / FAIL %d" % (r.pass_n, r.fail_n))
    return 1 if r.fail_n else 0


if __name__ == "__main__":
    sys.exit(main())
