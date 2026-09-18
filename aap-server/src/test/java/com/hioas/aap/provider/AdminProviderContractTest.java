package com.hioas.aap.provider;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * T14 · 管理端供应商运维（ADM-P01…03）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4（`ADM-P01` 供应商列表 / `ADM-P02` 暂停 /
 * `ADM-P03` 恢复）+ `json-schema/models/provider-profile.schema.json`
 * + `json-schema/requests/provider-suspend.schema.json`（`suspend_reason` 必填 2–500 字）
 * + `docs/backend/01-ER数据模型.md` §`aap_provider`（`status` 12 态 / `published_at` `suspended_at` `suspend_reason` 留痕）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>权限（清单）：`BIZ_OPERATOR` / `TECH_OPS` / `SUPER_ADMIN`；供应商与未认证一律 403 `E-1901` / 401 `E-1902`</li>
 *   <li>状态机：仅「非 SUSPENDED、非 TERMINATED」可暂停 → 409 `E-1601`；仅 `SUSPENDED` 可恢复 → 409 `E-1601`；
 *       恢复后回到**暂停前状态**（`status_before_suspend` 留痕列）</li>
 *   <li>写后重读（tdd-state 踩坑 17/18）：响应体里的 `status` / `version` 必须等于**库里的值**，
 *       不允许返回内存对象（否则乐观锁一挡，响应说 1、库里还是 0）</li>
 *   <li>暂停/恢复都必留审计（`PROVIDER_SUSPEND` / `PROVIDER_RESUME`，AC-48）</li>
 * </ul>
 */
class AdminProviderContractTest extends ApiTestBase {

    private static final String SUPPLIER_PHONE = "13800000210";

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

    /** 夹具：直插 aap_provider（时间参数一律 `::timestamptz` 强转，踩坑 25）。 */
    private void insertProvider(long id, String providerNo, String shortName, String companyName, String status,
                                String publishedAt, boolean deleted, String createdAt) {
        jdbc.update("""
                insert into aap_provider (id, provider_no, provider_code, short_name, company_name, status,
                    published_at, created_at, updated_at, deleted, version, completeness, recheck_interval_days)
                values (?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz, ?::timestamptz, ?, 0, 60, 30)
                """, id, providerNo, "AAP-P-" + providerNo, shortName, companyName, status,
                publishedAt, createdAt, createdAt, deleted);
    }

    // ------------------------------------------------------------------ ADM-P01

    @Test
    @DisplayName("ADM-P01 供应商列表：分页 + status/keyword 过滤 + 逻辑删除不出现（逐条符合 provider-profile）")
    void providerList() {
        String biz = adminToken(970201L, "BIZ_OPERATOR");
        insertProvider(810001, "P000001", "甲供应商", "甲科技（上海）有限公司", "PUBLISHED",
                "2026-09-01T00:00:00Z", false, "2026-09-01T00:00:00Z");
        insertProvider(810002, "P000002", "乙供应商", "乙智能科技有限公司", "DETECT_PASSED",
                null, false, "2026-09-02T00:00:00Z");
        insertProvider(810003, "P000003", "丙供应商", "丙数据服务有限公司", "SUSPENDED",
                "2026-08-01T00:00:00Z", false, "2026-09-03T00:00:00Z");
        insertProvider(810004, "P000004", "已删除", "已删除公司", "PUBLISHED",
                null, true, "2026-09-04T00:00:00Z");

        HttpResult list = get("/admin/providers", biz);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(list.body());
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).as("逻辑删除的供应商不得出现").isEqualTo(3L);
        assertThat(list.data().path("page").asInt()).isEqualTo(1);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(list.data().path("items").size()).isEqualTo(3);
        for (JsonNode item : list.data().path("items")) {
            SchemaAssert.assertModel("provider-profile", json(item));
        }
        JsonNode first = list.data().path("items").get(0);
        assertThat(first.path("provider_id").asText()).as("created_at desc, id desc").isEqualTo("810003");
        assertThat(first.path("company_name").asText()).isEqualTo("丙数据服务有限公司");
        assertThat(first.path("status").asText()).isEqualTo("SUSPENDED");
        assertThat(first.path("providerCode").asText()).as("客户端读 camelCase").isEqualTo("AAP-P-P000003");

        HttpResult byStatus = get("/admin/providers?status=published", biz);
        assertThat(byStatus.data().path("total").asLong()).as("状态过滤大小写不敏感").isEqualTo(1L);
        assertThat(get("/admin/providers?keyword=乙智能", biz).data().path("total").asLong())
                .as("关键字命中企业全称").isEqualTo(1L);
        assertThat(get("/admin/providers?keyword=P000003", biz).data().path("total").asLong())
                .as("关键字命中供应商编号").isEqualTo(1L);
        assertThat(get("/admin/providers?keyword=不存在的关键字", biz).data().path("total").asLong()).isZero();

