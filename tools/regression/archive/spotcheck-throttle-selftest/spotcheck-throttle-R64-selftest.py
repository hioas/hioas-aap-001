#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R64 抽查脚本的负向自测：合规夹具必须全绿、空夹具必须点名全部解析器正向对照、
每组注入缺陷必须**恰好**新增目标断言（且注入真的改到源码，坑 66/90/94）、
真实仓库只读（关键文件 md5 不变）+ 夹具目录零写副作用。

纪律：基线变量用 ok_out 专用名（坑 93）；FAIL token 取 split()[1]（坑 112-③）；
「恰好新增」用集合差并只比明细行（坑 82/103）。
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("C:/Users/laitz/AppData/Local/Temp/aap-r64-spotcheck/spotcheck-throttle-R64.py")
BASE = Path("C:/Users/laitz/AppData/Local/Temp/aap-r64-spotcheck-fixtures")
REAL = Path("E:/workspaces/hioas/hioas-aap-001")
PY = sys.executable

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run(root):
    p = subprocess.run([PY, str(SCRIPT), "--root", str(root), "--tokens"],
                       capture_output=True, text=True)
    toks = [t for t in p.stdout.split() if t.startswith("A") and t[1:2].isdigit()]
    return p.returncode, set(toks)


def w(dest, rel, text):
    p = Path(dest) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


MD = """# 夹具清单

## 0. 通用约定

| 项 | 约定 |
|---|---|
| 前缀 | `/api/v1` |

### 1.1 Auth

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| AUTH-01 | POST | `/auth/sms/send` | 免 | body `{phone, captcha}` | `{ttl:300}` | E-1001 E-1903 | 60s 频控（R-02） | 真源 | T03 |
| AUTH-02 | POST | `/auth/sms/login` | 免 | body `{phone, smsCode}` | `LoginResult{token,role}` | E-1001 E-1101 | 5 次错锁 15 分钟 | 真源 | T03 |

### 1.2 Detection

| ID | 方法 | 路径 | 鉴权 | 请求 | 响应 | 错误码 | 幂等/并发 | 依据 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| DET-01 | POST | `/detection-jobs` | ✅ | body `{credential_id}` | `{job_id,status}` | E-1301 E-1302 | C2 互斥；日配额 5 次（R-09） | 真源 | T06 |

### 3.1 Sync（管理端）

| ID | 方法 | 路径 | 角色 | 请求/响应 | 错误码 | 状态 |
|---|---|---|---|---|---|---|
| ADM-S03 | POST | `/admin/sync/tasks/{taskId}/retry` | TECH_OPS | → `SyncTask`（≤5 次退避 30s/2m/8m/30m） | E-1501 E-1505 | T14 |

## 4. 错误码

| 码 | HTTP | 场景 | 依据 |
|---|---|---|---|
| `0` | 200 | 成功 | |
| `E-1302` | 429 | 供应商日配额用尽（5 次） | R-09 |
| `E-1501` | 502 | 同步失败 | |
| `E-1903` | 429 | 限流（短信 60s 频控等） | |
"""

PRD = """# spec

关键规则：R-02 验证码 6 位 300s 60s 频控 5 次锁 15 分钟；R-09 供应商日配额 5 次；
R-40 同步重试 30s/2m/8m/30m ≤5 次；R-47 审计强制。
"""

YML = """app:
  sms:
    ttl-seconds: 300
    resend-interval-seconds: 60
    max-attempts: 5
    lock-minutes: 15
    expose-code: false
  detection:
    daily-quota: 5
    pass-score: 70
"""

SM_SVC = """package com.hioas.aap.iam;

class SmsService {
    private final Object config;

    public Object send(String phone, String clientIp) {
        if (latest.getLockedUntil() != null && latest.getLockedUntil().isAfter(now)) {
            throw new ApiException(ErrorCode.E_1903, "尝试过于频繁，请稍后再试");
        }
        if (latest.getSentAt().plusSeconds(config.resendIntervalSeconds()).isAfter(now)) {
            throw new ApiException(ErrorCode.E_1903, "验证码发送过于频繁，请稍后重试");
        }
        entity.setExpireAt(now.plusSeconds(config.ttlSeconds()));
        return new SentCode(config.ttlSeconds(), entity.getExpireAt(), config.exposeCode() ? code : null);
    }

    public void verify(String phone, String code) {
        if (record.getLockedUntil() != null && record.getLockedUntil().isAfter(now)) {
            throw new ApiException(ErrorCode.E_1903, "验证码错误次数过多，请稍后再试");
        }
        int attempts = (record.getAttemptCount() == null ? 0 : record.getAttemptCount()) + 1;
        boolean lock = attempts >= config.maxAttempts();
        OffsetDateTime lockedUntil = lock ? now.plusMinutes(config.lockMinutes()) : null;
    }
}
"""

