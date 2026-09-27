#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R72 抽查「出站 HTTP 调用的安全与韧性契约」的负向自测（判别力测试）。

覆盖：① 合规夹具 rc=0 且 FAIL 0、A0a…A0e 全 PASS；② 空夹具 rc≠0 且点名全部 A0* 且无 A0* PASS；
③ 9 组注入缺陷，每组断言「锚点命中 + 新文本真的出现 + FAIL 集合**恰好**新增/减少目标断言」（坑 66/90/94/104）；
④ 夹具目录零写副作用（含不得留下 __pycache__）+ 真实仓库关键文件 md5 不变（只读守卫）。

纪律：基线变量另起名 `ok_out`（坑 93）；FAIL 断言名取 split()[1]（坑 82/93/112）；
     夹具目录与脚本目录分开（坑 106）；比对排除汇总行（坑 103）。
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

AUDIT = Path("C:/Users/laitz/AppData/Local/Temp/aap-r72-spotcheck/spotcheck-outbound-R72.py")
FIX = Path("C:/Users/laitz/AppData/Local/Temp/aap-r72-outbound-fixtures")
REAL = Path("E:/workspaces/hioas/hioas-aap-001")
FAIL_RE = re.compile(r"^\[FAIL\s*\]\s+([A-Za-z0-9]+)")
PASS_RE = re.compile(r"^\[PASS\]\s+([A-Za-z0-9]+)")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" | " + str(detail)) if detail else ""))


MAIN = "aap-server/src/main/java/com/hioas/aap"
TEST = "aap-server/src/test/java/com/hioas/aap"

ERRORCODE = """package com.hioas.aap.common;

public enum ErrorCode {
    E_1101("E-1101", 400),
    E_1501("E-1501", 502);

    private final String code;
    private final int httpStatus;

    ErrorCode(String code, int httpStatus) {
        this.code = code;
        this.httpStatus = httpStatus;
    }
}
"""

GUARD = """package com.hioas.aap.common;

public class OutboundUrlGuard {
    public String verify(String url) {
        return "host";
    }
}
"""

UPSTREAM = """package com.hioas.aap.credential;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class UpstreamProbe {

    private static final int MAX_BODY_BYTES = 10 * 1024 * 1024;
    private static final int MAX_RETRY = 2;

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();

    public ProbeResult probe(String baseUrl, String apiKey, int timeoutSeconds) {
        int attempts = 0;
        while (true) {
            attempts++;
            try {
                HttpRequest request = HttpRequest.newBuilder()
                        .timeout(Duration.ofSeconds(timeoutSeconds))
                        .GET()
                        .build();
                HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
                int status = response.statusCode();
                if (status == 401 || status == 403) {
                    return new ProbeResult(false, "E-1101");
                }
                if (attempts <= MAX_RETRY && status >= 500) {
                    continue;
                }
                return new ProbeResult(true, null);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return new ProbeResult(false, "E-1101");
            } catch (Exception e) {
                if (attempts <= MAX_RETRY) {
                    continue;
                }
                return new ProbeResult(false, "E-1101");
            }
        }
    }

    public record ProbeResult(boolean ok, String errorCode) {
    }
}
"""

CREDSVC = """package com.hioas.aap.credential;

public class CredentialService {

    private final OutboundUrlGuard urlGuard;
    private final UpstreamProbe upstreamProbe;
    private final int probeTimeoutSeconds;

    public CredentialService(OutboundUrlGuard urlGuard, UpstreamProbe upstreamProbe, int probeTimeoutSeconds) {
        this.urlGuard = urlGuard;
        this.upstreamProbe = upstreamProbe;
        this.probeTimeoutSeconds = probeTimeoutSeconds;
    }

    public String precheck(String baseUrl, String apiKey) {
        urlGuard.verify(baseUrl);
        UpstreamProbe.ProbeResult probe = upstreamProbe.probe(baseUrl, apiKey, probeTimeoutSeconds);
        return probe.errorCode();
    }
}
"""

