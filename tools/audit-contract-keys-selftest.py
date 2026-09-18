#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""`tools/audit-contract-keys.py` 的**负向自测**（踩坑 32：判定有几个分支，自测就要有几条反例）。

为什么必须有它：「0 发现」无法区分「真干净」与「匹配逻辑全错」（踩坑 29）。
本脚本对审计的每个判定分支各造一条反例（必须报 FAIL），再给一组**正向对照**
（全部正确 → 必须全 PASS、rc=0），否则「一直在报错」也会被当成合格。

分支覆盖：
  A1 正向：OpenAPI 集合键名 items            → 必须 PASS
  A2 反向：OpenAPI 集合键名 list             → 必须 FAIL 并点名该 operationId
  B1 反向：带 pageSize 但响应未 PageMeta 包装 → 必须 FAIL 并点名该 operationId
  C1 反向：page.schema.json 只写 list        → 必须 FAIL（required/properties/旧键名三分支）
  D1 反向：PageResult 首分量为 list          → 必须 FAIL
  E1 反向：客户端接口只声明 records          → 必须 FAIL
  E2 正向：客户端接口声明 items              → 必须 PASS
  F1 反向：清单 §0 未写 data:{items:        → 必须 FAIL

另外校验：审计脚本对夹具**零写副作用**（踩坑 39：mtime 变了而 md5 没变也是写）。

用法： python tools/audit-contract-keys-selftest.py
退出码：0 = 全部断言 PASS；1 = 有断言失败。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "audit-contract-keys.py")

OPENAPI_HEAD = """openapi: 3.1.0
info:
  title: fixture
  version: "1.0"
paths:
  /demo:
    get:
      operationId: DEMO-01
      parameters:
        - name: page
          in: query
          schema:
            type: integer
        - name: pageSize
          in: query
          schema:
            type: integer
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/Envelope"
                  - type: object
                    properties:
                      data:
{WRAPPER}
"""

# 30 空格 = 集合属性名缩进（与生成器 yaml_dump 一致）
WRAPPER_PAGEMETA = """                        allOf:
                          - $ref: "#/components/schemas/PageMeta"
                          - type: object
                            properties:
{KEY}:
                                type: array
                                items:
                                  $ref: "#/components/schemas/Demo"
"""
WRAPPER_PLAIN = """                        $ref: "#/components/schemas/Demo"
"""


def openapi_text(key: str | None) -> str:
    if key is None:
        return OPENAPI_HEAD.replace("{WRAPPER}", WRAPPER_PLAIN)
    wrapper = WRAPPER_PAGEMETA.replace("{KEY}", " " * 30 + key)
    return OPENAPI_HEAD.replace("{WRAPPER}", wrapper)


def page_schema_text(key: str) -> str:
    return json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "page",
        "required": [key, "page", "pageSize", "total"],
        "properties": {key: {"type": "array"}, "page": {"type": "integer"},
                       "pageSize": {"type": "integer"}, "total": {"type": "integer"}},
        "type": "object",
    }, ensure_ascii=False, indent=2)


def page_result_text(first: str) -> str:
    return (
        "package com.hioas.aap.common;\n\nimport java.util.List;\n\n"
        f"public record PageResult<T>(List<T> {first}, int page, int pageSize, long total) {{\n}}\n"
    )


def client_text(field: str) -> str:
    return (
        "import { http } from './http'\n\n"
        "export interface DemoListRaw {\n"
        "  total?: number\n"
        f"  {field}?: unknown[]\n"
        "}\n\n"
        "export const demoApi = {\n"
        "  list() {\n    return http<DemoListRaw>('/demo')\n  }\n}\n"
    )


def manifest_text(key: str) -> str:
    return (
        "# API接口模型清单\n\n## §0 通用约定\n\n"
        f"| 分页 | 请求 `page` / `pageSize`；响应 `data:{{{key}:[],page,pageSize,total}}` |\n"
    )


