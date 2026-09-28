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
 * M4 段 · 管理端批量配置批次（ADM-CB01…05）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.6（逐行：201 / 分页 / 含明细与 mismatch 清单 /
 * 202 单模型重试与回滚）+
 * `json-schema/models/config-batch.schema.json` / `config-batch-item.schema.json` +
 * `json-schema/requests/config-batch-create.schema.json`（`batch_type`+`mode` 必填）/
 * `config-batch-rollback.schema.json`（`reason` 必填）+
 * `specs/001-intake-automation/spec.md` FR-2.5（批量模式 + 部分失败：成功的保留、失败的按单模型独立回滚/重试）、
 * FR-6.2（控制台：进度 / 成功失败与回读不一致清单 / 按单模型重试与回滚）、FR-6.3 + AC-10（dry-run 差异清单、
 * **生产零写入**）、R-57（**≤5 req/s、每批 ≤20**）、R-58（回读不一致不得静默成功）、R-59（**单模型失败只回滚该模型**）+
 * V16（`aap_config_batch` / `aap_config_batch_item` 迁移）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>权限（清单逐行）：`TECH_OPS` / `SUPER_ADMIN`；`BIZ_OPERATOR` 与供应商 → 403 `E-1901`，未认证 → 401 `E-1902`</li>
 *   <li>成功状态码按**清单**：创建 **201**、单模型重试/回滚 **202**（`ADM-SU03` 同族：非 200 成功码在 md 行里已声明）</li>
 *   <li>响应键名 = schema 键名（snake_case）；ID 一律 string；时间 RFC3339 UTC</li>
 *   <li><b>响应与库同源</b>（踩坑 17/18）：状态类断言都带 `.as(响应体)`，且同时钉「响应字段」与「库内列值」</li>
 *   <li><b>子集合必须补齐</b>（踩坑 22）：详情/创建的 `items` 在**响应体**里钉条数，不只看 SQL 行数</li>
 *   <li>R-59 单模型隔离：重试/回滚**只动该项**，同批次的兄弟项必须逐列不变</li>
 * </ul>
 */
class ConfigBatchAdminContractTest extends ApiTestBase {

    private static final String SUPPLIER_PHONE = "13800000211";
    private static final String V = "2026-09-20T00:00:00Z";

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
    private void insertProvider(long id, String shortCode) {
        jdbc.update("""
                insert into aap_provider (id, provider_no, provider_code, short_code, short_name, company_name,
                    status, completeness, recheck_interval_days, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, ?, ?, 'PUBLISHED', 60, 30, ?::timestamptz, ?::timestamptz, false, 0)
                """, id, "P" + String.format("%06d", id % 1000000), "AAP-P-" + id, shortCode,
                "供应商" + id, "供应商" + id + "有限公司", V, V);
    }

    /** 夹具：供给单元。 */
    private void insertSupplyUnit(long id, long providerId, String modelName, String status, String createdAt) {
        jdbc.update("""
                insert into aap_supply_unit (id, provider_id, credential_id, model_name, model_slug, model_uid,
                    status, detect_total_score, detect_confidence, quality_score, routing_priority, routing_weight,
                    auto_ban_enabled, binding_id, granularity, created_at, updated_at, deleted, version)
                values (?, ?, null, ?, ?, null, ?, 88.50, 'HIGH', 91.25, 10, 80, true, null, 'PER_MODEL',
                    ?::timestamptz, ?::timestamptz, false, 0)
                """, id, providerId, modelName, modelName.replace("/", "-"), status, createdAt, createdAt);
    }

    /** 夹具：渠道绑定（**标签维度的解析依据** = `aap_channel_binding.tag`；dry-run 不得改动它）。 */
    private void insertBinding(long id, long supplyUnitId, String modelName, String tag) {
        jdbc.update("""
                insert into aap_channel_binding (id, provider_id, supply_unit_id, model_name, channel_name, tag,
                    group_name, priority, weight, models, status, created_at, updated_at, deleted, version)
                values (?, 820001, ?, ?, ?, ?, 'default', 0, 80, ?::jsonb, 'SYNCED', now(), now(), false, 0)
                """, id, supplyUnitId, modelName, "aap-channel-" + supplyUnitId, tag,
                "[\"" + modelName + "\"]");
    }

    /** 夹具：批次行。 */
    private void insertBatch(long id, String batchNo, String type, String mode, String status, int total,
                             int succeeded, int failed, int mismatch, String createdAt, boolean deleted) {
        jdbc.update("""
                insert into aap_config_batch (id, batch_no, batch_type, mode, trigger_source, status,
                    total_count, succeeded_count, failed_count, mismatch_count, rate_limit_per_sec, diff_payload,
                    operator_id, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?, 'ADMIN_MANUAL', ?, ?, ?, ?, ?, 5, null, 970401, ?::timestamptz,
                    ?::timestamptz, ?, 0)
                """, id, batchNo, type, mode, status, total, succeeded, failed, mismatch, createdAt, createdAt, deleted);
    }

