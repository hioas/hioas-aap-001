package com.hioas.aap.compile;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.detection.DetectionService;
import com.hioas.aap.detection.ProbeScoring;
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
 * T09 · 计费编译验收（QT-12、ADM-Q01、ADM-CP01…04；AC-28…31）。
 *
 * <p>三道闸门（R-33）：编译 → 模拟验证 → 人工确认；未确认 `publish_blocked=true`；
 * 未验证就确认 → E-1407；验证不过 → E-1405 且必须定位到报价单字段。
 * 幂等（R-34）：同 `source_hash` 重复编译复用同一产物；编译前边界冲突（4.2）直接拒绝。
 */
class CompilationContractTest extends ApiTestBase {

    private static final String PHONE = "13800000060";
    private static final java.util.concurrent.atomic.AtomicInteger KEY_SEQ =
            new java.util.concurrent.atomic.AtomicInteger();

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
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        return login.data().path("token").asText();
    }

    /** 技术运营 token（编译管理端）。 */
    private String techOpsToken() {
        Long accountId = 930001L;
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'techops2', 'x', '技术运营', 'TECH_OPS', 'ACTIVE')
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

    /** 造一个「已报价 + 已定价 + 已审核通过」的报价单，返回 quoteId。 */
    private String approvedQuote(String token) throws Exception {
        HttpResult credential = post("/credentials", """
                {
                  "alias":"编译凭证","base_url":"%s","api_key":"sk-compile-test-%08d","primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(startUpstream(), KEY_SEQ.incrementAndGet()), token);
        String credentialId = credential.data().path("id").asText();
        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        detectionService.recordProbeResults(Long.valueOf(precheck.data().path("job_id").asText()), List.of(
                ProbeScoring.scoreTtft(List.of(200, 205, 210)),
                ProbeScoring.scoreThroughput(82.4),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 95.0, "tokenizer", 93.0,
                        "self_awareness", 90.0, "probability", 85.0, "context", 80.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA")), Map.of(), Map.of());

        HttpResult quote = post("/quotes", """
                {"name":"编译报价","credential_id":"%s","currency":"USD"}
                """.formatted(credentialId), token);
        String quoteId = quote.data().path("quote_id").asText();
        String itemId = post("/quotes/" + quoteId + "/items", """
                {"items":[{"model_name":"gpt-4o"}]}
                """, token).data().path("items").get(0).path("item_id").asText();
        HttpResult priced = put("/quotes/items/" + itemId, """
                {
                  "input_price":2.5,"output_price":15,"cache_read_price":0.25,
                  "tier":"标准","billing_mode":"按 token",
                  "price_time_rule":{"tz":"Asia/Shanghai","weekday_scope":"ALL",
                    "peak_ranges":[{"start":"09:00","end":"12:00"}],"peak_multiplier":1.5,"offpeak_multiplier":0.8},
                  "price_tier_rule":{"tier_field":"len","price_strategy":"OVERRIDE",
                    "tiers":[{"min":0,"max":512000,"input_price":2.5,"output_price":15},
                             {"min":512000,"max":1024000,"input_price":5,"output_price":30,"cache_read_price":0.5},
                             {"min":1024000,"max":null,"input_price":10,"output_price":60}]}
                }
                """, token);
        assertThat(priced.status()).as(priced.body()).isEqualTo(200);

        // 审核通过状态由 T10 流程产生；此处直接置位（T10 落地后改为走接口）
        jdbc.update("update aap_quote set status = 'APPROVED' where id = ?::bigint", quoteId);
        return quoteId;
    }

    // ------------------------------------------------------------------ ADM-Q01

    @Test
    @DisplayName("ADM-Q01 编译：未审核通过拒绝（E-1601）；通过后产出表达式，闸门 COMPILED 且禁止写入")
    void compileRequiresApprovedQuote() throws Exception {
        String token = token(PHONE);
        String admin = techOpsToken();
        String quoteId = approvedQuote(token);

        jdbc.update("update aap_quote set status = 'DRAFT' where id = ?::bigint", quoteId);
        HttpResult tooEarly = post("/admin/quotes/" + quoteId + "/compile", null, admin);
        assertThat(tooEarly.status()).isEqualTo(409);
        assertThat(tooEarly.code()).isEqualTo("E-1601");

        jdbc.update("update aap_quote set status = 'APPROVED' where id = ?::bigint", quoteId);
        HttpResult compiled = post("/admin/quotes/" + quoteId + "/compile", null, admin);
        assertThat(compiled.status()).as(compiled.body()).isEqualTo(200);
        SchemaAssert.assertModel("compilation-result", json(compiled.data()));
        assertThat(compiled.data().path("gate_status").asText()).isEqualTo("COMPILED");
        assertThat(compiled.data().path("publish_blocked").asBoolean()).isTrue();
        assertThat(compiled.data().path("compiled").size()).isEqualTo(1);
        String expr = compiled.data().path("compiled").get(0).path("expr").asText();
        assertThat(expr).contains("len <=").contains("hour(\"Asia/Shanghai\")")
                .contains("tier(\"t0_0_512K.peak\"");
        assertThat(compiled.data().path("compiled").get(0).path("tier_labels").size()).isEqualTo(3);
        assertThat(compiled.data().path("compiled").get(0).path("rule_hits").toString())
                .contains("R1_BASE_PRICE").contains("R2_TIER_BY_LEN").contains("R3_PEAK_OFFPEAK")
                .contains("R4_TIER_X_TIME");
        assertThat(compiled.data().path("verify_report").isNull()).isTrue();
    }

    @Test
    @DisplayName("R-34 幂等：同一份报价内容重复编译复用同一编译产物（source_hash 未变）")
    void compileIsIdempotentBySourceHash() throws Exception {
        String admin = techOpsToken();
        String quoteId = approvedQuote(token(PHONE));

        String first = post("/admin/quotes/" + quoteId + "/compile", null, admin)
                .data().path("compilation_id").asText();
        HttpResult second = post("/admin/quotes/" + quoteId + "/compile", null, admin);
        assertThat(second.status()).as(second.body()).isEqualTo(200);
        assertThat(second.data().path("compilation_id").asText()).isEqualTo(first);
        assertThat(jdbc.queryForObject("select count(*) from aap_compiled_expression where quote_id = ?::bigint",
                Long.class, quoteId)).isEqualTo(1L);

        // 改价 → hash 变 → 生成新产物，且旧表达式进 previous_expr（§4.3 保留旧快照）
        String itemId = jdbc.queryForObject(
                "select id from aap_quote_item where quote_id = ?::bigint limit 1", String.class, quoteId);
        jdbc.update("update aap_quote_item set input_price = 3.0 where id = ?::bigint", itemId);
        jdbc.update("update aap_quote set status = 'APPROVED' where id = ?::bigint", quoteId);
        HttpResult third = post("/admin/quotes/" + quoteId + "/compile", null, admin);
        assertThat(third.status()).as(third.body()).isEqualTo(200);
        assertThat(third.data().path("compilation_id").asText()).isNotEqualTo(first);
        assertThat(third.data().path("previous_expr").path("models").size()).isEqualTo(1);
        assertThat(third.data().path("previous_expr").path("models").get(0).path("expr").asText())
                .contains("p * 2.5");
    }

    @Test
    @DisplayName("同一供应商的第二张报价单（内容相同）→ 幂等复用既有产物，不得撞唯一索引（E-2001 回归）")
    void compileReusesArtifactAcrossQuotesOfSameProvider() throws Exception {
        String token = token(PHONE);
        String admin = techOpsToken();
        String firstQuote = approvedQuote(token);
        String firstCompilation = post("/admin/quotes/" + firstQuote + "/compile", null, admin)
                .data().path("compilation_id").asText();

        // 同一供应商、同样的计价规则内容 ⇒ source_hash 相同，但 quote_id 不同
        String secondQuote = approvedQuote(token);
        HttpResult second = post("/admin/quotes/" + secondQuote + "/compile", null, admin);
        assertThat(second.status()).as("相同 source_hash 的第二张报价单不得 500：%s", second.body()).isEqualTo(200);
        assertThat(second.data().path("compilation_id").asText())
                .as("相同内容应复用既有编译产物，而不是新建/报错").isEqualTo(firstCompilation);
    }

    @Test
    @DisplayName("两个供应商报价内容相同 → 各自独立成产物（不互相冲突、不互相复用）")
    void compileIsolatesIdenticalContentAcrossProviders() throws Exception {
        String admin = techOpsToken();
        String quoteA = approvedQuote(token(PHONE));
        String compilationA = post("/admin/quotes/" + quoteA + "/compile", null, admin)
                .data().path("compilation_id").asText();

        String quoteB = approvedQuote(token("13800000061"));
        HttpResult compiledB = post("/admin/quotes/" + quoteB + "/compile", null, admin);
        assertThat(compiledB.status()).as("另一供应商同内容不得 500：%s", compiledB.body()).isEqualTo(200);
        assertThat(compiledB.data().path("compilation_id").asText())
                .as("不同供应商的编译产物必须彼此独立")
                .isNotEqualTo(compilationA);
    }

    @Test
    @DisplayName("编译前边界冲突（4.2）：档位出现空洞直接拒绝（E-1402），不产出表达式")
    void boundaryConflictsBlockCompile() throws Exception {
        String admin = techOpsToken();
        String quoteId = approvedQuote(token(PHONE));
        // 人为制造空洞：把第二档下界推到 600000（首档上界仍是 512000）
        jdbc.update("""
                update aap_price_tier set min_value = 600000
                 where tier_rule_id in (select id from aap_price_tier_rule
                       where item_id in (select id from aap_quote_item where quote_id = ?::bigint))
                   and seq = 1
                """, quoteId);
        HttpResult blocked = post("/admin/quotes/" + quoteId + "/compile", null, admin);
        assertThat(blocked.status()).isEqualTo(400);
        assertThat(blocked.code()).isEqualTo("E-1402");
        assertThat(blocked.body()).contains("V11");
        assertThat(jdbc.queryForObject("select count(*) from aap_compiled_expression where quote_id = ?::bigint",
                Long.class, quoteId)).isZero();
    }

    // ------------------------------------------------------------------ ADM-CP03/04

    @Test
    @DisplayName("ADM-CP03/04 三道闸门：未验证确认 → E-1407；验证通过 → VERIFIED；确认 → CONFIRMED 且解除写入封锁")
    void verifyThenConfirmGate() throws Exception {
        String admin = techOpsToken();
        String quoteId = approvedQuote(token(PHONE));
        String compilationId = post("/admin/quotes/" + quoteId + "/compile", null, admin)
                .data().path("compilation_id").asText();

        HttpResult premature = post("/admin/compilations/" + compilationId + "/confirm", null, admin);
        assertThat(premature.status()).isEqualTo(409);
        assertThat(premature.code()).isEqualTo("E-1407");

        HttpResult verified = post("/admin/compilations/" + compilationId + "/verify", null, admin);
        assertThat(verified.status()).as(verified.body()).isEqualTo(200);
        SchemaAssert.assertModel("verify-report", json(verified.data()));
        assertThat(verified.data().path("status").asText()).isEqualTo("PASSED");
        assertThat(verified.data().path("case_total").asInt()).isGreaterThanOrEqualTo(10);
        assertThat(verified.data().path("case_passed").asInt())
                .isEqualTo(verified.data().path("case_total").asInt());
        SchemaAssert.assertModel("verify-case", json(verified.data().path("cases").get(0)));

        // 验证报告与单模型 verified 标记落库
        HttpResult detail = get("/admin/compilations/" + compilationId, admin);
        assertThat(detail.data().path("gate_status").asText()).isEqualTo("VERIFIED");
        assertThat(detail.data().path("verify_report").path("status").asText()).isEqualTo("PASSED");
        assertThat(detail.data().path("compiled").get(0).path("verified").asBoolean()).isTrue();

        HttpResult confirmed = post("/admin/compilations/" + compilationId + "/confirm", null, admin);
        assertThat(confirmed.status()).as(confirmed.body()).isEqualTo(200);
        assertThat(confirmed.data().path("gate_status").asText()).isEqualTo("CONFIRMED");
        assertThat(confirmed.data().path("publish_blocked").asBoolean()).isFalse();
        assertThat(confirmed.data().path("confirmed_at").asText()).isNotBlank();

        // 审计留痕（R-47：确认写入配置必须可审计）
        assertThat(jdbc.queryForObject("""
                select count(*) from aap_audit_log where action = 'CONFIG_PUBLISH' and target_id = ?::bigint
                """, Long.class, compilationId)).isGreaterThanOrEqualTo(1L);
    }

    @Test
    @DisplayName("ADM-CP01 编译记录列表按闸门状态过滤；ADM-CP02 详情")
    void listAndDetail() throws Exception {
        String admin = techOpsToken();
        String quoteId = approvedQuote(token(PHONE));
        String compilationId = post("/admin/quotes/" + quoteId + "/compile", null, admin)
                .data().path("compilation_id").asText();

        HttpResult list = get("/admin/compilations?status=COMPILED", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("items").size()).isEqualTo(1);
        SchemaAssert.assertModel("compilation-result", json(list.data().path("items").get(0)));

        assertThat(get("/admin/compilations?status=CONFIRMED", admin).data().path("items").size()).isZero();
        assertThat(get("/admin/compilations/99999999", admin).status()).isEqualTo(404);
        assertThat(get("/admin/compilations/" + compilationId, admin).data().path("compiled").size()).isEqualTo(1);
    }

    // ------------------------------------------------------------------ QT-12 与权限

    @Test
    @DisplayName("QT-12 编译预览：供应商可自检表达式与模拟结果，且不落库")
    void supplierPreviewDoesNotPersist() throws Exception {
        String token = token(PHONE);
        String quoteId = approvedQuote(token);
        long before = jdbc.queryForObject("select count(*) from aap_compiled_expression", Long.class);

        HttpResult preview = post("/quotes/" + quoteId + "/compile-preview", null, token);
        assertThat(preview.status()).as(preview.body()).isEqualTo(200);
        assertThat(preview.data().path("status").asText()).isEqualTo("PREVIEW");
        assertThat(preview.data().path("gate_status").asText()).isEqualTo("VERIFIED");
        assertThat(preview.data().path("compiled").get(0).path("expr").asText()).contains("tier(");
        assertThat(preview.data().path("verify_report").path("case_passed").asInt())
                .isEqualTo(preview.data().path("verify_report").path("case_total").asInt());
        assertThat(jdbc.queryForObject("select count(*) from aap_compiled_expression", Long.class))
                .isEqualTo(before);
    }

    @Test
    @DisplayName("权限：供应商访问管理端编译接口 403；未认证 401")
    void adminEndpointsAreProtected() throws Exception {
        String token = token(PHONE);
        assertThat(get("/admin/compilations", token).status()).isEqualTo(403);
        assertThat(post("/admin/compilations/1/verify", null, token).status()).isEqualTo(403);
        assertThat(get("/admin/compilations").status()).isEqualTo(401);
    }
}
