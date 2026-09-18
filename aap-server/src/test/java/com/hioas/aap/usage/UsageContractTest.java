package com.hioas.aap.usage;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * T12 · 用量聚合与对账验收（USE-01/02、ADM-U01/02；AC-43…46）。
 *
 * <p>契约真源：`docs/backend/endpoints.json`（USE-01 `usage-summary` 超集、USE-02 `usage-hourly-bucket` 分页）+
 * `docs/api/接口字段级schema.md` §1/§2 + `11-同步与用量统计PRD` §4（对账指标）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>**不得用 0 冒充没有数据**：窗口内无桶 → 指标回 {@code null}（前端渲染占位符），不是 0</li>
 *   <li>窗口半开 {@code [from, to)}；`month` 模式 = 当月 1 日 00:00Z 起、次月 1 日 00:00Z 止</li>
 *   <li>供应商端只看本人 provider（跨供应商必须隔离）；管理端看全量并可按下钻维度过滤</li>
 * </ul>
 */
class UsageContractTest extends ApiTestBase {

    private static final String PHONE = "13800000070";
    private static final String OTHER_PHONE = "13800000071";

    /** 与 `application-test.yml` 的 `app.usage.log-file` 一致（本项目 mock 日志源适配器） */
    private static final Path LOG_FIXTURE =
            Path.of(System.getProperty("java.io.tmpdir"), "aap-usage-log-fixture.json");

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    // ------------------------------------------------------------------ 工具

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

    /** 本用例内已注册的 provider 主键（truncateAll 后按 id 升序 = 注册顺序）。 */
    private List<Long> providerIds() {
        return jdbc.queryForList("select id from aap_provider order by id", Long.class);
    }

    private long onlyProviderId() {
        List<Long> ids = providerIds();
        assertThat(ids).as("前置：本用例只应有一个供应商主体").hasSize(1);
        return ids.get(0);
    }

    private String techOpsToken() {
        Long accountId = 940001L;
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'techops-usage', 'x', '技术运营', 'TECH_OPS', 'ACTIVE')
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

    /** 直接落一个用量小时桶（绕过聚合，聚焦接口语义；聚合链路由 ADM-U02 用例覆盖）。 */
    private void bucket(long id, String statHour, Long channelId, Long providerId, String model, String group,
                        long requests, long prompt, long completion, long total, long cacheRead,
                        long cacheWrite, long cacheWrite1h, long image, long audio, long video,
                        String quota, String cost, String tierDistribution, String cacheParseStatus,
                        String source, String collectedAt) {
        jdbc.update("""
                insert into aap_usage_hourly (id, stat_hour, channel_id, channel_name, provider_id, model_name,
                    group_name, request_count, prompt_tokens, completion_tokens, total_tokens, cache_read_tokens,
                    cache_write_tokens, cache_write_1h_tokens, image_input_tokens, audio_input_tokens,
                    video_input_tokens, quota_raw, cost_usd, tier_distribution, cache_parse_status, source,
                    collected_at)
                values (?, ?::timestamptz, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::numeric, ?::numeric,
                        ?::jsonb, ?, ?, ?::timestamptz)
                """, id, statHour, channelId, "AAP-测试渠道-1", providerId, model, group, requests, prompt,
                completion, total, cacheRead, cacheWrite, cacheWrite1h, image, audio, video, quota, cost,
                tierDistribution, cacheParseStatus, source, collectedAt);
    }

    /** 六月窗口的标准数据：A/B 在 2026-06-01（gpt-4o），C 落 2026-05-31（上月，用于环比）。 */
    private void juneData(long providerId) {
        bucket(700001L, "2026-06-01T00:00:00Z", 1001L, providerId, "gpt-4o", "default",
                10L, 1000L, 500L, 1500L, 2000L, 100L, 50L, 30L, 20L, 10L,
                "12.5", "3.0", "{\"t1_base\":120000,\"t2_long\":8000}", "OK", "LOG_DB", "2026-06-01T01:10:00Z");
        bucket(700002L, "2026-06-01T05:00:00Z", 1001L, providerId, "gpt-4o", "default",
                5L, 400L, 100L, 500L, 0L, 0L, 0L, 0L, 0L, 0L,
                "2.5", "1.0", "{\"t1_base\":20000}", "NO_CACHE_FIELD", "LOG_DB", "2026-06-01T06:10:00Z");
        bucket(700003L, "2026-05-31T23:00:00Z", 1001L, providerId, "gpt-4o", "default",
                7L, 700L, 300L, 1000L, 500L, 0L, 0L, 0L, 0L, 0L,
                "5.0", "99.0", null, "OK", "LOG_DB", "2026-06-01T00:10:00Z");
    }

