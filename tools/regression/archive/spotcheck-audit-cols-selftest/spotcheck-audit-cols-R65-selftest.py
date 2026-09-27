#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R65 抽查脚本的负向自测（判别力实测）。

覆盖：合规夹具必须 rc=0 且 FAIL 0 + A0a…A0g 七条正向对照全 PASS + 空夹具必须变红并点名全部正向对照与条件化断言 +
12 组注入缺陷各**恰好**新增目标断言（含 1 组多锚点、1 组解析器失效）+ 全部注入锚点命中且新文本真的出现（坑 66/90/94）+
夹具目录零写副作用（含不得留下 __pycache__，坑 106）+ 真实仓库 FAIL 集合与预期一致（只读）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("C:/Users/laitz/AppData/Local/Temp/aap-r65-spotcheck/spotcheck-audit-cols-R65.py")
FIX = Path("C:/Users/laitz/AppData/Local/Temp/aap-r65-spotcheck-fixtures")
REAL = Path("E:/workspaces/hioas/hioas-aap-001")

DDL = '''-- 夹具：三张业务表，均含通用审计字段
create table if not exists aap_demo_alpha (
    id              bigint primary key,
    name            varchar(64),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);

create table if not exists aap_demo_beta (
    id              bigint primary key,
    name            varchar(64),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);

create table if not exists aap_demo_gamma (
    id              bigint primary key,
    name            varchar(64),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);

create table if not exists aap_demo_log (
    id              bigint primary key,
    name            varchar(64),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
'''

ENTITY_ALPHA = '''package com.hioas.aap.demo;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;

@Table(value = "aap_demo_alpha", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class DemoAlphaEntity extends BaseEntity {
}
'''

ENTITY_GAMMA = '''package com.hioas.aap.demo;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;

@Table(value = "aap_demo_gamma",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class DemoGammaEntity extends BaseEntity {
}
'''

ENTITY_LOG = '''package com.hioas.aap.demo;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;

/** 追加型日志表（append-only）：插入后不再更新，故不挂 onUpdate。 */
@Table(value = "aap_demo_log", onInsert = AuditListeners.Insert.class)
public class DemoLogEntity extends BaseEntity {
}
'''

SERVICE = '''package com.hioas.aap.demo;

import com.hioas.aap.common.AuditContext;
import org.springframework.jdbc.core.JdbcTemplate;

public class DemoService {

    private final JdbcTemplate jdbc;

    public DemoService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void create(String name, Long actor) {
        AuditContext.set(new AuditContext.Actor(actor, "ADMIN", "admin", "127.0.0.1"));
        jdbc.update("""
                insert into aap_demo_beta (id, name, created_at, updated_at, created_by, updated_by, deleted, version)
                values (nextval('seq_demo'), ?, now(), now(), ?, ?, false, 0)
                """, name, actor, actor);
    }

    public void rename(Long id, String name, Long actor) {
        jdbc.update("""
                update aap_demo_beta
                   set name = ?, updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false
                """, name, actor, id);
    }

    public void upsert(String name, Long actor) {
        jdbc.update("""
                insert into aap_demo_beta (id, name, created_at, updated_at, created_by, updated_by, deleted, version)
                values (nextval('seq_demo'), ?, now(), now(), ?, ?, false, 0)
                on conflict (name) do update set
                    updated_at = now(), updated_by = ?, version = aap_demo_beta.version + 1
                """, name, actor, actor, actor);
    }
}
'''

LISTENERS = '''package com.hioas.aap.common;

import java.time.OffsetDateTime;

public final class AuditListeners {

    public static class Insert extends AbstractInsertListener<BaseEntity> {

        @Override
        public void doInsert(BaseEntity entity) {
            Long actorId = AuditContext.currentActorId().orElse(null);
            entity.setCreatedBy(actorId);
            entity.setUpdatedBy(actorId);
        }
    }

    public static class Update extends AbstractUpdateListener<BaseEntity> {

        @Override
        public void doUpdate(BaseEntity entity) {
            entity.setUpdatedAt(OffsetDateTime.now());
            Long actorId = AuditContext.currentActorId().orElse(null);
            entity.setUpdatedBy(actorId);
        }
    }
}
'''

TEST_SRC = '''package com.hioas.aap.demo;

import static org.assertj.core.api.Assertions.assertThat;

class DemoAuditTest {

    @Test
    @DisplayName("ORM 插入：审计字段自动填充（created_by/updated_by）")
    void insertFillsAuditFields() {
        DemoAlphaEntity entity = new DemoAlphaEntity();
        assertThat(entity.getCreatedBy()).isEqualTo(9001L);
        assertThat(entity.getUpdatedBy()).isEqualTo(9001L);
    }

    @Test
    @DisplayName("业务表通用审计字段齐备")
    void auditColumnsPresent() {
        assertThat(columns).contains("created_by", "updated_by");
    }
}
'''

