package com.hioas.aap.support;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * T13 · 站内信与审计查询验收（NTF-01/02、ADM-A01）。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §1.7（NTF-01/02）+ §2.4（ADM-A01）、
 * `docs/backend/json-schema/models/{notification,notification-read,audit-log}.schema.json`、
 * 客户端消费口径 `aap-client/src/utils/messages-model.ts`（读 `data.items[]`，单条读
 * `id/title/content/created_at/read_at/event_code/biz_type/biz_id/kind`）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>站内信按「收件人作用域」隔离：供应商只看 `recipient_type=PROVIDER` + 本人 provider，
 *       管理端只看 `ADMIN` + 本人账号（跨主体不可见，且未认证 401）</li>
 *   <li>`unread_count` = 本人**未读总数**（与 `unread/category` 过滤无关）；列表明细另受过滤影响</li>
 *   <li>NTF-02 的写与读回**同源**：条件 UPDATE + 读回落库值（避免「响应说已读、库里没改」）</li>
 *   <li>ADM-A01 是审计真源的可检索视图：真实业务动作（如登录）产生的审计行必须能查到</li>
 * </ul>
 */
class NotificationContractTest extends ApiTestBase {

    private static final String PHONE = "13800000080";
    private static final String OTHER_PHONE = "13800000081";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    // ------------------------------------------------------------------ 工具

    /** 供应商短信登录（同时会产生 1 条 AUTH_LOGIN 审计）。 */
    private HttpResult smsLogin(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login;
    }

    private String token(String phone) {
        return smsLogin(phone).data().path("token").asText();
    }

