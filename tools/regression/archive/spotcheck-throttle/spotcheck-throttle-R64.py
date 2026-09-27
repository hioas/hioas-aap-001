#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R64 抽查（只读）：**频控 / 配额 / 退避阈值契约**（第三十八类可审计不变量）。

为什么两套门禁都看不见：
  契约测试只把**响应体**与 JSON Schema 比对，而阈值是**行为语义**（"60s 内重复发码被拒"、
  "连续 5 次错码锁定 15 分钟"、"日配额 5 次"、"退避 30s/2m/8m/30m ≤5 次"）——
  任何 schema 里都没有阈值数值，`requests/*.schema.json` 也不描述行为；覆盖门禁只比「方法 + 路径」；
  openapi 与客户端 TS 不被任何测试读取/执行 → 204 例全绿也查不出「声明 2h 退避而实现只排到 30 分钟」这类漂移。

真源：
  M  = md 清单（逐端点「幂等/并发」列〔10 列表〕/「请求·响应」列〔7 列表〕＋ §4 错误码表场景列）
  Y  = application.yml（app.sms.* / app.detection.daily-quota）
  J  = 实现（AppProperties.Sms 分量 / SmsService 取值点与用户可见文案 / DetectionService 默认值与守卫 /
             SyncAdminService MAX_ATTEMPTS 与 BACKOFF 档序列）
  E  = ErrorCode（码 → HTTP 状态）
  T  = 测试源（阈值数值的断言：次数、时长、档序列）
  C  = 客户端（是否对频控码做专门处置）
  P  = PRD 17-spec R-40（退避序列的第三方裁判）
