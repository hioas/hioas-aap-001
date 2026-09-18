#!/usr/bin/env python3
"""`tools/audit-id-types.py` 的负向自测（R38）。

每个判定分支一条反例（skill 坑 32：判定有几个分支，自测就要有几条反例），外加：
  * **正向对照**：`ok` 夹具必须 rc=0（只有反例时「一直在报错」会被当成合格，坑 46）；
  * **空夹具必须变红**（解析器失效不得判 PASS，坑 46 / 72 / 75）；
  * **注入缺陷判别力**（坑 57 / 66）：
      inj#1 往**真实仓库副本**注入一处真实漂移（`provider_id` 改成 integer）→ 必须**恰好** A1 转红；
      inj#2 拆掉审计里的 A4 判据 → `c_number` 夹具必须**不再**报 A4（证明该守卫有判别力）；
      inj#3 拆掉审计里的 A6 判据 → `name_conflict` 夹具必须**不再**报 A6；
    每个注入都先断言**真的改到了源码**（锚点未命中 → 空转通过，坑 66）；
  * **零写副作用**：夹具目录与仓库文件在运行前后 md5 全等。

用法：python tools/audit-id-types-selftest.py
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
AUDIT = TOOLS / "audit-id-types.py"
REPO = TOOLS.parent

ER_OK = (
    "# ER 数据模型（夹具）\n\n"
    "**aap_channel_binding**：`provider_id`、`credential_id`、`endpoint_id`、"
    "`channel_id`(new-api)、`channel_name UQ`、`status`。\n"
    "**aap_usage_hourly**：`stat_hour`、`channel_id`、`model_name`。\n"
)


def schema(props: dict) -> str:
    return json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema",
                       "title": "fixture", "type": "object",
                       "properties": props, "additionalProperties": False},
                      ensure_ascii=False, indent=2)


def openapi(comps: dict[str, str], inline_id: bool = False) -> str:
    lines = ["openapi: 3.0.3", "info:", "  title: fixture", "  version: 1.0.0",
             "paths: {}", "components:", "  schemas:"]
    for name, target in comps.items():
        lines += [f"    {name}:", f"      $ref: {target}"]
    lines += ["    Role:", "      type: string", "      enum:", "        - PROVIDER"]
    if inline_id:
        lines += ["    BadInline:", "      type: object", "      properties:",
                  "        id:", "          type: string"]
    return "\n".join(lines) + "\n"


def views(channel_type: str = "Integer", id_type: str = "String") -> str:
    return ("package com.hioas.aap.sync;\n\n"
            "import com.fasterxml.jackson.annotation.JsonProperty;\n\n"
            "public final class SyncViews {\n"
            "    private SyncViews() {\n    }\n\n"
            "    public record Binding(\n"
            f'            @JsonProperty("channel_id") {channel_type} channelId,\n'
            f'            @JsonProperty("id") {id_type} id) {{\n'
            "    }\n}\n")


SERVICE = ("package com.hioas.aap.sync;\n\n"
           "// channel_id 在库里是 bigint（ER：new-api 渠道号），视图契约是 integer：按 Long 读再收窄\n"
           "public class SyncAdminService {\n}\n")

CLIENT_TS = ("export interface X {\n"
             "  id: string\n"
             "}\n")


def base_files() -> dict[str, str]:
    return {
        "docs/backend/01-ER数据模型.md": ER_OK,
        "docs/backend/openapi.yaml": openapi(
            {"UsageSummary": "./json-schema/models/usage-summary.schema.json",
             "ChannelBinding": "./json-schema/models/channel-binding.schema.json"}),
        "docs/backend/json-schema/models/usage-summary.schema.json": schema(
            {"provider_id": {"type": ["string", "null"]}, "request_count": {"type": "integer"}}),
        "docs/backend/json-schema/models/channel-binding.schema.json": schema(
            {"id": {"type": ["string", "null"]}, "channel_id": {"type": ["integer", "null"]}}),
        "aap-server/src/main/java/com/hioas/aap/sync/SyncViews.java": views(),
        "aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java": SERVICE,
        "aap-client/src/m.ts": CLIENT_TS,
    }


def write_case(files: dict[str, str], tag: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"idtypes-{tag}-"))
    for rel, content in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return d


def run(root: Path, script: Path = AUDIT) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(script), "--root", str(root), "--all"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def fails(out: str) -> list[str]:
    return [ln[7:].split("：")[0] for ln in out.splitlines() if ln.startswith("[FAIL] ")]


def tree_md5(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def mutate(tag: str, old: str, new: str) -> tuple[Path, bool]:
    """复制审计脚本并做一处替换；返回 (脚本路径, 是否真的改到了源码)。"""
    d = Path(tempfile.mkdtemp(prefix=f"idtypes-mut-{tag}-"))
    dst = d / "audit-id-types.py"
    src = AUDIT.read_text(encoding="utf-8")
    hit = old in src
    dst.write_text(src.replace(old, new), encoding="utf-8")
    return dst, hit


def main() -> int:
    ok_n = 0
    fail_n = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal ok_n, fail_n
        if ok:
            ok_n += 1
        else:
            fail_n += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    tmp_dirs: list[Path] = []

    def case(tag: str, files: dict[str, str], want_rc: int, want_assert: str | None,
             forbid: list[str] | None = None) -> str:
        root = write_case(files, tag)
        tmp_dirs.append(root)
        rc, out = run(root)
        got = fails(out)
        ok = rc == want_rc
        if want_assert:
            ok = ok and any(a.startswith(want_assert) for a in got)
        if forbid:
            ok = ok and not any(any(x.startswith(pref) for x in got) for pref in forbid)
        check(f"case_{tag}：rc={rc}(期望 {want_rc})"
              + (f" 命中「{want_assert}」={'是' if any(a.startswith(want_assert or '') for a in got) else '否'}"
                 if want_assert else "")
              + (f"；FAIL 列表={got}" if got else ""), ok)
        return out

    print("== A. 正向对照 ==")
    ok_out = case("ok", base_files(), 0, None)
    check("A0 正向对照：ok 夹具 rc=0 且断言 FAIL 0（解析器真的工作了）",
          "FAIL 0" in ok_out and "PASS " in ok_out,
          ok_out.strip().splitlines()[-1] if ok_out else "")

    print("== B. 每个判定分支一条反例 ==")
    f = base_files()
    f["docs/backend/json-schema/models/usage-summary.schema.json"] = schema(
        {"provider_id": {"type": ["integer", "null"]}})
    case("s_number", f, 1, "A1", forbid=["A3", "A4", "A6"])

    f = base_files()
    f["aap-server/src/main/java/com/hioas/aap/sync/SyncViews.java"] = views(id_type="Long")
    case("i_long", f, 1, "A3", forbid=["A1", "A4", "A6"])

    f = base_files()
    f["aap-client/src/m.ts"] = "export interface X {\n  id: number\n}\n"
    case("c_number", f, 1, "A4", forbid=["A1", "A3", "A6"])

    f = base_files()
    f["docs/backend/openapi.yaml"] = openapi({"Ghost": "./json-schema/models/ghost.schema.json"})
    case("o_dangling", f, 1, "A2a")

    f = base_files()
    f["docs/backend/openapi.yaml"] = openapi(
        {"UsageSummary": "./json-schema/models/usage-summary.schema.json"}, inline_id=True)
    case("o_inline_id", f, 1, "A2b")

    f = base_files()
    del f["aap-server/src/main/java/com/hioas/aap/sync/SyncViews.java"]
    case("ex_side_missing", f, 1, "A5b")

    f = base_files()
    f["aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java"] = \
        "package com.hioas.aap.sync;\n\npublic class SyncAdminService {\n}\n"
    case("ex_no_evidence", f, 1, "A5c")

    f = base_files()
    f["docs/backend/json-schema/models/usage-hourly.schema.json"] = schema(
        {"channel_id": {"type": ["string", "null"]}})
    case("name_conflict", f, 1, "A6", forbid=["A1", "A3", "A4"])

    f = base_files()
    f["docs/backend/json-schema/models/usage-summary.schema.json"] = schema(
        {"request_count": {"type": "integer"}})
    f["docs/backend/json-schema/models/channel-binding.schema.json"] = schema(
        {"channel_name": {"type": "string"}})
    case("empty_s", f, 1, "A0a")

    f = base_files()
    f["docs/backend/01-ER数据模型.md"] = "# ER（夹具，无 new-api 标注）\n"
    case("er_missing", f, 1, "A7")

    print("== C. 注入缺陷判别力（坑 57 / 66：注入必须真的改到源码） ==")
    # inj#1：往真实仓库副本注入一处真实漂移（唯一出现的 biz_id 改成 integer）→ 必须恰好 A1 转红
    # （选「全仓库只出现一次」的字段名：若选 provider_id 这类出现 17 次的字段，A6 会因同名不一致一并转红）
    d = Path(tempfile.mkdtemp(prefix="idtypes-inj1-"))
    tmp_dirs.append(d)
    shutil.copytree(REPO / "docs", d / "docs")
    shutil.copytree(REPO / "aap-server/src", d / "aap-server/src")
    shutil.copytree(REPO / "aap-client/src", d / "aap-client/src")
    target = d / "docs/backend/json-schema/models/notification.schema.json"
    rc0, out0 = run(d)
    baseline = fails(out0)  # 真实仓库副本的既有 FAIL（含 A6 的 channel_id 待拍板项）
    txt = target.read_text(encoding="utf-8")
    anchor = ('"biz_id": {\n      "type": [\n        "string",\n        "null"\n      ]')
    injected = txt.replace(anchor, anchor.replace('"string"', '"integer"'))
    hit1 = injected != txt  # 锚点真的命中了才叫注入成功（坑 66）
    target.write_text(injected, encoding="utf-8")
    rc, out = run(d)
    after = fails(out)
    new = [x for x in after if x not in baseline]
    check("inj#1 真实仓库副本注入 biz_id=integer → FAIL 集合恰好新增 A1（不越界到 A3/A4）",
          hit1 and rc == 1 and len(new) == 1 and new[0].startswith("A1")
          and set(after) >= set(baseline),
          f"锚点命中={hit1} rc={rc} 基线 FAIL={baseline} 注入后={after} 新增={new}")

    # inj#2：拆掉 A4 判据 → c_number 夹具不再报 A4
    mut2, hit2 = mutate("a4", 'if "string" not in t', "if False")
    tmp_dirs.append(mut2.parent)
    f = base_files()
    f["aap-client/src/m.ts"] = "export interface X {\n  id: number\n}\n"
    root2 = write_case(f, "inj2")
    tmp_dirs.append(root2)
    rc_b, out_b = run(root2)
    rc_a, out_a = run(root2, mut2)
    check("inj#2 拆掉 A4 判据后 c_number 夹具不再报 A4（该守卫确有判别力）",
          hit2 and any(x.startswith("A4") for x in fails(out_b))
          and not any(x.startswith("A4") for x in fails(out_a)),
          f"锚点命中={hit2} 拆前 FAIL={fails(out_b)} 拆后 FAIL={fails(out_a)}")

    # inj#3：拆掉 A6 判据 → name_conflict 夹具不再报 A6
    mut3, hit3 = mutate("a6", "if len(v) > 1", "if len(v) > 99")
    tmp_dirs.append(mut3.parent)
    f = base_files()
    f["docs/backend/json-schema/models/usage-hourly.schema.json"] = schema(
        {"channel_id": {"type": ["string", "null"]}})
    root3 = write_case(f, "inj3")
    tmp_dirs.append(root3)
    rc_b, out_b = run(root3)
    rc_a, out_a = run(root3, mut3)
    check("inj#3 拆掉 A6 判据后 name_conflict 夹具不再报 A6（该守卫确有判别力）",
          hit3 and any(x.startswith("A6") for x in fails(out_b))
          and not any(x.startswith("A6") for x in fails(out_a)),
          f"锚点命中={hit3} 拆前 FAIL={fails(out_b)} 拆后 FAIL={fails(out_a)}")

    print("== D. 零写副作用守卫 ==")
    repo_keys = ["docs/backend/endpoints.json", "docs/backend/openapi.yaml",
                 "docs/backend/01-ER数据模型.md"]
    before = {k: hashlib.md5((REPO / k).read_bytes()).hexdigest() for k in repo_keys}
    rc, _ = run(REPO)
    after = {k: hashlib.md5((REPO / k).read_bytes()).hexdigest() for k in repo_keys}
    check("D1 真实仓库跑一遍：只读（3 个关键文件 md5 全等）", before == after,
          f"rc={rc}（真实仓库 rc=1 是预期的：存在 A6 待拍板漂移）")

    for d in tmp_dirs:
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n== 自测结果：PASS {ok_n} / FAIL {fail_n} ==")
    return 1 if fail_n else 0


if __name__ == "__main__":
    sys.exit(main())
