#!/usr/bin/env python3
"""密钥泄漏只读审计（硬规则 4；R28 起为常备工具）。

做法：把 `E:/env/*.env` 里的**真实值**当模式，去仓库的四处比对：
  1) 暂存差异（`git diff --cached`）
  2) 提交历史 HEAD 树（`git grep -F -- <值> HEAD`）
  3) 已跟踪工作树（`git grep -F -- <值>`）
  4) 未跟踪文件（`git ls-files --others --exclude-standard`）

分层（skill 坑 45）：**只有「变量名含密钥语义」的值才是 Tier A**（必须 0 命中）；
其余（host/port/库名这类非密钥低熵值）只作信息项，输出「变量名 + 长度 + sha256 前 8 位」。

**绝不回显任何值**（连长度以外的东西都不打印）。命中只报文件名。

正向对照（skill 坑 46）：`--selftest` 用合成文本证明扫描函数**有判别力**，
否则「Tier A 0 命中」无法区分「真干净」与「扫描器根本没工作」。

用法：
  python tools/audit-secret-leak.py [--env-dir E:/env] [--repo <path>] [--selftest]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

TIER_A_RE = re.compile(r"(?i)(PASSWORD|PASSWD|PWD|SECRET|TOKEN|CREDENTIAL|CERT|KEY)")
MIN_LEN = 8


def sha8(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:8]


def load_env_files(env_dir: Path) -> list[tuple[str, str, str]]:
    """→ [(文件名, 变量名, 值)]；只解析 `VAR=VALUE`，忽略注释与空行。"""
    out = []
    if not env_dir.exists():
        return out
    for f in sorted(env_dir.glob("*.env")):
        for raw in f.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            name, _, val = ln.partition("=")
            name, val = name.strip(), val.strip().strip('"').strip("'")
            if name and val:
                out.append((f.name, name, val))
    return out


def classify(name: str) -> str:
    return "A" if TIER_A_RE.search(name) else "B"


def scan_text(values: list[str], text: str) -> list[str]:
    return [v for v in values if v and v in text]


def git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout or ""


def selftest() -> int:
    synthetic = "sk-synthetic-canary-not-a-real-secret"
    ok1 = scan_text([synthetic], f"a line mentioning {synthetic} inside") == [synthetic]
    ok2 = scan_text([synthetic], "a clean line with nothing in it") == []
    ok3 = scan_text([synthetic], "") == []
    print(f"[{'PASS' if ok1 else 'FAIL'}] 正向对照：扫描器能在文本里找到模式值")
    print(f"[{'PASS' if ok2 else 'FAIL'}] 负向对照：无该值的文本判 0 命中")
    print(f"[{'PASS' if ok3 else 'FAIL'}] 边界：空文本判 0 命中")
    n = sum([ok1, ok2, ok3])
    print(f"\n自测 {3} 条：PASS {n}，FAIL {3 - n}")
    return 0 if n == 3 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-dir", default="E:/env")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    env_dir = Path(args.env_dir)
    repo = Path(args.repo)
    entries = load_env_files(env_dir)
    tier_a = [(f, n, v) for f, n, v in entries if classify(n) == "A" and len(v) >= MIN_LEN]
    tier_b = [(f, n, v) for f, n, v in entries if classify(n) == "B"]

    print(f"仓库：{repo}")
    print(f"密钥目录：{env_dir}（{len(list(env_dir.glob('*.env'))) if env_dir.exists() else 0} 个 .env 文件）")
    print(f"Tier A（变量名含密钥语义、值长 >= {MIN_LEN}）：{len(tier_a)} 个变量 —— 必须 0 命中")
    print(f"Tier B（其余，非密钥低熵）：{len(tier_b)} 个变量 —— 仅信息项")
    if not entries:
        print("[FAIL] 未读到任何变量：密钥目录为空或路径不对（不把「读不到」当「干净」）")
        return 1
    print(f"[PASS] 正向对照：读到 {len(entries)} 个变量（扫描器确实有输入）")

    a_values = [v for _, _, v in tier_a]
    scans: list[tuple[str, list[str]]] = []
    staged = git(repo, "diff", "--cached", "-U0")
    scans.append(("暂存差异", scan_text(a_values, staged)))
    for label, args_ in (("提交历史 HEAD 树", ("grep", "-I", "-l", "-F", "--")),
                         ("已跟踪工作树", ("grep", "-I", "-l", "-F", "--"))):
        hits: list[str] = []
        for v in a_values:
            out = git(repo, *args_, v) if label == "已跟踪工作树" else git(repo, *args_, v, "HEAD")
            hits += [f"{Path(x).name}(值 {sha8(v)})" for x in out.splitlines() if x.strip()]
        scans.append((label, hits))
    # 未跟踪文件
    untracked = [x for x in git(repo, "ls-files", "--others", "--exclude-standard").splitlines() if x.strip()]
    uhits: list[str] = []
    for rel in untracked:
        p = repo / rel
        try:
            if p.is_file() and p.stat().st_size < 5_000_000:
                uhits += [f"{rel}(值 {sha8(v)})" for v in scan_text(a_values, p.read_text(encoding="utf-8", errors="replace"))]
        except OSError:
            continue
    scans.append((f"未跟踪文件（{len(untracked)} 个）", uhits))

    total = 0
    for label, hits in scans:
        uniq = sorted(set(hits))
        total += len(uniq)
        print(f"[{'FAIL' if uniq else 'PASS'}] {label}：Tier A 命中 {len(uniq)}")
        for h in uniq[:10]:
            print(f"      · {h}")

    print("--- Tier B（信息项，只报名字/长度/指纹，不回显值）---")
    for f, n, v in tier_b:
        print(f"      · {n}（{f}）len={len(v)} sha256:8={sha8(v)}")

    print("--- .gitignore 覆盖与 .env 跟踪面 ---")
    gi = (repo / ".gitignore")
    gi_text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    for pat in (".env", ".env.*", "target/", "node_modules/"):
        print(f"[{'PASS' if pat in gi_text else 'FAIL'}] .gitignore 含 `{pat}`")
    tracked_env = [x for x in git(repo, "ls-files").splitlines()
                   if Path(x).name == ".env" or Path(x).name.startswith(".env")]
    bad = [x for x in tracked_env if Path(x).name != ".env.example"]
    print(f"[{'PASS' if not bad else 'FAIL'}] 被跟踪的 .env 类文件只有 .env.example：{tracked_env}")

    print(f"\n结论：Tier A 泄漏命中 {total} 处")
    return 0 if total == 0 and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