用法：python spotcheck-throttle-R64.py [--root <dir>]
"""
import argparse
import re
import sys
from pathlib import Path

FAIL_RE = re.compile(r"\[FAIL\s*\]")

PASS, FAILS, INFOS = [], [], []


def ok(tok, msg):
    PASS.append("[PASS] %s %s" % (tok, msg))


def bad(tok, msg):
    FAILS.append("[FAIL] %s %s" % (tok, msg))


def info(tok, msg):
    INFOS.append("[INFO] %s %s" % (tok, msg))


def read(path):
    """文件缺失返回空串（坑 128：不得崩，让正向对照自己转红）。"""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- 解析器

def split_row(line):
    """md 表格按**未转义**竖线切分并还原字面竖线（坑 48/89）。"""
    cells = re.split(r"(?<!\\)\|", line)
    cells = [c.strip().replace("\\|", "|") for c in cells]
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def parse_md(text):
    """返回 (endpoint_rows, header_kinds, code_table)。行 = {id, cells, header}。"""
    rows, kinds, codes, header = [], {}, {}, None
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = split_row(s)
        if cells and cells[0] == "ID":
            header = cells
            kinds["10" if "幂等/并发" in cells else "7"] = kinds.get("10" if "幂等/并发" in cells else "7", 0) + 1
            continue
        if cells and set("".join(cells)) <= set("-: "):
            continue
        m = re.match(r"^\|\s*`(E-\d{4})`\s*\|\s*(\d{3})\s*\|\s*(.*?)\s*\|$", s)
        if m:
            codes[m.group(1)] = {"http": int(m.group(2)), "scene": m.group(3)}
            continue
        if header and cells and re.match(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$", cells[0]):
            rows.append({"id": cells[0], "cells": cells, "header": header})
    return rows, kinds, codes


THRESH_RE = re.compile(r"频控|配额|锁定|退避|错锁")


def md_thresholds(rows):
    """阈值声明：10 列表取「幂等/并发」列，7 列表取「请求/响应」列。"""
    out = []
    for r in rows:
        h, c = r["header"], r["cells"]
        col, kind = None, None
        if "幂等/并发" in h:
            i = h.index("幂等/并发")
            col, kind = (c[i] if i < len(c) else None), "10"
        elif "请求/响应" in h:
            i = h.index("请求/响应")
            col, kind = (c[i] if i < len(c) else None), "7"
        if col and THRESH_RE.search(col):
            out.append({"id": r["id"], "col": col, "kind": kind})
    return out


def first_int(text, key, default=None):
    m = re.search(r"(?m)^\s*%s:\s*(\d+)\s*$" % re.escape(key), text)
    return int(m.group(1)) if m else default


def durations_to_seconds(tokens):
    out = []
    for num, unit in tokens:
        n = int(num)
        out.append(n * {"s": 1, "m": 60, "h": 3600}[unit])
    return out


def parse_backoff_tokens(expr):
    return durations_to_seconds(re.findall(r"(\d+)([smh])\b", expr))


def parse_impl_sync(text):
    m = re.search(r"MAX_ATTEMPTS\s*=\s*(\d+)", text)
    attempts = int(m.group(1)) if m else None
    b = re.search(r"BACKOFF\s*=\s*\{(.*?)\}", text, re.S)
    seq = []
    if b:
        for d in re.finditer(r"Duration\.of(Seconds|Minutes|Hours)\((\d+)\)", b.group(1)):
            seq.append(int(d.group(2)) * {"Seconds": 1, "Minutes": 60, "Hours": 3600}[d.group(1)])
    return attempts, seq


def parse_errcode(text, code):
    num = code.split("-")[1]
    m = re.search(r'E_%s\("E-%s",\s*(\d+)' % (num, num), text)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- 主流程

def audit(root, verbose=True):
    P = {k: Path(root) / v for k, v in {
        "md": "docs/backend/02-API接口模型清单.md",
        "yml": "aap-server/src/main/resources/application.yml",
        "appprops": "aap-server/src/main/java/com/hioas/aap/config/AppProperties.java",
        "sms": "aap-server/src/main/java/com/hioas/aap/iam/SmsService.java",
        "det": "aap-server/src/main/java/com/hioas/aap/detection/DetectionService.java",
        "sync": "aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java",
        "errcode": "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java",
        "t_auth": "aap-server/src/test/java/com/hioas/aap/iam/AuthContractTest.java",
        "t_det": "aap-server/src/test/java/com/hioas/aap/detection/DetectionContractTest.java",
        "t_sync": "aap-server/src/test/java/com/hioas/aap/sync/SyncAdminContractTest.java",
        "client": "aap-client/src/api/http.ts",
        "prd": ".calicat/prd/17-零歧义执行规格spec.md",
    }.items()}
    T = {k: read(v) for k, v in P.items()}

    rows, kinds, codes = parse_md(T["md"])
    thr = md_thresholds(rows)
    yml = {k: first_int(T["yml"], k) for k in
           ("ttl-seconds", "resend-interval-seconds", "max-attempts", "lock-minutes", "daily-quota")}
    sms_cfg_uses = sorted(set(re.findall(r"config\.(\w+)\(\)", T["sms"])))
    hardcoded_min = re.findall(r'"[^"\n]*?(\d+)\s*分钟[^"\n]*?"', T["sms"])
    det_default = re.search(r'app\.detection\.daily-quota:(\d+)', T["det"])
    det_guard = "today >= dailyQuota" in T["det"]
    attempts, backoff = parse_impl_sync(T["sync"])
    e1302, e1903 = parse_errcode(T["errcode"], "E-1302"), parse_errcode(T["errcode"], "E-1903")

    md_backoff_expr = ""
    for t in thr:
        m = re.search(r"退避\s*([0-9smh/]+)", t["col"])
        if m:
            md_backoff_expr = m.group(1)
    md_backoff = parse_backoff_tokens(md_backoff_expr)
    prd_backoff = []
    m = re.search(r"R-40[^；\n]*?(\d+s(?:/\d+[smh])+)", T["prd"])
    if m:
        prd_backoff = parse_backoff_tokens(m.group(1))
    m = re.search(r"expectedSeconds\s*=\s*\{([^}]*)\}", T["t_sync"])
    test_backoff = [int(x) for x in re.findall(r"(\d+)L?", m.group(1))] if m else []

    n_429_auth = len(re.findall(r"isEqualTo\(429\)", T["t_auth"]))
    n_429_det = len(re.findall(r"isEqualTo\(429\)", T["t_det"]))
    ttl_backed = bool(re.search(r'ttl[^\n]{0,120}isEqualTo\(\s*300\s*\)', T["t_auth"]))
    win60_backed = bool(re.search(r"plusSeconds\(\s*60\s*\)|resendIntervalSeconds", T["t_auth"]))
    lock15_backed = bool(re.search(r"plusMinutes\(\s*15\s*\)|lockMinutes", T["t_auth"]))
    quota_backed = bool(re.search(r"i\s*<\s*5|i\s*<=\s*5|daily-quota", T["t_det"])) and n_429_det > 0
    backoff_backed = bool(test_backoff) and "isBetween" in T["t_sync"]
    client_branches = re.findall(r"status\s*===\s*(\d+)", T["client"])
    client_429 = bool(re.search(r"status\s*===\s*429|case\s+429|E-1903|E-1302", T["client"]))

    # ---------------- 正向对照（任一为 0 先怀疑解析器，坑 46/75/98/132）
    if rows:
        ok("A0a", "md 端点行解析到 %d 行" % len(rows))
    else:
        bad("A0a", "md 端点行解析到 0 行 → 解析器失效，判定不可用")
    if kinds.get("10") and kinds.get("7"):
        ok("A0b", "双表头各解析到行（10 列 %d / 7 列 %d），坑 89" % (kinds.get("10"), kinds.get("7")))
    else:
        bad("A0b", "双表头解析异常（10 列 %s / 7 列 %s）→ 判定不可用"
            % (kinds.get("10"), kinds.get("7")))
    k10 = [t for t in thr if t["kind"] == "10"]
    k7 = [t for t in thr if t["kind"] == "7"]
    if thr and k10 and k7:
        ok("A0c", "阈值声明行 %d 条（10 列 %d：%s；7 列 %d：%s）"
           % (len(thr), len(k10), ",".join(t["id"] for t in k10), len(k7),
              ",".join(t["id"] for t in k7)))
    else:
        bad("A0c", "阈值声明行解析异常（总 %d / 10 列 %d / 7 列 %d）→ 判定不可用"
            % (len(thr), len(k10), len(k7)))
    yml_keys = [k for k, v in yml.items() if v is not None]
    if len(yml_keys) >= 4:
        ok("A0d", "yml 解析到 %d 个阈值键：%s" % (len(yml_keys), ",".join(yml_keys)))
    else:
        bad("A0d", "yml 阈值键只解析到 %s → 判定不可用" % yml_keys)
    if sms_cfg_uses and det_default and attempts and backoff:
        ok("A0e", "实现解析到 SmsService 取值点 %d 个、检测配额默认值 %s、重试上限 %s、退避 %d 档"
           % (len(sms_cfg_uses), det_default.group(1), attempts, len(backoff)))
    else:
        bad("A0e", "实现解析异常（取值点 %s / 默认值 %s / 上限 %s / 退避 %s）→ 判定不可用"
            % (sms_cfg_uses, det_default, attempts, backoff))
    if codes and any(v["http"] == 429 for v in codes.values()):
        ok("A0f", "§4 码表解析到 %d 个码，其中 429 共 %d 个"
           % (len(codes), sum(1 for v in codes.values() if v["http"] == 429)))
    else:
        bad("A0f", "§4 码表解析异常（%d 个码，429 %d 个）→ 判定不可用"
            % (len(codes), sum(1 for v in codes.values() if v["http"] == 429)))
    if n_429_auth + n_429_det > 0:
        ok("A0g", "测试源解析到 429 状态断言 %d 处（auth %d / detection %d）"
           % (n_429_auth + n_429_det, n_429_auth, n_429_det))
    else:
        bad("A0g", "测试源 429 断言解析到 0 处 → 判定不可用")
    if client_branches:
        ok("A0h", "客户端解析到状态分支 %d 个（%s）" % (len(client_branches), ",".join(sorted(set(client_branches)))))
    else:
        bad("A0h", "客户端状态分支解析到 0 个 → 判定不可用")
    if prd_backoff:
        ok("A0i", "PRD R-40 退避序列解析到 %d 档（%s）" % (len(prd_backoff), prd_backoff))
    else:
        bad("A0i", "PRD R-40 退避序列解析到 0 档 → 判定不可用")

    # ---------------- A1 短信阈值：md ⇔ yml ⇔ 实现
    md_ttl = None
    m = re.search(r"ttl[:：]?\s*(\d+)", " ".join(r["cells"][4] + r["cells"][5]
                                                 for r in rows if r["id"] == "AUTH-01"))
    if m:
        md_ttl = int(m.group(1))
    md_win = None
    for t in thr:
        m = re.search(r"(\d+)s\s*频控", t["col"])
        if m:
            md_win = int(m.group(1))
    md_lock = None
    for t in thr:
        m = re.search(r"(\d+)\s*次[^\n]*?(\d+)\s*分钟", t["col"])
        if m:
            md_lock = (int(m.group(1)), int(m.group(2)))
    pairs = [("ttl(秒)", md_ttl, yml["ttl-seconds"]), ("频控窗口(秒)", md_win, yml["resend-interval-seconds"]),
             ("锁定次数", md_lock[0] if md_lock else None, yml["max-attempts"]),
             ("锁定时长(分钟)", md_lock[1] if md_lock else None, yml["lock-minutes"])]
    mismatch = [(n, a, b) for n, a, b in pairs if a is not None and a != b]
    if all(a is not None for _, a, _ in pairs) and not mismatch:
        ok("A1", "短信阈值 md ⇔ yml 逐项一致：%s；实现 %d 个取值点全部走 config（%s），0 处阈值硬编码"
           % (", ".join("%s=%s" % (n, a) for n, a, _ in pairs), len(sms_cfg_uses), ",".join(sms_cfg_uses)))
    else:
        bad("A1", "短信阈值不一致：md=%s yml=%s 偏差=%s" % (pairs, yml, mismatch))

    # ---------------- A2 日配额
    md_quota = None
    m = re.search(r"配额[^\d]*(\d+)\s*次", " ".join(t["col"] for t in thr) + " " +
                  " ".join(v["scene"] for v in codes.values()))
    if m:
        md_quota = int(m.group(1))
    impl_quota = int(det_default.group(1)) if det_default else None
    if md_quota is not None and md_quota == yml["daily-quota"] == impl_quota and det_guard:
        ok("A2", "日配额 md=%s ⇔ yml=%s ⇔ 实现默认值=%s，且实现有守卫（%s）"
           % (md_quota, yml["daily-quota"], impl_quota, "today >= dailyQuota"))
    else:
        bad("A2", "日配额不一致：md=%s yml=%s 实现默认=%s 守卫=%s"
            % (md_quota, yml["daily-quota"], impl_quota, det_guard))

    # ---------------- A3 退避档序列三方比对
    if md_backoff and backoff:
        if md_backoff == backoff:
            ok("A3a", "退避档序列 md ⇔ 实现一致：%s" % md_backoff)
        else:
            bad("A3a", "退避档序列 md ⇔ 实现不一致：md=%s（%d 档）实现=%s（%d 档，MAX_ATTEMPTS=%s，"
                "语义=1 次立即 + %d 次退避）→ 声明的最长退避在实现中不存在"
                % (md_backoff, len(md_backoff), backoff, len(backoff), attempts, len(backoff)))
    else:
        bad("A3a", "退避档序列判定不可用（md=%s 实现=%s）" % (md_backoff, backoff))
    if md_backoff and prd_backoff:
        if md_backoff == prd_backoff:
            ok("A3b", "退避档序列 md ⇔ PRD R-40 一致：%s" % md_backoff)
        else:
            bad("A3b", "退避档序列 md ⇔ PRD R-40 不一致：md=%s PRD=%s（第三方裁判：PRD）"
                % (md_backoff, prd_backoff))
    else:
        bad("A3b", "退避档序列判定不可用（md=%s PRD=%s）" % (md_backoff, prd_backoff))
    if backoff and test_backoff:
        if backoff == test_backoff:
            ok("A3c", "退避档序列 实现 ⇔ 测试期望一致：%s（含 isBetween 容差断言）" % backoff)
        else:
            bad("A3c", "退避档序列 实现 ⇔ 测试期望不一致：实现=%s 测试=%s" % (backoff, test_backoff))
    else:
        bad("A3c", "退避档序列判定不可用（实现=%s 测试=%s）" % (backoff, test_backoff))

    # ---------------- A4 阈值数值的测试背书（分档）
    if T["t_auth"]:
        (ok if ttl_backed else bad)(
            "A4a", "ttl=300 数值有测试背书" if ttl_backed
            else "ttl=300 只有结构背书（schema 校验 ttl 存在），数值零断言 → 阈值可被改成任意值而全量用例仍绿")
        (ok if win60_backed else bad)(
            "A4b", "60s 频控窗口有测试背书" if win60_backed
            else "60s 频控窗口只有「重复发码 → 429」的码断言，窗口时长数值零断言（测试无法证明是 60s）")
        (ok if lock15_backed else bad)(
            "A4c", "15 分钟锁定时长有测试背书" if lock15_backed
            else "15 分钟锁定时长只有「locked_until 非空」的断言，时长数值零断言（无法证明是 15 分钟）")
    else:
        bad("A4a", "判定不可用：测试源缺失")
        bad("A4b", "判定不可用：测试源缺失")
        bad("A4c", "判定不可用：测试源缺失")
    if T["t_det"]:
        (ok if quota_backed else bad)("A4d", "日配额 5 次有测试背书（造满 5 条后 429 E-1302）" if quota_backed
                                      else "日配额阈值零背书")
    else:
        bad("A4d", "判定不可用：检测测试源缺失")
    if T["t_sync"]:
        (ok if backoff_backed else bad)("A4e", "退避 4 档数值有测试背书（expectedSeconds + isBetween）" if backoff_backed
                                        else "退避档数值零背书")
    else:
        bad("A4e", "判定不可用：同步测试源缺失")

    # ---------------- A5 用户可见文案里的硬编码时长副本
    if T["sms"]:
        if hardcoded_min:
            bad("A5", "用户可见文案硬编码时长 %d 处（%s 分钟），与 config.lockMinutes() 脱钩 → "
                "配置改值后提示失真（同值硬编码副本，坑 122 的阈值版）"
                % (len(hardcoded_min), ",".join(sorted(set(hardcoded_min)))))
        else:
            ok("A5", "用户可见文案无硬编码时长副本（时长一律取自 config）")
    else:
        bad("A5", "判定不可用：SmsService 缺失")

    # ---------------- A6 客户端对频控码的处置
    if T["client"]:
        if client_429:
            ok("A6", "客户端对频控/配额码有专门处置")
        else:
            bad("A6", "客户端对 429 / 频控码零专门处置（仅 %s 分支）→ 频控提示只能靠服务端 message 透传"
                "（风险项，待拍板）" % ",".join(sorted(set(client_branches))))
    else:
        bad("A6", "判定不可用：客户端源缺失")

    # ---------------- A7 码 → HTTP 状态
    checks = []
    for code, impl_http in (("E-1302", e1302), ("E-1903", e1903)):
        md_http = codes.get(code, {}).get("http")
        checks.append((code, md_http, impl_http))
    if all(a is not None and a == b == 429 for _, a, b in checks):
        ok("A7", "限流/配额码 → HTTP 429 与 §4 一致：%s" % ", ".join("%s md=%s 实现=%s" % c for c in checks))
    else:
        bad("A7", "码 → HTTP 状态不一致：%s" % checks)

    # ---------------- A8 已知登记项（不重复计入新增）
    info("A8", "已知登记项（R29 裁决，不在本轮新增）：md AUTH-02 行的错误码列未声明实现真会抛的 E-1903；"
               "§4 对 E-1903 的语义描述为「限流（短信 60s 频控等）」，未显式覆盖「连续错码锁定」")
    info("A9", "阈值真源分布：md §0 通用约定**无**频控/配额行（0 处），阈值声明只在逐端点列与 §4 码表；"
               "PRD R-12（压测成本保护 $2/任务）与 R-13（RPM 硬上限 60 req/s）不在 md 清单端点行 → "
               "不属冻结契约表面，不判漂移")

    if verbose:
        print("== R64 抽查：频控 / 配额 / 退避阈值契约（第三十八类可审计不变量） ==")
        print("root = %s" % root)
        print("解析计数：md 端点行 %d（10 列 %d / 7 列 %d）· 阈值声明行 %d · §4 码 %d · yml 阈值键 %d · "
              "退避 md=%s 实现=%s PRD=%s 测试=%s"
              % (len(rows), kinds.get("10"), kinds.get("7"), len(thr), len(codes), len(yml_keys),
                 md_backoff, backoff, prd_backoff, test_backoff))
        print("")
        for ln in PASS + FAILS + INFOS:
            print(ln)
        print("")
        print("== 汇总 ==")
        print("PASS %d / FAIL %d / INFO %d" % (len(PASS), len(FAILS), len(INFOS)))
        print("FAIL token 集合 = %s" % sorted({ln.split()[1] for ln in FAILS}))
    return FAILS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/workspaces/hioas/hioas-aap-001")
    ap.add_argument("--tokens", action="store_true", help="只打印 FAIL token 集合（供判别力自测）")
    args = ap.parse_args()
    fails = audit(args.root, verbose=not args.tokens)
    if args.tokens:
        print(" ".join(sorted({ln.split()[1] for ln in fails})))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
