package com.hioas.aap.supply;

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
 * M4 段 · 管理端供给单元运维（ADM-SU01…04）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.6 +
 * `json-schema/models/supply-unit.schema.json` / `config-batch.schema.json` / `config-batch-item.schema.json` +
 * `json-schema/requests/supply-unit-reconfigure.schema.json`（`dry_run` 可选，默认 true）+
 * `specs/001-intake-automation/spec.md` FR-2.9（重配置）/ FR-2.10（下线留痕）/ R-65（下架前影响面校验）
 * + V15（`aap_supply_unit`）/ V16（`aap_config_batch` + 明细）迁移。
 *
 * <p>硬口径：
 * <ul>
 *   <li>权限（清单逐行）：`TECH_OPS` / `SUPER_ADMIN`；`BIZ_OPERATOR` 与供应商 → 403 `E-1901`，未认证 → 401 `E-1902`</li>
 *   <li>响应键名 = schema 键名（snake_case）：`provider_id` / `model_name` / `batch_no` / `rate_limit_per_sec` …</li>
 *   <li><b>响应与库同源</b>（踩坑 17/18）：状态类断言都带上 `.as(响应体)`，且同时钉「响应字段」与「库内列值」</li>
 *   <li>下架前置（R-65）：存在未结清账期（`UNSETTLED`/`PAYMENT_RECORDED` 的打款）→ 409 `E-1601` 且**库内状态不变**</li>
 *   <li>重配置默认 dry-run（AC-10）：`DRY_RUN` 批次明细一律 `SKIPPED`，**生产零写入**（无渠道绑定 / 无同步任务新增）</li>
 * </ul>
 */
class SupplyUnitAdminContractTest extends ApiTestBase {

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

    /** 夹具：供应商（含 `short_code`，渠道名生成要用）。时间参数一律 `::timestamptz` 强转（踩坑 25）。 */
    private void insertProvider(long id, String shortCode, String status, String createdAt) {
        jdbc.update("""
                insert into aap_provider (id, provider_no, provider_code, short_code, short_name, company_name,
                    status, completeness, recheck_interval_days, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, ?, ?, 60, 30, ?::timestamptz, ?::timestamptz, false, 0)
                """, id, "P" + String.format("%06d", id % 1000000), "AAP-P-" + id, shortCode,
                "供应商" + id, "供应商" + id + "有限公司", status, createdAt, createdAt);
    }

    /** 夹具：供给单元。 */
    private void insertSupplyUnit(long id, long providerId, String modelName, String status,
                                  Integer priority, Integer weight, String createdAt, boolean deleted) {
        jdbc.update("""
                insert into aap_supply_unit (id, provider_id, credential_id, model_name, model_slug, model_uid,
                    status, detect_total_score, detect_confidence, quality_score, routing_priority, routing_weight,
                    auto_ban_enabled, binding_id, granularity, created_at, updated_at, deleted, version)
                values (?, ?, null, ?, ?, null, ?, 88.50, 'HIGH', 91.25, ?, ?, true, null, 'PER_MODEL',
                    ?::timestamptz, ?::timestamptz, ?, 0)
                """, id, providerId, modelName, modelName.replace("/", "-"), status, priority, weight,
                createdAt, createdAt, deleted);
    }

    /** 夹具：打款记录（`status` 决定「是否未结清账期」）。 */
    private void insertPayment(long id, long providerId, String status) {
        jdbc.update("""
                insert into aap_payment_record (id, provider_id, amount, currency, status, created_at, updated_at,
                    deleted, version)
                values (?, ?, 1000.000000, 'USD', ?, now(), now(), false, 0)
                """, id, providerId, status);
    }

    private static final String V = "2026-09-20T00:00:00Z";

    // ------------------------------------------------------------------ ADM-SU01

