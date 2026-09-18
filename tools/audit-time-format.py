#!/usr/bin/env python3
"""时间字段序列化格式一致性审计（R33，只读）。

不变量：**响应里的每一个时间字段都必须经同一个格式化出口输出为 RFC3339 秒精度 UTC 字符串**
（`yyyy-MM-dd'T'HH:mm:ss'Z'`）。与既有审计同族，换第六类契约不变量：**格式 / 取值路径**（不是名字、不是路由、不是错误码）。

  简称  来源                                                  承载方式
  ----  ----------------------------------------------------  --------------------------------------------------
  S     docs/backend/json-schema/**/*.schema.json            `format: date-time` 字段的 `type` 必须是 string
  I     aap-server/src/main/java/**/*.java                   时间列的取值路径是否被统一出口包裹
  V     aap-server/src/main/java/**/*Views.java              响应 DTO 的时间字段声明类型必须是 String
  C     aap-client/src/**/*.ts                               时间字段声明类型必须是 string（不得 number）
  T     aap-server/src/test/java/**/*.java                   既有用例对时间格式的断言（信息项）

为什么需要它（skill 坑 1 / 43 / 44 / 60 族）：
  * 契约测试只校验 **JSON Schema**，而 schema 只写 `format: date-time` —— 秒精度 `...:ssZ`、
    毫秒 `...:ss.SSSZ`、偏移 `...+08:00`、pgjdbc 文本形态 `2026-09-18 15:17:23.123456+08`
    **全部都能过校验**；`format` 甚至不是必须强校验的关键字 → 204 例全绿也看不见格式漂移。
  * 覆盖门禁只比「方法 + 路径」注册表；路由/查询参数/错误码/鉴权/键名五套审计都不看**字段值的格式**。
  * 后果（坑 1 的同类）：客户端 `new Date(value)` 对「无偏移的本地时间文本」按**本地时区**解析，
    同一时刻会差一个时区（8 小时）；对 pgjdbc 的 `2026-09-18 15:17:23.123456+08` 直接得到 `Invalid Date`。

为什么把它当**契约不变量**：`docs/backend/json-schema/models/*.schema.json` 里每个时间字段的
`description` 都写着「RFC3339 UTC」，md 清单 §0 也把时间口径写死 —— 这就是冻结契约的一部分，
而它只由**实现自觉**维持（9 处 `rfc3339` 副本 + 1 处等价内联写法），任何一处写歪都不会有门禁变红。

判定（每分支都有正向对照，skill 坑 46）：
  A0  出口定义唯一：所有 `DateTimeFormatter.ofPattern("…")` 格式串去重后必须**只有 1 种**且等于秒精度 UTC；
      所有 `static String <fn>(OffsetDateTime …)` 辅助方法体（归一化形参名后）去重后必须**只有 1 种**。
  A1  取值路径包裹：每个把时间列读进响应的语句必须被 `rfc3339(...)` / `RFC3339.format(...)` 包裹；
      「先取到局部变量、再在别处包裹」的形式按**同文件变量引用**判定（避免假发现）。
  A2  文本直出：`rs.getString("<x>_at")` 出现在响应映射里 → FAIL（pgjdbc 文本形态不是 RFC3339）。
  A3  响应 DTO：`*Views.java` 里时间字段的声明类型必须是 `String`（`OffsetDateTime` 会被 Jackson 直出，
      与出口的秒精度形态不一致）。
  A4  客户端：`*_at` / `*At` 字段声明类型必须含 `string` 且不含 `number`（坑 1：ID/时间这类跨页面通用字段以客户端为准）。
  A5  schema 侧：`format: date-time` 字段的 `type` 必须是 string（不得 number/integer）。
  A6  信息项：两种等价写法并存（helper vs 内联 `RFC3339.format(...withOffsetSameInstant(UTC))`）与
      用例中的时间格式断言数 —— 说明「门禁为何看不见」与「未来漂移高发地」（坑 44）。

只读保证：脚本不写任何文件；收尾用 `(mtime_ns, size, md5)` 指纹自检全部被读文件未被改动（坑 39）。

用法：
  python tools/audit-time-format.py [--root <dir>] [--all]
  （--root 供负向自测指向仓库外的夹具目录，skill 坑 34）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SERVER_DIR = "aap-server/src/main/java/com/hioas/aap"
SCHEMA_DIR = "docs/backend/json-schema"
CLIENT_DIR = "aap-client/src"
TEST_DIR = "aap-server/src/test/java"

EXPECT_PATTERN = "yyyy-MM-dd'T'HH:mm:ss'Z'"

PATTERN_DEF_RE = re.compile(
    r'static\s+final\s+DateTimeFormatter\s+(\w+)\s*=\s*DateTimeFormatter\.ofPattern\("([^"]*)"\)')
HELPER_DEF_RE = re.compile(
    r'static\s+String\s+(\w+)\s*\(\s*OffsetDateTime\s+(\w+)\s*\)\s*\{(.*?)\n\s{4}\}', re.S)
WRAP_RE = re.compile(r'\b(?:rfc3339|RFC3339\.format)\s*\(')
TIME_READ_RE = re.compile(r'\.(?:getObject|getTimestamp)\(\s*"([a-z0-9_]*_at)"')
TIME_TEXT_RE = re.compile(r'\.getString\(\s*"([a-z0-9_]*_at)"\s*\)')
LOCAL_TIME_VAR_RE = re.compile(r'\bOffsetDateTime\s+(\w+)\s*=')
VIEW_FIELD_RE = re.compile(r'([A-Z][A-Za-z0-9_<>,. ]*?)\s+([a-zA-Z_]\w*)\s*[,)]')
CLIENT_FIELD_RE = re.compile(r'^\s*([A-Za-z_]\w*)\??:\s*(.+?)\s*$')
DATE_TIME_HINT_RE = re.compile(r'date-time|RFC3339|rfc3339|\d{4}-\d{2}-\d{2}T|Z"')


def rel_path(p: Path, root: Path) -> str:
    """仓库外路径也能显示（skill 坑 34）。"""
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve())).replace(os.sep, "/")
    except ValueError:
        return str(Path(p).resolve()).replace(os.sep, "/")


def fingerprint(paths: list[Path]) -> dict:
    out = {}
    for p in paths:
        if not p.exists():
            out[str(p)] = None
            continue
        st = p.stat()
        out[str(p)] = (st.st_mtime_ns, st.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    return out


def strip_comments(src: str) -> str:
    """剥注释、保留字符串与模板字面量（skill 坑 58：注释里的东西不是代码）。"""
    out = []
    i, n = 0, len(src)
    state = None          # None | 'line' | 'block' | 'str' | 'char'
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if state is None:
            if c == "/" and nxt == "/":
                state = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                state = "block"
                i += 2
                continue
            if c == '"':
                state = "str"
            elif c == "'":
                state = "char"
            out.append(c)
            i += 1
            continue
        if state == "line":
            if c == "\n":
                state = None
                out.append(c)
            i += 1
            continue
        if state == "block":
            if c == "*" and nxt == "/":
                state = None
                i += 2
                continue
            if c == "\n":
                out.append(c)
            i += 1
            continue
        # 字符串 / 字符字面量：原样保留（含转义）
        if c == "\\":
            out.append(c)
            if i + 1 < n:
                out.append(src[i + 1])
            i += 2
            continue
        if (state == "str" and c == '"') or (state == "char" and c == "'"):
            state = None
        out.append(c)
        i += 1
    return "".join(out)


def statements(src: str) -> list[tuple[int, str]]:
    """按 `;` 切逻辑语句（保留起始行号），供「同一语句内是否包裹」判定。"""
    out = []
    buf = []
    line = 1
    start_line = 1
    for ch in src:
        if ch == "\n":
            line += 1
        if ch == ";":
            text = "".join(buf).strip()
            if text:
                out.append((start_line, text))
            buf = []
            start_line = line
            continue
        if not buf and ch in " \t\r\n":
            start_line = line
            continue
        buf.append(ch)
    text = "".join(buf).strip()
    if text:
        out.append((start_line, text))
    return out


def java_files(root: Path) -> list[Path]:
    base = root / SERVER_DIR
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.java") if p.is_file())


def ts_files(root: Path) -> list[Path]:
    base = root / CLIENT_DIR
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.ts") if p.is_file())


def schema_files(root: Path) -> list[Path]:
    base = root / SCHEMA_DIR
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.schema.json") if p.is_file())


class Result:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.npass = 0
        self.nfail = 0

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        tag = "PASS" if ok else "FAIL"
        if ok:
            self.npass += 1
        else:
            self.nfail += 1
        self.lines.append(f"[{tag}] {name}" + (f" — {detail}" if detail else ""))
        return ok

    def info(self, text: str) -> None:
        self.lines.append(text)


def walk_schema_props(node, prefix, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict) and ("type" in v or "format" in v or "properties" in v):
                if v.get("format") == "date-time" or str(k).endswith("_at"):
                    types = v.get("type")
                    if isinstance(types, str):
                        types = [types]
                    acc.append((prefix + k, tuple(types or ()), v.get("format")))
                if "properties" in v:
                    walk_schema_props(v["properties"], f"{prefix}{k}.", acc)
            elif isinstance(v, dict):
                walk_schema_props(v, prefix, acc)
    return acc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="仓库根（默认脚本上一级）")
    ap.add_argument("--all", action="store_true", help="打印全部明细（默认只列前 12 条）")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    r = Result()
    r.info(f"# 时间字段序列化格式一致性审计（只读）root={root}")

    watched = [p for p in java_files(root) + ts_files(root) + schema_files(root)]
    before = fingerprint(watched)

    jf = java_files(root)
    srcs = {p: strip_comments(p.read_text(encoding="utf-8", errors="replace")) for p in jf}

    # ---------------- A0 出口定义唯一 ----------------
    r.info("--- A0 统一出口定义（格式串 + 辅助方法体）---")
    patterns: list[tuple[str, str, str]] = []
    other_patterns: list[tuple[str, str, str]] = []
    helpers: list[tuple[str, str, str]] = []
    for p, src in srcs.items():
        for m in PATTERN_DEF_RE.finditer(src):
            rec = (rel_path(p, root), m.group(1), m.group(2))
            # 只把「出口格式串」纳入断言：常量名含 RFC3339/ISO。
            # 其余（yyyyMM/yyyyMMdd 这类**键值**格式，不是时间出口）记信息项 —— 否则会报出假漂移（坑 29/46）。
            if re.search(r"RFC3339|ISO", m.group(1)):
                patterns.append(rec)
            else:
                other_patterns.append(rec)
        for m in HELPER_DEF_RE.finditer(src):
            body = re.sub(r"\s+", " ", m.group(3)).strip()
            body = re.sub(rf"\b{re.escape(m.group(2))}\b", "V", body)
            helpers.append((rel_path(p, root), m.group(1), body))
    pat_forms = sorted({p[2] for p in patterns})
    r.check("A0a 正向对照：解析到出口定义（解析器真的工作了）",
            bool(patterns) and bool(helpers),
            f"出口格式串声明 {len(patterns)} 处、辅助方法 {len(helpers)} 处（为 0 即解析器失效，不得判 PASS）")
    r.check("A0b 所有 DateTimeFormatter 格式串只有 1 种",
            len(pat_forms) == 1, f"实测 {len(pat_forms)} 种：{pat_forms}")
    r.check(f"A0c 格式串 = 秒精度 UTC（{EXPECT_PATTERN}）",
            pat_forms == [EXPECT_PATTERN], f"实测 {pat_forms}")
    helper_forms = sorted({h[2] for h in helpers})
    r.check("A0d 所有辅助方法体归一化后只有 1 种",
            len(helper_forms) == 1,
            f"副本 {len(helpers)} 处 → 形态 {len(helper_forms)} 种")
    for form in helper_forms:
        r.info(f"      · 形态：{form}")
    if len(helpers) > 1:
        r.info(f"      · 观察项：同一出口有 {len(helpers)} 份副本（{'、'.join(h[0] for h in helpers[:12])}"
               f"{' 等' if len(helpers) > 12 else ''}）——逐字节相同，但属「同一函数两种写法」的漂移高发地（坑 44）")
    if other_patterns:
        forms = sorted({o[2] for o in other_patterns})
        r.info(f"      · 信息项：非出口的 DateTimeFormatter（常量名不含 RFC3339/ISO，如键值格式）"
               f"{len(other_patterns)} 处、{len(forms)} 种：{forms} —— 不参与 A0b/A0c 断言（否则假漂移，坑 29/46）")

    # ---------------- A1/A2 取值路径 ----------------
    r.info("--- A1/A2 时间列的取值路径是否被统一出口包裹 ---")
    unwrapped: list[str] = []
    text_leak: list[str] = []
    wrapped_n = 0
    var_needed: list[tuple[Path, str, int]] = []
    internal: list[str] = []
    DTO_CTOR_RE = re.compile(r'new\s+([A-Z]\w*)\s*\(')

    def camel(col: str) -> str:
        head, *rest = col.split("_")
        return head + "".join(w[:1].upper() + w[1:] for w in rest)

    for p, src in srcs.items():
        stmts = statements(src)
        for start_line, text in stmts:
            reads = TIME_READ_RE.findall(text)
            texts = TIME_TEXT_RE.findall(text)
            if texts:
                text_leak.append(f"{rel_path(p, root)}:{start_line} getString({texts[0]})")
            if not reads:
                continue
            if WRAP_RE.search(text):
                wrapped_n += len(reads)
                continue
            vm = LOCAL_TIME_VAR_RE.search(text)
            if vm:
                # 「先取局部变量、再在别处包裹」：按同文件变量引用判定（避免假发现）
                if re.search(rf'\b(?:rfc3339|RFC3339\.format)\s*\(\s*{re.escape(vm.group(1))}\b', src):
                    wrapped_n += len(reads)
                else:
                    var_needed.append((p, vm.group(1), start_line))
                continue
            ctor = DTO_CTOR_RE.search(text)
            if ctor:
                # 值直接进记录构造器 → 出口应在**使用该组件**的地方（如 `span.updatedAt()`）
                comp = camel(reads[0])
                if re.search(rf'\b(?:rfc3339|RFC3339\.format)\s*\(\s*\w+\.{re.escape(comp)}\(\)', src):
                    wrapped_n += len(reads)
                else:
                    unwrapped.append(f"{rel_path(p, root)}:{start_line} {reads} → new {ctor.group(1)} 组件 {comp} 未见出口")
                continue
            # 既没包裹、也不进响应 DTO：内部读取（如 `select read_at` 只为判空）
            internal.append(f"{rel_path(p, root)}:{start_line} {reads}")
        for var, line in [(v, ln) for (pp, v, ln) in var_needed if pp == p]:
            if not re.search(rf'\b(?:rfc3339|RFC3339\.format)\s*\(\s*{re.escape(var)}\b', src):
                unwrapped.append(f"{rel_path(p, root)}:{line} 局部变量 {var} 未包裹")
    r.check("A1a 正向对照：解析到被出口包裹的时间取值点",
            wrapped_n > 0, f"已包裹 {wrapped_n} 处（为 0 即解析器失效，不得判 PASS）")
    r.check("A1b 所有进入响应的时间值都被统一出口包裹",
            not unwrapped, f"未包裹 {len(unwrapped)} 处"
            + (f"：{unwrapped[:12]}" if unwrapped else ""))
    r.check("A1c 「内部读取」判为信息项的条数不超过阈值（否则本规则形同虚设，坑 57）",
            len(internal) <= 3, f"内部读取 {len(internal)} 处"
            + (f"：{internal[:12]}" if internal else ""))
    if internal:
        r.info("      · 信息项（判据：语句里既无出口包裹、也不构造响应 DTO → 不进入响应）：")
        for it in internal[:12]:
            r.info(f"        - {it}")
    r.check("A2 没有把时间列按数据库文本原样透传（getString）",
            not text_leak, f"文本直出 {len(text_leak)} 处"
            + (f"：{text_leak[:12]}" if text_leak else ""))

    # ---------------- A3 响应 DTO 类型 ----------------
    r.info("--- A3 响应 DTO（*Views.java）时间字段声明类型 ---")
    view_files = [p for p in jf if p.name.endswith("Views.java")]
    view_fields: list[tuple[str, str, str]] = []
    bad_view: list[str] = []
    for p in view_files:
        for m in VIEW_FIELD_RE.finditer(srcs[p]):
            typ, name = m.group(1).strip(), m.group(2)
            if name.endswith("_at") or re.search(r"[a-z]At$", name):
                view_fields.append((rel_path(p, root), typ, name))
                if typ != "String":
                    bad_view.append(f"{rel_path(p, root)} {name}: {typ}")
    r.check("A3a 正向对照：解析到响应 DTO 时间字段",
            bool(view_fields), f"{len(view_files)} 个 *Views.java、时间字段 {len(view_fields)} 个")
    r.check("A3b 响应 DTO 时间字段一律声明为 String（避免 Jackson 直出）",
            not bad_view, f"非 String {len(bad_view)} 处" + (f"：{bad_view[:12]}" if bad_view else ""))

    # ---------------- A4 客户端 ----------------
    r.info("--- A4 客户端时间字段声明类型（坑 1：跨页面通用字段以客户端为准）---")
    client_fields: list[tuple[str, str, str]] = []
    bad_client: list[str] = []
    parse_points: list[str] = []
    for p in ts_files(root):
        src = p.read_text(encoding="utf-8", errors="replace")
        if "new Date(" in src:
            parse_points.append(rel_path(p, root))
        for i, line in enumerate(src.splitlines(), 1):
            m = CLIENT_FIELD_RE.match(line)
            if not m:
                continue
            name, typ = m.group(1), m.group(2)
            if not (name.endswith("_at") or re.search(r"[a-z]At$", name)):
                continue
            client_fields.append((rel_path(p, root), typ, name))
            if "number" in typ or typ in ("Date", "number"):
                bad_client.append(f"{rel_path(p, root)}:{i} {name}: {typ}")
    r.check("A4a 正向对照：解析到客户端时间字段",
            bool(client_fields), f"{len(client_fields)} 个")
    r.check("A4b 客户端时间字段类型为 string（不得 number）",
            not bad_client, f"异常 {len(bad_client)} 处" + (f"：{bad_client[:12]}" if bad_client else ""))
    r.info(f"      · 客户端解析点（`new Date(value)`）出现在 {len(parse_points)} 个文件："
           f"{parse_points[:6]} —— 解析要求服务端输出**带偏移/Z 的 ISO-8601**（坑 1 的时间侧）")

    # ---------------- A5 schema ----------------
    r.info("--- A5 JSON Schema 侧时间字段类型 ---")
    schema_fields: list[tuple[str, tuple, str]] = []
    for p in schema_files(root):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            r.info(f"      · 跳过无法解析的 schema：{rel_path(p, root)}（{exc}）")
            continue
        acc = walk_schema_props(doc.get("properties", {}), "", [])
        for name, types, fmt in acc:
            schema_fields.append((f"{rel_path(p, root)}#{name}", types, fmt or ""))
    bad_schema = [f"{n} type={t}" for n, t, _ in schema_fields
                  if t and ("string" not in t or "number" in t or "integer" in t)]
    r.check("A5a 正向对照：解析到 schema 时间字段",
            bool(schema_fields), f"{len(schema_fields)} 个（date-time 或 *_at）")
    r.check("A5b schema 时间字段类型含 string（不得 number/integer）",
            not bad_schema, f"异常 {len(bad_schema)} 处" + (f"：{bad_schema[:12]}" if bad_schema else ""))

    # ---------------- A6 信息项 ----------------
    r.info("--- A6 信息项（说明门禁为何看不见）---")
    inline_wrap = 0
    for p, src in srcs.items():
        inline_wrap += len(re.findall(r'RFC3339\.format\s*\(', src))
    helper_calls = 0
    for p, src in srcs.items():
        helper_calls += len(re.findall(r'\brfc3339\s*\(', src)) - len(re.findall(r'static\s+String\s+rfc3339', src))
    r.info(f"      · 两种等价写法并存：helper 调用 {helper_calls} 处、内联 `RFC3339.format(...)` {inline_wrap} 处"
           f"（坑 44：同一出口两种写法，未来改一处忘另一处即漂移）")
    test_dir = root / TEST_DIR
    fmt_asserts = 0
    if test_dir.exists():
        for p in sorted(test_dir.rglob("*.java")):
            fmt_asserts += len(DATE_TIME_HINT_RE.findall(p.read_text(encoding="utf-8", errors="replace")))
    r.info(f"      · 测试源里时间格式相关字样（date-time/RFC3339/…T…/Z\"）共 {fmt_asserts} 处；"
           f"契约测试只校验 JSON Schema，而 `format: date-time` 对秒/毫秒/偏移/无偏移**全部放行** → 格式漂移 204 例不可见")

    # ---------------- 零写副作用 ----------------
    r.info("--- 零写副作用自检 ---")
    after = fingerprint(watched)
    changed = [rel_path(Path(k), root) for k in before if before[k] != after[k]]
    r.check("Z1 全部被读文件指纹未变（脚本零写副作用）", not changed,
            f"被改写={len(changed)} 个：{changed[:5]}")

    print("\n".join(r.lines))
    print(f"\n断言 {r.npass + r.nfail} 条：PASS {r.npass}，FAIL {r.nfail}")
    return 0 if r.nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
