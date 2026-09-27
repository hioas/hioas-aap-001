#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R58 抽查脚本的负向自测（判别力实测）。

覆盖：合规夹具必须 rc=0 且 FAIL 0；空夹具必须变红并点名 A0a；注入缺陷必须**真的改到源码**
（锚点命中列表为空才允许继续，坑 66/94）且**恰好新增目标断言**；判据敏感性（契约表面）；
真实仓库只读守卫；夹具目录零写副作用。
脚本放 <tmp>/aap-r58-spotcheck/，夹具放 <tmp>/aap-r58-spotcheck-fixtures/（坑 106：不能同目录）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(r"C:/Users/laitz/AppData/Local/Temp/aap-r58-spotcheck/spotcheck-unique-R58.py")
FIX = Path(r"C:/Users/laitz/AppData/Local/Temp/aap-r58-spotcheck-fixtures")
REAL = Path(r"E:/workspaces/hioas/hioas-aap-001")

DDL = """-- fixture DDL
create table if not exists syn_provider (
    id              bigint primary key,
    uscc            varchar(32) not null,
    provider_id     bigint,
    api_key_fingerprint varchar(64),
    deleted         boolean not null default false
);
create unique index if not exists uq_syn_uscc on syn_provider (uscc) where deleted = false and uscc is not null;
"""

ENTITY = """package syn;

import com.mybatisflex.annotation.Table;

@Table(value = "syn_provider")
public class SynEntity {
    private Long id;
    private String uscc;
}
"""

MAPPER = """package syn;

public interface SynMapper extends BaseMapper<SynEntity> {
}
"""

SERVICE_HEAD = """package syn;

import org.springframework.dao.DuplicateKeyException;

public class SynService {

    private final SynMapper synMapper;

    private void ensureUsccUnique(String uscc) {
        long count = synMapper.selectCountByQuery(QueryWrapper.create().where("uscc = ?", uscc));
        if (count > 0) {
            throw new ApiException(ErrorCode.E_1104, "统一社会信用代码已被占用");
        }
    }

    public void save(String uscc) {
        ensureUsccUnique(uscc);
        synMapper.insert(new SynEntity());
    }
"""

CATCH_BLOCK = """
    public void saveWithCatch(String uscc) {
        try {
            synMapper.insert(new SynEntity());
        } catch (DuplicateKeyException race) {
            throw new ApiException(ErrorCode.E_1104, "重复提交");
        }
    }
"""

SERVICE_TAIL = "}\n"

GEH_WITH = """package syn;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.web.bind.annotation.ExceptionHandler;

public class GlobalExceptionHandler {
    @ExceptionHandler(DuplicateKeyException.class)
    public Object dup(DuplicateKeyException e) {
        return null;
    }
}
"""

GEH_WITHOUT = """package syn;

import org.springframework.web.bind.annotation.ExceptionHandler;

public class GlobalExceptionHandler {
    @ExceptionHandler(Exception.class)
    public Object any(Exception e) {
        return null;
    }
}
"""

MD = """# 接口清单（夹具）

## 4. 错误码表（统一响应 `code`）

| 码 | HTTP | 场景 | 依据 |
|---|---|---|---|
| `E-1104` | 409 | 唯一性冲突（uscc 重复、指纹重复） | AC-09 |
"""

TEST_SRC = """package syn;

class SynTest {
    void dup() {
        assertThat(body).contains("uscc");
        assertThat(res.code()).isEqualTo("E-1104");
    }
}
"""


