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
DONE = {"已验证"}


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

    pending = [r for r in rows if r["状态"] not in DONE]
    done = len(rows) - len(pending)
    print(f"台账 {len(rows)} 行 · 已验证 {done} · 未完成 {len(pending)}")
    show = pending if a.all else pending[: a.n]
    for r in show:
        print(f"{r['序号']:>6} | {r['状态']:<4} | 设计{r['设计抓取']} 交互{r['交互抓取']} | "
              f"{r['目标路由']:<34} | {r['页面ID']:<12} | {r['页面名']}")
    if not a.all and len(pending) > len(show):
        print(f"... 其余 {len(pending) - len(show)} 条见台账 CSV")


if __name__ == "__main__":
    main()
