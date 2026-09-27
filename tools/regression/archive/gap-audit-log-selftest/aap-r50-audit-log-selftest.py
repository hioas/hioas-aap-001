"""R50 抽查脚本的负向自测（判别力实测）。

夹具根：C:/Users/laitz/AppData/Local/Temp/aap-r50-spotcheck-fixtures（与脚本目录分开命名，坑 106）
被测：C:/Users/laitz/AppData/Local/Temp/aap-r50-spotcheck/aap-r50-audit-log.py

每条用例：先跑基线（合规夹具）→ 注入缺陷（先断言锚点全部命中）→ 断言 FAIL 断言集合**恰好新增**目标断言。
正向对照：合规夹具 rc=0 且 18 条断言全 PASS；空夹具必须点名 A0a…A0e（解析器失效，坑 46/75/98）。
"""
import hashlib
import importlib.util
import os
import shutil
import sys

TMP = r"C:/Users/laitz/AppData/Local/Temp"
SCRIPT = os.path.join(TMP, "aap-r50-spotcheck", "aap-r50-audit-log.py")
FIX = os.path.join(TMP, "aap-r50-spotcheck-fixtures")
REAL = r"E:/workspaces/hioas/hioas-aap-001"

spec = importlib.util.spec_from_file_location("r50audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILS = []
PASSES = []


def check(cond, text):
    (PASSES if cond else FAILS).append(text)
    print("  [%s] %s" % ("PASS" if cond else "FAIL", text))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def fingerprint(root):
    out = {}
    for dirpath, _d, files in os.walk(root):
        for fn in files:
            p = os.path.join(dirpath, fn)
            data = open(p, "rb").read()
            out[p] = (len(data), hashlib.md5(data).hexdigest())
    return out


def run(root):
    try:
        _n, text = mod.audit(root)
    except Exception as e:  # noqa
        return None, "EXC %s" % e
    fails = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("[FAIL ]"):
            fails.append(s[len("[FAIL ]"):].strip().split(" ")[0])   # 断言前缀（坑 82/93）
    return fails, text


def mutate(path, old, new, count=-1):
    """返回未命中的锚点数（坑 66/94：注入必须真的改到源码）。"""
    if not os.path.isfile(path):
        return 1
    raw = open(path, encoding="utf-8", errors="replace").read()
    n = raw.count(old)
    if n == 0 or (count > 0 and n < count):
        return 1
    raw2 = raw.replace(old, new) if count <= 0 else raw.replace(old, new, count)
    if raw2 == raw:
        return 1
    write(path, raw2)
    return 0


# --------------------------------------------------------------- 夹具构造
DDL = """create table if not exists aap_audit_log (
    id              bigint primary key,
    trace_id        varchar(64),
    action          varchar(64) not null,
    summary         varchar(500),
    result          varchar(16),
    risk_level      varchar(16) not null default 'NORMAL',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    created_by      bigint,
    updated_by      bigint,
    deleted         boolean not null default false,
    version         int not null default 0
);
"""

SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "audit-log",
  "properties": {
    "id": {"type": ["string", "null"]},
    "trace_id": {"type": ["string", "null"]},
    "action": {"type": "string", "enum": ["CREDENTIAL_REVEAL", "DETECTION_RELEASE"]},
    "summary": {"type": ["string", "null"]},
    "result": {"type": ["string", "null"]},
    "risk_level": {"type": ["string", "null"]},
    "created_at": {"type": ["string", "null"], "format": "date-time"}
  },
  "type": "object",
  "additionalProperties": true
}
"""

BASE_ENTITY = """package com.hioas.aap.common;

