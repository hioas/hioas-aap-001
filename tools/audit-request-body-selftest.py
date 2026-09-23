#!/usr/bin/env python3
"""`tools/audit-request-body.py` 的**负向自测**（R39）。

覆盖每一个判定分支（skill 坑 32：有几个分支就造几条反例），并给每个解析器配
**正向对照**（坑 46 / 75：只造「异常计数 ≤ 阈值」会被解析失效骗过），
再用**注入缺陷**实测判别力（坑 57 / 66：注入必须真的改到源码，否则是空转通过）。

用例清单：
  case_empty_fixture         空夹具 → 必须变红（正向对照/解析器失效不得判 PASS）
  case_ok_fixture            完整夹具 → rc=0 且 FAIL 0（正向对照）
  case_missing_schema_file   A1a 清单有 request_model 而缺 schema 文件
  case_orphan_schema         A1b 孤儿请求模型 schema 文件
  case_openapi_missing_body  A2a 清单有请求体而 openapi 无 requestBody
  case_openapi_extra_body    A2b openapi 有 requestBody 而清单无请求体
  case_md_no_body_has_model  A2c md 说无请求体而清单声明 request_model
  case_md_body_no_model      A2d md 写了请求体字段而清单无 request_model
  case_dangling_ref          A3a 请求体组件 $ref 悬空
  case_inline_prop_drift     A3b 内联组件属性 ≠ schema 属性
  case_md_field_missing      A4 md 字段不在请求模型 schema 里
  case_dto_missing_field     A5 schema 有而 DTO 无（含 @RequestBody(required=false) 与裸注解两种写法）
  case_dto_extra_field       A5 DTO 有而 schema 无
  case_client_key_out        A6 客户端 data 键越界
  case_client_get_ignored    A6 回归守卫：GET 的 data 是查询参数，不得当请求体（坑 62）
  case_md_style_guards       M 解析器回归守卫：`q：`/`{a,b}`/嵌套 `{items:[{x}]}`/引用式（坑 65）
  case_injection_teeth       注入缺陷：真实仓库副本里把 schema 属性改名 → FAIL 集合恰好新增 A5（坑 66）
  case_zero_write            真实仓库跑一遍：被读文件 md5 全等（零写副作用）

用法：python tools/audit-request-body-selftest.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUDIT = HERE / "audit-request-body.py"
TMP = Path(str(Path.home()) + "/AppData/Local/Temp") if not Path("/tmp").exists() else Path("/tmp")
# 唯一临时目录（结构性消除「rc 假红」这一缺陷类）：
# 旧写法只用 `%H%M%S`（日内秒，命名空间 86400）且脚本从不清理历史目录 → 残留逐轮累积（棘轮），
# 与任一历史运行**同秒**即 `shutil.copytree(..., WORK/"inject")` 撞 `FileExistsError` → rc 随机为 1，
# 在回归面里表现为一条**无法归因的 rc 变化**（而 FAIL 明细零变化）。改用 mkdtemp ⇒ 名字唯一、可重跑、并发安全。
WORK = Path(tempfile.mkdtemp(prefix="aap-reqbody-selftest-", dir=str(TMP)))

results: list[str] = []
npass = 0
nfail = 0


def check(name: str, ok: bool, detail: str = "") -> bool:
    global npass, nfail
    tag = "PASS" if ok else "FAIL"
    if ok:
        npass += 1
    else:
        nfail += 1
    results.append(f"  [{tag}] {name}" + (f"  ({detail})" if detail else ""))
    return ok


def run(root: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fails(out: str) -> list[str]:
    return [ln.split("] ", 1)[1] for ln in out.splitlines() if ln.startswith("[FAIL] ")]


def assert_red_on(case: str, prefix: str, root: Path, expect: str) -> None:
    rc, out = run(root)
    fs = fails(out)
    hit = any(x.startswith(expect) for x in fs)
    check(f"{case}：rc=1(期望 1) 命中「{expect}」", rc == 1 and hit,
          f"rc={rc}；FAIL={[f.split('：')[0] for f in fs]}")


# ------------------------------------------------------------------ 夹具

MD = """# 合成清单（夹具）

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-01 | POST | `/syn/a` | ✅ | body：`alpha` `beta?` | `A` | E-1001 | — | 真源 | T01 |
| SYN-02 | POST | `/syn/b` | ✅ | body `{gamma,delta?}` | `B` | | | 真源 | T01 |
| SYN-03 | POST | `/syn/c` | ✅ | body：同 SYN-01 的可写子集 | `A` | | | 真源 | T01 |
| SYN-04 | POST | `/syn/d` | ✅ | —（无请求体） | `A` | | | 真源 | T01 |
| SYN-05 | GET | `/syn/e` | ✅ | q：`page` `pageSize` | `A` | | | 真源 | T01 |
| SYN-06 | POST | `/syn/f` | ✅ | body `{items:[{model_name,model_alias?}]}` | `A` | | | 真源 | T01 |
"""


def schema(title: str, props: dict, required: list | None = None) -> str:
    d = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title,
         "properties": props, "type": "object", "additionalProperties": True}
    if required:
        d["required"] = required
    return json.dumps(d, ensure_ascii=False, indent=2)


OPENAPI_HEAD = """openapi: 3.0.3
info:
  title: 夹具
  version: "1.0"
