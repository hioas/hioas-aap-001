#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R60 抽查的**负向自测**：夹具 + 注入缺陷 + 正向对照 + 零写副作用（坑 46/66/75/82/93/98/104/128）。

用法：python spotcheck-string-length-R60-selftest.py [审计脚本路径] [夹具根]
  ① 合规夹具 → rc=0 且 FAIL 0（正向对照：A0a…A0g 全 PASS）；
  ② 空夹具 → rc=1 且点名 A0a…A0g（解析器失效必须可见）；
  ③ 6 组注入缺陷 → FAIL 集合**恰好新增**目标断言（先跑基线再比集合，坑 82/93）；
     每组都断言「注入真的改到了源码」（锚点未命中 = 空转通过，坑 66/90/94）；
  ④ 真实仓库只读：FAIL 断言集合 = 3 类已人工回查的漂移（A3b/A3c/A5b），9 条明细，关键文件 md5 不变；
  ⑤ 夹具目录零写副作用。

夹具设计要点（避免「注入顺带打红正向对照」造成的假失败，坑 82）：
  每个**正向对照**都有第二个来源兜底 —— 第 2 个 @Size(min=…)（captcha）、第 2 个 @NotBlank（base_url），
  于是「删掉 title 的注解」「删掉 code 的 @NotBlank」时 A0c / A0f 仍为 PASS，注入只影响被测判据。
  每个被测字段的证据来源**唯一**：title=注解 / note=注解 / remark=仅服务层形参检查 / code=@NotBlank。
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

AUDIT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("spotcheck-string-length-R60-v6.py")
FIX = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
    r"C:/Users/laitz/AppData/Local/Temp/aap-r60-spotcheck-fixtures")
