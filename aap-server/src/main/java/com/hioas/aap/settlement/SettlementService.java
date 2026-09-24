package com.hioas.aap.settlement;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.settlement.PaymentViews.Detail;
import com.hioas.aap.settlement.PaymentViews.Line;
import com.hioas.aap.settlement.PaymentViews.Payment;
import com.hioas.aap.settlement.PaymentViews.PaymentPage;
import com.hioas.aap.settlement.PaymentViews.Statement;
import com.hioas.aap.support.AuditService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
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
    /** 结算单号（{@code ST{yyyyMM}{4位}}）：生成器早已存在，此前零调用（D-SETTLE-02 接线）。 */
    private final DocNoGenerator docNoGenerator;

    /** 出账周期口径：当前仅 {@code MONTHLY}（自然月 UTC）。见 application.yml 的 app.settlement.*。 */
    @Value("${app.settlement.cycle:MONTHLY}")
    private String cycle;

    /** 金额计算基数：{@code COST_USD}（默认）或 {@code QUOTA_RAW}。 */
    @Value("${app.settlement.amount-basis:COST_USD}")
    private String amountBasis;

    /** 平台费口径：{@code CONTRACT_RATE}（默认，合同费率 × 基数）或 {@code ZERO}（不收）。 */
    @Value("${app.settlement.fee-basis:CONTRACT_RATE}")
    private String feeBasis;

    public SettlementService(JdbcTemplate jdbc, AuditService auditService,
                             PaymentRecordMapper paymentRecordMapper, DocNoGenerator docNoGenerator) {
        this.jdbc = jdbc;
        this.auditService = auditService;
        this.paymentRecordMapper = paymentRecordMapper;
        this.docNoGenerator = docNoGenerator;
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

    // ------------------------------------------------------------------ ADM-PAY06

    /**
     * ADM-PAY06 生成结算单（D-SETTLE-02 自主拍板口径；三项口径全部可配，见 application.yml 的 app.settlement.*）。
     *
     * <p>口径（为什么这么定见 `.agents/state/aap-decisions.md` D-SETTLE-02）：
     * <ul>
     *   <li>周期 = **自然月 UTC**（与用量窗口 {@code month=YYYY-MM} 同口径，不引入第二套时间定义）；</li>
     *   <li>金额基数 = {@code aap_usage_hourly} 的 {@code cost_usd}（可配为 {@code quota_raw}）合计；</li>
     *   <li>平台费 = 合同 {@code platform_fee_rate} × 基数（{@code fee-basis=ZERO} 时不收）；</li>
     *   <li>明细维度 = **渠道 × 模型**（= {@code aap_settlement_line} 的表列）；门槛 = 合同 {@code min_settlement_amount}。</li>
     * </ul>
     *
     * <p>硬口径：
     * <ul>
     *   <li>无 {@code SIGNED} 合同 → 409 {@code E-1701}（出账必须有生效合同）；</li>
     *   <li>周期内无用量 → 409 {@code E-1601}，**不生成 0 元单**（0 会冒充「有数据」）；</li>
     *   <li>同周期已有有效单 → 返回既有单（幂等，不新增行，唯一性由 V14 的部分唯一索引兜底）；</li>
     *   <li>生成时把期内、尚未关联的 {@code PAYMENT_RECORDED/CONFIRMED} 打款回填 {@code statement_id}
     *       （补上「打款与结算单无关联」这条悬空口径）。</li>
     * </ul>
     */
    @Transactional
    public Detail generate(AuthPrincipal principal, GenerateCommand cmd) {
        if (cmd.providerId() == null) {
            throw ApiException.field(ErrorCode.E_1001, "provider_id", "供应商必填");
        }
        if (!"MONTHLY".equalsIgnoreCase(cycle)) {
            // 诚实边界：配置项存在但只实现了 MONTHLY；配了别的值必须响亮失败，
            // 而不是「静默按自然月算」——否则配置看似生效、实际被忽略。
            throw new ApiException(ErrorCode.E_2001, "不支持的出账周期：" + cycle + "（当前仅实现 MONTHLY）");
        }
        YearMonth ym = parseMonth(cmd.month());
        OffsetDateTime from = ym.atDay(1).atStartOfDay().atOffset(ZoneOffset.UTC);
        OffsetDateTime to = ym.plusMonths(1).atDay(1).atStartOfDay().atOffset(ZoneOffset.UTC);
        Long providerId = cmd.providerId();

        String providerName = providerName(providerId);
        if (providerName == null) {
            throw new ApiException(ErrorCode.E_1406, "供应商不存在：" + providerId);
        }
        FeeContract contract = requireSignedContract(providerId);

        Long existing = jdbc.query("""
                select id from aap_settlement_statement
                 where provider_id = ? and period_from = ?::timestamptz and period_to = ?::timestamptz
                   and deleted = false and status <> 'VOID'
                 order by id desc limit 1
                """, rs -> rs.next() ? rs.getObject("id", Long.class) : null, providerId, from, to);
        if (existing != null) {
            log.info("结算单已存在（幂等复用） statement_id={} provider_id={} period={}", existing, providerId, ym);
            return detail(existing);
        }

        List<LineRow> rows = jdbc.query("""
                select channel_id, model_name,
                       coalesce(sum(total_tokens), 0) as tokens,
                       coalesce(sum(quota_raw), 0) as quota,
                       coalesce(sum(%s), 0) as amount
                  from aap_usage_hourly
                 where deleted = false and provider_id = ?
                   and stat_hour >= ?::timestamptz and stat_hour < ?::timestamptz
                 group by channel_id, model_name
                 order by channel_id nulls first, model_name
                """.formatted(amountColumn()),
                (rs, rowNum) -> new LineRow(rs.getObject("channel_id", Long.class), rs.getString("model_name"),
                        rs.getLong("tokens"), rs.getBigDecimal("quota"), rs.getBigDecimal("amount")),
                providerId, from, to);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1601,
                    "该周期（" + ym + "）没有用量数据，不能出账（不生成 0 元结算单）");
        }

        BigDecimal total = rows.stream().map(LineRow::amount).reduce(BigDecimal.ZERO, BigDecimal::add)
                .setScale(6, RoundingMode.HALF_UP);
        BigDecimal fee = platformFee(total, contract);
        if (contract.minAmount() != null && total.compareTo(contract.minAmount()) < 0) {
            throw new ApiException(ErrorCode.E_1601, "结算金额 " + total.toPlainString()
                    + " 低于合同约定门槛 " + contract.minAmount().toPlainString() + "，本期不出账");
        }

        Long actor = actorId(principal);
        long statementId = newId("seq_settlement_statement_id");
        String statementNo = docNoGenerator.statementNo();
        jdbc.update("""
                insert into aap_settlement_statement (id, statement_no, provider_id, period_from, period_to,
                                                      total_amount, platform_fee, status, created_by, updated_by)
                values (?, ?, ?, ?::timestamptz, ?::timestamptz, ?::numeric, ?::numeric, 'DRAFT', ?, ?)
                """, statementId, statementNo, providerId, from, to, total, fee, actor, actor);

        for (LineRow row : rows) {
            jdbc.update("""
                    insert into aap_settlement_line (id, statement_id, channel_id, model_name,
                                                     total_tokens, quota_raw, amount, created_by, updated_by)
                    values (?, ?, ?, ?, ?, ?::numeric, ?::numeric, ?, ?)
                    """, newId("seq_settlement_line_id"), statementId, row.channelId(), row.modelName(),
                    row.tokens(), row.quota(), row.amount(), actor, actor);
        }

        int linked = jdbc.update("""
                update aap_payment_record
                   set statement_id = ?, updated_at = now(), updated_by = ?, version = version + 1
                 where provider_id = ? and statement_id is null and deleted = false
                   and status in ('PAYMENT_RECORDED', 'CONFIRMED')
                   and paid_at >= ?::timestamptz and paid_at < ?::timestamptz
                """, statementId, actor, providerId, from, to);

        auditService.record(AuditService.AuditAction.STATEMENT_GENERATE, "settlement_statement", statementId,
                "生成结算单 " + statementNo + "（周期 " + ym + "，金额 " + total.toPlainString()
                        + "，平台费 " + fee.toPlainString() + "，明细 " + rows.size() + " 行，关联打款 " + linked + " 笔）",
                null, Map.of("status", "DRAFT"), "NORMAL");
        log.info("生成结算单 statement_id={} no={} provider_id={} period={} total={} fee={} lines={} linked_payments={}",
                statementId, statementNo, providerId, ym, total.toPlainString(), fee.toPlainString(),
                rows.size(), linked);
        return detail(statementId);
    }

    // ------------------------------------------------------------------ ADM-PAY07 / 08 / 09 + SET-01 / SET-02

    /** ADM-PAY07 结算单详情（含明细行与已关联打款）。 */
    public Detail detail(Long statementId) {
        return assemble(requireStatement(statementId));
    }

    /** SET-02 供应商端详情：只允许读本供应商的单；越权与不存在一律 404 {@code E-1406}（不泄露存在性）。 */
    public Detail detailForProvider(AuthPrincipal principal, Long statementId) {
        Long providerId = requireProviderPrincipal(principal);
        StatementRow row = requireStatement(statementId);
        if (!providerId.equals(row.providerId())) {
            throw new ApiException(ErrorCode.E_1406, "结算单不存在：" + statementId);
        }
        return assemble(row);
    }

    /** SET-01 本供应商结算单列表（分页，按创建时间倒序）。 */
    public PageResult<Statement> statementsForProvider(AuthPrincipal principal, Integer page, Integer pageSize) {
        Long providerId = requireProviderPrincipal(principal);
        PageQuery query = PageQuery.of(page, pageSize);
        Long total = jdbc.queryForObject("""
                select count(*) from aap_settlement_statement where deleted = false and provider_id = ?
                """, Long.class, providerId);
        List<Statement> items = jdbc.query("""
                select id, statement_no, provider_id, period_from, period_to, total_amount, platform_fee,
                       status, created_at
                  from aap_settlement_statement
                 where deleted = false and provider_id = ?
                 order by created_at desc, id desc limit ? offset ?
                """, SettlementService::mapStatement, providerId, query.pageSize(), query.offset());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    /** ADM-PAY08 确认出账：{@code DRAFT → CONFIRMED}（条件 UPDATE 拿真实影响行数做并发判定）。 */
    @Transactional
    public Detail confirmStatement(AuthPrincipal principal, Long statementId) {
        StatementRow row = requireStatement(statementId);
        if (!"DRAFT".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "结算单状态非法流转（当前：" + row.status() + "），仅草稿可确认出账");
        }
        Long actor = actorId(principal);
        int updated = jdbc.update("""
                update aap_settlement_statement
                   set status = 'CONFIRMED', updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'DRAFT' and deleted = false
                """, actor, statementId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "结算单状态已变化，确认未生效，请刷新后重试");
        }
        auditService.record(AuditService.AuditAction.STATEMENT_CONFIRM, "settlement_statement", statementId,
                "确认出账 " + row.statementNo() + "（金额 " + plain(row.totalAmount())
                        + "，平台费 " + plain(row.platformFee()) + "）",
                Map.of("status", "DRAFT"), Map.of("status", "CONFIRMED"), "HIGH");
        log.info("确认出账 statement_id={} no={} actor={}", statementId, row.statementNo(), actor);
        return detail(statementId);
    }

    /**
     * ADM-PAY09 作废结算单：{@code DRAFT → VOID}（理由必填，落审计）。
     *
     * <p>作废后**可重新生成**（V14 的部分唯一索引把 VOID 排除在唯一性之外），历史单保留可追溯 ——
     * 不物理删除、不覆盖（对账场景里「删掉重来」是不可接受的审计形态）。
     */
    @Transactional
    public Detail voidStatement(AuthPrincipal principal, Long statementId, String reason) {
        if (reason == null || reason.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "reason", "作废必须填写理由");
        }
        String trimmed = reason.trim();
        StatementRow row = requireStatement(statementId);
        if (!"DRAFT".equals(row.status())) {
            throw new ApiException(ErrorCode.E_1601,
                    "结算单状态非法流转（当前：" + row.status() + "），仅草稿可作废（已确认出账为终态）");
        }
        Long actor = actorId(principal);
        int updated = jdbc.update("""
                update aap_settlement_statement
                   set status = 'VOID', updated_at = now(), updated_by = ?, version = version + 1
                 where id = ? and status = 'DRAFT' and deleted = false
                """, actor, statementId);
        if (updated != 1) {
            throw new ApiException(ErrorCode.E_1601, "结算单状态已变化，作废未生效，请刷新后重试");
        }
        // 作废同时解开打款关联（否则该笔打款会挂在一张 VOID 单上，重新生成时无法再挂）
        int released = jdbc.update("""
                update aap_payment_record
                   set statement_id = null, updated_at = now(), updated_by = ?, version = version + 1
                 where statement_id = ? and deleted = false
                """, actor, statementId);
        auditService.record(AuditService.AuditAction.STATEMENT_VOID, "settlement_statement", statementId,
                "作废结算单 " + row.statementNo() + "（理由：" + trimmed + "，解除打款关联 " + released + " 笔）",
                Map.of("status", "DRAFT"), Map.of("status", "VOID"), "HIGH");
        log.info("作废结算单 statement_id={} no={} released_payments={} actor={}",
                statementId, row.statementNo(), released, actor);
        return detail(statementId);
    }

    // ------------------------------------------------------------------ 内部

    /** ADM-PAY06 入参。 */
    public record GenerateCommand(Long providerId, String month) {
    }

    /** 合同里的结算口径（费率 / 门槛 / 币种）。 */
    private record FeeContract(BigDecimal feeRate, BigDecimal minAmount, String currency) {
    }

    /** 用量汇总行（维度：渠道 × 模型）。 */
    private record LineRow(Long channelId, String modelName, long tokens, BigDecimal quota, BigDecimal amount) {
    }

    /** 结算单主行快照。 */
    private record StatementRow(Long id, String statementNo, Long providerId, OffsetDateTime periodFrom,
                                OffsetDateTime periodTo, BigDecimal totalAmount, BigDecimal platformFee,
                                String status, OffsetDateTime createdAt) {
    }

    /** 月份格式（与清单 §0「月份 `YYYY-MM`」一致；用字符类而非反斜杠，避免写盘转义层级问题）。 */
    private static final Pattern MONTH_PATTERN = Pattern.compile("[0-9]{4}-(0[1-9]|1[0-2])");

    /** 月份解析：非法格式 → 400 {@code E-1001}（字段级定位，不静默取当月）。 */
    private static YearMonth parseMonth(String month) {
        if (month == null || !MONTH_PATTERN.matcher(month.trim()).matches()) {
            throw ApiException.field(ErrorCode.E_1001, "month", "月份格式必须为 YYYY-MM（如 2026-09）");
        }
        return YearMonth.parse(month.trim());
    }

    /** 金额基数对应的列名（**白名单**：配置值不直接拼进 SQL）。 */
    private String amountColumn() {
        return "QUOTA_RAW".equalsIgnoreCase(amountBasis) ? "quota_raw" : "cost_usd";
    }

    /** 平台费：合同费率 × 基数；{@code fee-basis=ZERO} 时不收（口径可配）。 */
    private BigDecimal platformFee(BigDecimal total, FeeContract contract) {
        if ("ZERO".equalsIgnoreCase(feeBasis)) {
            return BigDecimal.ZERO.setScale(6, RoundingMode.HALF_UP);
        }
        BigDecimal rate = contract.feeRate() == null ? BigDecimal.ZERO : contract.feeRate();
        return total.multiply(rate).setScale(6, RoundingMode.HALF_UP);
    }

    /** 取该供应商最新 SIGNED 合同；无 → 409 {@code E-1701}（出账必须有生效合同）。 */
    private FeeContract requireSignedContract(Long providerId) {
        List<FeeContract> rows = jdbc.query("""
                select platform_fee_rate, min_settlement_amount, currency
                  from aap_contract
                 where provider_id = ? and deleted = false and status = 'SIGNED'
                 order by id desc limit 1
                """, (rs, rowNum) -> new FeeContract(rs.getBigDecimal("platform_fee_rate"),
                rs.getBigDecimal("min_settlement_amount"), rs.getString("currency")), providerId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1701, "该供应商没有生效（SIGNED）合同，不能出账");
        }
        return rows.get(0);
    }

    private String providerName(Long providerId) {
        List<String> names = jdbc.query("select company_name from aap_provider where id = ? and deleted = false",
                (rs, rowNum) -> rs.getString(1), providerId);
        return names.isEmpty() ? null : names.get(0);
    }

    private StatementRow requireStatement(Long statementId) {
        List<StatementRow> rows = statementId == null ? List.of() : jdbc.query("""
                select id, statement_no, provider_id, period_from, period_to, total_amount, platform_fee,
                       status, created_at
                  from aap_settlement_statement
                 where id = ? and deleted = false
                """, (rs, rowNum) -> new StatementRow(rs.getObject("id", Long.class), rs.getString("statement_no"),
                rs.getObject("provider_id", Long.class), rs.getObject("period_from", OffsetDateTime.class),
                rs.getObject("period_to", OffsetDateTime.class), rs.getBigDecimal("total_amount"),
                rs.getBigDecimal("platform_fee"), rs.getString("status"),
                rs.getObject("created_at", OffsetDateTime.class)), statementId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "结算单不存在：" + statementId);
        }
        return rows.get(0);
    }

    /**
     * 拼装结算单详情。
     *
     * <p>为什么是「一次查主行 + 一次查明细 + 一次查打款」而不是 join：明细与打款都是 1:N，
     * join 会笛卡尔放大；且三张表都很小（单供应商单周期）。
     *
     * <p>{@code currency} 取自合同（statement 表无该列）、{@code provider_name} 取自供应商表，
     * 二者都是**展示用派生字段**，不落库（避免同一事实两份存储）。
     */
    private Detail assemble(StatementRow s) {
        List<Line> lines = jdbc.query("""
                select id, statement_id, channel_id, model_name, total_tokens, quota_raw, amount
                  from aap_settlement_line
                 where statement_id = ? and deleted = false
                 order by channel_id nulls first, model_name
                """, (rs, rowNum) -> new Line(idText(rs.getObject("id", Long.class)),
                idText(rs.getObject("statement_id", Long.class)),
                idText(rs.getObject("channel_id", Long.class)), rs.getString("model_name"),
                rs.getLong("total_tokens"), rs.getBigDecimal("quota_raw"), rs.getBigDecimal("amount")), s.id());
        List<Payment> payments = jdbc.query(PAYMENT_SELECT + """
                 where p.statement_id = ? and p.deleted = false
                 order by p.id
                """, SettlementService::mapPayment, s.id());
        BigDecimal total = s.totalAmount() == null ? BigDecimal.ZERO : s.totalAmount();
        BigDecimal fee = s.platformFee() == null ? BigDecimal.ZERO : s.platformFee();
        FeeContract contract = latestContractQuietly(s.providerId());
        return new Detail(idText(s.id()), s.statementNo(), idText(s.providerId()), providerName(s.providerId()),
                rfc3339(s.periodFrom()), rfc3339(s.periodTo()), total, fee, total.subtract(fee),
                contract == null || contract.currency() == null ? "USD" : contract.currency(),
                s.status(), rfc3339(s.createdAt()), lines, payments);
    }

    /** 详情展示用的合同口径（缺失时返回 null，不抛错——详情查询不该因合同状态变化而失败）。 */
    private FeeContract latestContractQuietly(Long providerId) {
        List<FeeContract> rows = jdbc.query("""
                select platform_fee_rate, min_settlement_amount, currency
                  from aap_contract
                 where provider_id = ? and deleted = false and status = 'SIGNED'
                 order by id desc limit 1
                """, (rs, rowNum) -> new FeeContract(rs.getBigDecimal("platform_fee_rate"),
                rs.getBigDecimal("min_settlement_amount"), rs.getString("currency")), providerId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    /** 供应商端必须绑定档案（与 PAY-01 同口径）。 */
    private static Long requireProviderPrincipal(AuthPrincipal principal) {
        Long providerId = principal == null ? null : principal.providerId();
        if (providerId == null) {
            throw new ApiException(ErrorCode.E_1001, "当前账号未绑定供应商档案");
        }
        return providerId;
    }

    /** 从白名单序列取 ID（序列名不来自外部输入）。 */
    private long newId(String sequence) {
        Long value = jdbc.queryForObject("select nextval('" + sequence + "')", Long.class);
        return value == null ? 0L : value;
    }

    private static String plain(BigDecimal value) {
        return value == null ? "0" : value.toPlainString();
    }

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
