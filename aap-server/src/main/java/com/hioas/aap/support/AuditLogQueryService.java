package com.hioas.aap.support;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.support.AuditLogViews.Page;
import com.hioas.aap.support.AuditLogViews.Row;
import com.hioas.aap.support.AuditService.AuditAction;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * 审计日志查询（ADM-A01）。
 *
 * <p>与 {@link AuditService}（只写）分离：审计表 append-only（C8），读侧**不得**混入写逻辑，
 * 否则「审计不可篡改」这条不变量会随功能迭代被侵蚀。
 *
 * <p>过滤维度与清单 §2.4 一致：`actorType`、`action`（**必须命中审计字典**，否则 E-1001 ——
 * 拼错的动作名静默回空集会让技术运营误判「没有该操作」）、`traceId`、时间窗半开 `[from, to)`。
 */
@Service
public class AuditLogQueryService {

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 动作字典（真源 = {@link AuditAction} 枚举，与 audit-log.schema.json 的 enum 同源）。 */
    private static final Set<String> KNOWN_ACTIONS = Arrays.stream(AuditAction.values())
            .map(Enum::name)
            .collect(Collectors.toUnmodifiableSet());

    private final JdbcTemplate jdbc;

    public AuditLogQueryService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Page list(Integer page, Integer pageSize, String actorType, String action, String traceId,
                     String from, String to) {
        PageQuery query = PageQuery.of(page, pageSize);

        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        if (actorType != null && !actorType.isBlank()) {
            where.append(" and upper(actor_type) = upper(?)");
            args.add(actorType.trim());
        }
        if (action != null && !action.isBlank()) {
            String code = action.trim().toUpperCase(Locale.ROOT);
            if (!KNOWN_ACTIONS.contains(code)) {
                throw ApiException.field(ErrorCode.E_1001, "action", "不是合法的审计动作：" + action);
            }
            where.append(" and action = ?");
            args.add(code);
        }
        if (traceId != null && !traceId.isBlank()) {
            where.append(" and trace_id = ?");
            args.add(traceId.trim());
        }
        OffsetDateTime fromAt = parseInstant(from, "from");
        if (fromAt != null) {
            where.append(" and created_at >= ?");
            args.add(fromAt);
        }
        OffsetDateTime toAt = parseInstant(to, "to");
        if (toAt != null) {
            where.append(" and created_at < ?");
            args.add(toAt);
        }

        Long total = jdbc.queryForObject("select count(*) from aap_audit_log" + where,
                Long.class, args.toArray());

        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<Row> items = jdbc.query("""
                select id, trace_id, actor_type, actor_id, actor_name, actor_ip, user_agent, action, target_type,
                       target_id, summary, before_value::text as before_value, after_value::text as after_value,
                       result, risk_level, created_at
                  from aap_audit_log
                """ + where + " order by created_at desc, id desc limit ? offset ?",
                AuditLogQueryService::mapRow, pageArgs.toArray());

        return new Page(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    private static Row mapRow(ResultSet rs, int rowNum) throws SQLException {
        Long actorId = rs.getObject("actor_id", Long.class);
        Long targetId = rs.getObject("target_id", Long.class);
        return new Row(
                String.valueOf(rs.getLong("id")),
                rs.getString("trace_id"),
                rs.getString("actor_type"),
                actorId == null ? null : String.valueOf(actorId),
                rs.getString("actor_name"),
                rs.getString("actor_ip"),
                rs.getString("user_agent"),
                rs.getString("action"),
                rs.getString("target_type"),
                targetId == null ? null : String.valueOf(targetId),
                rs.getString("summary"),
                JsonCodec.readTree(rs.getString("before_value")),
                JsonCodec.readTree(rs.getString("after_value")),
                rs.getString("result"),
                rs.getString("risk_level"),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
    }

    /** 时间戳只接受 RFC3339/ISO-8601；无法解析 → E-1001（不静默忽略时间窗）。 */
    private static OffsetDateTime parseInstant(String value, String field) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String text = value.trim();
        try {
            return OffsetDateTime.parse(text).withOffsetSameInstant(ZoneOffset.UTC);
        } catch (DateTimeParseException ignored) {
            try {
                return Instant.parse(text).atOffset(ZoneOffset.UTC);
            } catch (DateTimeParseException e) {
                throw ApiException.field(ErrorCode.E_1001, field, "不是合法的 RFC3339 时间：" + value);
            }
        }
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }
}
