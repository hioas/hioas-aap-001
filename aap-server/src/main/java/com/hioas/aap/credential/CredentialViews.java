package com.hioas.aap.credential;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * 凭证响应模型（契约：docs/backend/json-schema/models/credential-detail.schema.json /
 * credential-row.schema.json / credential-precheck.schema.json / precheck-result.schema.json）。
 *
 * <p>安全红线：任何凭证响应**都不得包含 api_key 明文**（只出 {@code api_key_mask}）。
 */
public final class CredentialViews {

    private CredentialViews() {
    }

    /** 凭证明细（客户端序号 4 表单回填 + 序号 9 报价主体选择）。 */
    @JsonInclude(JsonInclude.Include.ALWAYS)
    public record Detail(
            @JsonProperty("id") String id,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("alias") String alias,
            @JsonProperty("base_url") String baseUrl,
            @JsonProperty("api_key_mask") String apiKeyMask,
            @JsonProperty("api_key_masked") String apiKeyMasked,
            @JsonProperty("primary_flag") boolean primaryFlag,
            @JsonProperty("is_primary") boolean isPrimary,
            @JsonProperty("declared_vendor") String declaredVendor,
            @JsonProperty("declared_rpm") Integer declaredRpm,
            @JsonProperty("declared_tpm") Integer declaredTpm,
            @JsonProperty("declared_context_window") Integer declaredContextWindow,
            @JsonProperty("model_list") List<Map<String, Object>> modelList,
            @JsonProperty("env_tag") String envTag,
            @JsonProperty("status") String status,
            @JsonProperty("detection_status") String detectionStatus,
            @JsonProperty("latest_report_id") String latestReportId,
            @JsonProperty("precheck_passed") Boolean precheckPassed,
            @JsonProperty("precheck_at") String precheckAt,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt,
            @JsonProperty("version") Integer version) {
    }

    /** 凭证列表行（客户端序号 3 凭证列表：状态 chips + 报告入口 + 模型数）。 */
    public record Row(
            @JsonProperty("id") String id,
            @JsonProperty("alias") String alias,
            @JsonProperty("base_url") String baseUrl,
            @JsonProperty("api_key_mask") String apiKeyMask,
            @JsonProperty("model_list") List<Map<String, Object>> modelList,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("detection_status") String detectionStatus,
            @JsonProperty("latest_report_id") String latestReportId,
            @JsonProperty("status") String status,
            @JsonProperty("primary_flag") boolean primaryFlag) {
    }

    /** 预检记录。 */
    public record Precheck(
            @JsonProperty("id") String id,
            @JsonProperty("credential_id") String credentialId,
            @JsonProperty("status") String status,
            @JsonProperty("connectivity_ok") Boolean connectivityOk,
            @JsonProperty("auth_ok") Boolean authOk,
            @JsonProperty("models_ok") Boolean modelsOk,
            @JsonProperty("error_code") String errorCode,
            @JsonProperty("error_msg") String errorMsg,
            @JsonProperty("latency_ms") Integer latencyMs,
            @JsonProperty("checked_at") String checkedAt) {
    }

    /** 提交检测（预检通过 → 建任务入队）结果。 */
    public record PrecheckResult(
            @JsonProperty("job_id") String jobId,
            @JsonProperty("detection_job_id") String detectionJobId,
            @JsonProperty("job_no") String jobNo,
            @JsonProperty("precheck_status") String precheckStatus,
            @JsonProperty("status") String status,
            @JsonProperty("models") List<String> models) {
    }

    /** 明文读取结果（仅超管 + 二次验证；调用方负责审计）。 */
    public record Reveal(@JsonProperty("api_key") String apiKey, @JsonProperty("expire_at") String expireAt) {
    }
}
