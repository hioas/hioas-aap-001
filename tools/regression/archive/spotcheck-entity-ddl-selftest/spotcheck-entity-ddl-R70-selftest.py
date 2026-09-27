#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R70 上条抽查（ORM 实体 ↔ DDL 映射一致性）的负向自测。

覆盖：合规夹具 rc=0 且 FAIL 明细空 · 正向对照 A0a..A0k 全 PASS · 空夹具 rc≠0 且点名全部 A0* ·
16 组注入缺陷（每条断言一个反例；锚点必须**真的命中且真的改到源码**，坑 66/94/104）·
2 组回归守卫（常量引用序列 / 分区子表豁免）· 夹具目录零写副作用 · 真实仓库关键文件 md5 不变（只读守卫）。
判据：注入后「FAIL 集合**恰好新增**目标断言」——基线用**专用变量名** `ok_fails`（坑 93）。
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "spotcheck-entity-ddl-R70.py"
FIX = Path("C:/Users/laitz/AppData/Local/Temp/aap-r70-spotcheck-fixtures")
REPO = Path("E:/workspaces/hioas/hioas-aap-001")
REL_DDL = "aap-server/src/main/resources/db/migration/V1__baseline.sql"
REL_JAVA = "aap-server/src/main/java/com/hioas/aap"
REL_ER = "docs/backend/01-ER数据模型.md"

DDL_SQL = """-- 夹具基线建表
create table if not exists aap_demo_item (
    id                  bigint primary key,
    name                varchar(64) not null,
    amount              numeric(18,6) not null default 0,
    status              varchar(16) not null default 'NEW',
    sms_2fa             boolean not null default false,
    payload             jsonb,
    extra_json          jsonb,
    alt_a               varchar(16),
    alt_b               varchar(16),
    alt_c               varchar(16),
    remark              text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean not null default false,
    version             int not null default 0
);

create table if not exists aap_demo_bare (
    id                  bigint primary key,
    name                varchar(64) not null,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    created_by          bigint,
    updated_by          bigint,
    deleted             boolean not null default false,
    version             int not null default 0
);

create table if not exists aap_demo_raw (
    id                  bigint primary key,
    name                varchar(64) not null,
    created_at          timestamptz not null default now(),
    created_by          bigint
);

create table if not exists aap_demo_hourly (
    id                  bigint primary key,
    stat_hour           timestamptz not null,
    created_at          timestamptz not null default now()
) partition by range (stat_hour);

create table if not exists aap_demo_hourly_default partition of aap_demo_hourly default;

create sequence if not exists seq_demo start 1 increment 1;
create sequence if not exists seq_demo_orphan start 1 increment 1;
"""

BASE_ENTITY_JAVA = """package com.hioas.aap.common;

import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import java.time.OffsetDateTime;

public abstract class BaseEntity {

    @Id(keyType = KeyType.Generator, value = "snowFlakeId")
    @Column("id")
    private Long id;

    @Column("created_at")
    private OffsetDateTime createdAt;

    @Column("updated_at")
    private OffsetDateTime updatedAt;

    @Column("created_by")
    private Long createdBy;

    @Column("updated_by")
    private Long updatedBy;

    @Column(value = "deleted", isLogicDelete = true)
    private Boolean deleted;

    @Column(value = "version", version = true)
    private Integer version;
}
"""

ITEM_JAVA = """package com.hioas.aap.demo;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.math.BigDecimal;

/** 夹具实体：aap_demo_item。 */
@Table(value = "aap_demo_item", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class DemoItemEntity extends BaseEntity {

    private String name;

    private BigDecimal amount;

    private String status;

    @Column("sms_2fa")
    private Boolean sms2fa;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String payload;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String extraJson;
}
"""

BARE_JAVA = """package com.hioas.aap.demo;

import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;

/** 夹具实体：aap_demo_bare（无手写 SQL 写路径）。 */
@Table(value = "aap_demo_bare")
public class DemoBareEntity extends BaseEntity {

    private String name;
}
"""

RAW_JAVA = """package com.hioas.aap.demo;

import com.hioas.aap.common.AuditListeners;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Id;
import com.mybatisflex.annotation.KeyType;
import com.mybatisflex.annotation.Table;

/** 夹具实体：aap_demo_raw（不继承 BaseEntity）。 */
@Table(value = "aap_demo_raw", onInsert = AuditListeners.Insert.class)
public class DemoRawEntity {

    @Id(keyType = KeyType.Generator, value = "snowFlakeId")
    @Column("id")
    private Long id;

    private String name;
}
"""

