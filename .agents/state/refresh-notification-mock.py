#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 api-20 站内信 mock 的 created_at 重写成「相对现在」的时间戳。

为什么需要它：设计帧 page-20-2 的 5 条消息时间文案是**相对时间**
（10 分钟前 / 2 小时前 / 昨天 18:20 / 3 天前 / 5 天前）。
mock 是静态 JSON，第一次建页（2026-09-16 05:2x）把绝对时间写死，
之后每跑一轮「10 分钟前 / 2 小时前」就会漂成「N 小时前」→
08:11 复核轮的 missingTexts 里已经出现这两条**假缺陷**
（页面没问题，是测量面过期）。

规则与 src/utils/messages-model.ts formatMessageTime 一致：
  diffMin < 60            → "N 分钟前"
  同日（dayDiff 0）        → "N 小时前"
  dayDiff 1              → "昨天 HH:mm"
  2 ≤ dayDiff ≤ 6         → "N 天前"

用法：
  python .agents/state/refresh-notification-mock.py [--mock api-20] [--check]
  --check 只打印「按当前 mock 会渲染成什么」并核对设计字面量，不写文件。
"""
import argparse
import datetime as dt
import io
import json
import os
import sys

ROOT = r"E:/workspaces/hioas/hioas-aap-001"
TZ = dt.timezone(dt.timedelta(hours=8))

# 设计帧 5 条时间的写法（逐字）与生成规则
PLAN = {
    "n1": ("minutes", 10, "10 分钟前"),
    "n2": ("hours", 2, "2 小时前"),
    "n3": ("yesterday_fixed", (18, 20), "昨天 18:20"),
    "n4": ("days", 3, "3 天前"),
    "n5": ("days", 5, "5 天前"),
}


def start_of_day(d):
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def render(created, now):
    """与 messages-model.ts formatMessageTime 同规则，返回 (文案, 说明)。"""
    t = created
    diff_min = int((now - t).total_seconds() // 60)
    if diff_min < 1:
        return "刚刚", "diffMin<1"
    if diff_min < 60:
        return "%d 分钟前" % diff_min, "diffMin<60"
    day_diff = round((start_of_day(now) - start_of_day(t)).days)
    if day_diff == 0:
        return "%d 小时前" % (diff_min // 60), "dayDiff=0"
    if day_diff == 1:
        return "昨天 %02d:%02d" % (t.hour, t.minute), "dayDiff=1"
    if 1 < day_diff < 7:
        return "%d 天前" % day_diff, "2<=dayDiff<=6"
    return "%02d-%02d" % (t.month, t.day), "dayDiff>=7"


def iso(d):
    return d.astimezone(TZ).replace(microsecond=0).isoformat()


def build_times(now):
    out = {}
    for key, (kind, arg, _want) in PLAN.items():
        if kind == "minutes":
            out[key] = now - dt.timedelta(minutes=arg)
        elif kind == "hours":
            out[key] = now - dt.timedelta(hours=arg)
        elif kind == "yesterday_fixed":
            y = start_of_day(now) - dt.timedelta(days=1)
            out[key] = y.replace(hour=arg[0], minute=arg[1])
        elif kind == "days":
            out[key] = now - dt.timedelta(days=arg)
    return out


def warn_window(now, times):
    warnings = []
    for key, (kind, arg, _want) in PLAN.items():
        text, _why = render(times[key], now)
        if text != _want:
            warnings.append((key, _want, text))
    return warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="api-20")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    path = os.path.join(ROOT, ".agents/state/h5-measure", args.mock, "v1/notifications/index")
    if not os.path.isfile(path):
        print("mock fixture 不存在: %s" % path)
        return 1
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh)

    now = dt.datetime.now(TZ)
    times = build_times(now)
    items = doc.get("data", {}).get("items", [])
    print("now = %s" % iso(now))

    changed = 0
    for item in items:
        nid = str(item.get("id"))
        if nid not in times:
            continue
        stamp = iso(times[nid])
        if item.get("created_at") != stamp:
            item["created_at"] = stamp
            changed += 1
        if item.get("read_at"):
            item["read_at"] = stamp
    for key, (_kind, _arg, want) in PLAN.items():
        text, why = render(times[key], now)
        mark = "OK " if text == want else "WARN"
        print("  %s %s: created_at=%s -> 渲染「%s」 (设计「%s」, %s)" % (mark, key, iso(times[key]), text, want, why))

    warnings = warn_window(now, times)
    for key, want, got in warnings:
        print("  ⚠️ 当前时刻无法生成设计字面量：%s 期望「%s」实得「%s」"
              "（00:00~02:00 之间「2 小时前」会跨日）" % (key, want, got))

    if args.check:
        print("check 模式：未写文件")
        return 0

    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2))
        fh.write("\n")
    print("wrote %s（%d 条 created_at 更新）" % (path, changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
