#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R62 抽查脚本的负向自测（合成夹具；零写副作用）。

覆盖：
 1) 合规夹具 rc=0 且 FAIL 0，A0a…A0f 六条正向对照全 PASS；
 2) 空夹具 rc≠0 且**点名全部解析器正向对照**（坑 46/75/98/132）；
 3) 16 组注入缺陷各**恰好**新增目标断言（先跑基线 `ok_out`，再比 FAIL 集合差集 —— 坑 82/93）；
 4) 每组注入的锚点必须**真的命中**（未命中即空转通过，坑 66/90/94）；
 5) 夹具目录零写副作用 + 真实仓库关键文件 md5 不变（只读）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "spotcheck-idempotency-R62.py"
FIX = Path("C:/Users/laitz/AppData/Local/Temp/aap-r62-spotcheck-fixtures")
EMPTY = Path("C:/Users/laitz/AppData/Local/Temp/aap-r62-spotcheck-fixtures-empty")
WORK = Path("C:/Users/laitz/AppData/Local/Temp/aap-r62-spotcheck-work")
REAL = Path("E:/workspaces/hioas/hioas-aap-001")

FAIL_RE = re.compile(r"\[FAIL\s*\]")

MD = "docs/backend/02-API接口模型清单.md"
OA = "docs/backend/openapi.yaml"
DDL = "aap-server/src/main/resources/db/migration/V1__baseline.sql"
FILT = "aap-server/src/main/java/com/hioas/aap/support/idempotency/IdempotencyFilter.java"
CLEAN = "aap-server/src/main/java/com/hioas/aap/support/idempotency/IdempotencyCleanupJob.java"
CTRL = "aap-server/src/main/java/com/hioas/aap/demo/DemoController.java"
TEST = "aap-server/src/test/java/com/hioas/aap/demo/DemoIdempotencyTest.java"
CLI = "aap-client/src/api/demo.ts"

IDS = ["SYN-%02d" % i for i in range(1, 11)]

OA_HEADER_BLOCK = ("        - name: Idempotency-Key\n"
                   "          in: header\n"
                   "          required: false\n"
                   "          schema:\n"
                   "            type: string\n")
OA_QUERY_BLOCK = ("        - name: page\n"
                  "          in: query\n"
                  "          schema:\n"
                  "            type: integer\n")

MD_TXT = """# 合成夹具：API 接口模型清单（仅 R62 抽查用）

## §0 通用约定

| 项 | 约定 |
| --- | --- |
| 前缀 | `/api/v1` |
| 幂等 | 非幂等写支持 `Idempotency-Key`（24h，命中返回首次响应体，C11） |

## §1 端点

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
""" + "".join(
    "| %s | POST | `/syn/%d` | 登录 | `a：string` | `syn-%d` | E-1001 | `Idempotency-Key` | 夹具 | T99 |\n"
    % (ids, i, i) for i, ids in enumerate(IDS, 1))

OA_TXT = """openapi: 3.0.3
info:
  title: 合成夹具
  version: 0.0.0
paths:
""" + "".join(
    "  /syn/%d:\n    post:\n      summary: %s\n      parameters:\n%s%s      responses:\n        '200':\n"
    "          description: ok\n" % (i, ids, OA_QUERY_BLOCK, OA_HEADER_BLOCK)
    for i, ids in enumerate(IDS, 1))

DDL_TXT = """create table aap_idempotency_record (
    id                  bigint primary key,
    idempotency_key     varchar(128) not null,
    actor               varchar(64),
    endpoint            varchar(128) not null,
    request_hash        char(64) not null,
    response_status     int,
    response_body       jsonb,
    state               varchar(16) not null default 'IN_PROGRESS',
    expire_at           timestamptz not null,
    created_at          timestamptz not null default now()
);
create unique index if not exists uq_idempotency_key on aap_idempotency_record (idempotency_key);
create index if not exists idx_idempotency_expire on aap_idempotency_record (expire_at);
"""