SERVICE_JAVA = """package com.hioas.aap.demo;

import org.springframework.jdbc.core.JdbcTemplate;

/** 夹具服务：手写 SQL 写路径 + 序列引用。 */
public class DemoService {

    private final JdbcTemplate jdbc = null;

    public Long nextDemoId() {
        return jdbc.queryForObject("select nextval('seq_demo')", Long.class);
    }

    public void touch(String name) {
        jdbc.update("insert into aap_demo_item (id, name, created_at) values (?, ?, now())", 1L, name);
    }
}
"""

ER_MD = """# 夹具 ER 数据模型

| 表 | 说明 |
| --- | --- |
| `aap_demo_item` | 主表 |
| `aap_demo_bare` | 无手写写路径 |
| `aap_demo_raw` | 非 BaseEntity |
| `aap_demo_hourly` | 分区父表 |
"""


def write_base(dst: Path):
    files = {
        REL_DDL: DDL_SQL,
        REL_JAVA + "/common/BaseEntity.java": BASE_ENTITY_JAVA,
        REL_JAVA + "/demo/DemoItemEntity.java": ITEM_JAVA,
        REL_JAVA + "/demo/DemoBareEntity.java": BARE_JAVA,
        REL_JAVA + "/demo/DemoRawEntity.java": RAW_JAVA,
        REL_JAVA + "/demo/DemoService.java": SERVICE_JAVA,
        REL_ER: ER_MD,
    }
    for rel, txt in files.items():
        p = dst / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8", newline="\n")


def fresh(name: str) -> Path:
    dst = FIX / name
    if dst.exists():
        for p in sorted(dst.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        dst.rmdir()
    dst.mkdir(parents=True, exist_ok=True)
    write_base(dst)
    return dst


def run_audit(root: Path):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)],
                          capture_output=True, cwd=str(REPO))
    text = proc.stdout.decode("utf-8", errors="replace") + proc.stderr.decode("utf-8", errors="replace")
    fails = sorted({ln.split()[1] for ln in text.splitlines()
                    if re.search(r"\[FAIL\s*\]", ln) and len(ln.split()) > 1})
    passes = sorted({ln.split()[1] for ln in text.splitlines()
                     if ln.startswith("[PASS]") and len(ln.split()) > 1})
    return proc.returncode, fails, passes, text


def mutate(root: Path, rel: str, pairs):
    """返回未命中的锚点列表（坑 66：锚点没命中 = 缺陷没注入 = 空转通过）。"""
    p = root / rel
    txt = p.read_text(encoding="utf-8")
    missed = []
    for old, new in pairs:
        if old not in txt:
            missed.append(old[:40])
            continue
        txt = txt.replace(old, new, 1)
    p.write_text(txt, encoding="utf-8", newline="\n")
    return missed


def fingerprint(root: Path):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


lines, bad = [], []


def emit(tag, ok, msg):
    lines.append("[%s] %s %s" % ("PASS" if ok else "FAIL", tag, msg))
    if not ok:
        bad.append(tag)


# ---------------------------------------------------------------- T1..T6 合规 / 空夹具
base = fresh("base")
rc, base_fails, base_passes, base_text = run_audit(base)
ok_rc, ok_fails = rc, list(base_fails)          # 基线专用变量名（坑 93）
emit("T1", ok_rc == 0, "合规夹具 rc=0 — rc=%d" % ok_rc)
emit("T2", ok_fails == [], "合规夹具 FAIL 明细为空 — FAIL=%s" % ok_fails)
EXPECT_A0 = ["A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h", "A0i", "A0j", "A0k"]
EXPECT_PASS = EXPECT_A0 + ["A5b", "A6b", "A7b", "A8b"]
emit("T3", sorted(base_passes) == sorted(EXPECT_PASS),
     "合规夹具正向对照（A0a..A0k + 4 条上限守卫）全 PASS — PASS=%s" % sorted(base_passes))
emit("T4", "解析计数：DDL 表 5" in base_text, "合规夹具解析到 5 张 DDL 表（正向对照真的读到输入）")