def build(root: Path, with_catch=True, with_surface=True, with_index=True, with_geh=True):
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    (root / "docs/backend/json-schema/requests").mkdir(parents=True)
    (root / "aap-server/src/main/java/syn").mkdir(parents=True)
    (root / "aap-server/src/test/java/syn").mkdir(parents=True)
    (root / "aap-server/src/main/resources/db/migration").mkdir(parents=True)

    ddl = DDL if with_index else DDL.replace(
        "create unique index if not exists uq_syn_uscc on syn_provider (uscc) where deleted = false and uscc is not null;",
        "-- (index removed by fixture)")
    (root / "aap-server/src/main/resources/db/migration/V1__baseline.sql").write_text(ddl, encoding="utf-8", newline="\n")

    props = '"uscc": {"type": "string"}' if with_surface else '"alias": {"type": "string"}'
    (root / "docs/backend/json-schema/requests/syn-create.schema.json").write_text(
        '{"title": "syn-create", "properties": {%s}}' % props, encoding="utf-8", newline="\n")
    (root / "docs/backend/endpoints.json").write_text(
        '{"total": 1, "endpoints": [{"id": "SYN-01", "method": "PUT", "path": "/api/v1/syn/profile", '
        '"request_model": "syn-create", "query_params": ["page"], "error_codes": ["E-1104"]}]}',
        encoding="utf-8", newline="\n")
    (root / "docs/backend/02-API接口模型清单.md").write_text(MD, encoding="utf-8", newline="\n")

    (root / "aap-server/src/main/java/syn/SynEntity.java").write_text(ENTITY, encoding="utf-8", newline="\n")
    (root / "aap-server/src/main/java/syn/SynMapper.java").write_text(MAPPER, encoding="utf-8", newline="\n")
    svc = SERVICE_HEAD + (CATCH_BLOCK if with_catch else "") + SERVICE_TAIL
    (root / "aap-server/src/main/java/syn/SynService.java").write_text(svc, encoding="utf-8", newline="\n")
    (root / "aap-server/src/main/java/syn/GlobalExceptionHandler.java").write_text(
        GEH_WITH if with_geh else GEH_WITHOUT, encoding="utf-8", newline="\n")
    (root / "aap-server/src/test/java/syn/SynTest.java").write_text(TEST_SRC, encoding="utf-8", newline="\n")


def run(root):
    p = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def fails(out):
    return sorted({line.split()[1] for line in out.splitlines()
                   if line.startswith("[FAIL]") and len(line.split()) > 1})


