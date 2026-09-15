#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 .calicat/inventory.json + 页面序号计划 生成/刷新 aap-tdd 台账 CSV。

用法：
    python .agents/state/gen-ledger.py            # 生成（保留已有行的状态/证据/备注列）
    python .agents/state/gen-ledger.py --stats    # 只打印统计
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INVENTORY = os.path.join(ROOT, ".calicat", "inventory.json")
LEDGER = os.path.join(ROOT, ".agents", "state", "aap-feature-status.csv")

# 小程序页面执行顺序（序号 → inventory page id）。序号即页面名前缀，按数字升序逐个执行。
PAGE_PLAN = [
    ("1",    "page-1-2",       "账号接入",   "/pages/login/index"),
    ("2",    "page-2-b",       "工作台与我的", "/pages/workbench/index"),
    ("3",    "page-3",         "工作台与我的", "/pages/credentials/index"),
    ("4",    "page-4-2",       "检测验真",   "/pages/credential-submit/index"),
    ("4-v1", "page-24",        "检测验真",   "/pages/credential-submit/form"),
    ("5",    "page-5-2",       "检测验真",   "/pages/detecting/index"),
    ("6",    "page-6",         "检测验真",   "/pages/report/index"),
    ("7",    "page-7-2",       "检测验真",   "/pages/report-failed/index"),
    ("8",    "page-8-2",       "报价管理",   "/pages/quotes/index"),
    ("9",    "page-9",         "报价管理",   "/pages/quote-models/index"),
    ("10",   "page-10-2",      "档案与凭证", "/pages/profile-edit/index"),
    ("10.1", "page-10-1-2",    "档案与凭证", "/pages/profile/index"),
    ("11",   "page-11",        "报价管理",   "/pages/model-pricing/index"),
    ("12",   "page-12-2",      "报价管理",   "/pages/quote-preview/index"),
    ("12-v1", "page-26",       "报价管理",   "/pages/quote-form/index"),
    ("12-v2", "page-apikey",   "报价管理",   "/pages/quote-form/apikey"),
    ("12-v3", "page-29",       "报价管理",   "/pages/quote-form/success"),
    ("15",   "page-15-2",      "合同与通知", "/pages/contract/index"),
    ("20",   "page-20-2",      "合同与通知", "/pages/messages/index"),
    ("21",   "page-21-2",      "工作台与我的", "/pages/mine/index"),
    ("22",   "page-22-2",      "工作台与我的", "/pages/usage/index"),
    ("23",   "page-23-2",      "工作台与我的", "/pages/settings/index"),
]

FIELDS = ["序号", "页面ID", "页面名", "模块", "目标路由", "设计抓取", "交互抓取",
          "截图", "用例(证据)", "状态", "备注"]

STATUS_DONE = {"已验证"}


def load_pages():
    with open(INVENTORY, encoding="utf-8") as f:
        inv = json.load(f)
    return {p["id"]: p for p in inv["pages"]}


def load_existing():
    if not os.path.exists(LEDGER):
        return {}
    with open(LEDGER, encoding="utf-8-sig", newline="") as f:
        return {r["页面ID"]: r for r in csv.DictReader(f)}


def build():
    pages = load_pages()
    existing = load_existing()
    rows = []
    for seq, pid, module, route in PAGE_PLAN:
        p = pages.get(pid)
        if p is None:
            print(f"!! 页面 {pid} 不在 inventory 中", file=sys.stderr)
            continue
        old = existing.get(pid, {})
        rows.append({
            "序号": seq,
            "页面ID": pid,
            "页面名": p["name"],
            "模块": module,
            "目标路由": route,
            "设计抓取": "是" if p.get("designCaptured") else "否",
            "交互抓取": "是" if p.get("interactionCaptured") else "否",
            "截图": p.get("screenshot") or "",
            "用例(证据)": old.get("用例(证据)", ""),
            "状态": old.get("状态", "未做"),
            "备注": old.get("备注", ""),
        })
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows


def stats(rows):
    from collections import Counter
    c = Counter(r["状态"] for r in rows)
    total = len(rows)
    done = sum(v for k, v in c.items() if k in STATUS_DONE)
    print(f"台账：{LEDGER}")
    print(f"页面总数 {total} · 已验证 {done} · 未完成 {total - done}")
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    design = sum(1 for r in rows if r["设计抓取"] == "是")
    inter = sum(1 for r in rows if r["交互抓取"] == "是")
    print(f"设计已抓 {design}/{total} · 交互已抓 {inter}/{total}")


if __name__ == "__main__":
    r = build()
    stats(r)
