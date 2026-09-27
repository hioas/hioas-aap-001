#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R52 抽查：时区/桶口径一致性（第二十六类可审计不变量）。v2

不变量：**对外时间与所有「日/月/小时桶」边界一律 UTC**，且 RFC3339 出口
（格式串把 Z 写成**字面量** `'Z'`）的实参必须已经归一到 UTC。

为什么两套门禁都看不见：
  * 契约测试只读 JSON Schema，而 `format: date-time` 对 `+08:00` / 无偏移文本一律放行
    （甚至不是必须校验的关键字）→「本地墙钟被当成 UTC 输出」在 204 例全绿下完全不可见；
  * 覆盖门禁只比「方法+路径」；
  * 客户端 TS 不被任何测试执行 →「客户端用本机当前月去查服务端 UTC 月桶」同样不可见。

真源：M=md §0 时间行（RFC3339 UTC / 小时桶整点 / DATE yyyy-MM-dd）＋逐端点行；
      I=实现（RFC3339 格式串与出口实参的 offset 来源 / 取当前时间点 / 桶边界点 / 裸 date_trunc）；
      S=JSON Schema（date-time / date 字段是否有 pattern 约束）；
      C=客户端（本地日期派生点、把本地月当查询参数的调用点 —— 标识符须回查定义）；
      T=测试（是否钉 Z / 是否用 parse→toInstant 这类对偏移敏感的断言）。

v2 修正（v1 的真实返工）：
  ① v1 把 `month: formatMonthLabel(raw.month)`（**消费服务端返回值**的展示路径）当成「传本地月给服务端」
     → 假发现（坑 46/81：判据范围与语义不符）；真实调用点是 `month: month.value` 且 `month = ref(currentMonth())`
     → 必须**回查标识符定义**（坑 107）。
  ② v1 未统计「对偏移敏感的断言」（parse→toInstant），把「测试完全不敏感」说得过满（坑 95：结论句要与上文计数自洽）。