FILT_TXT = """package com.hioas.aap.support.idempotency;

import java.util.Optional;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.web.filter.OncePerRequestFilter;

/** 合成夹具：幂等过滤器（把完整响应包体与状态码存进 aap_idempotency_record，24h）。 */
public class IdempotencyFilter extends OncePerRequestFilter {

    public static final String HEADER = "Idempotency-Key";
    private static final long TTL_HOURS = 24;

    @Override
    protected void doFilterInternal(Object request, Object response, Object chain) {
        String key = header(request);
        Optional<IdempotencyRecordEntity> existing = find(key);
        if (existing.isPresent() && "DONE".equals(existing.get().getState())) {
            setStatus(response, existing.get().getResponseStatus());
            writeBody(response, existing.get().getResponseBody());
            return;
        }
        insertPlaceholder(key);
        String body = capture(response);
        store(key, status(response), body);
    }

    private void insertPlaceholder(String key) {
        IdempotencyRecordEntity record = new IdempotencyRecordEntity();
        record.setIdempotencyKey(key);
        try {
            mapper.insert(record);
        } catch (DuplicateKeyException race) {
            log.info("幂等键并发插入冲突 key={}", key);
        }
    }

    private void store(String key, int status, String body) {
        if (body == null || body.isBlank()) {
            return;
        }
        IdempotencyRecordEntity record = find(key).orElse(null);
        record.setResponseStatus(status);
        record.setResponseBody(body);
        record.setState("DONE");
        mapper.update(record);
    }

    private Optional<IdempotencyRecordEntity> find(String key) {
        return Optional.ofNullable(mapper.selectOneByQuery(QueryWrapper.create()
                .where("idempotency_key = ? and expire_at > now()", key)
                .limit(1)));
    }
}
"""

CLEAN_TXT = """package com.hioas.aap.support.idempotency;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** 合成夹具：过期幂等记录清理（保证 24h 语义）。 */
@Component
public class IdempotencyCleanupJob {

    @Scheduled(fixedDelay = 3600000L)
    public void purgeExpired() {
        jdbc.update("delete from aap_idempotency_record where expire_at < now()");
    }
}
"""

CTRL_TXT = """package com.hioas.aap.demo;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class DemoController {
    @PostMapping("/api/v1/syn/1")
    public Object create() {
        return null;
    }
}
"""

TEST_TXT = """package com.hioas.aap.demo;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class DemoIdempotencyTest {
""" + "".join(
    '    @DisplayName("%s 幂等：同 Idempotency-Key 重复提交只落一次库，第二次返回首次响应")\n'
    "    @Test\n    void %s() {\n        // headers: Idempotency-Key\n    }\n\n"
    % (ids, ids.lower().replace("-", "_")) for ids in IDS) + "}\n"

CLI_TXT = """import { http } from './http';

export async function create(body: unknown) {
  return http('/syn/1', {
    method: 'POST',
    headers: { 'Idempotency-Key': newKey() },
    data: body,
  });
}
"""

FILES = {MD: MD_TXT, OA: OA_TXT, DDL: DDL_TXT, FILT: FILT_TXT, CLEAN: CLEAN_TXT,
         CTRL: CTRL_TXT, TEST: TEST_TXT, CLI: CLI_TXT}