    @Test
    @DisplayName("ADM-SU01 供给单元列表：分页 + providerId/modelName/status 过滤 + 逻辑删除不出现 + schema 键名")
    void supplyUnitList() {
        String techOps = adminToken(970301L, "TECH_OPS");
        insertProvider(820001, "ACME", "PUBLISHED", V);
        insertProvider(820002, "BETA", "PUBLISHED", V);
        insertSupplyUnit(830001, 820001, "gpt-4o", "ONLINE", 10, 80, "2026-09-01T00:00:00Z", false);
        insertSupplyUnit(830002, 820001, "claude-3-5", "DEGRADED", 5, 60, "2026-09-02T00:00:00Z", false);
        insertSupplyUnit(830003, 820002, "gpt-4o", "OFFLINE", 1, 10, "2026-09-03T00:00:00Z", false);
        insertSupplyUnit(830004, 820001, "已删除", "ONLINE", 1, 10, "2026-09-04T00:00:00Z", true);

        HttpResult list = get("/admin/supply-units", techOps);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(list.body());
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).as("逻辑删除的供给单元不得出现").isEqualTo(3L);
        assertThat(list.data().path("page").asInt()).isEqualTo(1);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(list.data().path("items").size()).isEqualTo(3);
        for (JsonNode item : list.data().path("items")) {
            SchemaAssert.assertModel("supply-unit", json(item));
        }
        JsonNode first = list.data().path("items").get(0);
        assertThat(first.path("id").asText()).as("排序 created_at desc, id desc").isEqualTo("830003");
        assertThat(first.path("provider_id").asText()).as("ID 对外 string 且键名为 schema 键名").isEqualTo("820002");
        assertThat(first.path("model_name").asText()).isEqualTo("gpt-4o");
        assertThat(first.path("status").asText()).isEqualTo("OFFLINE");
        assertThat(first.path("granularity").asText()).isEqualTo("PER_MODEL");
        assertThat(first.path("detect_total_score").decimalValue()).isEqualByComparingTo("88.50");
        assertThat(first.path("auto_ban_enabled").asBoolean()).isTrue();
        assertThat(first.path("created_at").asText()).as("RFC3339 UTC").isEqualTo("2026-09-03T00:00:00Z");

        HttpResult byProvider = get("/admin/supply-units?providerId=820001", techOps);
        assertThat(byProvider.data().path("total").asLong()).isEqualTo(2L);
        assertThat(get("/admin/supply-units?modelName=CLAUDE", techOps).data().path("total").asLong())
                .as("模型名过滤大小写不敏感").isEqualTo(1L);
        assertThat(get("/admin/supply-units?status=online", techOps).data().path("total").asLong())
                .as("状态过滤大小写不敏感").isEqualTo(1L);
        assertThat(get("/admin/supply-units?status=ONLINE&providerId=820001", techOps).data().path("total").asLong())
                .as("多条件与").isEqualTo(1L);
        assertThat(get("/admin/supply-units?modelName=不存在的模型", techOps).data().path("total").asLong()).isZero();

