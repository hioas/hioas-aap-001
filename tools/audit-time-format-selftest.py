#!/usr/bin/env python3
"""`tools/audit-time-format.py` 的负向自测（R33，只读夹具，不碰仓库）。

纪律（skill 坑 32 / 34 / 41 / 46 / 57 / 66）：
  * **每个判定分支一条反例**：A0b/A0c（格式串漂移）、A0d（辅助方法体漂移）、A1b（未包裹的响应时间值）、
    A1c（内部读取超阈值）、A2（文本直出）、A3b（响应 DTO 类型）、A4b（客户端类型）、A5b（schema 类型）；
  * **正向对照**：合规夹具上 15 条断言必须全 PASS（只造反例时「一直在报错」会被当成合格）；
  * **解析器失效**：空夹具目录必须让 5 条正向对照断言变红（而不是静默 PASS）；
  * **注入缺陷判别力实测**：每个反例断言「恰好命中的断言名」，并额外断言**注入真的改到了源码**
    （`mutate()` 返回未命中锚点列表，非空即失败）——否则空转通过（坑 41）；
  * 夹具在**仓库外**（坑 34）、脚本**零写副作用**（运行前后夹具指纹不变，坑 39）。

用法：python tools/audit-time-format-selftest.py
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "audit-time-format.py"

SERVICE = "aap-server/src/main/java/com/hioas/aap/x/FooService.java"
SERVICE2 = "aap-server/src/main/java/com/hioas/aap/x/BarService.java"
VIEWS = "aap-server/src/main/java/com/hioas/aap/x/FooViews.java"
CLIENT = "aap-client/src/api/foo.ts"
SCHEMA = "docs/backend/json-schema/models/foo.schema.json"

PATTERN = "yyyy-MM-dd'T'HH:mm:ss'Z'"

SERVICE_SRC = f"""package com.hioas.aap.x;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

class FooService {{
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("{PATTERN}");

