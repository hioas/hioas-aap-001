package com.hioas.aap.sync;

import com.hioas.aap.common.DocNoGenerator;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 上架同步的**落库侧**（ADM-S07/S08/S09；D-SYNC-03）。
 *
 * <p>为什么单独成类（而不是写在 {@link SyncPublishService} 里）：
 * <ol>
 *   <li>该服务要做出站 HTTP（建渠道/写价/回读），**长事务 + 事务内 I/O** 是明确的坏味道
 *       （项目既有巡检项 A3：外部 I/O 调用点必须落在事务边界外）。把写集中到这里，
 *       服务层保持「无事务、只有 HTTP 编排」，两条纪律同时成立。</li>
 *   <li>「任务 + 操作明细」必须同一事务成功或一起失败，不允许出现「任务已 SYNCED 但没有明细」的半截状态
 *       （与 {@link SyncAttemptRecorder} 同一理由）。</li>
 * </ol>
 *
 * <p>id 生成沿用本项目 JdbcTemplate 写路径的做法（`nextval('seq_...')`，见 V12 迁移）。
 */
@Component
public class SyncPublishRecorder {

    private final JdbcTemplate jdbc;
    private final DocNoGenerator docNoGenerator;

    public SyncPublishRecorder(JdbcTemplate jdbc, DocNoGenerator docNoGenerator) {
        this.jdbc = jdbc;
        this.docNoGenerator = docNoGenerator;
    }

    /** ADM-S07：登记 one 个 new-api 端点（api_key 只以密文落库）。 */
    @Transactional
    public long insertEndpoint(String name, String baseUrl, String apiKeyCipher, boolean readonly, Long actor) {
        Long id = jdbc.queryForObject("select nextval('seq_newapi_endpoint')", Long.class);
        long endpointId = id == null ? 0L : id;
        jdbc.update("""
                insert into aap_newapi_endpoint (id, name, base_url, api_key_cipher, readonly, status,
                    created_at, updated_at, created_by, updated_by, deleted, version)
                values (?, ?, ?, ?, ?, 'ACTIVE', now(), now(), ?, ?, false, 0)
                """, endpointId, name, baseUrl, apiKeyCipher, readonly, actor, actor);
        return endpointId;
    }

    /**
     * ADM-S08：创建同步任务 + 待执行明细（**同一事务**）。
     *
     * @param operations 操作名列表（本闭环固定 `ADD_CHANNEL` 与 `WRITE_EXPR`）
     */
    @Transactional
    public long createTaskWithOperations(Long providerId, Long compilationId, Long bindingId, String taskType,
                                         String payloadJson, String idempotencyKey, String requestPayloadJson,
                                         List<String> operations, Long actor) {
        Long id = jdbc.queryForObject("select nextval('seq_sync_task')", Long.class);
        long taskId = id == null ? 0L : id;
        jdbc.update("""
                insert into aap_sync_task (id, task_no, binding_id, provider_id, compilation_id, task_type, status,
                    payload, idempotency_key, attempt_count, created_at, updated_at, created_by, updated_by,
                    deleted, version)
                values (?, ?, ?, ?, ?, ?, 'PENDING', ?::jsonb, ?, 0, now(), now(), ?, ?, false, 0)
                """, taskId, docNoGenerator.syncTaskNo(), bindingId, providerId, compilationId, taskType,
                payloadJson, idempotencyKey, actor, actor);
        int seq = 0;
        for (String operation : operations) {
            seq++;
            Long operationId = jdbc.queryForObject("select nextval('seq_sync_operation')", Long.class);
            jdbc.update("""
                    insert into aap_sync_operation (id, task_id, operation, request_payload, response_payload,
                        result, readback_equal, attempt_no, created_at, updated_at, created_by, updated_by,
                        deleted, version)
                    values (?, ?, ?, ?::jsonb, null, 'PENDING', null, ?, now(), now(), ?, ?, false, 0)
                    """, operationId, taskId, operation, requestPayloadJson, seq, actor, actor);
        }
        return taskId;
    }

