#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R56 抽查的负向自测（判别力对照）—— spotcheck-paging.py。

纪律（每条对应一次真实返工）：
  * 基线变量另起名 ok_out（坑 93：基线被覆盖会让「恰好新增」恒为空）；
  * FAIL 集合按**断言前缀**（A1/A2/A7…）比对，不拿整行文本当键（坑 82/93）；
  * 注入必须**真的改到源码**（replace 命中数断言，坑 66/94），注入值不得与旧值互为子串（坑 90）；
  * 合规夹具必须 rc=0 且 FAIL 0（正向对照，坑 46/75）；空夹具必须变红并点名解析器失效（坑 75/98）；
  * 零写副作用：真实仓库关键文件 md5 全等（坑 39）。
夹具目录与脚本目录**分开**（坑 106）。
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "spotcheck-paging.py")
FIX = os.path.join(os.path.dirname(HERE), "aap-r56-spotcheck-fixtures")
REAL = r"E:/workspaces/hioas/hioas-aap-001"
PY = sys.executable
FAIL_LINE = re.compile(r"^\s*\[FAIL\s*\]\s*([A-Za-z0-9]+):")
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + str(detail)) if detail else ""))
    return bool(ok)


def run(root):
    p = subprocess.run([PY, AUDIT, "--root", root], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    fails = [m.group(1) for ln in out.splitlines() for m in [FAIL_LINE.match(ln)] if m]
    return p.returncode, out, fails


# --------------------------------------------------------------- 夹具构造
MD = """# API 接口模型清单（夹具）

## §0 通用约定

| 约定 | 说明 |
|---|---|
| 分页 | 请求 `page`（默认 1）/ `pageSize`（默认 20，上限 200）；响应 `data:{items:[],page,pageSize,total}` |

| ID | 方法 | 路径 | 认证 | 请求 | 响应 | 错误码 | 来源 | 任务号 |
|---|---|---|---|---|---|---|---|---|
| AAA-01 | GET | `/aaas` | ✅ | q：`page` `pageSize` | `{items:[A],page,pageSize,total}` | | 真源 | T99 |
"""

PAGEQUERY = """package com.hioas.aap.common;

/** 分页请求参数（默认 20、上限 200；非法值一律夹取而不是抛错——列表页容忍脏参数）。 */
public record PageQuery(int page, int pageSize) {

    public static final int DEFAULT_PAGE_SIZE = 20;
    public static final int MAX_PAGE_SIZE = 200;

    public static PageQuery of(Integer page, Integer pageSize) {
        int p = page == null || page < 1 ? 1 : page;
        int size = pageSize == null || pageSize < 1 ? DEFAULT_PAGE_SIZE : Math.min(pageSize, MAX_PAGE_SIZE);
        return new PageQuery(p, size);
    }

    public int offset() {
        return (page - 1) * pageSize;
    }
}
"""

CONTROLLER = """package com.hioas.aap.demo;

import com.hioas.aap.common.PageQuery;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

@RequestMapping("/api/v1/aaas")
public class DemoController {

    @GetMapping
    public Object list(@RequestParam(required = false) Integer page,
                       @RequestParam(required = false) Integer pageSize) {
        PageQuery q = PageQuery.of(page, pageSize);
        return q;
    }
}
"""

SERVICE = """package com.hioas.aap.demo;

import org.springframework.jdbc.core.JdbcTemplate;

public class DemoService {
    private final JdbcTemplate jdbc;

    public DemoService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Object page(int page, int pageSize) {
        return jdbc.query("select id from aap_demo order by id limit ? offset ?",
                (rs, i) -> rs.getLong(1), pageSize, (page - 1) * pageSize);
    }

    public Object one() {
        return jdbc.query("select id from aap_demo where id = ? limit 1",
                (rs, i) -> rs.getLong(1), 1L);
    }
}
"""

TEST_JAVA = """package com.hioas.aap.demo;

import org.junit.jupiter.api.Test;

class DemoContractTest {

    @Test
    void listClamped() {
        HttpResult clamped = get("/aaas?page=0&pageSize=1000", token);
        assertThat(clamped.data().path("pageSize").asInt()).isEqualTo(200);
    }
}
"""

CLIENT_TS = """export const PAGE_SIZE = 20
export async function list(params?: { page?: number; pageSize?: number }) {
  const data: Record<string, unknown> = { page: params?.page, pageSize: params?.pageSize }
  return http('/aaas', { data })
}

export async function firstPage() {
  return http('/aaas', { data: { page: 1, pageSize: 20 } })
}
"""

SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "page",
  "required": ["items", "page", "pageSize", "total"],
  "properties": {
    "items": { "type": "array" },
    "page": { "type": "integer", "minimum": 1 },
    "pageSize": { "type": "integer", "minimum": 1, "maximum": 200 },
    "total": { "type": "integer", "minimum": 0 }
  },
  "type": "object",
  "additionalProperties": true
}
"""


def openapi(maximum=True, default=True):
    def blk(name, extra):
        lines = [f"        - name: {name}", "          in: query", "          required: false",
                 "          schema:", "            type: integer", "            minimum: 1"]
        lines += extra
        return "\n".join(lines)

    mx = ["            maximum: 200"] if maximum else []
    df_s = ["            default: 20"] if default else []
    df_p = ["            default: 1"] if default else []
    return ("openapi: 3.0.3\npaths:\n  /aaas:\n    get:\n      parameters:\n"
            + blk("page", df_p) + "\n" + blk("pageSize", mx + df_s) + "\n      responses:\n        200:\n"
            "          description: 成功\n")


def build(root, maximum=True, default=True):
    if os.path.isdir(root):
        shutil.rmtree(root)
    files = {
        "docs/backend/02-API接口模型清单.md": MD,
        "docs/backend/openapi.yaml": openapi(maximum, default),
        "docs/backend/json-schema/common/page.schema.json": SCHEMA,
        "aap-server/src/main/java/com/hioas/aap/common/PageQuery.java": PAGEQUERY,
        "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java": CONTROLLER,
        "aap-server/src/main/java/com/hioas/aap/demo/DemoService.java": SERVICE,
        "aap-server/src/test/java/com/hioas/aap/demo/DemoContractTest.java": TEST_JAVA,
        "aap-client/src/api/demo.ts": CLIENT_TS,
    }
    for rel, txt in files.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
    return files


def mutate(src_root, dst_root, edits):
    """edits: list of (relpath, old, new, expect_hits)。返回未命中列表。"""
    build(dst_root)
    missed = []
    for rel, old, new, expect in edits:
        p = os.path.join(dst_root, *rel.split("/"))
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        n = txt.count(old)
        if n != expect:
            missed.append(f"{rel}: 命中 {n} 次（期望 {expect}）：{old[:40]}")
        txt = txt.replace(old, new)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)
    return missed


def md5_key_files(root):
    keys = ["docs/backend/openapi.yaml", "docs/backend/json-schema/common/page.schema.json",
            "aap-server/src/main/java/com/hioas/aap/common/PageQuery.java",
            "docs/backend/02-API接口模型清单.md"]
    out = {}
    for k in keys:
        p = os.path.join(root, *k.split("/"))
        with open(p, "rb") as fh:
            out[k] = hashlib.md5(fh.read()).hexdigest()
    return out


def main():
    ok_root = os.path.join(FIX, "ok")
    build(ok_root)
    rc, out, fails = run(ok_root)
    ok_out = out
    ok_fails = list(fails)
    check("T1 合规夹具 rc=0 且 FAIL 0（正向对照）", rc == 0 and not ok_fails, f"rc={rc} fails={ok_fails}")
    check("T1b 合规夹具解析到全部源（A0a…A0h 全 PASS）",
          all(f"A0{c}" in ok_out for c in "abcdefgh") and ok_out.count("[PASS] A0") == 8)

    empty = os.path.join(FIX, "empty")
    if os.path.isdir(empty):
        shutil.rmtree(empty)
    os.makedirs(empty)
    rc_e, out_e, fails_e = run(empty)
    check("T2 空夹具必须变红且点名解析器失效（A0a/A0b/A0c/A0d/A0e/A0f/A0g）",
          rc_e == 1 and {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"} <= set(fails_e),
          f"rc={rc_e} fails={sorted(set(fails_e))}")

    cases = [
        ("T3 注入：实现上限 200→500（A2 转红）",
         [("aap-server/src/main/java/com/hioas/aap/common/PageQuery.java",
           "MAX_PAGE_SIZE = 200", "MAX_PAGE_SIZE = 500", 1)], {"A2"}),
        ("T4 注入：契约 schema 上限 200→100（A3 转红）",
         [("docs/backend/json-schema/common/page.schema.json",
           '"maximum": 200', '"maximum": 100', 1)], {"A3"}),
        ("T5 注入：md §0 缺省 20→10（A1 转红）",
         [("docs/backend/02-API接口模型清单.md", "`pageSize`（默认 20，上限 200）",
           "`pageSize`（默认 10，上限 200）", 1)], {"A1"}),
        ("T6 注入：openapi 去掉 pageSize 上限（A4 转红）",
         [("docs/backend/openapi.yaml", "            maximum: 200\n", "", 1)], {"A4"}),
        ("T7 注入：客户端传 pageSize 500（A8 转红）",
         [("aap-client/src/api/demo.ts", "pageSize: params?.pageSize", "pageSize: 500", 1)], {"A8"}),
        ("T8 注入：手写分页 limit 50 offset 0（A7 转红）",
         [("aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
           "select id from aap_demo where id = ? limit 1",
           "select id from aap_demo where id = ? limit 50 offset 0", 1)], {"A7"}),
        ("T9 注入：删掉越界用例（A0f 转红）",
         [("aap-server/src/test/java/com/hioas/aap/demo/DemoContractTest.java",
           'page=0&pageSize=1000', 'page=1&pageSize=20', 1)], {"A0f"}),
        ("T10 注入：夹取改成抛错（A2b 转红）",
         [("aap-server/src/main/java/com/hioas/aap/common/PageQuery.java",
           "Math.min(pageSize, MAX_PAGE_SIZE)",
           "throw new IllegalArgumentException() == null ? 0 : 0", 1)], {"A2b"}),
    ]
    for title, edits, expect in cases:
        dst = os.path.join(FIX, "inj-" + re.sub(r"\W+", "-", title.split("：")[1])[:24])
        missed = mutate(ok_root, dst, edits)
        if not check(title + " —— 注入锚点全部命中（坑 66/94）", not missed, missed):
            continue
        rc_i, out_i, fails_i = run(dst)
        new = sorted(set(fails_i) - set(ok_fails))
        check(title + " —— 恰好新增目标断言", expect <= set(new) and rc_i == 1,
              f"新增={new}（期望含 {sorted(expect)}）")

    # 缺省值缺失夹具：合规但 openapi 无 default → A5/A5b 转红（与 A4 分开判别）
    dst = os.path.join(FIX, "inj-no-default")
    mutate(ok_root, dst, [])
    p = os.path.join(dst, "docs", "backend", "openapi.yaml")
    with open(p, encoding="utf-8") as fh:
        t = fh.read()
    n = t.count("            default: ")
    t = re.sub(r"^ +default: \d+\n", "", t, flags=re.M)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)
    check("T11 注入：openapi 去掉 default（锚点命中）", n == 2, f"命中 {n} 处")
    rc_i, out_i, fails_i = run(dst)
    new = sorted(set(fails_i) - set(ok_fails))
    check("T11 注入：openapi 去掉 default → A5/A5b 转红", {"A5", "A5b"} <= set(new), f"新增={new}")

    # 真实仓库只读守卫
    before = md5_key_files(REAL)
    rc_r, out_r, fails_r = run(REAL)
    after = md5_key_files(REAL)
    check("T12 真实仓库跑一遍：只读（4 个关键文件 md5 全等）", before == after,
          f"rc={rc_r}（真实仓库 rc=1 是预期的：存在已登记待拍板漂移）")
    check("T12b 真实仓库 FAIL 集合恰好 = {A4,A5,A5b}（其余全绿）",
          sorted(set(fails_r)) == ["A4", "A5", "A5b"], f"fails={sorted(set(fails_r))}")

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"\n自测 {len(RESULTS)} 条：PASS {n_pass}，FAIL {len(RESULTS) - n_pass}")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
