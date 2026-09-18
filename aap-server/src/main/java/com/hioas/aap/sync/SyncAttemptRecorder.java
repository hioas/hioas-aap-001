package com.hioas.aap.sync;

import java.time.OffsetDateTime;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * 重试尝试的落库（**独立事务** REQUIRES_NEW）。
 *
 * <p>为什么独立：ADM-S03 的失败路径要「先落库（任务状态 + 退避时间 + 一行 {@code aap_sync_operation}）
 * 再抛 {@code E-1501}/{@code E-1505}」。若与业务异常同一个事务，异常回滚会把失败痕迹一并抹掉——
 * 这正是 T03 验证码锁定、T05 预检记录踩过的同一个坑（tdd-state 踩坑 2 / R03）。
 *
 * <p>任务状态推进与操作明细必须在**同一事务**里成功或一起失败：不允许出现
 * 「任务已转 MANUAL 但没有对应操作明细」的半截状态。
 */
@Component
public class SyncAttemptRecorder {

    private final JdbcTemplate jdbc;

    public SyncAttemptRecorder(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** 落库一次重试尝试：推进任务状态 + 追加操作明细。 */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordAttempt(long taskId, int attempt, String status, OffsetDateTime nextRetryAt, String lastError,
                              Boolean readbackEqual, String operation, String result, String error,
                              String requestPayload, String responsePayload) {
        jdbc.update("""
                update aap_sync_task
                   set status = ?, attempt_count = ?, next_retry_at = ?, last_error = ?, readback_equal = ?,
                       updated_at = now(), version = version + 1
                 where id = ? and deleted = false
                """, status, attempt, nextRetryAt, lastError, readbackEqual, taskId);

        Long operationId = jdbc.queryForObject("select nextval('seq_sync_operation')", Long.class);
        jdbc.update("""
                insert into aap_sync_operation (id, task_id, operation, request_payload, response_payload, result,
                    readback_equal, attempt_no, error, created_at, updated_at, deleted, version)
                values (?, ?, ?, ?::jsonb, ?::jsonb, ?, ?, ?, ?, now(), now(), false, 0)
                """, operationId, taskId, operation, requestPayload, responsePayload, result, readbackEqual,
                attempt, error);
    }
}