def snapshot(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def mutate(path, old, new, count=-1):
    """替换并返回未命中锚点列表（空 = 注入真的改到了源码，坑 66/94）。"""
    txt = path.read_text(encoding="utf-8")
    n = txt.count(old)
    if n == 0:
        return ["anchor not found: %s" % old[:40]]
    txt2 = txt.replace(old, new) if count < 0 else txt.replace(old, new, count)
    path.write_text(txt2, encoding="utf-8", newline="\n")
    return []


results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("[%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


# ---------------- 1. 合规夹具：rc=0 且 FAIL 0 ----------------
build(FIX / "compliant")
before = snapshot(FIX / "compliant")
rc, out = run(FIX / "compliant")
after = snapshot(FIX / "compliant")
check("T1 合规夹具 rc=0", rc == 0, "rc=%d fails=%s" % (rc, fails(out)))
check("T2 合规夹具 FAIL 0", fails(out) == [], str(fails(out)))
check("T3 正向对照齐全（A0a/A0b/A0c/A0e/A0f 全部 PASS）",
      all(("[PASS] %s" % t) in out for t in ("A0a", "A0b", "A0c", "A0e", "A0f")),
      "A0a/A0b/A0c/A0e/A0f")
check("T4 夹具目录零写副作用", before == after,
      "changed=%d" % len([k for k in set(before) | set(after) if before.get(k) != after.get(k)]))
check("T5 合规夹具下唯一键被解析到（A0a 计数 > 0）",
      bool(re.search(r"\[PASS\] A0a DDL 解析到唯一键 [1-9]", out)), "")

# ---------------- 2. 空夹具必须变红并点名 A0a ----------------
build(FIX / "empty")
for p in sorted((FIX / "empty").rglob("*"), reverse=True):
    if p.is_file():
        p.unlink()
rc, out = run(FIX / "empty")
check("T6 空夹具 rc!=0", rc != 0, "rc=%d" % rc)
check("T7 空夹具点名 A0a（解析器失效必须转红，坑 46/75）", "A0a" in fails(out), str(fails(out)))

# ---------------- 3. 注入缺陷 1：去掉唯一冲突捕获 → 恰好新增 A2 ----------------
build(FIX / "inj1")
bad = mutate(FIX / "inj1/aap-server/src/main/java/syn/SynService.java",
             "catch (DuplicateKeyException race) {", "catch (IllegalStateException race) {")
check("T8 注入1 锚点命中（注入真的改到源码）", bad == [], str(bad))
rc1, out1 = run(FIX / "inj1")
f1 = fails(out1)
check("T9 注入1 恰好新增 A2（仅预查、无捕获）", f1 == ["A2"], str(f1))

# ---------------- 4. 判据敏感性：同时去掉契约表面 → A2 应消失 ----------------
build(FIX / "inj2")
bad2 = mutate(FIX / "inj2/aap-server/src/main/java/syn/SynService.java",
              "catch (DuplicateKeyException race) {", "catch (IllegalStateException race) {")
bad2 += mutate(FIX / "inj2/docs/backend/json-schema/requests/syn-create.schema.json",
               '"uscc": {"type": "string"}', '"alias": {"type": "string"}')
check("T10 注入2 锚点全部命中", bad2 == [], str(bad2))
rc2, out2 = run(FIX / "inj2")
f2 = fails(out2)
check("T11 注入2 后 A2 消失（证明 A2 判据真的依赖「契约表面」这一维度）",
      "A2" not in f2, "fails=%s" % f2)

# ---------------- 5. 注入缺陷 3：删掉唯一索引 → A0a 转红 ----------------
build(FIX / "inj3")
bad3 = mutate(FIX / "inj3/aap-server/src/main/resources/db/migration/V1__baseline.sql",
              "create unique index if not exists uq_syn_uscc on syn_provider (uscc) where deleted = false and uscc is not null;",
              "-- removed")
check("T12 注入3 锚点命中", bad3 == [], str(bad3))
rc3, out3 = run(FIX / "inj3")
f3 = fails(out3)
check("T13 注入3 点名 A0a（唯一索引消失必须转红）", "A0a" in f3, "fails=%s" % f3)

# ---------------- 6. 全局兜底分支：无 handler → A0d 变 INFO（不是 FAIL） ----------------
build(FIX / "geh")
bad4 = mutate(FIX / "geh/aap-server/src/main/java/syn/GlobalExceptionHandler.java",
              "@ExceptionHandler(DuplicateKeyException.class)", "@ExceptionHandler(IllegalStateException.class)")
check("T14 注入4 锚点命中", bad4 == [], str(bad4))
rc4, out4 = run(FIX / "geh")
check("T15 无全局兜底时 A0d 走 INFO 分支（且不产生 FAIL）",
      "[INFO] A0d" in out4 and "A0d" not in fails(out4), "fails=%s" % fails(out4))

# ---------------- 7. 真实仓库只读守卫 ----------------
# R68 修判据范围：原先比**全仓库** git status，同机另一代理在比对窗口内改客户端文件
# （实测 aap-client/package.json mtime 落在窗口内）会让它**假红**（坑 15/27/81：判据范围与语义不符）。
# 语义是「本抽查没写仓库」，故收窄到本抽查的读写范围（backend 源码 / docs / tools）。
SCOPE = ["aap-server", "docs", "tools"]
def snap():
    return subprocess.run(["git", "-C", str(REAL), "status", "--porcelain", "--"] + SCOPE,
                          capture_output=True, text=True).stdout
g0 = snap()
rcr, outr = run(REAL)
g1 = snap()
check("T16 真实仓库只读（本抽查范围内 git status 不变）", g0 == g1, "")
check("T17 真实仓库解析到 42 条唯一索引 + 5 条契约可触发唯一键命中 A2",
      "唯一键 95 条" in outr and "[FAIL] A2" in outr, "rc=%d" % rcr)
check("T18 真实仓库 FAIL 集合恰好 = {A2}", fails(outr) == ["A2"], str(fails(outr)))

print()
bad_total = [n for n, okk, _ in results if not okk]
print("自测汇总：%d/%d PASS" % (len(results) - len(bad_total), len(results)))
if bad_total:
    print("失败用例：%s" % ", ".join(bad_total))
sys.exit(1 if bad_total else 0)
