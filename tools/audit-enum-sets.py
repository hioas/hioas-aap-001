#!/usr/bin/env python3
"""R36 契约不变量审计（第十一类）：全局枚举取值集合跨五处真源逐枚举比对。

为什么需要它（为什么既有门禁查不出）：
  * 契约测试只把**真实 HTTP 响应**与 JSON Schema 的 `enum` 比对 → 只能发现
    「实现产出了 schema 未声明的取值」这一方向；而 **schema/openapi/md 里声明了、
    实现永远不产出**的取值（死枚举）对全部用例完全不可见。
  * `openapi.yaml` 的内联 enum 组件、`aap-client` 的 TS 联合类型
    **从不被任何测试读取或执行** → 两处声明漂移对 204 例不可见。
  * 客户端拿不到某个取值时，UI 的状态分支会静默落到兜底（空白/未知），
    与坑 1（字段名漂移导致列表空白）是同一类后果。

五处真源：
  M = docs/backend/02-API接口模型清单.md  §5 全局枚举字典（冻结字典）＋ §4 错误码表
  O = docs/backend/openapi.yaml            components.schemas 内联 `type: string` + `enum`
  S = docs/backend/json-schema/models/*.schema.json  逐属性 `enum`
  C = aap-client/src/**/*.ts               `export type X = 'A' | 'B'`
  I = aap-server/src/main/java/**/*.java   ①SQL 文本块内取值字面量 ②显式声明的取值集合
                                            （`Set.of(...)` 常量 / `@Pattern(regexp="^(A|B)$")`）

用法：
  python tools/audit-enum-sets.py            # 断言模式（任一 FAIL → rc=1）
  python tools/audit-enum-sets.py --measure  # 只打印计数与未分类项，不做断言
  python tools/audit-enum-sets.py --md <p> --openapi <p> --schemas-dir <d> ...
只读：本脚本不写任何仓库文件。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 实现侧允许出现的非枚举全大写字面量（HTTP 头/内部标记/环境变量名等）。
IMPL_LITERAL_ALLOWLIST = {
    "IF_MATCH", "IDEMPOTENCY_KEY", "X_REQUEST_ID", "BEARER", "UTF_8",
    "ASC", "DESC", "NORMAL", "NONE", "BOTH", "ADMIN", "BILL", "DETECT",
    "CONTRACT", "DETECTION", "ASSIGN", "DELETE", "POST", "GET", "PUT",
    "AAP_CREDENTIAL_AES_KEY", "AAP_JWT_SECRET",
}
IMPL_UNCLASSIFIED_MAX = 25      # A7：SQL 文本块内未分类字面量上限（超限说明豁免被架空，坑 68）
DECLARED_UNCLASSIFIED_MAX = 6   # A8：显式取值集合里无法归属到任何枚举族的上限

MD_SECTION5_RE = re.compile(r"^##\s*5\.\s*全局枚举字典\s*$", re.M)
MD_SECTION4_RE = re.compile(r"^##\s*4\..*$", re.M)
CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
MD_TOKEN_RE = re.compile(r"`([A-Za-z][A-Za-z_0-9-]*)`")
MD_CODE_RE = re.compile(r"`(E-\d{4}|0)`")
UPPER_LITERAL_RE = re.compile(r"[\"']([A-Z][A-Z_0-9]{2,})[\"']")
SQL_LITERAL_RE = re.compile(r"'([A-Z][A-Z_0-9]{2,})'")
SET_OF_RE = re.compile(r"Set(?:\.of|<\s*String\s*>\.of)\(([^)]*)\)")
PATTERN_RE = re.compile(r"@Pattern\s*\(\s*regexp\s*=\s*\"\^?\(([^)]*)\)\$?\"")
QUOTED_RE = re.compile(r"[\"']([A-Za-z][A-Za-z_0-9-]*)[\"']")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_unescaped(line: str) -> list[str]:
    """按**未转义**的竖线切分 md 表格行并还原字面竖线（坑 48）。"""
    cells = CELL_SPLIT_RE.split(line.strip())
    return [c.replace("\\|", "|").strip() for c in cells]


def drop_edge_empties(cells: list[str]) -> list[str]:
    """去掉行首/行尾由 `|` 产生的空单元格（坑 46：漏了它 → 全部行被静默跳过）。"""
    while cells and cells[0] == "":
        cells = cells[1:]
    while cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def parse_md_enum_dict(text: str) -> tuple[dict[str, set[str]], set[str], list[str]]:
    """M：§5 全局枚举字典 → ({枚举名: 取值集合}, §4 错误码全集, notes)。

    取值集合可能为空（如 `TierField` 行只登记 `len` 这类字段名）——
    **名字仍然算登记**，只是取值不参与集合比对。
    """
    m = MD_SECTION5_RE.search(text)
    if not m:
        return {}, set(), ["§5 全局枚举字典 未找到"]
    enums: dict[str, set[str]] = {}
    notes: list[str] = []
    for raw in text[m.end():].splitlines():
        if raw.startswith("## "):
            break
        if not raw.strip().startswith("|"):
            continue
        cells = drop_edge_empties(split_unescaped(raw))
        if len(cells) < 3:
            continue
        name = cells[0]
        if not name or set(name) <= set("-: ") or name in ("枚举", "取值"):
            continue
        vals = {t for t in MD_TOKEN_RE.findall(cells[1]) if t.isupper()}
        enums[name] = vals
        if not vals:
            notes.append(f"§5 行 `{name}` 无大写取值 token（字段名/非枚举项）：{cells[1][:48]}")
    codes = set(MD_CODE_RE.findall(text))
    return enums, codes, notes


def parse_openapi_enums(text: str) -> tuple[dict[str, set[str]], int]:
    """O：components.schemas 中内联 `type: string` + `enum:` 的组件；返回 (枚举, 组件总数)。"""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.rstrip() == "  schemas:")
    except StopIteration:
        return {}, 0
    enums: dict[str, set[str]] = {}
    total = 0
    cur: str | None = None
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() and not line.startswith(" "):
            break
        m4 = re.match(r"^    ([A-Za-z0-9_]+):\s*$", line)
        if m4:
            cur = m4.group(1)
            total += 1
            i += 1
            continue
        if cur and re.match(r"^      enum:\s*$", line):
            vals: set[str] = set()
            j = i + 1
            while j < len(lines) and re.match(r"^\s{8}-\s*\S", lines[j]):
                vals.add(lines[j].strip()[2:].strip().strip("'\""))
                j += 1
            enums[cur] = vals
            i = j
            continue
        i += 1
    return enums, total


def parse_schema_enums(schemas_dir: Path) -> list[tuple[str, str, set[str]]]:
    """S：逐属性 enum（剔除 null）→ [(文件, 属性路径, 取值集合)]。

    必须**递归**扫描 `json-schema/` 全部子目录（models + requests + common）：
    第一版只扫 `models/`，于是 `contract-sign.sign_method`(SMS/SEAL)、
    `qualification-create.category`(BUSINESS_LICENSE/AUTHORIZATION/OTHER) 被判「契约未声明」
    ——**2 条假发现**（坑 29/46 族：源没扫全 → 「找不到」被当成「不存在」）。
    """
    out: list[tuple[str, str, set[str]]] = []
    for path in sorted(schemas_dir.rglob("*.schema.json")):
        try:
            label = str(path.relative_to(schemas_dir))
        except ValueError:
            label = path.name
        data = json.loads(read_text(path))

        def walk(node, where: str) -> None:
            if isinstance(node, dict):
                if isinstance(node.get("enum"), list):
                    vals = {v for v in node["enum"] if isinstance(v, str)}
                    if vals:
                        out.append((label, where, vals))
                for k, v in node.items():
                    if k == "properties":
                        for pk, pv in v.items():
                            walk(pv, f"{where}.{pk}" if where else pk)
                    elif k in ("items", "$defs", "definitions", "allOf", "anyOf", "oneOf"):
                        walk(v, where)

        walk(data, "")
    return out


def parse_er_domains(er_path: Path) -> dict[str, set[str]]:
    """E：01-ER数据模型.md 的列取值域 → {列名: 取值集合}（用于给 A8 的未声明项做双向取证）。

    两种真实写法：`` `col`(A/B/C) ``（段落式）与 `` | col | varchar | | A/B/C | ``（表格式）。
    """
    if not er_path.exists():
        return {}
    text = read_text(er_path)
    domains: dict[str, set[str]] = {}
    for col, vals in re.findall(r"`([a-z_]+)`\(([A-Z][A-Z_/0-9]*)\)", text):
        domains.setdefault(col, set()).update(vals.split("/"))
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = drop_edge_empties(split_unescaped(line))
        if len(cells) < 3 or not re.fullmatch(r"[a-z_]+", cells[0]):
            continue
        for cell in cells[2:]:
            m = re.fullmatch(r"([A-Z][A-Z_0-9]*)(/[A-Z][A-Z_0-9]*)+", cell.replace(" ", ""))
            if m:
                domains.setdefault(cells[0], set()).update(cell.replace(" ", "").split("/"))
                break
    return domains


def parse_client_unions(client_dir: Path) -> dict[str, set[str]]:
    """C：`export type X = 'A' | 'B'` → {X: 取值集合}。"""
    out: dict[str, set[str]] = {}
    if not client_dir.exists():
        return out
    for path in sorted(client_dir.rglob("*.ts")):
        for line in read_text(path).splitlines():
            m = re.match(r"^\s*export\s+type\s+([A-Za-z0-9_]+)\s*=\s*(.+)$", line)
            if not m:
                continue
            vals = set(re.findall(r"'([A-Z][A-Z_0-9]*)'", m.group(2)))
            if vals:
                out[m.group(1)] = vals
    return out


def parse_impl_sql_literals(main_dir: Path) -> dict[str, int]:
    """I①：Java 文本块（`\"\"\"`）里的 SQL 取值字面量 → {字面量: 次数}。"""
    counts: dict[str, int] = {}
    if not main_dir.exists():
        return counts
    for path in sorted(main_dir.rglob("*.java")):
        in_block = False
        for line in read_text(path).splitlines():
            if line.count('"""') % 2 == 1:
                in_block = not in_block
                continue
            if in_block:
                for tok in SQL_LITERAL_RE.findall(line):
                    counts[tok] = counts.get(tok, 0) + 1
    return counts


