#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R52 抽查脚本 spotcheck-time-bucket-v2.py 的负向自测（判别力）。

纪律：
  * 脚本与夹具**分目录**（坑 106）；
  * 每个判定分支一条反例；空夹具必须变红（防空转，坑 46/57/75/98）；
  * 注入缺陷必须**真的改到源码**（mutate() 回传未命中锚点，先断言为空，坑 66/94）；
  * 基线与被测结果**分别命名**（基线 ok_out，坑 93）；
  * FAIL 集合按**断言前缀**比对，不比整行（坑 82/103）；
  * 真实仓库只读守卫：审计真实仓库必须只报已登记的 A5；
  * 零写副作用：比对运行前后全部相关文件的 (size, md5)。
"""
import hashlib
import importlib.util
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "spotcheck-time-bucket-v2.py")
FIXROOT = os.path.join(os.path.dirname(SCRIPT_DIR.rstrip("/\\")), "aap-r52-spotcheck-fixtures")
REPO = "E:/workspaces/hioas/hioas-aap-001"

spec = importlib.util.spec_from_file_location("spotcheck_time_bucket_v2", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CASE = []
FAILSELF = []


def check(name, cond, detail=""):
    if cond:
        CASE.append("[PASS] " + name)
    else:
        FAILSELF.append("[FAIL] " + name + ("  " + detail if detail else ""))


def fails_tokens():
    """按断言前缀取 FAIL token 集合（坑 82/103）。"""
    return set(t.split()[1] for t in mod.FAIL_LINES if len(t.split()) > 1)


def run(root):
    mod.PASS_LINES.clear()
    mod.FAIL_LINES.clear()
    mod.INFO_LINES.clear()
    import io
    buf = io.StringIO()
    real = sys.stdout
    sys.stdout = buf
    try:
        rc = mod.audit(root)
    finally:
        sys.stdout = real
    return rc, buf.getvalue()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def mutate(path, pairs):
    """按 (old,new) 逐条 replace，返回未命中的锚点列表（坑 66/94）。"""
    text = mod.read(path)
    missed = []
    for old, new in pairs:
        if old not in text:
            missed.append(old)
            continue
        text = text.replace(old, new)
    write(path, text)
    return missed


# --------------------------------------------------------------- 夹具内容
MD = """# 清单

| 项 | 约定 |
| --- | --- |
| 时间 | RFC3339 **UTC**；小时桶为整点；`DATE` 字段 `yyyy-MM-dd` |

| ID | 方法 | 路径 | 认证 | 请求 | 响应 | 错误码 | 幂等 | 来源 | 任务号 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| USE-01 | GET | `/usage/summary` | ✅ | q：`startHour?` `endHour?` `month?` | `UsageSummary` | E-1801 | | 真源 | T12 |
"""

SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "created_at": { "type": "string", "format": "date-time" }
  }
}
"""

SVC = """package com.x;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

public class Svc {
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    public String view(OffsetDateTime value) {
        return RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    public String nowText() {
        return RFC3339.format(OffsetDateTime.now(ZoneOffset.UTC));
    }

    public String monthBucketStart(String month) {
        YearMonth ym = YearMonth.parse(month);
        return RFC3339.format(ym.atDay(1).atStartOfDay().atOffset(ZoneOffset.UTC));
    }

    public String dayBucket() {
        LocalDate firstOfMonth = LocalDate.now(ZoneOffset.UTC).withDayOfMonth(1);
        return firstOfMonth.toString();
    }
}
"""

TEST = """package com.x;

public class T {
    void a() {
        org.assertj.core.api.Assertions.assertThat(text).endsWith("Z");
    }
}
"""

USAGE_TS = """import { http } from './http'

export const usageApi = {
  overview(params?: { month?: string }) {
    return http('/usage/summary', { method: 'GET', data: params })
  }
}
"""

USAGE_VUE = """<script setup lang="ts">
import { ref } from 'vue'
import { usageApi } from '@/api/usage'
import { formatMonthLabel } from '@/utils/usage-model'

const month = ref(props.month)
async function load() {
  const res = await usageApi.overview({ month: month.value })
  label.value = formatMonthLabel(res.month)
}
</script>
"""

FMT_TS = """export function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

export function label(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${d.getDate()}`
}
"""


def build_fixture(root):
    shutil.rmtree(root, ignore_errors=True)
    write(os.path.join(root, "docs/backend/02-API接口模型清单.md"), MD)
    write(os.path.join(root, "docs/backend/json-schema/models/x.schema.json"), SCHEMA)
    write(os.path.join(root, "aap-server/src/main/java/com/x/Svc.java"), SVC)
    write(os.path.join(root, "aap-server/src/test/java/com/x/T.java"), TEST)
    write(os.path.join(root, "aap-client/src/api/usage.ts"), USAGE_TS)
    write(os.path.join(root, "aap-client/src/pages/usage/index.vue"), USAGE_VUE)
    write(os.path.join(root, "aap-client/src/utils/format.ts"), FMT_TS)


def snapshot(paths):
    state = {}
    for base in paths:
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                p = os.path.join(dirpath, name)
                try:
                    with open(p, "rb") as fh:
                        raw = fh.read()
                    state[p] = (len(raw), hashlib.md5(raw).hexdigest())
                except OSError:
                    state[p] = (None, None)
    return state