    private static boolean isNullish(JsonNode node) {
        return node == null || node.isNull() || node.isMissingNode();
    }

    // ------------------------------------------------------------------ USE-01

    @Test
    @DisplayName("USE-01 无数据窗口：指标全 null（不臆造 0）、模型/逐日空数组、窗口与 provider_id 必备")
    void summaryWithoutDataReturnsNulls() {
        String token = token(PHONE);
        long providerId = onlyProviderId();

        HttpResult res = get("/usage/summary?startHour=2026-06-01T00:00:00Z&endHour=2026-06-02T00:00:00Z", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        SchemaAssert.assertModel("usage-summary", json(res.data()));

        JsonNode data = res.data();
        assertThat(data.path("provider_id").asText()).isEqualTo(String.valueOf(providerId));
        assertThat(data.path("stat_from").asText()).isEqualTo("2026-06-01T00:00:00Z");
        assertThat(data.path("stat_to").asText()).isEqualTo("2026-06-02T00:00:00Z");
        assertThat(data.path("degraded").asBoolean()).isFalse();
        for (String field : List.of("request_count", "total_tokens", "prompt_tokens", "completion_tokens",
                "cache_read_tokens", "cache_hit_rate", "cache_parse_rate", "quota_raw", "cost_usd",
                "amount_total", "mom_rate", "mom_saved_amount", "actual_unit_price", "deviation_rate",
                "cost", "updated_at")) {
            assertThat(isNullish(data.path(field))).as("空窗口的 %s 必须是 null（禁止用 0 冒充无数据）", field).isTrue();
        }
        assertThat(data.path("models").isArray()).isTrue();
        assertThat(data.path("models").size()).isZero();
        assertThat(data.path("daily").isArray()).isTrue();
        assertThat(data.path("daily").size()).isZero();
    }

    @Test
    @DisplayName("USE-01 month 模式聚合口径：六类词元/缓存三件套/额度/金额求和、命中率、逐日、模型占比、档位分布、环比")
    void summaryAggregatesMonthWindow() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        juneData(providerId);

        HttpResult res = get("/usage/summary?month=2026-06", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertModel("usage-summary", json(res.data()));
        JsonNode data = res.data();

        assertThat(data.path("month").asText()).isEqualTo("2026-06");
        assertThat(data.path("stat_from").asText()).isEqualTo("2026-06-01T00:00:00Z");
        assertThat(data.path("stat_to").asText()).isEqualTo("2026-07-01T00:00:00Z");
        // A + B（5 月桶 C 不得计入）
        assertThat(data.path("request_count").asLong()).isEqualTo(15L);
        assertThat(data.path("prompt_tokens").asLong()).isEqualTo(1400L);
        assertThat(data.path("completion_tokens").asLong()).isEqualTo(600L);
        assertThat(data.path("total_tokens").asLong()).isEqualTo(2000L);
        assertThat(data.path("cache_read_tokens").asLong()).isEqualTo(2000L);
        assertThat(data.path("cache_write_tokens").asLong()).isEqualTo(100L);
        assertThat(data.path("cache_write_1h_tokens").asLong()).isEqualTo(50L);
        assertThat(data.path("image_input_tokens").asLong()).isEqualTo(30L);
        assertThat(data.path("audio_input_tokens").asLong()).isEqualTo(20L);
        assertThat(data.path("video_input_tokens").asLong()).isEqualTo(10L);
        assertThat(data.path("quota_raw").decimalValue()).isEqualByComparingTo("15.0");
        assertThat(data.path("cost_usd").decimalValue()).isEqualByComparingTo("4.0");
        assertThat(data.path("amount_total").decimalValue()).isEqualByComparingTo("4.0");
        // 命中率 = 2000/(1400+2000)；可解析率 = 1/2（AC-45 有一桶无缓存字段 → 降级标记）
        assertThat(data.path("cache_hit_rate").asDouble()).isCloseTo(2000.0 / 3400.0, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(data.path("cache_parse_rate").asDouble()).isEqualTo(0.5);
        assertThat(data.path("degraded").asBoolean()).isTrue();
        // 实际单价 = 4.0 /(2000/1e6)
        assertThat(data.path("actual_unit_price").decimalValue()).isEqualByComparingTo("2000");
        // 环比 vs 上月（99.0）：(4−99)/99；节省 = 99 − 4
        assertThat(data.path("mom_rate").asDouble()).isCloseTo(-95.0 / 99.0, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(data.path("mom_saved_amount").decimalValue()).isEqualByComparingTo("95.0");
        // 档位分布按 key 求和
        assertThat(data.path("tier_distribution").path("t1_base").decimalValue()).isEqualByComparingTo("140000");
        assertThat(data.path("tier_distribution").path("t2_long").decimalValue()).isEqualByComparingTo("8000");
        // 逐日：只有 06-01 一天
        assertThat(data.path("daily").size()).isEqualTo(1);
        SchemaAssert.assertModel("usage-daily", json(data.path("daily").get(0)));
        assertThat(data.path("daily").get(0).path("stat_date").asText()).isEqualTo("2026-06-01");
        assertThat(data.path("daily").get(0).path("total_tokens").asLong()).isEqualTo(2000L);
        assertThat(data.path("daily").get(0).path("request_count").asLong()).isEqualTo(15L);
        // 模型明细 + 占比（客户端 share 归一：小数即分数）
        assertThat(data.path("models").size()).isEqualTo(1);
        SchemaAssert.assertModel("usage-model", json(data.path("models").get(0)));
        assertThat(data.path("models").get(0).path("model_name").asText()).isEqualTo("gpt-4o");
        assertThat(data.path("models").get(0).path("amount").decimalValue()).isEqualByComparingTo("4.0");
        assertThat(data.path("models").get(0).path("share").asDouble()).isCloseTo(1.0, org.assertj.core.data.Offset.offset(1e-9));
        // 数据更新时间 = 桶的最新 collected_at（页脚「更新时间」）
        assertThat(data.path("updated_at").asText()).isEqualTo("2026-06-01T06:10:00Z");
        assertThat(data.path("refreshed_at").asText()).isNotBlank();
    }

    @Test
    @DisplayName("USE-01 默认窗口 = 当月整月（工作台本月汇总，未传 month/startHour/endHour）")
    void summaryDefaultsToCurrentMonth() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        LocalDate first = LocalDate.now(ZoneOffset.UTC).withDayOfMonth(1);
        bucket(700010L, first + "T03:00:00Z", 1001L, providerId, "gpt-4o", "default",
                2L, 100L, 50L, 150L, 0L, 0L, 0L, 0L, 0L, 0L,
                "0.5", "0.2", null, "OK", "LOG_DB", first + "T04:00:00Z");

        HttpResult res = get("/usage/summary", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        assertThat(res.data().path("month").asText()).isEqualTo(first.toString().substring(0, 7));
        assertThat(res.data().path("stat_from").asText()).isEqualTo(first + "T00:00:00Z");
        assertThat(res.data().path("stat_to").asText()).isEqualTo(first.plusMonths(1) + "T00:00:00Z");
        assertThat(res.data().path("request_count").asLong()).isEqualTo(2L);
        assertThat(res.data().path("amount_total").decimalValue()).isEqualByComparingTo("0.2");
    }

    @Test
    @DisplayName("USE-01 参数校验：缺一半窗口 / 逆序窗口 / 非法 month / 非法时间戳 → E-1001")
    void summaryValidatesWindow() {
        String token = token(PHONE);
        for (String query : List.of(
                "?startHour=2026-06-01T00:00:00Z",
                "?endHour=2026-06-02T00:00:00Z",
                "?startHour=2026-06-02T00:00:00Z&endHour=2026-06-01T00:00:00Z",
                "?month=2026-13",
                "?month=六月",
                "?startHour=2026-06-01T00:00:00Z&endHour=不是时间")) {
            HttpResult res = get("/usage/summary" + query, token);
            assertThat(res.status()).as("%s → %s", query, res.body()).isEqualTo(400);
            assertThat(res.code()).as(query).isEqualTo("E-1001");
        }
    }

    @Test
    @DisplayName("USE-01 跨供应商隔离：只统计本人 provider 的用量（同窗口内他人数据必须不可见）")
    void summaryIsScopedToOwnProvider() {
        String mine = token(PHONE);
        String other = token(OTHER_PHONE);
        List<Long> ids = providerIds();
        assertThat(ids).hasSize(2);
        long mineId = ids.get(0);
        long otherId = ids.get(1);

        bucket(700020L, "2026-06-01T00:00:00Z", 1001L, mineId, "gpt-4o", "default",
                1L, 100L, 0L, 100L, 0L, 0L, 0L, 0L, 0L, 0L, "1.0", "0.1", null, "OK", "LOG_DB",
                "2026-06-01T01:00:00Z");
        bucket(700021L, "2026-06-01T00:00:00Z", 1002L, otherId, "gpt-4o", "default",
                9L, 900L, 0L, 900L, 0L, 0L, 0L, 0L, 0L, 0L, "9.0", "9.9", null, "OK", "LOG_DB",
                "2026-06-01T01:00:00Z");

        JsonNode mineData = get("/usage/summary?month=2026-06", mine).data();
        assertThat(mineData.path("provider_id").asText()).isEqualTo(String.valueOf(mineId));
        assertThat(mineData.path("request_count").asLong()).isEqualTo(1L);
        assertThat(mineData.path("amount_total").decimalValue()).isEqualByComparingTo("0.1");

        JsonNode otherData = get("/usage/summary?month=2026-06", other).data();
        assertThat(otherData.path("provider_id").asText()).isEqualTo(String.valueOf(otherId));
        assertThat(otherData.path("request_count").asLong()).isEqualTo(9L);
        assertThat(otherData.path("amount_total").decimalValue()).isEqualByComparingTo("9.9");
    }

    @Test
    @DisplayName("USE-01 未认证 401（用量属供应商私有数据）")
    void summaryRequiresAuth() {
        HttpResult res = get("/usage/summary?month=2026-06");
        assertThat(res.status()).isEqualTo(401);
        assertThat(res.code()).isEqualTo("E-1902");
    }

    @Test
    @DisplayName("USE-01 对账差异率：有 APPROVED 报价为基准 → 差异率；无报价 → null；平台费率取已签署合同")
    void summaryDeviationAndPlatformFee() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        // 100 万 token / 2.0 USD → 实际单价 2.0 USD/1M；报价 input_price = 2.0 → 报价单价同为 2.0
        bucket(700030L, "2026-06-04T00:00:00Z", 1001L, providerId, "gpt-4o", "default",
                1L, 1000000L, 0L, 1000000L, 0L, 0L, 0L, 0L, 0L, 0L, "1.0", "2.0", null, "OK", "LOG_DB",
                "2026-06-04T01:00:00Z");

        JsonNode noQuote = get("/usage/summary?month=2026-06", token).data();
        assertThat(isNullish(noQuote.path("deviation_rate"))).as("无已审报价 → 不留臆造差异率").isTrue();
        assertThat(isNullish(noQuote.path("cost").path("platform_fee_rate"))).isTrue();

        jdbc.update("""
                insert into aap_quote (id, quote_no, provider_id, status, currency)
                values (900001, 'Q20260601000001', ?, 'APPROVED', 'USD')
                """, providerId);
        jdbc.update("""
                insert into aap_quote_item (id, quote_id, model_name, input_price, output_price, cache_read_price)
                values (900002, 900001, 'gpt-4o', 2.0, 4.0, 0.5)
                """);
        jdbc.update("""
                insert into aap_contract (id, contract_no, provider_id, status, platform_fee_rate, valid_from)
                values (960001, 'HT202606010001', ?, 'SIGNED', 0.08, '2026-01-01T00:00:00Z')
                """, providerId);

        JsonNode priced = get("/usage/summary?month=2026-06", token).data();
        assertThat(priced.path("deviation_rate").asDouble()).isEqualTo(0.0);
        assertThat(priced.path("cost").path("total").decimalValue()).isEqualByComparingTo("2.0");
        assertThat(priced.path("cost").path("platform_fee_rate").decimalValue()).isEqualByComparingTo("0.08");
        assertThat(priced.path("cost").path("platform_fee").decimalValue()).isEqualByComparingTo("0.16");
        SchemaAssert.assertModel("usage-cost", json(priced.path("cost")));

        // 实际涨到 2.5 USD → 差异率 = (2.5−2.0)/2.0
        jdbc.update("update aap_usage_hourly set cost_usd = 2.5 where id = 700030");
        JsonNode deviated = get("/usage/summary?month=2026-06", token).data();
        assertThat(deviated.path("deviation_rate").asDouble()).isCloseTo(0.25, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(UsageMetrics.deviationAlert(deviated.path("deviation_rate").asDouble()))
                .as("±5% 阈值告警（AC-46/11-PRD §4）").isTrue();
    }

    // ------------------------------------------------------------------ USE-02

    @Test
    @DisplayName("USE-02 分时用量：窗口半开、按小时排序、分页元数据、桶契约（含缓存三件套与解析状态）")
    void hourlyListPagedAndScoped() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        juneData(providerId);

        HttpResult res = get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(res.data()));
        assertThat(res.data().path("total").asLong()).isEqualTo(2L);
        assertThat(res.data().path("page").asInt()).isEqualTo(1);
        assertThat(res.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(res.data().path("items").size()).isEqualTo(2);

        JsonNode first = res.data().path("items").get(0);
        SchemaAssert.assertModel("usage-hourly-bucket", json(first));
        assertThat(first.path("stat_hour").asText()).isEqualTo("2026-06-01T00:00:00Z");
        assertThat(first.path("model_name").asText()).isEqualTo("gpt-4o");
        assertThat(first.path("channel_id").asText()).isEqualTo("1001");
        assertThat(first.path("provider_id").asText()).isEqualTo(String.valueOf(providerId));
        assertThat(first.path("cache_read_tokens").asLong()).isEqualTo(2000L);
        assertThat(first.path("cache_write_tokens").asLong()).isEqualTo(100L);
        assertThat(first.path("cache_write_1h_tokens").asLong()).isEqualTo(50L);
        assertThat(first.path("image_input_tokens").asLong()).isEqualTo(30L);
        assertThat(first.path("cache_parse_status").asText()).isEqualTo("OK");
        assertThat(first.path("source").asText()).isEqualTo("LOG_DB");
        assertThat(res.data().path("items").get(1).path("cache_parse_status").asText()).isEqualTo("NO_CACHE_FIELD");

        // 分页：pageSize=1 → 第 1 页 1 条、total 仍为 2
        HttpResult paged = get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&page=2&pageSize=1", token);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
        assertThat(paged.data().path("total").asLong()).isEqualTo(2L);
        assertThat(paged.data().path("items").get(0).path("stat_hour").asText()).isEqualTo("2026-06-01T05:00:00Z");

        // 维度过滤：model / group
        assertThat(get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&model=gpt-4o", token)
                .data().path("total").asLong()).isEqualTo(2L);
        assertThat(get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&model=gpt-4o-mini", token)
                .data().path("total").asLong()).isZero();
        assertThat(get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&group=另外分组", token)
                .data().path("total").asLong()).isZero();
    }

    @Test
    @DisplayName("USE-02 只回本人渠道；缺 from/to 或逆序 → E-1001；未认证 → 401")
    void hourlyScopeAndValidation() {
        String mine = token(PHONE);
        String other = token(OTHER_PHONE);
        List<Long> ids = providerIds();
        bucket(700040L, "2026-06-01T00:00:00Z", 1001L, ids.get(0), "gpt-4o", "default",
                1L, 1L, 1L, 2L, 0L, 0L, 0L, 0L, 0L, 0L, "0.1", "0.1", null, "OK", "LOG_DB",
                "2026-06-01T01:00:00Z");
        bucket(700041L, "2026-06-01T00:00:00Z", 1002L, ids.get(1), "gpt-4o", "default",
                1L, 1L, 1L, 2L, 0L, 0L, 0L, 0L, 0L, 0L, "0.1", "0.1", null, "OK", "LOG_DB",
                "2026-06-01T01:00:00Z");

        HttpResult mineRes = get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z", mine);
        assertThat(mineRes.data().path("total").asLong()).isEqualTo(1L);
        assertThat(mineRes.data().path("items").get(0).path("provider_id").asText())
                .isEqualTo(String.valueOf(ids.get(0)));
        assertThat(get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z", other)
                .data().path("items").get(0).path("provider_id").asText()).isEqualTo(String.valueOf(ids.get(1)));

        assertThat(get("/usage/hourly?from=2026-06-01T00:00:00Z", mine).status()).isEqualTo(400);
        assertThat(get("/usage/hourly?to=2026-06-01T00:00:00Z", mine).status()).isEqualTo(400);
        HttpResult reversed = get("/usage/hourly?from=2026-06-02T00:00:00Z&to=2026-06-01T00:00:00Z", mine);
        assertThat(reversed.status()).isEqualTo(400);
        assertThat(reversed.code()).isEqualTo("E-1001");
        assertThat(get("/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z").status()).isEqualTo(401);
    }

    // ------------------------------------------------------------------ ADM-U01

    @Test
    @DisplayName("ADM-U01 管理端分时用量：供应商 403 / 未认证 401；TECH_OPS 全量可见并按 providerId/channelId/model 下钻")
    void adminHourlyCrossProviderAndFilters() {
        String admin = techOpsToken();
        String supplier = token(PHONE);
        String other = token(OTHER_PHONE);
        List<Long> ids = providerIds();
        assertThat(ids).hasSize(2);
        juneData(ids.get(0));
        bucket(700050L, "2026-06-01T00:00:00Z", 1002L, ids.get(1), "claude-3-5-sonnet", "default",
                4L, 400L, 100L, 500L, 0L, 0L, 0L, 0L, 0L, 0L, "1.0", "0.5", null, "OK", "LOG_DB",
                "2026-06-01T01:00:00Z");

        HttpResult all = get("/admin/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z", admin);
        assertThat(all.status()).as(all.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(all.data()));
        assertThat(all.data().path("total").asLong()).isEqualTo(3L);
        SchemaAssert.assertModel("usage-hourly-bucket", json(all.data().path("items").get(0)));

        assertThat(get("/admin/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&providerId=" + ids.get(1), admin)
                .data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&channelId=1002", admin)
                .data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z&model=gpt-4o", admin)
                .data().path("total").asLong()).isEqualTo(2L);
        assertThat(get("/admin/usage/hourly?from=2026-06-02T00:00:00Z&to=2026-06-03T00:00:00Z", admin)
                .data().path("total").asLong()).isZero();

        assertThat(get("/admin/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z", supplier).status())
                .isEqualTo(403);
        assertThat(get("/admin/usage/hourly?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z").status())
                .isEqualTo(401);
        assertThat(other).isNotBlank();
    }

    // ------------------------------------------------------------------ ADM-U02

    @Test
    @DisplayName("ADM-U02 用量聚合 UPSERT：AC-43 缓存字段落库、AC-45 无缓存字段标 NO_CACHE_FIELD、AC-44 幂等重跑")
    void refreshIsIdempotentUpsert() throws Exception {
        String admin = techOpsToken();
        String supplier = token(PHONE);
        long providerId = onlyProviderId();

        writeLogFixture(providerId, "0.9", "0.4");
        HttpResult first = post("/admin/usage/refresh", """
                {"from":"2026-06-03T00:00:00Z","to":"2026-06-04T00:00:00Z"}
                """, admin);
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        SchemaAssert.assertModel("usage-refresh-result", json(first.data()));
        assertThat(first.data().path("inserted").asInt()).isEqualTo(2);
        assertThat(first.data().path("updated").asInt()).isZero();
        assertThat(first.data().path("batch_total").asInt()).isEqualTo(2);
        assertThat(first.data().path("batch_id").asText()).isNotBlank();
        assertThat(first.data().path("cache_parse_status").asText()).isEqualTo("NO_CACHE_FIELD");

        // AC-43 缓存三件套 + 多模态字段落库
        assertThat(jdbc.queryForObject("select cache_read_tokens from aap_usage_hourly where model_name = 'gpt-4o'",
                Long.class)).isEqualTo(300L);
        assertThat(jdbc.queryForObject("select cache_write_tokens from aap_usage_hourly where model_name = 'gpt-4o'",
                Long.class)).isEqualTo(10L);
        assertThat(jdbc.queryForObject("select cache_write_1h_tokens from aap_usage_hourly where model_name = 'gpt-4o'",
                Long.class)).isEqualTo(5L);
        assertThat(jdbc.queryForObject("select tier_distribution->>'t1_base' from aap_usage_hourly where model_name = 'gpt-4o'",
                String.class)).isEqualTo("9000");
        // AC-45 无缓存字段的桶标 NO_CACHE_FIELD（枚举真源：生成器 CacheParseStatus = OK/NO_CACHE_FIELD）
        assertThat(jdbc.queryForObject(
                "select cache_parse_status from aap_usage_hourly where model_name = 'claude-3-5-sonnet'",
                String.class)).isEqualTo("NO_CACHE_FIELD");
        // 同步游标留痕
        assertThat(jdbc.queryForObject("select last_batch_id::text from aap_usage_sync_cursor where data_source = 'LOG_API'",
                String.class)).isEqualTo(first.data().path("batch_id").asText());

        // AC-44 幂等重跑：同窗口同数据 → 不新增行、全部计入 updated
        HttpResult second = post("/admin/usage/refresh", """
                {"from":"2026-06-03T00:00:00Z","to":"2026-06-04T00:00:00Z"}
                """, admin);
        assertThat(second.status()).as(second.body()).isEqualTo(200);
        assertThat(second.data().path("inserted").asInt()).isZero();
        assertThat(second.data().path("updated").asInt()).isEqualTo(2);
        assertThat(jdbc.queryForObject("select count(*) from aap_usage_hourly", Long.class)).isEqualTo(2L);
        assertThat(jdbc.queryForObject("select cost_usd from aap_usage_hourly where model_name = 'gpt-4o'",
                java.math.BigDecimal.class)).isEqualByComparingTo("0.9");

        // 源数据变化 → UPSERT 覆盖（不是新增一行）
        writeLogFixture(providerId, "1.2", "0.4");
        HttpResult third = post("/admin/usage/refresh", """
                {"from":"2026-06-03T00:00:00Z","to":"2026-06-04T00:00:00Z"}
                """, admin);
        assertThat(third.data().path("inserted").asInt()).isZero();
        assertThat(third.data().path("updated").asInt()).isEqualTo(2);
        assertThat(jdbc.queryForObject("select count(*) from aap_usage_hourly", Long.class)).isEqualTo(2L);
        assertThat(jdbc.queryForObject("select cost_usd from aap_usage_hourly where model_name = 'gpt-4o'",
                java.math.BigDecimal.class)).isEqualByComparingTo("1.2");

        // 权限：供应商不可触发聚合（TECH_OPS/SUPER_ADMIN）
        assertThat(post("/admin/usage/refresh", "{}", supplier).status()).isEqualTo(403);
        assertThat(post("/admin/usage/refresh", "{}").status()).isEqualTo(401);
    }

    /** 本项目 mock 日志源适配器的输入（`app.usage.log-file`）：小时桶列表，字段同字典。 */
    private void writeLogFixture(long providerId, String costGpt, String costClaude) throws Exception {
        String json = """
                {"buckets":[
                  {"stat_hour":"2026-06-03T00:00:00Z","channel_id":1001,"channel_name":"AAP-测试渠道-1","provider_id":"%d",
                   "model_name":"gpt-4o","group_name":"default","request_count":7,"prompt_tokens":700,
                   "completion_tokens":200,"total_tokens":900,"cache_read_tokens":300,"cache_write_tokens":10,
                   "cache_write_1h_tokens":5,"image_input_tokens":0,"audio_input_tokens":0,"video_input_tokens":0,
                   "quota_raw":1.5,"cost_usd":%s,"cache_parse_status":"OK","source":"LOG_API",
                   "tier_distribution":{"t1_base":9000},"collected_at":"2026-06-03T02:00:00Z"},
                  {"stat_hour":"2026-06-03T01:00:00Z","channel_id":1001,"channel_name":"AAP-测试渠道-1","provider_id":"%d",
                   "model_name":"claude-3-5-sonnet","group_name":"default","request_count":3,"prompt_tokens":300,
                   "completion_tokens":100,"total_tokens":400,"quota_raw":0.6,"cost_usd":%s,
                   "cache_parse_status":"NO_CACHE_FIELD","source":"LOG_API","collected_at":"2026-06-03T03:00:00Z"}
                ]}
                """.formatted(providerId, costGpt, providerId, costClaude);
        Files.createDirectories(LOG_FIXTURE.getParent());
        Files.writeString(LOG_FIXTURE, json, StandardCharsets.UTF_8);
    }
}
