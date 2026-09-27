#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R66 抽查脚本的负向自测：每分支一条反例 + 正向对照 + 空夹具必须变红 + 注入必须真的改到源码 + 零写副作用。

用法：python spotcheck-state-machine-R66-selftest.py
夹具目录与脚本目录**分开命名**（坑 106）：脚本在 aap-r66-spotcheck/，夹具在 aap-r66-spotcheck-fixtures/。
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "spotcheck-state-machine-R66-v2.py"
FX = HERE.parent / "aap-r66-spotcheck-fixtures"
FAILS = []


def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print("[%s] %s %s" % (tag, name, detail))
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------- 夹具内容
ERRORCODE = """package com.hioas.aap.common;

public enum ErrorCode {
    E_1001("E-1001", 400, "参数校验失败"),
    E_1601("E-1601", 409, "状态非法流转"),
    ;
    ErrorCode(String code, int httpStatus, String message) { }
}
"""

DEMO = """package com.hioas.aap.demo;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import java.util.Set;

public class DemoService {

    private static final Set<String> OPENABLE = Set.of("OPEN");

    private static final String VERIFY_SQL = \"\"\"
            update aap_demo
               set status = 'VERIFIED'
             where id = ? and status = 'OPEN' and deleted = false
            \"\"\";

    /** DEMO-01 流转：OPEN → DONE。 */
    public void finish(long id) {
        DemoEntity row = require(id);
        if (!OPENABLE.contains(row.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "当前状态不可完成");
        }
        row.setStatus("DONE");
        demoMapper.update(row);
    }

    /** 创建：初始状态 OPEN。 */
    public DemoEntity create(String name) {
        DemoEntity entity = new DemoEntity();
        entity.setName(name);
        entity.setStatus("OPEN");
        demoMapper.insert(entity);
        return entity;
    }

    /** 常量引用 SQL 的流转 OPEN → VERIFIED。 */
    public int verify(long id) {
        return jdbc.update(VERIFY_SQL, id);
    }

    /** 关联实体守卫（自述 from 集合与守卫一致）：OPEN → DONE。 */
    public void approve(long taskId) {
        TaskEntity task = requireTask(taskId);
        if (!OPENABLE.contains(task.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "审核任务已出结论");
        }
        if (jdbc.update(APPROVE_SQL, taskId) != 1) {
            throw new ApiException(ErrorCode.E_1601, "状态已变化");
        }
        DemoEntity demo = require(task.getDemoId());
        demo.setStatus("DONE");
        if (demoMapper.update(demo) != 1) {
            throw new ApiException(ErrorCode.E_1601, "演示对象状态已变化");
        }
    }

    /** 姊妹列守卫：gate_status OPEN → DONE。 */
    public void confirmGate(long id) {
        DemoEntity entity = require(id);
        if (!"OPEN".equals(entity.getGateStatus())) {
            throw new ApiException(ErrorCode.E_1601, "闸门状态非法");
        }
        entity.setGateStatus("DONE");
        entity.setStatus("DONE");
        demoMapper.update(entity);
    }

    /** 仅乐观锁守卫（可接受，记 INFO）。 */
    public void rotate(long id, String ifMatch) {
        DemoEntity entity = require(id);
        if (ifMatch != null && !ifMatch.equals(String.valueOf(entity.getVersion()))) {
            throw new ApiException(ErrorCode.E_1601, "已被更新，请刷新");
        }
        entity.setStatus("OPEN");
        demoMapper.update(entity);
    }

    /** 带守卫的字面量 SQL：OPEN → DONE。 */
    public int close(long id) {
        return jdbc.update(\"\"\"
                update aap_demo
                   set status = 'DONE', updated_at = now()
                 where id = ? and status = 'OPEN' and deleted = false
                \"\"\", id);
    }
}
"""

DEMO_EXTRA_SIBLING = """
    /** 姊妹列守卫副本 2（用于注入「豁免超限」缺陷）。 */
    public void confirmGate2(long id) {
        DemoEntity entity = require(id);
        if (!"OPEN".equals(entity.getGateStatus())) {
            throw new ApiException(ErrorCode.E_1601, "闸门状态非法");
        }
        entity.setStatus("DONE");
        demoMapper.update(entity);
    }

    /** 姊妹列守卫副本 3（用于注入「豁免超限」缺陷）。 */
    public void confirmGate3(long id) {
        DemoEntity entity = require(id);
        if (!"OPEN".equals(entity.getGateStatus())) {
            throw new ApiException(ErrorCode.E_1601, "闸门状态非法");
        }
        entity.setStatus("DONE");
        demoMapper.update(entity);
    }
}
"""

