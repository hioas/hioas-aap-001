package com.hioas.aap.report;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.detection.DetectionService;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.detection.ProbeScoring.ProbeScore;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T07 · 检测报告验收（接口 RPT-01…04；AC-18/21/49）。
 *
 * <p>红线（R-26）：报告**不得**出现「正品 / 保证为真」等保证性措辞；每项必须带四段式解释；
 * 必须带免责声明与有效期。本类同时对报告响应做 JSON Schema 契约校验。
 */
class ReportContractTest extends ApiTestBase {

    private static final String PHONE = "13800000030";
    private static final String OTHER_PHONE = "13800000031";
    private static final String API_KEY = "sk-report-test-0000000000";

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

    /** 建凭证 → 预检通过 → 返回 jobId（预检同时建了检测任务）。 */
    private String queuedJobId(String token) throws Exception {
        HttpResult created = post("/credentials", """
                {
                  "alias":"报告凭证","base_url":"%s","api_key":"%s","primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(startUpstream(), API_KEY), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String credentialId = created.data().path("id").asText();
        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(precheck.status()).as(precheck.body()).isEqualTo(200);
        return precheck.data().path("job_id").asText();
    }

    private static Map<String, Map<String, Object>> metrics() {
        Map<String, Map<String, Object>> m = new LinkedHashMap<>();
        m.put("D1", Map.of("p50_ms", 210));
        m.put("D2", Map.of("tps", 82.4));
        m.put("D3", Map.of("consistency_rate", 1.0));
        m.put("D4", Map.of("rpm", 60));
        m.put("D5", Map.of("tpm", 200000));
        m.put("D6", Map.of("cache_hit", true, "cache_field_visible", true));
        m.put("D7", Map.of("behavior", 95.0, "tokenizer", 93.0, "self_awareness", 90.0,
                "probability", 60.0, "context", 55.0));
        m.put("D8", Map.of("tls_issuer", "TestCA"));
        return m;
    }

    private static List<ProbeScore> passingScores() {
        return List.of(
                ProbeScoring.scoreTtft(List.of(200, 205, 210)),
                ProbeScoring.scoreThroughput(82.4),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 95.0, "tokenizer", 93.0,
                        "self_awareness", 90.0, "probability", 60.0, "context", 55.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA"));
    }

    /** 指纹远低于阈值 → 一票否决，结论 FAIL（AC-18 未通过报告页数据源）。 */
    private static List<ProbeScore> vetoedScores() {
        return List.of(
                ProbeScoring.scoreTtft(List.of(900, 1200, 1500)),
                ProbeScoring.scoreThroughput(12.0),
                ProbeScoring.scoreDeterminism(5, 8),
                ProbeScoring.scoreQuota("D4", 20.0, 60),
                ProbeScoring.scoreQuota("D5", 30000.0, 200000),
                ProbeScoring.scoreCache(false, false),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 20.0, "tokenizer", 25.0,
                        "self_awareness", 10.0, "probability", 30.0, "context", 15.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=UnknownCA"));
    }

    @Test
    @DisplayName("AC-18 未通过报告：章节/四段式解释/免责声明齐全，且无「正品」类保证性措辞")
    void vetoedReportHasSectionsExplanationsAndNoGuaranteeWording() throws Exception {
        String token = token(PHONE);
        String jobId = queuedJobId(token);
        detectionService.recordProbeResults(Long.valueOf(jobId), vetoedScores(), metrics(),
                Map.of("D1", "10 次采样 p50=1200ms", "D7", "5 条子证据线一致率 20%"));

        HttpResult list = get("/reports", token);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("items").size()).isEqualTo(1);
        SchemaAssert.assertModel("report-summary", json(list.data().path("items").get(0)));
        assertThat(list.data().path("items").get(0).path("result").asText()).isEqualTo("FAIL");

        String reportId = list.data().path("items").get(0).path("id").asText();
        HttpResult detail = get("/reports/" + reportId, token);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("report", json(detail.data()));

        // 一票否决与免责
        assertThat(detail.data().path("veto_triggered").asBoolean()).isTrue();
        assertThat(detail.data().path("veto_note").asText()).contains("一票否决");
        assertThat(detail.data().path("disclaimer").asText()).contains("不是「真 / 假」判决");
        assertThat(detail.data().path("verdict").asText()).doesNotContain("正品");
        // 4 个可计分维度（A/B/C/D）；E 段因上游未返回缓存字段而 NOT_MEASURABLE → 不计分、不进维度对照
        assertThat(detail.data().path("dims").size()).isGreaterThanOrEqualTo(4);
        assertThat(detail.data().path("unmeasurable_count").asInt()).isGreaterThanOrEqualTo(1);
        assertThat(detail.data().path("detail").path("code").asText()).isNotBlank();
        assertThat(detail.data().path("weight_note").asText()).contains("归一化");

        // 每个章节项必须四段式（测什么 / 怎么测 / 结果 / 意义与边界）
        int checked = 0;
        for (var section : detail.data().path("sections")) {
            for (var item : section.path("items")) {
                String explanation = item.path("explanation").asText();
                assertThat(explanation).contains("【测什么】").contains("【怎么测】")
                        .contains("【结果】").contains("【意义与边界】");
                checked++;
            }
        }
        assertThat(checked).isGreaterThanOrEqualTo(8);

        // R-26 措辞校验：禁止保证性断言；服务端输出连「正品」字样都不出现（比客户端兜底文案更严格）
        String body = detail.body();
        assertThat(ReportController.wordingCompliant(body)).as("报告正文命中保证性断言：%s", body).isTrue();
        assertThat(body).doesNotContain("正品");
        assertThat(body).doesNotContain("保证为真");
    }

    @Test
    @DisplayName("RPT-03/04 报告 HTML 版与导出：含免责声明与报告编号；导出返回可下载地址")
    void htmlAndExport() throws Exception {
        String token = token(PHONE);
        String jobId = queuedJobId(token);
        detectionService.recordProbeResults(Long.valueOf(jobId), passingScores(), metrics(),
                Map.of("D8", "TLS issuer=TestCA"));

        String reportId = jdbc.queryForObject("select id from aap_report order by id desc limit 1", String.class);

        HttpResult html = send("GET", "/reports/" + reportId + "/html", null, token);
        assertThat(html.status()).isEqualTo(200);
        assertThat(html.headers().firstValue("content-type").orElse("")).contains("text/html");
        assertThat(html.body()).contains("免责声明").contains("检测报告").contains("不是「真 / 假」判决");

        HttpResult export = get("/reports/" + reportId + "/export", token);
        assertThat(export.status()).as(export.body()).isEqualTo(200);
        SchemaAssert.assertModel("report-export", json(export.data()));
        assertThat(export.data().path("url").asText()).contains("/reports/" + reportId);
        assertThat(export.data().path("file_name").asText()).endsWith(".html");
    }

    @Test
    @DisplayName("AC-21 检测通过：写站内信/短信通知（脱敏，不含 api_key 明文）")
    void passNotifiesProvider() throws Exception {
        String token = token(PHONE);
        String jobId = queuedJobId(token);
        detectionService.recordProbeResults(Long.valueOf(jobId), passingScores(), metrics(),
                Map.of("D8", "TLS issuer=TestCA"));

        Long providerId = jdbc.queryForObject("select provider_id from aap_detection_job where id = ?::bigint",
                Long.class, jobId);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select event_code, channel, title, content, status, recipient_id
                from aap_notification where event_code = 'DETECTION_PASSED'
                """);
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0).get("recipient_id")).isEqualTo(providerId);
        assertThat(rows.get(0).get("channel")).isEqualTo("BOTH");
        assertThat(String.valueOf(rows.get(0).get("content"))).doesNotContain("sk-").doesNotContain(API_KEY);

        // 09-PRD 标准措辞：PASS 结论必须用「未发现与宣称模型不一致的迹象（置信度：…）」
        String reportId = jdbc.queryForObject("select id from aap_report order by id desc limit 1", String.class);
        HttpResult detail = get("/reports/" + reportId, token);
        assertThat(detail.data().path("verdict").asText())
                .startsWith("未发现与宣称模型不一致的迹象")
                .contains("置信度：");
        assertThat(detail.body()).doesNotContain("正品");

        // 供应商状态与凭证检测状态同步回写
        assertThat(jdbc.queryForObject("select status from aap_provider where id = ?", String.class, providerId))
                .isEqualTo("DETECT_PASSED");
    }

    @Test
    @DisplayName("越权：他人报告一律 404（不泄露存在性）；列表不跨供应商")
    void crossProviderIsolation() throws Exception {
        String token = token(PHONE);
        String jobId = queuedJobId(token);
        detectionService.recordProbeResults(Long.valueOf(jobId), passingScores(), metrics(),
                Map.of("D8", "TLS issuer=TestCA"));
        String reportId = jdbc.queryForObject("select id from aap_report order by id desc limit 1", String.class);

        String otherToken = token(OTHER_PHONE);
        HttpResult detail = get("/reports/" + reportId, otherToken);
        assertThat(detail.status()).isEqualTo(404);
        assertThat(detail.code()).isEqualTo("E-1406");

        HttpResult list = get("/reports", otherToken);
        assertThat(list.status()).isEqualTo(200);
        assertThat(list.data().path("items").size()).isZero();
    }

    @Test
    @DisplayName("RPT-01 报告列表按结论过滤；分页字段完整")
    void listFiltersByResult() throws Exception {
        String token = token(PHONE);
        String jobId = queuedJobId(token);
        detectionService.recordProbeResults(Long.valueOf(jobId), passingScores(), metrics(),
                Map.of("D8", "TLS issuer=TestCA"));

        HttpResult passed = get("/reports?result=PASS", token);
        assertThat(passed.status()).as(passed.body()).isEqualTo(200);
        assertThat(passed.data().path("items").size()).isEqualTo(1);
        assertThat(passed.data().path("page").asInt()).isEqualTo(1);

        HttpResult failed = get("/reports?result=FAIL", token);
        assertThat(failed.data().path("items").size()).isZero();
    }
}
