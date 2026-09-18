#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`audit-endpoint-tests.py` 的**负向自测**：证明判定分支都真会失败（不是橡皮图章）。

为什么必须有它（踩坑 29）：R22 那一轮只看 `ep["id"] in text` 的裸子串，
把项目既有的**组合引用**（`AUTH-05/06`、`DET-01…06`）全部漏判，
得出「19 条端点 ID 不可追溯」的假发现。本自测用一份**合成夹具**把边界钉死：

  SYN-01/02/03  —— 由区间引用 `SYN-01…03` 命中（区间必须展开）
  SYN-06        —— 由枚举引用 `SYN-05/06` 命中（枚举必须展开）
  SYN-04        —— 区间 01…03 **不得**外溢到 04，必须判「不可追溯」
  SYN-09        —— 任何地方都没提过，必须判「不可追溯」
  PATH-01       —— 路径在测试源里不存在 → 必须判 none（rc=1）
  PATH-02       —— 路径存在但方法不吻合 → 必须判 prefix（弱证据）

退出码：0 = 全部分支符合预期；1 = 有分支失效（审计已失去判别力）。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "tools" / "audit-endpoint-tests.py"

FAKE_SOURCE = """package com.hioas.aap.synthetic;

/**
 * 合成夹具（仅用于自测审计脚本，不参与构建）。
 * T00 · 合成验收（接口 SYN-01…03；SYN-05/06）。
 */
class SyntheticFixture {
    void probe() {
        get("/syn/probe", token);
        post("/syn/probe/only-post", null, token);
    }
}
"""

FIXTURE_ENDPOINTS = [
    {"id": "SYN-01", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "SYN-02", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "SYN-03", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "SYN-04", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "SYN-05", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "SYN-06", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "SYN-09", "method": "GET", "path": "/api/v1/syn/probe", "task": "T00"},
    {"id": "PATH-01", "method": "GET", "path": "/api/v1/nonexistent/never-called", "task": "T00"},
    {"id": "PATH-02", "method": "GET", "path": "/api/v1/syn/probe/only-post", "task": "T00"},
]


def metric(text: str, label: str) -> int:
    """从审计文本里取 `标签 …… ：N` 的 N（`N/M` 取 N）。"""
    for line in text.splitlines():
        if line.startswith(label):
            return int(line.split("：")[-1].split("/")[0].strip())
    raise AssertionError(f"未找到指标行：{label}")


def untraceable_ids(text: str) -> set[str]:
    """解析「测试源里未出现端点 ID 的端点」小节里的 ID 集合。"""
    ids: set[str] = set()
    collecting = False
    for line in text.splitlines():
        if line.startswith("=="):
            collecting = "未出现端点 ID" in line
            continue
        if collecting and line.strip():
            ids |= {t.strip() for t in line.strip().split(",") if t.strip()}
    return ids


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="aap-audit-selftest-"))
    tests_dir = tmp / "tests" / "synthetic"
    tests_dir.mkdir(parents=True)
    (tests_dir / "SyntheticFixture.java").write_text(FAKE_SOURCE, encoding="utf-8")
    manifest = tmp / "fake-endpoints.json"
    manifest.write_text(json.dumps({"endpoints": FIXTURE_ENDPOINTS}, ensure_ascii=False),
                        encoding="utf-8")

    out = subprocess.run(
        [sys.executable, str(AUDIT), "--manifest", str(manifest),
         "--tests-dir", str(tmp / "tests"), "--no-evidence"],
        capture_output=True, text=True, encoding="utf-8",
    )
    text = out.stdout
    print("---- 自测输出（审计 stdout）----")
    print(text)

    exact = metric(text, "exact")
    prefix = metric(text, "prefix")
    none = metric(text, "none")
    traceable = metric(text, "端点 ID 在测试源里可追溯")
    same_file = metric(text, "ID 引用与真实 HTTP 调用点同文件")
    untraceable = untraceable_ids(text)

    checks: list[tuple[str, bool, str, str]] = [
        ("路径骨架+方法吻合 → exact", exact == 7,
         f"exact={exact}（期望 7 = SYN-01…06 + SYN-09）", ""),
        ("路径不存在 → none 且 rc=1", none == 1 and out.returncode == 1,
         f"none={none} rc={out.returncode}", ""),
        ("方法不吻合 → prefix（弱证据，不冒充 exact）", prefix == 1,
         f"prefix={prefix}（期望 1 = 只有 PATH-02）", ""),
        ("短路径不得在长路径里当子串命中（尾部边界守卫）", prefix == 1,
         f"prefix={prefix}",
         "prefix>1 → `/syn/probe` 在 `/syn/probe/only-post` 里白捡了证据"),
        ("区间引用 `SYN-01…03` 展开 → 3 条可追溯", traceable >= 4,
         f"id_traceable={traceable}（期望 ≥4 = SYN-01/02/03 + SYN-06）", ""),
        ("枚举引用 `SYN-05/06` 展开 → SYN-06 可追溯", "SYN-06" not in untraceable,
         "SYN-06 已判为可追溯", "SYN-06 被误判为不可追溯（枚举未展开）"),
        ("区间不得外溢：SYN-04 必须判不可追溯", "SYN-04" in untraceable,
         "SYN-04 已判为不可追溯（区间未过度展开）", "SYN-04 被区间 01…03 误纳入（过度展开 = 假绿）"),
        ("未被提及的 SYN-09 必须判不可追溯", "SYN-09" in untraceable,
         "SYN-09 已判为不可追溯", "SYN-09 被判为可追溯（判定失效）"),
        ("同文件档：ID 引用与调用点同文件", same_file >= 4,
         f"same_file={same_file}（期望 ≥4）", ""),
    ]

    print("---- 断言 ----")
    ok = True
    for name, passed, detail, hint in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}  ({detail})")
        if not passed and hint:
            print(f"         → {hint}")
        ok &= passed
    print(f"\n结果：{'全部通过（审计有判别力）' if ok else '存在失效分支（审计已失去判别力）'}")
    print(f"夹具目录：{tmp}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
