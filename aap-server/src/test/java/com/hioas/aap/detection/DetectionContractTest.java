package com.hioas.aap.detection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.hioas.aap.detection.ProbeScoring.ProbeScore;
import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T06 · 检测任务验收（接口 DET-01…06；AC-13/19/20/47）。
 *
 * <p>打分公式与结论判定由 {@code ProbeScoringTest}（纯函数）覆盖；本类覆盖任务生命周期、
 * 权限归属、互斥/配额/状态流转，以及「引擎回写结果 → 详情/逐项结果」的闭环。
 */
class DetectionContractTest extends ApiTestBase {

    private static final String PHONE = "13800000020";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    @Autowired
    private DetectionService detectionService;

    private HttpServer upstream;

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    private String startUpstream() throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/v1/models", exchange -> {
            byte[] body = "{\"data\":[{\"id\":\"gpt-4o\"}]}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        upstream.start();
        return "http://127.0.0.1:" + upstream.getAddress().getPort() + "/v1";
    }

    private String token(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    private String techOpsToken() {
        Long accountId = 910001L;
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'techops', 'x', '技术运营', 'TECH_OPS', 'ACTIVE')
                """, accountId);
        var issued = jwtService.issueAccessToken(accountId, "TECH_OPS", "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    /** 建一个已预检通过（ACTIVE）的凭证，返回 credentialId。 */
    private String activeCredential(String token) throws Exception {
        HttpResult created = post("/credentials", """
                {
                  "alias":"检测凭证","base_url":"%s","api_key":"sk-detect-1111222233334444",
                  "primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(startUpstream()), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String credentialId = created.data().path("id").asText();
        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(precheck.status()).as(precheck.body()).isEqualTo(200);
        return credentialId;
    }

    private static List<ProbeScore> passingScores() {
        return List.of(
                ProbeScoring.scoreTtft(List.of(200, 200, 200)),
                ProbeScoring.scoreThroughput(80),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 90.0, "tokenizer", 90.0,
                        "self_awareness", 90.0, "probability", 90.0, "context", 90.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA"));
    }

    @Test
    @DisplayName("DET-01/02 重测：取消进行中的任务后可新建；详情返回进度字段")
    void createAndQueryJob() throws Exception {
        String token = token(PHONE);
        String credentialId = activeCredential(token);

        // 预检建的任务先取消，否则触发互斥
        String firstJobId = jdbc.queryForObject("select id from aap_detection_job order by id desc limit 1", String.class);
        HttpResult cancelled = post("/detection-jobs/" + firstJobId + "/cancel", null, token);
        assertThat(cancelled.status()).as(cancelled.body()).isEqualTo(200);
        assertThat(cancelled.data().path("status").asText()).isEqualTo("CANCELLED");

        HttpResult created = post("/detection-jobs", """
                {"credential_id":"%s","trigger_type":"MANUAL"}
                """.formatted(credentialId), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        SchemaAssert.assertModel("job-created", json(created.data()));
        String jobId = created.data().path("job_id").asText();
        assertThat(created.data().path("status").asText()).isEqualTo("QUEUED");

        HttpResult detail = get("/detection-jobs/" + jobId, token);
        assertThat(detail.status()).isEqualTo(200);
        SchemaAssert.assertModel("detection-job", json(detail.data()));
        assertThat(detail.data().path("progress").path("total").asInt()).isEqualTo(8);
        assertThat(detail.data().path("progress").path("percent").asInt()).isZero();
        assertThat(detail.data().path("trigger_type").asText()).isEqualTo("MANUAL");

        // DET-04 未产出结果时单项查询 → 404
        HttpResult missingResult = get("/detection-jobs/" + jobId + "/results/D1", token);
        assertThat(missingResult.status()).isEqualTo(404);
        assertThat(missingResult.code()).isEqualTo("E-1304");
    }

    @Test
    @DisplayName("AC-13 互斥：同凭证已有活跃任务 → 409 E-1301（预检已建任务时再建）")
    void activeJobBlocksNewOne() throws Exception {
        String token = token(PHONE);
        String credentialId = activeCredential(token);

        HttpResult again = post("/detection-jobs", """
                {"credential_id":"%s"}
                """.formatted(credentialId), token);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1301");
    }

    @Test
    @DisplayName("R-09 配额：当日已达上限 → 429 E-1302")
    void dailyQuotaEnforced() throws Exception {
        String token = token(PHONE);
        String credentialId = activeCredential(token);
        Long providerId = jdbc.queryForObject("select provider_id from aap_credential where id = ?::bigint",
                Long.class, credentialId);
        // 先取消预检建的任务（否则先撞互斥 E-1301，测不到配额）
        jdbc.update("update aap_detection_job set active_flag = false, status = 'CANCELLED' where active_flag = true");
        // 直接造 5 条当日任务，把配额用尽
        for (int i = 0; i < 5; i++) {
            jdbc.update("""
                    insert into aap_detection_job (id, job_no, provider_id, credential_id, trigger_type, status,
                                                   active_flag, created_at, updated_at)
                    values (?, ?, ?, ?::bigint, 'MANUAL', 'COMPLETED', false, now(), now())
                    """, 800000L + i, "DJ-QUOTA-" + i, providerId, credentialId);
        }
        HttpResult res = post("/detection-jobs", """
                {"credential_id":"%s","trigger_type":"MANUAL"}
                """.formatted(credentialId), token);
        assertThat(res.status()).isEqualTo(429);
        assertThat(res.code()).isEqualTo("E-1302");
    }

    @Test
    @DisplayName("E-1303：凭证未通过预检时不可发起检测")
    void inactiveCredentialRejected() {
        String token = token(PHONE);
        HttpResult created = post("/credentials", """
                {"alias":"未预检","base_url":"https://api.example.com/v1","api_key":"sk-not-active-1234"}
                """, token);
        String credentialId = created.data().path("id").asText();

        HttpResult res = post("/detection-jobs", """
                {"credential_id":"%s"}
                """.formatted(credentialId), token);
        assertThat(res.status()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1303");
    }

    @Test
    @DisplayName("AC-47 状态流转：已结束任务不可取消（409 E-1305），非法回写被拒（E-1601）")
    void stateMachineGuardsEndedJobs() throws Exception {
        String token = token(PHONE);
        activeCredential(token);
        Long jobId = jdbc.queryForObject("select id from aap_detection_job order by id desc limit 1", Long.class);

        assertThat(post("/detection-jobs/" + jobId + "/cancel", null, token).status()).isEqualTo(200);
        HttpResult again = post("/detection-jobs/" + jobId + "/cancel", null, token);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1305");

        assertThatThrownBy(() -> detectionService.recordProbeResults(jobId, passingScores(), Map.of(), Map.of()))
                .isInstanceOf(com.hioas.aap.common.ApiException.class)
                .hasMessageContaining("已结束");
    }

    @Test
    @DisplayName("引擎回写 → 任务详情/逐项结果闭环；总分与结论回写凭证（detection_status=PASS）")
    void engineCallbackCompletesJob() throws Exception {
        String token = token(PHONE);
        String credentialId = activeCredential(token);
        Long jobId = jdbc.queryForObject("select id from aap_detection_job order by id desc limit 1", Long.class);

        detectionService.recordProbeResults(jobId, passingScores(),
                Map.of("D1", Map.of("p50_ms", 200), "D7", Map.of("behavior_similarity", 0.93)),
                Map.of("D1", "样本 10 次，p50=200ms", "D8", "TLS issuer=TestCA"));

        HttpResult detail = get("/detection-jobs/" + jobId, token);
        assertThat(detail.status()).isEqualTo(200);
        SchemaAssert.assertModel("detection-job", json(detail.data()));
        assertThat(detail.data().path("status").asText()).isEqualTo("COMPLETED");
        assertThat(detail.data().path("result").asText()).isEqualTo("PASS");
        assertThat(detail.data().path("confidence").asText()).isEqualTo("HIGH");
        assertThat(detail.data().path("total_score").asDouble()).isGreaterThan(90);
        assertThat(detail.data().path("progress").path("percent").asInt()).isEqualTo(100);

        HttpResult results = get("/detection-jobs/" + jobId + "/results", token);
        assertThat(results.status()).isEqualTo(200);
        assertThat(results.data().path("total").asInt()).isEqualTo(8);
        SchemaAssert.assertModel("detection-result", json(results.data().path("items").get(0)));
        assertThat(results.data().path("items").get(0).path("explanation").asText()).contains("测什么");

        HttpResult single = get("/detection-jobs/" + jobId + "/results/D7", token);
        assertThat(single.status()).isEqualTo(200);
        assertThat(single.data().path("probe_name").asText()).isEqualTo("模型指纹");
        assertThat(single.data().path("weight_used").asDouble()).isGreaterThan(0.3);

        assertThat(jdbc.queryForObject("select detection_status from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("PASS");
        assertThat(jdbc.queryForObject("select status from aap_provider", String.class)).isEqualTo("DETECT_PASSED");
    }

    @Test
    @DisplayName("AC-19 未通过可重测：FAIL 后凭证不再有活跃任务，可再次发起检测")
    void failedJobCanBeRetested() throws Exception {
        String token = token(PHONE);
        String credentialId = activeCredential(token);
        Long jobId = jdbc.queryForObject("select id from aap_detection_job order by id desc limit 1", Long.class);

        List<ProbeScore> failing = List.of(
                ProbeScoring.scoreTtft(List.of(2900, 2900, 2900)),
                ProbeScoring.scoreThroughput(6),
                ProbeScoring.scoreDeterminism(8, 0),
                ProbeScoring.scoreQuota("D4", 6.0, 60),
                ProbeScoring.scoreQuota("D5", 1000.0, 200000),
                ProbeScoring.scoreCache(false, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 20.0, "tokenizer", 20.0,
                        "self_awareness", 20.0, "probability", 20.0, "context", 20.0)));
        var done = detectionService.recordProbeResults(jobId, failing, Map.of(), Map.of());
        assertThat(done.result()).isEqualTo("FAIL");

        assertThat(jdbc.queryForObject("select detection_status from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("FAIL");
        assertThat(jdbc.queryForObject("select status from aap_provider", String.class)).isEqualTo("DETECT_FAILED");

        HttpResult retest = post("/detection-jobs", """
                {"credential_id":"%s","trigger_type":"MANUAL"}
                """.formatted(credentialId), token);
        assertThat(retest.status()).as(retest.body()).isEqualTo(200);
    }

    @Test
    @DisplayName("AC-20/R-47a 人工放行：理由必填；放行后凭证置 PASS 并写 SENSITIVE 审计；供应商 token 无权放行")
    void manualReleaseRequiresReasonAndAudit() throws Exception {
        String token = token(PHONE);
        String credentialId = activeCredential(token);
        Long jobId = jdbc.queryForObject("select id from aap_detection_job order by id desc limit 1", Long.class);
        String admin = techOpsToken();

        // 供应商不得放行
        HttpResult forbidden = post("/detection-jobs/" + jobId + "/release", """
                {"override_reason":"想直接过"}
                """, token);
        assertThat(forbidden.status()).isEqualTo(403);
        assertThat(forbidden.code()).isEqualTo("E-1901");

        // 理由缺失 → E-1001
        HttpResult noReason = post("/detection-jobs/" + jobId + "/release", """
                {"override_reason":"  "}
                """, admin);
        assertThat(noReason.status()).isEqualTo(400);
        assertThat(noReason.code()).isEqualTo("E-1001");

        // 人工放行成功
        HttpResult released = post("/detection-jobs/" + jobId + "/release", """
                {"override_reason":"上游临时故障已人工确认接口可用"}
                """, admin);
        assertThat(released.status()).as(released.body()).isEqualTo(200);
        assertThat(released.data().path("result").asText()).isEqualTo("PASS");
        assertThat(released.data().path("status").asText()).isEqualTo("COMPLETED");

        assertThat(jdbc.queryForObject("select detection_status from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("PASS");
        assertThat(jdbc.queryForObject("select action from aap_audit_log order by id desc limit 1", String.class))
                .isEqualTo("DETECTION_RELEASE");
        assertThat(jdbc.queryForObject("select risk_level from aap_audit_log order by id desc limit 1", String.class))
                .isEqualTo("SENSITIVE");

        // AC-18「检测完成 → 报告 1:1」对**两条**通往 COMPLETED 的路径都必须成立。
        // 缺陷 9（2026-09-19 实测）：release() 把任务置 COMPLETED 却不调 reportGenerator，
        // 而 recordProbeResults 里有这句且注释明确写着「宁可整体回滚也不留『有任务无报告』」。
        // 更严重的是：任务已 COMPLETED 后 recordProbeResults 会以「任务已结束，不可回写结果」拒绝
        // → 这条任务的报告**永远**产不出来（H5 联调里 /reports 恒为 total=0）。
        Integer reportCount = jdbc.queryForObject(
                "select count(*) from aap_report where job_id = ?::bigint", Integer.class, jobId);
        assertThat(reportCount).as("人工放行后应产出报告（AC-18 1:1）").isEqualTo(1);
    }

    @Test
    @DisplayName("越权：他人任务不可见（404 E-1304）")
    void crossProviderJobIsInvisible() throws Exception {
        String tokenA = token(PHONE);
        activeCredential(tokenA);
        Long jobId = jdbc.queryForObject("select id from aap_detection_job order by id desc limit 1", Long.class);

        String tokenB = token("13800000021");
        HttpResult res = get("/detection-jobs/" + jobId, tokenB);
        assertThat(res.status()).isEqualTo(404);
        assertThat(res.code()).isEqualTo("E-1304");
    }
}