def write_fixture(root: str, *, key: str | None = "items", wrapper_key: str | None = "items",
                  page_key: str = "items", result_first: str = "items",
                  client_field: str = "items", manifest_key: str = "items") -> None:
    """按参数铺设一套夹具（默认全部正确）。"""
    os.makedirs(os.path.join(root, "docs", "backend", "json-schema", "common"), exist_ok=True)
    os.makedirs(os.path.join(root, "aap-server", "src", "main", "java", "com", "hioas", "aap",
                             "common"), exist_ok=True)
    os.makedirs(os.path.join(root, "aap-client", "src", "api"), exist_ok=True)

    with open(os.path.join(root, "docs", "backend", "openapi.yaml"), "w", encoding="utf-8") as fh:
        fh.write(openapi_text(wrapper_key))
    with open(os.path.join(root, "docs", "backend", "json-schema", "common",
                           "page.schema.json"), "w", encoding="utf-8") as fh:
        fh.write(page_schema_text(page_key))
    with open(os.path.join(root, "aap-server", "src", "main", "java", "com", "hioas", "aap",
                           "common", "PageResult.java"), "w", encoding="utf-8") as fh:
        fh.write(page_result_text(result_first))
    with open(os.path.join(root, "aap-client", "src", "api", "demo.ts"), "w", encoding="utf-8") as fh:
        fh.write(client_text(client_field))
    with open(os.path.join(root, "docs", "backend", "02-API接口模型清单.md"), "w",
              encoding="utf-8") as fh:
        fh.write(manifest_text(manifest_key))


def run_audit(root: str) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, AUDIT, "--root", root, "--json"],
                          capture_output=True, text=True, encoding="utf-8")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"rows": [], "failed": -1, "raw": proc.stdout, "err": proc.stderr}
    return proc.returncode, payload


def fails_for(payload: dict, check: str) -> list[dict]:
    return [r for r in payload.get("rows", []) if r.get("check") == check and not r.get("ok")]


def passes_for(payload: dict, check: str) -> list[dict]:
    return [r for r in payload.get("rows", []) if r.get("check") == check and r.get("ok")]


