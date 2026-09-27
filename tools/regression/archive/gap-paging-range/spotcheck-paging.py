#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R56 抽查：分页参数「取值域 / 越界行为」一致性（第三十类可审计不变量）。

为什么两套门禁都看不见：
  * 契约测试只把**响应体**与 JSON Schema 比对 —— 分页**请求参数**（page/pageSize）不是响应体，
    query 参数在 schema 里根本不存在；响应里回显的 pageSize 是「夹取后」的值，故「夹取口径」漂移全绿；
  * 覆盖门禁只比「方法 + 路径」，不比参数语义；
  * openapi.yaml 与客户端 TS 不被任何测试读取/执行。

真源六处（逐处比对）：
  M1 = md §0 通用约定「分页」行：`page`（默认 1）/ `pageSize`（默认 20，上限 200）
  M2 = md 逐端点「请求」列的 q：分页声明（端点集合，与 openapi 参数集合对账）
  I1 = 实现 PageQuery（DEFAULT_PAGE_SIZE / MAX_PAGE_SIZE 常量 + of() 缺省与夹取语义）
  I2 = 控制器 @RequestParam 声明（required / defaultValue）
  I3 = 是否存在绕过 PageQuery 的分页写点（手写 limit 字面量）
  O1 = openapi.yaml 每个 operation 的 page/pageSize 参数 schema（type/minimum/maximum/default）
  S1 = 契约 page.schema.json 的 page/pageSize 范围
  C1 = 客户端传参实参（pageSize 字面量取值集合 / 是否有夹取）
  T1 = 测试对越界行为（page=0 / pageSize 超上限 / 负数）的断言

只读脚本：不写任何文件（自测里对夹具副本的写入是显式指定的 --root）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

FAIL_RE = re.compile(r"\[FAIL\s*\]")
OUT: list[str] = []


def emit(tag: str, name: str, msg: str) -> None:
    OUT.append(f"[{tag}] {name}: {msg}")


