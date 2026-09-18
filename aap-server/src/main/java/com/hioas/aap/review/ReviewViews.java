package com.hioas.aap.review;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import tools.jackson.databind.JsonNode;

/**
 * 审核响应模型（契约真源：`docs/backend/json-schema/models/review-task.schema.json` /
 * `review-record.schema.json`，由 `tools/gen-backend-models.py` 从冻结清单生成）。
 *
 * <p>字段一律 snake_case；雪花 ID 对外**一律 string**（避免 JS 精度丢失，同全项目口径）；
 * 时间戳 RFC3339 UTC；缺值回 null（前端渲染占位符），不用空串/0 冒充。
 *
 * <p>{@code review_id} 是任务主键的兼容别名（模型里同时给了 id/review_id）——两处同值，
 * 不引入第二套主键语义。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class ReviewViews {

    private ReviewViews() {
    }

    /** ADM-R01/R02/R03/R04 的审核任务视图。 */
    public record Task(
            String id,
            @JsonProperty("review_id") String reviewId,
            @JsonProperty("quote_id") String quoteId,
            @JsonProperty("quote_no") String quoteNo,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("provider_name") String providerName,
            String status,
            @JsonProperty("claimed_by") String claimedBy,
            @JsonProperty("claimed_at") String claimedAt,
            @JsonProperty("review_comment") String reviewComment,
            @JsonProperty("reject_reason_code") String rejectReasonCode,
            @JsonProperty("tech_metrics_snapshot") JsonNode techMetricsSnapshot,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt) {
    }

    /** ADM-R05 审核记录（行动时间线）。 */
    public record Record(
            String id,
            @JsonProperty("quote_id") String quoteId,
            @JsonProperty("task_id") String taskId,
            String action,
            @JsonProperty("operator_id") String operatorId,
            @JsonProperty("operator_name") String operatorName,
            @JsonProperty("before_status") String beforeStatus,
            @JsonProperty("after_status") String afterStatus,
            String comment,
            @JsonProperty("created_at") String createdAt) {
    }

    /** ADM-R05 响应体：{@code {items:[ReviewRecord]}}（清单里该端点为非分页数组）。 */
    public record RecordList(@JsonProperty("items") List<Record> items) {
    }
}
