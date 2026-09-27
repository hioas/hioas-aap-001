# -*- coding: utf-8 -*-
"""窗口时刻解算（装置内**共享**纯函数，供 `run-round` 消费方 `analyze.py` 与 `independent.py` 共用）。

为什么需要它（真实返工，历史 12/244）：
  facts 里两轮 run 的起止只有 `HH:MM:SS`（无日期），而**轮次会跨午夜**——实测窗口出现过
  `2026-09-27 23:56:59 → 2026-09-28 00:02:04`（起止日期不同）。直接按字符串比单调性会把**合法窗口判成「非单调」**
  （`23:56:59 ≤ … ≤ 23:59:49` 之后接 `00:01:59` 恒为「逆序」）→ 独立复核探针 J1g 在合法轮次上
  报出假 FAIL。同一口径在 `analyze.py` A5 里另有一份副本（两轮之间实测存在 1 秒间隙：39 轮里 9 轮如此，
  故边界同样可能落在两轮之间）——故本模块作为**单一事实源**，两处消费者共用，杜绝两处分叉（历史 44/191）。

判据三态（缺一档就会误报或漏报）：
  ① 时间字面量非法 → 判据不可用；
  ② 窗口 ISO 不可用或跨度异常（>6h）→ 判据不可用（**不得判绿**，历史 46/98）；
  ③ 任一时刻在窗口内**无**合法落位（真的越界，如把 run1_end 注入成 13:00:00）→ 失败；
  ④ 全部落位唯一且非递减 → 通过。
牙齿保留：窗口 ≤6h ⇒ 合法落位唯一，故「注入到窗口之外」照旧转红（判别力实测见 `independent.py --selftest`）。
"""
import datetime
import re

FMT = "%Y-%m-%d %H:%M:%S"
HM_RE = re.compile(r"\d{2}:\d{2}:\d{2}")


def window_bounds(facts, max_hours=6.0):
    """窗口 [start, end]（含日期）。不可用/跨度异常 → None（判据不可用）。"""
    try:
        s = datetime.datetime.strptime(str(facts.get("FACTS_WINDOW_START_ISO", "")), FMT)
        e = datetime.datetime.strptime(str(facts.get("FACTS_WINDOW_END_ISO", "")), FMT)
    except (ValueError, TypeError):
        return None
    d = (e - s).total_seconds()
    if not (0 < d <= max_hours * 3600):        # 一轮窗口实测量级 ~5 分钟；>6h 说明 facts 异常
        return None
    return s, e


def resolve_window_seq(facts, keys):
    """把 `HH:MM:SS` 序列解算为绝对时刻后判非递减。返回 (ok, 说明)。"""
    vals = [facts.get(k) for k in keys]
    if any(not (isinstance(v, str) and HM_RE.fullmatch(v)) for v in vals):
        return False, "时间字面量非法：%s" % (vals,)
    b = window_bounds(facts)
    if b is None:
        return False, "窗口 ISO 不可用或跨度异常（判据不可用，历史 46/98）"
    s, e = b
    out = []
    for v in vals:
        h, m, sec = (int(x) for x in v.split(":"))
        cands = [t for t in (datetime.datetime.combine(d, datetime.time(h, m, sec))
                             for d in {s.date(), e.date()}) if s <= t <= e]
        if len(cands) != 1:
            return False, "%s 在窗口内合法落位 %d 个（须恰好 1：越界即异常）" % (v, len(cands))
        out.append(cands[0])
    detail = " → ".join(x.strftime(FMT) for x in out)
    return (out == sorted(out)), detail


def serial_ok(facts):
    """两轮是否串行（run1_end ≤ run2_start）。同一解算，跨午夜不假失败。"""
    return resolve_window_seq(facts, ("FACTS_RUN1_END", "FACTS_RUN2_START"))
