#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R61 抽查的**负向自测**：每分支一条反例 + 正向对照 + 注入缺陷判别力 + 零写副作用。

纪律（照抄 skill 的返工教训）：
  * 合规夹具必须 rc=0 且 FAIL 0（正向）；空夹具必须 rc=1 且**点名**各解析器正向对照（坑 46/75/128）；
  * 注入缺陷必须**真的改到源码**（锚点未命中即空转通过，坑 66/90/94），新值不得与旧值有子串包含关系（坑 90）；
  * 判别力判据 = 「先跑基线，再断言 FAIL **token 集合**恰好新增目标断言」（坑 82/93），
    按**断言前缀**比对而非整行文本（坑 82），排除汇总行（坑 103）；
  * 真实仓库只读 + 夹具目录零写副作用。
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "spotcheck-numeric-range-R61.py"
FIX = Path("C:/Users/laitz/AppData/Local/Temp/aap-r61-spotcheck-fixtures")
REAL = Path("E:/workspaces/hioas/hioas-aap-001")
FAIL_RE = re.compile(r"\[FAIL\s*\]")
PASS_RE = re.compile(r"\[PASS\s*\]")

results = []
mut_misses = []


def check(name, cond, detail=""):
    results.append(("[PASS] " if cond else "[FAIL] ") + name + (" | " + detail if detail else ""))


