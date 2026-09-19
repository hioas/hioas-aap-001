package com.hioas.aap.contract;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.query.QueryWrapper;
import java.math.BigDecimal;
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
 * 合同（CON-01…04 供应商端 + ADM-CT01…03 管理端）。
 *
 * <p>真源：`02-API接口模型清单.md` §1.3/§2.5 + `01-ER数据模型.md` §4.7 + `03-任务与TDD计划.md` T11
 * （`CON-01…04`、`ADM-CT01…03`）。T10 已实现「审核通过自动生成合同（CREATED）」，本类负责签发与签署流转。
 *
 * <p>状态机（清单 §ContractStatus + ADM-CT02/03 的箭头注释）：
 * <pre>
 *   CREATED --ADM-CT02 issue--> PENDING_SIGN --CON-04 sign--> SUPPLIER_SIGNED --ADM-CT03 confirm-sign--> SIGNED
 * </pre>
 *
 * <p>设计取舍：
 * <ul>
 *   <li>**流转一律条件 UPDATE**（`where status = '期望值'`）：并发签发/重复签署只能有一方成功，失败方拿 409
 *       （E-1601/E-1701），不静默覆盖——同 {@code ReviewService}。</li>
 *   <li>**读写同源**：合同的写（条件 UPDATE）与读（显式 SQL）都走 {@link JdbcTemplate}；
 *       签署记录只插不改，写与读都走 {@link ContractSignMapper}。避免「同请求内 ORM 写 + JdbcTemplate 读」
 *       读到写之前状态的经典不一致（见 `.agents/state/aap-server-tdd-state.md` 坑 17）。</li>
 *   <li>**未签发不可下载/不可签署**：{@code file_id} 为空或状态 CREATED → 409 E-1701
 *       （E-1701 在统一错误码里的语义是「合同状态非法」，清单把该码挂在 CON-02/03/04 上）。</li>
 *   <li>**短信验证码只做格式校验**：合同签署短信通道未接线（清单要求 6 位数字），
 *       发送/校验接口落地前不臆造；偏差记 D-API-02（见 tdd-state.md）。</li>
 *   <li>**审计动作字典无 CONTRACT_ISSUE**：签发复用 {@code CONTRACT_SIGN}，摘要里写明动作，不新增枚举
 *       （字典由清单生成，新增须先改清单）；偏差记 D-API-03。</li>
 * </ul>
 */
@Service
public class ContractService {

