package com.hioas.aap.report;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 报告响应模型（契约：docs/backend/json-schema/models/report.schema.json / report-summary.schema.json）。
 *
 * <p>响应是**超集**：既满足「多维度专业版」（`key_metrics`/`sections`/`findings`/`evidence`），
 * 也满足「未通过报告」页（`dims`/`detail`/`veto_note`）——两页各取所需，不各开一个端点。
 */
public final class ReportViews {

    private ReportViews() {
    }

    public record KeyMetric(@JsonProperty("key") String key,
                            @JsonProperty("label") String label,
                            @JsonProperty("value") String value,
                            @JsonProperty("unit") String unit,
                            @JsonProperty("sub") String sub,
                            @JsonProperty("tone") String tone) {
    }

    public record SectionItem(@JsonProperty("code") String code,
                              @JsonProperty("name") String name,
                              @JsonProperty("metric") String metric,
                              @JsonProperty("score") BigDecimal score,
                              @JsonProperty("status") String status,
                              @JsonProperty("value") String value,
                              @JsonProperty("explanation") String explanation) {
    }

    public record Section(@JsonProperty("code") String code,
                          @JsonProperty("name") String name,
                          @JsonProperty("avg") BigDecimal avg,
                          @JsonProperty("scored") Boolean scored,
                          @JsonProperty("note") String note,
                          @JsonProperty("items") List<SectionItem> items) {
    }

    public record Dim(@JsonProperty("code") String code,
                      @JsonProperty("name") String name,
                      @JsonProperty("score") BigDecimal score) {
    }

    public record Detail(@JsonProperty("code") String code,
                         @JsonProperty("title") String title,
                         @JsonProperty("score") BigDecimal score,
                         @JsonProperty("lines") List<String> lines) {
    }

    public record Finding(@JsonProperty("title") String title,
                          @JsonProperty("body") String body,
                          @JsonProperty("tone") String tone) {
    }

    public record Evidence(@JsonProperty("key") String key,
                           @JsonProperty("value") String value) {
    }

    public record Summary(
            @JsonProperty("id") String id,
            @JsonProperty("report_id") String reportId,
            @JsonProperty("report_no") String reportNo,
            @JsonProperty("result") String result,
            @JsonProperty("total_score") BigDecimal totalScore,
            @JsonProperty("confidence") String confidence,
            @JsonProperty("detected_at") String detectedAt,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("provider_code") String providerCode,
            @JsonProperty("credential_id") String credentialId,
            @JsonProperty("channel_name") String channelName) {
    }

    @JsonInclude(JsonInclude.Include.ALWAYS)
    public record Full(
            @JsonProperty("id") String id,
            @JsonProperty("report_id") String reportId,
            @JsonProperty("report_no") String reportNo,
            @JsonProperty("job_id") String jobId,
            @JsonProperty("credential_id") String credentialId,
            @JsonProperty("channel_name") String channelName,
            @JsonProperty("total_score") BigDecimal totalScore,
            @JsonProperty("result") String result,
            @JsonProperty("confidence") String confidence,
            @JsonProperty("confidence_label") String confidenceLabel,
            @JsonProperty("pass_count") Integer passCount,
            @JsonProperty("item_total") Integer itemTotal,
            @JsonProperty("unmeasurable_count") Integer unmeasurableCount,
            @JsonProperty("veto_triggered") Boolean vetoTriggered,
            @JsonProperty("verdict") String verdict,
            @JsonProperty("provider_name") String providerName,
            @JsonProperty("provider_code") String providerCode,
            @JsonProperty("api_key_masked") String apiKeyMasked,
            @JsonProperty("model_list") List<String> modelList,
            @JsonProperty("detected_at") String detectedAt,
            @JsonProperty("trigger_type") String triggerType,
            @JsonProperty("duration_text") String durationText,
            @JsonProperty("cost_estimate_usd") BigDecimal costEstimateUsd,
            @JsonProperty("cost_actual_usd") BigDecimal costActualUsd,
            @JsonProperty("key_metrics") List<KeyMetric> keyMetrics,
            @JsonProperty("sections") List<Section> sections,
            @JsonProperty("dims") List<Dim> dims,
            @JsonProperty("detail") Detail detail,
            @JsonProperty("findings") List<Finding> findings,
            @JsonProperty("evidence") List<Evidence> evidence,
            @JsonProperty("disclaimer") String disclaimer,
            @JsonProperty("veto_note") String vetoNote,
            @JsonProperty("weight_note") String weightNote,
            @JsonProperty("metrics") Map<String, Object> metrics) {
    }

    public record Export(@JsonProperty("url") String url,
                         @JsonProperty("file_url") String fileUrl,
                         @JsonProperty("file_name") String fileName,
                         @JsonProperty("expire_at") String expireAt) {
    }
}
