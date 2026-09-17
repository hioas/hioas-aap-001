package com.hioas.aap.quote;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.detection.DetectionService;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T08 · 报价单与明细定价验收（接口 QT-01…11；AC-22…27、AC-50）。
 *
 * <p>覆盖：报价前置（E-1602）、状态机（DRAFT/SUBMITTED/VOID + E-1601）、V1–V17 字段级错误码、
 * 幂等与乐观锁、越权隔离、客户端契约字段（items 分页 + quote-row/quote-detail/quote-item Schema）。
 */
class QuoteContractTest extends ApiTestBase {

    private static final String PHONE = "13800000050";
    private static final String OTHER_PHONE = "13800000051";
    /** 每个凭证用不同 key：同一供应商下 api_key 指纹唯一（R-03），重复即 E-1104。 */
    private static final java.util.concurrent.atomic.AtomicInteger KEY_SEQ = new java.util.concurrent.atomic.AtomicInteger();

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

    private static String fakeKey() {
        return "sk-quote-test-" + String.format("%08d", KEY_SEQ.incrementAndGet());
    }

    /** 建凭证（未跑检测）→ 返回 credentialId。 */
    private String credential(String token) throws Exception {
        HttpResult created = post("/credentials", """
                {
                  "alias":"报价凭证","base_url":"%s","api_key":"%s","primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(startUpstream(), fakeKey()), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        return created.data().path("id").asText();
    }

    /** 预检 + 回写通过结果（凭证 ACTIVE、detection_status=PASS）。 */
    private String passedCredential(String token) throws Exception {
        String credentialId = credential(token);
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

    private String createQuote(String token, String credentialId) throws Exception {
        HttpResult created = post("/quotes", """
                {
                  "name":"2026Q1 主线报价","credential_id":"%s","currency":"CNY",
                  "valid_from":"2026-10-01T00:00:00Z","valid_to":"2026-12-31T00:00:00Z"
                }
                """.formatted(credentialId), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        return created.data().path("quote_id").asText();
    }

    private String itemId(String token, String quoteId, String modelName) {
        HttpResult items = post("/quotes/" + quoteId + "/items",
                """
                {"items":[{"model_name":"%s"}]}
                """.formatted(modelName), token);
        assertThat(items.status()).as(items.body()).isEqualTo(200);
        return items.data().path("items").get(0).path("item_id").asText();
    }

    // ------------------------------------------------------------------ QT-02

    @Test
    @DisplayName("QT-02 前置（E-1602）：未通过检测不能报价；通过后创建返回 quote_no/DRAFT/空明细")
    void createRequiresPassedDetection() throws Exception {
        String token = token(PHONE);
        String fresh = credential(token);
        HttpResult blocked = post("/quotes", """
                {"name":"未检测就报价","credential_id":"%s"}
                """.formatted(fresh), token);
        assertThat(blocked.status()).isEqualTo(400);
        assertThat(blocked.code()).isEqualTo("E-1602");

        String passed = passedCredential(token);
        HttpResult created = post("/quotes", """
                {"name":"2026Q1 主线报价","credential_id":"%s","currency":"CNY"}
                """.formatted(passed), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        assertThat(created.data().path("status").asText()).isEqualTo("DRAFT");
        assertThat(created.data().path("items").size()).isZero();
        String quoteNo = created.data().path("quote_no").asText();
        assertThat(quoteNo).startsWith("Q").contains(LocalDate.now(ZoneOffset.UTC).toString().replace("-", ""));
        assertThat(quoteNo).hasSize(15);   // Q + yyyyMMdd + 6 位序列（10-PRD §3.1）
    }

    // ------------------------------------------------------------------ QT-05/06/07

    @Test
    @DisplayName("QT-05/06/07 明细行：写入后详情/列表/单行均可取，重复模型名拒绝（V2）")
    void itemLifecycle() throws Exception {
        String token = token(PHONE);
        String quoteId = createQuote(token, passedCredential(token));

        HttpResult items = post("/quotes/" + quoteId + "/items", """
                {"items":[{"model_name":"gpt-4o"}]}
                """, token);
        assertThat(items.status()).as(items.body()).isEqualTo(200);
        SchemaAssert.assertModel("quote-item", json(items.data().path("items").get(0)));

        HttpResult duplicate = post("/quotes/" + quoteId + "/items", """
                {"items":[{"model_name":"gpt-4o"},{"model_name":"gpt-4o"}]}
                """, token);
        assertThat(duplicate.status()).isEqualTo(400);
        assertThat(duplicate.code()).isEqualTo("E-1001");

        String itemId = items.data().path("items").get(0).path("item_id").asText();
        HttpResult one = get("/quotes/items/" + itemId, token);
        assertThat(one.status()).as(one.body()).isEqualTo(200);
        assertThat(one.data().path("model_name").asText()).isEqualTo("gpt-4o");

        HttpResult listItems = get("/quotes/" + quoteId + "/items", token);
        assertThat(listItems.data().path("total").asInt()).isEqualTo(1);

        HttpResult detail = get("/quotes/" + quoteId, token);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("quote-detail", json(detail.data()));
        assertThat(detail.data().path("item_count").asInt()).isEqualTo(1);
        assertThat(detail.data().path("status").asText()).isEqualTo("DRAFT");
    }

    // ------------------------------------------------------------------ QT-08

    @Test
    @DisplayName("QT-08 定价校验：负价(V4)/时区(V7)/时段重叠(V9)/阶梯空洞(V11)/首档(V12)/倍率(V10)/请求规则仅管理端(V15)")
    void saveItemValidationCodes() throws Exception {
        String token = token(PHONE);
        String quoteId = createQuote(token, passedCredential(token));
        String itemId = itemId(token, quoteId, "gpt-4o");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":-1,"output_price":3.6}
                """, token).code()).isEqualTo("E-1001");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":3.6,
                 "price_time_rule":{"tz":"Mars/Olympus","peak_ranges":[{"start":"08:00","end":"12:00"}]}}
                """, token).code()).isEqualTo("E-1401");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":3.6,
                 "price_time_rule":{"tz":"Asia/Shanghai","peak_ranges":[{"start":"08:00","end":"12:00"},{"start":"11:00","end":"14:00"}]}}
                """, token).code()).isEqualTo("E-1401");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":3.6,
                 "price_tier_rule":{"tier_field":"len","price_strategy":"OVERRIDE",
                   "tiers":[{"min":0,"max":1000,"input_price":1,"output_price":2},{"min":2000,"max":null,"input_price":1,"output_price":2}]}}
                """, token).code()).isEqualTo("E-1402");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":3.6,
                 "price_tier_rule":{"tier_field":"len","price_strategy":"OVERRIDE",
                   "tiers":[{"min":1,"max":null,"input_price":1,"output_price":2}]}}
                """, token).code()).isEqualTo("E-1404");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":3.6,
                 "price_time_rule":{"tz":"UTC","peak_ranges":[{"start":"08:00","end":"12:00"}],"peak_multiplier":0}}
                """, token).code()).isEqualTo("E-1403");

        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":3.6,
                 "request_rules":[{"field":"input_len","op":">","value":"1000","multiplier":1.5}]}
                """, token).code()).isEqualTo("E-1001");

        // 合法保存：缓存价高于输入价 → 警告但不阻塞（V5）
        HttpResult ok = put("/quotes/items/" + itemId, """
                {
                  "input_price":1.2,"output_price":3.6,"cache_read_price":2.0,
                  "tier":"标准","billing_mode":"按 token",
                  "price_time_rule":{"tz":"Asia/Shanghai","weekday_scope":"ALL",
                    "peak_ranges":[{"start":"08:00","end":"12:00"}],"peak_multiplier":1.5},
                  "price_tier_rule":{"tier_field":"len","price_strategy":"OVERRIDE",
                    "tiers":[{"min":0,"max":1000,"input_price":1.2,"output_price":3.6},
                             {"min":1000,"max":null,"input_price":1.0,"output_price":3.0}]}
                }
                """, token);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        assertThat(ok.data().path("warnings").size()).isGreaterThanOrEqualTo(1);
        assertThat(ok.data().path("warnings").get(0).asText()).contains("V5");
        assertThat(ok.data().path("input_price").asDouble()).isEqualTo(1.2);
        SchemaAssert.assertModel("quote-item", json(ok.data()));

        // 读回：规则持久化
        HttpResult readBack = get("/quotes/items/" + itemId, token);
        assertThat(readBack.data().path("time_rule").path("peak_ranges").size()).isEqualTo(1);
        assertThat(readBack.data().path("time_rule").path("tz").asText()).isEqualTo("Asia/Shanghai");
        assertThat(readBack.data().path("tier_rule").path("tiers").size()).isEqualTo(2);
        SchemaAssert.assertModel("price-time-rule", json(readBack.data().path("time_rule")));
        SchemaAssert.assertModel("price-tier-rule", json(readBack.data().path("tier_rule")));
    }

    @Test
    @DisplayName("QT-08 If-Match：版本不符 → 409 E-1104（乐观锁，防覆盖他人修改）")
    void saveItemOptimisticLock() throws Exception {
        String token = token(PHONE);
        String quoteId = createQuote(token, passedCredential(token));
        String itemId = itemId(token, quoteId, "gpt-4o");

        HttpResult first = send("PUT", "/quotes/items/" + itemId,
                """
                {"input_price":1,"output_price":2}
                """, token);
        assertThat(first.status()).as(first.body()).isEqualTo(200);

        HttpResult stale = send("PUT", "/quotes/items/" + itemId,
                """
                {"input_price":1,"output_price":3}
                """, token, Map.of("If-Match", "0"));
        assertThat(stale.status()).isEqualTo(409);
        assertThat(stale.code()).isEqualTo("E-1104");
    }

    // ------------------------------------------------------------------ QT-09

    @Test
    @DisplayName("QT-09 提交：空明细(V1)/缺价(V3)/模型不在检测清单(V17→E-1602)/有效期(V6) 均被拦；通过后 SUBMITTED + 版本快照")
    void submitValidationsAndSuccess() throws Exception {
        String token = token(PHONE);
        String quoteId = createQuote(token, passedCredential(token));

        HttpResult empty = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(empty.status()).isEqualTo(400);
        assertThat(empty.code()).isEqualTo("E-1001");

        String itemId = itemId(token, quoteId, "gpt-4o");
        HttpResult missingPrice = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(missingPrice.code()).isEqualTo("E-1001");
        assertThat(missingPrice.body()).contains("output_price").contains("V3");

        put("/quotes/items/" + itemId, """
                {"input_price":1.2,"output_price":3.6}
                """, token);

        // V17：明细里塞一个不在检测清单内的模型 （直接改库模拟历史数据）
        jdbc.update("update aap_quote_item set model_name = 'claude-3.7' where id = ?::bigint", itemId);
        HttpResult unknownModel = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(unknownModel.code()).isEqualTo("E-1602");
        assertThat(unknownModel.body()).contains("V17");
        jdbc.update("update aap_quote_item set model_name = 'gpt-4o' where id = ?::bigint", itemId);

        // V6：有效期止早于起
        jdbc.update("""
                update aap_quote set valid_from = now() + interval '10 days', valid_to = now() where id = ?::bigint
                """, quoteId);
        HttpResult badValidity = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(badValidity.code()).isEqualTo("E-1001");
        assertThat(badValidity.body()).contains("V6");

        jdbc.update("""
                update aap_quote set valid_from = now(), valid_to = now() + interval '90 days' where id = ?::bigint
                """, quoteId);

        HttpResult submitted = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(submitted.status()).as(submitted.body()).isEqualTo(200);
        assertThat(submitted.data().path("status").asText()).isEqualTo("SUBMITTED");
        assertThat(submitted.data().path("submitted_at").asText()).isNotBlank();
        // 提交后 current_version 递增（1 → 2）
        assertThat(submitted.data().path("current_version").asInt()).isEqualTo(2);

        HttpResult versions = get("/quotes/" + quoteId + "/versions", token);
        assertThat(versions.status()).as(versions.body()).isEqualTo(200);
        assertThat(versions.data().path("items").size()).isEqualTo(1);
        assertThat(versions.data().path("items").get(0).path("version_no").asInt()).isEqualTo(1);
        SchemaAssert.assertModel("quote-version", json(versions.data().path("items").get(0)));
        assertThat(versions.data().path("items").get(0).path("snapshot").path("items").size()).isEqualTo(1);

        // 重复提交 → E-1601
        HttpResult again = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
    }

    // ------------------------------------------------------------------ QT-10/11/04

    @Test
    @DisplayName("QT-10 撤回仅限已提交；QT-04 作废状态门禁；QT-01 列表状态过滤")
    void withdrawVoidAndList() throws Exception {
        String token = token(PHONE);
        String quoteId = createQuote(token, passedCredential(token));
        String itemId = itemId(token, quoteId, "gpt-4o");
        put("/quotes/items/" + itemId, """
                {"input_price":1.2,"output_price":3.6}
                """, token);

        // DRAFT 不可撤回
        HttpResult early = post("/quotes/" + quoteId + "/withdraw", null, token);
        assertThat(early.code()).isEqualTo("E-1601");

        post("/quotes/" + quoteId + "/submit", null, token);
        HttpResult withdrawn = post("/quotes/" + quoteId + "/withdraw", null, token);
        assertThat(withdrawn.status()).as(withdrawn.body()).isEqualTo(200);
        assertThat(withdrawn.data().path("status").asText()).isEqualTo("DRAFT");

        HttpResult again = post("/quotes/" + quoteId + "/withdraw", null, token);
        assertThat(again.code()).isEqualTo("E-1601");

        // 列表过滤：DRAFT 命中、SUBMITTED 不命中
        HttpResult drafts = get("/quotes?status=DRAFT", token);
        assertThat(drafts.status()).as(drafts.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(drafts.data()));
        assertThat(drafts.data().path("items").size()).isEqualTo(1);
        SchemaAssert.assertModel("quote-row", json(drafts.data().path("items").get(0)));
        assertThat(drafts.data().path("items").get(0).path("item_count").asInt()).isEqualTo(1);

        HttpResult submitted = get("/quotes?status=SUBMITTED,REVIEWING", token);
        assertThat(submitted.data().path("items").size()).isZero();

        // 作废 → VOID 且不可再编辑/撤回
        HttpResult deleted = delete("/quotes/" + quoteId, token);
        assertThat(deleted.status()).as(deleted.body()).isEqualTo(200);
        assertThat(deleted.data().isNull() || deleted.data().isMissingNode()).isTrue();

        // 作废是状态机终态：记录仍在（可按 status=VOID 查到），但不可再编辑 → E-1601
        HttpResult afterVoid = post("/quotes/" + quoteId + "/items", """
                {"items":[{"model_name":"gpt-4o"}]}
                """, token);
        assertThat(afterVoid.status()).isEqualTo(409);
        assertThat(afterVoid.code()).isEqualTo("E-1601");
        assertThat(get("/quotes?status=VOID", token).data().path("items").size()).isEqualTo(1);
    }

    // ------------------------------------------------------------------ 越权

    @Test
    @DisplayName("越权：他人报价单/明细行一律 404 E-1401（不泄露存在性）")
    void crossProviderIsolation() throws Exception {
        String token = token(PHONE);
        String quoteId = createQuote(token, passedCredential(token));
        String itemId = itemId(token, quoteId, "gpt-4o");

        String other = token(OTHER_PHONE);
        assertThat(get("/quotes/" + quoteId, other).status()).isEqualTo(404);
        assertThat(get("/quotes/" + quoteId, other).code()).isEqualTo("E-1406");
        assertThat(get("/quotes/items/" + itemId, other).status()).isEqualTo(404);
        assertThat(put("/quotes/items/" + itemId, """
                {"input_price":1,"output_price":2}
                """, other).status()).isEqualTo(404);
        assertThat(get("/quotes", other).data().path("items").size()).isZero();
    }
}
