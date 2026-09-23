package com.hioas.aap.iam;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AdminUserViews.AdminUser;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.query.QueryWrapper;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 运营账号管理（**新增端点 ADM-AUTH02…05**）。
 *
 * <p>为什么需要（2026-09-23 运行态实测）：{@link AdminAuthService} 打通了管理端登录，但**建号只能靠 SQL**
 * —— 生产运维无法自助开通/停用运营账号。真源：13-管理端PRD（管理端账号与角色）+ 02-API接口清单 §2.5。
 *
 * <p>安全口径（每条对应一段实现）：
 * <ul>
 *   <li>**全部限 SUPER_ADMIN**（控制器 {@code @PreAuthorize("hasRole('SUPER_ADMIN')")}）——
 *       建号/停用是提权操作，不能让 BIZ_OPERATOR/TECH_OPS 自助扩权；</li>
 *   <li>{@code username} 唯一（DB 有 {@code uq_admin_username} 唯一索引，先查后插避免 500）；</li>
 *   <li>{@code phone_hash} 唯一（**DB 无唯一索引**，必须代码校验：短信登录按 phone_hash 查账号，
 *       重复会导致登录到谁不确定）；</li>
 *   <li>角色白名单：只允许 BIZ_OPERATOR / TECH_OPS / SUPER_ADMIN（避免把 SUPPLIER 写进管理端账号）；</li>
 *   <li>不能停用**自己**；不能停用**最后一个 ACTIVE 超管**（否则管理端彻底失联）；</li>
 *   <li>全动作写审计（建号 NORMAL、停用 HIGH），理由必填（停用）。</li>
 * </ul>
 *
 * <p>⚠️ 与 {@code SettlementService} 同一条经验：MyBatis mapper 的写入在**同一事务内对 JdbcTemplate 不可见**，
 * 故建号后不回读，响应直接用已插入实体拼装。
 */
@Service
public class AdminUserService {