        HttpResult paged = get("/admin/providers?page=2&pageSize=2", biz);
        assertThat(paged.data().path("page").asInt()).isEqualTo(2);
        assertThat(paged.data().path("pageSize").asInt()).isEqualTo(2);
        assertThat(paged.data().path("total").asLong()).isEqualTo(3L);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
    }

    // ------------------------------------------------------------------ ADM-P02 / P03

    @Test
    @DisplayName("ADM-P02/03 暂停与恢复：状态机 409 E-1601、留痕列、写后重读、遗留数据回退口径 + 审计")
    void suspendAndResume() {
        String biz = adminToken(970221L, "BIZ_OPERATOR");
        String techOps = adminToken(970222L, "TECH_OPS");
        insertProvider(810001, "P000001", "甲供应商", "甲科技（上海）有限公司", "DETECT_PASSED",
                null, false, "2026-09-01T00:00:00Z");
        insertProvider(810003, "P000003", "丙供应商", "丙数据服务有限公司", "TERMINATED",
                null, false, "2026-09-03T00:00:00Z");

        // 入参校验（清单：suspend_reason 2–500 字必填）
        HttpResult noReason = post("/admin/providers/810001/suspend", "{}", biz);
        assertThat(noReason.status()).as(noReason.body()).isEqualTo(400);
        assertThat(noReason.code()).isEqualTo("E-1001");
        assertThat(noReason.json().path("details").toString()).contains("suspend_reason");
        HttpResult shortReason = post("/admin/providers/810001/suspend", """
                {"suspend_reason":"x"}
                """, biz);
        assertThat(shortReason.status()).as(shortReason.body()).isEqualTo(400);
        assertThat(shortReason.code()).isEqualTo("E-1001");

        // 资源不存在 / 非法 ID
        HttpResult missing = post("/admin/providers/999999/suspend", """
                {"suspend_reason":"资质复核中"}
                """, biz);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        HttpResult badId = post("/admin/providers/abc/suspend", """
                {"suspend_reason":"资质复核中"}
                """, biz);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");

        // 暂停：响应与库同源
        HttpResult suspended = post("/admin/providers/810001/suspend", """
                {"suspend_reason":"资质复核中"}
                """, biz);
        assertThat(suspended.status()).as(suspended.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(suspended.body());
        SchemaAssert.assertModel("provider-profile", json(suspended.data()));
        assertThat(suspended.data().path("status").asText()).as(suspended.body()).isEqualTo("SUSPENDED");
        assertThat(suspended.data().path("version").asInt()).as("响应版本必须等于库里版本（写后重读）").isEqualTo(1);
        Map<String, Object> row = jdbc.queryForMap("""
                select status, suspend_reason, status_before_suspend, suspended_at from aap_provider where id = 810001
                """);
        assertThat(row.get("status")).isEqualTo("SUSPENDED");
        assertThat(row.get("suspend_reason")).isEqualTo("资质复核中");
        assertThat(row.get("status_before_suspend")).as("暂停前状态必须留痕").isEqualTo("DETECT_PASSED");
        assertThat(row.get("suspended_at")).isNotNull();

        // 状态机：重复暂停 / 已终止
        HttpResult again = post("/admin/providers/810001/suspend", """
                {"suspend_reason":"重复暂停"}
                """, biz);
        assertThat(again.status()).as(again.body()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select suspend_reason from aap_provider where id = 810001", String.class))
                .as("被拒的暂停不得改动留痕").isEqualTo("资质复核中");
        HttpResult terminated = post("/admin/providers/810003/suspend", """
                {"suspend_reason":"已终止供应商"}
                """, techOps);
        assertThat(terminated.status()).as(terminated.body()).isEqualTo(409);
        assertThat(terminated.code()).isEqualTo("E-1601");

        // 恢复：回到暂停前状态，并清空暂停留痕
        HttpResult resumed = post("/admin/providers/810001/resume", null, techOps);
        assertThat(resumed.status()).as(resumed.body()).isEqualTo(200);
        SchemaAssert.assertModel("provider-profile", json(resumed.data()));
        assertThat(resumed.data().path("status").asText()).as(resumed.body()).isEqualTo("DETECT_PASSED");
        row = jdbc.queryForMap("""
                select status, status_before_suspend, suspended_at from aap_provider where id = 810001
                """);
        assertThat(row.get("status")).isEqualTo("DETECT_PASSED");
        assertThat(row.get("status_before_suspend")).as("恢复后清空，避免下一次暂停复用旧值").isNull();
        assertThat(row.get("suspended_at")).isNull();

        // 非暂停态 / 已终止 不可恢复
        HttpResult notSuspended = post("/admin/providers/810001/resume", null, biz);
        assertThat(notSuspended.status()).as(notSuspended.body()).isEqualTo(409);
        assertThat(notSuspended.code()).isEqualTo("E-1601");
        assertThat(post("/admin/providers/810003/resume", null, biz).status()).isEqualTo(409);
        assertThat(post("/admin/providers/999999/resume", null, biz).status()).isEqualTo(404);

        // 遗留数据（暂停前状态缺失）的回退口径：有上架时间 → PUBLISHED，否则 → DETECT_PASSED
        insertProvider(810004, "P000004", "丁供应商", "丁计算有限公司", "SUSPENDED",
                "2026-09-01T00:00:00Z", false, "2026-09-04T00:00:00Z");
        insertProvider(810005, "P000005", "戊供应商", "戊网络有限公司", "SUSPENDED",
                null, false, "2026-09-05T00:00:00Z");
        assertThat(post("/admin/providers/810004/resume", null, biz).data().path("status").asText())
                .as("曾上架 → 回 PUBLISHED").isEqualTo("PUBLISHED");
        assertThat(post("/admin/providers/810005/resume", null, biz).data().path("status").asText())
                .as("未上架 → 回 DETECT_PASSED").isEqualTo("DETECT_PASSED");

        // 审计（AC-48）：暂停 1 次 + 恢复 3 次
        HttpResult suspendLogs = get("/admin/audit-logs?action=PROVIDER_SUSPEND", techOps);
        assertThat(suspendLogs.status()).as(suspendLogs.body()).isEqualTo(200);
        assertThat(suspendLogs.data().path("total").asLong()).as("暂停必留审计").isEqualTo(1L);
        assertThat(suspendLogs.data().path("items").get(0).path("target_type").asText()).isEqualTo("provider");
        assertThat(suspendLogs.data().path("items").get(0).path("target_id").asText()).isEqualTo("810001");
        HttpResult resumeLogs = get("/admin/audit-logs?action=PROVIDER_RESUME", techOps);
        assertThat(resumeLogs.data().path("total").asLong()).as("恢复必留审计").isEqualTo(3L);
    }

    // ------------------------------------------------------------------ 权限

    @Test
    @DisplayName("ADM-P01…03 权限：BIZ_OPERATOR/TECH_OPS/SUPER_ADMIN 可用；供应商 403 E-1901、未认证 401 E-1902")
    void permissions() {
        String supplier = supplierToken();
        String biz = adminToken(970231L, "BIZ_OPERATOR");
        String techOps = adminToken(970232L, "TECH_OPS");
        String superAdmin = adminToken(970233L, "SUPER_ADMIN");
        insertProvider(810001, "P000001", "甲供应商", "甲科技（上海）有限公司", "PUBLISHED",
                "2026-09-01T00:00:00Z", false, "2026-09-01T00:00:00Z");

        assertThat(get("/admin/providers", biz).status()).isEqualTo(200);
        assertThat(get("/admin/providers", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/providers", superAdmin).status()).isEqualTo(200);
        assertThat(post("/admin/providers/810001/suspend", """
                {"suspend_reason":"超管暂停"}
                """, superAdmin).status()).isEqualTo(200);
        assertThat(post("/admin/providers/810001/resume", null, superAdmin).status()).isEqualTo(200);

        HttpResult supplierDenied = get("/admin/providers", supplier);
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        HttpResult supplierSuspend = post("/admin/providers/810001/suspend", """
                {"suspend_reason":"越权暂停"}
                """, supplier);
        assertThat(supplierSuspend.status()).as(supplierSuspend.body()).isEqualTo(403);
        assertThat(supplierSuspend.code()).isEqualTo("E-1901");
        assertThat(jdbc.queryForObject("select status from aap_provider where id = 810001", String.class))
                .as("越权请求不得改动状态").isEqualTo("PUBLISHED");

        HttpResult anonymous = get("/admin/providers");
        assertThat(anonymous.status()).as(anonymous.body()).isEqualTo(401);
        assertThat(anonymous.code()).isEqualTo("E-1902");
        assertThat(post("/admin/providers/810001/resume", null, null).status()).isEqualTo(401);
    }
}
