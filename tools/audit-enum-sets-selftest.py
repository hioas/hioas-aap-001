#!/usr/bin/env python3
"""audit-enum-sets.py 的负向自测（每个判定分支一条反例 + 正向对照 + 零写副作用）。

为什么必须有：坑 46/32 —— 没有反例的审计「一直在报错」会被当成合格；
没有正向对照的「0 发现」无法区分「真干净」与「匹配逻辑全错」。
本脚本在**临时目录**造合成夹具（不碰仓库任何文件），逐用例断言
「恰好该分支变红、其余仍绿」，并对真实仓库跑一次正向对照。

用例清单（每个 A 分支至少一条反例）：
  clean           全部一致 → rc=0 且 A0 正向对照全 PASS（含 A0.1 = 12 个族）
  md_lead_pipe    md 表格行带行首 `|` → 仍解析到 12 个族（真实返工回归守卫）
  md_escaped_pipe 单元格里的转义竖线不得吞掉该行（坑 48）
  a1_drift        openapi 与 md 取值不一致 → A1 点名 FAIL
  a2_orphan       openapi 多出一个未登记族 → A2 FAIL
  a5_typo         schema 出现 md 未声明的取值 → A5 点名 FAIL
  a6_drift        同族 schema 与 openapi 取值不一致 → A6 FAIL
  a7_sql          30 个 SQL 未分类字面量 → A7 阈值 FAIL
  a8_impl         实现集合不在契约取值域内 → A8 FAIL
  a8_subset       实现集合是契约子集 → 不判 FAIL（合法收窄）
  a9_mismatch     openapi ResultCode ≠ md §4 码表 → A9 FAIL
  empty           夹具缺 §5 字典 → A0.1 FAIL（空夹具必须变红）
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "tools/audit-enum-sets.py"
FAMILIES = [f"FAM{i:02d}" for i in range(1, 13)]


def fam_vals(name: str) -> list[str]:
    # FAM12 给 3 个取值：供 a8_subset 用例造「真子集」（2 个取值才够 declared_sets 采集门槛）
    if name == "FAM12":
        return ["FAM12_A", "FAM12_B", "FAM12_C"]
    return [f"{name}_A", f"{name}_B"]


def build_fixture(root: Path) -> Path:
    (root / "docs/backend/json-schema/models").mkdir(parents=True, exist_ok=True)
    (root / "docs/backend/json-schema/requests").mkdir(parents=True, exist_ok=True)
    (root / "client").mkdir(parents=True, exist_ok=True)
    (root / "java").mkdir(parents=True, exist_ok=True)

    md = ["# 接口清单", "", "## 4. 错误码表", "| 错误码 | HTTP | 说明 |", "|---|---|---|"]
    for i in range(1, 13):
        md.append(f"| `E-10{i:02d}` | 400 | 说明{i} |")
    md += ["", "## 5. 全局枚举字典", "| 枚举 | 取值 | 出处 |", "|---|---|---|"]
    for name in FAMILIES:
        vals = " ".join(f"`{v}`" for v in fam_vals(name))
        md.append(f"| {name} | {vals} | spec |")
    # ResultCode 也登记进 §5：openapi 有该族，不登记就会触发 A2 孤儿（clean 基线必须零 FAIL）
    md.append("| ResultCode | " + " ".join(f"`E-10{i:02d}`" for i in range(1, 13)) + " | §4 |")
    (root / "docs/backend/02-API接口模型清单.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    oa = ["openapi: 3.0.3", "components:", "  schemas:"]
    for name in FAMILIES:
        oa += [f"    {name}:", "      type: string", "      enum:"]
        oa += [f"        - {v}" for v in fam_vals(name)]
    oa += ["    ResultCode:", "      type: string", "      enum:"]
    oa += [f"        - E-10{i:02d}" for i in range(1, 13)]
    oa += ["    Model01:", "      $ref: ./json-schema/models/model01.schema.json"]
    (root / "docs/backend/openapi.yaml").write_text("\n".join(oa) + "\n", encoding="utf-8")

    (root / "docs/backend/json-schema/models/model01.schema.json").write_text(
        '{"type":"object","properties":{"status":{"type":["string","null"],'
        '"enum":["FAM01_A","FAM01_B",null]}}}\n', encoding="utf-8")
    (root / "docs/backend/json-schema/requests/req01.schema.json").write_text(
        '{"type":"object","properties":{"mode":{"type":"string",'
        '"enum":["FAM02_A","FAM02_B"]}}}\n', encoding="utf-8")
    (root / "client/types.ts").write_text(
        "export type FAM01 = 'FAM01_A' | 'FAM01_B'\n", encoding="utf-8")
    (root / "java/Svc.java").write_text(
        "public class Svc {\n"
        "    private static final String SQL = \"\"\"\n"
        "            update t set status = 'FAM01_A' where status = 'FAM01_B'\n"
        "            \"\"\";\n"
        "    private static final Set<String> EDITABLE = Set.of(\"FAM03_A\", \"FAM03_B\");\n"
        "    record R(@Pattern(regexp = \"^(FAM04_A|FAM04_B)$\") String mode) {}\n"
        "}\n", encoding="utf-8")
    (root / "docs/backend/01-ER数据模型.md").write_text(
        "**aap_x**：`status`(FAM01_A/FAM01_B)、`mode`(FAM04_A/FAM04_B)。\n"
        "| trigger_type | varchar(16) | FAM03_A/FAM03_B |\n"
        "| weekday_scope | varchar(16) | FAM05_A/FAM05_B |\n"
        "| price_strategy | varchar(16) | FAM06_A/FAM06_B |\n"
        "| tier_field | varchar(16) | FAM07_A/FAM07_B |\n"
        "| sign_method | varchar(16) | FAM08_A/FAM08_B |\n", encoding="utf-8")
    return root


def run_audit(root: Path) -> tuple[int, str]:
    cmd = [sys.executable, str(AUDIT),
           "--md", str(root / "docs/backend/02-API接口模型清单.md"),
           "--openapi", str(root / "docs/backend/openapi.yaml"),
           "--schemas-dir", str(root / "docs/backend/json-schema"),
           "--er-doc", str(root / "docs/backend/01-ER数据模型.md"),
           "--client-dir", str(root / "client"),
           "--main-dir", str(root / "java")]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def mutate(path: Path, old: str, new: str) -> bool:
    """按锚点替换；返回是否**真的**改到（坑 66：锚点失效会静默空转）。"""
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def check(name: str, cond: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    return cond


def main() -> int:
    results: list[bool] = []
    tmp = Path(tempfile.mkdtemp(prefix="enum-audit-selftest-"))
    try:
        base = build_fixture(tmp / "base")

        # ---- clean：全一致 → rc=0，且正向对照真的解析到了（不能是「解析到 0 个所以全 PASS」）
        rc, out = run_audit(base)
        results.append(check("clean rc=0", rc == 0, f"rc={rc}"))
        results.append(check("clean A0.1 解析到 13 个族", "A0.1 M 解析到 ≥10 个枚举族 | 实际 13" in out))
        results.append(check("clean A0.7/A0.8 解析到实现集合与 ER 域",
                             "A0.8 E(ER 列取值域) 解析到 ≥5 个 | 实际 7" in out
                             and "A0.7 I② 解析到 ≥2 个显式取值集合 | 实际 2" in out))
        results.append(check("clean A1 逐名一致", "A1 FAM01 md↔openapi 一致" in out))
        results.append(check("clean A6/A9 一致", "A6 FAM01 schema↔openapi 一致" in out
                             and "A9 openapi ResultCode 集合 == md §4 码表集合" in out))
        results.append(check("clean 无 FAIL 行", "[FAIL]" not in out))

        # ---- md_lead_pipe：行首 `|` 造成的空首列不得吞掉整行（真实返工回归守卫）
        # 由 clean 的 A0.1=13 覆盖：若解析器回退成 cells[0] 取空，这里会变红
        results.append(check("md_lead_pipe 回归守卫（行首竖线）", "实际 13" in out))

        # ---- md_escaped_pipe：转义竖线所在行仍被解析
        esc = build_fixture(tmp / "esc")
        ok = mutate(esc / "docs/backend/02-API接口模型清单.md",
                    "| FAM12 | `FAM12_A` `FAM12_B` `FAM12_C` | spec |",
                    "| FAM12 | `FAM12_A` `FAM12_B` `FAM12_C` | a\\|b |")
        results.append(check("mutate md_escaped_pipe 真的改到", ok))
        rc, out = run_audit(esc)
        results.append(check("md_escaped_pipe 仍解析 13 个族且 rc=0",
                             rc == 0 and "实际 13" in out, f"rc={rc}"))

        # ---- a1_drift
        d1 = build_fixture(tmp / "a1")
        ok = mutate(d1 / "docs/backend/openapi.yaml", "        - FAM01_B", "        - FAM01_Z")
        results.append(check("mutate a1_drift 真的改到", ok))
        rc, out = run_audit(d1)
        results.append(check("a1_drift → A1 点名 FAIL 且 rc=1",
                             rc == 1 and "[FAIL] A1 FAM01 md↔openapi 一致" in out))

        # ---- a2_orphan
        d2 = build_fixture(tmp / "a2")
        ok = mutate(d2 / "docs/backend/openapi.yaml", "    ResultCode:",
                    "    Gamma:\n      type: string\n      enum:\n        - G1\n    ResultCode:")
        results.append(check("mutate a2_orphan 真的改到", ok))
        rc, out = run_audit(d2)
        results.append(check("a2_orphan → A2 FAIL 且点名 Gamma",
                             rc == 1 and "A2 openapi 内联枚举名全部在 md §5 登记" in out
                             and "Gamma(1)" in out))

        # ---- a5_typo：schema 出现 md 未声明取值
        d5 = build_fixture(tmp / "a5")
        ok = mutate(d5 / "docs/backend/json-schema/models/model01.schema.json",
                    '"FAM01_A","FAM01_B",null', '"FAM01_A","FAM01_TYPO",null')
        results.append(check("mutate a5_typo 真的改到", ok))
        rc, out = run_audit(d5)
        results.append(check("a5_typo → A5 点名 FAIL 且 rc=1",
                             rc == 1 and "model01.schema.json:status 无匹配" in out))

        # ---- a6_drift：同族 schema 与 openapi 不一致（schema 收窄到子集不报，这里造真漂移）
        d6 = build_fixture(tmp / "a6")
        ok = mutate(d6 / "docs/backend/json-schema/models/model01.schema.json",
                    '"FAM01_A","FAM01_B",null', '"FAM01_A",null')
        results.append(check("mutate a6_drift 真的改到", ok))
        rc, out = run_audit(d6)
        results.append(check("a6_drift → A6 FAIL（openapi-only 出现 FAM01_B）",
                             rc == 1 and "[FAIL] A6 FAM01 schema↔openapi 一致" in out
                             and "openapi-only=['FAM01_B']" in out))

        # ---- a7_sql：未分类 SQL 字面量超阈值
        d7 = build_fixture(tmp / "a7")
        extra = "".join(f"            and c{i} = 'ZZ{i:02d}'\n" for i in range(30))
        ok = mutate(d7 / "java/Svc.java", "            \"\"\";\n", extra + "            \"\"\";\n")
        results.append(check("mutate a7_sql 真的改到", ok))
        rc, out = run_audit(d7)
        results.append(check("a7_sql → A7 阈值 FAIL",
                             rc == 1 and "[FAIL] A7 未分类 SQL 字面量 ≤ 阈值" in out))

        # ---- a8_impl：实现集合不在契约取值域内
        d8 = build_fixture(tmp / "a8")
        ok = mutate(d8 / "java/Svc.java", 'Set.of("FAM03_A", "FAM03_B")',
                    'Set.of("FAM03_A", "FAM03_ZZ")')
        results.append(check("mutate a8_impl 真的改到", ok))
        rc, out = run_audit(d8)
        results.append(check("a8_impl → A8 FAIL 且点名 Svc.java",
                             rc == 1 and "[FAIL] A8 实现声明的取值域均在契约中声明" in out
                             and "FAM03_ZZ" in out))

        # ---- a8_subset：实现集合是契约子集 → 不得判 FAIL（合法收窄）
        d8s = build_fixture(tmp / "a8s")
        ok = mutate(d8s / "java/Svc.java", 'Set.of("FAM03_A", "FAM03_B")',
                    'Set.of("FAM12_A", "FAM12_B")')
        results.append(check("mutate a8_subset 真的改到", ok))
        rc, out = run_audit(d8s)
        results.append(check("a8_subset → 该分支不判 FAIL（rc=0）",
                             rc == 0 and "[FAIL] A8" not in out, f"rc={rc}"))

        # ---- a9_mismatch
        d9 = build_fixture(tmp / "a9")
        ok = mutate(d9 / "docs/backend/openapi.yaml", "        - E-1012", "        - E-9999")
        results.append(check("mutate a9_mismatch 真的改到", ok))
        rc, out = run_audit(d9)
        results.append(check("a9_mismatch → A9 FAIL 且给出双向差集",
                             rc == 1 and "A9 openapi ResultCode 集合 == md §4 码表集合" in out
                             and "E-9999" in out and "E-1012" in out))

        # ---- empty：夹具缺 §5 → A0.1 必须变红（空夹具必须变红）
        de = build_fixture(tmp / "empty")
        ok = mutate(de / "docs/backend/02-API接口模型清单.md", "## 5. 全局枚举字典",
                    "## 5x. 字典缺失")
        results.append(check("mutate empty 真的改到", ok))
        rc, out = run_audit(de)
        results.append(check("empty → A0.1 FAIL 且 rc=1（空夹具不得全绿）",
                             rc == 1 and "[FAIL] A0.1 M 解析到 ≥10 个枚举族" in out))

        # ---- 真实仓库正向对照（只读；断言「不是解析到 0 个」）
        rc, out = run_audit(ROOT)
        results.append(check("真实仓库：解析到 16 个族 / 34 个 schema enum / 21 个 openapi enum",
                             "M(§5 枚举族)=16" in out and "S(schema enum 属性)=34" in out
                             and "O(openapi 内联 enum)=21" in out, f"rc={rc}"))
        results.append(check("真实仓库：A6/A9 一致（其余 FAIL 为已裁决漂移项）",
                             "A6 QuoteStatus schema↔openapi 一致" in out
                             and "A9 openapi ResultCode 集合 == md §4 码表集合" in out))

        print(f"\n== 自测汇总：{sum(results)}/{len(results)} PASS ==")
        return 0 if all(results) else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
