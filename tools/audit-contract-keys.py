#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""只读审计：分页响应的**集合键名**在「四处真源」之间是否一致。

背景（`aap-server-tdd-state.md` 踩坑 1）：契约文档曾写 `data.list`，而客户端读 `raw.items`
→ 上线后所有列表页空白。该冲突已作为偏差 **D-API-01** 记入
`docs/backend/02-API接口模型清单.md` §0，结论是**字段名以客户端为准 = `items`**。

但**生成器的 OpenAPI 产物从未跟着修正**：`tools/gen-backend-models.py` 的 `_enveloped()`
对 `LIST_RESPONSE_MODELS` 仍输出 `list`，而同一个函数对 `detection-result` / `quote-item`
输出 `items`（同一文件内两种写法）。由于契约测试校验的是 **JSON Schema 文件**、不读
`openapi.yaml`，这条漂移对全量用例**完全不可见**（踩坑 39 同族：假的安全感）。

本脚本把「集合键名」当契约不变量，在四个独立来源上比对：

  A. OpenAPI：每个被 `PageMeta` 包装的响应，其集合属性名必须为 `items`
  B. OpenAPI：每个带 `pageSize` 查询参数的端点，响应必须被 `PageMeta` 包装（分页端点不得漏包装）
  C. `page.schema.json`：`required` 与 `properties` 必须含 `items`，且不得出现 `list`
  D. 运行时 `PageResult` 的 record 分量名必须是 `items`
  E. 客户端 `aap-client/src/api/*.ts`：声明为列表响应的接口必须声明 `items`
  F. 冻结清单 `02-API接口模型清单.md` §0 必须写明 `data:{items:`

只读：本脚本不写任何文件（含自身目录）。用法：
    python tools/audit-contract-keys.py [--root <仓库根>] [--json]