用法：python spotcheck-time-bucket-v2.py [--root <仓库或夹具根>]
"""
import os
import re
import sys

DEFAULT_ROOT = "E:/workspaces/hioas/hioas-aap-001"

PASS_LINES = []
FAIL_LINES = []
INFO_LINES = []


def ok(tag, msg):
    PASS_LINES.append("[PASS] %s %s" % (tag, msg))


def bad(tag, msg):
    FAIL_LINES.append("[FAIL] %s %s" % (tag, msg))


def info(tag, msg):
    INFO_LINES.append("[INFO] %s %s" % (tag, msg))


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def collect(root, pattern, subdirs):
    hits = []
    for sub in subdirs:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if re.search(pattern, name):
                    hits.append(os.path.join(dirpath, name))
    return sorted(hits)


FMT_DEF = re.compile(r"([A-Za-z0-9_]*RFC3339[A-Za-z0-9_]*)\s*=\s*"
                     r"DateTimeFormatter\.ofPattern\(\"([^\"]*)\"\)")
FORMAT_CALL = re.compile(r"RFC3339\.format\(")


def match_paren(text, open_idx):
    """括号深度扫描（坑 55/63 的正确实现）。"""
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def classify_format_arg(arg):
    a = arg.strip()
    if not a:
        return "未能静态判定"
    if "withOffsetSameInstant" in a and "ZoneOffset.UTC" in a:
        return "显式 UTC 归一"
    if "ZoneOffset.UTC" in a:
        return "now(UTC) 派生"
    if re.search(r"\bnow\(\)", a):
        return "本地墙钟（未归一到 UTC）"
    return "未能静态判定"


def java_files(root):
    return collect(root, r"\.java$", [os.path.join("aap-server", "src", "main", "java")])


def test_files(root):
    return collect(root, r"\.java$", [os.path.join("aap-server", "src", "test", "java")])


def ts_files(root):
    return collect(root, r"\.(ts|vue)$", [os.path.join("aap-client", "src")])


LOCAL_MONTH_DEF = re.compile(
    r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]*)?=\s*"
    r"(?:(?:ref|computed|shallowRef)\(\s*)?(currentMonth\(\)|new Date\(\))")


def local_month_vars(text):
    """回查「值为本机当前月」的局部变量（坑 107：标识符必须回查定义）。"""
    found = {}
    for m in LOCAL_MONTH_DEF.finditer(text):
        found[m.group(1)] = m.group(2)
    return found


def audit(root):
    # ---------------- I：实现
    fmt_defs, format_calls, bare_date_trunc, bucket_utc_points, local_wallclock_now = [], [], [], [], []
    for path in java_files(root):
        text = read(path)
        if text is None:
            continue
        rel = os.path.relpath(path, root).replace("\\", "/")
        for m in FMT_DEF.finditer(text):
            fmt_defs.append((rel, m.group(1), m.group(2)))
        for m in FORMAT_CALL.finditer(text):
            close_idx = match_paren(text, m.end() - 1)
            arg = text[m.end():close_idx] if close_idx > 0 else ""
            line_no = text[:m.start()].count("\n") + 1
            format_calls.append((rel, line_no, arg.strip(), classify_format_arg(arg)))
        for m in re.finditer(r"date_trunc\(\s*'(day|month|week|year)'\s*,([^)]*)\)", text):
            span = text[m.start():m.end() + 40]
            if "at time zone" not in span and "at time zone" not in m.group(2):
                bare_date_trunc.append((rel, m.group(1)))
        lines = text.splitlines()
        for m in re.finditer(r"ZoneOffset\.UTC", text):
            line_no = text[:m.start()].count("\n") + 1
            line = lines[line_no - 1] if line_no - 1 < len(lines) else ""
            if re.search(r"withDayOfMonth|atStartOfDay|withHour\(0\)|LocalDate\.now|to_char\(|at time zone", line):
                bucket_utc_points.append((rel, line_no, line.strip()))
        for m in re.finditer(r"OffsetDateTime\.now\(\)|LocalDate\.now\(\)|LocalDateTime\.now\(\)", text):
            line_no = text[:m.start()].count("\n") + 1
            local_wallclock_now.append((rel, line_no, m.group(0)))

    # ---------------- M：md 清单
    md = read(os.path.join(root, "docs", "backend", "02-API接口模型清单.md")) or ""
    md_time_row = [ln.strip() for ln in md.splitlines() if ln.strip().startswith("| 时间 |")]
    md_utc = bool(md_time_row) and "UTC" in md_time_row[0]
    md_hour_bucket = bool(md_time_row) and "小时桶" in md_time_row[0]

    # ---------------- S：JSON Schema
    schema_datetime = schema_date = schema_pattern_z = 0
    for path in collect(root, r"\.schema\.json$", [os.path.join("docs", "backend", "json-schema")]):
        text = read(path) or ""
        schema_datetime += len(re.findall(r"\"format\"\s*:\s*\"date-time\"", text))
        schema_date += len(re.findall(r"\"format\"\s*:\s*\"date\"", text))
        schema_pattern_z += len(re.findall(r"\"pattern\"\s*:\s*\"[^\"]*Z", text))

    # ---------------- C：客户端（本地月 → 查询参数，标识符回查定义）
    client_local_deriv, month_args, local_month_query_args = [], [], []
    for path in ts_files(root):
        text = read(path)
        if text is None:
            continue
        rel = os.path.relpath(path, root).replace("\\", "/")
        for m in re.finditer(r"getFullYear\(\)|getMonth\(\)|getDate\(\)|new Date\(\)", text):
            client_local_deriv.append((rel, text[:m.start()].count("\n") + 1, m.group(0)))
        vars_local = local_month_vars(text)
        for m in re.finditer(r"\bmonth\s*:\s*([A-Za-z_$][\w$]*(?:\.value)?)", text):
            line_no = text[:m.start()].count("\n") + 1
            expr = m.group(1)
            base = expr.split(".")[0]
            month_args.append((rel, line_no, expr, base in vars_local, vars_local.get(base, "")))
        # 变量在本文件里被当作查询实参传递（同一文件内的用法）
        for name, src in vars_local.items():
            if re.search(r"\bmonth\s*:\s*" + re.escape(name) + r"(?:\.value)?", text):
                local_month_query_args.append((rel, name, src))

    # ---------------- T：测试
    tests_z = tests_sensitive = 0
    for path in test_files(root):
        text = read(path) or ""
        tests_z += len(re.findall(r"endsWith\(\"Z\"\)", text))
        # 对偏移**敏感**的断言：parse(...).toInstant()。实参里含嵌套括号 → 必须括号配对扫描
        # （`OffsetDateTime\.parse\([^)]*\)` 会被 `path("read_at")` 的内层 `)` 提前截断 → 计到 0 处，
        #  得出「测试完全不敏感」的假发现；坑 46/63 同族）
        for m in re.finditer(r"(?:OffsetDateTime|Instant|ZonedDateTime)\.parse\(", text):
            close_idx = match_paren(text, m.end() - 1)
            if close_idx > 0 and text[close_idx + 1:close_idx + 11].startswith(".toInstant"):
                tests_sensitive += 1

    # ================================================================ 正向对照
    if format_calls:
        ok("P1", "Java 侧解析到 RFC3339 出口调用点 %d 处" % len(format_calls))
    else:
        bad("P1", "Java 侧解析到 RFC3339 出口调用点 0 处 → 解析器失效（两侧都 0 会让断言空转）")
    if fmt_defs:
        ok("P2", "RFC3339 格式串定义 %d 处" % len(fmt_defs))
    else:
        bad("P2", "未解析到任何 RFC3339 格式串定义 → 解析器失效")
    if md_time_row:
        ok("P3", "md §0 时间约定行解析到 %d 行" % len(md_time_row))
    else:
        bad("P3", "md §0 时间约定行解析到 0 行 → 解析器失效")
    if client_local_deriv:
        ok("P4", "客户端本机日期派生点解析到 %d 处" % len(client_local_deriv))
    else:
        bad("P4", "客户端本机日期派生点解析到 0 处 → 解析器失效")
    if bucket_utc_points:
        ok("P5", "服务端 UTC 桶边界取证点解析到 %d 处" % len(bucket_utc_points))
    else:
        bad("P5", "服务端 UTC 桶边界取证点解析到 0 处 → 解析器失效")
    if schema_datetime or schema_date:
        ok("P6", "JSON Schema 时间字段 format 解析到 date-time=%d / date=%d" % (schema_datetime, schema_date))
    else:
        bad("P6", "JSON Schema 里解析到 0 个时间 format → 解析器失效")
    if month_args:
        ok("P7", "客户端 month 实参解析到 %d 处（其中回查定义命中本机当前月 %d 处）"
           % (len(month_args), sum(1 for a in month_args if a[3])))
    else:
        bad("P7", "客户端 month 实参解析到 0 处 → 解析器失效")

    # ================================================================ A 组
    literal_z = [d for d in fmt_defs if "'Z'" in d[2]]
    if literal_z:
        ok("A0", "RFC3339 格式串把 Z 写作**字面量** %d 处（如 `%s`）→ 实参必须先归一到 UTC，"
                 "否则带偏移的墙钟会被当成 UTC 输出" % (len(literal_z), literal_z[0][2]))
    else:
        info("A0", "未发现字面量 Z 格式串（可能改用 XXX/偏移模式）→ 归一要求另判")

    unnormalized = [c for c in format_calls if c[3] == "本地墙钟（未归一到 UTC）"]
    unknown = [c for c in format_calls if c[3] == "未能静态判定"]
    if literal_z:
        if format_calls and not unnormalized and not unknown:
            ok("A1", "全部 %d 处 RFC3339 出口实参均已归一到 UTC（显式 withOffsetSameInstant(UTC) 或 now(ZoneOffset.UTC)）"
                     "→ 字面量 Z 与真实时刻一致" % len(format_calls))
        else:
            bad("A1", "有 %d 处出口实参未归一到 UTC、%d 处未能静态判定 → 输出的 Z 与真实时刻不符（明细见 A1d）"
                % (len(unnormalized), len(unknown)))
            for rel, line_no, arg, kind in unnormalized + unknown:
                info("A1d", "%s:%d [%s] %s" % (rel, line_no, kind, arg[:80]))
    else:
        info("A1", "无字面量 Z 格式串 → A1 不适用")

    if not bare_date_trunc:
        ok("A2", "实现里没有「不指定时区的 date_trunc('day'|'month'|…, timestamptz)」→ 桶边界不随 DB 会话时区漂移")
    else:
        bad("A2", "发现 %d 处会话时区依赖的 date_trunc：%s" % (len(bare_date_trunc), bare_date_trunc[:3]))

    if md_utc and md_hour_bucket:
        ok("A3", "md §0 声明「时间 RFC3339 UTC；小时桶为整点」")
    else:
        bad("A3", "md §0 时间约定行未解析出「UTC」或「小时桶」：%s" % (md_time_row[:1],))

    if bucket_utc_points:
        ok("A4", "服务端桶边界一律带 ZoneOffset.UTC（%d 处取证点）" % len(bucket_utc_points))
    else:
        bad("A4", "未取证到任何 UTC 桶边界点 → 无法证明月/日桶按 UTC")

    server_utc_month_bucket = [c for c in bucket_utc_points if "atStartOfDay" in c[2] or "withDayOfMonth" in c[2]]
    traced_local = [a for a in month_args if a[3]]
    if month_args and server_utc_month_bucket:
        if not traced_local:
            ok("A5", "客户端传给服务端月桶的 month 实参均**不**来自本机当前月（%d 个调用点，回查定义后无命中）"
                     "→ 桶口径跨源一致" % len(month_args))
        else:
            rel, line_no, expr, _flag, src = traced_local[0]
            bad("A5", "服务端月桶按 UTC 计算（取证点 %d 处），而客户端把**本机当前月**当 month 查询参数传给该端点"
                      "（%s:%d `%s` ← `%s`）→ 东八区每月 1 日 00:00–08:00 请求的月份在 UTC 口径下刚起头、桶为空；"
                      "跨源桶口径不一致（两套门禁都看不见）" % (len(server_utc_month_bucket), rel, line_no, expr, src))
            for rel2, name, src2 in local_month_query_args:
                info("A5d", "%s: `%s = %s` 被当作 month 查询实参" % (rel2, name, src2))
    else:
        bad("A5", "客户端 month 实参 %d 处 / 服务端 UTC 月桶取证点 %d 处 → 任一为 0 时该断言会空转，"
                  "故判解析失效而非通过（坑 98）" % (len(month_args), len(server_utc_month_bucket)))

    # ================================================================ B 组（信息项）
    if local_wallclock_now:
        info("B1", "无显式时区的取当前时间点 %d 处（落 timestamptz 是绝对时刻故安全，但若经未归一出口即漂移）：%s"
             % (len(local_wallclock_now), ["%s:%d" % (a, b) for a, b, _c in local_wallclock_now[:3]]))
    else:
        info("B1", "无 `now()` 无时区调用点")
    info("B2", "时间文本形状的测试背书：`endsWith(\"Z\")` 断言 %d 处；对偏移**敏感**的 parse→toInstant 断言 %d 处；"
               "其余 %d 个 date-time 字段只有 JSON Schema 的容忍校验（format 对 +08:00/无偏移一律放行）"
         % (tests_z, tests_sensitive, schema_datetime))
    if schema_pattern_z:
        ok("B3", "JSON Schema 里有 %d 处 pattern 约束 ...Z" % schema_pattern_z)
    else:
        info("B3", "JSON Schema 对时间字段无 Z 约束 → 出口漂移对全量用例不可见")

    # ================================================================ 输出
    print("== R52 时区/桶口径抽查（root=%s） ==" % root)
    print("解析计数：RFC3339 格式串定义 %d；出口调用点 %d（已归一 %d / now(UTC) 派生 %d / 未判定 %d）；"
          "裸 date_trunc %d；UTC 桶边界取证点 %d；客户端本机日期派生 %d；客户端 month 实参 %d（回查命中 %d）；"
          "md 时间行 %d；schema date-time %d / date %d；测试 endsWith Z %d / parse→toInstant %d"
          % (len(fmt_defs), len(format_calls),
             sum(1 for c in format_calls if c[3] == "显式 UTC 归一"),
             sum(1 for c in format_calls if c[3] == "now(UTC) 派生"),
             len(unknown), len(bare_date_trunc), len(bucket_utc_points),
             len(client_local_deriv), len(month_args), len(traced_local), len(md_time_row),
             schema_datetime, schema_date, tests_z, tests_sensitive))
    for line in PASS_LINES + FAIL_LINES + INFO_LINES:
        print(line)
    print("汇总: PASS %d / FAIL %d / INFO %d" % (len(PASS_LINES), len(FAIL_LINES), len(INFO_LINES)))
    print("A5 明细（客户端 month 实参逐条）：")
    for rel, line_no, expr, hit, src in month_args:
        print("  %s:%d  month: %-28s 回查命中本机当前月=%s %s" % (rel, line_no, expr, hit, ("← " + src) if hit else ""))
    print("A1 明细（出口实参分类）：")
    for rel, line_no, arg, kind in format_calls:
        print("  %-70s %s | %s" % ("%s:%d" % (rel, line_no), kind, arg[:60]))
    return 1 if FAIL_LINES else 0


def main(argv):
    root = DEFAULT_ROOT
    if "--root" in argv:
        root = argv[argv.index("--root") + 1]
    return audit(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
