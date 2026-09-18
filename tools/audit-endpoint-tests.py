#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端点「真实 HTTP 用例」可追溯性审计（**只读**，不写业务代码、不改测试）。

背景：`EndpointCoverageTest` 只比对 Spring 路由注册表与清单（证明「路由已注册」），
**不证明「每条端点都有真实 HTTP 用例」**。本脚本补上这一层。

关键事实（否则会得出「90/90 都没有用例」的假结论）：集成测试走 `ApiTestBase`，
测试里写的路径**不含 `/api/v1` 前缀**（基类 `URI.create(baseUrl() + "/api/v1" + path)`），
且路径变量常写成 `"/credentials/" + id + "/precheck"` 这种**字符串拼接**。
因此匹配要同时处理：① 去掉/保留 `/api/v1` 前缀两种写法；② `{var}` → 裸标识符或 `" + expr + "` 拼接。

判定：
  - `exact` : 命中完整路径骨架且该行是一次 HTTP 调用 → 强证据；
  - `prefix`: 只命中首个变量之前的静态前缀（弱证据，需人工确认）；
  - `none`  : 无任何调用点 → **真发现**（该端点只有路由注册，没有 HTTP 用例）。

产出（供定时巡检取证）：
  `.agents/state/evidence/endpoint-test-audit.json`  —— 机器可读逐条结果
  `.agents/state/evidence/endpoint-test-audit.txt`   —— 人类可读摘要
退出码：0 = 每条端点都有调用点（exact/prefix 均可）；1 = 存在 none。

ID 可追溯性三档（R23 修正：R22 曾因只做裸子串判断误报「19 条 ID 不可追溯」）：
  1. 裸字面量命中 `AUTH-05`；
  2. **组合引用**命中：`AUTH-05/06`、`PROV-03/04/05`（枚举）、`DET-01…06`（区间）；
  3. 更严一档：ID 引用必须与真实 HTTP 调用点**落在同一文件**。
判别力由 `tools/audit-endpoint-tests-selftest.py` 的负向自测保证（区间不得外溢、
未被提及的 ID 必须判不可追溯、短路径不得在长路径里当子串命中）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs" / "backend" / "endpoints.json"
DEFAULT_TESTS_DIR = ROOT / "aap-server" / "src" / "test" / "java"
EVIDENCE_DIR = ROOT / ".agents" / "state" / "evidence"


def _arg(flag: str, default: Path) -> Path:
    """极简 `--flag value` 解析（支持负向自测：换一份含假端点的清单）。"""
    argv = sys.argv[1:]
    if flag in argv:
        return Path(argv[argv.index(flag) + 1]).resolve()
    return default


MANIFEST = _arg("--manifest", DEFAULT_MANIFEST)
TESTS_DIR = _arg("--tests-dir", DEFAULT_TESTS_DIR)
WRITE_EVIDENCE = "--no-evidence" not in sys.argv

HTTP_CALL = re.compile(r"(?<![A-Za-z0-9_])(get|post|put|delete|patch|send)\s*\(")
PATH_VAR = re.compile(r"\{[^}]+\}")
VAR_ALT = (r'(?:"\s*\+\s*[A-Za-z0-9_.()\[\]"\' ]+\s*\+\s*"'
           r'|"\s*\+\s*[A-Za-z0-9_.()\[\]]+'
           r'|[A-Za-z0-9_.()\[\]]+)')
API_PREFIX = "/api/v1"

# 项目既有约定：同一族端点常写成**组合引用**，例如 `AUTH-05/06`、`PROV-03/04/05`、
# `ADM-CFG01…05`、`QT-01…11；AC-22…27`。只做 `ep["id"] in text` 的裸子串判断会把
# 这些引用全部漏掉 → 得出「19 条端点 ID 不可追溯」的**假发现**（踩坑 29 同族：
# 审计脚本必须对齐被测代码的真实书写约定，否则「0 发现/假发现」无法区分）。
GROUPED_ID = re.compile(r"([A-Z]+(?:-[A-Z]+)*-?)(\d+)((?:\s*(?:/|…|\.\.\.)\s*\d+)*)")


