package com.hioas.aap.adminconfig;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import tools.jackson.databind.JsonNode;

/**
 * 检测配置响应/请求模型（契约真源：`docs/backend/json-schema/models/detection-config.schema.json`
 * 与 `requests/detection-config-save.schema.json`，由 `tools/gen-backend-models.py` 从冻结清单生成）。
 *
 * <p>口径与报告模板一致：雪花 ID 对外一律 string（避免 JS 精度丢失）；时间 RFC3339 UTC；缺值回 null。
 * {@code config_id} 是 {@code id} 的兼容别名（模型里两个字段都在）—— 两处同值，不引入第二套主键语义。
 * {@code veto_rule} / {@code params} 是 jsonb 列，直接以 JSON 树返回（不再是字符串）。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class DetectionConfigViews {

    private DetectionConfigViews() {
    }

    /** 单个检测项（D1–D8 的启停/权重/超时/参数）。 */
    public record Probe(
            @JsonProperty("probe_code") String probeCode,
            @JsonProperty("probe_name") String probeName,
            Boolean enabled,
            Double weight,
            @JsonProperty("timeout_seconds") Integer timeoutSeconds,
            JsonNode params) {
    }

    /** 一份检测配置版本（ADM-CFG01…05 的统一视图）。 */
    public record DetectionConfig(
            String id,
            @JsonProperty("config_id") String configId,
            @JsonProperty("version_no") String versionNo,
            String name,
            @JsonProperty("pass_score") Integer passScore,
            @JsonProperty("veto_rule") JsonNode vetoRule,
            String status,
            List<Probe> probes,
            @JsonProperty("published_at") String publishedAt,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt) {
    }

    /** ADM-CFG02/04 请求体（清单字段名：`name` `pass_score` `veto_rule` `status` `probes[]`）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record SaveRequest(
            String name,
            @JsonProperty("pass_score") Integer passScore,
            @JsonProperty("veto_rule") JsonNode vetoRule,
            String status,
            List<ProbeRequest> probes) {
    }

    /** 请求体里的检测项；`probe_name`/`timeout_seconds` 缺省时由服务端按 ER 规则补全。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record ProbeRequest(
            @JsonProperty("probe_code") String probeCode,
            @JsonProperty("probe_name") String probeName,
            Boolean enabled,
            Double weight,
            @JsonProperty("timeout_seconds") Integer timeoutSeconds,
            JsonNode params) {
    }
}