    /** 管理端令牌（直接签发，不产生登录审计，便于断言确定性）。 */
    private String adminToken(long accountId, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', '巡检账号', ?, 'ACTIVE')
                """, accountId, role.toLowerCase() + "-" + accountId, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private List<Long> providerIds() {
        return jdbc.queryForList("select id from aap_provider order by id", Long.class);
    }

    private long onlyProviderId() {
        List<Long> ids = providerIds();
        assertThat(ids).as("前置：本用例只应有一个供应商主体").hasSize(1);
        return ids.get(0);
    }

    private void notif(long id, String recipientType, long recipientId, String title, String category,
                       String eventCode, String bizType, Long bizId, String readAt, String createdAt) {
        jdbc.update("""
                insert into aap_notification (id, recipient_type, recipient_id, channel, event_code, title, content,
                    biz_type, biz_id, category, read_at, status, created_at, updated_at, deleted, version)
                values (?, ?, ?, 'INBOX', ?, ?, ?, ?, ?, ?, ?::timestamptz, 'SENT', ?::timestamptz, ?::timestamptz,
                        false, 0)
                """, id, recipientType, recipientId, eventCode, title, title + "（内容已脱敏）", bizType, bizId,
                category, readAt, createdAt, createdAt);
    }

    private void audit(long id, String traceId, String actorType, Long actorId, String action, String targetType,
                       Long targetId, String summary, String before, String after, String risk, String createdAt) {
        jdbc.update("""
                insert into aap_audit_log (id, trace_id, actor_type, actor_id, actor_name, actor_ip, user_agent,
                    action, target_type, target_id, summary, before_value, after_value, result, risk_level,
                    created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, '127.0.0.1', 'JUnit', ?, ?, ?, ?, ?::jsonb, ?::jsonb, 'SUCCESS', ?,
                        ?::timestamptz, ?::timestamptz, false, 0)
                """, id, traceId, actorType, actorId, actorType + "#" + actorId, action, targetType, targetId,
                summary, before, after, risk, createdAt, createdAt);
    }

    private static boolean isNullish(JsonNode node) {
        return node == null || node.isNull() || node.isMissingNode();
    }

    // ------------------------------------------------------------------ NTF-01

    @Test
    @DisplayName("NTF-01 列表契约：本人通知倒序分页、unread_count 只计未读、字段对齐客户端（kind/read_at）")
    void listContract() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        notif(800001L, "PROVIDER", providerId, "检测通过", "SYSTEM", "DETECTION_PASSED", "DETECTION", 900001L,
                null, "2026-06-01T00:00:00Z");
        notif(800002L, "PROVIDER", providerId, "报价已通过", "ORDER", "QUOTE_APPROVED", "QUOTE", 900002L,
                null, "2026-06-02T00:00:00Z");
        notif(800003L, "PROVIDER", providerId, "合同已签署", "ORDER", "CONTRACT_SIGNED", "CONTRACT", 900003L,
                "2026-06-02T01:00:00Z", "2026-06-03T00:00:00Z");

        HttpResult res = get("/notifications", token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        SchemaAssert.assertPageMeta(json(res.data()));
        assertThat(res.data().path("page").asInt()).isEqualTo(1);
        assertThat(res.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(res.data().path("total").asLong()).isEqualTo(3L);
        assertThat(res.data().path("unread_count").asLong()).isEqualTo(2L);

        // 排序：created_at desc, id desc → 最新一份在最前
        JsonNode items = res.data().path("items");
        assertThat(items.size()).isEqualTo(3);
        assertThat(items.get(0).path("id").asText()).isEqualTo("800003");
        assertThat(items.get(1).path("id").asText()).isEqualTo("800002");
        assertThat(items.get(2).path("id").asText()).isEqualTo("800001");

        JsonNode read = items.get(0);
        SchemaAssert.assertModel("notification", json(read));
        assertThat(read.path("title").asText()).isEqualTo("合同已签署");
        assertThat(read.path("content").asText()).isNotBlank();
        assertThat(read.path("event_code").asText()).isEqualTo("CONTRACT_SIGNED");
        assertThat(read.path("biz_type").asText()).isEqualTo("CONTRACT");
        assertThat(read.path("biz_id").asText()).isEqualTo("900003");
        assertThat(read.path("category").asText()).isEqualTo("ORDER");
        assertThat(read.path("status").asText()).isEqualTo("SENT");
        assertThat(read.path("channel").asText()).isEqualTo("INBOX");
        assertThat(read.path("kind").asText()).isEqualTo("contract");
        assertThat(read.path("read_at").asText()).isNotBlank();
        assertThat(read.path("read").asBoolean()).isTrue();
        assertThat(read.path("is_read").asBoolean()).isTrue();
        assertThat(read.path("created_at").asText()).isEqualTo("2026-06-03T00:00:00Z");

        // 未读一条：read/read_at 双口径一致；kind 由 event_code 派生（客户端图标）
        JsonNode unread = items.get(1);
        SchemaAssert.assertModel("notification", json(unread));
        assertThat(unread.path("kind").asText()).isEqualTo("quote");
        assertThat(isNullish(unread.path("read_at"))).isTrue();
        assertThat(unread.path("read").asBoolean()).isFalse();
        assertThat(unread.path("is_read").asBoolean()).isFalse();
        assertThat(items.get(2).path("kind").asText()).isEqualTo("detect");
    }

    @Test
    @DisplayName("NTF-01 过滤与作用域：unread/category 过滤、分页元数据不变、跨供应商与跨主体隔离")
    void listFiltersAndScope() {
        String mine = token(PHONE);
        String other = token(OTHER_PHONE);
        List<Long> ids = providerIds();
        assertThat(ids).hasSize(2);
        notif(800011L, "PROVIDER", ids.get(0), "系统公告", "SYSTEM", "SYSTEM_NOTICE", "SYSTEM", null,
                null, "2026-06-01T00:00:00Z");
        notif(800012L, "PROVIDER", ids.get(0), "已读公告", "SYSTEM", "SYSTEM_NOTICE", "SYSTEM", null,
                "2026-06-01T01:00:00Z", "2026-06-01T00:30:00Z");
        notif(800013L, "PROVIDER", ids.get(0), "打款到账", "ORDER", "PAYMENT_CONFIRMED", "PAYMENT", 900013L,
                null, "2026-06-02T00:00:00Z");
        notif(800014L, "PROVIDER", ids.get(1), "他人通知", "SYSTEM", "SYSTEM_NOTICE", "SYSTEM", null,
                null, "2026-06-02T00:00:00Z");
        long adminId = 950001L;
        String admin = adminToken(adminId, "TECH_OPS");
        notif(800015L, "ADMIN", adminId, "管理端通知", "SYSTEM", "SYSTEM_NOTICE", "SYSTEM", null,
                null, "2026-06-02T00:00:00Z");

        // unread=true → 只看未读（不含已读的 800012）
        HttpResult unreadOnly = get("/notifications?unread=true", mine);
        assertThat(unreadOnly.status()).as(unreadOnly.body()).isEqualTo(200);
        assertThat(unreadOnly.data().path("total").asLong()).isEqualTo(2L);
        assertThat(unreadOnly.data().path("unread_count").asLong()).isEqualTo(2L);
        assertThat(unreadOnly.data().path("items").size()).isEqualTo(2);

        // category=ORDER（客户端 chip 取值）→ 仅订单类，unread_count 仍是本人未读总数
        HttpResult orderOnly = get("/notifications?category=ORDER", mine);
        assertThat(orderOnly.data().path("total").asLong()).isEqualTo(1L);
        assertThat(orderOnly.data().path("items").get(0).path("id").asText()).isEqualTo("800013");
        assertThat(orderOnly.data().path("unread_count").asLong())
                .as("unread_count 是本人未读总数，不受列表过滤影响（避免徽标数随筛选跳动）").isEqualTo(2L);

        assertThat(get("/notifications?category=SYSTEM&unread=true", mine).data().path("total").asLong())
                .isEqualTo(1L);
        assertThat(get("/notifications?category=ORDER&unread=true", mine).data().path("total").asLong())
                .as("ORDER 且未读 → 800013 一条（800012 已读不计）").isEqualTo(1L);
        assertThat(get("/notifications?category=ORDER&unread=false", mine).data().path("total").asLong())
                .isZero();

        // 分页：total 与 unread_count 不随分页变化；越界页空集
        HttpResult paged = get("/notifications?page=2&pageSize=2", mine);
        assertThat(paged.data().path("page").asInt()).isEqualTo(2);
        assertThat(paged.data().path("pageSize").asInt()).isEqualTo(2);
        assertThat(paged.data().path("total").asLong()).isEqualTo(3L);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
        assertThat(get("/notifications?page=3&pageSize=2", mine).data().path("items").size()).isZero();

        // 跨供应商隔离：他人只看到自己的 1 条
        HttpResult otherRes = get("/notifications", other);
        assertThat(otherRes.data().path("total").asLong()).isEqualTo(1L);
        assertThat(otherRes.data().path("items").get(0).path("id").asText()).isEqualTo("800014");

        // 跨主体隔离：管理端收件箱看不到供应商通知（且不是 403，NTF-01 对已认证主体开放）
        HttpResult adminRes = get("/notifications", admin);
        assertThat(adminRes.status()).as(adminRes.body()).isEqualTo(200);
        assertThat(adminRes.data().path("total").asLong()).isEqualTo(1L);
        assertThat(adminRes.data().path("items").get(0).path("id").asText()).isEqualTo("800015");
    }

    @Test
    @DisplayName("NTF-01 参数与认证：未认证 401、脏分页夹取（page=0→1、pageSize=1000→200）、unread 非法值 400")
    void listParamsAndAuth() {
        String token = token(PHONE);
        onlyProviderId();

        assertThat(get("/notifications").status()).isEqualTo(401);
        HttpResult clamped = get("/notifications?page=0&pageSize=1000", token);
        assertThat(clamped.status()).as(clamped.body()).isEqualTo(200);
        assertThat(clamped.data().path("page").asInt()).isEqualTo(1);
        assertThat(clamped.data().path("pageSize").asInt()).isEqualTo(200);

        HttpResult bad = get("/notifications?unread=maybe", token);
        assertThat(bad.status()).as(bad.body()).isEqualTo(400);
        assertThat(bad.code()).isEqualTo("E-1001");
        assertThat(isNullish(bad.data())).as("校验失败不得带 data").isTrue();
    }

    // ------------------------------------------------------------------ NTF-02

    @Test
    @DisplayName("NTF-02 标记已读：响应 read_at 与库值同源，未读数下降，列表口径同步为已读")
    void markRead() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        notif(800020L, "PROVIDER", providerId, "检测通过", "SYSTEM", "DETECTION_PASSED", "DETECTION", 900020L,
                null, "2026-06-01T00:00:00Z");

        HttpResult res = post("/notifications/800020/read", null, token);
        assertThat(res.status()).as(res.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(res.body());
        SchemaAssert.assertModel("notification-read", json(res.data()));
        assertThat(res.data().path("id").asText()).isEqualTo("800020");
        assertThat(res.data().path("read_at").asText()).isNotBlank();

        // 库值：确实落库（响应与库同源，不是只改了内存对象）
        OffsetDateTime stored = jdbc.queryForObject(
                "select read_at from aap_notification where id = 800020", OffsetDateTime.class);
        assertThat(stored).isNotNull();
        assertThat(OffsetDateTime.parse(res.data().path("read_at").asText()).toInstant())
                .isEqualTo(stored.toInstant().truncatedTo(java.time.temporal.ChronoUnit.SECONDS));

        // 列表口径同步：未读数 1 → 0，单条 read=true 且 read_at 与响应一致
        HttpResult list = get("/notifications", token);
        assertThat(list.data().path("unread_count").asLong()).isZero();
        assertThat(list.data().path("items").get(0).path("read").asBoolean()).isTrue();
        assertThat(list.data().path("items").get(0).path("read_at").asText())
                .isEqualTo(res.data().path("read_at").asText());
    }

    @Test
    @DisplayName("NTF-02 重复标记幂等：read_at 保持首次时间，不产生第二次写（version 不递增）")
    void markReadIsIdempotent() {
        String token = token(PHONE);
        long providerId = onlyProviderId();
        notif(800021L, "PROVIDER", providerId, "合同已签署", "ORDER", "CONTRACT_SIGNED", "CONTRACT", 900021L,
                null, "2026-06-01T00:00:00Z");

        HttpResult first = post("/notifications/800021/read", null, token);
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        HttpResult second = post("/notifications/800021/read", null, token);
        assertThat(second.status()).as(second.body()).isEqualTo(200);
        assertThat(second.data().path("read_at").asText())
                .as("重复标记不得刷新为新的已读时间").isEqualTo(first.data().path("read_at").asText());
        assertThat(jdbc.queryForObject("select version from aap_notification where id = 800021", Integer.class))
                .as("第二次调用应命中 read_at is null 条件失败 → 不写库").isEqualTo(1);
    }

    @Test
    @DisplayName("NTF-02 越权与非法入参：他人通知/不存在 → 403 E-1901（不泄露存在性）、非数字 id 400、未认证 401")
    void markReadDenied() {
        String mine = token(PHONE);
        String other = token(OTHER_PHONE);
        List<Long> ids = providerIds();
        assertThat(ids).hasSize(2);
        notif(800030L, "PROVIDER", ids.get(1), "他人通知", "SYSTEM", "SYSTEM_NOTICE", "SYSTEM", null,
                null, "2026-06-01T00:00:00Z");
        assertThat(other).isNotBlank();

        HttpResult foreign = post("/notifications/800030/read", null, mine);
        assertThat(foreign.status()).as(foreign.body()).isEqualTo(403);
        assertThat(foreign.code()).isEqualTo("E-1901");
        assertThat(jdbc.queryForObject("select read_at from aap_notification where id = 800030",
                OffsetDateTime.class)).as("越权调用不得改动他人通知").isNull();

        HttpResult missing = post("/notifications/999999/read", null, mine);
        assertThat(missing.status()).as(missing.body()).isEqualTo(403);
        assertThat(missing.code()).isEqualTo("E-1901");

        HttpResult malformed = post("/notifications/abc/read", null, mine);
        assertThat(malformed.status()).as(malformed.body()).isEqualTo(400);
        assertThat(malformed.code()).isEqualTo("E-1001");

        assertThat(post("/notifications/800030/read", null, null).status()).isEqualTo(401);
    }

    // ------------------------------------------------------------------ ADM-A01

    @Test
    @DisplayName("ADM-A01 审计检索：真实登录审计可查（traceId 对齐）、字段合契约、action/actorType/traceId/时间窗过滤")
    void auditLogQuery() {
        HttpResult login = smsLogin(PHONE);
        String loginTrace = login.header("X-Trace-Id");
        assertThat(loginTrace).isNotBlank();
        String admin = adminToken(950010L, "TECH_OPS");

        audit(810001L, "aaa1", "ADMIN", 9001L, "PROVIDER_SUSPEND", "provider", 7001L, "暂停供应商",
                null, "{\"status\":\"ACTIVE\"}", "HIGH", "2026-06-01T00:00:00Z");
        audit(810002L, "aaa2", "PROVIDER", 9002L, "CONTRACT_SIGN", "contract", 7002L, "签署合同",
                "{\"status\":\"PENDING_SIGN\"}", "{\"status\":\"SUPPLIER_SIGNED\"}", "NORMAL", "2026-06-02T00:00:00Z");
        audit(810003L, "aaa3", "ADMIN", 9001L, "CREDENTIAL_REVEAL", "credential", 7003L, "查看凭证明文",
                null, null, "HIGH", "2026-06-03T00:00:00Z");

        HttpResult all = get("/admin/audit-logs", admin);
        assertThat(all.status()).as(all.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(all.body());
        SchemaAssert.assertPageMeta(json(all.data()));
        assertThat(all.data().path("total").asLong()).isEqualTo(4L);

        JsonNode first = all.data().path("items").get(0);
        SchemaAssert.assertModel("audit-log", json(first));
        assertThat(first.path("action").asText()).as("真实业务链路写入的审计行必须可检索（created_at desc）")
                .isEqualTo("AUTH_LOGIN");
        assertThat(first.path("trace_id").asText()).as("审计 traceId 与本请求响应头一致").isEqualTo(loginTrace);
        assertThat(first.path("actor_type").asText()).isEqualTo("PROVIDER");
        assertThat(first.path("created_at").asText()).isNotBlank();
        assertThat(first.path("result").asText()).isEqualTo("SUCCESS");

        // 落库的 before/after（jsonb）按对象返回
        JsonNode signed = get("/admin/audit-logs?action=CONTRACT_SIGN", admin).data();
        assertThat(signed.path("total").asLong()).isEqualTo(1L);
        JsonNode signRow = signed.path("items").get(0);
        SchemaAssert.assertModel("audit-log", json(signRow));
        assertThat(signRow.path("id").asText()).isEqualTo("810002");
        assertThat(signRow.path("before_value").path("status").asText()).isEqualTo("PENDING_SIGN");
        assertThat(signRow.path("after_value").path("status").asText()).isEqualTo("SUPPLIER_SIGNED");
        assertThat(signRow.path("target_id").asText()).isEqualTo("7002");
        assertThat(signRow.path("actor_name").asText()).isNotBlank();

        assertThat(get("/admin/audit-logs?actorType=ADMIN", admin).data().path("total").asLong()).isEqualTo(2L);
        assertThat(get("/admin/audit-logs?actorType=PROVIDER", admin).data().path("total").asLong()).isEqualTo(2L);
        assertThat(get("/admin/audit-logs?traceId=aaa3", admin).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/audit-logs?action=CONTRACT_SIGN&actorType=PROVIDER", admin)
                .data().path("total").asLong()).isEqualTo(1L);
        // 时间窗半开 [from, to)
        assertThat(get("/admin/audit-logs?from=2026-06-02T00:00:00Z&to=2026-06-03T00:00:00Z", admin)
                .data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/audit-logs?from=2030-01-01T00:00:00Z", admin).data().path("total").asLong())
                .isZero();
        // 分页元数据不随过滤丢失
        HttpResult paged = get("/admin/audit-logs?page=2&pageSize=2", admin);
        assertThat(paged.data().path("page").asInt()).isEqualTo(2);
        assertThat(paged.data().path("pageSize").asInt()).isEqualTo(2);
        assertThat(paged.data().path("total").asLong()).isEqualTo(4L);
        assertThat(paged.data().path("items").size()).isEqualTo(2);

        // 非法入参：action 不在审计字典、时间戳非法 → E-1001
        HttpResult badAction = get("/admin/audit-logs?action=NOT_AN_ACTION", admin);
        assertThat(badAction.status()).as(badAction.body()).isEqualTo(400);
        assertThat(badAction.code()).isEqualTo("E-1001");
        assertThat(get("/admin/audit-logs?from=不是时间", admin).status()).isEqualTo(400);
    }

    @Test
    @DisplayName("ADM-A01 权限：仅 TECH_OPS/SUPER_ADMIN 可读（供应商与 BIZ_OPERATOR 均 403、未认证 401）")
    void auditLogPermissions() {
        String supplier = token(PHONE);
        onlyProviderId();
        String techOps = adminToken(950020L, "TECH_OPS");
        String superAdmin = adminToken(950021L, "SUPER_ADMIN");
        String bizOperator = adminToken(950022L, "BIZ_OPERATOR");

        assertThat(get("/admin/audit-logs", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/audit-logs", superAdmin).status()).isEqualTo(200);
        assertThat(get("/admin/audit-logs", bizOperator).status()).as("运营商务无审计读取权").isEqualTo(403);
        HttpResult denied = get("/admin/audit-logs", supplier);
        assertThat(denied.status()).as(denied.body()).isEqualTo(403);
        assertThat(denied.code()).isEqualTo("E-1901");
        assertThat(get("/admin/audit-logs").status()).isEqualTo(401);
    }
}