DET_SVC = """package com.hioas.aap.detection;

class DetectionService {
    private final int dailyQuota;

    public DetectionService(@Value("${app.detection.daily-quota:5}") int dailyQuota) {
        this.dailyQuota = dailyQuota;
    }

    private void ensureDailyQuota(Long providerId) {
        long today = jobMapper.selectCountByQuery(q);
        if (today >= dailyQuota) {
            throw new ApiException(ErrorCode.E_1302, "今日检测配额已用尽（上限 " + dailyQuota + " 次）");
        }
    }
}
"""

SYNC_SVC = """package com.hioas.aap.sync;

class SyncAdminService {
    /** 重试上限（PRD §5：1 次立即 + 30s/2m/8m/30m）。 */
    private static final int MAX_ATTEMPTS = 5;

    private static final Duration[] BACKOFF = {
            Duration.ofSeconds(30), Duration.ofMinutes(2), Duration.ofMinutes(8), Duration.ofMinutes(30)};

    public Object retry(Long taskId) {
        int attempt = before.attemptCount() + 1;
        if (attempt > MAX_ATTEMPTS) {
            throw new ApiException(ErrorCode.E_1601, "重试次数已达上限");
        }
        boolean exhausted = attempt >= MAX_ATTEMPTS;
        OffsetDateTime nextRetryAt = exhausted ? null : OffsetDateTime.now(ZoneOffset.UTC).plus(BACKOFF[attempt - 1]);
        return nextRetryAt;
    }
}
"""

ERRCODE = """package com.hioas.aap.common;

public enum ErrorCode {
    E_1302("E-1302", 429, "今日检测配额已用尽"),
    E_1501("E-1501", 502, "同步失败"),
    E_1601("E-1601", 409, "状态非法流转"),
    E_1903("E-1903", 429, "请求过于频繁");
}
"""

T_AUTH = """package com.hioas.aap.iam;

class AuthContractTest {
    void resendWithinSixtySecondsIsThrottled() {
        HttpResult again = post("/auth/sms/send", body);
        assertThat(again.status()).isEqualTo(429);
        assertThat(again.code()).isEqualTo("E-1903");
    }

    void sendReturnsTtl() {
        HttpResult res = post("/auth/sms/send", body);
        assertThat(res.data().path("ttl").asInt()).isEqualTo(300);
    }

    void windowIsSixtySeconds() {
        assertThat(record.getSentAt().plusSeconds(60)).isAfter(now);
    }

    void fiveWrongCodesLockThePhone() {
        for (int i = 1; i <= 5; i++) {
            HttpResult res = login(PHONE, wrong);
            assertThat(res.status()).isEqualTo(400);
        }
        HttpResult locked = login(PHONE, code);
        assertThat(locked.status()).isEqualTo(429);
        assertThat(locked.code()).isEqualTo("E-1903");
        assertThat(rec.getLockedUntil()).isEqualTo(now.plusMinutes(15));
    }
}
"""

T_DET = """package com.hioas.aap.detection;

class DetectionContractTest {
    void dailyQuotaEnforced() {
        for (int i = 0; i < 5; i++) {
            jdbc.update("insert into aap_detection_job ...");
        }
        HttpResult res = post("/detection-jobs", body, token);
        assertThat(res.status()).isEqualTo(429);
        assertThat(res.code()).isEqualTo("E-1302");
    }
}
"""

T_SYNC = """package com.hioas.aap.sync;

class SyncAdminContractTest {
    void retryBackoffScheduleAndExhaustion() {
        long[] expectedSeconds = {30L, 120L, 480L, 1800L};
        for (int attempt = 1; attempt <= 4; attempt++) {
            assertThat(secondsUntil(taskNextRetry(820002L)))
                    .isBetween(expectedSeconds[attempt - 1] - 15, expectedSeconds[attempt - 1] + 30);
        }
    }
}
"""

CLIENT = """export function http<T>(path: string) {
  return new Promise<T>((resolve, reject) => {
    const status = 0
    if (status === 401) {
      refreshToken()
    }
    if (status === 429) {
      reject(new ApiError(body?.code, body?.message))
    }
    if (status >= 400) {
      reject(new ApiError(body?.code || 'E-2001', body?.message))
    }
  })
}
"""

