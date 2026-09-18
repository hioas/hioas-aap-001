#!/usr/bin/env python3
"""错误码契约一致性审计（R28，只读）。

不变量：**同一个错误码集合**必须在五处真源逐端点一致 —— 与 `audit-contract-keys.py`
（分页集合键名不变量）同族，但换一条契约不变量：错误码。

  简称  文件                                                        承载方式
  ----  ----------------------------------------------------------  ------------------------------
  M     docs/backend/endpoints.json                                逐端点 `error_codes`
  O     docs/backend/openapi.yaml                                    `components.schemas.ResultCode.enum`
                                                                    + 每 operation `4XX.description: 业务失败：...`
  J     aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java 枚举字面量
  S     docs/backend/json-schema/common/error.schema.json            `properties.code.enum`
  D     docs/backend/02-API接口模型清单.md                           逐行「错误码」列（**按表头定位列序**）

为什么需要它（skill 坑 43 / 44）：契约测试只校验 JSON Schema 文件，**从不读 openapi.yaml**；
生成器若在 OpenAPI 分支写错错误码，全部 204 例仍然全绿 —— 漂移对用例完全不可见。

只读保证：脚本不写任何仓库文件；收尾用 `(mtime_ns, size, md5)` 指纹自检五处源文件未被改动。

用法：
  python tools/audit-error-codes.py [--root <dir>]
  （--root 供负向自测指向仓库外的夹具目录；默认 = 本脚本上一级目录）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 解析工具

REL = [
    "docs/backend/endpoints.json",
    "docs/backend/openapi.yaml",
    "docs/backend/json-schema/common/error.schema.json",
    "docs/backend/02-API接口模型清单.md",
    "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java",
]

CODE_RE = re.compile(r"E-\d{4}")
RANGE_RE = re.compile(r"(E-(\d{4}))\s*[~～-]\s*(?:E-)?(\d{4})")
NOTE_RE = re.compile(r"[（(][^）)]*[）)]")


def rel_path(p: Path, root: Path) -> str:
    """仓库外路径也能显示（skill 坑 34）。"""
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve())).replace(os.sep, "/")
    except ValueError:
        return str(Path(p).resolve()).replace(os.sep, "/")


def sha8(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:8]


def fingerprint(paths: list[Path]) -> dict:
    out = {}
    for p in paths:
        if not p.exists():
            out[str(p)] = None
            continue
        st = p.stat()
        out[str(p)] = (st.st_mtime_ns, st.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    return out


def expand_codes(cell: str) -> set[str]:
    """把「E-1401~E-1405 E-1601(未审核通过)」这类单元格展开成码集合。

    - 区间必须**同前缀且升序**才展开，且**不得外溢**（E-1401~E-1403 不含 E-1404）
    - 括号里的中文注释先剥离（否则 E-1601(未审核通过) 会解析成 E-1601 + 噪声）
    """
    text = NOTE_RE.sub(" ", cell or "")
    out: set[str] = set()
    for m in RANGE_RE.finditer(text):
        start_pref, start, end = m.group(2), int(m.group(2)), int(m.group(3))
        if start <= end:
            for n in range(start, end + 1):
                out.add("E-%04d" % n)
        # 升序外的区间不展开（视为书写错误，由调用方报 FAIL）
        text = text[: m.start()] + " " + text[m.end():]
    for c in CODE_RE.findall(text):
        out.add(c)
    return out


# ---------------------------------------------------------------- 五处解析

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
        self.lines.append(f"[{tag}] {name}" + (f"：{detail}" if detail else ""))
        return ok

    def info(self, text: str) -> None:
        self.lines.append(text)


def parse_manifest(p: Path) -> tuple[int, dict[str, set[str]]]:
    """M：endpoints.json → {ID: 码集合}，返回 (total, map)。"""
    data = json.loads(p.read_text(encoding="utf-8"))
    total = int(data.get("total", len(data.get("endpoints", []))))
    return total, {e["id"]: set(e.get("error_codes") or []) for e in data["endpoints"]}


def parse_openapi_enum(text: str) -> set[str]:
    """O1：components.schemas.ResultCode.enum（严格按缩进定位，别蹭到别处的 enum）。"""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^    ResultCode:\s*$", ln):
            start = i
            break
    if start is None:
        return set()
    codes: set[str] = set()
    in_enum = False
    for ln in lines[start + 1:]:
        if re.match(r"^    \S", ln):  # 下一个同级 schema → 结束
            break
        if re.match(r"^      enum:\s*$", ln):
            in_enum = True
            continue
        if in_enum:
            m = re.match(r"^        - (\S+)\s*$", ln)
            if m:
                codes.add(m.group(1))
            elif ln.strip():
                break
    return codes


def parse_openapi_ops(text: str) -> dict[str, set[str]]:
    """O2：逐 operation 的 4XX 描述里的码集合（按 operationId 归属）。

    缩进必须逐层校验：`  /path:`(2) → `    method:`(4) → `      operationId:`(6) → `        4XX:`(8)
    → `          description: 业务失败：...`(10)。缩进写错会让全部 FAIL 消失（假绿，坑 44）。
    """
    ops: dict[str, set[str]] = {}
    cur_id = None
    in_4xx = False
    for ln in text.splitlines():
        m = re.match(r"^      operationId: (\S+)\s*$", ln)
        if m:
            cur_id = m.group(1)
            ops.setdefault(cur_id, set())
            in_4xx = False
            continue
        if re.match(r"^        4XX:\s*$", ln):
            in_4xx = True
            continue
        if in_4xx and cur_id is not None:
            m = re.match(r"^          description: (.*)$", ln)
            if m:
                ops[cur_id] = expand_codes(m.group(1))
                in_4xx = False
            elif re.match(r"^        \S", ln):  # 离开该 operation 的 responses 块
                in_4xx = False
    return ops


def parse_java_codes(p: Path) -> set[str]:
    """J：ErrorCode.java 的枚举字面量（含 SUCCESS 的 '0'）。"""
    text = p.read_text(encoding="utf-8")
    codes = set(CODE_RE.findall(text))
    if re.search(r'SUCCESS\("0"', text):
        codes.add("0")
    return codes


def parse_schema_codes(p: Path) -> set[str]:
    """S：error.schema.json 的 code.enum。"""
    data = json.loads(p.read_text(encoding="utf-8"))
    return set(data["properties"]["code"]["enum"])


def split_row(ln: str) -> list[str]:
    """按**未被转义**的 `|` 切分 markdown 表格行。

    真实返工（R28 首次运行）：ADM-S05 的单元格写作 ``body `{target_status:ENABLED\\|DISABLED}` ``
    —— markdown 里 `\\|` 是单元格内的字面竖线，裸 `split("|")` 会多切出一格，
    于是该行因「列数与表头不符」被静默跳过（D 行数 89 而非 90，A8 报出假缺口 ADM-S05）。
    规则：切分用 `(?<!\\\\)\\|`，并把转义竖线还原为字面 `|` 后再参与解析。
    """
    cells = re.split(r"(?<!\\)\|", ln.strip("|"))
    return [c.replace("\\|", "|").strip() for c in cells]


def parse_md_rows(p: Path) -> tuple[dict[str, set[str]], list[str]]:
    """D：md 清单逐行「错误码」列，**按表头定位列序**（本文件有两套表头：10 列 / 7 列）。

    返回 (rows, problems)。第一格为 `ID` 的行是表头；其余以 `|` 开头的行按当前表头解析。
    """
    rows: dict[str, set[str]] = {}
    problems: list[str] = []
    header: list[str] | None = None
    for raw in p.read_text(encoding="utf-8").splitlines():
        ln = raw.strip()
        if not ln.startswith("|"):
            continue
        cells = split_row(ln)
        if cells and cells[0] == "ID":
            header = cells
            continue
        if header is None:
            continue
        if set("".join(cells)) <= set("-: "):  # 分隔行
            continue
        if len(cells) != len(header):
            continue
        row_id = cells[0]
        if not re.match(r"^[A-Z]+-[A-Z0-9]+$", row_id):
            continue
        if "错误码" not in header:
            problems.append(f"{row_id}: 当前表头无「错误码」列（列序定位失败）")
            continue
        idx = header.index("错误码")
        rows[row_id] = expand_codes(cells[idx])
    return rows, problems


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    paths = {k: root / r for k, r in zip(["M", "O", "S", "D", "J"], REL)}

    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        print("[FAIL] 源文件缺失：" + ", ".join(f"{k}={paths[k]}" for k in missing))
        return 1

    before = fingerprint(list(paths.values()))
    r = Result()
    r.info(f"根目录：{rel_path(root, root)}")

    total, m_map = parse_manifest(paths["M"])
    o_text = paths["O"].read_text(encoding="utf-8")
    o_enum = parse_openapi_enum(o_text)
    o_ops = parse_openapi_ops(o_text)
    j_codes = parse_java_codes(paths["J"])
    s_codes = parse_schema_codes(paths["S"])
    d_map, d_problems = parse_md_rows(paths["D"])

    r.info("--- 正向对照（解析器真的解析到了）---")
    r.check("A0a M 端点数 = total", total > 0 and len(m_map) == total, f"total={total} parsed={len(m_map)}")
    r.check("A0b O operation 数 = total", len(o_ops) == total, f"parsed={len(o_ops)} 期望={total}")
    r.check("A0c D 行数 = total", len(d_map) == total, f"parsed={len(d_map)} 期望={total}")
    r.check("A0d J 码数 = O.enum 码数", len(j_codes) == len(o_enum), f"J={len(j_codes)} O.enum={len(o_enum)}")
    r.check("A0e S 码数 = J 码数 - 1（S 不含成功码 0）", len(s_codes) == len(j_codes) - 1,
            f"S={len(s_codes)} J={len(j_codes)}")
    r.check("A0f O ResultCode enum 非空", len(o_enum) > 0, f"parsed={len(o_enum)}")

    r.info("--- 目录级一致（J ↔ S ↔ O.enum）---")
    r.check("A1 J 与 S 码集合一致", j_codes - {"0"} == s_codes,
            "差集=" + str(sorted((j_codes - {"0"}) ^ s_codes)))
    r.check("A2 O.ResultCode 与 J 一致", o_enum == j_codes,
            "差集=" + str(sorted(o_enum ^ j_codes)))

    r.info("--- 逐端点一致（M ↔ J / O.4XX / D）---")
    undeclared = {eid: sorted(c - j_codes) for eid, c in m_map.items() if c - j_codes}
    r.check("A3 清单声明的码都在 ErrorCode.java 目录里", not undeclared, f"越界={undeclared}")

    used = set().union(*m_map.values()) if m_map else set()
    orphan = sorted((j_codes - {"0"}) - used)
    r.check("A4 目录里的码都被至少一个端点声明（无孤儿码）", not orphan, f"孤儿={orphan}")

    r.check("A5 openapi operation 数 = 清单端点数", set(o_ops) == set(m_map),
            "差集=" + str(sorted(set(o_ops) ^ set(m_map))))
    o_mismatch = {eid: {"openapi": sorted(o_ops.get(eid, set())), "清单": sorted(m_map.get(eid, set()))}
                  for eid in sorted(m_map) if o_ops.get(eid, set()) != m_map[eid]}
    r.check("A6 openapi 每 operation 4XX 码集合 = 清单", not o_mismatch, f"不一致 {len(o_mismatch)} 条")
    if o_mismatch:
        for eid, d in list(o_mismatch.items())[:12]:
            r.info(f"      · {eid}: openapi={d['openapi']} 清单={d['清单']}")

    r.check("A7 md 表头定位无异常", not d_problems, "; ".join(d_problems[:5]))
    r.check("A8 md 行 ID 集合 = 清单 ID 集合", set(d_map) == set(m_map),
            "差集=" + str(sorted(set(d_map) ^ set(m_map))))
    d_mismatch = {eid: {"md": sorted(d_map.get(eid, set())), "清单": sorted(m_map.get(eid, set()))}
                  for eid in sorted(m_map) if d_map.get(eid, set()) != m_map[eid]}
    r.check("A9 md 每行错误码列 = 清单", not d_mismatch, f"不一致 {len(d_mismatch)} 条")
    if d_mismatch:
        for eid, d in list(d_mismatch.items())[:15]:
            r.info(f"      · {eid}: md={d['md']} 清单={d['清单']}")

    r.info("--- 零写副作用自检 ---")
    after = fingerprint(list(paths.values()))
    changed = [rel_path(Path(k), root) for k in before if before[k] != after[k]]
    r.check("Z1 五处源文件指纹未变（脚本零写副作用）", not changed, f"被改写={changed}")

    print("\n".join(r.lines))
    print(f"\n断言 {r.npass + r.nfail} 条：PASS {r.npass}，FAIL {r.nfail}")
    return 0 if r.nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
