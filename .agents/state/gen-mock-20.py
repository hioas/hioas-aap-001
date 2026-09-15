#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成序号 20（站内信列表 / page-20-2）的 H5 mock 数据。

为什么要生成而不是手写：设计帧的时间写法是**相对当前时间**的（10 分钟前 / 2 小时前 /
昨天 18:20 / 3 天前 / 5 天前），写死时间戳在下次跑测量时就对不上设计文案。
本脚本按「运行时刻」反推 created_at，保证 H5 实测文案与设计帧逐字一致。

用法：python .agents/state/gen-mock-20.py
产物：.agents/state/h5-measure/api-20/v1/notifications/index（列表）
      + n1..n3 的 /read POST mock
"""
import datetime
import io
import json
import os

ROOT = os.path.join(".agents", "state", "h5-measure", "api-20", "v1", "notifications")
os.makedirs(ROOT, exist_ok=True)

now = datetime.datetime.now().replace(microsecond=0)
yesterday = (now - datetime.timedelta(days=1)).replace(hour=18, minute=20, second=0)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "+08:00"


items = [
    {
        "id": "n1",
        "title": "检测报告已生成（通过）",
        "content": "华东主线路综合评分 92 分，可进入报价流程。",
        "created_at": iso(now - datetime.timedelta(minutes=10)),
        "event_code": "DETECTION_PASSED",
        "biz_type": "REPORT",
        "biz_id": "r1",
    },
    {
        "id": "n2",
        "title": "报价单被驳回，请修改后重提",
        "content": "06 月增量报价：输出价高于市场均价 18%。",
        "created_at": iso(now - datetime.timedelta(hours=2)),
        "event_code": "QUOTE_REJECTED",
        "biz_type": "QUOTE",
        "biz_id": "q1",
    },
    {
        "id": "n3",
        "title": "合同待签署提醒",
        "content": "API 接入服务合同请在 06-20 前完成签署。",
        "created_at": iso(yesterday),
        "event_code": "CONTRACT_SIGN_REMINDER",
        "biz_type": "CONTRACT",
        "biz_id": "ct1",
    },
    {
        "id": "n4",
        "title": "6 月账单已出，结算金额 ¥12,860.00",
        "content": "预计 07-15 打款至绑定对公账户。",
        "created_at": iso(now - datetime.timedelta(days=3)),
        "read_at": iso(now - datetime.timedelta(days=3)),
        "biz_type": "BILL",
        "biz_id": "b1",
    },
    {
        "id": "n5",
        "title": "平台系统升级公告",
        "content": "06-16 02:00–04:00 计费系统维护，期间不影响调用。",
        "created_at": iso(now - datetime.timedelta(days=5)),
        "read_at": iso(now - datetime.timedelta(days=5)),
        "event_code": "SYSTEM_NOTICE",
    },
]


def write(path, payload):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=2))
    print("wrote", path)


write(
    os.path.join(ROOT, "index"),
    {"code": "0", "message": "ok", "data": {"total": len(items), "items": items}},
)

for nid in ("n1", "n2", "n3"):
    read_dir = os.path.join(ROOT, nid, "read")
    os.makedirs(read_dir, exist_ok=True)
    write(os.path.join(read_dir, "post"), {"code": "0", "message": "ok", "data": {"id": nid}})

print("now =", iso(now))
