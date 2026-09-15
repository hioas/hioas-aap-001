#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按序号列出台账中未完成的页面（aap-tdd 每轮取件用）。

用法：
    python .agents/state/list-pending.py          # 前 5 条未完成
    python .agents/state/list-pending.py -n 20    # 前 20 条
    python .agents/state/list-pending.py --all    # 全部未完成
"""
import argparse
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER = os.path.join(ROOT, ".agents", "state", "aap-feature-status.csv")
# 已验证 = 做完且无缺口；部分 = 已实现并留证、仅剩「等人类拍板」的缺口 → 都不得重复取件。
# 只有 未做/进行中 才计入取件（阻塞 单独列出，等人解除后再取）。
DONE = {"已验证", "部分"}
BLOCKED = {"阻塞"}


def seq_key(seq):
    parts = []
    for chunk in str(seq).replace("-v", ".").split("."):
        parts.append(int(chunk) if chunk.isdigit() else 0)
    return parts + [0] * (4 - len(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    with open(LEDGER, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)]
    rows.sort(key=lambda r: seq_key(r["序号"]))

    pending = [r for r in rows if r["状态"] not in DONE and r["状态"] not in BLOCKED]
    blocked = [r for r in rows if r["状态"] in BLOCKED]
    done = len([r for r in rows if r["状态"] in DONE])
    print(f"台账 {len(rows)} 行 · 已验证/部分 {done} · 阻塞 {len(blocked)} · 待取件 {len(pending)}")
    if blocked:
        print("  阻塞（等人解除，不取件）：" + "、".join(f"{r['序号']} {r['页面ID']}" for r in blocked))
    show = pending if a.all else pending[: a.n]
    for r in show:
        print(f"{r['序号']:>6} | {r['状态']:<4} | 设计{r['设计抓取']} 交互{r['交互抓取']} | "
              f"{r['目标路由']:<34} | {r['页面ID']:<12} | {r['页面名']}")
    if not a.all and len(pending) > len(show):
        print(f"... 其余 {len(pending) - len(show)} 条见台账 CSV")


if __name__ == "__main__":
    main()
