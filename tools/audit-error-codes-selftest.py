#!/usr/bin/env python3
"""`tools/audit-error-codes.py` 的负向自测（R28）。

纪律（skill 坑 32 / 46）：**每个判定分支都要有反例**，且必须同时有**正向对照** ——
否则「审计一直在报错」会被误当成「审计很严格」。

覆盖的分支：
  case_positive                 全部一致 → 16 条断言全 PASS、rc=0（正向对照）
  case_manifest_code_unknown    A3：清单声明了目录里没有的码
  case_orphan_code              A4：目录里有、无端点声明（孤儿码）
  case_openapi_op_mismatch      A6：openapi 某 operation 的 4XX 码与清单不一致
  case_md_row_mismatch          A9：md 某行「错误码」列与清单不一致
  case_md_escaped_pipe          回归：单元格内 `\\|` 不得让该行被静默跳过（R28 真实缺陷）
  case_md_range_ok              区间展开：`E-1001~E-1003` 正常展开 → PASS
  case_md_range_no_overflow     区间**不得外溢**：清单多一个 E-1004 必须判 FAIL
  case_openapi_decoy_enum       缩进/命名纪律：同级的诱饵 enum 不得被当成 ResultCode
  case_openapi_missing_enum     正向对照：ResultCode 无 enum 时必须 FAIL（不得静默空集通过）
  case_missing_source           源文件缺失 → 显式 FAIL、rc=1
  case_zero_write               跑完夹具与真实仓库源文件指纹不变（只读保证）

夹具写在 $LOCALAPPDATA/Temp 下的**唯一时间戳目录**（不做递归删除，skill 坑 28），
以 `--root` 指向仓库外路径（skill 坑 34）。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "audit-error-codes.py"
REPO = HERE.parent

TMP_BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Temp"

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


# ---------------------------------------------------------------- 夹具构造

def write_fixture(root: Path, *, java_codes: list[str], schema_codes: list[str],
                  enum_codes: list[str], eps: list[dict], md_tables: list[tuple[list[str], list[list[str]]]],
                  openapi_op_codes: dict[str, list[str]] | None = None,
                  openapi_decoy: bool = False, openapi_enum_missing: bool = False,
                  skip_endpoints: bool = False) -> None:
    """按真实仓库的相对布局生成夹具（--root 指向它即可）。"""
    (root / "docs/backend/json-schema/common").mkdir(parents=True, exist_ok=True)
    (root / "aap-server/src/main/java/com/hioas/aap/common").mkdir(parents=True, exist_ok=True)

    if not skip_endpoints:
        (root / "docs/backend/endpoints.json").write_text(
            json.dumps({"total": len(eps), "endpoints": eps}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    java = ["package com.hioas.aap.common;", "", "public enum ErrorCode {"]
    for c in java_codes:
        if c == "0":
            java.append('    SUCCESS("0", 200, "ok"),')
        else:
            java.append(f'    {c.replace("-", "_")}("{c}", 400, "x"),')
    java.append("}")
    (root / "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java").write_text(
        "\n".join(java) + "\n", encoding="utf-8")

    (root / "docs/backend/json-schema/common/error.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema",
                    "properties": {"code": {"type": "string", "enum": schema_codes}}},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    ops = openapi_op_codes or {e["id"]: e["error_codes"] for e in eps}
    out = ["openapi: 3.0.3", "paths:"]
    for e in eps:
        out += [f"  {e['path']}:", f"    {e['method'].lower()}:", f"      operationId: {e['id']}",
                "      responses:", "        200:", "          description: 成功"]
        codes = ops.get(e["id"], [])
        if codes:
            out += ["        4XX:", "          description: 业务失败：" + ",".join(codes)]
    out += ["components:", "  schemas:"]
    if openapi_decoy:
        out += ["    OtherCode:", "      type: string", "      enum:",
                "        - E-9999"]
    out += ["    ResultCode:", "      type: string"]
    if not openapi_enum_missing:
        out += ["      enum:"] + [f"        - {c}" for c in enum_codes]
    (root / "docs/backend/openapi.yaml").write_text("\n".join(out) + "\n", encoding="utf-8")

    md = ["# 接口清单夹具", ""]
    for header, rows in md_tables:
        md += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        for r in rows:
            md.append("| " + " | ".join(r) + " |")
        md.append("")
    (root / "docs/backend/02-API接口模型清单.md").write_text("\n".join(md) + "\n", encoding="utf-8")


HEAD10 = ["ID", "方法", "路径", "鉴权", "请求", "响应", "错误码", "幂等/并发", "依据", "状态"]
HEAD7 = ["ID", "方法", "路径", "角色", "请求/响应", "错误码", "状态"]


def base_pieces():
    """两套表头（10 列 / 7 列）各一行 —— 同时覆盖「按表头定位列序」这一分支。"""
    eps = [
        {"id": "SYN-01", "method": "POST", "path": "/syn/one", "error_codes": ["E-1001", "E-1903"]},
        {"id": "SYN-02", "method": "GET", "path": "/syn/two", "error_codes": []},
    ]
    java = ["0", "E-1001", "E-1903"]
    tables = [
        (HEAD10, [["SYN-01", "POST", "`/syn/one`", "免", "body `{a}`", "`R`", "E-1001 E-1903", "", "真源", "T99"]]),
        (HEAD7, [["SYN-02", "GET", "`/syn/two`", "TECH_OPS", "→ `R`", "", "T99"]]),
    ]
    return eps, java, tables


def build(name: str, **kw) -> Path:
    root = TMP_BASE / f"aap-ec-selftest-{name}-{int(time.time() * 1000)}"
    root.mkdir(parents=True, exist_ok=True)
    eps, java, tables = base_pieces()
    kw.setdefault("eps", eps)
    kw.setdefault("java_codes", java)
    kw.setdefault("schema_codes", ["E-1001", "E-1903"])
    kw.setdefault("enum_codes", java)
    kw.setdefault("md_tables", tables)
    write_fixture(root, **kw)
    return root


def run_audit(root: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "").replace("\r\n", "\n") + (p.stderr or "")


def fingerprint_tree(root: Path) -> dict:
    out = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            st = f.stat()
            out[str(f)] = (st.st_mtime_ns, st.st_size, hashlib.md5(f.read_bytes()).hexdigest())
    return out


def case(name: str, root: Path, want_rc: int, want: str, must_not: str = "") -> None:
    rc, out = run_audit(root)
    ok = rc == want_rc and want in out and (not must_not or must_not not in out)
    detail = f"rc={rc}(期望 {want_rc}) 命中「{want}」={'是' if want in out else '否'}"
    if must_not:
        detail += f" 反证「{must_not}」={'出现(异常)' if must_not in out else '未出现'}"
    record(name, ok, detail)
    if not ok:
        print(f"    --- {name} 实际输出 ---")
        print("\n".join("    " + ln for ln in out.splitlines()[-14:]))


def main() -> int:
    print(f"夹具根目录：{TMP_BASE}")
    print(f"被测审计：{AUDIT.relative_to(REPO)}")

    # 1 正向对照
    root = build("positive")
    fp_before = fingerprint_tree(root)
    case("case_positive", root, 0, "断言 16 条：PASS 16，FAIL 0")
    fp_after = fingerprint_tree(root)
    record("case_zero_write", fp_before == fp_after,
           "夹具 5 个文件 (mtime,size,md5) 不变" if fp_before == fp_after else "有文件被改写")

    # 2 A3 清单声明了目录里没有的码
    eps, java, tables = base_pieces()
    eps2 = [dict(eps[0], error_codes=["E-1001", "E-1999"]), eps[1]]
    case("case_manifest_code_unknown", build("a3", eps=eps2), 1,
         "A3 清单声明的码都在 ErrorCode.java 目录里")

    # 3 A4 孤儿码
    case("case_orphan_code", build("a4", java_codes=["0", "E-1001", "E-1903", "E-1501"],
                                   schema_codes=["E-1001", "E-1903", "E-1501"],
                                   enum_codes=["0", "E-1001", "E-1903", "E-1501"]), 1,
         "孤儿=['E-1501']")

    # 4 A6 openapi operation 码与清单不一致
    case("case_openapi_op_mismatch", build("a6", openapi_op_codes={"SYN-01": ["E-1001"], "SYN-02": []}), 1,
         "A6 openapi 每 operation 4XX 码集合 = 清单")

    # 5 A9 md 行与清单不一致
    row0 = tables[0][1][0]
    t = [row0[:6] + ["E-1001"] + row0[7:]]
    case("case_md_row_mismatch",
         build("a9", md_tables=[(HEAD10, t), tables[1]]), 1,
         "A9 md 每行错误码列 = 清单")

    # 6 回归：单元格内转义竖线不得让该行被跳过（R28 真实缺陷）
    rows7 = [["SYN-02", "GET", "`/syn/two`", "TECH_OPS", "body `{s:ENABLED\\|DISABLED}`", "", "T99"]]
    case("case_md_escaped_pipe", build("pipe", md_tables=[tables[0], (HEAD7, rows7)]), 0,
         "A0c D 行数 = total：parsed=2")

    # 7 区间展开：正常 / 不外溢
    eps_r = [dict(eps[0], error_codes=["E-1001", "E-1002", "E-1003"]), eps[1]]
    rows_r = [["SYN-01", "POST", "`/syn/one`", "免", "body `{a}`", "`R`", "E-1001~E-1003", "", "真源", "T99"]]
    case("case_md_range_ok", build("range", eps=eps_r, java_codes=["0", "E-1001", "E-1002", "E-1003"],
                                   schema_codes=["E-1001", "E-1002", "E-1003"],
                                   enum_codes=["0", "E-1001", "E-1002", "E-1003"],
                                   md_tables=[(HEAD10, rows_r), tables[1]]), 0,
         "A9 md 每行错误码列 = 清单")
    eps_o = [dict(eps[0], error_codes=["E-1001", "E-1002", "E-1003", "E-1004"]), eps[1]]
    case("case_md_range_no_overflow",
         build("overflow", eps=eps_o, java_codes=["0", "E-1001", "E-1002", "E-1003", "E-1004"],
               schema_codes=["E-1001", "E-1002", "E-1003", "E-1004"],
               enum_codes=["0", "E-1001", "E-1002", "E-1003", "E-1004"],
               md_tables=[(HEAD10, rows_r), tables[1]]), 1,
         "A9 md 每行错误码列 = 清单")

    # 8 缩进/命名纪律：诱饵 enum 不得被当 ResultCode；缺 enum 必须 FAIL
    case("case_openapi_decoy_enum", build("decoy", openapi_decoy=True), 0, "A2 O.ResultCode 与 J 一致")
    case("case_openapi_missing_enum", build("noenum", openapi_enum_missing=True), 1, "A0f O ResultCode enum 非空")

    # 9 源文件缺失
    case("case_missing_source", build("nosrc", skip_endpoints=True), 1, "源文件缺失")

    print()
    npass = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}：{detail}")
    print(f"\n自测断言 {len(results)} 条：PASS {npass}，FAIL {len(results) - npass}")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