# ---------------------------------------------------------------- 注入缺陷定义
# (名字, [(相对路径, 旧串, 新串, 替换全部?), ...], 期望新增的 FAIL 断言集合)
INJECTIONS = [
    ("md-ttl", [(MD, "（24h，命中返回首次响应体", "（12h，命中返回首次响应体", False)], {"A2a"}),
    ("md-header", [(MD, "`Idempotency-Key`（24h", "`Idempotency_Key`（24h", False)], {"A1a"}),
    ("md-ttl-drop", [(MD, "（24h，", "（按需，", False)], {"A0a", "A2a"}),
    ("md-idem-row-drop", [(MD, "| 幂等 | 非幂等写支持 `Idempotency-Key`（24h，命中返回首次响应体，C11） |\n", "", False)],
     {"A0a", "A1a", "A2a"}),
    ("md-one-row-drop", [(MD, "| SYN-01 | POST | `/syn/1` | 登录 | `a：string` | `syn-1` | E-1001 | `Idempotency-Key` | 夹具 | T99 |\n", "", False)],
     {"A1b"}),
    ("md-all-rows-drop", [(MD, "| SYN-%02d | POST | `/syn/%d` | 登录 | `a：string` | `syn-%d` | E-1001 | `Idempotency-Key` | 夹具 | T99 |\n" % (i, i, i), "", True) for i in range(1, 11)],
     {"A0b", "A1b", "A5a", "A5b", "A6a"}),
    ("md-drop-code", [(MD, "| SYN-10 | POST | `/syn/10` | 登录 | `a：string` | `syn-10` | E-1001 |",
                       "| SYN-10 | POST | `/syn/10` | 登录 | `a：string` | `syn-10` | E-1401 |", False)], {"A6a"}),
    ("oa-drop-header", [(OA, OA_HEADER_BLOCK, "", True)], {"A1b"}),
    ("oa-no-query", [(OA, "          in: query\n", "          in: cookie\n", True)], {"A0e"}),
    ("ddl-drop-uq", [(DDL, "create unique index if not exists uq_idempotency_key on aap_idempotency_record (idempotency_key);\n", "", False)],
     {"A0c", "A4a"}),
    ("impl-drop-ttl", [(FILT, "TTL_HOURS = 24;", "TTL_HOURS_OLD = 24;", False)], {"A0d", "A2a"}),
    ("impl-no-expire", [(FILT, "idempotency_key = ? and expire_at > now()", "idempotency_key = ?", False)], {"A2b"}),
    ("impl-no-cleanup", [(CLEAN, "    @Scheduled(fixedDelay = 3600000L)\n", "", False)], {"A2c"}),
    ("impl-no-catch", [(FILT, "catch (DuplicateKeyException race)", "catch (IllegalStateException race)", False)], {"A4a"}),
    ("impl-no-replay", [(FILT, "existing.get().getResponseBody()", "existing.get().getState()", False)], {"A3a"}),
    ("ctrl-204", [(CTRL, "    public Object create() {\n        return null;\n    }",
                   "    public ResponseEntity<Void> create() {\n        return ResponseEntity.noContent().build();\n    }", False)], {"A3b"}),
    ("test-drop-case", [(TEST, '    @DisplayName("SYN-05 幂等：同 Idempotency-Key 重复提交只落一次库，第二次返回首次响应")\n', "", False)],
     {"A5b"}),
    ("test-drop-idem", [(TEST, "幂等：同 Idempotency-Key", "重复：同 Idempotency-Key", True)], {"A0f"}),
]

BAD = []
OK = []


def check(cond, label, extra=""):
    (OK if cond else BAD).append(label)
    print("%s %s%s" % ("[OK ]" if cond else "[BAD]", label, (" — " + extra) if extra else ""))


def write_files(root, files):
    for rel, txt in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8", newline="\n")


def tree_fp(root):
    out = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            out[str(p.relative_to(root))] = (len(b), hashlib.md5(b).hexdigest())
    return out


def run_audit(root):
    proc = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                          cwd=str(REAL), capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def fails(text):
    """FAIL 断言名集合；只取明细行（汇总行不含该标记，坑 103）。"""
    out = set()
    for ln in text.splitlines():
        if FAIL_RE.search(ln):
            parts = ln.split()
            if len(parts) >= 2:
                out.add(parts[1])
    return out


def mutate(files, ops):
    """返回 (新 files, 未命中锚点列表)。未命中必须为空，否则注入是空转（坑 66/94）。"""
    new = dict(files)
    missed = []
    for rel, old, newtxt, allocc in ops:
        cur = new.get(rel, "")
        if old not in cur:
            missed.append("%s :: %s" % (rel, old[:48]))
            continue
        new[rel] = cur.replace(old, newtxt) if allocc else cur.replace(old, newtxt, 1)
    return new, missed