        HttpResult paged = get("/admin/supply-units?page=2&pageSize=2", techOps);
        assertThat(paged.data().path("page").asInt()).isEqualTo(2);
        assertThat(paged.data().path("pageSize").asInt()).isEqualTo(2);
        assertThat(paged.data().path("total").asLong()).isEqualTo(3L);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
    }

    // ------------------------------------------------------------------ ADM-SU02

    @Test
    @DisplayName("ADM-SU02 详情：逐字段符合 supply-unit；不存在/已删除 404 E-1406，非法 id 400 E-1001")
    void supplyUnitDetail() {
        String techOps = adminToken(970311L, "TECH_OPS");
        insertProvider(820001, "ACME", "PUBLISHED", V);
        insertSupplyUnit(830001, 820001, "gpt-4o", "ONLINE", 10, 80, V, false);
        insertSupplyUnit(830002, 820001, "已删除", "ONLINE", 1, 10, V, true);

        HttpResult detail = get("/admin/supply-units/830001", techOps);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(detail.body());
        SchemaAssert.assertModel("supply-unit", json(detail.data()));
        assertThat(detail.data().path("id").asText()).isEqualTo("830001");
        assertThat(detail.data().path("provider_id").asText()).isEqualTo("820001");
        assertThat(detail.data().path("routing_priority").asInt()).isEqualTo(10);
        assertThat(detail.data().path("routing_weight").asInt()).isEqualTo(80);
        assertThat(detail.data().path("quality_score").decimalValue()).isEqualByComparingTo("91.25");

        HttpResult missing = get("/admin/supply-units/999999", techOps);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        HttpResult deleted = get("/admin/supply-units/830002", techOps);
        assertThat(deleted.status()).as(deleted.body()).isEqualTo(404);
        assertThat(deleted.code()).isEqualTo("E-1406");
        HttpResult badId = get("/admin/supply-units/abc", techOps);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");
    }

    // ------------------------------------------------------------------ ADM-SU03

    @Test
    @DisplayName("ADM-SU03 重配置：202 + 契约默认 dry-run（明细 SKIPPED、生产零写入）+ 响应与库同源 + 非法状态 409")
    void reconfigure() {
        String techOps = adminToken(970321L, "TECH_OPS");
        insertProvider(820001, "ACME", "PUBLISHED", V);
        insertSupplyUnit(830001, 820001, "gpt-4o", "ONLINE", 10, 80, V, false);
        insertSupplyUnit(830002, 820001, "已下线", "OFFLINE", 1, 10, V, false);
        insertSupplyUnit(830003, 820001, "待配置", "PENDING", 1, 10, V, false);

        // 省略请求体 ⇒ 契约默认 dry_run=true
        HttpResult dry = post("/admin/supply-units/830001/reconfigure", null, techOps);
        assertThat(dry.status()).as(dry.body()).isEqualTo(202);
        SchemaAssert.assertEnvelope(dry.body());
        SchemaAssert.assertModel("config-batch", json(dry.data()));
        assertThat(dry.data().path("mode").asText()).isEqualTo("DRY_RUN");
        assertThat(dry.data().path("batch_type").asText()).isEqualTo("RECONFIG");
        assertThat(dry.data().path("trigger_source").asText()).isEqualTo("ADMIN_MANUAL");
        assertThat(dry.data().path("status").asText()).isEqualTo("SUCCEEDED");
        assertThat(dry.data().path("rate_limit_per_sec").asInt()).as("R-57 限速 5").isEqualTo(5);
        assertThat(dry.data().path("total_count").asInt()).isEqualTo(1);
        assertThat(dry.data().path("succeeded_count").asInt()).isZero();
        assertThat(dry.data().path("batch_no").asText()).matches("^CFG-B\\d{6}-\\d{4}$");
        assertThat(dry.data().path("items").size()).as("明细必须补齐（踩坑 22）").isEqualTo(1);
        JsonNode item = dry.data().path("items").get(0);
        SchemaAssert.assertModel("config-batch-item", json(item));
        assertThat(item.path("action").asText()).isEqualTo("RECONFIG");
        assertThat(item.path("status").asText()).as("dry-run 零写入 ⇒ 明细 SKIPPED").isEqualTo("SKIPPED");
        assertThat(item.path("supply_unit_id").asText()).isEqualTo("830001");
        assertThat(item.path("model_name").asText()).isEqualTo("gpt-4o");
        assertThat(dry.data().path("diff_summary").path("mode").asText()).isEqualTo("DRY_RUN");
        assertThat(dry.data().path("diff_summary").path("writeRequired").asInt())
                .as("无绑定 ⇒ 目标为 CREATE（1 处需写上游，但 dry-run 不写）").isEqualTo(1);

        // 响应 ⇔ 库同源（踩坑 17/18）
        Map<String, Object> batch = jdbc.queryForMap(
                "select batch_no, mode, status, total_count, rate_limit_per_sec, diff_payload::text as payload"
                        + " from aap_config_batch where id = ?", Long.valueOf(dry.data().path("id").asText()));
        assertThat(batch.get("batch_no")).as(dry.body()).isEqualTo(dry.data().path("batch_no").asText());
        assertThat(batch.get("mode")).isEqualTo("DRY_RUN");
        assertThat(batch.get("status")).isEqualTo("SUCCEEDED");
        assertThat(((Number) batch.get("total_count")).intValue()).isEqualTo(1);
        assertThat(((Number) batch.get("rate_limit_per_sec")).intValue()).isEqualTo(5);
        assertThat(jdbc.queryForObject("select count(*) from aap_config_batch_item where batch_id = ?",
                Long.class, Long.valueOf(dry.data().path("id").asText()))).isEqualTo(1L);
        // AC-10 零写入：dry-run 不得新增渠道绑定 / 同步任务
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_task", Long.class)).isZero();

        // APPLY：只登记受理（执行器 T-M4-08~11 未落地）
        HttpResult apply = post("/admin/supply-units/830001/reconfigure", """
                {"dry_run":false,"reason":"凭证轮换后同步差异"}
                """, techOps);
        assertThat(apply.status()).as(apply.body()).isEqualTo(202);
        assertThat(apply.data().path("mode").asText()).isEqualTo("APPLY");
        assertThat(apply.data().path("status").asText()).isEqualTo("PENDING");
        assertThat(apply.data().path("items").get(0).path("status").asText()).isEqualTo("PENDING");
        assertThat(jdbc.queryForObject("select status from aap_config_batch where id = ?", String.class,
                Long.valueOf(apply.data().path("id").asText()))).as("响应与库同源").isEqualTo("PENDING");
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class))
                .as("APPLY 尚未执行 ⇒ 仍零写入").isZero();

        // 状态守卫（契约：未上架 / 已下线 → 409）
        HttpResult offlineUnit = post("/admin/supply-units/830002/reconfigure", null, techOps);
        assertThat(offlineUnit.status()).as(offlineUnit.body()).isEqualTo(409);
        assertThat(offlineUnit.code()).isEqualTo("E-1601");
        HttpResult pendingUnit = post("/admin/supply-units/830003/reconfigure", null, techOps);
        assertThat(pendingUnit.status()).as(pendingUnit.body()).isEqualTo(409);
        assertThat(pendingUnit.code()).isEqualTo("E-1601");
        HttpResult missing = post("/admin/supply-units/999999/reconfigure", null, techOps);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");

        // 审计（治理类动作全程审计）
        HttpResult logs = get("/admin/audit-logs?action=SUPPLY_UNIT_RECONFIGURE", techOps);
        assertThat(logs.status()).as(logs.body()).isEqualTo(200);
        assertThat(logs.data().path("total").asLong()).as("2 次受理（DRY_RUN + APPLY）各留一条").isEqualTo(2L);
        assertThat(logs.data().path("items").get(0).path("target_type").asText()).isEqualTo("supply_unit");
        assertThat(logs.data().path("items").get(0).path("target_id").asText()).isEqualTo("830001");
    }

    // ------------------------------------------------------------------ ADM-SU04

    @Test
    @DisplayName("ADM-SU04 下架：状态置 OFFLINE（响应与库同源）+ R-65 未结清账期 409 且库不变 + 审计留痕")
    void offline() {
        String techOps = adminToken(970331L, "TECH_OPS");
        insertProvider(820001, "ACME", "PUBLISHED", V);
        insertProvider(820002, "BETA", "PUBLISHED", V);
        insertSupplyUnit(830001, 820001, "gpt-4o", "ONLINE", 10, 80, V, false);
        insertSupplyUnit(830002, 820002, "claude-3-5", "DEGRADED", 5, 60, V, false);
        insertSupplyUnit(830003, 820001, "已下线", "OFFLINE", 1, 10, V, false);

        // R-65：存在未结清账期（已记录未确认）→ 409 且库内状态不变
        insertPayment(840001, 820002, "PAYMENT_RECORDED");
        HttpResult blocked = post("/admin/supply-units/830002/offline", null, techOps);
        assertThat(blocked.status()).as(blocked.body()).isEqualTo(409);
        assertThat(blocked.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select status from aap_supply_unit where id = 830002", String.class))
                .as("被拒的下架不得改动状态").isEqualTo("DEGRADED");

        // 已下线 → 409（不重复下架）
        HttpResult already = post("/admin/supply-units/830003/offline", null, techOps);
        assertThat(already.status()).as(already.body()).isEqualTo(409);
        assertThat(already.code()).isEqualTo("E-1601");
        // 不存在 → 404
        HttpResult missing = post("/admin/supply-units/999999/offline", null, techOps);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");

        // 正常下架：响应与库同源（含乐观锁 version 递增）
        HttpResult ok = post("/admin/supply-units/830001/offline", null, techOps);
        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(ok.body());
        SchemaAssert.assertModel("supply-unit", json(ok.data()));
        assertThat(ok.data().path("status").asText()).as(ok.body()).isEqualTo("OFFLINE");
        Map<String, Object> row = jdbc.queryForMap(
                "select status, version, updated_by from aap_supply_unit where id = 830001");
        assertThat(row.get("status")).isEqualTo("OFFLINE");
        assertThat(((Number) row.get("version")).intValue()).as("条件 UPDATE 命中 1 行并递增版本").isEqualTo(1);
        assertThat(((Number) row.get("updated_by")).longValue()).isEqualTo(970331L);
        assertThat(post("/admin/supply-units/830001/offline", null, techOps).status())
                .as("下架后重复调用 → 409").isEqualTo(409);

        // 账期结清（CONFIRMED / VOID 均视为已结清）后可下架
        jdbc.update("update aap_payment_record set status = 'CONFIRMED' where id = 840001");
        HttpResult afterSettled = post("/admin/supply-units/830002/offline", null, techOps);
        assertThat(afterSettled.status()).as(afterSettled.body()).isEqualTo(200);
        assertThat(afterSettled.data().path("status").asText()).isEqualTo("OFFLINE");

        // 审计留痕（FR-2.10）
        HttpResult logs = get("/admin/audit-logs?action=SUPPLY_UNIT_OFFLINE", techOps);
        assertThat(logs.status()).as(logs.body()).isEqualTo(200);
        assertThat(logs.data().path("total").asLong()).as("成功下架 2 次各留一条（被拒的 409 不留）").isEqualTo(2L);
    }

    // ------------------------------------------------------------------ 权限

    @Test
    @DisplayName("ADM-SU01…04 权限：TECH_OPS/SUPER_ADMIN 可用；BIZ_OPERATOR 与供应商 403 E-1901、未认证 401 E-1902")
    void permissions() {
        String supplier = supplierToken();
        String techOps = adminToken(970341L, "TECH_OPS");
        String superAdmin = adminToken(970342L, "SUPER_ADMIN");
        String bizOperator = adminToken(970343L, "BIZ_OPERATOR");
        insertProvider(820001, "ACME", "PUBLISHED", V);
        insertSupplyUnit(830001, 820001, "gpt-4o", "ONLINE", 10, 80, V, false);
        // 第二个单元专供「越权不得改动状态」断言：它全程不被任何合法调用动过（否则夹具状态会被前一步的合法下架改掉，坑 19）
        insertSupplyUnit(830002, 820001, "claude-3-5", "ONLINE", 5, 60, V, false);

        assertThat(get("/admin/supply-units", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/supply-units", superAdmin).status()).isEqualTo(200);
        assertThat(get("/admin/supply-units/830001", techOps).status()).isEqualTo(200);
        assertThat(post("/admin/supply-units/830001/reconfigure", null, superAdmin).status()).isEqualTo(202);
        assertThat(post("/admin/supply-units/830001/offline", null, superAdmin).status()).isEqualTo(200);

        // BIZ_OPERATOR 不在清单角色列 → 403（不得因「也是管理端」而放行）
        HttpResult bizList = get("/admin/supply-units", bizOperator);
        assertThat(bizList.status()).as(bizList.body()).isEqualTo(403);
        assertThat(bizList.code()).isEqualTo("E-1901");
        assertThat(post("/admin/supply-units/830001/offline", null, bizOperator).status()).isEqualTo(403);

        HttpResult supplierList = get("/admin/supply-units", supplier);
        assertThat(supplierList.status()).as(supplierList.body()).isEqualTo(403);
        assertThat(supplierList.code()).isEqualTo("E-1901");
        HttpResult supplierOffline = post("/admin/supply-units/830002/offline", null, supplier);
        assertThat(supplierOffline.status()).as(supplierOffline.body()).isEqualTo(403);
        assertThat(supplierOffline.code()).isEqualTo("E-1901");
        assertThat(jdbc.queryForObject("select status from aap_supply_unit where id = 830002", String.class))
                .as("越权请求不得改动状态").isEqualTo("ONLINE");

        HttpResult anonymous = get("/admin/supply-units");
        assertThat(anonymous.status()).as(anonymous.body()).isEqualTo(401);
        assertThat(anonymous.code()).isEqualTo("E-1902");
    }
}