    /** 夹具：批次明细行（返回明细 id）。 */
    private long insertItem(long id, long batchId, long supplyUnitId, String modelName, String action,
                            String status, int attemptCount, String idempotencyKey, Boolean readbackEqual,
                            String lastError) {
        jdbc.update("""
                insert into aap_config_batch_item (id, batch_id, supply_unit_id, provider_id, model_name, action,
                    status, idempotency_key, readback_equal, attempt_count, last_error, created_at, updated_at,
                    deleted, version)
                values (?, ?, ?, 820001, ?, ?, ?, ?, ?, ?, ?, now(), now(), false, 0)
                """, id, batchId, supplyUnitId, modelName, action, status, idempotencyKey, readbackEqual,
                attemptCount, lastError);
        return id;
    }

    // ------------------------------------------------------------------ ADM-CB01

    @Test
    @DisplayName("ADM-CB01 创建批次：201 + dry-run 差异清单（零上游写入）+ APPLY 只登记受理 + 校验 400 + 影响面 >20 → 409")
    void createBatch() {
        String techOps = adminToken(970401L, "TECH_OPS");
        insertProvider(820001, "ACME");
        insertProvider(820002, "BETA");
        insertSupplyUnit(830001, 820001, "gpt-4o", "ONLINE", "2026-09-01T00:00:00Z");
        insertSupplyUnit(830002, 820001, "claude-3-5", "DEGRADED", "2026-09-02T00:00:00Z");
        insertSupplyUnit(830003, 820002, "gpt-4o-mini", "OFFLINE", "2026-09-03T00:00:00Z");

        // 按 provider 维度选目标（FR-6.5「按供应商/模型/标签批量」）；DRY_RUN 出差异清单、零写入（AC-10）
        HttpResult dry = post("/admin/config-batches", """
                {"batch_type":"RECONFIG","mode":"DRY_RUN","scope":{"providerIds":[820001]},"reason":"凭证轮换后重算差异"}
                """, techOps);
        assertThat(dry.status()).as(dry.body()).isEqualTo(201);
        SchemaAssert.assertEnvelope(dry.body());
        SchemaAssert.assertModel("config-batch", json(dry.data()));
        assertThat(dry.data().path("batch_no").asText()).matches("^CFG-B\\d{6}-\\d{4}$");
        assertThat(dry.data().path("batch_type").asText()).isEqualTo("RECONFIG");
        assertThat(dry.data().path("mode").asText()).isEqualTo("DRY_RUN");
        assertThat(dry.data().path("trigger_source").asText()).as("管理端手工触发").isEqualTo("ADMIN_MANUAL");
        assertThat(dry.data().path("status").asText()).as("dry-run 无上游写入 ⇒ 批次已收敛").isEqualTo("SUCCEEDED");
        assertThat(dry.data().path("rate_limit_per_sec").asInt()).as("R-57 限速上限 5").isEqualTo(5);
        assertThat(dry.data().path("total_count").asInt()).as("目标 = 该供应商的 2 个供给单元").isEqualTo(2);
        assertThat(dry.data().path("succeeded_count").asInt()).isZero();
        assertThat(dry.data().path("failed_count").asInt()).isZero();
        assertThat(dry.data().path("items").size()).as("明细必须补齐（踩坑 22）").isEqualTo(2);
        for (JsonNode item : dry.data().path("items")) {
            SchemaAssert.assertModel("config-batch-item", json(item));
            assertThat(item.path("status").asText()).as("dry-run 零写入 ⇒ 明细 SKIPPED（AC-10）").isEqualTo("SKIPPED");
            assertThat(item.path("action").asText()).as("库内无绑定 ⇒ 目标动作 CREATE").isEqualTo("CREATE");
        }
        assertThat(dry.data().path("diff_summary").path("mode").asText()).isEqualTo("DRY_RUN");
        assertThat(dry.data().path("diff_summary").path("byAction").path("CREATE").asInt()).isEqualTo(2);
        assertThat(dry.data().path("diff_summary").path("writeRequired").asInt()).isEqualTo(2);

        // 响应 ⇔ 库同源（踩坑 17/18）
        long batchId = Long.parseLong(dry.data().path("id").asText());
        Map<String, Object> row = jdbc.queryForMap(
                "select batch_no, mode, status, total_count, rate_limit_per_sec, operator_id, updated_by"
                        + " from aap_config_batch where id = ?", batchId);
        assertThat(row.get("batch_no")).as(dry.body()).isEqualTo(dry.data().path("batch_no").asText());
        assertThat(row.get("mode")).isEqualTo("DRY_RUN");
        assertThat(row.get("status")).isEqualTo("SUCCEEDED");
        assertThat(((Number) row.get("total_count")).intValue()).isEqualTo(2);
        assertThat(((Number) row.get("rate_limit_per_sec")).intValue()).isEqualTo(5);
        assertThat(((Number) row.get("operator_id")).longValue()).isEqualTo(970401L);
        assertThat(((Number) row.get("updated_by")).longValue()).as("留痕列必须写（审计列口径）").isEqualTo(970401L);
        assertThat(jdbc.queryForObject("select count(*) from aap_config_batch_item where batch_id = ?",
                Long.class, batchId)).isEqualTo(2L);
        // AC-10 零写入：dry-run 不得新增渠道绑定 / 同步任务 / 改动供给单元状态
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_task", Long.class)).isZero();

        // 省略 scope ⇒ 全量未下线供给单元（OFFLINE 单元不参与）
        HttpResult all = post("/admin/config-batches", """
                {"batch_type":"UPDATE_CHANNEL","mode":"DRY_RUN"}
                """, techOps);
        assertThat(all.status()).as(all.body()).isEqualTo(201);
        assertThat(all.data().path("total_count").asInt()).as("省略 scope = 全量未下线（2 个）").isEqualTo(2);
        assertThat(all.data().path("items").size()).isEqualTo(2);

        // 按模型维度
        HttpResult byModel = post("/admin/config-batches", """
                {"batch_type":"UPDATE_CHANNEL","mode":"DRY_RUN","scope":{"modelNames":["GPT-4O"]}}
                """, techOps);
        assertThat(byModel.status()).as(byModel.body()).isEqualTo(201);
        assertThat(byModel.data().path("total_count").asInt())
                .as("模型名匹配大小写不敏感（库里存 'gpt-4o'，请求用大写 'GPT-4O' 仍命中那 1 个；大小写敏感会得 0）")
                .isEqualTo(1);

        // 按标签维度（FR-6.5「按供应商/模型/标签批量」）：标签挂在渠道绑定上（供给单元表无标签列，V15 实测）
        insertBinding(870001, 830002, "claude-3-5", "premium");
        HttpResult byTag = post("/admin/config-batches", """
                {"batch_type":"UPDATE_CHANNEL","mode":"DRY_RUN","scope":{"tags":["premium"]}}
                """, techOps);
        assertThat(byTag.status()).as(byTag.body()).isEqualTo(201);
        assertThat(byTag.data().path("total_count").asInt()).as("标签维度命中 1 个供给单元").isEqualTo(1);
        assertThat(byTag.data().path("items").get(0).path("supply_unit_id").asText()).isEqualTo("830002");
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding where deleted = false", Long.class))
                .as("dry-run 不得新增/改动绑定（AC-10 零写入）").isEqualTo(1L);
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_task", Long.class))
                .as("dry-run 不得排队同步任务").isZero();

        // 维度命中 0 个供给单元：登记一个**空批次**（total_count=0、无明细、无差异），不静默报错
        HttpResult empty = post("/admin/config-batches", """
                {"batch_type":"UPDATE_CHANNEL","mode":"DRY_RUN","scope":{"providerIds":[999999]}}
                """, techOps);
        assertThat(empty.status()).as(empty.body()).isEqualTo(201);
        assertThat(empty.data().path("total_count").asInt()).isZero();
        assertThat(empty.data().path("items").size()).as("无目标 ⇒ 无明细").isZero();
        assertThat(empty.data().path("status").asText()).isEqualTo("SUCCEEDED");

        // APPLY：只登记受理（执行器 T-M4-08~11 未落地），状态 PENDING 且明细 PENDING
        // APPLY 的上游零写入必须相对**发请求前的基线**读（绝对值会把本方法前半段插入的绑定夹具算成「APPLY 写了上游」；
        // 也不能在请求之后再取基线 —— 那是恒真的空转判据，历史 19/81/230）
        long bindingsBeforeApply = jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class);
        long syncTasksBeforeApply = jdbc.queryForObject("select count(*) from aap_sync_task", Long.class);
        HttpResult apply = post("/admin/config-batches", """
                {"batch_type":"ADD_CHANNEL","mode":"APPLY","scope":{"supplyUnitIds":[830001]}}
                """, techOps);
        assertThat(apply.status()).as(apply.body()).isEqualTo(201);
        assertThat(apply.data().path("mode").asText()).isEqualTo("APPLY");
        assertThat(apply.data().path("status").asText()).isEqualTo("PENDING");
        assertThat(apply.data().path("items").get(0).path("status").asText()).isEqualTo("PENDING");
        assertThat(jdbc.queryForObject("select status from aap_config_batch where id = ?", String.class,
                Long.parseLong(apply.data().path("id").asText()))).as("响应与库同源").isEqualTo("PENDING");
        // 上游零写入的判据必须相对**发请求前的基线**（本方法前半段为「标签维度」插过 1 条绑定夹具，
        // 绝对 `isZero()` 会把夹具算成「APPLY 写了上游」——判据范围与语义不符，历史 19/81）
        assertThat(jdbc.queryForObject("select count(*) from aap_channel_binding", Long.class))
                .as("APPLY 尚未执行 ⇒ 不改上游（基线 %d 条）", bindingsBeforeApply).isEqualTo(bindingsBeforeApply);
        assertThat(jdbc.queryForObject("select count(*) from aap_sync_task", Long.class))
                .as("APPLY 尚未执行 ⇒ 不排队同步任务（基线 %d 条）", syncTasksBeforeApply).isEqualTo(syncTasksBeforeApply);

