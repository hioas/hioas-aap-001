package com.hioas.aap.supply;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;

/**
 * 供给单元与配置批次的管理端视图（ADM-SU / ADM-CB 的响应体）。
 *
 * <p>契约真源：`docs/backend/json-schema/models/{supply-unit,config-batch,config-batch-item}.schema.json`
 * （由 `tools/gen-backend-models.py` 生成）+ `specs/001-intake-automation/contracts/intake-automation.openapi.yaml`。
 *
 * <p>ID 一律以 **string** 对外（雪花 ID 超出 JS 安全整数范围，与既有约定一致）。
 *
 * <p>键名口径：这三个模型的 schema **只声明 snake_case 键**（无 camelCase 别名，且 `aap-admin`
 * 尚未消费本族）⇒ 用 {@code @JsonProperty} 把出口键钉成 schema 的键名，与 `DetectionConfigViews`
 * 的既有做法一致。将来客户端若改 camelCase，按坑 1「契约字段名回客户端适配层核对」先改 schema（生成器）再改这里。
 */
public final class SupplyUnitViews {

    private SupplyUnitViews() {
    }

    /** 供给单元（契约 model：supply-unit）。 */
    public record SupplyUnit(@JsonProperty("id") String id,
                             @JsonProperty("provider_id") String providerId,
                             @JsonProperty("credential_id") String credentialId,
                             @JsonProperty("model_name") String modelName,
                             @JsonProperty("model_slug") String modelSlug,
                             @JsonProperty("model_uid") String modelUid,
                             @JsonProperty("status") String status,
                             @JsonProperty("detect_total_score") BigDecimal detectTotalScore,
                             @JsonProperty("detect_confidence") String detectConfidence,
                             @JsonProperty("quality_score") BigDecimal qualityScore,
                             @JsonProperty("routing_priority") Integer routingPriority,
                             @JsonProperty("routing_weight") Integer routingWeight,
                             @JsonProperty("auto_ban_enabled") Boolean autoBanEnabled,
                             @JsonProperty("binding_id") String bindingId,
                             @JsonProperty("granularity") String granularity,
                             @JsonProperty("created_at") String createdAt) {
    }

    /** 配置批次（契约 model：config-batch）。 */
    public record ConfigBatch(@JsonProperty("id") String id,
                              @JsonProperty("batch_no") String batchNo,
                              @JsonProperty("batch_type") String batchType,
                              @JsonProperty("mode") String mode,
                              @JsonProperty("trigger_source") String triggerSource,
                              @JsonProperty("status") String status,
                              @JsonProperty("total_count") Integer totalCount,
                              @JsonProperty("succeeded_count") Integer succeededCount,
                              @JsonProperty("failed_count") Integer failedCount,
                              @JsonProperty("mismatch_count") Integer mismatchCount,
                              @JsonProperty("rate_limit_per_sec") Integer rateLimitPerSec,
                              @JsonProperty("diff_summary") Object diffSummary,
                              @JsonProperty("started_at") String startedAt,
                              @JsonProperty("finished_at") String finishedAt,
                              @JsonProperty("created_at") String createdAt,
                              @JsonProperty("items") List<ConfigBatchItem> items) {
    }

    /** 批次明细（契约 model：config-batch-item）。 */
    public record ConfigBatchItem(@JsonProperty("id") String id,
                                  @JsonProperty("batch_id") String batchId,
                                  @JsonProperty("supply_unit_id") String supplyUnitId,
                                  @JsonProperty("provider_id") String providerId,
                                  @JsonProperty("model_name") String modelName,
                                  @JsonProperty("action") String action,
                                  @JsonProperty("status") String status,
                                  @JsonProperty("readback_equal") Boolean readbackEqual,
                                  @JsonProperty("attempt_count") Integer attemptCount,
                                  @JsonProperty("last_error") String lastError,
                                  @JsonProperty("created_at") String createdAt) {
    }

    /** 重配置请求（契约 request：supply-unit-reconfigure；`dry_run` 省略即默认 true）。 */
    public record ReconfigureRequest(@JsonProperty("dry_run") Boolean dryRun,
                                     @JsonProperty("reason") String reason) {
    }

    /** 批次创建请求（契约 request：config-batch-create）。 */
    public record ConfigBatchCreateRequest(@JsonProperty("batch_type") String batchType,
                                           @JsonProperty("mode") String mode,
                                           @JsonProperty("scope") Object scope,
                                           @JsonProperty("rate_limit_per_sec") Integer rateLimitPerSec,
                                           @JsonProperty("reason") String reason) {
    }

    /** 回滚请求（契约 request：config-batch-rollback，理由必填）。 */
    public record RollbackRequest(@JsonProperty("reason") String reason) {
    }
}