MD = """# 接口清单（夹具）

## 3. 供应商端

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEMO-00 | GET | `/demo` | ✅ | — | `Demo` | | | 真源 | T01 |

## 6. 管理端

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| DEMO-01 | POST | `/admin/demo/{id}/finish` | TECH_OPS | → `Demo`（OPEN→DONE） | E-1601 | T01 |
| DEMO-02 | POST | `/admin/demo/{id}/verify` | TECH_OPS | → `Demo` | E-1601 | T01 |

## 4. 错误码表

| 码 | HTTP | 描述 | 依据 |
| --- | --- | --- | --- |
| `E-1001` | 400 | 参数校验失败 | spec §9 |
| `E-1601` | 409 | 状态非法流转 | spec §4 |
"""

SPEC = """# 零歧义执行规格spec

## 4. 状态机定义（全部枚举与合法流转）

DemoStatus：OPEN/DONE/VERIFIED。任何不在合法流转表内的变更拒绝 E-1601。
GateStatus：OPEN/DONE。

## 9. 错误码表

E-1001 参数校验；E-1601 状态非法流转。
"""

ER = """# ER 数据模型（夹具）

| 表 | status 取值 |
| --- | --- |
| aap_demo | OPEN/DONE/VERIFIED |
"""

TEST = """package com.hioas.aap.demo;

class DemoContractTest {
    void finishRejected() {
        assertThat(rejected.status()).as(rejected.body()).isEqualTo(409);
        assertThat(body(rejected).path("code").asText()).isEqualTo("E-1601");
    }
}
"""


def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def build(root, extra=""):
    write(root / "src/com/hioas/aap/common/ErrorCode.java", ERRORCODE)
    write(root / "src/com/hioas/aap/demo/DemoService.java", DEMO.replace("}\n", extra + "}\n") if extra else DEMO)
    write(root / "tests/com/hioas/aap/demo/DemoContractTest.java", TEST)
    write(root / "docs/md.md", MD)
    write(root / "docs/spec.md", SPEC)
    write(root / "docs/er.md", ER)