        // 请求校验（清单 §2.6 的 `batch_type`/`mode` 是必填；非法值必须 400 而不是落库报 500，踩坑 21/130）
        assertThat(post("/admin/config-batches", """
                {"mode":"DRY_RUN"}
                """, techOps).code()).as("缺 batch_type").isEqualTo("E-1001");
        assertThat(post("/admin/config-batches", """
                {"batch_type":"NO_SUCH_TYPE","mode":"DRY_RUN"}
                """, techOps).code()).as("非法 batch_type").isEqualTo("E-1001");
        assertThat(post("/admin/config-batches", """
                {"batch_type":"RECONFIG","mode":"MAYBE"}
                """, techOps).code()).as("非法 mode").isEqualTo("E-1001");
        HttpResult badRate = post("/admin/config-batches", """
                {"batch_type":"RECONFIG","mode":"DRY_RUN","rate_limit_per_sec":20}
                """, techOps);
        assertThat(badRate.status()).as(badRate.body()).isEqualTo(400);
        assertThat(badRate.code()).as("R-57：限速上限 5，不接受抬高").isEqualTo("E-1001");

        // R-57「每批 ≤20」+ 影响面确认：恰好 20 个可行（AC-10），21 个 → 409 E-1601
        StringBuilder twenty = new StringBuilder();
        for (int i = 0; i < 20; i++) {
            insertSupplyUnit(840000L + i, 820002, "bulk-" + i, "ONLINE", "2026-09-10T00:00:00Z");
            if (i > 0) {
                twenty.append(',');
            }
            twenty.append(840000L + i);
        }
        HttpResult exactly20 = post("/admin/config-batches", """
                {"batch_type":"UPDATE_CHANNEL","mode":"DRY_RUN","scope":{"supplyUnitIds":[%s]}}
                """.formatted(twenty), techOps);
        assertThat(exactly20.status()).as(exactly20.body()).as("AC-10：20 个供给单元的 dry-run").isEqualTo(201);
        assertThat(exactly20.data().path("total_count").asInt()).isEqualTo(20);

