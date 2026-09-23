package com.hioas.aap.detection;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 检测任务响应模型（契约：docs/backend/json-schema/models/detection-job.schema.json /
 * detection-result.schema.json）。
 *
 * <p>{@code progress} 供「检测进行中」页（序号 5）轮询展示；{@code detection_status} 回写凭证后
 * 供凭证列表状态 chips 使用。
 */
public final class DetectionViews {

    private DetectionViews() {
    }

    public record Progress(
            @JsonProperty("percent") BigDecimal percent,
            @JsonProperty("finished") Integer finished,
            @JsonProperty("total") Integer total,
            @JsonProperty("eta_minutes") BigDecimal etaMinutes) {
    }

    public record Job(
            @JsonProperty("id") String id,
            @JsonProperty("job_id") String jobId,
            @JsonProperty("job_no") String jobNo,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("credential_id") String credentialId,
            @JsonProperty("status") String status,
            @JsonProperty("trigger_type") String triggerType,
            @JsonProperty("started_at") String startedAt,
            @JsonProperty("finished_at") String finishedAt,
            @JsonProperty("total_score") BigDecimal totalScore,
            @JsonProperty("result") String result,
            @JsonProperty("confidence") String confidence,
            @JsonProperty("cost_estimate_usd") BigDecimal costEstimateUsd,
            @JsonProperty("cost_actual_usd") BigDecimal costActualUsd,
            @JsonProperty("challenge_verified") Boolean challengeVerified,
            @JsonProperty("error_code") String errorCode,
            @JsonProperty("error_msg") String errorMsg,
            @JsonProperty("report_id") String reportId,
            @JsonProperty("attempt_count") Integer attemptCount,
            @JsonProperty("progress") Progress progress,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt,
            // 管理端列表附加（ADM-DET01，2026-09-23 新增）：供应商名与凭证别名，便于运营辨认；
            // 供应商侧接口不填（null），属**可选附加字段**，向后兼容。
            @JsonProperty("provider_name") String providerName,
            @JsonProperty("credential_alias") String credentialAlias) {
    }

    public record Result(
            @JsonProperty("probe_code") String probeCode,
            @JsonProperty("probe_name") String probeName,
            @JsonProperty("status") String status,
            @JsonProperty("score") BigDecimal score,
            @JsonProperty("weight_original") BigDecimal weightOriginal,
            @JsonProperty("weight_used") BigDecimal weightUsed,
            @JsonProperty("metrics") Map<String, Object> metrics,
            @JsonProperty("evidence") Object evidence,
            @JsonProperty("explanation") String explanation,
            @JsonProperty("detail") String detail,
            @JsonProperty("attempt_count") Integer attemptCount) {
    }

    /** 逐项结果响应（{@code {job_id,total,items[]}}）。 */
    public record ResultList(
            @JsonProperty("job_id") String jobId,
            @JsonProperty("total") int total,
            @JsonProperty("items") List<Result> items) {
    }
}
