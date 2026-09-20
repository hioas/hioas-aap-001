package com.hioas.aap.common;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.DbTestBase;
import java.util.List;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationInfo;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T02 · 数据库迁移测试（`docs/backend/01-ER数据模型.md` 的 54 张表必须真的建出来）。
 */
class MigrationTest extends DbTestBase {

    /** ER 文档 §3 表清单（顺序无关，逐条比对）。 */
    private static final List<String> EXPECTED_TABLES = List.of(
            // iam
            "aap_provider_account", "aap_admin_user", "aap_role", "aap_user_role", "aap_sms_code",
            "aap_wechat_binding", "aap_auth_token",
            // provider
            "aap_provider", "aap_provider_qualification",
            // credential
            "aap_credential", "aap_credential_precheck", "aap_provider_challenge",
            // detection
            "aap_detection_config", "aap_detection_config_probe", "aap_detection_job", "aap_detection_result",
            "aap_detection_baseline", "aap_baseline_sample", "aap_probe_question",
            // report
            "aap_report_template", "aap_report", "aap_report_section",
            // quote
            "aap_quote", "aap_quote_version", "aap_quote_item", "aap_price_time_rule", "aap_price_time_segment",
            "aap_price_tier_rule", "aap_price_tier", "aap_price_request_rule", "aap_reference_price",
            // review
            "aap_review_task", "aap_review_record",
            // contract
            "aap_contract", "aap_contract_sign",
            // settlement
            "aap_payment_record", "aap_settlement_statement", "aap_settlement_line",
            // compilation
            "aap_compiled_expression", "aap_model_expression", "aap_verify_run", "aap_verify_case",
            // sync
            "aap_newapi_endpoint", "aap_channel_binding", "aap_sync_task", "aap_sync_operation", "aap_sync_log",
            // catalog（V9：模型目录 —— 管理端 page-3/3.1/3.2；H5 凭证页模型下拉的数据源）
            "aap_vendor", "aap_model",
            // usage
            "aap_usage_hourly", "aap_usage_sync_cursor",
            // support
            "aap_audit_log", "aap_notification", "aap_file_asset", "aap_outbox_event", "aap_idempotency_record");

    @Autowired
    private Flyway flyway;

    @Test
    @DisplayName("54 张 ER 表全部存在（与 docs/backend/01-ER数据模型.md §3 逐条一致）")
    void allErTablesExist() {
        // 排除分区子表（如 aap_usage_hourly_default）：那些是分区实现细节，不是业务表
        List<String> actual = jdbc.queryForList("""
                select c.relname from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'public' and c.relkind in ('r', 'p') and c.relname like 'aap\\_%'
                  and not exists (select 1 from pg_inherits i where i.inhrelid = c.oid)
                order by c.relname
                """, String.class);
        assertThat(actual)
                .as("ER 文档表清单与迁移结果必须一致（缺表或多余表都要红）")
                .containsExactlyInAnyOrderElementsOf(EXPECTED_TABLES);
        assertThat(EXPECTED_TABLES).hasSize(56);
    }

    @Test
    @DisplayName("迁移可重入：再跑一次 Flyway 不报错且无新迁移（幂等自愈）")
    void migrationIsIdempotent() {
        var result = flyway.migrate();
        assertThat(result.migrationsExecuted).as("第二次迁移不应重复执行").isZero();
        MigrationInfo[] applied = flyway.info().applied();
        assertThat(applied).isNotEmpty();
        assertThat(applied[applied.length - 1].getState().isApplied()).isTrue();
    }

    @Test
    @DisplayName("关键唯一约束存在：C1 主凭证 / C2 活跃任务 / C3 明细行 / C7 用量桶 / C11 幂等键")
    void criticalUniqueIndexesExist() {
        List<String> indexes = jdbc.queryForList(
                "select indexname from pg_indexes where schemaname='public'", String.class);
        assertThat(indexes).contains(
                "uq_credential_primary", "uq_credential_fingerprint", "uq_job_active",
                "uq_quote_item_model", "uq_usage_hourly", "uq_sync_idempotency", "uq_idempotency_key",
                "uq_provider_uscc", "uq_report_job", "uq_result_job_probe");
    }

    @Test
    @DisplayName("aap_usage_hourly 是按月 RANGE 分区的分区表（含 default 分区，未建月分区也不丢数据）")
    void usageHourlyIsPartitioned() {
        String strategy = jdbc.queryForObject("""
                select p.partstrat from pg_partitioned_table p
                join pg_class c on c.oid = p.partrelid
                where c.relname = 'aap_usage_hourly'
                """, String.class);
        assertThat(strategy).isEqualTo("r");

        List<String> partitions = jdbc.queryForList("""
                select c.relname from pg_class c
                join pg_inherits i on i.inhrelid = c.oid
                join pg_class p on p.oid = i.inhparent
                where p.relname = 'aap_usage_hourly'
                """, String.class);
        assertThat(partitions).contains("aap_usage_hourly_default");
    }

    @Test
    @DisplayName("业务表通用审计字段齐备（id/created_at/updated_at/created_by/updated_by/deleted/version）")
    void auditColumnsPresent() {
        List<String> columns = jdbc.queryForList("""
                select column_name from information_schema.columns
                where table_schema='public' and table_name='aap_provider'
                """, String.class);
        assertThat(columns).contains(
                "id", "created_at", "updated_at", "created_by", "updated_by", "deleted", "version");
    }
}
