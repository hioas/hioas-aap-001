package com.hioas.aap.quote;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * T14 · 管理端报价历史对比（ADM-Q02）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4（`ADM-Q02` `GET /admin/quotes/compare`
 * `q：quoteIds(逗号) → {items:[QuoteCompare]}`（旧值/新值/涨跌幅））+ `json-schema/models/quote-compare.schema.json`
 * + `.calicat/prd/13-管理端PRD.md` §5.3/§5.6「报价历史对比：该供应商历次报价」（运营商务 + 超管可看）。
 *
 * <p>硬口径（偏差 D-ADM-02 已记入 `aap-server-tdd-state.md`）：
 * <ul>
 *   <li>`quoteIds` 逗号分隔、**按「旧 → 新」顺序**；比较**首单**与**末单**的明细价（≥2 个才成立，否则 400 `E-1001`）</li>
 *   <li>`items` 以两侧 `model_name` 并集为基准、按模型名升序；单侧缺失则该侧值为 `null`、`change_rate` 也为 `null`
 *       （不臆造涨跌幅）；`old_value = 0` 同样回 `null`（避免除零）</li>
 *   <li>`change_rate` 是**百分数**（25.0000 = +25%），四位小数 HALF_UP；`field` 用数据字典列名</li>
 *   <li>非法 ID / 少于 2 个 400 `E-1001`；不存在的报价单 404 `E-1406`（沿用全局语义，清单未列错误码）</li>
 *   <li>权限：`BIZ_OPERATOR` + `SUPER_ADMIN`；技术运营按清单不参与经营对比 → 403 `E-1901`</li>
 * </ul>
 */
class AdminQuoteCompareContractTest extends ApiTestBase {