    private static final Logger log = LoggerFactory.getLogger(ContractService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 签署方式（真源：contract-sign.schema.json 的 enum）。 */
    private static final Set<String> SIGN_METHODS = Set.of("SMS", "SEAL");

    private static final Pattern SMS_CODE = Pattern.compile("^\\d{6}$");

    /** 供应商可自行签署的状态：仅 PENDING_SIGN（CREATED 未签发、SUPPLIER_SIGNED/SIGNED 已签、VOIDED 作废）。 */
    private static final String PENDING_SIGN = "PENDING_SIGN";

    private static final String SELECT = """
            select c.id, c.contract_no, c.quote_id, c.provider_id, c.title, c.status, c.sign_channel,
                   c.cooperation_mode, c.valid_from, c.valid_to, c.settlement_cycle, c.platform_fee_rate,
                   c.currency, c.min_settlement_amount, c.sign_deadline, c.signer_name, c.signer_phone_mask,
                   c.sign_method, c.terms, c.file_id, c.signed_at, c.archived_at, c.created_at, c.updated_at,
                   c.version, q.quote_no,
                   coalesce(p.short_name, p.company_name, p.provider_no) as supplier_name,
                   f.original_name as file_name
              from aap_contract c
              left join aap_quote q on q.id = c.quote_id
              left join aap_provider p on p.id = c.provider_id
              left join aap_file_asset f on f.id = c.file_id and f.deleted = false
            """;

    private static final String SELECT_ROW = """
            select c.id, c.contract_no, c.provider_id, c.status, c.file_id, c.sign_method
              from aap_contract c
            """;

    private final JdbcTemplate jdbc;
    private final ContractSignMapper signMapper;
    private final AuditService auditService;

    public ContractService(JdbcTemplate jdbc, ContractSignMapper signMapper, AuditService auditService) {
        this.jdbc = jdbc;
        this.signMapper = signMapper;
        this.auditService = auditService;
    }

    /** ADM-CT02 签发入参（requests/contract-issue.schema.json）。 */
    public record IssueCommand(Long fileId, OffsetDateTime validFrom, OffsetDateTime validTo,
                               String cooperationMode, String settlementCycle, BigDecimal platformFeeRate,
                               String currency, BigDecimal minSettlementAmount, List<String> terms,
                               OffsetDateTime signDeadline) {
    }

    // ------------------------------------------------------------------ CON-01 / ADM-CT01

    /** CON-01 本供应商合同列表（status 可选过滤；分页）。 */
    public PageResult<ContractViews.Contract> listForProvider(AuthPrincipal principal, Integer page,
                                                             Integer pageSize, String status) {
        Long providerId = principal == null ? null : principal.providerId();
        if (providerId == null) {
            throw new ApiException(ErrorCode.E_1001, "当前账号未绑定供应商档案");
        }
        return page(" where c.deleted = false and c.provider_id = ?", providerId, page, pageSize, status);
    }

    /** ADM-CT01 管理端合同列表（跨供应商；status 可选过滤）。 */
    public PageResult<ContractViews.Contract> listForAdmin(Integer page, Integer pageSize, String status) {
        return page(" where c.deleted = false", null, page, pageSize, status);
    }

    private PageResult<ContractViews.Contract> page(String baseWhere, Long providerId, Integer page,
                                                    Integer pageSize, String status) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(baseWhere);
        List<Object> args = new ArrayList<>();
        if (providerId != null) {
            args.add(providerId);
        }
        if (status != null && !status.isBlank()) {
            where.append(" and c.status = ?");
            args.add(status.trim().toUpperCase());
        }
        Long total = jdbc.queryForObject("select count(*) from aap_contract c" + where,
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        // 排序列显式指定（含 id 兜底）：同一毫秒生成的合同顺序稳定，分页不漏不重
        List<ContractViews.Contract> items = jdbc.query(
                SELECT + where + " order by c.created_at desc, c.id desc limit ? offset ?",
                ContractService::mapContract, pageArgs.toArray());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ CON-02

    /** CON-02 合同详情（含 terms[] 与签署时间轴 records[]）。 */
    public ContractViews.Contract detailForProvider(AuthPrincipal principal, Long contractId) {
        requireOwned(principal, contractId);
        return loadOne(contractId);
    }

    // ------------------------------------------------------------------ CON-03

    /**
     * CON-03 合同文件。
     *
     * <p>未签发（CREATED）或没有文件资产 → 409 E-1701（合同状态非法，尚未产生可下载文件）。
     *
     * <p><b>补缺陷2 收口</b>：此前注释写「对象存储签名未接线：{@code url} 回文件资产的 {@code file_key}」——
     * 现在文件服务已接线（{@link com.hioas.aap.file.FileService}），所以这里返回**真实可下载**的地址
     * {@code /api/v1/files/{file_id}}，而不是把存储键当 URL 回给前端（前端拿 file_key 无从下载）。
     */
    public ContractViews.File file(AuthPrincipal principal, Long contractId) {
        Row row = requireOwned(principal, contractId);
        if (row.fileId() == null || "CREATED".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1701,
                    "合同尚未签发（当前：" + row.status() + "），暂无合同文件");
        }
        List<Map<String, Object>> assets = jdbc.queryForList("""
                select file_key, original_name from aap_file_asset where id = ? and deleted = false
                """, row.fileId());
        if (assets.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "合同文件不存在：" + row.fileId());
        }
        String originalName = (String) assets.get(0).get("original_name");
        String fileName = originalName == null || originalName.isBlank()
                ? "合同-" + row.contractNo() + ".pdf" : originalName;
        String url = "/api/v1/files/" + row.fileId();
        return new ContractViews.File(url, url, fileName,
                RFC3339.format(OffsetDateTime.now(ZoneOffset.UTC).plusHours(1)));
    }

    // ------------------------------------------------------------------ CON-04

