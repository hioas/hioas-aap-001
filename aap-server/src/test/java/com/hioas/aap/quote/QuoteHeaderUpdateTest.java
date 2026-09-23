package com.hioas.aap.quote;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.detection.DetectionService;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.support.ApiTestBase;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * #12 报价单**表头**可更新（QT-02b：{@code PUT /quotes/{quoteId}}）。
 *
 * <p><b>修复前的缺口</b>：编辑页只能改明细行，表头（名称/凭证/币种/有效期/备注）没有接口可改 ——
 * 客户端注释写着「后端没有 PUT /quotes/{id} → 表头字段无法修改，只能如实回填」，
 * 于是同一张草稿改个名字/换个凭证再报做不到。
 *
 * <p>口径必须与明细行写入一致（同一守卫方法）：只有自己的、只有可编辑状态（DRAFT/REJECTED）、
 * 换凭证要求预检+检测通过 —— 否则就成了绕过 E-1601/E-1602 的后门。
 */
class QuoteHeaderUpdateTest extends ApiTestBase {

    private static final AtomicInteger KEY_SEQ = new AtomicInteger(0);

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
        if (upstream != null) {
            upstream.stop(0);
        }
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

    private static String fakeKey(String tag) {
        return "sk-header-" + tag + "-" + String.format("%08d", KEY_SEQ.incrementAndGet());
    }

    /** 建凭证（未跑检测）。 */
    private String credential(String token, String tag) throws Exception {
        HttpResult created = post("/credentials", """
                {
                  "alias":"表头凭证-%s","base_url":"%s","api_key":"%s",
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(tag, startUpstream(), fakeKey(tag)), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        return created.data().path("id").asText();
    }

    /** 预检 + 回写通过结果（ACTIVE + detection_status=PASS），否则报价前置 E-1602 过不去。 */
    private String passedCredential(String token, String tag) throws Exception {
        String credentialId = credential(token, tag);
        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(precheck.status()).as(precheck.body()).isEqualTo(200);
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
        return credentialId;
    }

    private String createQuote(String token, String credentialId, String name) {
        HttpResult created = post("/quotes", """
                {"name":"%s","credential_id":"%s","currency":"CNY"}
                """.formatted(name, credentialId), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        return created.data().path("quote_id").asText();
    }

    private HttpResult putHeader(String token, String quoteId, String body) {
        return send("PUT", "/quotes/" + quoteId, body, token);
    }

    @Test
    @DisplayName("QT-02b 草稿表头可改：名称/币种/备注更新后详情回读一致，并写审计")
    void draftHeaderIsUpdatable() throws Exception {
        String token = token("13800000060");
        String quoteId = createQuote(token, passedCredential(token, "a"), "2026Q1 主线报价");

        HttpResult res = putHeader(token, quoteId, """
                {"name":"2026Q1 主线报价（改名后）","currency":"usd","remark":"改过备注"}
                """);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        assertThat(res.data().path("name").asText()).isEqualTo("2026Q1 主线报价（改名后）");
        assertThat(res.data().path("currency").asText()).as("币种按口径大写").isEqualTo("USD");
        assertThat(res.data().path("remark").asText()).isEqualTo("改过备注");

        // 回读：真的落库了，不是只在响应里改
        HttpResult detail = get("/quotes/" + quoteId, token);
        assertThat(detail.data().path("name").asText()).isEqualTo("2026Q1 主线报价（改名后）");
        assertThat(detail.data().path("currency").asText()).isEqualTo("USD");
        assertThat(jdbc.queryForObject("select remark from aap_quote where id = ?::bigint",
                String.class, quoteId)).isEqualTo("改过备注");

        // 部分更新：不传的字段不能被清空
        HttpResult partial = putHeader(token, quoteId, """
                {"remark":"只改备注"}
                """);
        assertThat(partial.status()).as(partial.body()).isEqualTo(200);
        assertThat(partial.data().path("name").asText()).as("未传的字段保持原值").isEqualTo("2026Q1 主线报价（改名后）");
        assertThat(partial.data().path("currency").asText()).isEqualTo("USD");

        assertThat(jdbc.queryForObject("select count(*) from aap_audit_log where action = 'QUOTE_SAVE' "
                + "and target_id = ?::bigint", Integer.class, quoteId)).as("必须留审计").isEqualTo(2);
    }

    @Test
    @DisplayName("QT-02b 非可编辑状态改表头 → 409 E-1601（与明细行写入同一守卫，不能当后门）")
    void nonEditableStatusRejectsHeaderUpdate() throws Exception {
        String token = token("13800000061");
        String quoteId = createQuote(token, passedCredential(token, "b"), "已提交的报价");
        // 直接把状态推到「已提交」（走 submit 需要先填满 8 项定价，与本用例要测的守卫无关）
        jdbc.update("update aap_quote set status = 'SUBMITTED', updated_at = now() where id = ?::bigint",
                Long.valueOf(quoteId));

        HttpResult res = putHeader(token, quoteId, """
                {"name":"偷偷改名"}
                """);
        assertThat(res.status()).as(res.body()).isEqualTo(409);
        assertThat(res.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select name from aap_quote where id = ?::bigint",
                String.class, quoteId)).as("被拒后不得有半成品写入").isEqualTo("已提交的报价");
    }

    @Test
    @DisplayName("QT-02b 他人报价单不可见：改别人的表头 → 404 E-1406（不区分他人/不存在）")
    void othersQuoteIsInvisible() throws Exception {
        String owner = token("13800000062");
        String other = token("13800000063");
        String quoteId = createQuote(owner, passedCredential(owner, "c"), "别人的报价");

        HttpResult res = putHeader(other, quoteId, """
                {"name":"越权改名"}
                """);
        assertThat(res.status()).as(res.body()).isEqualTo(404);
        assertThat(res.code()).isEqualTo("E-1406");
        assertThat(jdbc.queryForObject("select name from aap_quote where id = ?::bigint",
                String.class, quoteId)).isEqualTo("别人的报价");
    }

    @Test
    @DisplayName("QT-02b 换凭证必须已通过检测：指到未检测凭证 → 400 E-1602")
    void credentialSwapRequiresPassedDetection() throws Exception {
        String token = token("13800000064");
        String passed = passedCredential(token, "d");
        String notDetected = credential(token, "e");
        String quoteId = createQuote(token, passed, "待换凭证的报价");

        HttpResult res = putHeader(token, quoteId, """
                {"credential_id":"%s"}
                """.formatted(notDetected));
        assertThat(res.status()).as(res.body()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1602");
        assertThat(jdbc.queryForObject("select credential_id from aap_quote where id = ?::bigint",
                String.class, quoteId)).as("被拒后凭证不能被换掉").isEqualTo(passed);
    }
}
