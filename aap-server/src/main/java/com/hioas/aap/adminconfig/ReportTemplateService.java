package com.hioas.aap.adminconfig;

import com.hioas.aap.adminconfig.ReportTemplateViews.Template;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.report.ReportService;
import com.hioas.aap.support.AuditService;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 报告模板配置（ADM-CFG06…10）。
 *
 * <p>真源：`02-API接口模型清单.md` §2.4 + `13-管理端PRD.md`（报告模板：Logo/标题/章节顺序/免责声明，
 * **保存时校验不得出现「保证为真模型」措辞**）+ `01-ER数据模型.md` §`aap_report_template`。
 *
 * <p>三条刻意的口径：
 * <ol>
 *   <li><b>状态机</b> {@code DRAFT → PUBLISHED}，被替代的活版 → {@code SUPERSEDED}：
 *       改与发布一律**条件 UPDATE**（`and status = 'DRAFT'` + 校验影响行数），
 *       并发/重复操作只能有一方成功 → 409 `E-1601`。</li>
 *   <li><b>活版唯一</b>：任一时刻全表只有一份 `PUBLISHED`（报告生成取该份，否则「用哪一份」不确定）。</li>
 *   <li><b>脱敏无关但留痕相关</b>：发布写 `published_at/published_by` 并落 `CONFIG_PUBLISH` 审计
 *       （R-47 配置发布属必录动作），审计可用 ADM-A01 检索。</li>
 * </ol>
 *
 * <p>偏差（记台账）：ER 的 `aap_report_template` 只有 `template_no`（UQ）与 `version_no`，
 * **没有「模板族」列**，因此「同族多版本」在当前表结构下不可表达 → 新建即新模板编号（`version_no=V1`），
 * 版本迭代需要新端点/新列（待拍板，见 tdd-state D-API-21）。
 */
@Service
public class ReportTemplateService {

    private static final Logger log = LoggerFactory.getLogger(ReportTemplateService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private static final int MAX_TITLE_LENGTH = 128;

    private static final String COLUMNS = """
            id, template_no, version_no, title, logo_file_id, section_order::text as section_order, disclaimer,
            status, published_at, created_at, updated_at
            """;

    private final JdbcTemplate jdbc;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;

    public ReportTemplateService(JdbcTemplate jdbc, DocNoGenerator docNoGenerator, AuditService auditService) {
        this.jdbc = jdbc;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-CFG06 / 08

    /** ADM-CFG06 模板列表（`status` 可选过滤，大小写不敏感）。 */
    public PageResult<Template> list(Integer page, Integer pageSize, String status) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> args = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and upper(status) = upper(?)");
            args.add(status.trim());
        }
        Long total = jdbc.queryForObject("select count(*) from aap_report_template" + where,
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<Template> items = jdbc.query("select " + COLUMNS + " from aap_report_template" + where
                        + " order by created_at desc, id desc limit ? offset ?", ReportTemplateService::map,
                pageArgs.toArray());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    /** ADM-CFG08 模板详情（不存在 → 404 `E-1406`）。 */
    public Template detail(Long id) {
        List<Template> rows = jdbc.query("select " + COLUMNS
                + " from aap_report_template where id = ? and deleted = false", ReportTemplateService::map, id);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "报告模板不存在");
        }
        return rows.get(0);
    }

    // ------------------------------------------------------------------ ADM-CFG07

    /** ADM-CFG07 创建（新模板编号 + `version_no=V1`，初始 `DRAFT`）。 */
    @Transactional
    public Template create(AuthPrincipal principal, String title, String logoFileId, List<String> sectionOrder,
                           String disclaimer) {
        validate(title, sectionOrder, disclaimer, true);
        Long actor = actorId(principal);
        Long id = jdbc.queryForObject("select nextval('seq_report_template')", Long.class);
        String templateNo = docNoGenerator.reportTemplateNo();
        jdbc.update("""
                insert into aap_report_template (id, template_no, version_no, title, logo_file_id, section_order,
                    disclaimer, status, created_at, updated_at, created_by, updated_by, deleted, version)
                values (?, ?, 'V1', ?, ?, ?::jsonb, ?, 'DRAFT', now(), now(), ?, ?, false, 0)
                """, id, templateNo, title.trim(), parseFileId(logoFileId), JsonCodec.toJson(sectionOrder),
                disclaimer, actor, actor);
        log.info("报告模板已创建 id={} no={} title={}", id, templateNo, title);
        return detail(id);
    }

    // ------------------------------------------------------------------ ADM-CFG09