paths:
"""


def op(eid: str, path: str, body: str | None) -> str:
    s = f"""  {path}:
    post:
      operationId: {eid}
      x-aap-id: {eid}
      responses:
        200:
          description: ok
"""
    if body:
        s = s.replace("      responses:", f"""      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/{body}"
      responses:""")
    return s


def controller(path: str, eid: str, dto: str, annot: str, pkg: str = "com.syn") -> str:
    return f"""package {pkg};

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynController {{
    @PostMapping("{path}")
    {annot} {dto} request) {{
        return null;
    }}

    public record SynRequest(String alpha, String beta) {{
    }}
}}
"""


def build_fixture(dst: Path, *, missing_schema=False, orphan_schema=False,
                  openapi_missing_body=False, openapi_extra_body=False,
                  md_no_body_has_model=False, md_body_no_model=False,
                  dangling_ref=False, inline_drift=False, md_field_missing=False,
                  dto_missing=False, dto_extra=False, client_key_out=False,
                  include_client_get=True, empty=False) -> Path:
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "docs/backend").mkdir(parents=True, exist_ok=True)
    (dst / "docs/backend/json-schema/requests").mkdir(parents=True, exist_ok=True)
    (dst / "aap-server/src/main/java/com/hioas/aap/syn").mkdir(parents=True, exist_ok=True)
    (dst / "aap-client/src/api").mkdir(parents=True, exist_ok=True)
    if empty:
        return dst

    (dst / "docs/backend/02-API接口模型清单.md").write_text(MD, encoding="utf-8")

    eps = [
        {"id": "SYN-01", "method": "POST", "path": "/api/v1/syn/a", "request_model": "syn-a",
         "query_params": []},
        {"id": "SYN-02", "method": "POST", "path": "/api/v1/syn/b", "request_model": "syn-b",
         "query_params": []},
        {"id": "SYN-06", "method": "POST", "path": "/api/v1/syn/f", "request_model": "syn-f",
         "query_params": []},
    ]
    if md_no_body_has_model:
        eps.append({"id": "SYN-04", "method": "POST", "path": "/api/v1/syn/d",
                    "request_model": "syn-a", "query_params": []})
    if md_body_no_model:
        for e in eps:
            if e["id"] == "SYN-02":
                e["request_model"] = None
    if not missing_schema:
        sa = {"alpha": {"type": "string"},
              "beta": {"type": "string"},
              "delta": {"type": "string"},
              "gamma": {"type": "string"}}
        if md_field_missing:
            sa.pop("beta")
        (dst / "docs/backend/json-schema/requests/syn-a.schema.json").write_text(
            schema("syn-a", sa), encoding="utf-8")
    (dst / "docs/backend/json-schema/requests/syn-b.schema.json").write_text(
        schema("syn-b", {"alpha": {"type": "string"}, "beta": {"type": "string"},
                         "delta": {"type": "string"}, "gamma": {"type": "string"}}), encoding="utf-8")
    (dst / "docs/backend/json-schema/requests/syn-f.schema.json").write_text(
        schema("syn-f", {"items": {"type": "array"}}), encoding="utf-8")
    if orphan_schema:
        (dst / "docs/backend/json-schema/requests/syn-orphan.schema.json").write_text(
            schema("syn-orphan", {"x": {"type": "string"}}), encoding="utf-8")
    (dst / "docs/backend/endpoints.json").write_text(
        json.dumps({"total": len(eps), "endpoints": eps}, ensure_ascii=False), encoding="utf-8")

    oa = OPENAPI_HEAD
    oa += op("SYN-01", "/syn/a", "RequestSynA")
    oa += op("SYN-02", "/syn/b", "RequestSynB")
    oa += op("SYN-06", "/syn/f", "RequestSynF")
    if md_no_body_has_model:
        oa += op("SYN-04", "/syn/d", "RequestSynA")
    if openapi_missing_body:
        oa = oa.replace("""      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/RequestSynA"
""", "", 1)
    if openapi_extra_body:
        oa += op("SYN-05", "/syn/e", "RequestSynA")
    oa += """components:
  schemas:
    RequestSynA:
      $ref: ./json-schema/requests/syn-a.schema.json
    RequestSynB:
      $ref: ./json-schema/requests/syn-b.schema.json
    RequestSynF:
      $ref: ./json-schema/requests/syn-f.schema.json
