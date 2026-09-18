#!/usr/bin/env python3
"""`tools/audit-response-shape.py` 的负向自测（R37）。

每个判定分支一条反例（skill 坑 32：判定有几个分支，自测就要有几条反例），外加：
  * **正向对照**：`ok` 夹具必须 rc=0（只有反例时「一直在报错」会被当成合格，坑 46）；
  * **空夹具必须变红**（解析器失效不得判 PASS，坑 46 / 72）；
  * **注入缺陷判别力**：把审计脚本复制一份并注入缺陷，断言**恰好**目标断言转红，
    且先断言注入真的改到了源码（锚点没命中 → 空转通过，坑 66）；
  * **零写副作用**：夹具目录与仓库文件在运行前后 md5 全等。

用法：python tools/audit-response-shape-selftest.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
AUDIT = TOOLS / "audit-response-shape.py"
REPO = TOOLS.parent
MD_HEADER = "| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |\n" \
            "|---|---|---|---|---|---|---|---|---|---|\n"


def md_row(eid: str, method: str, path: str, resp_cell: str) -> str:
    return f"| {eid} | {method} | {path} | ✅ | — | {resp_cell} | | | 真源 | T01 |\n"


def manifest(eps: list[dict]) -> str:
    return json.dumps({"total": len(eps), "endpoints": eps}, ensure_ascii=False, indent=2)


def ep(eid, method, path, resp, params=None) -> dict:
    return {"id": eid, "method": method, "path": path, "tag": "T", "auth": "PROVIDER",
            "request_model": None, "response_model": resp, "query_params": params or [],
            "error_codes": [], "source": "真源", "task": "T01"}


def single_op(eid: str, path: str, comp: str, page_params: bool = False) -> str:
    params = ""
    if page_params:
        params = ("      parameters:\n"
                  "        - name: page\n          in: query\n          required: false\n"
                  "          schema:\n            type: integer\n"
                  "        - name: pageSize\n          in: query\n          required: false\n"
                  "          schema:\n            type: integer\n")
    return (f"  {path}:\n"
            "    get:\n"
            f"      operationId: {eid}\n"
            "      tags:\n        - T\n"
            f"{params}"
            "      responses:\n"
            "        200:\n"
            "          description: 成功\n"
            "          content:\n"
            "            application/json:\n"
            "              schema:\n"
            "                allOf:\n"
            "                  - $ref: \"#/components/schemas/Envelope\"\n"
            "                  - type: object\n"
            "                    properties:\n"
            "                      data:\n"
            f"                        $ref: \"#/components/schemas/{comp}\"\n")


def page_op(eid: str, path: str, comp: str, page_params: bool = True) -> str:
    params = ""
    if page_params:
        params = ("      parameters:\n"
                  "        - name: page\n          in: query\n          required: false\n"
                  "          schema:\n            type: integer\n"
                  "        - name: pageSize\n          in: query\n          required: false\n"
                  "          schema:\n            type: integer\n")
    return (f"  {path}:\n"
            "    get:\n"
            f"      operationId: {eid}\n"
            "      tags:\n        - T\n"
            f"{params}"
            "      responses:\n"
            "        200:\n"
            "          description: 成功\n"
            "          content:\n"
            "            application/json:\n"
            "              schema:\n"
            "                allOf:\n"
            "                  - $ref: \"#/components/schemas/Envelope\"\n"
            "                  - type: object\n"
            "                    properties:\n"
            "                      data:\n"
            "                        allOf:\n"
            "                          - $ref: \"#/components/schemas/PageMeta\"\n"
            "                          - type: object\n"
            "                            properties:\n"
            "                              items:\n"
            "                                type: array\n"
            "                                items:\n"
            f"                                  $ref: \"#/components/schemas/{comp}\"\n")


def openapi(paths: list[str], comps: dict[str, str]) -> str:
    head = ("openapi: 3.1.0\n"
            "info:\n  title: fixture\n  version: 1.0.0\n"
            "paths:\n")
    comp_lines = ["components:", "  schemas:", "    Envelope:",
                  "      $ref: ./json-schema/common/envelope.schema.json",
                  "    PageMeta:", "      $ref: ./json-schema/common/page.schema.json"]
    for k, v in comps.items():
        comp_lines += [f"    {k}:", f"      $ref: {v}"]
    return head + "".join(paths) + "\n".join(comp_lines) + "\n"


def schema_model(name: str, props: dict[str, str], required: list[str]) -> str:
    return json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name, "type": "object", "required": required,
        "properties": {k: {"type": v} for k, v in props.items()},
    }, ensure_ascii=False, indent=2)


CONTROLLER_HEAD = """package com.hioas.aap;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class FixtureController {
"""


def controller(methods: list[str], records: list[str]) -> str:
    return CONTROLLER_HEAD + "".join(methods) + "}\n" + "".join(records)


def single_method(path: str, dto: str) -> str:
    return (f"    @GetMapping(\"{path}\")\n"
            f"    public ApiEnvelope<{dto}> get() {{\n        return null;\n    }}\n")


def page_method(path: str, dto: str) -> str:
    return (f"    @GetMapping(\"{path}\")\n"
            f"    public ApiEnvelope<PageResult<{dto}>> list() {{\n        return null;\n    }}\n")


REC_PAGERESULT = "record PageResult<T>(List<T> items, int page, int pageSize, long total) {}\n"
REC_ROW = "record Row(String id, String name) {}\n"
REC_PROFILE = "record Profile(String provider_id, String status) {}\n"

OK_FILES: dict[str, str] = {
    "docs/backend/endpoints.json": manifest([
        ep("T-01", "GET", "/api/v1/items", "row", ["page", "pageSize"]),
        ep("T-02", "GET", "/api/v1/profile", "profile"),
    ]),
    "docs/backend/openapi.yaml": openapi(
        [page_op("T-01", "/items", "Row"), single_op("T-02", "/profile", "Profile")],
        {"Row": "./json-schema/models/row.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"},
    ),
    "docs/backend/02-API接口模型清单.md": MD_HEADER + md_row("T-01", "GET", "/items", "`{items:[Row],page,pageSize,total}`")
    + md_row("T-02", "GET", "/profile", "`Profile`"),
    "docs/backend/json-schema/models/row.schema.json":
        schema_model("row", {"id": "string", "name": "string"}, ["id"]),
    "docs/backend/json-schema/models/profile.schema.json":
        schema_model("profile", {"provider_id": "string", "status": "string"}, ["provider_id"]),
    "aap-server/src/main/java/com/hioas/aap/FixtureController.java": controller(
        [page_method("/items", "Row"), single_method("/profile", "Profile")],
        [REC_PAGERESULT, REC_ROW, REC_PROFILE]),
}


def write_case(files: dict[str, str], tag: str) -> Path:
    root = Path(tempfile.gettempdir()) / f"r37-shape-{tag}"
    if root.exists():
        shutil.rmtree(root)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def run(root: Path, script: Path = AUDIT) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(script), "--root", str(root), "--all"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def tree_md5(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    npass = nfail = 0
    lines: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal npass, nfail
        if ok:
            npass += 1
        else:
            nfail += 1
        lines.append(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"：{detail}" if detail else ""))

    def case(tag: str, files: dict[str, str], want_rc: int, want_assert: str | None,
             forbid: str | None = None) -> None:
        root = write_case(files, tag)
        before = tree_md5(root)
        rc, out = run(root)
        after = tree_md5(root)
        ok = rc == want_rc
        detail = f"rc={rc}(期望 {want_rc})"
        if want_assert:
            hit = want_assert in out
            ok = ok and hit
            detail += f" 命中「{want_assert}」={'是' if hit else '否'}"
        if forbid:
            bad = forbid in out
            ok = ok and not bad
            detail += f" 不应出现「{forbid}」={'未出现' if not bad else '却出现了'}"
        ok = ok and before == after
        detail += " 夹具未被改写" if before == after else " 夹具被改写了！"
        check(f"{tag}：{detail}", ok)

    # ---- 正向对照 ----
    case("ok", OK_FILES, 0, "结论：逐端点响应形状一致")

    # ---- 分支反例 ----
    f = dict(OK_FILES)
    f["docs/backend/openapi.yaml"] = openapi(
        [page_op("T-01", "/items", "Row"), page_op("T-02", "/profile", "Profile", page_params=False)],
        {"Row": "./json-schema/models/row.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"})
    case("openapi 把单对象端点声明成分页（本轮真实缺陷）", f, 1,
         "A2 openapi 声明分页 ⇔ 实现返回分页形状 DTO", "[FAIL] A4 实现分页形状 DTO ⇒ openapi 分页")

    f = dict(OK_FILES)
    f["docs/backend/openapi.yaml"] = openapi(
        [single_op("T-01", "/items", "Row"), single_op("T-02", "/profile", "Profile")],
        {"Row": "./json-schema/models/row.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"})
    case("反向：实现分页而 openapi 声明单对象", f, 1, "A4 实现分页形状 DTO ⇒ openapi 分页")

    f = dict(OK_FILES)
    f["docs/backend/endpoints.json"] = manifest([
        ep("T-01", "GET", "/api/v1/items", "row", []),
        ep("T-02", "GET", "/api/v1/profile", "profile"),
    ])
    f["docs/backend/openapi.yaml"] = openapi(
        [page_op("T-01", "/items", "Row", page_params=False), single_op("T-02", "/profile", "Profile")],
        {"Row": "./json-schema/models/row.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"})
    case("分页响应却没有 page/pageSize 查询参数（自洽性第三证人）", f, 1,
         "A3 openapi 分页响应 ⇒ 该端点声明 page+pageSize 查询参数")

    f = dict(OK_FILES)
    f["docs/backend/openapi.yaml"] = openapi(
        [page_op("T-01", "/items", "Rows"), single_op("T-02", "/profile", "Profile")],
        {"Rows": "./json-schema/models/row.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"})
    case("组件名不是 PascalCase(response_model)", f, 1,
         "A1b 每端点 200 的 data 绑定组件 = PascalCase(response_model)")

    f = dict(OK_FILES)
    f["docs/backend/openapi.yaml"] = openapi(
        [page_op("T-01", "/items", "Row"), single_op("T-02", "/profile", "Profile")],
        {"Row": "./json-schema/models/profile.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"})
    case("组件指向错误的 schema 文件", f, 1,
         "A1c 被绑定组件解析到的文件 = models/<response_model>.schema.json")

    f = dict(OK_FILES)
    f["docs/backend/json-schema/models/row.schema.json"] = schema_model(
        "row", {"items": "array", "page": "integer", "pageSize": "integer", "total": "integer"}, ["items"])
    case("元素模型 schema 自身又是分页包装（双重包装）", f, 1,
         "A5 元素模型 schema 存在且是单对象模型")

    f = dict(OK_FILES)
    f["docs/backend/endpoints.json"] = manifest([
        ep("T-01", "GET", "/api/v1/items", "row", ["page", "pageSize"]),
        ep("T-02", "GET", "/api/v1/profile", "profile"),
        ep("T-03", "GET", "/api/v1/ghost", "profile"),
    ])
    f["docs/backend/02-API接口模型清单.md"] = MD_HEADER \
        + md_row("T-01", "GET", "/items", "`{items:[Row],page,pageSize,total}`") \
        + md_row("T-02", "GET", "/profile", "`Profile`") \
        + md_row("T-03", "GET", "/ghost", "`Profile`")
    case("清单端点不在 openapi 里（未定位）", f, 1, "A1a 清单每条端点在 openapi 里都能定位")

    f = dict(OK_FILES)
    f["docs/backend/02-API接口模型清单.md"] = MD_HEADER \
        + md_row("T-01", "GET", "/items", "`{items:[Row],page,pageSize,total}`")
    case("md 清单缺行（行数 ≠ total）", f, 1, "A0b D 行数 = total")

    f = dict(OK_FILES)
    f["docs/backend/openapi.yaml"] = openapi(
        [single_op("T-01", "/items", "Row"), single_op("T-02", "/profile", "Profile")],
        {"Row": "./json-schema/models/row.schema.json",
         "Profile": "./json-schema/models/profile.schema.json"})
    case("正向对照：ok 夹具的 md 散文列解析到「列表」1 条", OK_FILES, 0, "md 说「列表」而 openapi 非分页：0 条")

    # ---- 空夹具必须变红（解析器失效不得判 PASS） ----
    empty = dict(OK_FILES)
    empty["docs/backend/endpoints.json"] = manifest([])
    empty["docs/backend/02-API接口模型清单.md"] = MD_HEADER
    case("空夹具：正向对照必须变红", empty, 1, "A0a M 端点数 = total")

    # ---- 缺源文件必须显式失败 ----
    root = write_case({"docs/backend/endpoints.json": manifest([])}, "missing-src")
    rc, out = run(root)
    check("缺源文件 → 显式 FAIL 且不崩溃", rc == 1 and "源文件/目录缺失" in out, f"rc={rc}")

    # ---- 注入缺陷判别力（先断言注入真的改到了源码，坑 66） ----
    def mutate(tag: str, old: str, new: str) -> tuple[Path, bool]:
        src = AUDIT.read_text(encoding="utf-8")
        if src.count(old) == 0:
            return AUDIT, False
        dst = Path(tempfile.gettempdir()) / f"r37-audit-mut-{tag}.py"
        dst.write_text(src.replace(old, new, 1), encoding="utf-8")
        return dst, True

    m1, applied1 = mutate("pagedetect", 'PAGE_COMPONENTS = {"items", "page", "pageSize", "total"}',
                          'PAGE_COMPONENTS = {"items", "page", "pageSize", "total", "nope_field"}')
    check("注入#1 真的改到了源码（锚点命中）", applied1)
    if applied1:
        rc, out = run(write_case(OK_FILES, "mut1"), m1)
        check("注入#1（分页判据加一个不存在的分量）→ ok 夹具必须转红且恰好命中 A2",
              rc == 1 and "A2 openapi 声明分页 ⇔ 实现返回分页形状 DTO" in out, f"rc={rc}")

    m2, applied2 = mutate("mdshape", 'if re.search(r"\\bitems\\s*:", c) or "分页" in c:',
                          'if False:')
    check("注入#2 真的改到了源码（锚点命中）", applied2)
    if applied2:
        rc, out = run(write_case(OK_FILES, "mut2"), m2)
        check("注入#2（md 散文解析失效）→ ok 夹具转红（A6b 正向对照兜底）",
              rc == 1 and "A6b D 解析到「列表」形状的端点 > 0" in out, f"rc={rc}")

    m3, applied3 = mutate("compref", 'COMPONENT_RE = re.compile(r"^    (\\w+):\\n      \\$ref: (\\S+)$", re.MULTILINE)',
                          'COMPONENT_RE = re.compile(r"^    (\\w+):\\n      \\$refXX: (\\S+)$", re.MULTILINE)')
    check("注入#3 真的改到了源码（锚点命中）", applied3)
    if applied3:
        rc, out = run(write_case(OK_FILES, "mut3"), m3)
        check("注入#3（组件表解析失效）→ 空转假绿必须被 A0d 兜住",
              rc == 1 and "A0d O 组件表解析到 $ref 组件" in out, f"rc={rc}")

    # ---- 仓库只读守卫：真实仓库文件未被本自测改写 ----
    repo_files = [REPO / "docs/backend/openapi.yaml", REPO / "docs/backend/endpoints.json",
                  REPO / "docs/backend/02-API接口模型清单.md", AUDIT]
    before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in repo_files}
    rc, out = run(REPO)
    after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in repo_files}
    check("真实仓库跑一遍：只读（4 个关键文件 md5 全等）", before == after,
          f"rc={rc}（真实仓库本轮 rc=1 是预期的：存在待拍板漂移）")

    print("\n".join(lines))
    print(f"\n自测 {npass + nfail} 条：PASS {npass}，FAIL {nfail}")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