MD = '''# 01 ER 数据模型（夹具）

| 项目 | 列 |
| --- | --- |
| 审计字段（业务表通用） | `id, created_at, updated_at, created_by, updated_by, deleted, version` |

| 3 | `aap_demo_log` | demo | 追加型日志（append-only，四类操作必录） | ✅ |
'''

FILES = {
    "aap-server/src/main/resources/db/migration/V1__baseline.sql": DDL,
    "aap-server/src/main/java/com/hioas/aap/demo/DemoAlphaEntity.java": ENTITY_ALPHA,
    "aap-server/src/main/java/com/hioas/aap/demo/DemoGammaEntity.java": ENTITY_GAMMA,
    "aap-server/src/main/java/com/hioas/aap/demo/DemoLogEntity.java": ENTITY_LOG,
    "aap-server/src/main/java/com/hioas/aap/demo/DemoService.java": SERVICE,
    "aap-server/src/main/java/com/hioas/aap/common/AuditListeners.java": LISTENERS,
    "aap-server/src/test/java/com/hioas/aap/demo/DemoAuditTest.java": TEST_SRC,
    "docs/backend/01-ER数据模型.md": MD,
}

# 注入缺陷：每个用例 = (名字, [(相对路径, 旧文本, 新文本, 替换次数)], 期望新增的 FAIL token 集合)
INJECTIONS = [
    ("sql-insert-del-created-by", [
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
         "created_at, updated_at, created_by, updated_by, deleted, version",
         "created_at, updated_at, deleted, version", 1),
    ], {"A1"}),
    ("entity-del-oninsert", [
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoAlphaEntity.java",
         "onInsert = AuditListeners.Insert.class, ", "", 1),
    ], {"A1b"}),
    ("entity-del-onupdate", [
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoAlphaEntity.java",
         ", onUpdate = AuditListeners.Update.class)", ")", 1),
    ], {"A2b"}),
    ("sql-update-del-updated-by", [
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
         "set name = ?, updated_at = now(), updated_by = ?, version = version + 1",
         "set name = ?, updated_at = now(), version = version + 1", 1),
    ], {"A2"}),
    ("upsert-del-updated-by", [
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
         "updated_at = now(), updated_by = ?, version = aap_demo_beta.version + 1",
         "updated_at = now(), version = aap_demo_beta.version + 1", 1),
    ], {"A2"}),
    ("listeners-update-guard", [
        ("aap-server/src/main/java/com/hioas/aap/common/AuditListeners.java",
         "            entity.setUpdatedAt(OffsetDateTime.now());\n"
         "            Long actorId = AuditContext.currentActorId().orElse(null);\n"
         "            entity.setUpdatedBy(actorId);",
         "            entity.setUpdatedAt(OffsetDateTime.now());\n"
         "            Long actorId = AuditContext.currentActorId().orElse(null);\n"
         "            if (actorId != null) {\n"
         "                entity.setUpdatedBy(actorId);\n"
         "            }", 1),
    ], {"A3"}),
    ("md-del-claim", [
        ("docs/backend/01-ER数据模型.md",
         "| 审计字段（业务表通用） | `id, created_at, updated_at, created_by, updated_by, deleted, version` |",
         "", 1),
    ], {"A0g", "A5"}),
    ("ddl-add-table-no-audit", [
        ("aap-server/src/main/resources/db/migration/V1__baseline.sql",
         "create table if not exists aap_demo_gamma (",
         "create table if not exists aap_demo_omega (\n"
         "    id              bigint primary key,\n"
         "    name            varchar(64)\n"
         ");\n\n"
         "create table if not exists aap_demo_gamma (", 1),
    ], {"A5"}),
    ("test-del-value", [
        ("aap-server/src/test/java/com/hioas/aap/demo/DemoAuditTest.java",
         "        assertThat(entity.getCreatedBy()).isEqualTo(9001L);\n"
         "        assertThat(entity.getUpdatedBy()).isEqualTo(9001L);\n",
         "", 1),
    ], {"A4"}),
    ("test-del-struct", [
        ("aap-server/src/test/java/com/hioas/aap/demo/DemoAuditTest.java",
         'assertThat(columns).contains("created_by", "updated_by");',
         'assertThat(columns).contains("id");', 1),
    ], {"A0f"}),
    ("svc-del-writes", [
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
         "insert into aap_demo_beta", "select 1 from aap_demo_beta", 2),
        ("aap-server/src/main/java/com/hioas/aap/demo/DemoService.java",
         "update aap_demo_beta", "select 1 from aap_demo_beta", 1),
    ], {"A0c", "A0d", "A1", "A2"}),
    ("md-del-append-only", [
        ("docs/backend/01-ER数据模型.md",
         "| 3 | `aap_demo_log` | demo | 追加型日志（append-only，四类操作必录） | ✅ |",
         "| 3 | `aap_demo_log` | demo | 追加型日志 | ✅ |", 1),
    ], {"A2b"}),
]