"""
    if dangling_ref:
        oa += "    RequestSynZ:\n      $ref: ./json-schema/requests/syn-z.schema.json\n"
    if inline_drift:
        # 把 SYN-01 的请求体改成**内联组件**（属性与 schema 不一致）→ A3b 必须转红
        oa = oa.replace('$ref: "#/components/schemas/RequestSynA"\n      responses:\n        200:\n          description: ok\n',
                        '$ref: "#/components/schemas/RequestSynInline"\n      responses:\n        200:\n          description: ok\n', 1)
        oa += """    RequestSynInline:
      type: object
      properties:
        only_here:
"""
    (dst / "docs/backend/openapi.yaml").write_text(oa, encoding="utf-8")

    # 控制器：SYN-01 用「注解带实参」写法、SYN-02 用「裸注解直接跟签名」写法（坑 63）
    dto1 = "SynRequest" if not dto_missing else "SynTiny"
    (dst / "aap-server/src/main/java/com/hioas/aap/syn/SynController.java").write_text(
        f"""package com.hioas.aap.syn;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/syn")
public class SynController {{
    @PostMapping("/a")
    public Object a(
            @RequestBody(
                    required = false) {dto1} request) {{
        return null;
    }}

    @PostMapping("/b")
    public Object b(@RequestBody SynRequest request) {{
        return null;
    }}

    @PostMapping("/d")
    public Object d(@RequestBody SynRequest request) {{
        return null;
    }}

    @PostMapping("/f")
    public Object f(@RequestBody SynFRequest request) {{
        return null;
    }}

    public record SynRequest(String alpha, String beta, String delta, String gamma{", String extra_field" if dto_extra else ""}) {{
    }}

    public record SynFRequest(List<String> items) {{
    }}

