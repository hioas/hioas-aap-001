package com.hioas.aap.support;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * 通知下发（事件 → 站内信/短信记录）。
 *
 * <p>本期把通知**落库**（{@code aap_notification}）并由站内信接口（NTF-01）读取；
 * 短信通道未接真实网关，{@code status=SENT} 表示「已入队待发」。内容一律**脱敏**
 * （不得出现完整手机号、api_key 明文）。
 */
@Service
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    private final NotificationMapper notificationMapper;

    public NotificationService(NotificationMapper notificationMapper) {
        this.notificationMapper = notificationMapper;
    }

    /** 发供应商站内信 + 短信（AC-21 检测通过通知）。 */
    public void notifyProvider(Long providerId, String eventCode, String title, String content,
                              String category, String bizType, Long bizId) {
        NotificationEntity entity = new NotificationEntity();
        entity.setRecipientType("PROVIDER");
        entity.setRecipientId(providerId);
        entity.setChannel("BOTH");
        entity.setEventCode(eventCode);
        entity.setTitle(title);
        entity.setContent(content);
        entity.setCategory(category);
        entity.setBizType(bizType);
        entity.setBizId(bizId);
        entity.setStatus("SENT");
        notificationMapper.insert(entity);
        log.info("通知已下发 recipient={}#{} event={} title={}", "PROVIDER", providerId, eventCode, title);
    }

    /** 标记已读（NTF-02 使用）。 */
    public NotificationEntity markRead(Long notificationId, Long recipientId) {
        NotificationEntity entity = notificationMapper.selectOneById(notificationId);
        if (entity == null || !entity.getRecipientId().equals(recipientId)) {
            return null;
        }
        if (entity.getReadAt() == null) {
            entity.setReadAt(OffsetDateTime.now(ZoneOffset.UTC));
            notificationMapper.update(entity);
        }
        return entity;
    }
}