退出码：0 = 全部 PASS；1 = 存在 FAIL。
"""
from __future__ import annotations

import json
import os
import re
import sys

# 集合键名的唯一正确值（真源 = 客户端读法，见清单 §0 / D-API-01）
EXPECTED_KEY = "items"
# 生成器里出现过、但已被 D-API-01 否定的旧写法（审计要能点名）
REJECTED_KEYS = ("list", "records", "rows")

# OpenAPI 里 `operationId:` 的缩进（生成器 yaml_dump 固定 2 空格递进）
OP_INDENT = 6
# PageMeta 引用行缩进
PAGEMETA_INDENT = 26
# 集合属性名（`properties:` 下的键）缩进
COLLECTION_KEY_INDENT = 30
# 查询参数条目缩进
PARAM_ITEM_INDENT = 8


def read_text(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def rel(path: str, root: str) -> str:
    """相对路径展示；仓库外路径回退为绝对路径（踩坑 34）。"""
    try:
        return os.path.relpath(path, root).replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


# --------------------------------------------------------------------------- A / B
def split_operations(text: str) -> list[tuple[str, int, int]]:
    """返回 [(operationId, start_line_idx, end_line_idx)]（end 不含）。"""
    op_re = re.compile(r"^ {%d}operationId: (\S+)\s*$" % OP_INDENT)
    marks = []
    for idx, line in enumerate(text.splitlines()):
        m = op_re.match(line)
        if m:
            marks.append((m.group(1), idx))
    blocks = []
    for i, (op_id, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text.splitlines())
        blocks.append((op_id, start, end))
    return blocks


def audit_openapi(path: str, root: str) -> tuple[list[dict], list[dict]]:
    """A：集合键名；B：分页端点是否被 PageMeta 包装。"""
    text = read_text(path)
    label = rel(path, root)
    if text is None:
        return ([{"check": "A", "file": label, "op": "-", "key": None,
                  "ok": False, "detail": "文件缺失"}],
                [{"check": "B", "file": label, "op": "-", "ok": False,
                  "detail": "文件缺失"}])
    lines = text.splitlines()
    key_rows, wrap_rows = [], []

    for op_id, start, end in split_operations(text):
        block = lines[start:end]
        has_pagemeta = any(
            line.strip().startswith("- $ref:") and "schemas/PageMeta" in line
            for line in block
        )
        has_page_param = any(
            line == " " * PARAM_ITEM_INDENT + "- name: pageSize" for line in block
        )

        # --- B：带 pageSize 的端点必须被 PageMeta 包装
        if has_page_param:
            wrap_rows.append({
                "check": "B", "file": label, "op": op_id, "ok": has_pagemeta,
                "detail": "响应已 PageMeta 包装" if has_pagemeta
                else "有 pageSize 参数但响应未 PageMeta 包装（分页端点漏包装）",
            })

        # --- A：被 PageMeta 包装的响应，其集合键名
        if not has_pagemeta:
            continue
        keys = []
        seen_pagemeta = False
        for line in block:
            if line.strip().startswith("- $ref:") and "schemas/PageMeta" in line:
                seen_pagemeta = True
                continue
            if not seen_pagemeta:
                continue
            m = re.match(r"^ {%d}([A-Za-z_][A-Za-z0-9_]*):\s*$" % COLLECTION_KEY_INDENT, line)
            if m:
                keys.append(m.group(1))
                break
        if len(keys) != 1:
            key_rows.append({
                "check": "A", "file": label, "op": op_id, "key": None, "ok": False,
                "detail": f"无法唯一定位集合属性名（解析到 {keys!r}）",
            })
            continue
        key = keys[0]
        key_rows.append({
            "check": "A", "file": label, "op": op_id, "key": key,
            "ok": key == EXPECTED_KEY,
            "detail": f"集合键名 = {key!r}" + ("" if key == EXPECTED_KEY else
                                             f"，应为 {EXPECTED_KEY!r}"
                                             + ("（已被 D-API-01 否定的旧写法）"
                                                if key in REJECTED_KEYS else "")),
        })
    return key_rows, wrap_rows


# --------------------------------------------------------------------------- C
def audit_page_schema(path: str, root: str) -> list[dict]:
    label = rel(path, root)
    text = read_text(path)
    if text is None:
        return [{"check": "C", "file": label, "op": "-", "ok": False, "detail": "文件缺失"}]
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        return [{"check": "C", "file": label, "op": "-", "ok": False,
                 "detail": f"JSON 解析失败：{exc}"}]
    required = doc.get("required") or []
    props = doc.get("properties") or {}
    rows = [
        {"check": "C", "file": label, "op": "required", "ok": EXPECTED_KEY in required,
         "detail": f"required 含 {EXPECTED_KEY!r}" if EXPECTED_KEY in required
         else f"required 缺 {EXPECTED_KEY!r}：{required!r}"},
        {"check": "C", "file": label, "op": "properties", "ok": EXPECTED_KEY in props,
         "detail": f"properties 含 {EXPECTED_KEY!r}" if EXPECTED_KEY in props
         else f"properties 缺 {EXPECTED_KEY!r}：{sorted(props)!r}"},
    ]
    rejected = [k for k in REJECTED_KEYS if k in props or k in required]
    rows.append({
        "check": "C", "file": label, "op": "no-rejected-key", "ok": not rejected,
        "detail": "未出现被否定的旧键名" if not rejected
        else f"出现被 D-API-01 否定的旧键名：{rejected!r}",
    })
    return rows


# --------------------------------------------------------------------------- D
def audit_runtime(path: str, root: str) -> list[dict]:
    label = rel(path, root)
    text = read_text(path)
    if text is None:
        return [{"check": "D", "file": label, "op": "-", "ok": False, "detail": "文件缺失"}]
    m = re.search(r"public\s+record\s+PageResult\s*<[^>]*>\s*\(([^)]*)\)", text)
    if not m:
        return [{"check": "D", "file": label, "op": "-", "ok": False,
                 "detail": "未找到 PageResult record 定义"}]
    comps = [c.strip().split()[-1] for c in m.group(1).split(",") if c.strip()]
    return [{
        "check": "D", "file": label, "op": "record-components",
        "ok": comps[:1] == [EXPECTED_KEY],
        "detail": f"PageResult 分量 = {comps!r}"
        + ("" if comps[:1] == [EXPECTED_KEY]
           else f"，首分量应为 {EXPECTED_KEY!r}（序列化后的集合键名）"),
    }]


# --------------------------------------------------------------------------- E
LISTY_FIELD_RE = re.compile(r"^\s*(items|list|records|rows)\??:\s*(.+?)\s*$", re.MULTILINE)


def audit_client(api_dir: str, root: str) -> list[dict]:
    label = rel(api_dir, root)
    if not os.path.isdir(api_dir):
        return [{"check": "E", "file": label, "op": "-", "ok": False, "detail": "目录缺失"}]
    rows = []
    for name in sorted(os.listdir(api_dir)):
        if not name.endswith(".ts"):
            continue
        fpath = os.path.join(api_dir, name)
        text = read_text(fpath) or ""
        # 找出「声明了列表响应字段」的 interface 块
        blocks = re.split(r"^export\s+interface\s+", text, flags=re.MULTILINE)[1:]
        for blk in blocks:
            iface = blk.split("{", 1)[0].strip()
            body = blk
            fields = {m.group(1) for m in LISTY_FIELD_RE.finditer(body)}
            if not fields:
                continue
            rows.append({
                "check": "E", "file": f"{rel(fpath, root)}#{iface}", "op": iface,
                "ok": EXPECTED_KEY in fields,
                "detail": f"声明字段 = {sorted(fields)!r}"
                + ("" if EXPECTED_KEY in fields
                   else f"，列表响应必须声明 {EXPECTED_KEY!r}（客户端真源）"),
            })
    if not rows:
        rows.append({"check": "E", "file": label, "op": "-", "ok": False,
                     "detail": "未在客户端 api 层发现任何列表响应接口（匹配逻辑可疑）"})
    return rows


# --------------------------------------------------------------------------- F
def audit_manifest(path: str, root: str) -> list[dict]:
    label = rel(path, root)
    text = read_text(path)
    if text is None:
        return [{"check": "F", "file": label, "op": "-", "ok": False, "detail": "文件缺失"}]
    ok = "data:{items:" in text.replace(" ", "")
    return [{
        "check": "F", "file": label, "op": "§0-分页约定", "ok": ok,
        "detail": "§0 写明 data:{items:…}" if ok
        else "§0 未写明 data:{items:…}（分页字段名约定缺失）",
    }]


def main(argv: list[str]) -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    as_json = "--json" in argv
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]

    openapi = os.path.join(root, "docs", "backend", "openapi.yaml")
    page_schema = os.path.join(root, "docs", "backend", "json-schema", "common", "page.schema.json")
    runtime = os.path.join(root, "aap-server", "src", "main", "java", "com", "hioas", "aap",
                           "common", "PageResult.java")
    client_api = os.path.join(root, "aap-client", "src", "api")
    manifest = os.path.join(root, "docs", "backend", "02-API接口模型清单.md")

    key_rows, wrap_rows = audit_openapi(openapi, root)
    rows = key_rows + wrap_rows
    rows += audit_page_schema(page_schema, root)
    rows += audit_runtime(runtime, root)
    rows += audit_client(client_api, root)
    rows += audit_manifest(manifest, root)

    fails = [r for r in rows if not r["ok"]]
    by_check: dict[str, list[dict]] = {}
    for r in rows:
        by_check.setdefault(r["check"], []).append(r)

    if as_json:
        print(json.dumps({"root": root, "rows": rows,
                          "total": len(rows), "failed": len(fails)}, ensure_ascii=False, indent=2))
        return 1 if fails else 0

    titles = {
        "A": "A. OpenAPI 分页集合键名（应为 items）",
        "B": "B. OpenAPI 分页端点必须被 PageMeta 包装",
        "C": "C. page.schema.json 必须 required/properties 含 items",
        "D": "D. 运行时 PageResult 分量名",
        "E": "E. 客户端列表响应接口必须声明 items",
        "F": "F. 冻结清单 §0 分页字段名约定",
    }
    for chk in ("A", "B", "C", "D", "E", "F"):
        group = by_check.get(chk, [])
        bad = [r for r in group if not r["ok"]]
        print(f"== {titles[chk]}：{len(group) - len(bad)}/{len(group)} PASS ==")
        if chk == "A":
            keys = {}
            for r in group:
                keys.setdefault(r.get("key") or "(未定位)", []).append(r["op"])
            for k, ops in sorted(keys.items()):
                mark = "OK " if k == EXPECTED_KEY else "BAD"
                print(f"   [{mark}] 集合键名 {k}：{len(ops)} 个端点 → {' '.join(ops[:8])}"
                      + (" …" if len(ops) > 8 else ""))
        if chk == "B" and not bad:
            print(f"   [OK ] 全部 {len(group)} 个带 pageSize 参数的端点均已 PageMeta 包装")
        for r in group:
            if not r["ok"]:
                print(f"   [FAIL] {r['file']} {r['op']}：{r['detail']}")
        if chk in ("C", "D", "E", "F") and not bad:
            for r in group[:3]:
                print(f"   [OK ] {r['file']} {r['op']}：{r['detail']}")
            if len(group) > 3:
                print(f"   [OK ] …另有 {len(group) - 3} 条同样 PASS")
        print()

    print(f"合计 {len(rows)} 条断言：PASS {len(rows) - len(fails)}，FAIL {len(fails)}")
    if fails:
        print("结论：集合键名契约在多个真源之间**不一致**（见上 FAIL 行）。")
    else:
        print("结论：分页集合键名在 OpenAPI / JSON Schema / 运行时 / 客户端 / 清单五处一致。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
