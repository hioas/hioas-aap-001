package com.hioas.aap.support;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * 站内信响应模型（契约真源：`docs/backend/json-schema/models/notification.schema.json`
 * 与 `notification-read.schema.json`，由 `tools/gen-backend-models.py` 从冻结清单生成）。
 *
 * <p>字段名以**客户端消费口径**为准（`aap-client/src/utils/messages-model.ts` 的 {@code MessageRaw}）：
 * {@code id/title/content/created_at/read_at/event_code/biz_type/biz_id/kind}；其中
 * <ul>
 *   <li>{@code kind}（detect/quote/contract/bill/system）服务端**优先给出**，客户端不再自行猜测图标；</li>
 *   <li>{@code read} 与 {@code is_read} 是同一语义的两个命名（客户端 `isUnread()` 两种都容忍），两处同值，
 *       不引入第二套已读语义；{@code read_at} 为真源（空即未读）。</li>
 * </ul>
 *
 * <p>雪花 ID 对外**一律 string**（避免 JS Number 精度丢失，同全项目口径）；时间 RFC3339 UTC；
 * 缺值回 null（前端渲染占位符），不用空串/0 冒充。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class NotificationViews {

    private NotificationViews() {
    }

    /** 单条站内信。 */
    public record Item(
            String id,
            String title,
            String content,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("read_at") String readAt,
            @JsonProperty("read") Boolean read,
            @JsonProperty("is_read") Boolean isRead,
            @JsonProperty("event_code") String eventCode,
            @JsonProperty("biz_type") String bizType,
            @JsonProperty("biz_id") String bizId,
            String channel,
            String category,
            String kind,
            String status) {
    }

    /**
     * NTF-01 响应体：{@code {items,page,pageSize,total,unread_count}}（清单 §1.7）。
     *
     * <p>{@code unread_count} 语义 = 当前收件人的**未读总数**，与 `unread/category` 过滤无关：
     * 徽标「N 条未读」不应随页面筛选跳动（客户端 messages-model 注释「接口未定义汇总字段」→ 本次补上）。
     */
    public record ListResult(
            List<Item> items,
            int page,
            int pageSize,
            long total,
            @JsonProperty("unread_count") long unreadCount) {
    }

    /** NTF-02 响应体：{@code {id,read_at}}（notification-read.schema.json）。 */
    public record ReadResult(
            String id,
            @JsonProperty("read_at") String readAt) {
    }
}