def run_audit(root):
    p = subprocess.run([sys.executable, str(AUDIT), "--root", str(root),
                        "--src", str(root / "src"), "--tests-dir", str(root / "tests"),
                        "--md", str(root / "docs/md.md"), "--spec", str(root / "docs/spec.md"),
                        "--er", str(root / "docs/er.md")],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def run_audit_root(root):
    """真实仓库：只传 --root，用仓库自身默认路径（夹具布局不适用）。"""
    p = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def fails(out):
    """FAIL 明细的断言 token（取 split()[1]，坑 112-③：split()[0] 是 '[FAIL]'）。"""
    return [ln.split()[1] for ln in out.splitlines() if ln.startswith("[FAIL]")]


def passes(out):
    return [ln.split()[1] for ln in out.splitlines() if ln.startswith("[PASS]")]


def manifest(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            out[str(p.relative_to(root))] = (len(b), hashlib.md5(b).hexdigest())
    return out


def mutate(root, rel, old, new, count=None):
    """返回未命中锚点列表；count=None 表示全部替换（坑 90/94/104）。"""
    p = root / rel
    t = p.read_text(encoding="utf-8")
    if old not in t:
        return [old]
    t2 = t.replace(old, new) if count is None else t.replace(old, new, count)
    if t2 == t:
        return [old]
    p.write_text(t2, encoding="utf-8", newline="\n")
    return []


# --------------------------------------------------------------------------- 自测主体
def main():
    if not AUDIT.exists():
        print("找不到被测脚本 %s" % AUDIT)
        return 2
    # 夹具目录清空（与脚本目录分开命名，坑 106）
    if FX.exists():
        for p in sorted(FX.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
    FX.mkdir(parents=True, exist_ok=True)

    base = FX / "compliant"
    build(base)
    rc0, out0 = run_audit(base)
    print("== 合规夹具 ==")
    print(out0)
    ok_fails = fails(out0)
    check("C1 合规夹具 FAIL 明细为空（rc=0）", rc0 == 0 and ok_fails == [],
          "rc=%d FAIL=%s" % (rc0, ok_fails))
    a0 = [a for a in passes(out0) if a.startswith("A0")]
    check("C2 合规夹具 8 条正向对照全 PASS", len(a0) == 8, "PASS=%s" % a0)
    check("C3 合规夹具 A2 无「无守卫」流转点", "A2" in passes(out0), "A2 未 PASS")

    # ---------------- 注入缺陷（每条都要「真的改到源码」）
    cases = [
        ("inj-sql-drop-guard", "src/com/hioas/aap/demo/DemoService.java",
         "where id = ? and status = 'OPEN' and deleted = false",
         "where id = ? and deleted = false", 1, "A1"),
        ("inj-orm-drop-guard", "src/com/hioas/aap/demo/DemoService.java",
         """        if (!OPENABLE.contains(row.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "当前状态不可完成");
        }
""", "", None, "A2"),
        ("inj-md-wrong-from", "docs/md.md", "（OPEN→DONE）", "（CLOSED→DONE）", None, "A3"),
        ("inj-impl-drop-throw", "src/com/hioas/aap/demo/DemoService.java",
         "ErrorCode.E_1601", "ErrorCode.E_1001", None, "A4"),
        ("inj-unknown-status", "src/com/hioas/aap/demo/DemoService.java",
         'setStatus("OPEN")', 'setStatus("BOGUS")', None, "A5"),
        ("inj-selfdecl-mismatch", "src/com/hioas/aap/demo/DemoService.java",
         "/** 带守卫的字面量 SQL：OPEN → DONE。 */",
         "/** 带守卫的字面量 SQL：CLOSED|OPEN → DONE。 */", None, "A3b"),
    ]
    for (name, rel, old, new, cnt, expect) in cases:
        root = FX / name
        build(root)
        missed = mutate(root, rel, old, new, cnt)
        check("I-%s 注入锚点命中" % name, missed == [], "未命中=%s" % missed)
        rc, out = run_audit(root)
        newf = set(fails(out)) - set(ok_fails)
        if expect == "A1":
            # 同源连带：去掉 VERIFIED 语句的守卫后，A3b（自述 `OPEN → VERIFIED`）必然同时点名
            # → 判据写成「必须包含 A1 且不越界」，并写明连带理由（坑 82/93/136）
            check("I-%s 恰好新增 %s（同源连带 A3b；rc!=0）" % (name, expect),
                  "A1" in newf and newf <= {"A1", "A3b"} and rc != 0,
                  "新增=%s rc=%d" % (sorted(newf), rc))
        else:
            check("I-%s 恰好新增 %s（且 rc!=0）" % (name, expect),
                  newf == {expect} and rc != 0, "新增=%s rc=%d" % (sorted(newf), rc))

    # 豁免超限：姊妹列守卫 3 个（上限 2）→ A2d 必须转红
    root = FX / "inj-weak-cap"
    build(root, extra=DEMO_EXTRA_SIBLING)
    rc, out = run_audit(root)
    newf = set(fails(out)) - set(ok_fails)
    check("I-inj-weak-cap 姊妹列豁免超限 → 恰好新增 A2d", newf == {"A2d"}, "新增=%s rc=%d" % (sorted(newf), rc))

    # ---------------- 空夹具必须变红并点名全部 A0*
    empty = FX / "empty"
    empty.mkdir(parents=True, exist_ok=True)
    rc_e, out_e = run_audit(empty)
    ef = set(fails(out_e))
    want = {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h"}
    check("E1 空夹具 rc!=0 且点名全部 8 条 A0*", rc_e != 0 and want <= ef, "rc=%d 缺失=%s" % (rc_e, sorted(want - ef)))
    check("E2 空夹具不得出现 PASS 的 A0*", not [a for a in passes(out_e) if a.startswith("A0")],
          "PASS=%s" % [a for a in passes(out_e) if a.startswith("A0")])

    # ---------------- 零写副作用（含不得留下 __pycache__）
    before = manifest(base)
    rc2, _ = run_audit(base)
    after = manifest(base)
    check("Z1 审计对夹具目录零写副作用", before == after,
          "差异=%s" % [k for k in set(before) | set(after) if before.get(k) != after.get(k)])
    check("Z2 夹具目录无 __pycache__", not list(base.rglob("__pycache__")), "")

    # ---------------- 真实仓库只读守卫（FAIL 集合与「只跑一次」一致）
    real = Path("E:/workspaces/hioas/hioas-aap-001")
    if (real / "docs/backend/02-API接口模型清单.md").exists():
        rc_a, out_a = run_audit_root(real)
        rc_b, out_b = run_audit_root(real)
        check("R1 真实仓库两次运行 FAIL 明细一致（只读、无状态）",
              fails(out_a) == fails(out_b) and rc_a == rc_b,
              "rc=%d/%d FAIL=%s" % (rc_a, rc_b, sorted(set(fails(out_a)) ^ set(fails(out_b)))))
        check("R2 真实仓库解析到 FAIL 行数 > 0（正向对照，坑 46/98）", len(fails(out_a)) > 0,
              "FAIL=%s" % fails(out_a))
        check("R3 真实仓库 A0* 全 PASS（解析器有效）",
              len([a for a in passes(out_a) if a.startswith("A0")]) == 8,
              "PASS=%s" % [a for a in passes(out_a) if a.startswith("A0")])

    print("")
    print("== 自测汇总：%s（FAIL %d） ==" % ("全部通过" if not FAILS else "存在失败", len(FAILS)))
    if FAILS:
        print("失败项：%s" % FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
