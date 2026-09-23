package com.hioas.aap.settlement;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.settlement.PaymentViews.Payment;
import com.hioas.aap.settlement.PaymentViews.PaymentPage;
import com.hioas.aap.settlement.PaymentViews.Statement;
import com.hioas.aap.support.AuditService;
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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 打款与结算（PAY-01 供应商端 + ADM-PAY01…03 管理端）。
 *
 * <p>真源：`02-API接口模型清单.md` §1.3/§2.5 + `01-ER数据模型.md` §4.7 + `03-任务与TDD计划.md` T11。
 *
 * <p>设计取舍：
 * <ul>
 *   <li>**打款仅记录（R-42）**：平台不做资金流转。确认打款只推进
 *       {@code PAYMENT_RECORDED → CONFIRMED} 并留痕（确认人/时间 + 审计），不产生资金动作。</li>
 *   <li>**AC-40 未签署禁打款**：确认前校验合同状态必须为 {@code SIGNED}，否则 409 E-1701，
 *       且打款状态与确认人一律不变（先校验、后条件 UPDATE，失败不留半成品）。</li>
 *   <li>**读写同源**：状态流转与读查询都走 {@link JdbcTemplate}，顺带拿到真实影响行数做并发判定。</li>
 *   <li>**钱包三项为约定口径**（清单标注无 PRD 依据）：见 {@link PaymentViews.PaymentPage}，三态互斥不重复计数。</li>
 * </ul>
 */
@Service
public class SettlementService {