    Item map(java.sql.ResultSet rs) throws java.sql.SQLException {{
        return new Item(rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
    }}

    private static String rfc3339(OffsetDateTime value) {{
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }}
}}
"""

VIEWS_SRC = """package com.hioas.aap.x;

import com.fasterxml.jackson.annotation.JsonProperty;

class FooViews {
    public record Item(@JsonProperty("created_at") String createdAt) {
    }
}
"""

CLIENT_SRC = """export interface FooRaw {
  created_at?: string
}

export const parse = (v?: string | null) => (v ? new Date(v) : null)
"""

SCHEMA_SRC = """{
  "title": "foo",
  "type": "object",
  "properties": {
    "created_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "RFC3339 UTC"
    }
  }
}
"""


class Result:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.npass = 0
        self.nfail = 0

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.lines.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if ok:
            self.npass += 1
        else:
            self.nfail += 1
        return ok


def write_fixture(root: Path) -> None:
    # 两份出口副本（真实项目实测 14 份）——A0b/A0c/A0d 的漂移只可能发生在「多副本」场景
    service2 = SERVICE_SRC.replace("class FooService", "class BarService")
    for rel, body in ((SERVICE, SERVICE_SRC), (SERVICE2, service2), (VIEWS, VIEWS_SRC),
                      (CLIENT, CLIENT_SRC), (SCHEMA, SCHEMA_SRC)):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def mutate(root: Path, rel: str, pairs: list[tuple[str, str]]) -> list[str]:
    """就地替换；返回未命中的锚点（非空 = 注入失败 → 必须报错，坑 66）。"""
    p = root / rel
    text = p.read_text(encoding="utf-8")
    missed = []
    for old, new in pairs:
        if old not in text:
            missed.append(old)
            continue
        text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    return missed


def fingerprint(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            st = p.stat()
            out[str(p)] = (st.st_mtime_ns, st.st_size, hashlib.md5(p.read_bytes()).hexdigest())
    return out


def run_audit(root: Path) -> tuple[int, str]:
    env = dict(os.environ)
    proc = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout + proc.stderr


def assert_red(out: str, expect: list[str]) -> tuple[bool, str]:
    """每个预期断言名必须出现 FAIL 行，且**其余**断言仍为 PASS（判别力不越界）。"""
    fails = [ln for ln in out.splitlines() if ln.startswith("[FAIL]")]
    names = [ln.split("]", 1)[1].strip().split(" —")[0] for ln in fails]
    missing = [e for e in expect if not any(n.startswith(e) for n in names)]
    extra = [n for n in names if not any(n.startswith(e) for e in expect)]
    ok = not missing and not extra
    detail = f"FAIL 断言={names}（预期 {expect}）"
    if missing:
        detail += f" 缺 {missing}"
    if extra:
        detail += f" 越界 {extra}"
    return ok, detail


def main() -> int:
    r = Result()
    base = Path(tempfile.mkdtemp(prefix="aap-timefmt-selftest-"))
    r.lines.append(f"# audit-time-format 负向自测（夹具根={base}，仓库外，坑 34）")

    try:
        # ---------- 0. 合规夹具：正向对照必须全绿 ----------
        good = base / "good"
        write_fixture(good)
        before = fingerprint(good)
        rc, out = run_audit(good)
        r.check("C0 合规夹具：审计 rc=0 且 15 条断言全 PASS（正向对照）",
                rc == 0 and "PASS 15，FAIL 0" in out, f"rc={rc}；{out.strip().splitlines()[-1]}")
        r.check("C1 审计对夹具零写副作用（运行前后指纹一致）",
                before == fingerprint(good), "夹具文件被改写")

        # ---------- 1. 每个判定分支一条反例 ----------
        cases: list[tuple[str, str, list[tuple[str, str]], list[str]]] = [
            ("C2 A0b/A0c 格式串漂移（第二份出口用毫秒精度）", SERVICE2,
             [(PATTERN, "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")], ["A0b", "A0c"]),
            ("C3 A0d 辅助方法体漂移（少了 withOffsetSameInstant）", SERVICE2,
             [("return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));",
               "return value == null ? null : RFC3339.format(value);")], ["A0d"]),
            ("C4 A1b 响应时间值未包裹出口（直接进 DTO 构造器）", SERVICE,
             [('return new Item(rfc3339(rs.getObject("created_at", OffsetDateTime.class)));',
               'return new Item(rs.getObject("created_at", OffsetDateTime.class));')], ["A1b"]),
            ("C5 A1c 内部读取超阈值（4 处仅判空用途）", SERVICE,
             [("private static String rfc3339(OffsetDateTime value) {",
               "void internal(java.sql.Connection c) {\n"
               "        c.createStatement();\n"
               "        jdbc.query(\"select read_at\", (rs, n) -> rs.getObject(\"read_at\", OffsetDateTime.class));\n"
               "        jdbc.query(\"select read_at\", (rs, n) -> rs.getObject(\"read_at\", OffsetDateTime.class));\n"
               "        jdbc.query(\"select read_at\", (rs, n) -> rs.getObject(\"read_at\", OffsetDateTime.class));\n"
               "        jdbc.query(\"select read_at\", (rs, n) -> rs.getObject(\"read_at\", OffsetDateTime.class));\n"
               "    }\n\n"
               "    private static String rfc3339(OffsetDateTime value) {")], ["A1c"]),
            ("C6 A2 时间列按数据库文本直出（getString）", SERVICE,
             [('rs.getObject("created_at", OffsetDateTime.class)', 'rs.getString("created_at")')],
             ["A2"]),
            ("C7 A3b 响应 DTO 时间字段声明为 OffsetDateTime", VIEWS,
             [('@JsonProperty("created_at") String createdAt', '@JsonProperty("created_at") OffsetDateTime createdAt')],
             ["A3b"]),
            ("C8 A4b 客户端时间字段声明为 number", CLIENT,
             [("created_at?: string", "created_at?: number")], ["A4b"]),
            ("C9 A5b schema 时间字段类型写成 number", SCHEMA,
             [('"type": ["string", "null"],\n      "format": "date-time"',
               '"type": ["number", "null"],\n      "format": "date-time"')], ["A5b"]),
        ]
        for idx, (name, rel, pairs, expect) in enumerate(cases):
            case = base / f"case{idx}"
            write_fixture(case)
            missed = mutate(case, rel, pairs)
            r.check(f"{name} —— 注入锚点全部命中（坑 66：注入必须真的改到源码）",
                    not missed, f"未命中锚点 {missed}")
            rc, out = run_audit(case)
            ok, detail = assert_red(out, expect)
            r.check(f"{name} —— 恰好命中预期断言且 rc=1", rc == 1 and ok, f"rc={rc}；{detail}")

        # ---------- 2. 解析器失效必须变红（不是静默 PASS） ----------
        empty = base / "empty"
        empty.mkdir(parents=True, exist_ok=True)
        rc, out_empty = run_audit(empty)
        ok, detail = assert_red(out_empty, ["A0a", "A0b", "A0c", "A0d", "A1a", "A3a", "A4a", "A5a"])
        r.check("C10 空夹具：8 条正向对照/唯一性断言必须变红（解析器失效不得判 PASS）",
                rc == 1 and ok, f"rc={rc}；{detail}")

        # ---------- 3. 仓库外夹具根可显示路径（坑 34） ----------
        rc, out_good = run_audit(good)
        norm = out_good.replace("\\", "/")
        base_s = str(base).replace(os.sep, "/")
        with_base = [ln for ln in norm.splitlines() if base_s in ln]
        r.check("C11 --root 指向仓库外时审计能正常输出（文件路径展示为相对路径，不抛 ValueError）",
                rc == 0 and SERVICE in norm and with_base and all(ln.startswith("# ") for ln in with_base),
                f"含夹具绝对路径的非表头行 {[ln[:80] for ln in with_base if not ln.startswith('# ')]}")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print("\n".join(r.lines))
    print(f"\n自测断言 {r.npass + r.nfail} 条：PASS {r.npass}，FAIL {r.nfail}")
    return 0 if r.nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
