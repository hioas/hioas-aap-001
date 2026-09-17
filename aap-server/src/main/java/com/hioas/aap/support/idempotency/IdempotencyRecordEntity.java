package com.hioas.aap.support.idempotency;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 幂等记录（表 {@code aap_idempotency_record}，C11 幂等键全局唯一，24h 有效）。
 *
 * <p>存的是**首次响应的完整包体**：重放时原样返回，调用方（含前端）看到的是同一次结果，
 * 不会因为重试拿到"第二次执行"的副作用。
 */
@Table(value = "aap_idempotency_record",
        onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class IdempotencyRecordEntity extends BaseEntity {

    private String idempotencyKey;
    private String actor;
    private String endpoint;
    private String requestHash;
    private Integer responseStatus;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String responseBody;

    private String state;
    private OffsetDateTime expireAt;

    public String getIdempotencyKey() {
        return idempotencyKey;
    }

    public void setIdempotencyKey(String v) {
        this.idempotencyKey = v;
    }

    public String getActor() {
        return actor;
    }

    public void setActor(String v) {
        this.actor = v;
    }

    public String getEndpoint() {
        return endpoint;
    }

    public void setEndpoint(String v) {
        this.endpoint = v;
    }

    public String getRequestHash() {
        return requestHash;
    }

    public void setRequestHash(String v) {
        this.requestHash = v;
    }

    public Integer getResponseStatus() {
        return responseStatus;
    }

    public void setResponseStatus(Integer v) {
        this.responseStatus = v;
    }

    public String getResponseBody() {
        return responseBody;
    }

    public void setResponseBody(String v) {
        this.responseBody = v;
    }

    public String getState() {
        return state;
    }

    public void setState(String v) {
        this.state = v;
    }

    public OffsetDateTime getExpireAt() {
        return expireAt;
    }

    public void setExpireAt(OffsetDateTime v) {
        this.expireAt = v;
    }
}