public abstract class BaseEntity {
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

ENTITY = """package com.hioas.aap.support;

@Table(value = "aap_audit_log", onInsert = AuditListeners.Insert.class)
public class AuditLogEntity extends BaseEntity {
    private String traceId;
    private String action;
    private String summary;
    private String result;
    private String riskLevel;
}
"""

VIEWS = """package com.hioas.aap.support;

public final class AuditLogViews {
    public record Row(
            String id,
            @JsonProperty("trace_id") String traceId,
            String action,
            String summary,
            String result,
            @JsonProperty("risk_level") String riskLevel,
            @JsonProperty("created_at") String createdAt) {
    }
}
"""

SERVICE = """package com.hioas.aap.support;

@Service
public class AuditService {

    public void record(AuditAction action, String targetType, Long targetId, String summary) {
        AuditLogEntity entity = new AuditLogEntity();
        entity.setTraceId("t");
        entity.setAction(action.code());
        entity.setSummary(summary);
        entity.setResult("SUCCESS");
        entity.setRiskLevel("NORMAL");
        auditLogMapper.insert(entity);
    }

    public enum AuditAction {
        CREDENTIAL_REVEAL, DETECTION_RELEASE;

        public String code() {
            return name();
        }
    }
}
"""

QUERY = """package com.hioas.aap.support;

@Service
public class AuditLogQueryService {
    public Object list() {
        return jdbc.query(
                "select id, trace_id, action, summary, result, risk_level, created_at"
                        + " from aap_audit_log order by id desc limit ? offset ?",
                (rs, i) -> null, 1, 0);
    }
}
"""

CRED_CTRL = """package com.hioas.aap.credential;

@RestController
@RequestMapping("/api/v1/credentials")
public class CredentialController {

    @PostMapping("/{id}/reveal")
    public Object reveal(@PathVariable Long id) {
        return ApiEnvelope.ok(credentialService.reveal(id));
    }
}
"""

ADM_CTRL = """package com.hioas.aap.credential;

@RestController
@RequestMapping("/api/v1/admin/credentials")
public class AdminCredentialController {

    @PostMapping("/{id}/reveal")
    public Object reveal(@PathVariable Long id) {
        return ApiEnvelope.ok(credentialService.reveal(id));
    }
}
"""

DET_CTRL = """package com.hioas.aap.detection;

@RestController
@RequestMapping("/api/v1/detection-jobs")
public class DetectionController {

    @PostMapping("/{jobId}/release")
    public Object release(@PathVariable Long jobId) {
        return ApiEnvelope.ok(detectionService.release(jobId));
    }
}
"""

CRED_SVC = """package com.hioas.aap.credential;

@Service
public class CredentialService {
    public Object reveal(Long credentialId) {
        auditService.record(AuditService.AuditAction.CREDENTIAL_REVEAL, "credential", credentialId, "读取明文");
        return null;
    }
}
"""

DET_SVC = """package com.hioas.aap.detection;

@Service
public class DetectionService {
    public Object release(Long jobId) {
        auditService.record(AuditService.AuditAction.DETECTION_RELEASE, "detection_job", jobId, "人工放行");
        return null;
    }

    public Object escalate(Long jobId) {
        auditService.record(AuditService.AuditAction.DETECTION_RELEASE, "detection_job", jobId, "升级");
        return null;
    }
}
"""

MD = """# 接口清单

| ID | 方法 | 路径 | 认证 | 请求 | 响应 | 错误码 | 说明 | 来源 | 任务号 |
|---|---|---|---|---|---|---|---|---|---|
| CRED-07 | POST | `/credentials/{id}/reveal` | SUPER_ADMIN | body `{smsCode}` | `{api_key}` | E-1901 | 二次验证 + 审计（AC-30） | 真源 | T05 |
| ADM-C02 | POST | `/admin/credentials/{id}/reveal` | SUPER_ADMIN | body `{smsCode}` | `{api_key}` + 审计 | E-1901 | T14 |
| DET-06 | POST | `/detection-jobs/{jobId}/release` | ✅ 管理端 | body `{override_reason}` | `DetectionJob` | E-1601 | R-47a 理由必填；审计 | 真源 | T06 |
| CRED-01 | GET | `/credentials` | ✅ | q：分页 | `Credential` | - | 列表 | 真源 | T05 |
"""

ER = """# ER

| 50 | `aap_audit_log` | support | 审计（append-only，四类操作必录 R-47） | ✅ |

| C8 | 审计不可变 | 仅 INSERT/SELECT；`updated_at` 不更新 |
"""


def build_fixture():
    if os.path.isdir(FIX):
        shutil.rmtree(FIX, ignore_errors=True)
    write(os.path.join(FIX, "aap-server/src/main/resources/db/migration/V1__baseline.sql"), DDL)
    write(os.path.join(FIX, "docs/backend/json-schema/models/audit-log.schema.json"), SCHEMA)
    write(os.path.join(FIX, "docs/backend/01-ER数据模型.md"), ER)
    write(os.path.join(FIX, "docs/backend/02-API接口模型清单.md"), MD)
    j = os.path.join(FIX, "aap-server/src/main/java/com/hioas/aap")
    write(os.path.join(j, "common/BaseEntity.java"), BASE_ENTITY)
    write(os.path.join(j, "support/AuditLogEntity.java"), ENTITY)
    write(os.path.join(j, "support/AuditLogViews.java"), VIEWS)
    write(os.path.join(j, "support/AuditService.java"), SERVICE)
    write(os.path.join(j, "support/AuditLogQueryService.java"), QUERY)
    write(os.path.join(j, "credential/CredentialController.java"), CRED_CTRL)
    write(os.path.join(j, "credential/AdminCredentialController.java"), ADM_CTRL)
    write(os.path.join(j, "credential/CredentialService.java"), CRED_SVC)
    write(os.path.join(j, "detection/DetectionController.java"), DET_CTRL)
    write(os.path.join(j, "detection/DetectionService.java"), DET_SVC)


def p(*parts):
    return os.path.join(FIX, *parts)


SCHEMA_P = p("docs/backend/json-schema/models/audit-log.schema.json")
DDL_P = p("aap-server/src/main/resources/db/migration/V1__baseline.sql")
ENTITY_P = p("aap-server/src/main/java/com/hioas/aap/support/AuditLogEntity.java")
SERVICE_P = p("aap-server/src/main/java/com/hioas/aap/support/AuditService.java")
QUERY_P = p("aap-server/src/main/java/com/hioas/aap/support/AuditLogQueryService.java")
DET_SVC_P = p("aap-server/src/main/java/com/hioas/aap/detection/DetectionService.java")

CASES = [
    ("C2", "schema 多一个属性 → A1（schema↔视图 1:1）",
     [(SCHEMA_P, '"created_at": {"type": ["string", "null"], "format": "date-time"}',
       '"created_at": {"type": ["string", "null"], "format": "date-time"},\n    "extra_field": {"type": ["string", "null"]}', -1)],
     ["A1"]),
    ("C3", "契约 enum 多一个常量 → A3（枚举集合）",
     [(SCHEMA_P, '"enum": ["CREDENTIAL_REVEAL", "DETECTION_RELEASE"]',
       '"enum": ["CREDENTIAL_REVEAL", "DETECTION_RELEASE", "SYNC_WRITE_PRICE"]', -1)],
     ["A3"]),
    ("C4", "实体多一个字段 → A2（实体↔DDL）",
     [(ENTITY_P, "    private String riskLevel;", "    private String riskLevel;\n    private String ghostField;", -1)],
     ["A2"]),
    ("C5", "对 aap_audit_log 加 UPDATE 语句 → A4（append-only）",
     [(DDL_P, "    version         int not null default 0\n);",
       "    version         int not null default 0\n);\nupdate aap_audit_log set result = 'X' where id = 1;", -1)],
     ["A4"]),
    ("C6", "两侧同时多一个孤儿 action → A6（孤儿 action）",
     [(SCHEMA_P, '"enum": ["CREDENTIAL_REVEAL", "DETECTION_RELEASE"]',
       '"enum": ["CREDENTIAL_REVEAL", "DETECTION_RELEASE", "SYNC_WRITE_PRICE"]', -1),
      (SERVICE_P, "        CREDENTIAL_REVEAL, DETECTION_RELEASE;",
       "        CREDENTIAL_REVEAL, DETECTION_RELEASE, SYNC_WRITE_PRICE;", -1)],
     ["A6"]),
    ("C7", "写入路径删掉 setTraceId → A7（声明未填充列）",
     [(SERVICE_P, '        entity.setTraceId("t");\n', "", -1)],
     ["A7"]),
    ("C8", "查询 select 加不存在列 → A5（查询列越界）",
     [(QUERY_P, '"select id, trace_id, action, summary, result, risk_level, created_at"',
       '"select id, trace_id, action, summary, result, risk_level, created_at, ghost_col"', -1)],
     ["A5"]),
    ("C9", "release() 的 action 换成另一个 → A8（语义不匹配；escalate() 仍用旧码，A6 不连带）",
     [(DET_SVC_P, "AuditService.AuditAction.DETECTION_RELEASE",
       "AuditService.AuditAction.CREDENTIAL_REVEAL", 1)],
     ["A8"]),
]


# --------------------------------------------------------------- C0/C1 正向对照
build_fixture()
before = fingerprint(FIX)
ok_fails, ok_out = run(FIX)
print("---- 合规夹具输出（前 14 行）----")
print("\n".join(ok_out.splitlines()[:14]))
print("----")
check(ok_fails == [], "C0 合规夹具：审计 FAIL 0（正向对照） — FAIL=%s" % ok_fails)
check("断言 18 条：PASS 18，FAIL 0" in ok_out,
      "C0b 合规夹具：18 条断言全 PASS（断言数正向对照，坑 46/75）")
after = fingerprint(FIX)
check(before == after, "C1 审计对夹具零写副作用（size+md5 全等）")

# --------------------------------------------------------------- 逐分支注入
for tag, desc, muts, targets in CASES:
    build_fixture()
    base_fails, _ = run(FIX)
    miss = 0
    for rel, old, new, cnt in muts:
        miss += mutate(rel, old, new, cnt)
    check(miss == 0, "%s 注入锚点全部命中（注入真的改到源码，坑 66/94） — 未命中 %d" % (tag, miss))
    new_fails, out = run(FIX)
    added = sorted(set(new_fails) - set(base_fails))
    check(added == targets, "%s %s：FAIL 集合恰好新增 %s（基线 %s → 注入后 %s）"
          % (tag, desc, targets, base_fails, new_fails))
    if tag == "C6":
        check(any("A6" in l and "SYNC_WRITE_PRICE" in l for l in out.splitlines()),
              "C6b 点名孤儿 action SYNC_WRITE_PRICE")
    if tag == "C7":
        check(any("A7" in l and "trace_id" in l for l in out.splitlines()),
              "C7b 点名未填充列 trace_id")
    if tag == "C9":
        check(any("A8" in l and "DET-06" in l and "语义不匹配" in l for l in out.splitlines()),
              "C9b 点名 DET-06 语义不匹配")

# --------------------------------------------------------------- C10 空夹具
build_fixture()
shutil.rmtree(FIX, ignore_errors=True)
os.makedirs(FIX, exist_ok=True)
empty_fails, empty_out = run(FIX)
check(empty_fails is not None and set(empty_fails) >= {"A0a", "A0b", "A0c", "A0d", "A0e"},
      "C10 空夹具：解析器失效被点名（A0a…A0e 全 FAIL） — %s" % empty_fails)
check(empty_fails is not None and "A1" in empty_fails and "A2" in empty_fails,
      "C10b 空夹具：跨源相等断言不得空转判绿（A1/A2 也 FAIL） — %s" % empty_fails)

# --------------------------------------------------------------- C11 真实仓库只读守卫
build_fixture()
targets = [os.path.join(REAL, "aap-server/src/main/java/com/hioas/aap/support/AuditService.java"),
           os.path.join(REAL, "aap-server/src/main/java/com/hioas/aap/support/AuditLogEntity.java"),
           os.path.join(REAL, "docs/backend/json-schema/models/audit-log.schema.json"),
           os.path.join(REAL, "aap-server/src/main/resources/db/migration/V1__baseline.sql")]
b2 = {q: (os.path.getsize(q), hashlib.md5(open(q, "rb").read()).hexdigest()) for q in targets}
real_fails, real_out = run(REAL)
a2 = {q: (os.path.getsize(q), hashlib.md5(open(q, "rb").read()).hexdigest()) for q in targets}
check(b2 == a2, "C11 真实仓库运行零写副作用（4 个关键文件 size+md5 全等）")
check(real_fails is not None and len(real_fails) > 0,
      "C12 真实仓库 FAIL 行数 > 0（正向对照，坑 97/98） — %s" % real_fails)
check("A6" in (real_fails or []) and "A7" in (real_fails or []),
      "C13 真实仓库的两条发现（A6 孤儿 action / A7 声明未填充列）可复现")

print()
print("自测 %d 条：PASS %d，FAIL %d" % (len(PASSES) + len(FAILS), len(PASSES), len(FAILS)))
if FAILS:
    for f in FAILS:
        print("  FAILED: %s" % f)
sys.exit(1 if FAILS else 0)