def parse_impl_declared_sets(main_dir: Path) -> dict[str, set[str]]:
    """I②：显式声明的取值集合 → {来源标签: 取值集合}。

    覆盖两种真实写法：`Set.of("A","B")`（如 ReviewService.REASON_CODES）
    与 `@Pattern(regexp = "^(A|B|C)$")`（如 ProviderController.industry_category）。
    """
    out: dict[str, set[str]] = {}
    if not main_dir.exists():
        return out
    for path in sorted(main_dir.rglob("*.java")):
        text = read_text(path)
        for i, line in enumerate(text.splitlines(), start=1):
            if "Set.of" in line or re.search(r"Set<\s*String\s*>\s*\w+\s*=", line):
                chunk = line
                j = i
                lines = text.splitlines()
                while chunk.count("(") > chunk.count(")") and j < len(lines):
                    chunk += lines[j]
                    j += 1
                vals = set(QUOTED_RE.findall(chunk))
                vals = {v for v in vals if v.isupper() and len(v) > 2}
                if len(vals) >= 2:
                    out[f"{path.name}:{i}"] = vals
            for m in PATTERN_RE.finditer(line):
                vals = {v.strip() for v in m.group(1).split("|") if v.strip()}
                if len(vals) >= 2:
                    out[f"{path.name}:{i} (@Pattern)"] = vals
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=str(ROOT / "docs/backend/02-API接口模型清单.md"))
    ap.add_argument("--openapi", default=str(ROOT / "docs/backend/openapi.yaml"))
    ap.add_argument("--schemas-dir", default=str(ROOT / "docs/backend/json-schema"))
    ap.add_argument("--er-doc", default=str(ROOT / "docs/backend/01-ER数据模型.md"))
    ap.add_argument("--client-dir", default=str(ROOT / "aap-client/src"))
    ap.add_argument("--main-dir", default=str(ROOT / "aap-server/src/main/java"))
    ap.add_argument("--measure", action="store_true")
    args = ap.parse_args()

    md_enums, md_codes, md_notes = parse_md_enum_dict(read_text(Path(args.md)))
    oa_enums, oa_components = parse_openapi_enums(read_text(Path(args.openapi)))
    schema_enums = parse_schema_enums(Path(args.schemas_dir))
    er_domains = parse_er_domains(Path(args.er_doc))
    client_unions = parse_client_unions(Path(args.client_dir))
    sql_literals = parse_impl_sql_literals(Path(args.main_dir))
    declared_sets = parse_impl_declared_sets(Path(args.main_dir))

    md_universe = set().union(*md_enums.values()) if md_enums else set()

    fails: list[str] = []
    infos: list[str] = []

    def ok(cond: bool, label: str, detail: str = "") -> None:
        print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" | {detail}" if detail else ""))
        if not cond:
            fails.append(label)

    print("== 解析计数（正向对照，任一为 0 即说明解析器失效，坑 46） ==")
    print(f"   M(§5 枚举族)={len(md_enums)}  M(§4 错误码)={len(md_codes)}  "
          f"O(openapi 内联 enum)={len(oa_enums)}/{oa_components} 组件  "
          f"S(schema enum 属性)={len(schema_enums)}  C(客户端联合类型)={len(client_unions)}  "
          f"I①(SQL 字面量)={len(sql_literals)}  I②(显式集合)={len(declared_sets)}")
    for note in md_notes:
        print(f"   [M-note] {note}")

    print("\n== A0 解析器正向对照 ==")
    ok(len(md_enums) >= 10, "A0.1 M 解析到 ≥10 个枚举族", f"实际 {len(md_enums)}")
    ok(len(md_codes) >= 10, "A0.2 M 解析到 ≥10 个错误码", f"实际 {len(md_codes)}")
    ok(len(oa_enums) >= 1, "A0.3 O 解析到 ≥1 个内联枚举", f"实际 {len(oa_enums)}")
    ok(len(schema_enums) >= 1, "A0.4 S 解析到 ≥1 个 enum 属性", f"实际 {len(schema_enums)}")
    ok(len(client_unions) >= 1, "A0.5 C 解析到 ≥1 个联合类型", f"实际 {len(client_unions)}")
    ok(len(sql_literals) >= 1, "A0.6 I① 解析到 ≥1 个 SQL 字面量", f"实际 {len(sql_literals)}")
    ok(len(declared_sets) >= 2, "A0.7 I② 解析到 ≥2 个显式取值集合", f"实际 {len(declared_sets)}")
    ok(len(er_domains) >= 5, "A0.8 E(ER 列取值域) 解析到 ≥5 个", f"实际 {len(er_domains)}")

    print("\n== A1 M↔O（共有枚举名）取值集合逐名比对 ==")
    shared = sorted(n for n in set(md_enums) & set(oa_enums) if md_enums[n])
    ok(len(shared) >= 5, "A1.0 可比对共有枚举名 ≥5", f"实际 {len(shared)}")
    for name in shared:
        a, b = md_enums[name], oa_enums[name]
        ok(a == b, f"A1 {name} md↔openapi 一致",
           "" if a == b else f"md-only={sorted(a - b)} openapi-only={sorted(b - a)}")

    print("\n== A2 openapi 侧孤儿枚举（名字未在 §5 字典登记） ==")
    oa_orphans = sorted(set(oa_enums) - set(md_enums))
    ok(not oa_orphans, "A2 openapi 内联枚举名全部在 md §5 登记",
       f"孤儿 {len(oa_orphans)}: " + ", ".join(f"{n}({len(oa_enums[n])})" for n in oa_orphans))

    print("\n== A3 md 侧有、openapi 无（信息项） ==")
    md_only = sorted(set(md_enums) - set(oa_enums))
    print(f"[INFO] md 有而 openapi 无的枚举族 {len(md_only)}: {md_only}")
    infos.append(f"md-only 枚举族 {len(md_only)}")

    print("\n== A4 M↔C（客户端联合类型）逐名比对 ==")
    for name, vals in sorted(client_unions.items()):
        if name in md_enums and md_enums[name]:
            ok(md_enums[name] == vals, f"A4 {name} md↔客户端 一致",
               "" if md_enums[name] == vals
               else f"md-only={sorted(md_enums[name] - vals)} client-only={sorted(vals - md_enums[name])}")
        else:
            infos.append(f"客户端联合类型 {name} 未在 md §5 登记：{sorted(vals)}")
            print(f"[INFO] 客户端联合类型 `{name}` 不在 md §5：{sorted(vals)}")

    print("\n== A5 S 的每个 enum 取值集合必须能归属到一个枚举族 ==")
    assign: dict[tuple[str, str], str] = {}   # 键必须是 (文件, 属性路径)：只按属性名会跨文件串味
    unassigned = 0
    for fname, where, vals in schema_enums:
        exact = [n for n, mv in md_enums.items() if mv and vals == mv]
        subs = [n for n, mv in md_enums.items() if mv and vals <= mv]
        name_only = [n for n, mv in md_enums.items() if not mv and n.lower().replace("_", "") in
                     (where.replace("_", ""), where.replace("_field", "").replace("_code", ""))]
        if len(exact) == 1:
            assign[(fname, where)] = exact[0]
            print(f"  [exact ] {fname}:{where} == {exact[0]} ({len(vals)} 值)")
        elif len(subs) == 1:
            assign[(fname, where)] = subs[0]
            print(f"  [subset] {fname}:{where} ⊆ {subs[0]} ({len(vals)} 值) → 合法收窄")
        elif name_only:
            infos.append(f"{fname}:{where} 对应 §5 行 `{name_only[0]}`（该行只登记字段名、无大写取值，"
                         f"取值不可机器比对）：{sorted(vals)}")
            print(f"  [md-name-only] {fname}:{where} §5 行 `{name_only[0]}` 无取值可比 → 记 INFO，不判 FAIL")
        else:
            oa_hits = [n for n, mv in oa_enums.items() if vals == mv]
            oa_sub = [n for n, mv in oa_enums.items() if vals < mv]
            unassigned += 1
            fails.append(f"A5 {fname}:{where} 无匹配")
            hint = ""
            if oa_hits:
                hint = f"（与 openapi 族 {oa_hits[0]} 相同 → 疑似 §5 漏登记）"
            elif oa_sub:
                hint = f"（是 openapi 族 {oa_sub[0]} 的子集 → 疑似 §5 漏登记）"
            print(f"  [FAIL ] {fname}:{where} 取值 {sorted(vals)} 不匹配任何 md §5 族{hint}")
    ok(unassigned == 0, "A5 全部 schema enum 均归属到 md §5 枚举族（未归属的已逐条 FAIL）",
       f"已归属 {len(assign)} / {len(schema_enums)}，未归属 {unassigned}")

    print("\n== A6 S↔O 逐族一致（同一族的 schema 取值并集 == openapi 集合） ==")
    union_by_family: dict[str, set[str]] = {}
    for (fname, where, vals) in schema_enums:
        fam = assign.get((fname, where))
        if fam:
            union_by_family.setdefault(fam, set()).update(vals)
    for fam in sorted(set(union_by_family) & set(oa_enums)):
        u, o = union_by_family[fam], oa_enums[fam]
        ok(u == o, f"A6 {fam} schema↔openapi 一致",
           "" if u == o else f"schema-only={sorted(u - o)} openapi-only={sorted(o - u)}")


    print("\n== A7 实现 SQL 字面量 ⊆ (md §5 ∪ §4 错误码) ==")
    universe = md_universe | md_codes
    unclassified = sorted(v for v in sql_literals if v not in universe and v not in IMPL_LITERAL_ALLOWLIST)
    print(f"[INFO] 未分类 SQL 字面量 {len(unclassified)}: "
          + ", ".join(f"{v}x{sql_literals[v]}" for v in unclassified[:30]))
    ok(len(unclassified) <= IMPL_UNCLASSIFIED_MAX, "A7 未分类 SQL 字面量 ≤ 阈值",
       f"{len(unclassified)} ≤ {IMPL_UNCLASSIFIED_MAX}")

    print("\n== A8 实现显式取值集合必须落在契约取值域内（未声明项做 ER 双向取证） ==")
    contract_sets = {f"{n} (openapi)": v for n, v in oa_enums.items()}
    for (fname, where, vals) in schema_enums:
        contract_sets.setdefault(f"{fname}:{where} (schema)", vals)
    unmatched: list[str] = []
    for label, vals in sorted(declared_sets.items()):
        eq = [n for n, ov in contract_sets.items() if vals == ov]
        sub = [n for n, ov in contract_sets.items() if vals <= ov]
        if eq:
            print(f"  [exact ] {label} == {eq[0]} ({len(vals)} 值)")
        elif sub:
            print(f"  [subset] {label} ⊆ {sub[0]} ({len(vals)} 值) → 合法收窄（可编辑/可选状态集）")
        else:
            er_hits = sorted(c for c, dv in er_domains.items() if vals <= dv)
            unmatched.append(f"{label}={sorted(vals)}")
            if er_hits:
                print(f"  [FAIL ] {label} {sorted(vals)}：契约(schema/openapi)未声明该取值域，"
                      f"但 ER 文档有据（列 {er_hits}）→ 契约完备性项")
            else:
                print(f"  [FAIL ] {label} {sorted(vals)}：契约与 ER 文档**均无**取值域声明"
                      f" → 实现凭空定义，需拍板")
    ok(not unmatched, "A8 实现声明的取值域均在契约中声明",
       f"未声明 {len(unmatched)}: " + "; ".join(unmatched[:6]))

    print("\n== A9 ResultCode ↔ md §4 错误码表（同一码集两处声明） ==")
    if "ResultCode" in oa_enums:
        rc = oa_enums["ResultCode"]
        ok(rc == md_codes, "A9 openapi ResultCode 集合 == md §4 码表集合",
           "" if rc == md_codes else f"openapi-only={sorted(rc - md_codes)} md-only={sorted(md_codes - rc)}")
    else:
        ok(False, "A9 openapi 存在 ResultCode 枚举", "未找到 ResultCode 组件")


    print("\n== 汇总 ==")
    print(f"断言 FAIL {len(fails)} 条；INFO {len(infos)} 条")
    for f in fails:
        print(f"  FAIL: {f}")
    if args.measure:
        print("[measure] 已跳过断言退出码")
        return 0
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