def referenced_ids(text: str, known: set[str]) -> set[str]:
    """从源码里抽出被引用的端点 ID（含 `/` 枚举与 `…` 区间的组合引用）。

    注意清单里并存两种书写：`AUTH-05`（前缀后带连字符）与 `ADM-CFG01`（连字符后直接接数字），
    因此保留匹配到的前缀原文（含可能的尾连字符）再拼数字，两种都能还原。
    候选串一律回查 `known`（清单 ID 全集）后才算命中，避免凭空构造出不存在的 ID。
    """
    found: set[str] = set()
    for m in GROUPED_ID.finditer(text):
        base, first = m.group(1), int(m.group(2))
        prev = first
        seq: list[int] = [first]
        for sep, num in re.findall(r"(\s*(?:/|…|\.\.\.)\s*)(\d+)", m.group(3)):
            n = int(num)
            if "…" in sep or "..." in sep:      # 区间：补齐中间值
                seq.extend(range(min(prev, n), max(prev, n) + 1))
            else:                               # 枚举
                seq.append(n)
            prev = n
        for n in seq:
            for cand in (f"{base}{n}", f"{base}{n:02d}"):
                if cand in known:
                    found.add(cand)
    return found

# 调用助手名 → 它实际发出的 HTTP 方法（send 显式传 method，视为方法未定）
HELPER_METHOD = {"get": "GET", "post": "POST", "put": "PUT", "delete": "DELETE", "patch": "PATCH"}


def skeleton_regex(path: str) -> re.Pattern[str]:
    """把 `/a/{id}/b` 变成能匹配 `/a/123/b` 与 `/a/" + id + "/b` 的正则。"""
    parts = PATH_VAR.split(path)
    body = ""
    for i, part in enumerate(parts):
        body += re.escape(part)
        if i < len(parts) - 1:
            body += VAR_ALT
    # 尾部边界：防止短路径在长路径里**当子串**命中（`/syn/probe` 会匹配 `/syn/probe/only-post`，
    # 若两者方法又恰好相同，短端点就会白捡一个 exact 假证据）。
    return re.compile(body + r"(?![A-Za-z0-9_/])")


def variants(path: str) -> list[str]:
    out = [path]
    if path.startswith(API_PREFIX):
        stripped = path[len(API_PREFIX):]
        if stripped:
            out.append(stripped)
    return out


def line_of(text: str, pos: int) -> str:
    ls = text.rfind("\n", 0, pos) + 1
    le = text.find("\n", pos)
    return text[ls: le if le != -1 else len(text)].strip()