def rel(root: pathlib.Path, p: pathlib.Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------- M1 / M2
def parse_md(root: pathlib.Path) -> dict:
    md = root / "docs/backend/02-API接口模型清单.md"
    text = md.read_text(encoding="utf-8", errors="replace") if md.exists() else ""
    lines = text.splitlines()
    m1: dict = {"page_default": None, "pageSize_default": None, "max": None, "line": None}
    for ln in lines:
        if "分页" in ln and "pageSize" in ln and "默认" in ln and ln.lstrip().startswith("|"):
            defaults = re.findall(r"默认\s*(\d+)", ln)
            mx = re.search(r"上限\s*(\d+)", ln)
            if len(defaults) >= 2 and mx:
                m1["page_default"] = int(defaults[0])
                m1["pageSize_default"] = int(defaults[1])
                m1["max"] = int(mx.group(1))
                m1["line"] = ln
                break
    # M2：逐端点「请求」列里的 q：分页声明（两种写法：q：`page` `pageSize` / 裸 page/pageSize）
    eps: dict[str, list[str]] = {}
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = re.split(r"(?<!\\)\|", ln)
        if len(cells) < 5:
            continue
        eid = cells[1].strip().strip("`")
        if not re.fullmatch(r"[A-Z]+-[A-Z0-9]+", eid or ""):
            continue
        req = " ".join(cells[4:])
        if "pageSize" in req:
            eps[eid] = re.findall(r"`?([a-zA-Z][A-Za-z0-9]*)`?", req)
    return {"M1": m1, "M2": eps}


# ---------------------------------------------------------------- I1 / I2 / I3
def parse_impl(root: pathlib.Path) -> dict:
    pq = root / "aap-server/src/main/java/com/hioas/aap/common/PageQuery.java"
    txt = pq.read_text(encoding="utf-8", errors="replace") if pq.exists() else ""
    d: dict = {"file": rel(root, pq), "default_page_size": None, "max_page_size": None,
               "clamps": False, "page_floor": False, "throws": False}
    m = re.search(r"DEFAULT_PAGE_SIZE\s*=\s*(\d+)", txt)
    if m:
        d["default_page_size"] = int(m.group(1))
    m = re.search(r"MAX_PAGE_SIZE\s*=\s*(\d+)", txt)
    if m:
        d["max_page_size"] = int(m.group(1))
    d["clamps"] = bool(re.search(r"Math\.min\(\s*pageSize\s*,\s*MAX_PAGE_SIZE\s*\)", txt))
    d["page_floor"] = bool(re.search(r"page\s*<\s*1\s*\?\s*1", txt))
    d["throws"] = bool(re.search(r"throw\s+new\s+\w*(IllegalArgument|BadRequest|Validation)", txt))

    params: list[tuple[str, str]] = []
    with_default = 0
    for p in sorted((root / "aap-server/src/main/java").rglob("*.java")):
        src = p.read_text(encoding="utf-8", errors="replace")
        if "@RequestParam" not in src:
            continue
        for m in re.finditer(r"@RequestParam\(([^)]*)\)\s*(?:final\s+)?Integer\s+(page|pageSize)\b", src):
            params.append((rel(root, p), m.group(1)))
            if "defaultValue" in m.group(1):
                with_default += 1
    # 手写分页：limit <字面量>（>1）或 limit <字面量> offset —— 绕过 clamp 的候选；
    # `limit 1`（单行取回）与 `limit ? offset ?`（PageQuery 驱动）都不是分页绕过。
    # 正面对照：另计「PageQuery/JdbcTemplate 驱动的 limit ? offset ?」语句数，>0 才说明判据看得见分页。
    bypass: list[str] = []
    driven = 0
    for p in sorted((root / "aap-server/src/main/java").rglob("*.java")):
        src = p.read_text(encoding="utf-8", errors="replace")
        driven += len(re.findall(r"limit\s+\?\s*\n?\s*offset\s+\?", src, re.IGNORECASE))
        for m in re.finditer(r"limit\s+(\d+)\s*(offset\s+\d+)?", src, re.IGNORECASE):
            n = int(m.group(1))
            if n > 1 or m.group(2):
                bypass.append(f"{rel(root, p)}:limit {n}{' ' + m.group(2) if m.group(2) else ''}")
    return {"I1": d, "I2": params, "I2_default": with_default, "I3": bypass, "I3_driven": driven}


# ---------------------------------------------------------------- O1
def parse_openapi(root: pathlib.Path) -> dict:
    oa = root / "docs/backend/openapi.yaml"
    txt = oa.read_text(encoding="utf-8", errors="replace") if oa.exists() else ""
    lines = txt.splitlines()
    blocks: list[dict] = []
    for i, ln in enumerate(lines):
        m = re.match(r"\s*-\s*name:\s*(page|pageSize)\s*$", ln)
        if not m:
            continue
        name = m.group(1)
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not re.match(r"\s*-\s*name:\s", lines[j]) and "responses:" not in lines[j]:
            body.append(lines[j])
            j += 1
        blob = "\n".join(body)
        sch = {}
        mm = re.search(r"schema:\s*\n((?:\s+.*\n?)+)", blob)
        if mm:
            schblob = mm.group(1)
            t = re.search(r"type:\s*(\w+)", schblob)
            mn = re.search(r"minimum:\s*(-?\d+)", schblob)
            mx = re.search(r"maximum:\s*(-?\d+)", schblob)
            df = re.search(r"default:\s*(-?\d+)", schblob)
            sch = {"type": t.group(1) if t else None,
                   "minimum": int(mn.group(1)) if mn else None,
                   "maximum": int(mx.group(1)) if mx else None,
                   "default": int(df.group(1)) if df else None}
        blocks.append({"name": name, "line": i + 1, "schema": sch, "in": "in: query" in blob})
    return {"O1": blocks}


# ---------------------------------------------------------------- S1
def parse_page_schema(root: pathlib.Path) -> dict:
    f = root / "docs/backend/json-schema/common/page.schema.json"
    if not f.exists():
        return {"S1": None}
    d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
    props = d.get("properties", {})
    return {"S1": {"required": d.get("required", []),
                   "page": props.get("page", {}),
                   "pageSize": props.get("pageSize", {})}}


# ---------------------------------------------------------------- C1
def parse_client(root: pathlib.Path) -> dict:
    cdir = root / "aap-client/src"
    lits: list[tuple[str, int]] = []
    clamps = 0
    if cdir.exists():
        for p in sorted(cdir.rglob("*")):
            if p.suffix not in (".ts", ".vue"):
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"pageSize\s*:\s*(\d+)", src):
                lits.append((rel(root, p), int(m.group(1))))
            clamps += len(re.findall(r"Math\.(?:min|max)\([^)]*pageSize", src))
    return {"C1": lits, "C1_clamp": clamps}