FILES = [
    ("docs/backend/02-API接口模型清单.md", MD),
    (".calicat/prd/17-零歧义执行规格spec.md", PRD),
    ("aap-server/src/main/resources/application.yml", YML),
    ("aap-server/src/main/java/com/hioas/aap/config/AppProperties.java",
     "package com.hioas.aap.config;\n\npublic class AppProperties {\n"
     "    public record Sms(int ttlSeconds, int resendIntervalSeconds, int maxAttempts, int lockMinutes, boolean exposeCode) {}\n"
     "    public record Detection(int dailyQuota, int passScore, int vetoScore) {}\n}\n"),
    ("aap-server/src/main/java/com/hioas/aap/iam/SmsService.java", SM_SVC),
    ("aap-server/src/main/java/com/hioas/aap/detection/DetectionService.java", DET_SVC),
    ("aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java", SYNC_SVC),
    ("aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java", ERRCODE),
    ("aap-server/src/test/java/com/hioas/aap/iam/AuthContractTest.java", T_AUTH),
    ("aap-server/src/test/java/com/hioas/aap/detection/DetectionContractTest.java", T_DET),
    ("aap-server/src/test/java/com/hioas/aap/sync/SyncAdminContractTest.java", T_SYNC),
    ("aap-client/src/api/http.ts", CLIENT),
]


def build(dest):
    d = Path(dest)
    if d.exists():
        shutil.rmtree(d)
    for rel, text in FILES:
        w(d, rel, text)
    return d


def snapshot(root):
    root = Path(root)
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def mutate(path, old, new, all_occ=False):
    """返回 (命中?, 注入后新文本真的出现了?)。未命中即空转通过（坑 66/90/94）。"""
    p = Path(path)
    t = p.read_text(encoding="utf-8")
    if old not in t:
        return False, False
    t2 = t.replace(old, new) if all_occ else t.replace(old, new, 1)
    p.write_text(t2, encoding="utf-8", newline="\n")
    return True, new in t2


# ---------------------------------------------------------------- 1) 合规夹具
BASE.mkdir(parents=True, exist_ok=True)
fix = build(BASE / "compliant")
before_fix = snapshot(fix)
rc, ok_out = run(fix)
after_fix = snapshot(fix)
check("合规夹具 rc=0", rc == 0, "rc=%d" % rc)
check("合规夹具 FAIL 0", not ok_out, "FAIL=%s" % sorted(ok_out))
check("合规夹具零写副作用", before_fix == after_fix,
      "新增/消失=%s" % sorted(set(before_fix) ^ set(after_fix)))
check("夹具目录无 __pycache__", not any("__pycache__" in f for f in after_fix))

# ---------------------------------------------------------------- 2) 正向对照（合规夹具下 A0a…A0i 必须全 PASS）
p = subprocess.run([PY, str(SCRIPT), "--root", str(fix)], capture_output=True, text=True)
a0 = [ln for ln in p.stdout.splitlines() if ln.startswith("[PASS] A0")]
check("合规夹具下 A0a…A0i 九条正向对照全 PASS", len(a0) == 9, "命中 %d 条" % len(a0))

# ---------------------------------------------------------------- 3) 空夹具必须变红并点名全部正向对照
empty = BASE / "empty"
if empty.exists():
    shutil.rmtree(empty)
empty.mkdir(parents=True)
rc_e, tok_e = run(empty)
need = {"A0a", "A0b", "A0c", "A0d", "A0e", "A0f", "A0g", "A0h", "A0i"}
check("空夹具 rc≠0", rc_e != 0, "rc=%d" % rc_e)
check("空夹具点名全部 A0* 正向对照", need <= tok_e, "缺失=%s" % sorted(need - tok_e))
check("空夹具点名条件化断言（A3a/A3b/A4a/A5/A6）",
      {"A3a", "A3b", "A4a", "A5", "A6"} <= tok_e, "缺失=%s" % sorted({"A3a", "A3b", "A4a", "A5", "A6"} - tok_e))