    private static final Logger log = LoggerFactory.getLogger(AdminUserService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 管理端角色白名单（与 json-schema 的 Role enum 中管理端子集一致）。 */
    private static final Set<String> ROLES = Set.of("BIZ_OPERATOR", "TECH_OPS", "SUPER_ADMIN");

    private static final Pattern PHONE = Pattern.compile("^1[3-9]\\d{9}$");

    private static final String USERNAME_MAX = "64";

    /**
     * 密码列占位：本期内管理端**只走短信登录**（{@link AdminAuthService}），没有密码校验路径。
     * 落 {@code "!"} 而不是空串/随机值 —— 语义是「不可用口令」，与 /etc/shadow 的锁定标记同义，
     * 且 {@code password_hash} 列 not null 满足约束。
     */
    private static final String UNUSABLE_PASSWORD = "!";

    private static final String SELECT = """
            select id, username, display_name, role, status, phone_masked, last_login_at, created_at
              from aap_admin_user
            """;

    private final AdminUserMapper adminUserMapper;
    private final JdbcTemplate jdbc;
    private final CryptoService crypto;
    private final AuditService auditService;

    public AdminUserService(AdminUserMapper adminUserMapper, JdbcTemplate jdbc, CryptoService crypto,
                            AuditService auditService) {
        this.adminUserMapper = adminUserMapper;
        this.jdbc = jdbc;
        this.crypto = crypto;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-AUTH02

    /** ADM-AUTH02 运营账号列表（分页 + role/status/keyword 过滤；只出脱敏手机号）。 */
    public PageResult<AdminUser> list(Integer page, Integer pageSize, String role, String status, String keyword) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        if (role != null && !role.isBlank()) {
            where.append(" and role = ?");
            args.add(role.trim().toUpperCase());
        }
        if (status != null && !status.isBlank()) {
            where.append(" and status = ?");
            args.add(status.trim().toUpperCase());
        }
        if (keyword != null && !keyword.isBlank()) {
            where.append(" and (username ilike ? or display_name ilike ?)");
            args.add("%" + keyword.trim() + "%");
            args.add("%" + keyword.trim() + "%");
        }
        Long total = jdbc.queryForObject("select count(*) from aap_admin_user" + where, Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<AdminUser> items = jdbc.query(SELECT + where + " order by created_at desc, id desc limit ? offset ?",
                AdminUserService::map, pageArgs.toArray());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ ADM-AUTH03

    /** ADM-AUTH03 开运营账号（手机号即登录名；落 phone_hash/phone_masked/phone_cipher 三件套）。 */
    @Transactional
    public AdminUser create(AuthPrincipal principal, CreateCommand cmd) {
        String username = requireText(cmd.username(), "username", 64, "账号名");
        String role = cmd.role() == null ? null : cmd.role().trim().toUpperCase();
        if (role == null || !ROLES.contains(role)) {
            throw ApiException.field(ErrorCode.E_1001, "role",
                    "角色非法：" + cmd.role() + "（可选 " + String.join("/", ROLES) + "）");
        }
        String phone = cmd.phone() == null ? null : cmd.phone().trim();
        if (phone == null || !PHONE.matcher(phone).matches()) {
            throw ApiException.field(ErrorCode.E_1001, "phone", "手机号格式不正确");
        }
        String displayName = cmd.displayName() == null ? username : cmd.displayName().trim();
        if (displayName.length() > 64) {
            throw ApiException.field(ErrorCode.E_1001, "display_name", "显示名不超过 64 字");
        }

        Long sameName = jdbc.queryForObject("""
                select count(*) from aap_admin_user where deleted = false and lower(username) = lower(?)
                """, Long.class, username);
        if (sameName != null && sameName > 0) {
            throw ApiException.field(ErrorCode.E_1001, "username", "账号名已存在：" + username);
        }
        String phoneHash = crypto.sha256Hex(phone);
        Long samePhone = jdbc.queryForObject("""
                select count(*) from aap_admin_user where deleted = false and phone_hash = ?
                """, Long.class, phoneHash);
        if (samePhone != null && samePhone > 0) {
            // 不提示「是哪个账号」：避免用建号接口探测管理端手机号归属
            throw ApiException.field(ErrorCode.E_1001, "phone", "该手机号已被管理端账号占用");
        }

        AdminUserEntity entity = new AdminUserEntity();
        entity.setUsername(username);
        entity.setPasswordHash(UNUSABLE_PASSWORD);
        entity.setDisplayName(displayName);
        entity.setRole(role);
        entity.setStatus("ACTIVE");
        entity.setPhoneCipher(crypto.encrypt(phone));
        entity.setPhoneHash(phoneHash);
        entity.setPhoneMasked(crypto.maskPhone(phone));
        adminUserMapper.insert(entity);

        auditService.record(AuditService.AuditAction.ADMIN_USER_CREATE, "admin_user", entity.getId(),
                "开通运营账号 " + username + "（role=" + role + "，" + entity.getPhoneMasked() + "）",
                null, Map.of("role", role, "status", "ACTIVE"), "NORMAL");
        log.info("开通运营账号 account_id={} username={} role={} actor={}",
                entity.getId(), username, role, principal == null ? null : principal.accountId());
        // mapper 写入与本事务的 JdbcTemplate 不同连接（见类注释），故不回读
        return toView(entity);
    }

    // ------------------------------------------------------------------ ADM-AUTH04

    /** ADM-AUTH04 停用运营账号（必填理由；不能停用自己，也不能停用最后一个 ACTIVE 超管）。 */
    @Transactional
    public AdminUser suspend(AuthPrincipal principal, Long adminUserId, String reason) {
        if (reason == null || reason.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "reason", "停用必须填写理由");
        }
        String trimmed = reason.trim();
        Row row = requireActive(adminUserId, "停用");
        Long actor = principal == null ? null : principal.accountId();
        if (actor != null && actor.equals(adminUserId)) {
            throw new ApiException(ErrorCode.E_1601, "不可停用当前登录账号（会造成自己把自己踢出管理端）");
        }
        if ("SUPER_ADMIN".equals(row.role())) {
            Long others = jdbc.queryForObject("""
                    select count(*) from aap_admin_user
                     where deleted = false and status = 'ACTIVE' and role = 'SUPER_ADMIN' and id <> ?
                    """, Long.class, adminUserId);
            if (others == null || others == 0) {
                throw new ApiException(ErrorCode.E_1601, "这是最后一个启用中的超管，停用后管理端将无法登录");
            }
        }
        int updated = jdbc.update("""
                update aap_admin_user
                   set status = 'SUSPENDED', updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'ACTIVE' and deleted = false
                """, actor, adminUserId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "账号状态已变化，停用未生效，请刷新后重试");
        }
        auditService.record(AuditService.AuditAction.ADMIN_USER_SUSPEND, "admin_user", adminUserId,
                "停用运营账号 " + row.username() + "（理由：" + trimmed + "）",
                Map.of("status", "ACTIVE"), Map.of("status", "SUSPENDED"), "HIGH");
        log.info("停用运营账号 account_id={} actor={} reason={}", adminUserId, actor, trimmed);
        return loadOne(adminUserId);
    }

    // ------------------------------------------------------------------ ADM-AUTH05

    /** ADM-AUTH05 恢复运营账号（SUSPENDED → ACTIVE）。 */
    @Transactional
    public AdminUser resume(AuthPrincipal principal, Long adminUserId) {
        Row row = requireRow(adminUserId, "恢复", false);
        if (!"SUSPENDED".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "仅「已停用」账号可恢复（当前：" + row.status() + "）");
        }
        Long actor = principal == null ? null : principal.accountId();
        int updated = jdbc.update("""
                update aap_admin_user
                   set status = 'ACTIVE', updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'SUSPENDED' and deleted = false
                """, actor, adminUserId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "账号状态已变化，恢复未生效，请刷新后重试");
        }
        auditService.record(AuditService.AuditAction.ADMIN_USER_RESUME, "admin_user", adminUserId,
                "恢复运营账号 " + row.username(),
                Map.of("status", "SUSPENDED"), Map.of("status", "ACTIVE"), "HIGH");
        log.info("恢复运营账号 account_id={} actor={}", adminUserId, actor);
        return loadOne(adminUserId);
    }

    /** ADM-AUTH03 入参。 */
    public record CreateCommand(String username, String displayName, String role, String phone) {
    }

    // ------------------------------------------------------------------ 内部

    private record Row(Long id, String username, String role, String status) {
    }

    private Row requireActive(Long adminUserId, String action) {
        return requireRow(adminUserId, action, true);
    }

    private Row requireRow(Long adminUserId, String action, boolean mustBeActive) {
        List<Row> rows = adminUserId == null ? List.of() : jdbc.query("""
                select id, username, role, status from aap_admin_user where id = ? and deleted = false
                """, (rs, rowNum) -> new Row(rs.getObject("id", Long.class), rs.getString("username"),
                rs.getString("role"), rs.getString("status")), adminUserId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "运营账号不存在：" + adminUserId);
        }
        Row row = rows.get(0);
        if (mustBeActive && !"ACTIVE".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601, "账号非启用状态，无法" + action + "（当前：" + row.status() + "）");
        }
        return row;
    }

    private AdminUser loadOne(Long adminUserId) {
        List<AdminUser> rows = jdbc.query(SELECT + " where id = ? and deleted = false",
                AdminUserService::map, adminUserId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "运营账号不存在：" + adminUserId);
        }
        return rows.get(0);
    }

    private static AdminUser map(ResultSet rs, int rowNum) throws SQLException {
        String id = idText(rs.getObject("id", Long.class));
        return new AdminUser(id, id, rs.getString("username"), rs.getString("display_name"),
                rs.getString("role"), rs.getString("status"), rs.getString("phone_masked"),
                rfc3339(rs.getObject("last_login_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
    }

    private static AdminUser toView(AdminUserEntity e) {
        return new AdminUser(idText(e.getId()), idText(e.getId()), e.getUsername(), e.getDisplayName(),
                e.getRole(), e.getStatus(), e.getPhoneMasked(),
                rfc3339(e.getLastLoginAt()), rfc3339(e.getCreatedAt()));
    }

    private static String requireText(String value, String field, int max, String label) {
        String trimmed = value == null ? null : value.trim();
        if (trimmed == null || trimmed.isEmpty()) {
            throw ApiException.field(ErrorCode.E_1001, field, label + "必填");
        }
        if (trimmed.length() > max) {
            throw ApiException.field(ErrorCode.E_1001, field, label + "不超过 " + max + " 字");
        }
        return trimmed;
    }

    private static String idText(Long value) {
        return value == null ? null : String.valueOf(value);
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }
}