empty = FIX / "empty"
if empty.exists():
    for p in sorted(empty.rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
empty.mkdir(parents=True, exist_ok=True)
erc, efails, epasses, etext = run_audit(empty)
emit("T5", erc != 0, "空夹具 rc≠0 — rc=%d" % erc)
missing_a0 = [t for t in EXPECT_A0 if t not in efails]
emit("T6", not missing_a0, "空夹具点名全部 A0* — 未点名=%s" % missing_a0)
emit("T7", not [t for t in epasses if t.startswith("A0")],
     "空夹具下 A0* 无一条 PASS — PASS=%s" % [t for t in epasses if t.startswith("A0")])
GUARDS = ["A1", "A1c", "A1d", "A2", "A4", "A5", "A6", "A7"]
emit("T8", all(g in efails for g in GUARDS),
     "空夹具点名全部条件化断言 — 未点名=%s" % [g for g in GUARDS if g not in efails])

# ---------------------------------------------------------------- N1..N16 注入缺陷
INJ = [
    ("N1-A1 列不存在", REL_JAVA + "/demo/DemoItemEntity.java",
     [('    private String name;', '    @Column("missing_col")\n    private String name;')], ["A1"]),
    ("N2-A1b 表名错", REL_JAVA + "/demo/DemoItemEntity.java",
     [('@Table(value = "aap_demo_item", onInsert', '@Table(value = "aap_demo_item_x", onInsert')],
     ["A1b", "A0e"]),
    ("N3-A1c 去掉内联主键", REL_DDL,
     [("    id                  bigint primary key,\n    name                varchar(64) not null,\n    amount",
       "    id                  bigint,\n    name                varchar(64) not null,\n    amount")], ["A1c"]),
    ("N4-A1d 两字段映射同列", REL_JAVA + "/demo/DemoItemEntity.java",
     [('    private String name;', '    @Column("name")\n    private String nameDup;\n\n    private String name;')],
     ["A1d"]),
    ("N5-A2 类型族不符", REL_DDL,
     [("    amount              numeric(18,6) not null default 0,", "    amount              bigint not null default 0,")],
     ["A2"]),
    ("N6-A3 jsonb 无 typeHandler", REL_JAVA + "/demo/DemoItemEntity.java",
     [('    @Column(typeHandler = JsonbTypeHandler.class)\n    private String payload;', '    private String payload;')],
     ["A3"]),
    ("N7-A4 监听器要写的列不存在", REL_DDL,
     [("create table if not exists aap_demo_raw (\n    id                  bigint primary key,\n    name                varchar(64) not null,\n    created_at          timestamptz not null default now(),\n    created_by          bigint",
       "create table if not exists aap_demo_raw (\n    id                  bigint primary key,\n    name                varchar(64) not null,\n    created_at          timestamptz not null default now()")],
     ["A4"]),
    ("N8-A1+A5 约定名漂移且无注解", REL_JAVA + "/demo/DemoItemEntity.java",
     [("    private String status;", "    private String statS;")], ["A1", "A5"]),
    ("N9-A6 未映射 NOT NULL 无默认列（ORM 独占）", REL_DDL,
     [("create table if not exists aap_demo_bare (\n    id                  bigint primary key,\n    name                varchar(64) not null,",
       "create table if not exists aap_demo_bare (\n    id                  bigint primary key,\n    name                varchar(64) not null,\n    owner_code          varchar(32) not null,")],
     ["A6"]),
    ("N10-A7 引用未声明序列", REL_JAVA + "/demo/DemoService.java",
     [("nextval('seq_demo')", "nextval('seq_missing')")], ["A7"]),
    ("N11-A7b 孤儿序列超上限", REL_DDL,
     [("create sequence if not exists seq_demo_orphan start 1 increment 1;",
       "create sequence if not exists seq_demo_orphan start 1 increment 1;\n"
       "create sequence if not exists seq_o1 start 1 increment 1;\n"
       "create sequence if not exists seq_o2 start 1 increment 1;\n"
       "create sequence if not exists seq_o3 start 1 increment 1;")], ["A7b"]),
    ("N12-A8 ER 声明表未建", REL_ER,
     [("| `aap_demo_hourly` | 分区父表 |", "| `aap_demo_hourly` | 分区父表 |\n| `aap_ghost_table` | 幽灵表 |")],
     ["A8"]),
    ("N13-A8b 分区子表超上限", REL_DDL,
     [("create table if not exists aap_demo_hourly_default partition of aap_demo_hourly default;",
       "create table if not exists aap_demo_hourly_default partition of aap_demo_hourly default;\n"
       "create table if not exists aap_demo_p1_default partition of aap_demo_hourly default;\n"
       "create table if not exists aap_demo_p2_default partition of aap_demo_hourly default;\n"
       "create table if not exists aap_demo_p3_default partition of aap_demo_hourly default;")], ["A8b"]),
    ("N14-A5b 显式 @Column 超上限", REL_JAVA + "/demo/DemoItemEntity.java",
     [('    @Column(typeHandler = JsonbTypeHandler.class)\n    private String extraJson;',
       '    @Column(typeHandler = JsonbTypeHandler.class)\n    private String extraJson;\n\n'
       '    @Column("alt_a")\n    private String altA1;\n\n'
       '    @Column("alt_b")\n    private String altB1;\n\n'
       '    @Column("alt_c")\n    private String altC1;')], ["A5b"]),
    ("N15-A9 SQL 引用未建表", REL_JAVA + "/demo/DemoService.java",
     [('jdbc.update("insert into aap_demo_item (id, name, created_at) values (?, ?, now())", 1L, name);',
       'jdbc.update("insert into aap_ghost_table (id) values (?)", 1L);')], ["A9"]),
    ("N16-A6b 手写写路径豁免超上限", REL_DDL,
     [("    remark              text,",
       "\n".join("    req_%d               varchar(8) not null," % i for i in range(1, 10)))], ["A6b"]),
]

for name, rel, pairs, expect in INJ:
    root = fresh("inj")
    missed = mutate(root, rel, pairs)
    if missed:
        emit(name + " 锚点命中", False, "锚点未命中（缺陷未注入，坑 66）：%s" % missed)
        continue
    emit(name + " 锚点命中", True, "锚点命中 %d 个且源码已改" % len(pairs))
    rc2, f2, _, t2 = run_audit(root)
    delta = sorted(set(f2) - set(ok_fails))
    gone = sorted(set(ok_fails) - set(f2))
    emit(name + " 恰好新增目标断言 " + "/".join(expect), delta == sorted(expect) and not gone,
         "新增=%s 消失=%s rc=%d（期望新增=%s）" % (delta, gone, rc2, sorted(expect)))

# ---------------------------------------------------------------- R1..R2 回归守卫
root = fresh("regr-const-seq")
missed = mutate(root, REL_JAVA + "/demo/DemoService.java", [
    ('    private final JdbcTemplate jdbc = null;',
     '    private static final String SEQ_DEMO = "seq_demo";\n\n    private final JdbcTemplate jdbc = null;'),
    ("nextval('seq_demo')", "nextval(SEQ_DEMO)"),
])
if missed:
    emit("R1-常量引用序列 锚点命中", False, "锚点未命中：%s" % missed)
else:
    emit("R1-常量引用序列 锚点命中", True, "锚点命中 2 个（常量声明 + 引用改写）")
    rc2, f2, _, _ = run_audit(root)
    emit("R1-常量引用序列 结果不变（仍 0 FAIL）", rc2 == 0 and sorted(set(f2)) == sorted(set(ok_fails)),
         "新增=%s rc=%d" % (sorted(set(f2) - set(ok_fails)), rc2))

emit("R2-分区子表豁免 结果不变", "A8b ER 文档差异中的分区子表 1 条" in base_text,
     "基线里分区子表按豁免类计数 1 条且未判 A8 FAIL（%s）" % ("命中" if "A8b ER 文档差异中的分区子表 1 条" in base_text else "未命中"))

# ---------------------------------------------------------------- 零写副作用 / 只读守卫
before = fingerprint(base)
run_audit(base)
after = fingerprint(base)
emit("T9 夹具目录零写副作用", before == after,
     "审计前后夹具指纹一致（%d 文件）" % len(after))
emit("T10 夹具目录无 __pycache__", not list(FIX.rglob("__pycache__")), "夹具目录未残留 __pycache__")

KEY = [REPO / "docs/backend/openapi.yaml", REPO / "docs/backend/endpoints.json",
       REPO / REL_DDL, REPO / "aap-server/src/main/java/com/hioas/aap/common/BaseEntity.java"]
kbefore = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in KEY if p.exists()}
rrc, rfails, _, rtext = run_audit(REPO)
kafter = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in KEY if p.exists()}
emit("T11 真实仓库关键文件只读", kbefore == kafter, "真实仓库 %d 个关键文件 md5 不变" % len(kafter))
emit("T12 真实仓库仍可判定（非空转）", "解析计数：DDL 表" in rtext and rrc in (0, 1),
     "真实仓库 rc=%d，FAIL=%s" % (rrc, rfails))

print("\n".join(lines))
print("")
print("== 自测汇总：FAIL %d 项 %s ==" % (len(bad), bad))
sys.exit(1 if bad else 0)