    /**
     * ADM-CFG09 修改（仅 `DRAFT`）。未提供的字段按 **coalesce 语义保持原值**（省略=保持，不是清空），
     * 与合同签发接口的取舍一致（省略 `currency` 不得把列写成 null）。
     */
    @Transactional
    public Template update(AuthPrincipal principal, Long id, String title, String logoFileId,
                           List<String> sectionOrder, String disclaimer) {
        Template before = detail(id);
        String nextTitle = title == null || title.isBlank() ? before.title() : title;
        List<String> nextSections = sectionOrder == null ? before.sectionOrder() : sectionOrder;
        String nextDisclaimer = disclaimer == null ? before.disclaimer() : disclaimer;
        validate(nextTitle, nextSections, nextDisclaimer, false);

        Long actor = actorId(principal);
        int affected = jdbc.update("""
                update aap_report_template
                   set title = ?, logo_file_id = coalesce(?, logo_file_id), section_order = ?::jsonb,
                       disclaimer = ?, updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'DRAFT' and deleted = false
                """, nextTitle.trim(), parseFileId(logoFileId), JsonCodec.toJson(nextSections), nextDisclaimer,
                actor, id);
        if (affected != 1) {
            throw new ApiException(ErrorCode.E_1601,
                    "只有草稿状态的报告模板可以修改（当前：" + before.status() + "）");
        }
        return detail(id);
    }

    // ------------------------------------------------------------------ ADM-CFG10

    /** ADM-CFG10 发布（`DRAFT → PUBLISHED`；其余已发布模板置 `SUPERSEDED`；落 `CONFIG_PUBLISH` 审计）。 */
    @Transactional
    public Template publish(AuthPrincipal principal, Long id) {
        Template before = detail(id);
        Long actor = actorId(principal);
        int affected = jdbc.update("""
                update aap_report_template
                   set status = 'PUBLISHED', published_at = now(), published_by = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'DRAFT' and deleted = false
                """, actor, actor, id);
        if (affected != 1) {
            throw new ApiException(ErrorCode.E_1601,
                    "只有草稿状态的报告模板可以发布（当前：" + before.status() + "）");
        }
        // 活版唯一：旧活版置 SUPERSEDED（报告生成永远取唯一 PUBLISHED 的那份）
        int superseded = jdbc.update("""
                update aap_report_template
                   set status = 'SUPERSEDED', updated_at = now(), version = version + 1
                 where id <> ? and status = 'PUBLISHED' and deleted = false
                """, id);
        auditService.record(AuditService.AuditAction.CONFIG_PUBLISH, "report_template", id,
                "发布报告模板 " + before.templateNo() + "（" + before.title() + "），替代旧版 "
                        + superseded + " 份");
        return detail(id);
    }

    // ------------------------------------------------------------------ 内部

    private static void validate(String title, List<String> sectionOrder, String disclaimer, boolean requireAll) {
        if (requireAll && (title == null || title.isBlank())) {
            throw ApiException.field(ErrorCode.E_1001, "title", "标题必填");
        }
        if (title != null && title.length() > MAX_TITLE_LENGTH) {
            throw ApiException.field(ErrorCode.E_1001, "title", "标题长度不得超过 " + MAX_TITLE_LENGTH + " 字符");
        }
        if (sectionOrder == null || sectionOrder.isEmpty()) {
            throw ApiException.field(ErrorCode.E_1001, "section_order", "章节顺序必填且不得为空数组");
        }
        Set<String> allowed = ReportService.sectionCodes();
        Set<String> seen = new LinkedHashSet<>();
        for (String code : sectionOrder) {
            if (code == null || !allowed.contains(code.trim())) {
                throw ApiException.field(ErrorCode.E_1001, "section_order",
                        "非法章节：" + code + "（只允许 " + allowed + "）");
            }
            if (!seen.add(code.trim())) {
                throw ApiException.field(ErrorCode.E_1001, "section_order", "章节重复：" + code);
            }
        }
        // R-26 措辞红线：字符串级判定（禁用词出现在否定句里同样失败）
        List<String> violations = ReportTemplateWording.violations(disclaimer);
        if (!violations.isEmpty()) {
            throw ApiException.field(ErrorCode.E_1001, "disclaimer",
                    "免责声明不得出现保证性措辞：" + String.join("、", violations));
        }
    }

    /** 只接受雪花 ID 的十进制字符串/数字；空 → null。 */
    private static Long parseFileId(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "logo_file_id", "不是合法的雪花 ID：" + value);
        }
    }

    private static Template map(ResultSet rs, int rowNum) throws SQLException {
        Long id = rs.getLong("id");
        Long logoFileId = rs.getObject("logo_file_id", Long.class);
        return new Template(
                String.valueOf(id),
                String.valueOf(id),
                rs.getString("template_no"),
                rs.getString("version_no"),
                rs.getString("title"),
                logoFileId == null ? null : String.valueOf(logoFileId),
                JsonCodec.toStringList(rs.getString("section_order")),
                rs.getString("disclaimer"),
                rs.getString("status"),
                rfc3339(rs.getObject("published_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("updated_at", OffsetDateTime.class)));
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    private static Long actorId(AuthPrincipal principal) {
        return principal == null ? null : principal.accountId();
    }
}