SYNCCLIENT = """package com.hioas.aap.sync;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

public class NewApiSyncClient {

    private static final int MAX_BODY_BYTES = 1024 * 1024;
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);
    private static final Duration REQUEST_TIMEOUT = Duration.ofSeconds(10);

    private final OutboundUrlGuard outboundUrlGuard;

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(CONNECT_TIMEOUT)
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();

    public NewApiSyncClient(OutboundUrlGuard outboundUrlGuard) {
        this.outboundUrlGuard = outboundUrlGuard;
    }

    public Probe get(String baseUrl, String apiKey, String path) {
        outboundUrlGuard.verify(baseUrl);
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .timeout(REQUEST_TIMEOUT)
                .GET();
        return send(builder.build());
    }

    public Probe put(String baseUrl, String apiKey, String path, String jsonBody) {
        outboundUrlGuard.verify(baseUrl);
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .timeout(REQUEST_TIMEOUT)
                .PUT(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8));
        return send(builder.build());
    }

    private Probe send(HttpRequest request) {
        try {
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
            return new Probe(true, response.statusCode(), null, null);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return new Probe(false, 0, null, "E-1501");
        } catch (Exception e) {
            return new Probe(false, 0, null, "E-1501");
        }
    }

    public record Probe(boolean reachable, int httpStatus, String body, String errorCode) {
    }
}
"""

SYNCADMINSVC = """package com.hioas.aap.sync;

public class SyncAdminService {

    private final NewApiSyncClient newApiSyncClient;

    public SyncAdminService(NewApiSyncClient newApiSyncClient) {
        this.newApiSyncClient = newApiSyncClient;
    }

    public String retry(String baseUrl, String apiKey) {
        NewApiSyncClient.Probe probe = newApiSyncClient.get(baseUrl, apiKey, "/models");
        return probe.errorCode();
    }

    public String changeBindingStatus(String baseUrl, String apiKey) {
        NewApiSyncClient.Probe before = newApiSyncClient.get(baseUrl, apiKey, "/api/channel/1");
        NewApiSyncClient.Probe write = newApiSyncClient.put(baseUrl, apiKey, "/api/channel/", "{}");
        NewApiSyncClient.Probe after = newApiSyncClient.get(baseUrl, apiKey, "/api/channel/1");
        return before.errorCode() + write.errorCode() + after.errorCode();
    }
}
"""

TESTSTUB = """package com.hioas.aap.credential;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;

class FixtureStubTest {

    private final AtomicInteger upstreamCalls = new AtomicInteger();

    private String startUpstream(int status) throws Exception {
        HttpServer upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/v1/models", exchange -> {
            upstreamCalls.incrementAndGet();
            byte[] body = "{}".getBytes();
            exchange.sendResponseHeaders(status, body.length);
        });
        return "http://127.0.0.1:1";
    }

    void authFailureIsNotRetried() throws Exception {
        String baseUrl = startUpstream(401);
        assertThat(upstreamCalls.get()).as("401 属鉴权失败，不重试").isEqualTo(1);
        assertThat("E-1101").as("连通性失败码").isEqualTo("E-1101");
    }

    void serverErrorIsRetried() throws Exception {
        String baseUrl = startUpstream(503);
        assertThat(upstreamCalls.get()).as("5xx 重试到上限").isEqualTo(3);
        assertThat("E-1501").isEqualTo("E-1501");
    }
}
"""

PRD = """# 09 检测验证引擎PRD（夹具）

* 异步：分项并行；单项超时；网络失败重试 2 次（指数退避），鉴权失败不重试。

安全约束：SSRF 防护（专用代理、禁内网/环回/元数据、仅 http(s)、重定向≤3、响应体≤10MB）。
"""