def is_code(line: str) -> bool:
    """排除注释行（`// post("/x", …)` 与 javadoc `* post(…)` 不算用例）。"""
    stripped = line.lstrip()
    return not (stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"))


def rel_path(p: Path) -> str:
    """仓库内用相对路径展示；仓库外（负向自测用的临时清单）直接给绝对路径。"""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def main() -> int:
    if not MANIFEST.exists():
        print(f"清单缺失：{MANIFEST}（先跑 python tools/gen-backend-models.py）", file=sys.stderr)
        return 2
    endpoints = json.loads(MANIFEST.read_text(encoding="utf-8"))["endpoints"]
    known_ids = {ep["id"] for ep in endpoints}

    sources: dict[str, str] = {}
    for f in sorted(TESTS_DIR.rglob("*.java")):
        # 用 rel_path()：`--tests-dir` 指向仓库外（负向自测夹具）时 relative_to(ROOT) 会抛 ValueError
        sources[rel_path(f)] = f.read_text(encoding="utf-8", errors="replace")

    # 逐文件预抽 ID 引用（组合引用已展开），避免每条端点重复扫描
    file_ids: dict[str, set[str]] = {rel: referenced_ids(text, known_ids)
                                     for rel, text in sources.items()}

    rows = []
    for ep in endpoints:
        raw_path = ep["path"]
        exact: list[dict] = []
        weak: list[dict] = []
        id_refs = sorted(rel for rel, ids in file_ids.items() if ep["id"] in ids)
        id_refs_literal = sorted(rel for rel, text in sources.items() if ep["id"] in text)

        regexes = [skeleton_regex(v) for v in variants(raw_path)]
        # 弱证据：首个变量之前的静态前缀（保留 /api/v1 与去前缀两种写法）
        prefixes = [v.split("{", 1)[0] for v in variants(raw_path) if "{" in v]
        prefixes = [p for p in prefixes if len(p) > 6]

        for rel, text in sources.items():
            for rx in regexes:
                for m in rx.finditer(text):
                    line = line_of(text, m.start())
                    call = HTTP_CALL.search(line)
                    if not call or not is_code(line):
                        continue
                    helper = call.group(1)
                    hit = {"file": rel, "line": line[:200], "helper": helper}
                    if HELPER_METHOD.get(helper, ep["method"]) == ep["method"]:
                        exact.append(hit)      # 方法也吻合 → 强证据
                    else:
                        weak.append(hit)       # 路径命中但方法不同/send 未定 → 弱证据
            for p in prefixes:
                for m in re.finditer(re.escape(p), text):
                    line = line_of(text, m.start())
                    if HTTP_CALL.search(line) and is_code(line):
                        weak.append({"file": rel, "line": line[:200], "helper": None})

        kind = "exact" if exact else ("prefix" if weak else "none")
        # 更严的一档：ID 引用必须落在**同时含真实 HTTP 调用点**的同一文件里，
        # 否则「类注释里列了 ID、文件里却没人调」会冒充可追溯（假绿）。
        exact_files = {h["file"] for h in exact}
        id_refs_with_call = [f for f in id_refs if f in exact_files]
        rows.append({
            "id": ep["id"], "method": ep["method"], "path": raw_path,
            "task": ep.get("task"), "tag": ep.get("tag"),
            "evidence": kind,
            "id_refs": id_refs,
            "id_refs_with_call": id_refs_with_call,
            "id_refs_literal": id_refs_literal,
            "id_grouped_only": bool(id_refs) and not id_refs_literal,
            "exact_sites": len(exact), "prefix_sites": len(weak),
            "exact_sample": exact[:2], "prefix_sample": weak[:2],
        })

    none_rows = [r for r in rows if r["evidence"] == "none"]
    prefix_rows = [r for r in rows if r["evidence"] == "prefix"]
    no_id_ref = [r for r in rows if not r["id_refs"]]
    grouped_only = [r for r in rows if r["id_grouped_only"]]
    no_id_with_call = [r for r in rows if not r["id_refs_with_call"]]

    report = {
        "total": len(rows),
        "exact": sum(1 for r in rows if r["evidence"] == "exact"),
        "prefix": len(prefix_rows),
        "none": len(none_rows),
        "id_traceable": len(rows) - len(no_id_ref),
        "id_traceable_literal_only": sum(1 for r in rows if r["id_refs_literal"]),
        "id_grouped_only": len(grouped_only),
        "id_traceable_same_file_as_call": len(rows) - len(no_id_with_call),
        "id_not_traceable": [r["id"] for r in no_id_ref],
        "id_not_traceable_same_file_as_call": [r["id"] for r in no_id_with_call],
        "none_ids": [r["id"] for r in none_rows],
        "prefix_ids": [r["id"] for r in prefix_rows],
        "endpoints": rows,
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    if WRITE_EVIDENCE:
        (EVIDENCE_DIR / "endpoint-test-audit.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "端点「真实 HTTP 用例」可追溯性审计（只读）",
        f"清单：{rel_path(MANIFEST)}（{report['total']} 条）",
        f"测试源：{rel_path(TESTS_DIR)}（{len(sources)} 个 .java 文件）",
        "",
        f"exact （路径骨架 + 方法都吻合的真实 HTTP 调用点）：{report['exact']}",
        f"prefix（路径命中但方法不吻合 / 仅静态前缀，弱证据）：{report['prefix']}",
        f"none  （无任何调用点 —— 真发现）            ：{report['none']}",
        f"端点 ID 在测试源里可追溯（含组合引用展开）  ：{report['id_traceable']}/{report['total']}",
        f"  其中仅裸字面量可追溯                      ：{report['id_traceable_literal_only']}/{report['total']}",
        f"  靠组合引用（`A-05/06`、`A-01…05`）才算命中  ：{report['id_grouped_only']}",
        f"ID 引用与真实 HTTP 调用点同文件（更严一档）  ：{report['id_traceable_same_file_as_call']}/{report['total']}",
        "",
    ]
    if none_rows:
        lines.append("== none 明细（只有路由注册，未找到真实 HTTP 用例）==")
        for r in none_rows:
            lines.append(f"  {r['id']:<10} {r['method']:<6} {r['path']:<48} task={r['task']} id_refs={len(r['id_refs'])}")
        lines.append("")
    if prefix_rows:
        lines.append("== prefix 明细（弱证据：仅静态前缀命中）==")
        for r in prefix_rows:
            sample = r["prefix_sample"][0]["line"] if r["prefix_sample"] else ""
            lines.append(f"  {r['id']:<10} {r['method']:<6} {r['path']:<48} sites={r['prefix_sites']} 例：{sample}")
        lines.append("")
    if no_id_ref:
        lines.append("== 测试源里未出现端点 ID 的端点（可追溯性缺口，不影响「有用例」判定）==")
        lines.append("  " + ", ".join(r["id"] for r in no_id_ref))
        lines.append("")
    if no_id_with_call:
        lines.append("== ID 引用与真实 HTTP 调用点**不同文件**的端点（弱可追溯）==")
        lines.append("  " + ", ".join(r["id"] for r in no_id_with_call))
        lines.append("")

    text = "\n".join(lines) + "\n"
    if WRITE_EVIDENCE:
        (EVIDENCE_DIR / "endpoint-test-audit.txt").write_text(text, encoding="utf-8")
    print(text)
    return 1 if none_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