    /** CON-04 供应商签署：PENDING_SIGN → SUPPLIER_SIGNED（落签署记录 + 审计留痕）。 */
    @Transactional
    public ContractViews.Contract signForProvider(AuthPrincipal principal, Long contractId,
                                                  String signMethod, String smsCode) {
        String method = signMethod == null || signMethod.isBlank() ? "SEAL" : signMethod.trim().toUpperCase();
        if (!SIGN_METHODS.contains(method)) {
            throw ApiException.field(ErrorCode.E_1001, "sign_method",
                    "签署方式非法：" + signMethod + "（可选 " + String.join("/", SIGN_METHODS) + "）");
        }
        if ("SMS".equals(method) && (smsCode == null || !SMS_CODE.matcher(smsCode.trim()).matches())) {
            throw ApiException.field(ErrorCode.E_1001, "smsCode", "短信签署需 6 位数字验证码");
        }
        Row row = requireOwned(principal, contractId);
        if ("CREATED".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1701, "合同尚未签发（当前：" + row.status() + "），不可签署");
        }
        if (!PENDING_SIGN.equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "合同状态非法流转（当前：" + row.status() + "），不可重复签署");
        }
        Map<String, Object> contact = providerContact(row.providerId());
        String signerName = contact == null ? null : (String) contact.get("contact_name");
        String phoneMask = contact == null ? null : (String) contact.get("contact_phone_mask");
        Long actor = actorId(principal);
        // 条件 UPDATE：并发签署时后来者影响 0 行 → 409（E1 乐观锁）
        int updated = jdbc.update("""
                update aap_contract
                   set status = 'SUPPLIER_SIGNED', sign_method = ?, signer_name = ?, signer_phone_mask = ?,
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'PENDING_SIGN' and deleted = false
                """, method, signerName, phoneMask, actor, contractId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "合同状态已变化，签署未生效，请刷新后重试");
        }
        insertSignRecord(contractId, "SUPPLIER", signerName, method, "pending");
        auditService.record(AuditService.AuditAction.CONTRACT_SIGN, "contract", contractId,
                "供应商签署合同 " + row.contractNo() + "（" + method + "）",
                Map.of("status", PENDING_SIGN), Map.of("status", "SUPPLIER_SIGNED"), "NORMAL");
        log.info("合同签署 contract_no={} method={} actor={}", row.contractNo(), method, actor);
        return loadOne(contractId);
    }

    // ------------------------------------------------------------------ ADM-CT02

    /**
     * ADM-CT02 签发：CREATED → PENDING_SIGN（补全文件/有效期/费率/条款/签署截止）。
     *
     * <p>校验：{@code file_id} 必填且必须是**真实存在**的文件资产；{@code platform_fee_rate} ∈ [0,1]；
     * 有效期必须 {@code valid_to > valid_from}。任一不满足 → 400 E-1001，且状态不变。
     */
    @Transactional
    public ContractViews.Contract issue(AuthPrincipal principal, Long contractId, IssueCommand command) {
        Row row = requireRow(contractId);
        IssueCommand cmd = command == null
                ? new IssueCommand(null, null, null, null, null, null, null, null, null, null) : command;
        if (cmd.fileId() == null) {
            throw ApiException.field(ErrorCode.E_1001, "file_id", "合同文件必填");
        }
        Long fileCount = jdbc.queryForObject("""
                select count(*) from aap_file_asset where id = ? and deleted = false
                """, Long.class, cmd.fileId());
        if (fileCount == null || fileCount == 0L) {
            throw ApiException.field(ErrorCode.E_1001, "file_id", "合同文件不存在：" + cmd.fileId());
        }
        if (cmd.platformFeeRate() != null
                && (cmd.platformFeeRate().compareTo(BigDecimal.ZERO) < 0
                    || cmd.platformFeeRate().compareTo(BigDecimal.ONE) > 0)) {
            throw ApiException.field(ErrorCode.E_1001, "platform_fee_rate",
                    "平台服务费率须在 [0,1] 之间：" + cmd.platformFeeRate());
        }
        if (cmd.validFrom() != null && cmd.validTo() != null && !cmd.validTo().isAfter(cmd.validFrom())) {
            throw ApiException.field(ErrorCode.E_1001, "valid_to", "合同有效期结束必须晚于开始");
        }
        if (!"CREATED".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "合同状态非法流转（当前：" + row.status() + "），不可重复签发");
        }
        String termsJson = cmd.terms() == null ? null : JsonCodec.toJson(cmd.terms());
        Long actor = actorId(principal);
        // 未提供的字段一律 coalesce 保持原值：签发是「补全」而不是「清空」——
        // 曾因 currency=? 传 null 撞 aap_contract.currency NOT NULL（HTTP 只见 500 E-2001）。
        int updated = jdbc.update("""
                update aap_contract
                   set status = 'PENDING_SIGN', file_id = ?,
                       valid_from = coalesce(?, valid_from), valid_to = coalesce(?, valid_to),
                       cooperation_mode = coalesce(?, cooperation_mode),
                       settlement_cycle = coalesce(?, settlement_cycle),
                       platform_fee_rate = coalesce(?, platform_fee_rate),
                       currency = coalesce(?, currency),
                       min_settlement_amount = coalesce(?, min_settlement_amount),
                       terms = coalesce(cast(? as jsonb), terms),
                       sign_deadline = coalesce(?, sign_deadline),
                       updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'CREATED' and deleted = false
                """, cmd.fileId(), cmd.validFrom(), cmd.validTo(), cmd.cooperationMode(), cmd.settlementCycle(),
                cmd.platformFeeRate(), cmd.currency(), cmd.minSettlementAmount(), termsJson, cmd.signDeadline(),
                actor, contractId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "合同状态已变化，签发未生效，请刷新后重试");
        }
        // 审计字典无 CONTRACT_ISSUE（由清单生成的枚举），签发复用 CONTRACT_SIGN 并在摘要里写明动作
        auditService.record(AuditService.AuditAction.CONTRACT_SIGN, "contract", contractId,
                "签发合同 " + row.contractNo() + "（CREATED→PENDING_SIGN）",
                Map.of("status", "CREATED"), Map.of("status", PENDING_SIGN), "NORMAL");
        log.info("合同签发 contract_no={} file_id={} actor={}", row.contractNo(), cmd.fileId(), actor);
        return loadOne(contractId);
    }

    // ------------------------------------------------------------------ ADM-CT03

    /** ADM-CT03 平台确认签署：SUPPLIER_SIGNED → SIGNED（落平台签署记录 + signed_at）。 */
    @Transactional
    public ContractViews.Contract confirmSign(AuthPrincipal principal, Long contractId) {
        Row row = requireRow(contractId);
        if (!"SUPPLIER_SIGNED".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "合同状态非法流转（当前：" + row.status() + "），供应商尚未签署或已确认");
        }
        Long actor = actorId(principal);
        String platformSigner = principal == null || principal.name() == null ? "平台" : principal.name();
        int updated = jdbc.update("""
                update aap_contract
                   set status = 'SIGNED', signed_at = now(), updated_at = now(), updated_by = ?,
                       version = version + 1
                 where id = ? and status = 'SUPPLIER_SIGNED' and deleted = false
                """, actor, contractId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "合同状态已变化，确认签署未生效，请刷新后重试");
        }
        String method = row.signMethod() == null ? "SEAL" : row.signMethod();
        insertSignRecord(contractId, "PLATFORM", platformSigner, method, "success");
        auditService.record(AuditService.AuditAction.CONTRACT_SIGN, "contract", contractId,
                "平台确认签署合同 " + row.contractNo() + "（SUPPLIER_SIGNED→SIGNED）",
                Map.of("status", "SUPPLIER_SIGNED"), Map.of("status", "SIGNED"), "NORMAL");
        log.info("合同确认签署 contract_no={} actor={}", row.contractNo(), actor);
        return loadOne(contractId);
    }

    // ------------------------------------------------------------------ 内部

    private record Row(Long id, String contractNo, Long providerId, String status, Long fileId,
                       String signMethod) {
    }

    private Row requireRow(Long contractId) {
        List<Row> rows = contractId == null ? List.of()
                : jdbc.query(SELECT_ROW + " where c.id = ? and c.deleted = false",
                        (rs, rowNum) -> new Row(rs.getObject("id", Long.class), rs.getString("contract_no"),
                                rs.getObject("provider_id", Long.class), rs.getString("status"),
                                rs.getObject("file_id", Long.class), rs.getString("sign_method")),
                        contractId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "合同不存在：" + contractId);
        }
        return rows.get(0);
    }

    /** 归属校验：不属于本供应商的合同按「不存在」（404 E-1406）处理，不泄露存在性。 */
    private Row requireOwned(AuthPrincipal principal, Long contractId) {
        Row row = requireRow(contractId);
        Long providerId = principal == null ? null : principal.providerId();
        if (providerId == null || !providerId.equals(row.providerId())) {
            throw new ApiException(ErrorCode.E_1406, "合同不存在：" + contractId);
        }
        return row;
    }

    private Map<String, Object> providerContact(Long providerId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                select contact_name, contact_phone_mask from aap_provider where id = ? and deleted = false
                """, providerId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private void insertSignRecord(Long contractId, String signerType, String signerName, String signMethod,
                                  String tone) {
        ContractSignEntity record = new ContractSignEntity();
        record.setContractId(contractId);
        record.setSignerType(signerType);
        record.setSignerName(signerName);
        record.setSignMethod(signMethod);
        record.setTone(tone);
        record.setSignedAt(OffsetDateTime.now(ZoneOffset.UTC));
        signMapper.insert(record);
    }

    private ContractViews.Contract loadOne(Long contractId) {
        List<ContractViews.Contract> rows = jdbc.query(SELECT + " where c.id = ? and c.deleted = false",
                ContractService::mapContract, contractId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "合同不存在：" + contractId);
        }
        ContractViews.Contract base = rows.get(0);
        return new ContractViews.Contract(base.id(), base.contractId(), base.contractNo(), base.quoteId(),
                base.quoteNo(), base.providerId(), base.title(), base.name(), base.contractName(), base.status(),
                base.signChannel(), base.cooperationMode(), base.validFrom(), base.validTo(),
                base.settlementCycle(), base.platformFeeRate(), base.currency(), base.minSettlementAmount(),
                base.signDeadline(), base.supplierName(), base.signerName(), base.signerPhoneMasked(),
                base.signMethod(), base.terms(), signRecords(contractId), base.fileId(), base.fileName(),
                base.signedAt(), base.archivedAt(), base.createdAt(), base.updatedAt(), base.version());
    }

    /** 签署时间轴（只插不改；写读都走 ORM，与 {@code JdbcTemplate} 侧的合同状态互不干扰）。 */
    private List<ContractViews.SignRecord> signRecords(Long contractId) {
        List<ContractSignEntity> rows = signMapper.selectListByQuery(QueryWrapper.create()
                .where("contract_id = ?", contractId)
                .orderBy("signed_at asc, id asc"));
        List<ContractViews.SignRecord> records = new ArrayList<>();
        for (ContractSignEntity row : rows) {
            String at = rfc3339(row.getSignedAt());
            String tone = row.getTone() == null
                    ? ("SUPPLIER".equals(row.getSignerType()) ? "pending" : "success") : row.getTone();
            records.add(new ContractViews.SignRecord(title(row.getSignerType()), at, tone, at,
                    row.getSignerType(), row.getSignMethod()));
        }
        return records;
    }

    private static String title(String signerType) {
        if ("SUPPLIER".equals(signerType)) {
            return "供应商已签署";
        }
        if ("PLATFORM".equals(signerType)) {
            return "平台已确认";
        }
        return "签署记录";
    }

    private static ContractViews.Contract mapContract(ResultSet rs, int rowNum) throws SQLException {
        String id = idText(rs.getObject("id", Long.class));
        String title = rs.getString("title");
        return new ContractViews.Contract(id, id, rs.getString("contract_no"),
                idText(rs.getObject("quote_id", Long.class)), rs.getString("quote_no"),
                idText(rs.getObject("provider_id", Long.class)), title, title, title,
                rs.getString("status"), rs.getString("sign_channel"), rs.getString("cooperation_mode"),
                rfc3339(rs.getObject("valid_from", OffsetDateTime.class)),
                rfc3339(rs.getObject("valid_to", OffsetDateTime.class)), rs.getString("settlement_cycle"),
                rs.getBigDecimal("platform_fee_rate"), rs.getString("currency"),
                rs.getBigDecimal("min_settlement_amount"),
                rfc3339(rs.getObject("sign_deadline", OffsetDateTime.class)), rs.getString("supplier_name"),
                rs.getString("signer_name"), rs.getString("signer_phone_mask"), rs.getString("sign_method"),
                terms(rs.getString("terms")), null, idText(rs.getObject("file_id", Long.class)),
                rs.getString("file_name"), rfc3339(rs.getObject("signed_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("archived_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("updated_at", OffsetDateTime.class)),
                rs.getObject("version", Integer.class));
    }

    private static List<String> terms(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return JsonCodec.toStringList(json);
        } catch (RuntimeException e) {
            log.warn("合同条款 JSON 解析失败，按无条款返回：{}", e.getMessage());
            return null;
        }
    }

    /** 雪花 ID 对外一律 string（避免 JS Number 精度丢失）；null 保持 null。 */
    private static String idText(Long value) {
        return value == null ? null : String.valueOf(value);
    }

    private static String rfc3339(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    private static Long actorId(AuthPrincipal principal) {
        return principal == null ? null : principal.accountId();
    }
}