def write_fixture(root: Path):
    files = {
        MAIN + "/common/ErrorCode.java": ERRORCODE,
        MAIN + "/common/OutboundUrlGuard.java": GUARD,
        MAIN + "/credential/UpstreamProbe.java": UPSTREAM,
        MAIN + "/credential/CredentialService.java": CREDSVC,
        MAIN + "/sync/NewApiSyncClient.java": SYNCCLIENT,
        MAIN + "/sync/SyncAdminService.java": SYNCADMINSVC,
        TEST + "/credential/FixtureStubTest.java": TESTSTUB,
        ".calicat/prd/09-检测验证引擎PRD.md": PRD,
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")


def fingerprint(root: Path):
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            b = p.read_bytes()
            out[str(p.relative_to(root))] = (len(b), hashlib.md5(b).hexdigest())
    return out


def run_audit(root: Path):
    proc = subprocess.run([sys.executable, str(AUDIT), "--root", str(root)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    text = proc.stdout.decode("utf-8", errors="replace")
    fails = {m.group(1) for ln in text.split("\n") for m in [FAIL_RE.match(ln)] if m}
    passes = {m.group(1) for ln in text.split("\n") for m in [PASS_RE.match(ln)] if m}
    return proc.returncode, text, fails, passes


def mutate(path: Path, old: str, new: str, count: int = -1):
    """返回未命中的锚点列表；并断言新文本真的出现（坑 66/94）。"""
    text = path.read_text(encoding="utf-8")
    if count < 0:
        n = text.count(old)
    else:
        n = count
    if n == 0:
        return [old]
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")
    if new not in path.read_text(encoding="utf-8"):
        return [old + "（新文本未出现）"]
    return []


def reset_fixture():
    if FIX.exists():
        shutil.rmtree(FIX, ignore_errors=True)
    write_fixture(FIX)


# ------------------------------------------------------------------ ① 合规夹具
reset_fixture()
before_fix = fingerprint(FIX)
real_before = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in (
    REAL / "aap-server/src/main/java/com/hioas/aap/credential/UpstreamProbe.java",
    REAL / "aap-server/src/main/java/com/hioas/aap/sync/NewApiSyncClient.java",
    REAL / ".agents/state/evidence/audit-regression-R72.txt")}
rc, out, fails, passes = run_audit(FIX)
ok_out, ok_fails, ok_passes = out, fails, passes
check("T1 合规夹具 rc=0", rc == 0, "rc=%d FAIL=%s" % (rc, sorted(fails)))
check("T2 合规夹具 FAIL 明细为空", not fails, str(sorted(fails)))
for a in ("A0a", "A0b", "A0c", "A0d", "A0e"):
    check("T3 合规夹具正向对照 %s PASS" % a, a in passes, sorted(passes))

# ------------------------------------------------------------------ ② 空夹具
EMPTY = Path("C:/Users/laitz/AppData/Local/Temp/aap-r72-outbound-fixtures-empty")
if EMPTY.exists():
    shutil.rmtree(EMPTY, ignore_errors=True)
EMPTY.mkdir(parents=True, exist_ok=True)
rc_e, out_e, fails_e, passes_e = run_audit(EMPTY)
check("T4 空夹具 rc≠0", rc_e != 0, "rc=%d" % rc_e)
for a in ("A0a", "A0b", "A0c", "A0d", "A0e"):
    check("T5 空夹具点名 %s（判定不可用）" % a, a in fails_e, sorted(fails_e))
check("T6 空夹具无任何 A0* PASS", not any(p.startswith("A0") for p in passes_e), sorted(passes_e))

# ------------------------------------------------------------------ ③ 注入缺陷（判别力）
INJECTIONS = [
    ("I1 去掉全部 SSRF 守卫", [("credential/CredentialService.java", "urlGuard.verify(baseUrl);", "// guard removed"),
                               ("sync/NewApiSyncClient.java", "outboundUrlGuard.verify(baseUrl);", "// guard removed")],
     {"A1"}, set()),
    ("I2 去掉重试次数上限", [("credential/UpstreamProbe.java", "attempts <= MAX_RETRY", "attempts > 0")], {"A3"}, set()),
    ("I3 去掉 401/403 不重试守卫", [("credential/UpstreamProbe.java", "status == 401 || status == 403", "status == 0")],
     {"A3b"}, set()),
    ("I4 响应体上限放大到 20MiB", [("credential/UpstreamProbe.java", "10 * 1024 * 1024", "20 * 1024 * 1024")], {"A4"}, set()),
    ("I5 改回全量读入（ofByteArray）", [("credential/UpstreamProbe.java", "BodyHandlers.ofInputStream()", "BodyHandlers.ofByteArray()"),
                                        ("sync/NewApiSyncClient.java", "BodyHandlers.ofInputStream()", "BodyHandlers.ofByteArray()")],
     {"A4b"}, set()),
    ("I6 改回跟随重定向（NORMAL）", [("credential/UpstreamProbe.java", "Redirect.NEVER", "Redirect.NORMAL"),
                                     ("sync/NewApiSyncClient.java", "Redirect.NEVER", "Redirect.NORMAL")],
     {"A5", "A5b"}, set()),
    ("I7 去掉中断标志恢复", [("credential/UpstreamProbe.java", "Thread.currentThread().interrupt();", "// no interrupt")],
     {"A7"}, set()),
    ("I8 去掉请求级超时", [("credential/UpstreamProbe.java", ".timeout(Duration.ofSeconds(timeoutSeconds))", "// no timeout")],
     {"A2"}, set()),
    ("I9 去掉 5xx 桩（重试路径零背书）", [("test/credential/FixtureStubTest.java", "startUpstream(503)", "startUpstream(200)")],
     {"A8c"}, set()),
]

for label, edits, add_fails, drop_fails in INJECTIONS:
    reset_fixture()
    unmatched = []
    for rel, old, new in edits:
        parts = rel.split("/")
        if parts[0] == "test":
            target = FIX / TEST / "/".join(parts[1:])
        else:
            target = FIX / MAIN / rel
        unmatched += mutate(target, old, new)
    check("T7 %s：全部锚点命中且新文本真的出现" % label, not unmatched, str(unmatched))
    rc_i, out_i, fails_i, passes_i = run_audit(FIX)
    delta_new = sorted(fails_i - ok_fails)
    delta_gone = sorted(ok_fails - fails_i)
    check("T8 %s：FAIL 集合恰好新增 %s" % (label, sorted(add_fails)),
          delta_new == sorted(add_fails) and delta_gone == sorted(drop_fails),
          "新增=%s 减少=%s" % (delta_new, delta_gone))

# ------------------------------------------------------------------ ④ 零写副作用
reset_fixture()
before_fix = fingerprint(FIX)
run_audit(FIX)
after_fix = fingerprint(FIX)
check("T9 夹具目录零写副作用（审计运行不改夹具）", before_fix == after_fix,
      str([k for k in set(before_fix) | set(after_fix) if before_fix.get(k) != after_fix.get(k)]))
check("T10 夹具目录无 __pycache__ 残留", not list(FIX.rglob("__pycache__")))
real_after = {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in (
    REAL / "aap-server/src/main/java/com/hioas/aap/credential/UpstreamProbe.java",
    REAL / "aap-server/src/main/java/com/hioas/aap/sync/NewApiSyncClient.java",
    REAL / ".agents/state/evidence/audit-regression-R72.txt")}
check("T11 真实仓库关键文件 md5 不变（只读守卫）", real_before == real_after)
rc_real, out_real, real_fails, real_passes = run_audit(REAL)
check("T12 真实仓库 FAIL 集合非空（审计在真实仓库上确实报出漂移，坑 46/98）",
      bool(real_fails) and {"A5b", "A4b"} <= real_fails, "rc=%d FAIL=%s" % (rc_real, sorted(real_fails)))

bad = [n for n, c, _ in results if not c]
print("")
print("自测 %d 条：PASS %d，FAIL %d" % (len(results), len(results) - len(bad), len(bad)))
if bad:
    print("失败项：" + ", ".join(bad))
sys.exit(1 if bad else 0)