    /** 建渠道成功后落绑定（首次插入；已存在同 provider + 同渠道名则复用该行）。 */
    @Transactional
    public long upsertBinding(Long providerId, Long credentialId, Long endpointId, Long channelId,
                              String channelName, String tag, String modelsJson, String readbackHash, Long actor) {
        List<Long> existing = jdbc.queryForList(
                "select id from aap_channel_binding where provider_id = ? and channel_name = ? and deleted = false"
                        + " order by id limit 1", Long.class, providerId, channelName);
        if (!existing.isEmpty()) {
            long bindingId = existing.get(0);
            jdbc.update("""
                    update aap_channel_binding
                       set channel_id = ?, endpoint_id = ?, models = ?::jsonb, status = 'SYNCED',
                           last_synced_at = now(), last_readback_hash = ?, updated_at = now(), updated_by = ?,
                           version = version + 1
                     where id = ? and deleted = false
                    """, channelId, endpointId, modelsJson, readbackHash, actor, bindingId);
            return bindingId;
        }
        Long id = jdbc.queryForObject("select nextval('seq_channel_binding')", Long.class);
        long bindingId = id == null ? 0L : id;
        jdbc.update("""
                insert into aap_channel_binding (id, provider_id, credential_id, endpoint_id, channel_id,
                    channel_name, tag, group_name, priority, weight, models, status, last_synced_at,
                    last_readback_hash, created_at, updated_at, created_by, updated_by, deleted, version)
                values (?, ?, ?, ?, ?, ?, ?, 'default', 0, 1, ?::jsonb, 'SYNCED', now(), ?, now(), now(),
                        ?, ?, false, 0)
                """, bindingId, providerId, credentialId, endpointId, channelId, channelName, tag, modelsJson,
                readbackHash, actor, actor);
        return bindingId;
    }

    /**
     * 任务终态 + 一次操作明细（同一事务；失败也必须留痕）。
     *
     * @param bindingId 非空时一并回写任务的绑定（建渠道成功后任务才与绑定关联）
     */
    @Transactional
    public void markTaskTerminal(long taskId, String status, Boolean readbackEqual, String lastError, int attempt,
                                 String operation, String result, String error, String responsePayloadJson,
                                 Long bindingId, Long actor) {
        jdbc.update("""
                update aap_sync_task
                   set status = ?, attempt_count = ?, last_error = ?, readback_equal = ?,
                       binding_id = coalesce(?, binding_id), updated_at = now(), updated_by = ?,
                       version = version + 1
                 where id = ? and deleted = false
                """, status, attempt, lastError, readbackEqual, bindingId, actor, taskId);
        Long operationId = jdbc.queryForObject("select nextval('seq_sync_operation')", Long.class);
        jdbc.update("""
                insert into aap_sync_operation (id, task_id, operation, request_payload, response_payload,
                    result, readback_equal, attempt_no, error, created_at, updated_at, created_by, updated_by,
                    deleted, version)
                values (?, ?, ?, null, ?::jsonb, ?, ?, ?, ?, now(), now(), ?, ?, false, 0)
                """, operationId, taskId, operation, responsePayloadJson, result, readbackEqual, attempt, error,
                actor, actor);
    }

    /** 上架成功：绑定 `ENABLED` + 供应商推进到生命周期末态 `PUBLISHED`（PRD 01 §4），并记 `sync_log`。 */
    @Transactional
    public void markPublished(long taskId, long bindingId, long channelId, Long providerId, String readbackHash,
                              String operation, String requestPayloadJson, String responsePayloadJson, Long actor) {
        jdbc.update("""
                update aap_channel_binding
                   set status = 'ENABLED', last_synced_at = now(), last_readback_hash = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false
                """, readbackHash, actor, bindingId);
        jdbc.update("""
                update aap_provider
                   set status = 'PUBLISHED', published_at = coalesce(published_at, now()),
                       updated_at = now(), version = version + 1
                 where id = ? and deleted = false
                """, providerId);
        Long logId = jdbc.queryForObject("select nextval('seq_sync_operation')", Long.class);
        jdbc.update("""
                insert into aap_sync_log (id, provider_id, channel_id, operation, idempotency_key,
                    request_payload, response_payload, result, readback_equal, attempt_no, created_at,
                    updated_at, created_by, updated_by, deleted, version)
                values (?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, 'SUCCESS', true, 1, now(), now(), ?, ?, false, 0)
                """, logId, providerId, channelId, operation,
                "aap-provider-" + providerId + "|" + operation + "|" + channelId,
                requestPayloadJson, responsePayloadJson, actor, actor);
        jdbc.update("""
                update aap_sync_task
                   set status = 'SYNCED', readback_equal = true, last_error = null, binding_id = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and deleted = false
                """, bindingId, actor, taskId);
    }

    /** 回读不一致：只记事实（不留假成功），库内状态保持调用前语义。 */
    @Transactional
    public void markReadbackMismatch(long taskId, Long bindingId, String readbackHash, String summary, Long actor) {
        if (bindingId != null) {
            jdbc.update("""
                    update aap_channel_binding
                       set last_readback_hash = ?, updated_at = now(), updated_by = ?, version = version + 1
                     where id = ? and deleted = false
                    """, readbackHash, actor, bindingId);
        }
        jdbc.update("""
                update aap_sync_task
                   set status = 'PARTIAL', readback_equal = false, last_error = ?,
                       binding_id = coalesce(?, binding_id), updated_at = now(), updated_by = ?,
                       version = version + 1
                 where id = ? and deleted = false
                """, summary, bindingId, actor, taskId);
    }
}