def main():
    os.makedirs(FIXROOT, exist_ok=True)
    fx = os.path.join(FIXROOT, "compliant")
    build_fixture(fx)

    # ---------- 1. 合规夹具：rc=0 且 0 FAIL（正向对照全过）
    rc, out = run(fx)
    check("T0 合规夹具 rc=0", rc == 0, "rc=%d" % rc)
    check("T0b 合规夹具 FAIL=0", not mod.FAIL_LINES, str(mod.FAIL_LINES)[:200])
    p_tokens = set(l.split()[1] for l in mod.PASS_LINES if l.startswith("[PASS] P"))
    check("T1 合规夹具正向对照 P1..P7 全部命中",
          {"P1", "P2", "P3", "P4", "P5", "P6", "P7"} <= p_tokens, str(sorted(p_tokens)))

    ok_out = (rc, set(fails_tokens()), list(mod.FAIL_LINES))  # 基线专用名（坑 93）

    # ---------- 2. 空夹具：必须变红且点名「解析失效」，不得空转判绿
    empty = os.path.join(FIXROOT, "empty")
    os.makedirs(empty, exist_ok=True)
    rc_e, _o = run(empty)
    tok_e = fails_tokens()
    check("T2 空夹具 rc=1", rc_e == 1)
    check("T2b 空夹具点名全部正向对照(P1..P7)", {"P1", "P2", "P3", "P4", "P5", "P6", "P7"} <= tok_e,
          str(sorted(tok_e)))
    check("T2c 空夹具点名 A5（防空转）", "A5" in tok_e, str(sorted(tok_e)))

    # ---------- 3. 注入缺陷：每条恰好新增目标断言（锚点必须真的命中）
    injections = [
        ("A1", os.path.join(fx, "aap-server/src/main/java/com/x/Svc.java"),
         [("RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC))", "RFC3339.format(value)")],
         {"A1"}),
        ("A2", os.path.join(fx, "aap-server/src/main/java/com/x/Svc.java"),
         [('private static final DateTimeFormatter RFC3339',
           "private static final String Q = \"date_trunc('day', created_at)\";\n"
           "    private static final DateTimeFormatter RFC3339")],
         {"A2"}),
        ("A3", os.path.join(fx, "docs/backend/02-API接口模型清单.md"),
         [("RFC3339 **UTC**", "RFC3339 约定")],
         {"A3"}),
        ("A5", os.path.join(fx, "aap-client/src/pages/usage/index.vue"),
         [("const month = ref(props.month)", "const month = ref(currentMonth())")],
         {"A5"}),
        ("P5/A4", os.path.join(fx, "aap-server/src/main/java/com/x/Svc.java"),
         [("    public String monthBucketStart(String month) {\n        YearMonth ym = YearMonth.parse(month);\n"
           "        return RFC3339.format(ym.atDay(1).atStartOfDay().atOffset(ZoneOffset.UTC));\n    }\n\n", ""),
          ("        LocalDate firstOfMonth = LocalDate.now(ZoneOffset.UTC).withDayOfMonth(1);\n"
           "        return firstOfMonth.toString();\n", "        return \"\";\n")],
         {"P5", "A4", "A5"}),
    ]
    for tag, path, pairs, expected in injections:
        build_fixture(fx)  # 每个注入都从合规基线重建
        missed = mutate(path, pairs)
        check("T3[%s] 注入锚点全部命中（缺陷真的改到源码）" % tag, not missed, "未命中锚点=%s" % missed)
        rc_i, _o = run(fx)
        added = fails_tokens() - ok_out[1]
        check("T3[%s] 恰好新增目标断言 %s" % (tag, sorted(expected)), added == expected,
              "实际新增=%s（基线 FAIL=%s）" % (sorted(added), sorted(ok_out[1])))
        check("T3[%s] 无断言消失（守卫不滥报）" % tag, ok_out[1] - fails_tokens() == set(),
              "消失=%s" % sorted(ok_out[1] - fails_tokens()))

    # ---------- 4. 真实仓库只读守卫
    build_fixture(fx)  # 还原夹具（不影响仓库）
    before = snapshot([os.path.join(REPO, "docs"), os.path.join(REPO, "tools"),
                       os.path.join(REPO, "aap-server/src"), os.path.join(REPO, "aap-client/src")])
    rc_r, out_r = run(REPO)
    tok_r = fails_tokens()
    check("T4 真实仓库 rc=1（存在已登记的 A5 漂移）", rc_r == 1, "rc=%d" % rc_r)
    check("T4b 真实仓库只报 A5、无正向对照失败", tok_r == {"A5"}, "实际 FAIL=%s" % sorted(tok_r))
    check("T4c 真实仓库解析到出口调用点 > 0", "出口调用点 0 处" not in out_r)
    after = snapshot([os.path.join(REPO, "docs"), os.path.join(REPO, "tools"),
                      os.path.join(REPO, "aap-server/src"), os.path.join(REPO, "aap-client/src")])
    changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
    check("T5 零写副作用（真实仓库文件逐字节未变）", not changed, "变化=%s" % changed[:5])

    print("== R52 抽查负向自测 ==")
    for line in CASE + FAILSELF:
        print(line)
    print("汇总: PASS %d / FAIL %d" % (len(CASE), len(FAILSELF)))
    return 1 if FAILSELF else 0


if __name__ == "__main__":
    sys.exit(main())