# ---------------------------------------------------------------- T1
def parse_tests(root: pathlib.Path) -> dict:
    tdir = root / "aap-server/src/test/java"
    hits: list[str] = []
    if tdir.exists():
        for p in sorted(tdir.rglob("*.java")):
            src = p.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"page=(\d+)&(?:amp;)?pageSize=(\d+)", src):
                pg, ps = int(m.group(1)), int(m.group(2))
                if pg < 1 or ps < 1 or ps > 200:
                    hits.append(f"{rel(root, p)}:page={pg}&pageSize={ps}")
            for m in re.finditer(r'path\("pageSize"\)\.asInt\(\)\)\.isEqualTo\((\d+)\)', src):
                if int(m.group(1)) > 200:
                    hits.append(f"{rel(root, p)}:assert pageSize=={m.group(1)}")
    return {"T1": hits}


def run(root: pathlib.Path) -> int:
    md = parse_md(root)
    impl = parse_impl(root)
    oa = parse_openapi(root)
    sch = parse_page_schema(root)
    cli = parse_client(root)
    tst = parse_tests(root)

    m1, m2 = md["M1"], md["M2"]
    i1, i2, i3 = impl["I1"], impl["I2"], impl["I3"]
    blocks = oa["O1"]
    s1 = sch["S1"]
    page_blocks = [b for b in blocks if b["name"] == "page"]
    size_blocks = [b for b in blocks if b["name"] == "pageSize"]

    emit("INFO", "M2", f"md 逐端点声明分页的端点 {len(m2)} 条（openapi pageSize 参数 {len(size_blocks)} 个）")

    # ---- A0 正向对照（每源必须解析到 > 0 条，否则判「解析器失效」）
    emit("PASS" if m1["line"] else "FAIL", "A0a",
         f"md §0 分页行解析：page 默认={m1['page_default']} / pageSize 默认={m1['pageSize_default']} / 上限={m1['max']}")
    emit("PASS" if (i1["default_page_size"] and i1["max_page_size"]) else "FAIL", "A0b",
         f"实现常量解析：DEFAULT_PAGE_SIZE={i1['default_page_size']} / MAX_PAGE_SIZE={i1['max_page_size']}")
    emit("PASS" if page_blocks else "FAIL", "A0c", f"openapi 解析到 page/pageSize 参数块 {len(blocks)} 个")
    emit("PASS" if impl["I2"] else "FAIL", "A0d", f"控制器 @RequestParam(page/pageSize) 解析到 {len(impl['I2'])} 处")
    emit("PASS" if cli["C1"] else "FAIL", "A0e", f"客户端 pageSize 字面量实参解析到 {len(cli['C1'])} 处")
    emit("PASS" if tst["T1"] else "FAIL", "A0f", f"测试越界行为断言解析到 {len(tst['T1'])} 处（page=0 / pageSize>200）")
    if s1 is None:
        emit("FAIL", "A0g", "page.schema.json 未解析到")
    else:
        emit("PASS", "A0g", f"契约 page.schema.json 解析到 page/pageSize 属性（required={s1['required']}）")

    # ---- A1/A2：实现 ⇔ md §0
    emit("PASS" if i1["default_page_size"] == m1["pageSize_default"] else "FAIL", "A1",
         f"缺省页大小：实现 {i1['default_page_size']} vs md §0 {m1['pageSize_default']}")
    emit("PASS" if i1["max_page_size"] == m1["max"] else "FAIL", "A2",
         f"页大小上限：实现 {i1['max_page_size']} vs md §0 {m1['max']}")
    emit("PASS" if i1["clamps"] and i1["page_floor"] and not i1["throws"] else "FAIL", "A2b",
         f"越界语义：夹取={i1['clamps']} / page 下限回 1={i1['page_floor']} / 不抛错={not i1['throws']}")

    # ---- A3：契约 schema ⇔ 实现
    if s1:
        ps = s1["pageSize"]
        emit("PASS" if ps.get("maximum") == i1["max_page_size"] else "FAIL", "A3",
             f"page.schema.json.pageSize.maximum={ps.get('maximum')} vs 实现上限 {i1['max_page_size']}")
        emit("PASS" if ps.get("minimum") == 1 and s1["page"].get("minimum") == 1 else "FAIL", "A3b",
             f"page/pageSize minimum：{s1['page'].get('minimum')}/{ps.get('minimum')}")

    # ---- A4/A5：openapi query 参数 ⇔ md §0（生成物侧）
    with_max = [b for b in size_blocks if b["schema"].get("maximum") == i1["max_page_size"]]
    emit("PASS" if len(with_max) == len(size_blocks) and size_blocks else "FAIL", "A4",
         f"openapi 声明 pageSize 上限 {i1['max_page_size']} 的 operation：{len(with_max)}/{len(size_blocks)}")
    with_def = [b for b in size_blocks if b["schema"].get("default") == m1["pageSize_default"]]
    emit("PASS" if len(with_def) == len(size_blocks) and size_blocks else "FAIL", "A5",
         f"openapi 声明 pageSize 默认值 {m1['pageSize_default']} 的 operation：{len(with_def)}/{len(size_blocks)}")
    with_pdef = [b for b in page_blocks if b["schema"].get("default") == m1["page_default"]]
    emit("PASS" if len(with_pdef) == len(page_blocks) and page_blocks else "FAIL", "A5b",
         f"openapi 声明 page 默认值 {m1['page_default']} 的 operation：{len(with_pdef)}/{len(page_blocks)}")

    # ---- A6：控制器声明语义（required=false → 缺省由服务层兜底，与 md 缺省容忍一致）
    req_true = [p for p in impl["I2"] if "required = true" in p[1] or "required=true" in p[1]]
    emit("PASS" if not req_true else "FAIL", "A6",
         f"控制器把 page/pageSize 声明为必填的处数={len(req_true)}（应为 0，缺省容忍）；"
         f"带 defaultValue 的处数={impl['I2_default']}（0 = 缺省由 PageQuery 兜底）")

    # ---- A7：无绕过 PageQuery 的手写分页（`limit 1` 单行取回不属分页域）
    emit("PASS" if not i3 else "FAIL", "A7",
         f"手写 limit 字面量（>1 或带 offset）的分页写点 {len(i3)} 处（应为 0）；"
         f"PageQuery/JdbcTemplate 驱动的 `limit ? offset ?` 语句 {impl['I3_driven']} 处（正向对照 > 0）")
    emit("PASS" if impl["I3_driven"] > 0 else "FAIL", "A0h",
         f"分页语句正向对照：解析到 `limit ? offset ?` {impl['I3_driven']} 处")

    # ---- A8：客户端传参取值域
    bad = [x for x in cli["C1"] if x[1] < 1 or x[1] > 200]
    emit("PASS" if not bad else "FAIL", "A8",
         f"客户端 pageSize 字面量越界 {len(bad)} 处（取值集合 {sorted({v for _, v in cli['C1']})}）；"
         f"客户端夹取逻辑 {cli['C1_clamp']} 处（上限由服务端夹取，客户端只传固定页大小）")

    fails = [l for l in OUT if FAIL_RE.search(l)]
    passes = [l for l in OUT if l.startswith("[PASS]")]
    print(f"# R56 抽查：分页参数取值域一致性（第三十类可审计不变量） root={root}")
    for l in OUT:
        print(l)
    print(f"汇总：PASS {len(passes)} / FAIL {len(fails)} / INFO {len([l for l in OUT if l.startswith('[INFO]')])}")
    return 1 if fails else 0


def md5_tree(root: pathlib.Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--snapshot", action="store_true", help="打印被测根目录全部文件 md5（只读守卫用）")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    if a.snapshot:
        for k, v in md5_tree(root).items():
            print(f"{v}  {k}")
        return 0
    return run(root)


if __name__ == "__main__":
    sys.exit(main())