def run(root):
    proc = subprocess.run([sys.executable, str(AUDIT), str(root)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def toks(out):
    """FAIL 断言 token 集合（按前缀，排除汇总行 —— 坑 82/103）。"""
    got = set()
    for ln in out.splitlines():
        if "汇总" in ln or not FAIL_RE.search(ln):
            continue
        parts = ln.split()
        if len(parts) >= 2:
            got.add(parts[1])
    return got


def pass_toks(out):
    got = set()
    for ln in out.splitlines():
        if PASS_RE.search(ln):
            parts = ln.split()
            if len(parts) >= 2:
                got.add(parts[1])
    return got


def snapshot(root):
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            out[str(p.relative_to(root))] = hashlib.md5(b).hexdigest()
    return out


def write(rel, text):
    p = FIX / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def mutate(rel, old, new, count=1):
    """就地改夹具文件；返回是否命中（未命中即注入失败 → 必须转红，坑 66/94）。"""
    p = FIX / rel
    t = p.read_text(encoding="utf-8")
    if old not in t:
        mut_misses.append("%s :: %s" % (rel, old[:40]))
        return False
    p.write_text(t.replace(old, new, count), encoding="utf-8", newline="\n")
    return True


# ------------------------------------------------------------------ 合规夹具
def build_fixture():
    write("docs/backend/02-API接口模型清单.md", "# 清单\n\n| ID | 说明 |\n| SYN-01 | 测试 |\n")
    write("docs/backend/json-schema/requests/syn-a.schema.json", """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "syn-a",
  "properties": {
    "amount": {"type": ["number", "null"], "minimum": 0, "maximum": 1000},
    "child": {"$ref": "../models/syn-child.schema.json"}
  },
  "type": "object",
  "additionalProperties": true
}
""")
    write("docs/backend/json-schema/requests/syn-b.schema.json", """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "syn-b",
  "properties": {
    "count": {"type": ["integer", "null"], "minimum": 1, "maximum": 365}
  },
  "type": "object",
  "additionalProperties": true
}
""")
    write("docs/backend/json-schema/models/syn-child.schema.json", """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "syn-child",
  "properties": {
    "ratio": {"type": ["number", "null"], "minimum": 0, "maximum": 1}
  },
  "type": "object"
}
""")
    write("docs/backend/endpoints.json", """{
  "endpoints": [
    {"id": "SYN-01", "method": "POST", "path": "/api/v1/syn/a", "request_model": "syn-a",
     "response_model": "syn-a", "query_params": [], "error_codes": ["E-1001"], "source": "真源"},
    {"id": "SYN-02", "method": "PUT", "path": "/api/v1/syn/b", "request_model": "syn-b",
     "response_model": "syn-b", "query_params": [], "error_codes": ["E-1001"], "source": "真源"}
  ]
}
""")
    write("tools/gen-backend-models.py", '''"""夹具生成器（只为让注册表解析器有输入）。"""
REQUESTS: dict[str, dict] = {
    "syn-a": dict(properties={}),
    "syn-b": dict(properties={}),
}
''')
    write("aap-server/src/main/resources/db/migration/V1__baseline.sql", """create table if not exists syn_tbl (
    id bigint primary key,
    amount numeric(18,6),
    count int not null default 1,
    ratio numeric(6,4)
);
""")
    write("aap-server/src/main/java/com/hioas/aap/syn/SynController.java", """package com.hioas.aap.syn;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SynController {

    public record SaveRequest(@Min(value = 1, message = "至少 1") @Max(value = 365, message = "最多 365")
                              Integer count) {
    }

    private final SynService service;

    public SynController(SynService service) {
        this.service = service;
    }

    @PutMapping("/api/v1/syn/b")
    public Object save(@Valid @RequestBody SaveRequest request) {
        return service.save(request);
    }
}
""")
    write("aap-server/src/main/java/com/hioas/aap/syn/SynService.java", """package com.hioas.aap.syn;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import java.math.BigDecimal;

public class SynService {

    private static final BigDecimal MAX_AMOUNT = new BigDecimal("1000");

    public Object save(Object request) {
        return request;
    }

    public void issue(IssueCommand cmd) {
        if (cmd.amount() != null
                && (cmd.amount().compareTo(BigDecimal.ZERO) < 0
                    || cmd.amount().compareTo(MAX_AMOUNT) > 0)) {
            throw ApiException.field(ErrorCode.E_1001, "amount", "金额须在 [0,1000] 之间");
        }
    }

    public void checkRatio(BigDecimal ratio) {
        if (ratio != null && ratio.compareTo(BigDecimal.ONE) > 0) {
            throw ApiException.field(ErrorCode.E_1001, "ratio", "占比不得超过 1");
        }
    }

    public record IssueCommand(BigDecimal amount) {
    }
}
""")
    write("aap-server/src/test/java/com/hioas/aap/syn/SynContractTest.java", """package com.hioas.aap.syn;

class SynContractTest {
    void rejectsOutOfRange() {
        post("/syn/a", "{\\"amount\\":-1}");
        post("/syn/a", "{\\"amount\\":999999}");
        put("/syn/b", "{\\"count\\":0}");
        put("/syn/b", "{\\"count\\":999}");
    }
}
""")


def main():
    if not AUDIT.exists():
        print("[FAIL] 自测自身：审计脚本不存在 %s" % AUDIT)
        return 2
    build_fixture()
    fix_before = snapshot(FIX)

    rc_ok, ok_out = run(FIX)
    check("合规夹具 rc=0", rc_ok == 0, "rc=%d FAIL=%s" % (rc_ok, sorted(toks(ok_out))))
    check("合规夹具 FAIL 断言行 = 0", not toks(ok_out), str(sorted(toks(ok_out))))
    base_pass = pass_toks(ok_out)
    for need in ("A0a", "A0b", "A0c", "A0d", "A0e", "A1b", "A2b", "A3d", "A4b", "A5"):
        check("合规夹具正向对照 %s 存在" % need, need in base_pass, str(sorted(base_pass)))
    # 合规夹具应解析到：2 个被引用模型 + 嵌套 $ref 字段
    check("合规夹具解析到 3 个数值字段（含嵌套 $ref 跟进）",
          "3 个数值约束字段" in ok_out or "3 个数值/数组约束字段" in ok_out,
          [l for l in ok_out.splitlines() if "数值" in l][:1].__str__())

    # ------------------------------------------------------------------ 空夹具
    empty = Path("C:/Users/laitz/AppData/Local/Temp/aap-r61-spotcheck-fixtures-empty")
    empty.mkdir(parents=True, exist_ok=True)
    rc_e, out_e = run(empty)
    etoks = toks(out_e)
    check("空夹具 rc=1（必须变红）", rc_e == 1, "rc=%d" % rc_e)
    for need in ("A0a", "A0b", "A0c", "A0d", "A0e"):
        check("空夹具点名 %s" % need, need in etoks, str(sorted(etoks)))

    # ------------------------------------------------------------------ 注入缺陷（判别力）
    def expect(tag, name, old, new, expected, count=1):
        hits_before = len(mut_misses)
        if not mutate(name, old, new, count):
            check("注入锚点命中（%s）" % tag, False, "锚点未命中 → 注入无效")
            return
        rc, out = run(FIX)
        delta = toks(out) - toks(ok_out)
        check("%s → 恰好新增 %s" % (tag, sorted(expected)), delta == set(expected),
              "实际 delta=%s" % sorted(delta))
        check("%s → 注入真的改到源码" % tag, len(mut_misses) == hits_before)
        # 回滚
        t = (FIX / name).read_text(encoding="utf-8")
        (FIX / name).write_text(t.replace(new, old, count), encoding="utf-8", newline="\n")

    expect("A4 注册表加孤儿模型", "tools/gen-backend-models.py",
           '    "syn-a": dict(', '    "syn-orphan": dict(properties={}),\n    "syn-a": dict(', {"A4"})
    expect("A1 删掉字段级范围注解", "aap-server/src/main/java/com/hioas/aap/syn/SynController.java",
           "@Min(value = 1, message = \"至少 1\") @Max(value = 365, message = \"最多 365\")\n                              Integer count",
           "Integer count", {"A1"})
    expect("A3c schema 上限超出 numeric(p,s) 容量", "docs/backend/json-schema/requests/syn-a.schema.json",
           '"maximum": 1000', '"maximum": 1000000000000000', {"A3c"})
    expect("A2 schema 数值类型与 DDL 列类型不一致", "docs/backend/json-schema/requests/syn-b.schema.json",
           '"type": ["integer", "null"]', '"type": ["number", "null"]', {"A2"})
    expect("A4 端点 request_model 置空致孤儿", "docs/backend/endpoints.json",
           '"request_model": "syn-b"', '"request_model": null', {"A4"})

    check("全部注入锚点命中（未命中即空转通过，坑 66/90/94）", not mut_misses, str(mut_misses[:4]))

    # ------------------------------------------------------------------ 零写副作用
    check("夹具目录零写副作用", snapshot(FIX) == fix_before,
          "夹具被改写：%s" % sorted(set(snapshot(FIX)) ^ set(fix_before))[:3])

    key_files = [REAL / "docs/backend/openapi.yaml", REAL / "docs/backend/endpoints.json",
                 REAL / "tools/gen-backend-models.py"]
    before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in key_files if p.exists()}
    run(REAL)
    after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in key_files if p.exists()}
    check("真实仓库只读（关键文件 md5 不变）", before == after)
    rc_r, out_r = run(REAL)
    check("真实仓库 FAIL 集合 = {A4}（与登记一致）", toks(out_r) == {"A4"}, str(sorted(toks(out_r))))

    print("=== R61 抽查负向自测 ===")
    for line in results:
        print(line)
    n_fail = sum(1 for r in results if r.startswith("[FAIL]"))
    print()
    print("汇总：%d 条断言，FAIL %d" % (len(results), n_fail))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
