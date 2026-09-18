package com.hioas.aap.support;

import com.hioas.aap.common.AuditContext;
import com.hioas.aap.common.JsonCodec;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * 审计写入（C8 只插不改）。
 *
 * <p>红线：{@code beforeValue/afterValue} 必须**已脱敏**（不得写入 api_key 明文、完整手机号）。
 * 调用方负责传脱敏后的值；本类只补 traceId 与操作者上下文。
 */
@Service
public class AuditService {

    private static final Logger log = LoggerFactory.getLogger(AuditService.class);

    private final AuditLogMapper auditLogMapper;

    public AuditService(AuditLogMapper auditLogMapper) {
        this.auditLogMapper = auditLogMapper;
    }

    public void record(AuditAction action, String targetType, Long targetId, String summary) {
        record(action, targetType, targetId, summary, null, null, "NORMAL");
    }

    public void record(AuditAction action, String targetType, Long targetId, String summary,
                       Map<String, Object> before, Map<String, Object> after, String riskLevel) {
        AuditLogEntity entity = new AuditLogEntity();
        entity.setTraceId(org.slf4j.MDC.get("traceId"));
        AuditContext.Actor actor = AuditContext.current().orElse(AuditContext.Actor.system());
        entity.setActorType(actor.type());
        entity.setActorId(actor.id());
        entity.setActorName(actor.name());
        entity.setActorIp(actor.ip());
        entity.setAction(action.code());
        entity.setTargetType(targetType);
        entity.setTargetId(targetId);
        entity.setSummary(summary);
        entity.setBeforeValue(before == null ? null : JsonCodec.toJson(before));
        entity.setAfterValue(after == null ? null : JsonCodec.toJson(after));
        entity.setResult("SUCCESS");
        entity.setRiskLevel(riskLevel);
        auditLogMapper.insert(entity);
        log.info("审计 action={} target={}#{} actor={} summary={}",
                action.code(), targetType, targetId, actor.id(), summary);
    }

    /** 审计动作字典（与 docs/backend/json-schema/models/audit-log.schema.json 的 enum 一致）。 */
    public enum AuditAction {
        CREDENTIAL_REVEAL, QUOTE_CREATE, QUOTE_SAVE, QUOTE_SUBMIT, QUOTE_WITHDRAW, QUOTE_VOID,
        QUOTE_APPROVE, QUOTE_REJECT, SYNC_WRITE_PRICE, PROVIDER_SUSPEND, PROVIDER_RESUME,
        CONTRACT_SIGN, PAYMENT_CONFIRM, DETECTION_RELEASE, PROFILE_UPDATE, AUTH_LOGIN,
        CONFIG_PUBLISH, SYNC_EXECUTE;

        public String code() {
            return name();
        }
    }
}
