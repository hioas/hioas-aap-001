package com.hioas.aap.support;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import tools.jackson.databind.JsonNode;

/**
 * 审计日志响应模型（契约真源：`docs/backend/json-schema/models/audit-log.schema.json`）。
 *
 * <p>本视图是 `aap_audit_log`（append-only，C8）的**只读投影**：字段与列 1:1，
 * {@code before_value/after_value} 由 jsonb 还原为对象（写入侧已脱敏，红线见 {@link AuditService}）。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class AuditLogViews {

    private AuditLogViews() {
    }

    /** 单条审计：雪花 ID 对外 string；时间 RFC3339 UTC。 */
    public record Row(
            String id,
            @JsonProperty("trace_id") String traceId,
            @JsonProperty("actor_type") String actorType,
            @JsonProperty("actor_id") String actorId,
            @JsonProperty("actor_name") String actorName,
            @JsonProperty("actor_ip") String actorIp,
            @JsonProperty("user_agent") String userAgent,
            String action,
            @JsonProperty("target_type") String targetType,
            @JsonProperty("target_id") String targetId,
            String summary,
            @JsonProperty("before_value") JsonNode beforeValue,
            @JsonProperty("after_value") JsonNode afterValue,
            String result,
            @JsonProperty("risk_level") String riskLevel,
            @JsonProperty("created_at") String createdAt) {
    }

    /** ADM-A01 响应体（分页结构：{@code items/page/pageSize/total}）。 */
    public record Page(List<Row> items, int page, int pageSize, long total) {
    }
}