def fingerprint(root: str) -> dict:
    out = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            p = os.path.join(dirpath, name)
            with open(p, "rb") as fh:
                data = fh.read()
            st = os.stat(p)
            out[os.path.relpath(p, root)] = (st.st_mtime_ns, st.st_size,
                                             hashlib.md5(data).hexdigest())
    return out


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))

    base = os.path.join(tempfile.gettempdir(),
                        "aap-keyaudit-selftest-" + str(os.getpid()))
    if os.path.isdir(base):
        shutil.rmtree(base)
    os.makedirs(base, exist_ok=True)

    try:
        # ---------- 正向对照：全部正确 → 必须全 PASS、rc=0
        ok_root = os.path.join(base, "ok")
        write_fixture(ok_root)
        fp_before = fingerprint(ok_root)
        rc, payload = run_audit(ok_root)
        check("A1 正向 OpenAPI 集合键名 items → rc=0",
              rc == 0 and payload.get("failed") == 0,
              f"rc={rc} failed={payload.get('failed')} "
              f"raw={str(payload.get('raw'))[:160]!r} err={str(payload.get('err'))[:160]!r}")
        check("A1b 正向 A 分支有 PASS 记录（证明解析器真的解析到了）",
              len(passes_for(payload, "A")) == 1,
              f"A PASS 条数={len(passes_for(payload, 'A'))}")
        check("E2 正向 客户端接口声明 items → E 分支 PASS",
              len(passes_for(payload, "E")) == 1,
              f"E PASS 条数={len(passes_for(payload, 'E'))}")

        # ---------- 零写副作用（踩坑 39/40）
        fp_after = fingerprint(ok_root)
        check("Z1 审计对夹具零写副作用（mtime_ns/size/md5 全等）",
              fp_before == fp_after,
              "有文件被改写：" + str([k for k in fp_before if fp_before.get(k) != fp_after.get(k)]))

        # ---------- A2：集合键名 list → A 必须 FAIL 且点名 DEMO-01
        a_root = os.path.join(base, "a_bad")
        write_fixture(a_root, wrapper_key="list")
        rc, payload = run_audit(a_root)
        a_fails = fails_for(payload, "A")
        check("A2 反向 集合键名 list → A 分支 FAIL 且点名 DEMO-01",
              rc == 1 and len(a_fails) == 1 and a_fails[0]["op"] == "DEMO-01"
              and a_fails[0].get("key") == "list",
              f"rc={rc} fails={[(r['op'], r.get('key')) for r in a_fails]}")

        # ---------- B1：带 pageSize 但未 PageMeta 包装 → B 必须 FAIL
        b_root = os.path.join(base, "b_bad")
        write_fixture(b_root, wrapper_key=None)
        rc, payload = run_audit(b_root)
        b_fails = fails_for(payload, "B")
        check("B1 反向 分页端点未 PageMeta 包装 → B 分支 FAIL 且点名 DEMO-01",
              rc == 1 and len(b_fails) == 1 and b_fails[0]["op"] == "DEMO-01",
              f"rc={rc} fails={[(r['op'], r['detail']) for r in b_fails]}")

        # ---------- C1：page.schema.json 只写 list → C 三条子断言全 FAIL
        c_root = os.path.join(base, "c_bad")
        write_fixture(c_root, page_key="list")
        rc, payload = run_audit(c_root)
        c_fails = fails_for(payload, "C")
        ops = sorted(r["op"] for r in c_fails)
        check("C1 反向 page schema 只写 list → C 三分支（required/properties/旧键名）全 FAIL",
              rc == 1 and ops == ["no-rejected-key", "properties", "required"],
              f"rc={rc} C FAIL ops={ops}")

        # ---------- D1：PageResult 首分量为 list → D 必须 FAIL
        d_root = os.path.join(base, "d_bad")
        write_fixture(d_root, result_first="list")
        rc, payload = run_audit(d_root)
        d_fails = fails_for(payload, "D")
        check("D1 反向 PageResult 首分量 list → D 分支 FAIL",
              rc == 1 and len(d_fails) == 1 and "list" in d_fails[0]["detail"],
              f"rc={rc} D fails={[r['detail'] for r in d_fails]}")

        # ---------- E1：客户端只声明 records → E 必须 FAIL
        e_root = os.path.join(base, "e_bad")
        write_fixture(e_root, client_field="records")
        rc, payload = run_audit(e_root)
        e_fails = fails_for(payload, "E")
        check("E1 反向 客户端接口只声明 records → E 分支 FAIL",
              rc == 1 and len(e_fails) == 1 and "records" in e_fails[0]["detail"],
              f"rc={rc} E fails={[r['detail'] for r in e_fails]}")

        # ---------- F1：清单 §0 未写 data:{items: → F 必须 FAIL
        f_root = os.path.join(base, "f_bad")
        write_fixture(f_root, manifest_key="list")
        rc, payload = run_audit(f_root)
        f_fails = fails_for(payload, "F")
        check("F1 反向 清单 §0 未写 data:{items: → F 分支 FAIL",
              rc == 1 and len(f_fails) == 1,
              f"rc={rc} F fails={[r['detail'] for r in f_fails]}")

        # ---------- 缺文件必须报 FAIL 而不是崩溃（坑 34：仓库外路径也要能跑）
        m_root = os.path.join(base, "missing")
        os.makedirs(m_root, exist_ok=True)
        rc, payload = run_audit(m_root)
        missing_ok = rc == 1 and payload.get("failed", 0) > 0 and payload.get("rows")
        check("G1 夹具目录缺文件 → 报 FAIL 且不崩溃（rc=1，有 rows）",
              bool(missing_ok),
              f"rc={rc} rows={len(payload.get('rows') or [])} raw={str(payload.get('raw'))[:160]!r}")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    passed = sum(1 for _n, ok, _d in results if ok)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"
              + ("" if ok else f"\n        {detail}"))
    print(f"\n合计 {len(results)} 条断言：PASS {passed}，FAIL {len(results) - passed}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
