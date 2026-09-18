package com.hioas.aap.sync;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import tools.jackson.databind.JsonNode;

/**
 * new-api 同步运维的响应/请求模型（契约真源：`docs/backend/json-schema/models/`
 * 下 `sync-task.schema.json` / `sync-operation.schema.json` / `channel-binding.schema.json` /
 * `model-info.schema.json`，由 `tools/gen-backend-models.py` 从冻结清单生成）。
 *
 * <p>口径与既有视图一致：雪花 ID 对外一律 string（避免 JS 精度丢失）；时间 RFC3339 UTC；缺值回 null；
 * jsonb 列直接以 JSON 树返回（不再是字符串）。`task_id` / `binding_id` 是 `id` 的兼容别名
 * （模型里两个字段都在，两处同值，不引入第二套主键语义）。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class SyncViews {

    private SyncViews() {
    }

    /** 同步操作明细（读前写后三段式的每一次尝试）。 */
    public record SyncOperation(
            String id,
            String operation,
            @JsonProperty("request_payload") JsonNode requestPayload,
            @JsonProperty("response_payload") JsonNode responsePayload,
            String result,
            @JsonProperty("readback_equal") Boolean readbackEqual,
            @JsonProperty("attempt_no") Integer attemptNo,
            String error,
            @JsonProperty("created_at") String createdAt) {
    }

    /** 一份同步任务（ADM-S01 列表 / ADM-S02 详情 / ADM-S03 重试响应统一视图，含 operations）。 */
    public record SyncTask(
            String id,
            @JsonProperty("task_id") String taskId,
            @JsonProperty("task_no") String taskNo,
            @JsonProperty("binding_id") String bindingId,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("compilation_id") String compilationId,
            @JsonProperty("task_type") String taskType,
            String status,
            JsonNode payload,
            @JsonProperty("idempotency_key") String idempotencyKey,
            @JsonProperty("attempt_count") Integer attemptCount,
            @JsonProperty("next_retry_at") String nextRetryAt,
            @JsonProperty("last_error") String lastError,
            @JsonProperty("readback_equal") Boolean readbackEqual,
            List<SyncOperation> operations,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt) {
    }

    /** 渠道绑定（ADM-S04 列表 / ADM-S05 启停响应统一视图）。 */
    public record ChannelBinding(
            String id,
            @JsonProperty("binding_id") String bindingId,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("credential_id") String credentialId,
            @JsonProperty("endpoint_id") String endpointId,
            @JsonProperty("channel_id") Integer channelId,
            @JsonProperty("channel_name") String channelName,
            String tag,
            @JsonProperty("group_name") String groupName,
            Integer priority,
            Integer weight,
            List<String> models,
            String status,
            @JsonProperty("last_synced_at") String lastSyncedAt,
            @JsonProperty("last_readback_hash") String lastReadbackHash) {
    }

    /** 上游模型条目（ADM-S06）。 */
    public record ModelInfo(
            @JsonProperty("model_name") String modelName,
            String vendor,
            @JsonProperty("owned_by") String ownedBy,
            Boolean enabled) {
    }

    /** ADM-S06 响应体：`{models:[ModelInfo]}`（清单口径）。 */
    public record UpstreamModels(List<ModelInfo> models) {
    }

    /** ADM-S05 请求体（清单字段名：`target_status` = `ENABLED` | `DISABLED`）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BindingStatusRequest(@JsonProperty("target_status") String targetStatus) {
    }
}
