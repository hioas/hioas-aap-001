package com.hioas.aap.supply;

import java.math.BigDecimal;
import java.util.List;

/**
 * 供给单元与配置批次的管理端视图（ADM-SU / ADM-CB 的响应体）。
 *
 * <p>契约真源：`docs/backend/json-schema/models/{supply-unit,config-batch,config-batch-item}.schema.json`
 * （由 `tools/gen-backend-models.py` 生成）+ `specs/001-intake-automation/contracts/intake-automation.openapi.yaml`。
 *
 * <p>ID 一律以 **string** 对外（雪花 ID 超出 JS 安全整数范围，与既有约定一致）。
 */
public final class SupplyUnitViews {

    private SupplyUnitViews() {
    }

    /** 供给单元（契约 model：supply-unit）。 */
    public record SupplyUnit(String id,
                             String providerId,
                             String credentialId,
                             String modelName,
                             String modelSlug,
                             String modelUid,
                             String status,
                             BigDecimal detectTotalScore,
                             String detectConfidence,
                             BigDecimal qualityScore,
                             Integer routingPriority,
                             Integer routingWeight,
                             Boolean autoBanEnabled,
                             String bindingId,
                             String granularity,
                             String createdAt) {
    }

    /** 配置批次（契约 model：config-batch）。 */
    public record ConfigBatch(String id,
                              String batchNo,
                              String batchType,
                              String mode,
                              String triggerSource,
                              String status,
                              Integer totalCount,
                              Integer succeededCount,
                              Integer failedCount,
                              Integer mismatchCount,
                              Integer rateLimitPerSec,
                              Object diffSummary,
                              String startedAt,
                              String finishedAt,
                              String createdAt,
                              List<ConfigBatchItem> items) {
    }

    /** 批次明细（契约 model：config-batch-item）。 */
    public record ConfigBatchItem(String id,
                                  String batchId,
                                  String supplyUnitId,
                                  String providerId,
                                  String modelName,
                                  String action,
                                  String status,
                                  Boolean readbackEqual,
                                  Integer attemptCount,
                                  String lastError,
                                  String createdAt) {
    }

    /** 重配置请求（契约 request：supply-unit-reconfigure）。 */
    public record ReconfigureRequest(Boolean dryRun, String reason) {
    }

    /** 批次创建请求（契约 request：config-batch-create）。 */
    public record ConfigBatchCreateRequest(String batchType, String mode, Object scope,
                                           Integer rateLimitPerSec, String reason) {
    }

    /** 回滚请求（契约 request：config-batch-rollback，理由必填）。 */
    public record RollbackRequest(String reason) {
    }
}