        insertSupplyUnit(845000, 820002, "bulk-21", "ONLINE", "2026-09-11T00:00:00Z");
        HttpResult tooMany = post("/admin/config-batches", """
                {"batch_type":"UPDATE_CHANNEL","mode":"DRY_RUN","scope":{"providerIds":[820002]}}
                """, techOps);
        assertThat(tooMany.status()).as(tooMany.body()).as("21 个 > R-57 每批 20").isEqualTo(409);
        assertThat(tooMany.code()).isEqualTo("E-1601");
    }

    // ------------------------------------------------------------------ ADM-CB02

    @Test
    @DisplayName("ADM-CB02 批次列表：分页 + status 过滤（大小写不敏感）+ 逻辑删除不出现 + 排序 created_at desc,id desc")
    void listBatches() {
        String techOps = adminToken(970411L, "TECH_OPS");
        insertBatch(850001, "CFG-B202609-0001", "RECONFIG", "DRY_RUN", "SUCCEEDED", 3, 0, 0, 0,
                "2026-09-01T00:00:00Z", false);
        insertBatch(850002, "CFG-B202609-0002", "ADD_CHANNEL", "APPLY", "PENDING", 5, 0, 0, 0,
                "2026-09-02T00:00:00Z", false);
        insertBatch(850003, "CFG-B202609-0003", "WRITE_PRICE", "APPLY", "FAILED", 2, 1, 1, 0,
                "2026-09-03T00:00:00Z", false);
        insertBatch(850004, "CFG-B202609-0004", "OFFLINE", "APPLY", "SUCCEEDED", 1, 1, 0, 0,
                "2026-09-04T00:00:00Z", true);
        insertItem(860001, 850001, 830001, "gpt-4o", "CREATE", "SKIPPED", 0, "CFG-B202609-0001:830001", null, null);

        HttpResult list = get("/admin/config-batches", techOps);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(list.body());
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).as("逻辑删除的批次不得出现").isEqualTo(3L);
        assertThat(list.data().path("page").asInt()).isEqualTo(1);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(list.data().path("items").size()).isEqualTo(3);
        for (JsonNode item : list.data().path("items")) {
            SchemaAssert.assertModel("config-batch", json(item));
        }
        JsonNode first = list.data().path("items").get(0);
        assertThat(first.path("id").asText()).as("排序 created_at desc, id desc").isEqualTo("850003");
        assertThat(first.path("batch_no").asText()).isEqualTo("CFG-B202609-0003");
        assertThat(first.path("status").asText()).isEqualTo("FAILED");
        assertThat(first.path("failed_count").asInt()).isEqualTo(1);
        assertThat(first.path("items").isArray()).as("列表行也必须带明细数组（同一模型同一形状）").isTrue();

        HttpResult byStatus = get("/admin/config-batches?status=pending", techOps);
        assertThat(byStatus.data().path("total").asLong()).as("状态过滤大小写不敏感").isEqualTo(1L);
        assertThat(byStatus.data().path("items").get(0).path("batch_no").asText()).isEqualTo("CFG-B202609-0002");
        assertThat(byStatus.data().path("items").get(0).path("items").size()).as("该批次无明细").isZero();
        assertThat(get("/admin/config-batches?status=NoneSuchStatus", techOps).data().path("total").asLong()).isZero();

        HttpResult paged = get("/admin/config-batches?page=2&pageSize=2", techOps);
        assertThat(paged.data().path("page").asInt()).isEqualTo(2);
        assertThat(paged.data().path("pageSize").asInt()).isEqualTo(2);
        assertThat(paged.data().path("total").asLong()).isEqualTo(3L);
        assertThat(paged.data().path("items").size()).isEqualTo(1);
        assertThat(paged.data().path("items").get(0).path("id").asText()).isEqualTo("850001");
        assertThat(paged.data().path("items").get(0).path("items").size())
                .as("分页行也补齐所属明细").isEqualTo(1);
    }

    // ------------------------------------------------------------------ ADM-CB03

    @Test
    @DisplayName("ADM-CB03 详情：含明细与 mismatch 清单；不存在/已删除 404 E-1406，非法 id 400 E-1001")
    void batchDetail() {
        String techOps = adminToken(970421L, "TECH_OPS");
        insertBatch(850001, "CFG-B202609-0001", "RECONFIG", "APPLY", "PARTIAL", 2, 1, 0, 1,
                "2026-09-01T00:00:00Z", false);
        insertItem(860001, 850001, 830001, "gpt-4o", "UPDATE", "SUCCEEDED", 1, "CFG-B202609-0001:830001",
                true, null);
        insertItem(860002, 850001, 830002, "claude-3-5", "UPDATE", "MISMATCH", 2, "CFG-B202609-0001:830002",
                false, "回读不一致：weight 期望 80 实读 60");
        insertBatch(850002, "CFG-B202609-0009", "OFFLINE", "APPLY", "SUCCEEDED", 0, 0, 0, 0, V, true);

        HttpResult detail = get("/admin/config-batches/850001", techOps);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(detail.body());
        SchemaAssert.assertModel("config-batch", json(detail.data()));
        assertThat(detail.data().path("batch_no").asText()).isEqualTo("CFG-B202609-0001");
        assertThat(detail.data().path("mismatch_count").asInt()).as("回读不一致数必须可见（R-58）").isEqualTo(1);
        assertThat(detail.data().path("items").size()).as("明细必须在**响应体**里补齐（踩坑 22）").isEqualTo(2);
        JsonNode mismatch = detail.data().path("items").get(1);
        SchemaAssert.assertModel("config-batch-item", json(mismatch));
        assertThat(mismatch.path("id").asText()).isEqualTo("860002");
        assertThat(mismatch.path("status").asText()).as("mismatch 清单 = 明细里 status=MISMATCH 的项").isEqualTo("MISMATCH");
        assertThat(mismatch.path("readback_equal").asBoolean()).isFalse();
        assertThat(mismatch.path("attempt_count").asInt()).isEqualTo(2);
        assertThat(mismatch.path("last_error").asText()).contains("回读不一致");
        assertThat(detail.data().path("items").get(0).path("readback_equal").asBoolean()).isTrue();
        assertThat(detail.data().path("created_at").asText()).as("RFC3339 UTC").isEqualTo("2026-09-01T00:00:00Z");

        HttpResult missing = get("/admin/config-batches/999999", techOps);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        HttpResult deleted = get("/admin/config-batches/850002", techOps);
        assertThat(deleted.status()).as(deleted.body()).as("逻辑删除的批次不可见").isEqualTo(404);
        assertThat(deleted.code()).isEqualTo("E-1406");
        HttpResult badId = get("/admin/config-batches/abc", techOps);
        assertThat(badId.status()).as(badId.body()).isEqualTo(400);
        assertThat(badId.code()).isEqualTo("E-1001");
    }

    // ------------------------------------------------------------------ ADM-CB04

    @Test
    @DisplayName("ADM-CB04 单模型重试：202 + 该项回 PENDING/attempt+1 + R-59 兄弟项逐列不变 + 不可重试 409")
    void retryItem() {
        String techOps = adminToken(970431L, "TECH_OPS");
        insertBatch(850001, "CFG-B202609-0001", "ADD_CHANNEL", "APPLY", "FAILED", 2, 1, 1, 0,
                "2026-09-01T00:00:00Z", false);
        insertItem(860001, 850001, 830001, "gpt-4o", "CREATE", "FAILED", 1, "CFG-B202609-0001:830001",
                null, "网关 503");
        insertItem(860002, 850001, 830002, "claude-3-5", "CREATE", "SUCCEEDED", 1, "CFG-B202609-0001:830002",
                true, null);
        insertBatch(850002, "CFG-B202609-0002", "ADD_CHANNEL", "APPLY", "FAILED", 1, 0, 1, 0,
                "2026-09-02T00:00:00Z", false);
        insertItem(860003, 850002, 830003, "gpt-4o-mini", "CREATE", "FAILED", 1, "CFG-B202609-0002:830003",
                null, "网关 503");
        Map<String, Object> siblingBefore = jdbc.queryForMap(
                "select status, attempt_count, readback_equal, version from aap_config_batch_item where id = 860002");

        HttpResult retry = post("/admin/config-batches/850001/items/860001/retry", null, techOps);
        assertThat(retry.status()).as(retry.body()).as("清单 §2.6：重试 → 202").isEqualTo(202);
        SchemaAssert.assertEnvelope(retry.body());
        SchemaAssert.assertModel("config-batch-item", json(retry.data()));
        assertThat(retry.data().path("id").asText()).isEqualTo("860001");
        assertThat(retry.data().path("status").asText()).as("重试 = 重新排队（执行器消费）").isEqualTo("PENDING");
        assertThat(retry.data().path("attempt_count").asInt()).as("本次入队要计入尝试次数").isEqualTo(2);

        // 响应 ⇔ 库同源 + 幂等键复用（重试必须复用同一键，否则上游会重复建渠道，C-11/R-58）
        Map<String, Object> itemRow = jdbc.queryForMap(
                "select status, attempt_count, idempotency_key, updated_at, version"
                        + " from aap_config_batch_item where id = 860001");
        assertThat(itemRow.get("status")).as(retry.body()).isEqualTo("PENDING");
        assertThat(((Number) itemRow.get("attempt_count")).intValue()).isEqualTo(2);
        assertThat(itemRow.get("idempotency_key")).isEqualTo("CFG-B202609-0001:830001");
        assertThat(((Number) itemRow.get("version")).intValue()).as("乐观锁版本推进").isEqualTo(1);
        // 批次侧：重新进入运行态 + 计数重算 + 留痕列
        Map<String, Object> batchRow = jdbc.queryForMap(
                "select status, succeeded_count, failed_count, mismatch_count, updated_by, version"
                        + " from aap_config_batch where id = 850001");
        assertThat(batchRow.get("status")).as("有待执行项 ⇒ 批次回到 RUNNING").isEqualTo("RUNNING");
        assertThat(((Number) batchRow.get("succeeded_count")).intValue()).as("仅有 1 项成功").isEqualTo(1);
        assertThat(((Number) batchRow.get("failed_count")).intValue()).as("失败的项已回到 PENDING").isZero();
        assertThat(((Number) batchRow.get("updated_by")).longValue()).isEqualTo(970431L);
        assertThat(((Number) batchRow.get("version")).intValue()).isEqualTo(1);
        // R-59 单模型隔离：兄弟项与另一批次的项逐列不变
        assertThat(jdbc.queryForMap("select status, attempt_count, readback_equal, version"
                + " from aap_config_batch_item where id = 860002")).as("重试不得波及兄弟项（R-59）")
                .isEqualTo(siblingBefore);
        assertThat(jdbc.queryForObject("select status from aap_config_batch_item where id = 860003", String.class))
                .as("另一批次的项不受影响").isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("select status from aap_config_batch where id = 850002", String.class))
                .isEqualTo("FAILED");

        // 状态守卫：成功的项不可重试 → 409 E-1601
        HttpResult notRetryable = post("/admin/config-batches/850001/items/860002/retry", null, techOps);
        assertThat(notRetryable.status()).as(notRetryable.body()).isEqualTo(409);
        assertThat(notRetryable.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select status from aap_config_batch_item where id = 860002", String.class))
                .as("被拒的重试不得改动该项").isEqualTo("SUCCEEDED");

        // 归属校验：明细必须属于该批次（否则 404，不泄露跨批次存在性）
        HttpResult crossBatch = post("/admin/config-batches/850001/items/860003/retry", null, techOps);
        assertThat(crossBatch.status()).as(crossBatch.body()).isEqualTo(404);
        assertThat(crossBatch.code()).isEqualTo("E-1406");
        HttpResult missingItem = post("/admin/config-batches/850001/items/999999/retry", null, techOps);
        assertThat(missingItem.status()).as(missingItem.body()).isEqualTo(404);
        assertThat(missingItem.code()).isEqualTo("E-1406");
        HttpResult missingBatch = post("/admin/config-batches/999999/items/860001/retry", null, techOps);
        assertThat(missingBatch.status()).as(missingBatch.body()).isEqualTo(404);
        assertThat(missingBatch.code()).isEqualTo("E-1406");
    }

    // ------------------------------------------------------------------ ADM-CB05

    @Test
    @DisplayName("ADM-CB05 单模型回滚：202 + 该项 ROLLED_BACK/理由留痕 + R-59 兄弟项不变 + reason 必填 400 + 状态守卫 409")
    void rollbackItem() {
        String techOps = adminToken(970441L, "TECH_OPS");
        insertBatch(850001, "CFG-B202609-0001", "RECONFIG", "APPLY", "SUCCEEDED", 2, 2, 0, 0,
                "2026-09-01T00:00:00Z", false);
        insertItem(860001, 850001, 830001, "gpt-4o", "UPDATE", "SUCCEEDED", 1, "CFG-B202609-0001:830001", true, null);
        insertItem(860002, 850001, 830002, "claude-3-5", "UPDATE", "SUCCEEDED", 1, "CFG-B202609-0001:830002", true, null);
        insertItem(860004, 850001, 830003, "gpt-4o-mini", "UPDATE", "PENDING", 0, "CFG-B202609-0001:830003", null, null);

        HttpResult rollback = post("/admin/config-batches/850001/items/860001/rollback", """
                {"reason":"回读不一致，按 R-59 只回滚该模型"}
                """, techOps);
        assertThat(rollback.status()).as(rollback.body()).as("清单 §2.6：回滚 → 202").isEqualTo(202);
        SchemaAssert.assertEnvelope(rollback.body());
        SchemaAssert.assertModel("config-batch-item", json(rollback.data()));
        assertThat(rollback.data().path("id").asText()).isEqualTo("860001");
        assertThat(rollback.data().path("status").asText()).isEqualTo("ROLLED_BACK");

        Map<String, Object> itemRow = jdbc.queryForMap(
                "select status, reason, updated_at, version from aap_config_batch_item where id = 860001");
        assertThat(itemRow.get("status")).as(rollback.body()).isEqualTo("ROLLED_BACK");
        assertThat(itemRow.get("reason")).as("回滚理由必须留痕").isEqualTo("回读不一致，按 R-59 只回滚该模型");
        assertThat(((Number) itemRow.get("version")).intValue()).isEqualTo(1);
        Map<String, Object> batchRow = jdbc.queryForMap(
                "select status, succeeded_count, failed_count, mismatch_count, updated_by"
                        + " from aap_config_batch where id = 850001");
        assertThat(batchRow.get("status")).as("部分回滚 ⇒ 批次 PARTIAL（不得仍称成功）").isEqualTo("PARTIAL");
        assertThat(((Number) batchRow.get("succeeded_count")).intValue()).isEqualTo(1);
        assertThat(((Number) batchRow.get("updated_by")).longValue()).isEqualTo(970441L);
        // R-59 单模型隔离：兄弟项逐列不变
        assertThat(jdbc.queryForMap("select status, reason, attempt_count, version"
                + " from aap_config_batch_item where id = 860002").get("status")).isEqualTo("SUCCEEDED");
        assertThat(jdbc.queryForObject("select status from aap_config_batch_item where id = 860004", String.class))
                .as("同批次待执行项不受回滚影响").isEqualTo("PENDING");

        // reason 必填（requests/config-batch-rollback.schema.json 的 required）
        HttpResult noReason = post("/admin/config-batches/850001/items/860002/rollback", "{}", techOps);
        assertThat(noReason.status()).as(noReason.body()).isEqualTo(400);
        assertThat(noReason.code()).isEqualTo("E-1001");
        HttpResult blankReason = post("/admin/config-batches/850001/items/860002/rollback", """
                {"reason":"   "}
                """, techOps);
        assertThat(blankReason.status()).as(blankReason.body()).isEqualTo(400);
        assertThat(blankReason.code()).isEqualTo("E-1001");
        assertThat(jdbc.queryForObject("select status from aap_config_batch_item where id = 860002", String.class))
                .as("缺理由被拒 ⇒ 不得改动该行").isEqualTo("SUCCEEDED");

        // 状态守卫：未执行成功的项不可回滚 → 409；已回滚项重复回滚 → 409；跨批次 → 404
        HttpResult pendingItem = post("/admin/config-batches/850001/items/860004/rollback", """
                {"reason":"未执行成功不可回滚"}
                """, techOps);
        assertThat(pendingItem.status()).as(pendingItem.body()).isEqualTo(409);
        assertThat(pendingItem.code()).isEqualTo("E-1601");
        HttpResult again = post("/admin/config-batches/850001/items/860001/rollback", """
                {"reason":"重复回滚"}
                """, techOps);
        assertThat(again.status()).as(again.body()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select reason from aap_config_batch_item where id = 860001", String.class))
                .as("被拒的回滚不得覆盖原理由").isEqualTo("回读不一致，按 R-59 只回滚该模型");
        HttpResult crossBatch = post("/admin/config-batches/850002/items/860001/rollback", """
                {"reason":"跨批次"}
                """, techOps);
        assertThat(crossBatch.status()).as(crossBatch.body()).isEqualTo(404);
        assertThat(crossBatch.code()).isEqualTo("E-1406");
        HttpResult missingBatch = post("/admin/config-batches/999999/items/860001/rollback", """
                {"reason":"批次不存在"}
                """, techOps);
        assertThat(missingBatch.status()).as(missingBatch.body()).isEqualTo(404);
        assertThat(missingBatch.code()).isEqualTo("E-1406");
    }

    // ------------------------------------------------------------------ 权限

    @Test
    @DisplayName("ADM-CB01…05 权限：TECH_OPS/SUPER_ADMIN 可用；BIZ_OPERATOR 与供应商 403 E-1901、未认证 401 E-1902")
    void permissions() {
        String supplier = supplierToken();
        String techOps = adminToken(970451L, "TECH_OPS");
        String superAdmin = adminToken(970452L, "SUPER_ADMIN");
        String bizOperator = adminToken(970453L, "BIZ_OPERATOR");
        insertBatch(850001, "CFG-B202609-0001", "ADD_CHANNEL", "APPLY", "FAILED", 2, 1, 1, 0, V, false);
        insertItem(860001, 850001, 830001, "gpt-4o", "CREATE", "FAILED", 1, "CFG-B202609-0001:830001", null, "网关 503");
        insertItem(860002, 850001, 830002, "claude-3-5", "CREATE", "FAILED", 1, "CFG-B202609-0001:830002", null, "网关 503");

        assertThat(get("/admin/config-batches", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/config-batches", superAdmin).status()).isEqualTo(200);
        assertThat(get("/admin/config-batches/850001", techOps).status()).isEqualTo(200);
        assertThat(post("/admin/config-batches", """
                {"batch_type":"RECONFIG","mode":"DRY_RUN","scope":{"supplyUnitIds":[830001]}}
                """, superAdmin).status()).isEqualTo(201);
        assertThat(post("/admin/config-batches/850001/items/860001/retry", null, superAdmin).status()).isEqualTo(202);
        assertThat(post("/admin/config-batches/850001/items/860002/rollback", """
                {"reason":"超管回滚"}
                """, superAdmin).status()).as("超管可回滚（回滚只对 SUCCEEDED 项生效，此处 409 也说明路由已放行）")
                .isIn(202, 409);

        // BIZ_OPERATOR 不在清单角色列 → 403（不得因「也是管理端」而放行）
        HttpResult bizList = get("/admin/config-batches", bizOperator);
        assertThat(bizList.status()).as(bizList.body()).isEqualTo(403);
        assertThat(bizList.code()).isEqualTo("E-1901");
        assertThat(post("/admin/config-batches", """
                {"batch_type":"RECONFIG","mode":"DRY_RUN"}
                """, bizOperator).status()).isEqualTo(403);
        assertThat(post("/admin/config-batches/850001/items/860002/retry", null, bizOperator).status()).isEqualTo(403);

        HttpResult supplierList = get("/admin/config-batches", supplier);
        assertThat(supplierList.status()).as(supplierList.body()).isEqualTo(403);
        assertThat(supplierList.code()).isEqualTo("E-1901");
        assertThat(get("/admin/config-batches/850001", supplier).status()).isEqualTo(403);
        assertThat(post("/admin/config-batches/850001/items/860002/retry", null, supplier).status()).isEqualTo(403);
        assertThat(jdbc.queryForObject("select status from aap_config_batch_item where id = 860002", String.class))
                .as("越权请求不得改动状态").isEqualTo("FAILED");

        HttpResult anonymous = get("/admin/config-batches");
        assertThat(anonymous.status()).as(anonymous.body()).isEqualTo(401);
        assertThat(anonymous.code()).isEqualTo("E-1902");
    }
}