def main():
    print("== R62 抽查脚本负向自测（合成夹具）==")
    print("脚本：%s" % AUDIT)
    print()

    # 0) 清理并重建夹具目录（脚本与夹具目录分开命名，坑 106）
    for d in (FIX, EMPTY, WORK):
        if d.exists():
            shutil.rmtree(d)
    FIX.mkdir(parents=True, exist_ok=True)
    EMPTY.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    write_files(FIX, FILES)
    print("[OK ] 夹具写入 %s（%d 文件）；空夹具目录 %s" % (FIX, len(FILES), EMPTY))
    print()

    # 1) 真实仓库只读守卫（关键文件 md5 前后不变）
    real_keys = [REAL / MD, REAL / OA, REAL / DDL, REAL / FILT,
                 REAL / "aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java"]
    real_before = {str(p): (hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None) for p in real_keys}

    fix_before = tree_fp(FIX)

    # 2) 合规夹具：rc=0 且 FAIL 0，A0a…A0f 全 PASS
    rc, out = run_audit(FIX)
    ok_out = fails(out)
    check(rc == 0, "合规夹具 rc=0（实际 rc=%d）" % rc)
    check(ok_out == set(), "合规夹具 FAIL 集合为空（实际 %s）" % sorted(ok_out))
    for a in ["A0a", "A0b", "A0c", "A0d", "A0e", "A0f"]:
        check(a in out and ("[PASS] %s" % a) in out, "合规夹具正向对照 %s 为 PASS" % a)
    check("汇总 PASS" in out, "合规夹具输出含汇总行（正向对照：解析器真的解析到了）")
    print()

    # 3) 空夹具：rc≠0 且点名全部解析器正向对照
    rc_e, out_e = run_audit(EMPTY)
    fe = fails(out_e)
    check(rc_e != 0, "空夹具 rc≠0（实际 rc=%d）" % rc_e)
    for a in ["A0a", "A0b", "A0c", "A0d", "A0e", "A0f"]:
        check(a in fe, "空夹具点名解析器正向对照 %s（坑 46/75/98）" % a)
    for a in ["A1a", "A3b", "A5a"]:
        check(a in fe, "空夹具点名条件化断言 %s（坑 98 空转假绿守卫）" % a)
    print()

    # 4) 注入缺陷判别力
    print("== 注入缺陷判别力（先跑基线，再断言 FAIL 集合恰好新增目标断言）==")
    for name, ops, expected in INJECTIONS:
        mutated, missed = mutate(FILES, ops)
        check(not missed, "注入 %s 锚点全部命中（未命中即空转通过，坑 66/94）" % name,
              "未命中=%s" % missed)
        if missed:
            continue
        wd = WORK / name
        if wd.exists():
            shutil.rmtree(wd)
        write_files(wd, mutated)
        rc_m, out_m = run_audit(wd)
        delta = fails(out_m) - ok_out
        check(delta == expected,
              "注入 %s → 恰好新增目标断言 %s（实际 %s）" % (name, sorted(expected), sorted(delta)))
        check(rc_m != 0, "注入 %s → rc≠0" % name)
        shutil.rmtree(wd)
    print()

    # 5) 零写副作用
    fix_after = tree_fp(FIX)
    check(fix_before == fix_after, "夹具目录零写副作用（%d 文件 size+md5 全等）" % len(fix_after))
    real_after = {str(p): (hashlib.md5(p.read_bytes()).hexdigest() if p.exists() else None) for p in real_keys}
    check(real_before == real_after, "真实仓库关键文件 md5 不变（只读）")
    check(tree_fp(EMPTY) == {}, "空夹具目录仍为空（审计未写入任何文件）")

    print()
    print("自测汇总：OK %d / BAD %d" % (len(OK), len(BAD)))
    if BAD:
        print("失败项：")
        for b in BAD:
            print("  - %s" % b)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