REAL = "E:/workspaces/hioas/hioas-aap-001"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("[%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def run(root):
    p = subprocess.run([sys.executable, str(AUDIT), str(root)], capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout + p.stderr


def fails_of(out):
    tags = []
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("[FAIL]") and "汇总" not in s:
            parts = s.split()
            if len(parts) > 1:
                tags.append(parts[1])
    return set(tags)


def md5dir(base):
    return {str(p.relative_to(base)): hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(Path(base).rglob("*")) if p.is_file()}


DDL = """-- fixture
create table if not exists aap_demo (
    id              bigint primary key,
    title           varchar(64) not null,
    note            varchar(128),
    remark          varchar(200),
    tag             text
);
"""
CTRL = """package com.hioas.aap.demo;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class DemoController {
    public record DemoRequest(
            @Size(min = 2, max = 64, message = "标题 2-64 字") String title,
            @Size(max = 128, message = "备注最多 128 字") String note,
            String remark,
            @NotBlank(message = "缺少 code") String code,
            @NotBlank(message = "缺少 base_url") String base_url,
            @Size(min = 1, max = 8, message = "图形验证码长度不正确") String captcha) {
    }
}
"""
SVC = """package com.hioas.aap.demo;

public class DemoService {
    private static final int MAX_REMARK_LENGTH = 200;

    private static void validateRemark(String remark) {
        if (remark != null && remark.length() > MAX_REMARK_LENGTH) {
            throw new IllegalStateException("remark too long");
        }
    }
}
"""
TEST = """package com.hioas.aap.demo;

public class DemoContractTest {
    void overlong() {
        String s = "x".repeat(65);
    }
}
"""
REQ = """{
  "title": "demo-create",
  "properties": {
    "title": { "type": "string", "minLength": 2, "maxLength": 64 },
    "note": { "type": ["string", "null"], "maxLength": 128 },
    "remark": { "type": ["string", "null"], "maxLength": 200 },
    "code": { "type": "string", "minLength": 1 }
  },
  "type": "object"
}
"""
MODEL = """{
  "title": "demo",
  "properties": { "id": { "type": "string" } },
  "type": "object"
}
"""
EP = """{
  "total": 1,
  "endpoints": [
    { "id": "DEMO-01", "method": "POST", "path": "/api/v1/demos", "request_model": "demo-create" }
  ]
}
"""
MD = "# 清单（夹具）\n"


def build_fixture(root):
    root = Path(root)
    if root.exists():
        shutil.rmtree(root)
    (root / "aap-server/src/main/resources/db/migration").mkdir(parents=True)
    (root / "aap-server/src/main/java/com/hioas/aap/demo").mkdir(parents=True)
    (root / "aap-server/src/test/java/com/hioas/aap/demo").mkdir(parents=True)
    (root / "docs/backend/json-schema/requests").mkdir(parents=True)
    (root / "docs/backend/json-schema/models").mkdir(parents=True)
    (root / "aap-server/src/main/resources/db/migration/V1__baseline.sql").write_text(DDL, encoding="utf-8")
    (root / "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java").write_text(CTRL, encoding="utf-8")
    (root / "aap-server/src/main/java/com/hioas/aap/demo/DemoService.java").write_text(SVC, encoding="utf-8")
    (root / "aap-server/src/test/java/com/hioas/aap/demo/DemoContractTest.java").write_text(TEST, encoding="utf-8")
    (root / "docs/backend/json-schema/requests/demo-create.schema.json").write_text(REQ, encoding="utf-8")
    (root / "docs/backend/json-schema/models/demo.schema.json").write_text(MODEL, encoding="utf-8")
    (root / "docs/backend/endpoints.json").write_text(EP, encoding="utf-8")
    (root / "docs/backend/02-API接口模型清单.md").write_text(MD, encoding="utf-8")
    return root


def mutate(root, rel, pairs):
    p = Path(root) / rel
    s = p.read_text(encoding="utf-8")
    missed = []
    for old, new in pairs:
        if old not in s:
            missed.append(old)
            continue
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    return missed


def main():
    # ---------- ① 合规夹具
    build_fixture(FIX)
    before = md5dir(FIX)
    rc, out = run(FIX)
    f = fails_of(out)
    n_a0 = len([1 for line in out.splitlines() if line.startswith("[PASS] A0")])
    check("S1 合规夹具 rc=0", rc == 0, "rc=%d" % rc)
    check("S2 合规夹具 FAIL 0", not f, "FAIL=%s" % sorted(f))
    check("S3 合规夹具正向对照 A0a…A0g 全 PASS", n_a0 >= 7, "A0 正向对照=%d 条" % n_a0)
    check("S4 合规夹具解析到 DDL/schema/实现/端点/测试",
          "DDL: 1 表 / 3 varchar 列" in out and "测试: 1 处" in out,
          [l for l in out.splitlines() if l.startswith("DDL:") or l.startswith("测试:")])
    check("S5 夹具零写副作用", md5dir(FIX) == before)
    baseline = f

    # ---------- ② 空夹具
    empty = build_fixture(FIX.with_name(FIX.name + "-empty"))
    for p in list(empty.rglob("*")):
        if p.is_file():
            p.unlink()
    rc_e, out_e = run(empty)
    fe = fails_of(out_e)
    need = {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"}
    check("S6 空夹具 rc=1 且点名全部解析器正向对照", rc_e == 1 and need <= fe,
          "rc=%d 缺失=%s" % (rc_e, sorted(need - fe)))

    # ---------- ③ 注入缺陷
    inj = [
        ("S7 注入①schema maxLength 64→999（越界放行）",
         "docs/backend/json-schema/requests/demo-create.schema.json",
         [('"minLength": 2, "maxLength": 64', '"minLength": 2, "maxLength": 999')],
         {"A2", "A3b"}),
        ("S8 注入②DDL varchar(64)→varchar(32)（库比声明更窄）",
         "aap-server/src/main/resources/db/migration/V1__baseline.sql",
         [("title           varchar(64) not null", "title           varchar(32) not null")],
         {"A2", "A4"}),
        ("S9 注入③删掉 title 的 @Size(min=2,max=64)（上限+下限同时失控）",
         "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java",
         [('@Size(min = 2, max = 64, message = "标题 2-64 字") String title,', "String title,")],
         {"A3b", "A5b"}),
        ("S10 注入④@Size(max=64)→@Size(max=999)（实现放行、库拒绝）",
         "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java",
         [("@Size(min = 2, max = 64,", "@Size(min = 2, max = 999,")],
         {"A3b", "A4"}),
        ("S11 注入⑤remark 的**唯一**证据（服务层形参 length()）上限 200→999",
         "aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
         [("MAX_REMARK_LENGTH = 200", "MAX_REMARK_LENGTH = 999")],
         {"A3b"}),
        ("S12 注入⑥删掉 code 的 @NotBlank（minLength=1 失控）",
         "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java",
         [('@NotBlank(message = "缺少 code") String code,', "String code,")],
         {"A5b"}),
    ]
    for name, rel, pairs, expect in inj:
        build_fixture(FIX)
        missed = mutate(FIX, rel, pairs)
        check(name + " · 锚点全部命中", not missed, "未命中=%s" % missed)
        rc_i, out_i = run(FIX)
        fi = fails_of(out_i)
        check(name + " · 恰好新增目标断言", (fi - baseline) == expect and (baseline - fi) == set(),
              "新增=%s 期望=%s 消失=%s" % (sorted(fi - baseline), sorted(expect), sorted(baseline - fi)))
        check(name + " · rc=1", rc_i == 1, "rc=%d" % rc_i)

    # ---------- ④ 真实仓库只读 + 结论
    real_files = [Path(REAL) / "aap-server/src/main/resources/db/migration/V1__baseline.sql",
                  Path(REAL) / "docs/backend/json-schema/requests/qualification-create.schema.json",
                  Path(REAL) / "docs/backend/json-schema/requests/review-approve.schema.json",
                  Path(REAL) / "docs/backend/endpoints.json"]
    h_before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in real_files}
    rc_r, out_r = run(REAL)
    fr = fails_of(out_r)
    h_after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in real_files}
    expect_real = {"A3b", "A3c", "A5b"}
    check("S13 真实仓库 FAIL 断言集合 = 已人工回查的 3 类", fr == expect_real,
          "实际=%s 期望=%s" % (sorted(fr), sorted(expect_real)))
    check("S14 真实仓库 rc=1", rc_r == 1, "rc=%d" % rc_r)
    check("S15 真实仓库只读（关键文件 md5 不变）", h_before == h_after)
    check("S16 真实仓库 FAIL 明细 9 条", len([1 for line in out_r.splitlines() if line.startswith("[FAIL]")]) == 9,
          "FAIL 明细=%d" % len([1 for line in out_r.splitlines() if line.startswith("[FAIL]")]))

    bad = [n for n, ok, _d in results if not ok]
    print()
    print("自测汇总：%d/%d PASS" % (len(results) - len(bad), len(results)))
    if bad:
        print("失败项：%s" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