    private static final String SUPPLIER_PHONE = "13800000230";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private String adminToken(long accountId, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', ?, ?, 'ACTIVE')
                """, accountId, role.toLowerCase() + "-" + accountId, role, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String supplierToken() {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(SUPPLIER_PHONE));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(SUPPLIER_PHONE, send.data().path("dev_code").asText()));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    private void insertQuote(long id, String quoteNo, String status, int itemCount, String createdAt) {
        jdbc.update("""
                insert into aap_quote (id, quote_no, provider_id, status, current_version, currency, item_count,
                    created_at, updated_at, deleted, version)
                values (?, ?, 850001, ?, 1, 'USD', ?, ?::timestamptz, ?::timestamptz, false, 0)
                """, id, quoteNo, status, itemCount, createdAt, createdAt);
    }

    private void insertItem(long id, long quoteId, String modelName, String inputPrice, String outputPrice) {
        jdbc.update("""
                insert into aap_quote_item (id, quote_id, model_name, input_price, output_price, compile_status,
                    created_at, updated_at, deleted, version)
                values (?, ?, ?, ?::numeric, ?::numeric, 'NOT_COMPILED', now(), now(), false, 0)
                """, id, quoteId, modelName, inputPrice, outputPrice);
    }

    /** 夹具：旧单 710001（gpt-4o 2.0/8.0、claude 3.0/—）、新单 710002（gpt-4o 2.5/7.0、mini 0.5/—）、
     *  更晚的 710003（仅 gpt-4o 输入 3.0）用于「多单取首末」。 */
    private void insertHistory() {
        insertQuote(710001, "QT20260901000001", "SUBMITTED", 2, "2026-09-01T00:00:00Z");
        insertQuote(710002, "QT20260915000001", "SUBMITTED", 2, "2026-09-15T00:00:00Z");
        insertQuote(710003, "QT20260918000001", "SUBMITTED", 1, "2026-09-18T00:00:00Z");
        insertItem(710011, 710001, "gpt-4o", "2.000000", "8.000000");
        insertItem(710012, 710001, "claude-3-5-sonnet", "3.000000", null);
        insertItem(710021, 710002, "gpt-4o", "2.500000", "7.000000");
        insertItem(710022, 710002, "gpt-4o-mini", "0.500000", null);
        insertItem(710031, 710003, "gpt-4o", "3.000000", null);
    }

    private static JsonNode find(JsonNode items, String modelName, String field) {
        for (JsonNode item : items) {
            if (modelName.equals(item.path("model_name").asText()) && field.equals(item.path("field").asText())) {
                return item;
            }
        }
        throw new AssertionError("对比结果里缺少 " + modelName + "/" + field + "：" + items);
    }

    @Test
    @DisplayName("ADM-Q02 报价历史对比：旧值/新值/涨跌幅（模型并集、单侧缺失为 null）、逐条符合 quote-compare")
    void compareTwoQuotes() {
        String biz = adminToken(970401L, "BIZ_OPERATOR");
        insertHistory();

        HttpResult res = get("/admin/quotes/compare?quoteIds=710001,710002", biz);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        JsonNode items = res.data().path("items");
        assertThat(items.size()).as("模型并集 × 出现的价字段：claude 1 + gpt-4o 2 + mini 1").isEqualTo(4);
        for (JsonNode item : items) {
            SchemaAssert.assertModel("quote-compare", json(item));
        }

        JsonNode gptInput = find(items, "gpt-4o", "input_price");
        assertThat(gptInput.path("old_value").asDouble()).isEqualTo(2.0);
        assertThat(gptInput.path("new_value").asDouble()).isEqualTo(2.5);
        assertThat(gptInput.path("change_rate").asDouble()).as("涨跌幅为百分数：+25%").isEqualTo(25.0);

        JsonNode gptOutput = find(items, "gpt-4o", "output_price");
        assertThat(gptOutput.path("old_value").asDouble()).isEqualTo(8.0);
        assertThat(gptOutput.path("new_value").asDouble()).isEqualTo(7.0);
        assertThat(gptOutput.path("change_rate").asDouble()).as("降价 → 负涨跌幅：-12.5%").isEqualTo(-12.5);

        JsonNode claudeInput = find(items, "claude-3-5-sonnet", "input_price");
        assertThat(claudeInput.path("old_value").asDouble()).isEqualTo(3.0);
        assertThat(claudeInput.path("new_value").isNull()).as("新单已下架该模型 → 新值为 null").isTrue();
        assertThat(claudeInput.path("change_rate").isNull()).as("单侧缺失不臆造涨跌幅").isTrue();

        JsonNode miniInput = find(items, "gpt-4o-mini", "input_price");
        assertThat(miniInput.path("old_value").isNull()).isTrue();
        assertThat(miniInput.path("new_value").asDouble()).isEqualTo(0.5);
        assertThat(miniInput.path("change_rate").isNull()).isTrue();

        // 三个 id：取首末（710001 → 710003）
        HttpResult three = get("/admin/quotes/compare?quoteIds=710001,710002,710003", biz);
        assertThat(three.status()).as(three.body()).isEqualTo(200);
        JsonNode threeItems = three.data().path("items");
        assertThat(threeItems.size()).as("首末两单：claude 输入、gpt-4o 输入/输出").isEqualTo(3);
        JsonNode raised = find(threeItems, "gpt-4o", "input_price");
        assertThat(raised.path("old_value").asDouble()).isEqualTo(2.0);
        assertThat(raised.path("new_value").asDouble()).isEqualTo(3.0);
        assertThat(raised.path("change_rate").asDouble()).as("+50%").isEqualTo(50.0);

        // 单模型两侧都缺价的字段不出现（避免噪声行）
        for (JsonNode item : threeItems) {
            assertThat(item.path("old_value").isNull() && item.path("new_value").isNull())
                    .as("不得输出两侧都为空的价字段").isFalse();
        }
    }

    @Test
    @DisplayName("ADM-Q02 入参校验：缺 quoteIds / 少于 2 个 / 非数字 → 400 E-1001；不存在报价单 → 404 E-1406")
    void compareValidatesInput() {
        String biz = adminToken(970411L, "BIZ_OPERATOR");
        insertHistory();

        HttpResult missing = get("/admin/quotes/compare", biz);
        assertThat(missing.status()).as(missing.body()).isEqualTo(400);
        assertThat(missing.code()).isEqualTo("E-1001");
        HttpResult blank = get("/admin/quotes/compare?quoteIds=", biz);
        assertThat(blank.status()).as(blank.body()).isEqualTo(400);
        assertThat(blank.code()).isEqualTo("E-1001");
        HttpResult single = get("/admin/quotes/compare?quoteIds=710001", biz);
        assertThat(single.status()).as("至少两个报价单才能对比：%s", single.body()).isEqualTo(400);
        assertThat(single.code()).isEqualTo("E-1001");
        HttpResult badId = get("/admin/quotes/compare?quoteIds=710001,abc", biz);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");
        HttpResult unknown = get("/admin/quotes/compare?quoteIds=710001,999999", biz);
        assertThat(unknown.status()).as(unknown.body()).isEqualTo(404);
        assertThat(unknown.code()).isEqualTo("E-1406");
    }

    @Test
    @DisplayName("ADM-Q02 权限：BIZ_OPERATOR/SUPER_ADMIN 可用；TECH_OPS 与供应商 403 E-1901、未认证 401 E-1902")
    void permissions() {
        String supplier = supplierToken();
        String biz = adminToken(970421L, "BIZ_OPERATOR");
        String techOps = adminToken(970422L, "TECH_OPS");
        String superAdmin = adminToken(970423L, "SUPER_ADMIN");
        insertHistory();

        assertThat(get("/admin/quotes/compare?quoteIds=710001,710002", biz).status()).isEqualTo(200);
        assertThat(get("/admin/quotes/compare?quoteIds=710001,710002", superAdmin).status()).isEqualTo(200);

        HttpResult techDenied = get("/admin/quotes/compare?quoteIds=710001,710002", techOps);
        assertThat(techDenied.status()).as(techDenied.body()).isEqualTo(403);
        assertThat(techDenied.code()).isEqualTo("E-1901");
        HttpResult supplierDenied = get("/admin/quotes/compare?quoteIds=710001,710002", supplier);
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        HttpResult anonymous = get("/admin/quotes/compare?quoteIds=710001,710002");
        assertThat(anonymous.status()).as(anonymous.body()).isEqualTo(401);
        assertThat(anonymous.code()).isEqualTo("E-1902");
    }
}
