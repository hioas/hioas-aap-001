#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R57 抽查脚本的负向自测（夹具在 <tmp>/aap-r57-spotcheck-fixtures/，脚本在 <tmp>/aap-r57-spotcheck/，坑 106）。

覆盖：
  1) 合规夹具 rc=0 且 FAIL 0（正向对照，坑 75/98）；
  2) 每个判定分支一条反例：A1 / A2 / A3 / A4 各一条点名 FAIL；
  3) 空夹具必须变红并点名 A0a…A0j（解析器失效必须可见，坑 46/128）；
  4) **花括号解析回归守卫**（v1 用 match_paren 配 `{}` → 多字段只解析到第一个）：夹具断言可选 token = 2；
  5) 注入缺陷判别力：3 组注入，断言「注入真的改到源码」（锚点命中，坑 66/94）＋「FAIL 集合恰好新增/减少目标断言」
     （基线用 `ok_out` 专用变量，坑 93；FAIL 按断言前缀比对，坑 82）；
  6) 真实仓库只读守卫 + 夹具零写副作用（坑 39/40）。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TMP = Path(r"C:/Users/laitz/AppData/Local/Temp")
SCRIPT = TMP / "aap-r57-spotcheck" / "spotcheck-required-R57.py"
FX = TMP / "aap-r57-spotcheck-fixtures"
REAL = Path(r"E:/workspaces/hioas/hioas-aap-001")

MD_OK = """# demo 清单

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| DEMO-01 | POST | `/demo` | ✅ | body `{name, tags?}` | `Demo` | E-1001 | | 真源 | T99 |
| DEMO-02 | POST | `/demo/{id}/submit` | ✅ | body：`name` `note?` | `Demo` | E-1001 | | 真源 | T99 |
| DEMO-03 | GET | `/demo` | ✅ | q：`page` `pageSize` | `{items}` | | | 真源 | T99 |
"""

SCHEMA_OK = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "demo-create",
    "required": ["name"],
    "properties": {
        "name": {"type": "string"},
        "note": {"type": ["string", "null"]},
        "tags": {"type": ["array", "null"]},
    },
}

ENDPOINTS_OK = [
    {"id": "DEMO-01", "method": "POST", "path": "/api/v1/demo", "request_model": "demo-create"},
    {"id": "DEMO-02", "method": "POST", "path": "/api/v1/demo/{id}/submit", "request_model": "demo-create"},
    {"id": "DEMO-03", "method": "GET", "path": "/api/v1/demo", "request_model": None},
]

POM_OK = """<project>
  <dependencies>
    <dependency>
      <groupId>com.networknt</groupId>
      <artifactId>json-schema-validator</artifactId>
      <version>1.5.6</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""

CTRL_OK = """package com.hioas.aap.demo;

@RestController
@RequestMapping("/api/v1/demo")
public class DemoController {
    public record DemoRequest(
            @NotBlank(message = "缺少 name") String name,
            String note) {
    }

    @PostMapping
    public ApiEnvelope<Object> create(@Valid @RequestBody DemoRequest request) {
        return ApiEnvelope.ok(service.create(request));
    }

    @PostMapping("/{id}/submit")
    public ApiEnvelope<Object> submit(@RequestBody DemoRequest request) {
        return ApiEnvelope.ok(service.submit(request));
    }
}
"""

SVC_OK = """package com.hioas.aap.demo;

public class DemoService {
    public Object create(DemoRequest request) {
        if (request.name() == null || request.name().isBlank()) {
            throw new IllegalStateException("name");
        }
        return request;
    }
}
"""

DDL_OK = """create table if not exists aap_demo (
    id      bigint primary key,
    name    varchar(32) not null,
    note    varchar(64)
);
"""

TEST_OK = """package com.hioas.aap.demo;