FAIL_RE = re.compile(r"\[FAIL\s*\]\s+(\S+)")
ok_count = [0]
bad_count = [0]


def check(cond, msg):
    if cond:
        ok_count[0] += 1
        print("[PASS] %s" % msg)
    else:
        bad_count[0] += 1
        print("[FAIL] %s" % msg)


def build(root, files):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")


def run_spotcheck(root):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out, set(FAIL_RE.findall(out))


def snapshot(root):
    snap = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            snap[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return snap


def mutate(root, ops):
    unhit = []
    for (rel, old, new, cnt) in ops:
        p = root / rel
        txt = p.read_text(encoding="utf-8")
        n = txt.count(old)
        if n < cnt:
            unhit.append("%s :: %r (期望 %d 处，实际 %d 处)" % (rel, old[:48], cnt, n))
            continue
        txt2 = txt.replace(old, new, cnt)
        if txt2 == txt:
            unhit.append("%s :: %r (替换后文本未变化)" % (rel, old[:48]))
            continue
        if new and new not in txt2:
            unhit.append("%s :: 新文本未出现 %r" % (rel, new[:48]))
            continue
        p.write_text(txt2, encoding="utf-8", newline="\n")
    return unhit


def main():
    print("== R65 抽查负向自测（spotcheck-audit-cols-R65-selftest） ==")
    if FIX.exists():
        shutil.rmtree(FIX)
    FIX.mkdir(parents=True)

    # ---- 合规夹具
    comp = FIX / "compliant"
    build(comp, FILES)
    before = snapshot(comp)
    rc, out, fails = run_spotcheck(comp)
    check(rc == 0, "合规夹具 rc=0（实际 %d）" % rc)
    check(not fails, "合规夹具 FAIL 0（实际 %s）" % sorted(fails))
    a0 = [x for x in re.findall(r"\[(?:PASS|FAIL)\s*\]\s+(A0[a-g])", out)]
    check(sorted(set(a0)) == ["A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"],
          "合规夹具下 A0a…A0g 七条正向对照全部出现（实际 %s）" % sorted(set(a0)))
    check(len([x for x in re.findall(r"\[PASS\s*\]\s+(A0[a-g])", out)]) == 7,
          "合规夹具下 A0a…A0g 七条正向对照全部 PASS")
    check(not re.search(r"\[FAIL\s*\]\s+A0", out), "合规夹具下无 A0* FAIL")
    after = snapshot(comp)
    check(before == after, "合规夹具零写副作用（%d 个文件 md5 全等）" % len(before))
    check(not list(FIX.rglob("__pycache__")), "夹具目录无 __pycache__")

    # ---- 空夹具
    empty = FIX / "empty"
    empty.mkdir(parents=True, exist_ok=True)
    rc_e, out_e, fails_e = run_spotcheck(empty)
    check(rc_e != 0, "空夹具 rc≠0（实际 %d）" % rc_e)
    miss = [a for a in ["A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g"] if a not in fails_e]
    check(not miss, "空夹具点名全部 A0* 正向对照（缺 %s）" % miss)
    miss2 = [a for a in ["A1", "A1b", "A2", "A2b", "A3", "A4", "A5"] if a not in fails_e]
    check(not miss2, "空夹具点名全部条件化断言（缺 %s）" % miss2)

    # ---- 注入缺陷（基线用专用名，坑 93）
    ok_out = out
    for (name, ops, expect) in INJECTIONS:
        d = FIX / ("inj-" + name)
        shutil.copytree(comp, d)
        unhit = mutate(d, ops)
        check(not unhit, "注入 %s 的锚点全部命中且真的改到源码" % name)
        rc_i, out_i, fails_i = run_spotcheck(d)
        delta = sorted(fails_i - set(FAIL_RE.findall(ok_out)))
        check(set(delta) == set(expect),
              "注入 %s → 恰好新增 %s（实际 %s）" % (name, sorted(expect), delta))

    # ---- 真实仓库（只读）
    rc_r, out_r, fails_r = run_spotcheck(REAL)
    check(rc_r == 1, "真实仓库 rc=1（存在 FAIL 明细，实际 %d）" % rc_r)
    check(fails_r == {"A1", "A2", "A3"}, "真实仓库 FAIL 集合 = {A1,A2,A3}（实际 %s）" % sorted(fails_r))

    print()
    total = ok_count[0] + bad_count[0]
    print("SELFTEST PASS %d/%d" % (ok_count[0], total))
    return 0 if bad_count[0] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