    public record SynTiny(String alpha, String beta) {{
    }}
}}
""", encoding="utf-8")

    keys = "{ alpha: 1, beta: 2 }"
    if client_key_out:
        keys = "{ alpha: 1, not_in_schema: 2 }"
    get_call = ("    return http<T>('/syn/e', { method: 'GET', data: { page: 1, pageSize: 20 } })\n"
                if include_client_get else "")
    (dst / "aap-client/src/api/syn.ts").write_text(
        "import { http } from './http'\n"
        "export const syn = {\n"
        f"  create: () => http<T>('/syn/a', {{ method: 'POST', data: {keys} }}),\n"
        f"{get_call}"
        "}\n", encoding="utf-8")
    return dst


# ------------------------------------------------------------------ 用例

def main() -> int:
    print("== audit-request-body.py 负向自测 ==")
    WORK.mkdir(parents=True, exist_ok=True)

    # --- 空夹具：正向对照必须变红（解析器失效不得判 PASS） ---
    d = build_fixture(WORK / "empty", empty=True)
    rc, out = run(d)
    fs = fails(out)
    check("case_empty_fixture：空夹具 rc=1 且 A0 正向对照转红",
          rc == 1 and sum(1 for f in fs if f.startswith("A0")) >= 4,
          f"rc={rc}；A0 FAIL={sum(1 for f in fs if f.startswith('A0'))}")

    # --- ok 夹具：必须全绿（正向对照） ---
    d = build_fixture(WORK / "ok")
    rc, out = run(d)
    check("case_ok_fixture：完整夹具 rc=0 且 FAIL 0", rc == 0 and not fails(out),
          f"rc={rc}；FAIL={[f.split('：')[0] for f in fails(out)]}")

    # --- 每个分支一条反例 ---
    assert_red_on("case_missing_schema_file", "", build_fixture(WORK / "miss_schema",
                 missing_schema=True), "A1a")
    assert_red_on("case_orphan_schema", "", build_fixture(WORK / "orphan",
                 orphan_schema=True), "A1b")
    assert_red_on("case_openapi_missing_body", "", build_fixture(WORK / "oa_miss",
                 openapi_missing_body=True), "A2a")
    assert_red_on("case_openapi_extra_body", "", build_fixture(WORK / "oa_extra",
                 openapi_extra_body=True), "A2b")
    assert_red_on("case_md_no_body_has_model", "", build_fixture(WORK / "md_nobody",
                 md_no_body_has_model=True), "A2c")
    assert_red_on("case_md_body_no_model", "", build_fixture(WORK / "md_nomodel",
                 md_body_no_model=True), "A2d")
    assert_red_on("case_dangling_ref", "", build_fixture(WORK / "dangling",
                 dangling_ref=True), "A3a")
    assert_red_on("case_inline_prop_drift", "", build_fixture(WORK / "inline",
                 inline_drift=True), "A3b")
    assert_red_on("case_md_field_missing", "", build_fixture(WORK / "md_miss",
                 md_field_missing=True), "A4")
    assert_red_on("case_dto_missing_field", "", build_fixture(WORK / "dto_miss",
                 dto_missing=True), "A5")
    assert_red_on("case_dto_extra_field", "", build_fixture(WORK / "dto_extra",
                 dto_extra=True), "A5")
    assert_red_on("case_client_key_out", "", build_fixture(WORK / "cli_out",
                 client_key_out=True), "A6")

    # --- 回归守卫：GET 的 data 是查询参数（坑 62），不得当请求体 ---
    d = build_fixture(WORK / "cli_get")
    rc, out = run(d)
    check("case_client_get_ignored：GET 的 data 不被当请求体（rc=0）", rc == 0,
          f"rc={rc}；FAIL={[f.split('：')[0] for f in fails(out)]}")

    # --- M 解析器回归守卫（坑 65）：q：/花括号/嵌套花括号/引用式 ---
    d = build_fixture(WORK / "md_styles")
    sys.path.insert(0, str(HERE))
    import importlib.util
    spec = importlib.util.spec_from_file_location("arb", AUDIT)
    arb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(arb)
    bodies, undec, _ = arb.parse_md_bodies(d)
    check("case_md_style_guards：`q：` 行判「无请求体」而不是漂移",
          bodies.get("SYN-05") == frozenset(), f"SYN-05={bodies.get('SYN-05')}")
    check("case_md_style_guards：花括号式取到 {gamma,delta}",
          bodies.get("SYN-02") == frozenset({"gamma", "delta"}), f"SYN-02={bodies.get('SYN-02')}")
    check("case_md_style_guards：嵌套花括号只取最外层键（items）",
          bodies.get("SYN-06") == frozenset({"items"}), f"SYN-06={bodies.get('SYN-06')}")
    check("case_md_style_guards：引用式写法记「未能静态判定」而不是漂移",
          "SYN-03" in undec and "SYN-03" not in bodies, f"undec={undec.get('SYN-03')}")
    check("case_md_style_guards：正向对照 —— 反引号式取到 {alpha,beta}",
          bodies.get("SYN-01") == frozenset({"alpha", "beta"}), f"SYN-01={bodies.get('SYN-01')}")

    # --- 注入缺陷：判别力实测（坑 66：注入必须真的改到源码） ---
    inj = WORK / "inject"
    shutil.copytree(ROOT, inj, ignore=shutil.ignore_patterns(".git", "node_modules", "target", "dist"))
    base_rc, base_out = run(inj)
    base_fails = fails(base_out)
    base_a5 = [f for f in base_fails if f.startswith("A5 ")]
    base_kinds = {f.split("：")[0] for f in base_fails}
    tgt = inj / "docs/backend/json-schema/requests/credential-create.schema.json"
    txt = tgt.read_text(encoding="utf-8")
    mutated = txt.replace('"env_tag": {', '"env_tag_injected": {')
    hit_anchor = mutated != txt
    tgt.write_text(mutated, encoding="utf-8")
    inj_rc, inj_out = run(inj)
    inj_fails = fails(inj_out)
    inj_a5 = [f for f in inj_fails if f.startswith("A5 ")]
    inj_kinds = {f.split("：")[0] for f in inj_fails}
    check("case_injection_teeth：注入锚点真的改到了源码（坑 66）", hit_anchor, f"锚点命中={hit_anchor}")
    check("case_injection_teeth：注入后 A5 明细变化且点名注入字段（判别力实测）",
          base_a5 != inj_a5 and any("env_tag_injected" in f for f in inj_a5),
          f"基线 A5={len(base_a5)} 条；注入后 A5={len(inj_a5)} 条；"
          f"点名={'env_tag_injected' in (inj_a5[0] if inj_a5 else '')}")
    check("case_injection_teeth：注入不新增/不减少断言类型（判据不越界）",
          base_kinds == inj_kinds,
          f"基线 {len(base_kinds)} 类 / 注入后 {len(inj_kinds)} 类；差={sorted(base_kinds ^ inj_kinds)}")

    # --- 零写副作用：真实仓库跑一遍 ---
    watched = [ROOT / "docs/backend/02-API接口模型清单.md", ROOT / "docs/backend/endpoints.json",
               ROOT / "docs/backend/openapi.yaml",
               ROOT / "docs/backend/json-schema/requests/credential-create.schema.json"]
    before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in watched}
    rc, out = run(ROOT)
    after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in watched}
    check("case_zero_write：真实仓库跑一遍只读（4 个关键文件 md5 全等）",
          before == after, f"rc={rc}（真实仓库 rc={rc} 是预期的：存在待拍板漂移）")

    print("\n".join(results))
    print(f"\n== 自测结果：PASS {npass} / FAIL {nfail} ==")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