class DemoContractTest {
    void t() {
        post("/demo", Map.of("name", "x"));
    }
}
"""


def write_repo(base: Path, md=MD_OK, schema=SCHEMA_OK, ctrl=CTRL_OK, svc=SVC_OK, ddl=DDL_OK):
    if base.exists():
        shutil.rmtree(base)
    (base / "docs/backend/json-schema/requests").mkdir(parents=True)
    (base / "aap-server/src/main/java/com/hioas/aap/demo").mkdir(parents=True)
    (base / "aap-server/src/main/resources/db/migration").mkdir(parents=True)
    (base / "aap-server/src/test/java/com/hioas/aap/demo").mkdir(parents=True)
    (base / "docs/backend/02-API接口模型清单.md").write_text(md, encoding="utf-8", newline="\n")
    (base / "docs/backend/endpoints.json").write_text(json.dumps(ENDPOINTS_OK, ensure_ascii=False, indent=2),
                                                      encoding="utf-8", newline="\n")
    (base / "docs/backend/json-schema/requests/demo-create.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (base / "aap-server/pom.xml").write_text(POM_OK, encoding="utf-8", newline="\n")
    (base / "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java").write_text(ctrl, encoding="utf-8", newline="\n")
    (base / "aap-server/src/main/java/com/hioas/aap/demo/DemoService.java").write_text(svc, encoding="utf-8", newline="\n")
    (base / "aap-server/src/main/resources/db/migration/V1__baseline.sql").write_text(ddl, encoding="utf-8", newline="\n")
    (base / "aap-server/src/test/java/com/hioas/aap/demo/DemoContractTest.java").write_text(TEST_OK, encoding="utf-8", newline="\n")


def run(script: Path, root: Path, timeout=180):
    p = subprocess.run([sys.executable, str(script), "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fails(out: str) -> set:
    """FAIL 明细的**断言名**集合（按前缀比对，坑 82/97：方括号内允许空格）。"""
    res = set()
    for line in out.splitlines():
        m = re.match(r"^\s*\[FAIL\s*\]\s*(\S+)", line)
        if m:
            res.add(m.group(1))
    return res


def has(out: str, token: str) -> bool:
    return any(f.startswith(token) for f in fails(out))


def main() -> int:
    npass = nfail = 0
    lines = []

    def chk(name, ok, detail=""):
        nonlocal npass, nfail
        if ok:
            npass += 1
        else:
            nfail += 1
        lines.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"：{detail}" if detail else ""))
        return ok

    FX.mkdir(parents=True, exist_ok=True)

    # ---------- 1) 合规夹具
    ok_dir = FX / "ok"
    write_repo(ok_dir)
    rc, out = run(SCRIPT, ok_dir)
    (FX / "ok-output.txt").write_text(out, encoding="utf-8", newline="\n")
    chk("ok 夹具 rc=0", rc == 0, f"rc={rc}")
    chk("ok 夹具 FAIL 0（正向对照：判据不瞎报）", not fails(out), f"FAIL={sorted(fails(out))}")
    chk("ok 夹具解析到 2 个可选 token（**花括号回归守卫**：v1 用 match_paren 配 {} → 只解析到第一个字段）",
        "可选 token 2" in out, [l for l in out.splitlines() if "A0b" in l][:1])

    # ---------- 2) 分支反例
    cases = [
        ("bad-a1", dict(md=MD_OK.replace("`{name, tags?}`", "`{name?, tags?}`")), "A1",
         "md 标可选而 schema.required 含之"),
        ("bad-a2", dict(schema={**SCHEMA_OK, "properties": {**SCHEMA_OK["properties"],
                                                          "name": {"type": ["string", "null"]}}}), "A2",
         "required ∧ nullable 自相矛盾"),
        ("bad-a3", dict(ctrl=CTRL_OK.replace('@NotBlank(message = "缺少 name") ', ""),
                        svc=SVC_OK.replace("if (request.name() == null || request.name().isBlank()) {\n            throw new IllegalStateException(\"name\");\n        }\n", "")),
         "A3", "schema.required 但实现侧零校验"),
        ("bad-a4", dict(ctrl=CTRL_OK.replace("String note)", '@NotBlank String note)')), "A4",
         "实现声明必填而 schema.required 未声明"),
    ]
    for name, kw, token, desc in cases:
        d = FX / name
        write_repo(d, **kw)
        rc, out = run(SCRIPT, d)
        (FX / f"{name}-output.txt").write_text(out, encoding="utf-8", newline="\n")
        chk(f"{name}：点名 {token}（{desc}）", rc == 1 and has(out, token),
            f"rc={rc} FAIL={sorted(fails(out))}")

    # ---------- 3) 空夹具
    empty = FX / "empty"
    if empty.exists():
        shutil.rmtree(empty)
    empty.mkdir(parents=True)
    rc, out = run(SCRIPT, empty)
    (FX / "empty-output.txt").write_text(out, encoding="utf-8", newline="\n")
    missing = [t for t in ("A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h", "A0i", "A0j") if not has(out, t)]
    chk("空夹具 rc=1 且 A0a…A0j 全部点名（解析器失效必须可见，坑 46/128）", rc == 1 and not missing,
        f"rc={rc} 未点名={missing}")

    # ---------- 4) 真实仓库基线
    rc_real, ok_out = run(SCRIPT, REAL)
    (FX / "real-output.txt").write_text(ok_out, encoding="utf-8", newline="\n")
    base_fails = fails(ok_out)
    chk("真实仓库跑通且解析到 FAIL 明细 > 0（正向对照，坑 97）", rc_real == 1 and len(base_fails) > 0,
        f"rc={rc_real} FAIL={sorted(base_fails)}")
    a0b_real = re.search(r"A0b[^\n]*可选 token (\d+)", ok_out)
    base_opt = int(a0b_real.group(1)) if a0b_real else -1
    chk("真实仓库 A0b 可选 token ≥ 10（v1 只有 6，是花括号 bug 的指纹）", base_opt >= 10, f"可选 token={base_opt}")

    # ---------- 5) 注入缺陷（判别力）
    src = SCRIPT.read_text(encoding="utf-8")
    injections = [
        ("mut-matchparen", "e = match_pair(brace, 0)",
         "e = match_paren(brace, 0)",
         "把花括号配对改回圆括号 → A0b 可选 token 必须下降（花括号回归守卫有牙齿）"),
        ("mut-ann-format", 'REQUIRED_ANN = ("NotBlank", "NotNull", "NotEmpty")',
         'REQUIRED_ANN = ("@NotBlank", "@NotNull", "@NotEmpty")',
         "把注解白名单写成带 @ 的形式（v1 的 bug）→ A0f 必须转红（正向对照有效）"),
        ("mut-evidence", 'EVIDENCE_TIERS = {"注解", "守卫(直接)", "守卫(别名·直接)"}',
         'EVIDENCE_TIERS = {"注解", "守卫(直接)", "守卫(别名·直接)", "弱证据(跨包同名形参，不作数)", "无"}',
         "把「无证据」也算作证据 → A3 必须消失（证明 A3 不是空转）"),
    ]
    for name, old, new, desc in injections:
        mutated = src.replace(old, new)
        hit = (mutated != src) and (mutated.count(new) >= src.count(old))
        chk(f"{name}：注入真的改到源码（锚点命中，坑 66/94）", hit, f"锚点 {old!r} 命中={mutated != src}")
        if not hit:
            continue
        mp = TMP / "aap-r57-spotcheck" / f"{name}.py"
        mp.write_text(mutated, encoding="utf-8", newline="\n")
        rc_m, out_m = run(mp, REAL)
        (FX / f"{name}-output.txt").write_text(out_m, encoding="utf-8", newline="\n")
        f_m = fails(out_m)
        if name == "mut-matchparen":
            m = re.search(r"A0b[^\n]*可选 token (\d+)", out_m)
            opt_m = int(m.group(1)) if m else -1
            chk(f"{name}：{desc}", opt_m < base_opt, f"注入后可选 token={opt_m}（基线 {base_opt}）")
        elif name == "mut-ann-format":
            chk(f"{name}：{desc}", has(out_m, "A0f") and not has(ok_out, "A0f"),
                f"注入后新增 FAIL={sorted(f_m - base_fails)}")
        else:
            chk(f"{name}：{desc}", "A3" not in f_m and "A3" in base_fails,
                f"注入后消失 FAIL={sorted(base_fails - f_m)}")

    # ---------- 6) 零写副作用
    before = {p: p.stat().st_mtime_ns for p in (REAL / "docs/backend/json-schema/requests").glob("*.schema.json")}
    run(SCRIPT, REAL)
    after = {p: p.stat().st_mtime_ns for p in (REAL / "docs/backend/json-schema/requests").glob("*.schema.json")}
    chk("真实仓库只读（被读 schema 文件 mtime 未变）", before == after, f"变化={[str(k) for k in before if before[k] != after.get(k)]}")

    print("\n".join(lines))
    print(f"\n== 自测断言：PASS {npass} / FAIL {nfail} ==")
    print(f"夹具目录：{FX}")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