# ---------------------------------------------------------------- 4) 注入缺陷判别力
INJ = [
    ("yml-60-90", [("aap-server/src/main/resources/application.yml",
                    "resend-interval-seconds: 60", "resend-interval-seconds: 90")], {"A1"}),
    ("yml-quota-5-3", [("aap-server/src/main/resources/application.yml",
                        "daily-quota: 5", "daily-quota: 3")], {"A2"}),
    ("impl-backoff-8m-10m", [("aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java",
                              "Duration.ofMinutes(8)", "Duration.ofMinutes(10)")], {"A3a", "A3c"}),
    ("impl-backoff-append-2h", [("aap-server/src/main/java/com/hioas/aap/sync/SyncAdminService.java",
                                 "Duration.ofMinutes(30)};", "Duration.ofMinutes(30), Duration.ofHours(2)};")],
     {"A3a", "A3c"}),
    ("md-window-60-90", [("docs/backend/02-API接口模型清单.md",
                          "60s 频控（R-02）", "90s 频控（R-02）")], {"A1"}),
    ("md-del-sync-row", [("docs/backend/02-API接口模型清单.md",
                          "| ADM-S03 | POST | `/admin/sync/tasks/{taskId}/retry` | TECH_OPS | → `SyncTask`（≤5 次退避 30s/2m/8m/30m） | E-1501 E-1505 | T14 |\n",
                          "")], {"A0c", "A3a", "A3b"}),
    ("prd-8m-10m", [(".calicat/prd/17-零歧义执行规格spec.md",
                     "R-40 同步重试 30s/2m/8m/30m ≤5 次", "R-40 同步重试 30s/2m/10m/30m ≤5 次")], {"A3b"}),
    ("test-del-ttl", [("aap-server/src/test/java/com/hioas/aap/iam/AuthContractTest.java",
                       'assertThat(res.data().path("ttl").asInt()).isEqualTo(300);', "")], {"A4a"}),
    ("test-del-window60", [("aap-server/src/test/java/com/hioas/aap/iam/AuthContractTest.java",
                            "assertThat(record.getSentAt().plusSeconds(60)).isAfter(now);", "")], {"A4b"}),
    ("test-del-lock15", [("aap-server/src/test/java/com/hioas/aap/iam/AuthContractTest.java",
                          "assertThat(rec.getLockedUntil()).isEqualTo(now.plusMinutes(15));", "")], {"A4c"}),
    ("test-del-quota-loop", [("aap-server/src/test/java/com/hioas/aap/detection/DetectionContractTest.java",
                              "for (int i = 0; i < 5; i++) {", "for (int i = 0; i < 4; i++) {")], {"A4d"}),
    ("test-del-backoff-exp", [("aap-server/src/test/java/com/hioas/aap/sync/SyncAdminContractTest.java",
                               "long[] expectedSeconds = {30L, 120L, 480L, 1800L};",
                               "long[] expectedSeconds = {};")], {"A3c", "A4e"}),
    ("impl-hardcoded-15min", [("aap-server/src/main/java/com/hioas/aap/iam/SmsService.java",
                               '"验证码错误次数过多，请稍后再试"', '"验证码错误次数过多，请 15 分钟后再试"')], {"A5"}),
    ("client-del-429", [("aap-client/src/api/http.ts",
                         "if (status === 429) {\n      reject(new ApiError(body?.code, body?.message))\n    }\n", "")],
     {"A6"}),
    ("errcode-429-403", [("aap-server/src/main/java/com/hioas/aap/common/ErrorCode.java",
                          'E_1903("E-1903", 429,', 'E_1903("E-1903", 403,')], {"A7"}),
    ("md-del-429-rows", [("docs/backend/02-API接口模型清单.md",
                          "| `E-1903` | 429 | 限流（短信 60s 频控等） | |\n", ""),
                         ("docs/backend/02-API接口模型清单.md",
                          "| `E-1302` | 429 | 供应商日配额用尽（5 次） | R-09 |\n", "")], {"A0f", "A7"}),
]

missed = []
for name, muts, expect in INJ:
    d = build(BASE / ("inj-" + name))
    okmut = True
    for rel, old, new in muts:
        hit, changed = mutate(d / rel, old, new)
        if not hit:
            missed.append("%s@%s(锚点未命中)" % (name, rel))
            okmut = False
        elif not changed:
            missed.append("%s@%s(注入后新文本未出现)" % (name, rel))
            okmut = False
    if not okmut:
        continue
    rc_i, tok_i = run(d)
    delta = set(tok_i) - set(ok_out)
    check("注入 %s → 恰好新增 %s" % (name, sorted(expect)), delta == set(expect),
          "rc=%d 实际新增=%s 期望=%s" % (rc_i, sorted(delta), sorted(expect)))
check("全部注入锚点命中且真的改到源码（坑 66/90/94）", not missed, "未命中=%s" % missed)

# ---------------------------------------------------------------- 5) 真实仓库只读
KEY = [REAL / rel for rel, _ in FILES] + [REAL / "tools/gen-backend-models.py"]
before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in KEY if p.exists()}
rc_r, tok_r = run(REAL)
after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in KEY if p.exists()}
check("真实仓库关键文件 md5 不变（只读）", before == after,
      "变化=%s" % sorted(k for k in before if before[k] != after.get(k)))
check("真实仓库 FAIL 集合 = {A3a,A3b,A4a,A4b,A4c,A5,A6}",
      tok_r == {"A3a", "A3b", "A4a", "A4b", "A4c", "A5", "A6"}, "实际=%s" % sorted(tok_r))

# ---------------------------------------------------------------- 汇总
print("== R64 抽查负向自测（spotcheck-throttle-R64-selftest） ==")
for name, okv, detail in results:
    print("%s %s%s" % ("[PASS]" if okv else "[FAIL]", name, (" | " + detail) if detail and not okv else ""))
bad = [r for r in results if not r[1]]
print("")
print("SELFTEST PASS %d/%d" % (len(results) - len(bad), len(results)))
if bad:
    print("失败项：%s" % [b[0] for b in bad])
sys.exit(1 if bad else 0)
