package com.hioas.aap.support;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.support.NotificationViews.Item;
import com.hioas.aap.support.NotificationViews.ListResult;
import com.hioas.aap.support.NotificationViews.ReadResult;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * 通知下发 + 站内信读取（NTF-01/02）。
 *
 * <p>本期把通知**落库**（{@code aap_notification}）并由站内信接口读取；
 * 短信通道未接真实网关，{@code status=SENT} 表示「已入队待发」。内容一律**脱敏**
 * （不得出现完整手机号、api_key 明文）。
 *
 * <p><b>为什么读路径用 {@link JdbcTemplate} 而不是 ORM</b>（R15 踩坑 17/18 的固化结论）：
 * 列表需要 `count(*)`、`read_at is null` 条件计数与 `created_at desc, id desc` 稳定排序；
 * 已读是**条件 UPDATE + 读回**的状态迁移（`read_at is null` 才算一次真实迁移，重复调用影响 0 行
 * → 幂等、且不刷新首次已读时间）。写与随后的读回**同源**，响应体不会出现「说已读、库里没改」。
 */
@Service
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private static final String COLUMNS =
            "id, title, content, created_at, read_at, event_code, biz_type, biz_id, channel, category, status";

    private final NotificationMapper notificationMapper;
    private final JdbcTemplate jdbc;

    public NotificationService(NotificationMapper notificationMapper, JdbcTemplate jdbc) {
        this.notificationMapper = notificationMapper;
        this.jdbc = jdbc;
    }

    // ------------------------------------------------------------------ 下发

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

    // ------------------------------------------------------------------ NTF-01

    /**
     * 站内信列表（按收件人作用域隔离：供应商 = 本人 provider，管理端 = 本人账号）。
     *
     * @param unread 未读过滤：`true/false`（兼容 1/0、yes/no）；非法值 → E-1001（不静默忽略过滤条件）
     * @param category 分类过滤：`ORDER`/`SYSTEM`（大小写不敏感）
     */
    public ListResult list(String recipientType, Long recipientId, Integer page, Integer pageSize,
                           String unread, String category) {
        PageQuery query = PageQuery.of(page, pageSize);

        StringBuilder where = new StringBuilder(
                " where deleted = false and recipient_type = ? and recipient_id = ?");
        List<Object> args = new ArrayList<>(List.of(recipientType, recipientId));
        Boolean unreadOnly = parseUnread(unread);
        if (unreadOnly != null) {
            where.append(unreadOnly ? " and read_at is null" : " and read_at is not null");
        }
        if (category != null && !category.isBlank()) {
            where.append(" and upper(category) = upper(?)");
            args.add(category.trim());
        }

        Long total = jdbc.queryForObject("select count(*) from aap_notification" + where,
                Long.class, args.toArray());
        // 未读总数始终按「本人 + 未读」统计（徽标口径），不受 unread/category 过滤影响
        Long unreadCount = jdbc.queryForObject("""
                select count(*) from aap_notification
                 where deleted = false and recipient_type = ? and recipient_id = ? and read_at is null
                """, Long.class, recipientType, recipientId);

        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<Item> items = jdbc.query("select " + COLUMNS + " from aap_notification" + where
                        + " order by created_at desc, id desc limit ? offset ?", NotificationService::mapItem,
                pageArgs.toArray());
        return new ListResult(items, query.page(), query.pageSize(),
                total == null ? 0L : total, unreadCount == null ? 0L : unreadCount);
    }

    // ------------------------------------------------------------------ NTF-02

    /**
     * 标记已读（幂等）。不属于当前收件人的通知与不存在的通知**同回 403 E-1901**：
     * 清单把该端点错误码钉为 E-1901 —— 不区分「不存在 / 不是你的」，避免拿他人通知 id 探测存在性。
     */
    public ReadResult markRead(String recipientType, Long recipientId, Long notificationId) {
        List<OffsetDateTime> existing = jdbc.query("""
                select read_at from aap_notification
                 where id = ? and deleted = false and recipient_type = ? and recipient_id = ?
                """, (rs, rowNum) -> rs.getObject("read_at", OffsetDateTime.class),
                notificationId, recipientType, recipientId);
        if (existing.isEmpty()) {
            throw new ApiException(ErrorCode.E_1901, "站内信不存在或不属于当前账号");
        }
        if (existing.get(0) == null) {
            int affected = jdbc.update("""
                    update aap_notification
                       set read_at = now(), updated_at = now(), version = version + 1
                     where id = ? and recipient_type = ? and recipient_id = ? and read_at is null and deleted = false
                    """, notificationId, recipientType, recipientId);
            log.info("站内信标记已读 id={} affected={}", notificationId, affected);
        }
        // 读回库值：响应 read_at 就是落库值本身（不是内存时间）；重复调用不刷新首次已读时间
        OffsetDateTime readAt = jdbc.queryForObject(
                "select read_at from aap_notification where id = ?", OffsetDateTime.class, notificationId);
        return new ReadResult(String.valueOf(notificationId), rfc3339(readAt));
    }

    // ------------------------------------------------------------------ 内部

    private static Item mapItem(ResultSet rs, int rowNum) throws SQLException {
        OffsetDateTime readAt = rs.getObject("read_at", OffsetDateTime.class);
        String eventCode = rs.getString("event_code");
        String bizType = rs.getString("biz_type");
        Long bizId = rs.getObject("biz_id", Long.class);
        return new Item(
                String.valueOf(rs.getLong("id")),
                rs.getString("title"),
                rs.getString("content"),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)),
                rfc3339(readAt),
                readAt != null,
                readAt != null,
                eventCode,
                bizType,
                bizId == null ? null : String.valueOf(bizId),
                rs.getString("channel"),
                rs.getString("category"),
                kind(eventCode, bizType),
                rs.getString("status"));
    }

    /**
     * 图标类型派生（与客户端 `messages-model.ts#resolveMessageKind` 同一套规则，服务端优先给出）：
     * DETECT→detect、QUOTE|REJECT→quote、CONTRACT|SIGN→contract、BILL|PAYMENT|SETTLE→bill、其余 system。
     */
    private static String kind(String eventCode, String bizType) {
        String token = ((eventCode == null ? "" : eventCode) + " " + (bizType == null ? "" : bizType))
                .toUpperCase(Locale.ROOT);
        if (token.contains("DETECT")) {
            return "detect";
        }
        if (token.contains("QUOTE") || token.contains("REJECT")) {
            return "quote";
        }
        if (token.contains("CONTRACT") || token.contains("SIGN")) {
            return "contract";
        }
        if (token.contains("BILL") || token.contains("PAYMENT") || token.contains("SETTLE")) {
            return "bill";
        }
        return "system";
    }

    private static Boolean parseUnread(String unread) {
        if (unread == null || unread.isBlank()) {
            return null;
        }
        return switch (unread.trim().toLowerCase(Locale.ROOT)) {
            case "true", "1", "yes" -> Boolean.TRUE;
            case "false", "0", "no" -> Boolean.FALSE;
            default -> throw ApiException.field(ErrorCode.E_1001, "unread", "只接受 true/false，收到：" + unread);
        };
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }
}