    private static final Logger log = LoggerFactory.getLogger(SettlementService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private static final String PAYMENT_SELECT = """
            select p.id, p.provider_id, p.contract_id, p.statement_id, p.amount, p.currency, p.status,
                   p.voucher_file_id, p.paid_at, p.confirmed_by, p.confirmed_at, p.remark, p.created_at,
                   c.contract_no
              from aap_payment_record p
              left join aap_contract c on c.id = p.contract_id
            """;

    private static final String CONFIRM_SQL = """
            update aap_payment_record
               set status = 'CONFIRMED', confirmed_by = ?, confirmed_at = now(),
                   updated_at = now(), updated_by = ?, version = version + 1
             where id = ? and status = 'PAYMENT_RECORDED' and deleted = false
            """;

    /** 作废：状态 + 理由并入 remark，条件 UPDATE 拿到真实影响行数做并发判定。 */
    private static final String VOID_SQL = """
            update aap_payment_record
               set status = 'VOID',
                   remark = case when remark is null or remark = '' then '作废理由：' || ?
                                 else remark || ' | 作废理由：' || ? end,
                   updated_at = now(), updated_by = ?, version = version + 1
             where id = ? and status in ('PAYMENT_RECORDED','CONFIRMED') and deleted = false
            """;

    /** 可作废状态（PRD 10 §4.3：VOID 作废后重录）。 */
    private static final Set<String> VOIDABLE = Set.of("PAYMENT_RECORDED", "CONFIRMED");

    private final JdbcTemplate jdbc;
    private final AuditService auditService;
    /** 记录打款走 Mapper：需要雪花 ID 与审计字段（created_by）由监听器自动落。 */
    private final PaymentRecordMapper paymentRecordMapper;

    public SettlementService(JdbcTemplate jdbc, AuditService auditService,
                             PaymentRecordMapper paymentRecordMapper) {
        this.jdbc = jdbc;
        this.auditService = auditService;
        this.paymentRecordMapper = paymentRecordMapper;
    }

    // ------------------------------------------------------------------ PAY-01

    /** PAY-01 本供应商打款列表（分页 + 钱包三项）。 */
    public PaymentPage listForProvider(AuthPrincipal principal, Integer page, Integer pageSize) {
        Long providerId = principal == null ? null : principal.providerId();
        if (providerId == null) {
            throw new ApiException(ErrorCode.E_1001, "当前账号未绑定供应商档案");
        }
        PageQuery query = PageQuery.of(page, pageSize);
        Long total = jdbc.queryForObject("""
                select count(*) from aap_payment_record where deleted = false and provider_id = ?
                """, Long.class, providerId);
        List<Payment> items = jdbc.query(PAYMENT_SELECT + """
                 where p.deleted = false and p.provider_id = ?
                 order by p.created_at desc, p.id desc limit ? offset ?
                """, SettlementService::mapPayment, providerId, query.pageSize(), query.offset());
        return new PaymentPage(items, query.page(), query.pageSize(), total == null ? 0L : total,
                wallet(providerId, "PAYMENT_RECORDED"), wallet(providerId, "UNSETTLED"),
                wallet(providerId, "CONFIRMED"));
    }

    /** 单状态打款金额合计（三态互斥口径，见 {@link PaymentViews.PaymentPage}）。 */
    private BigDecimal wallet(Long providerId, String status) {
        BigDecimal sum = jdbc.queryForObject("""
                select coalesce(sum(amount), 0) from aap_payment_record
                 where deleted = false and provider_id = ? and status = ?
                """, BigDecimal.class, providerId, status);
        return sum == null ? BigDecimal.ZERO : sum;
    }

    // ------------------------------------------------------------------ ADM-PAY01

    /** ADM-PAY01 管理端打款列表（跨供应商；status 可选过滤）。 */
    public PageResult<Payment> listForAdmin(Integer page, Integer pageSize, String status) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where p.deleted = false");
        List<Object> args = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and p.status = ?");
            args.add(status.trim().toUpperCase());
        }
        Long total = jdbc.queryForObject("select count(*) from aap_payment_record p" + where,
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        List<Payment> items = jdbc.query(PAYMENT_SELECT + where
                + " order by p.created_at desc, p.id desc limit ? offset ?",
                SettlementService::mapPayment, pageArgs.toArray());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ ADM-PAY02

    /**
     * ADM-PAY02 确认打款：PAYMENT_RECORDED → CONFIRMED。
     *
     * <p>AC-40：合同必须已 {@code SIGNED}，否则 409 E-1701（未签署禁打款），打款状态不变。
     */
    @Transactional
    public Payment confirm(AuthPrincipal principal, Long paymentId) {
        Row row = requireRow(paymentId);
        if (!"PAYMENT_RECORDED".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "打款状态非法流转（当前：" + row.status() + "），仅「已打款待确认」可确认");
        }
        String contractStatus = row.contractId() == null ? null : jdbc.queryForObject("""
                select status from aap_contract where id = ? and deleted = false
                """, String.class, row.contractId());
        if (!"SIGNED".equals(contractStatus)) {
            throw new ApiException(ErrorCode.E_1701,
                    "合同未签署（关联合同状态：" + (contractStatus == null ? "无合同" : contractStatus)
                            + "），禁止确认打款");
        }
        Long actor = actorId(principal);
        int updated = jdbc.update(CONFIRM_SQL, actor, actor, paymentId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "打款状态已变化，确认未生效，请刷新后重试");
        }
        BigDecimal amount = row.amount() == null ? BigDecimal.ZERO : row.amount();
        auditService.record(AuditService.AuditAction.PAYMENT_CONFIRM, "payment", paymentId,
                "确认打款（金额 " + amount.toPlainString() + " " + (row.currency() == null ? "USD" : row.currency())
                        + "，合同 " + (row.contractNo() == null ? row.contractId() : row.contractNo()) + "）",
                Map.of("status", "PAYMENT_RECORDED"), Map.of("status", "CONFIRMED"), "NORMAL");
        log.info("确认打款 payment_id={} amount={} actor={}", paymentId, amount.toPlainString(), actor);
        return loadOne(paymentId);
    }

    // ------------------------------------------------------------------ ADM-PAY04

    /**
     * ADM-PAY04 记录打款：{@code UNSETTLED → PAYMENT_RECORDED}（线下打款留痕，**不产生资金流水**，PRD 10 R-42）。
     *
     * <p>为什么必须有这个端点（2026-09-23 运行态实测）：{@code aap_payment_record} 在本仓库**没有任何 insert 代码路径**，
     * 于是 {@link #confirm} 永远没有可确认对象（实测 {@code /admin/payments} total=0）——合同签完后链路直接断开。
     * PRD 10 §4.3 的真源口径是：**运营商务线下打款后"记录打款"，上传凭证截图，再确认**。
     *
     * <p>校验（PRD 10 §5.3 + AC-40）：
     * <ul>
     *   <li>合同必须存在且为 {@code SIGNED}（未签署禁打款，409 E-1601）；</li>
     *   <li>C4：金额 &gt; 0，币种必与合同一致（不传则取合同币种）；</li>
     *   <li>C5：凭证文件必填且必须存在于 {@code aap_file_asset}；</li>
     *   <li>同一合同不允许存在第二笔生效中的打款（须先作废再重录，见 {@link #voidPayment}）。</li>
     * </ul>
     */
    @Transactional
    public Payment recordPayment(AuthPrincipal principal, RecordCommand cmd) {
        if (cmd.contractId() == null) {
            throw ApiException.field(ErrorCode.E_1001, "contract_id", "合同必填");
        }
        ContractRow contract = requireContract(cmd.contractId());
        if (!"SIGNED".equals(contract.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "合同未签署（当前：" + contract.status() + "），禁止记录打款");
        }
        if (cmd.amount() == null || cmd.amount().signum() <= 0) {
            throw ApiException.field(ErrorCode.E_1001, "amount", "打款金额必须大于 0（C4）");
        }
        String currency = cmd.currency() == null || cmd.currency().isBlank()
                ? contract.currency() : cmd.currency().trim().toUpperCase();
        if (contract.currency() != null && !contract.currency().equalsIgnoreCase(currency)) {
            throw ApiException.field(ErrorCode.E_1001, "currency",
                    "币种必须与合同一致（合同：" + contract.currency() + "，提交：" + cmd.currency() + "）（C4）");
        }
        if (cmd.voucherFileId() == null) {
            throw ApiException.field(ErrorCode.E_1001, "voucher_file_id", "打款凭证必填（C5 记录打款需凭证截图）");
        }
        Long fileCount = jdbc.queryForObject("""
                select count(*) from aap_file_asset where id = ? and deleted = false
                """, Long.class, cmd.voucherFileId());
        if (fileCount == null || fileCount == 0) {
            throw ApiException.field(ErrorCode.E_1001, "voucher_file_id",
                    "打款凭证文件不存在：" + cmd.voucherFileId());
        }
        Long active = jdbc.queryForObject("""
                select count(*) from aap_payment_record
                 where contract_id = ? and deleted = false and status in ('PAYMENT_RECORDED','CONFIRMED')
                """, Long.class, cmd.contractId());
        if (active != null && active > 0) {
            throw new ApiException(ErrorCode.E_1601, "该合同已有生效中的打款记录，如需重录请先作废");
        }

        Long actor = actorId(principal);
        PaymentRecordEntity entity = new PaymentRecordEntity();
        entity.setProviderId(contract.providerId());
        entity.setContractId(cmd.contractId());
        entity.setAmount(cmd.amount());
        entity.setCurrency(currency);
        entity.setStatus("PAYMENT_RECORDED");
        entity.setVoucherFileId(cmd.voucherFileId());
        entity.setPaidAt(cmd.paidAt() == null ? OffsetDateTime.now(ZoneOffset.UTC) : cmd.paidAt());
        entity.setRemark(cmd.remark());
        paymentRecordMapper.insert(entity);

        auditService.record(AuditService.AuditAction.PAYMENT_RECORD, "payment", entity.getId(),
                "记录打款（金额 " + cmd.amount().toPlainString() + " " + currency + "，合同 "
                        + (contract.contractNo() == null ? cmd.contractId() : contract.contractNo()) + "）",
                null, Map.of("status", "PAYMENT_RECORDED"), "NORMAL");
        log.info("记录打款 payment_id={} contract={} amount={} actor={}",
                entity.getId(), cmd.contractId(), cmd.amount().toPlainString(), actor);
        // ⚠️ 不要在这里用 JdbcTemplate 回读刚插入的行：本仓库里 MyBatis mapper 的写入与 JdbcTemplate
        //    不在同一个连接/事务中（实测：mapper insert 后同事务内 jdbc 查该 id 得 0 行），
        //    回读会误报 E-1406 并把整笔记录回滚。视图直接用实体 + 已加载的合同行拼装。
        return toView(entity, contract);
    }

    /** 由已插入实体 + 合同快照拼装 Payment 视图（字段顺序与 {@link #mapPayment} 一致）。 */
    private static Payment toView(PaymentRecordEntity e, ContractRow contract) {
        return new Payment(idText(e.getId()), idText(e.getId()), idText(e.getProviderId()),
                idText(e.getContractId()), contract.contractNo(), idText(e.getStatementId()),
                e.getAmount(), e.getCurrency(), e.getStatus(), idText(e.getVoucherFileId()),
                rfc3339(e.getPaidAt()), idText(e.getConfirmedBy()), rfc3339(e.getConfirmedAt()),
                e.getRemark(), rfc3339(e.getCreatedAt()));
    }

    // ------------------------------------------------------------------ ADM-PAY05

    /** ADM-PAY05 作废打款：{@code PAYMENT_RECORDED/CONFIRMED → VOID}（必填理由；作废后可重录，PRD 10 §4.3）。 */
    @Transactional
    public Payment voidPayment(AuthPrincipal principal, Long paymentId, String reason) {
        if (reason == null || reason.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "reason", "作废必须填写理由");
        }
        String trimmed = reason.trim();
        Row row = requireRow(paymentId);
        if (!VOIDABLE.contains(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "打款状态非法流转（当前：" + row.status() + "），仅「已打款待确认/已确认」可作废");
        }
        Long actor = actorId(principal);
        // 参数个数必须与 VOID_SQL 的 4 个占位符一致：reason×2（case 两个分支）+ updated_by + id
        int updated = jdbc.update(VOID_SQL, trimmed, trimmed, actor, paymentId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "打款状态已变化，作废未生效，请刷新后重试");
        }
        auditService.record(AuditService.AuditAction.PAYMENT_VOID, "payment", paymentId,
                "作废打款（理由：" + trimmed + "，合同 "
                        + (row.contractNo() == null ? row.contractId() : row.contractNo()) + "）",
                Map.of("status", row.status()), Map.of("status", "VOID"), "HIGH");
        log.info("作废打款 payment_id={} from={} actor={}", paymentId, row.status(), actor);
        return loadOne(paymentId);
    }

    /** ADM-PAY04 入参。 */
    public record RecordCommand(Long contractId, BigDecimal amount, String currency, Long voucherFileId,
                                OffsetDateTime paidAt, String remark) {
    }

    // ------------------------------------------------------------------ ADM-PAY03

    /** ADM-PAY03 结算单列表（分页）。 */
    public PageResult<Statement> statements(Integer page, Integer pageSize) {
        PageQuery query = PageQuery.of(page, pageSize);
        Long total = jdbc.queryForObject("select count(*) from aap_settlement_statement where deleted = false",
                Long.class);
        List<Statement> items = jdbc.query("""
                select id, statement_no, provider_id, period_from, period_to, total_amount, platform_fee,
                       status, created_at
                  from aap_settlement_statement
                 where deleted = false
                 order by created_at desc, id desc limit ? offset ?
                """, SettlementService::mapStatement, query.pageSize(), query.offset());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ 内部

    private record Row(Long id, Long contractId, String contractNo, String status, BigDecimal amount,
                       String currency) {
    }

    /** 合同快照（打款前校验：状态 / 币种 / 归属供应商）。 */
    private record ContractRow(Long id, String contractNo, Long providerId, String currency, String status) {
    }

    private ContractRow requireContract(Long contractId) {
        List<ContractRow> rows = jdbc.query("""
                select id, contract_no, provider_id, currency, status
                  from aap_contract where id = ? and deleted = false
                """, (rs, rowNum) -> new ContractRow(rs.getObject("id", Long.class),
                        rs.getString("contract_no"), rs.getObject("provider_id", Long.class),
                        rs.getString("currency"), rs.getString("status")), contractId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "合同不存在：" + contractId);
        }
        return rows.get(0);
    }

    private Row requireRow(Long paymentId) {
        List<Row> rows = paymentId == null ? List.of() : jdbc.query("""
                select p.id, p.contract_id, p.status, p.amount, p.currency, c.contract_no
                  from aap_payment_record p
                  left join aap_contract c on c.id = p.contract_id
                 where p.id = ? and p.deleted = false
                """, (rs, rowNum) -> new Row(rs.getObject("id", Long.class),
                        rs.getObject("contract_id", Long.class), rs.getString("contract_no"),
                        rs.getString("status"), rs.getBigDecimal("amount"), rs.getString("currency")),
                paymentId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "打款记录不存在：" + paymentId);
        }
        return rows.get(0);
    }

    private Payment loadOne(Long paymentId) {
        List<Payment> rows = jdbc.query(PAYMENT_SELECT + " where p.id = ? and p.deleted = false",
                SettlementService::mapPayment, paymentId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "打款记录不存在：" + paymentId);
        }
        return rows.get(0);
    }

    private static Payment mapPayment(ResultSet rs, int rowNum) throws SQLException {
        String id = idText(rs.getObject("id", Long.class));
        return new Payment(id, id, idText(rs.getObject("provider_id", Long.class)),
                idText(rs.getObject("contract_id", Long.class)), rs.getString("contract_no"),
                idText(rs.getObject("statement_id", Long.class)), rs.getBigDecimal("amount"),
                rs.getString("currency"), rs.getString("status"),
                idText(rs.getObject("voucher_file_id", Long.class)),
                rfc3339(rs.getObject("paid_at", OffsetDateTime.class)),
                idText(rs.getObject("confirmed_by", Long.class)),
                rfc3339(rs.getObject("confirmed_at", OffsetDateTime.class)), rs.getString("remark"),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
    }

    private static Statement mapStatement(ResultSet rs, int rowNum) throws SQLException {
        return new Statement(idText(rs.getObject("id", Long.class)), rs.getString("statement_no"),
                idText(rs.getObject("provider_id", Long.class)),
                rfc3339(rs.getObject("period_from", OffsetDateTime.class)),
                rfc3339(rs.getObject("period_to", OffsetDateTime.class)), rs.getBigDecimal("total_amount"),
                rs.getBigDecimal("platform_fee"), rs.getString("status"),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
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
