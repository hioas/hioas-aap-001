package com.hioas.aap.detection;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.report.ReportService;
import com.hioas.aap.support.ApiTestBase;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/** T07 · AC-49 定期复测：报告过期（30 天）自动入队复测，未过期不重复触发。 */
class RecheckServiceTest extends ApiTestBase {

    private static final String PHONE = "13800000040";
    private static final String API_KEY = "sk-recheck-test-000000";

    @Autowired
    private DetectionService detectionService;

    @Autowired
    private RecheckService recheckService;

    @Autowired
    private ReportService reportService;

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
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        return login.data().path("token").asText();
    }

    /** 建凭证 → 预检 → 回写通过结果，产出一份 PASS 报告。 */
    private Long passedProviderId(String token) throws Exception {
        HttpResult created = post("/credentials", """
                {
                  "alias":"复测凭证","base_url":"%s","api_key":"%s","primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(startUpstream(), API_KEY), token);
        String credentialId = created.data().path("id").asText();
        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        String jobId = precheck.data().path("job_id").asText();

        detectionService.recordProbeResults(Long.valueOf(jobId), List.of(
                ProbeScoring.scoreTtft(List.of(200, 205, 210)),
                ProbeScoring.scoreThroughput(82.4),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 95.0, "tokenizer", 93.0,
                        "self_awareness", 90.0, "probability", 85.0, "context", 80.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA")), Map.of(), Map.of());

        return jdbc.queryForObject("select provider_id from aap_credential where id = ?::bigint",
                Long.class, credentialId);
    }

    @Test
    @DisplayName("AC-49 到期复测：报告过期入队 RECHECK 任务；未过期不重复入队")
    void dueProviderEnqueuesRecheck() throws Exception {
        String token = token(PHONE);
        Long providerId = passedProviderId(token);
        Long reportId = jdbc.queryForObject("select id from aap_report order by id desc limit 1", Long.class);

        // 刚出报告 → 未到期
        assertThat(recheckService.dueProviderIds()).doesNotContain(providerId);
        assertThat(recheckService.runOnce()).isZero();

        // 把报告检测时间推到 31 天前 → 到期
        jdbc.update("update aap_report set detected_at = now() - interval '31 days' where id = ?", reportId);
        assertThat(recheckService.dueProviderIds()).contains(providerId);

        // 上一轮预检任务还挂着 → 先把活跃任务放掉，验证复测能真正入队
        jdbc.update("update aap_detection_job set active_flag = false, status = 'COMPLETED' where active_flag = true");
        assertThat(recheckService.runOnce()).isEqualTo(1);

        Map<String, Object> job = jdbc.queryForMap("""
                select trigger_type, status, credential_id from aap_detection_job order by id desc limit 1
                """);
        assertThat(job.get("trigger_type")).isEqualTo("RECHECK");
        assertThat(job.get("status")).isEqualTo("QUEUED");

        // RECHECK 不计入供应商日配额（R-09 只约束 FIRST/MANUAL）：连续复测不被 E-1302 挡住
        jdbc.update("update aap_detection_job set active_flag = false, status = 'COMPLETED' where active_flag = true");
        assertThat(recheckService.runOnce()).isEqualTo(1);
    }

    @Test
    @DisplayName("AC-49 最近一次通过报告时间可读；非通过供应商不在复测队列")
    void onlyPassedProvidersAreDue() throws Exception {
        String token = token(PHONE);
        Long providerId = passedProviderId(token);
        assertThat(recheckService.latestPassedAt(providerId)).isNotNull();

        jdbc.update("update aap_provider set status = 'DRAFT' where id = ?", providerId);
        assertThat(recheckService.dueProviderIds()).doesNotContain(providerId);

        jdbc.update("update aap_provider set status = 'DETECT_PASSED' where id = ?", providerId);
        jdbc.update("update aap_report set detected_at = now() - interval '31 days' where provider_id = ?", providerId);
        assertThat(recheckService.dueProviderIds()).contains(providerId);
    }
}
