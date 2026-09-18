package com.hioas.aap.review;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.contract.ContractEntity;
import com.hioas.aap.contract.ContractMapper;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.quote.QuoteEntity;
import com.hioas.aap.quote.QuoteMapper;
import com.hioas.aap.review.ReviewViews.Record;
import com.hioas.aap.review.ReviewViews.RecordList;
import com.hioas.aap.review.ReviewViews.Task;
import com.hioas.aap.support.AuditService;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 报价单审核（ADM-R01…R05；真源 `13-管理端PRD.md` §5 M8 + `10-报价与合同结算PRD.md` §3.6/§4.1）。
 *
 * <p>设计取舍：
 * <ul>
 *   <li>**入池由提交驱动**：QT-09 提交时落一条 {@code aap_review_task(PENDING)}，待审池直接查任务表
 *       （不在读取时反推报价单状态——那会让「已领取/已驳回」的历史丢失）。</li>
 *   <li>**状态流转一律条件 UPDATE**（见本类 CLAIM/APPROVE/REJECT 常量）：并发领取/终态重放都只能有一个人成功，
 *       失败方拿 E-1601，不静默覆盖。</li>
 *   <li>**A9 合同同事务生成**：通过 → 插合同（CREATED）→ 回写 {@code quote.contract_id}/APPROVED，
 *       任何一步失败整体回滚，不出现「已通过但无合同」或「有合同但没通过」。</li>
 *   <li>**查询用显式 SQL**：待审池/时间线是 join + 过滤 + 分页，{@link JdbcTemplate} 比 QueryWrapper 可读
 *       （同 {@code UsageService} 的取舍）。</li>
 * </ul>
 */
@Service
public class ReviewService {

    private static final Logger log = LoggerFactory.getLogger(ReviewService.class);

    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 可被审核动作推进的状态（终态 APPROVED/REJECTED 一律拒绝，E-1601）。 */
    private static final Set<String> REVIEWABLE = Set.of("PENDING", "CLAIMED");

    /** 驳回原因码（真源：review-reject.schema.json 的 enum，与 PRD §5.2 一致）。 */
    private static final Set<String> REASON_CODES = Set.of("PRICE_TOO_HIGH", "PRICE_STRUCTURE_INVALID",
            "CACHE_PRICE_MISSING", "TECH_RISK", "VALIDITY_ISSUE", "MISSING_INFO", "OTHER");

    private static final String TASK_SELECT = """
            select t.id, t.quote_id, t.provider_id, t.status, t.claimed_by, t.claimed_at,
                   t.review_comment, t.reject_reason_code, t.tech_metrics_snapshot,
                   t.created_at, t.updated_at, q.quote_no,
                   coalesce(p.short_name, p.company_name, p.provider_no) as provider_name
              from aap_review_task t
              left join aap_quote q on q.id = t.quote_id
              left join aap_provider p on p.id = t.provider_id
            """;

    /**
     * 状态流转 SQL（条件 UPDATE = 乐观锁）。
     *
     * <p><b>为什么这些 UPDATE 走 JdbcTemplate 而不是 Mapper</b>：同一请求里「Mapper 写 → JdbcTemplate 读」
     * 会读到**写之前**的值（实测：领取响应仍回 PENDING，而库里的确已 CLAIMED；两个客户端各拿各的连接，
     * 未提交写对另一个连接不可见）。读写必须同源——本类读侧统一 JdbcTemplate，写侧（这四条）也统一；
     * 顺带拿到**真实影响行数**，乐观锁才真的能判定「有人抢先」。
     */
    private static final String CLAIM_SQL_NO_SNAPSHOT = """
            update aap_review_task
               set status = 'CLAIMED', claimed_by = ?, claimed_at = now(),
                   updated_at = now(), updated_by = ?, version = version + 1
             where id = ? and status = 'PENDING' and deleted = false
            """;

    private static final String CLAIM_SQL_WITH_SNAPSHOT = """
            update aap_review_task
               set status = 'CLAIMED', claimed_by = ?, claimed_at = now(),
                   tech_metrics_snapshot = cast(? as jsonb),
                   updated_at = now(), updated_by = ?, version = version + 1
             where id = ? and status = 'PENDING' and deleted = false
            """;

    private static final String APPROVE_SQL = """
            update aap_review_task
               set status = 'APPROVED', review_comment = coalesce(?, review_comment),
                   reject_reason_code = null, reject_reason_text = null,
                   updated_at = now(), updated_by = ?, version = version + 1
             where id = ? and status in ('PENDING', 'CLAIMED') and deleted = false
            """;

    private static final String REJECT_SQL = """
            update aap_review_task
               set status = 'REJECTED', review_comment = coalesce(?, review_comment),
                   reject_reason_code = ?, reject_reason_text = ?,
                   updated_at = now(), updated_by = ?, version = version + 1
             where id = ? and status in ('PENDING', 'CLAIMED') and deleted = false
            """;

    private final JdbcTemplate jdbc;
    private final ReviewTaskMapper taskMapper;
    private final ReviewRecordMapper recordMapper;
    private final QuoteMapper quoteMapper;
    private final ContractMapper contractMapper;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;

    public ReviewService(JdbcTemplate jdbc, ReviewTaskMapper taskMapper, ReviewRecordMapper recordMapper,
                         QuoteMapper quoteMapper, ContractMapper contractMapper,
                         DocNoGenerator docNoGenerator, AuditService auditService) {
        this.jdbc = jdbc;
        this.taskMapper = taskMapper;
        this.recordMapper = recordMapper;
        this.quoteMapper = quoteMapper;
        this.contractMapper = contractMapper;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ 入池

    /**
     * 报价单提交入池（QT-09 同事务调用）。
     *
     * <p>已存在任务的报价单（驳回后重提）**复用同一行**回到 PENDING：{@code uq_review_quote}
     * 唯一索引不允许第二条任务行，硬插会 500。
     */
    @Transactional
    public void onQuoteSubmitted(QuoteEntity quote) {
        ReviewTaskEntity existing = taskMapper.selectByQuote(quote.getId());
        if (existing == null) {
            ReviewTaskEntity task = new ReviewTaskEntity();
            task.setQuoteId(quote.getId());
            task.setProviderId(quote.getProviderId());
            task.setStatus("PENDING");
            taskMapper.insert(task);
            log.info("审核任务入池 quote_id={} task_id={}", quote.getId(), task.getId());
            return;
        }
        jdbc.update("""
                update aap_review_task
                   set status = 'PENDING',
                       claimed_by = null,
                       claimed_at = null,
                       tech_metrics_snapshot = null,
                       review_comment = null,
                       reject_reason_code = null,
                       reject_reason_text = null,
                       updated_at = now(),
                       updated_by = ?,
                       version = version + 1
                 where id = ? and deleted = false and status <> 'PENDING'
                """, quote.getSubmittedBy(), existing.getId());
        log.info("审核任务重提复位 quote_id={} task_id={}", quote.getId(), existing.getId());
    }

    // ------------------------------------------------------------------ ADM-R01

    /** ADM-R01 待审报价池（可按 status 过滤）。 */
    public PageResult<Task> list(String status, Integer page, Integer pageSize) {
        PageQuery query = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where t.deleted = false");
        List<Object> args = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and t.status = ?");
            args.add(status.trim().toUpperCase());
        }
        Long total = jdbc.queryForObject("select count(*) from aap_review_task t" + where,
                Long.class, args.toArray());
        List<Object> pageArgs = new ArrayList<>(args);
        pageArgs.add(query.pageSize());
        pageArgs.add(query.offset());
        // 排序列显式指定（含 id 兜底）：同一毫秒入池的两单顺序稳定，分页才不会漏/重。
        List<Task> items = jdbc.query(TASK_SELECT + where + " order by t.created_at desc, t.id desc limit ? offset ?",
                ReviewService::mapTask, pageArgs.toArray());
        return PageResult.of(items, query.page(), query.pageSize(), total == null ? 0L : total);
    }

    // ------------------------------------------------------------------ ADM-R02

    /** ADM-R02 领取：PENDING → CLAIMED，并把检测结论快照冻结到任务上。 */
    @Transactional
    public Task claim(AuthPrincipal principal, Long taskId) {
        Long actor = actorId(principal);
        ReviewTaskEntity task = requireTask(taskId);
        String before = task.getStatus();
        if (!"PENDING".equals(before)) {
            throw new ApiException(ErrorCode.E_1601, "该审核任务已被领取或已出结论（当前：" + before + "）");
        }
        String snapshot = techSnapshotJson(task.getProviderId());
        int updated = snapshot == null
                ? jdbc.update(CLAIM_SQL_NO_SNAPSHOT, actor, actor, taskId)
                : jdbc.update(CLAIM_SQL_WITH_SNAPSHOT, actor, snapshot, actor, taskId);
        if (updated != 1) {
            // 并发领取：条件在读写窗口内被改写 → 后来者失败（E1 乐观锁）
            throw new ApiException(ErrorCode.E_1601, "该审核任务已被他人领取，请刷新后重试");
        }
        moveQuoteToReviewing(task.getQuoteId());
        record(task, "ASSIGN", before, "CLAIMED", null, null, actor, principal);
        log.info("审核领取 task_id={} quote_id={} actor={}", taskId, task.getQuoteId(), actor);
        return loadTask(taskId);
    }

    // ------------------------------------------------------------------ ADM-R03

    /** ADM-R03 通过：PENDING|CLAIMED → APPROVED，并生成合同（A9）。 */
    @Transactional
    public Task approve(AuthPrincipal principal, Long taskId, String comment) {
        Long actor = actorId(principal);
        ReviewTaskEntity task = requireTask(taskId);
        String before = task.getStatus();
        if (!REVIEWABLE.contains(before)) {
            throw new ApiException(ErrorCode.E_1601, "该审核任务已出结论（当前：" + before + "），不可重复通过");
        }
        if (jdbc.update(APPROVE_SQL, comment, actor, taskId) != 1) {
            throw new ApiException(ErrorCode.E_1601, "该审核任务状态已变化，请刷新后重试");
        }
        QuoteEntity quote = requireQuote(task.getQuoteId());
        ContractEntity contract = createContract(quote);
        quote.setStatus("APPROVED");
        quote.setReviewedBy(actor);
        quote.setReviewedAt(OffsetDateTime.now(ZoneOffset.UTC));
        quote.setApprovedQuoteVersion(quote.getCurrentVersion());
        quote.setContractId(contract.getId());
        if (quoteMapper.update(quote) != 1) {
            throw new ApiException(ErrorCode.E_1601, "报价单状态已变化，审核结论未生效");
        }
        record(task, "APPROVE", before, "APPROVED", comment, null, actor, principal);
        auditService.record(AuditService.AuditAction.QUOTE_APPROVE, "quote", quote.getId(),
                "审核通过报价单 " + quote.getQuoteNo() + "，生成合同 " + contract.getContractNo()
                        + (comment == null || comment.isBlank() ? "" : "（备注：" + comment + "）"),
                Map.of("status", before), Map.of("status", "APPROVED"), "NORMAL");
        log.info("审核通过 task_id={} quote_id={} contract_no={} actor={}",
                taskId, quote.getId(), contract.getContractNo(), actor);
        return loadTask(taskId);
    }

    // ------------------------------------------------------------------ ADM-R04

    /** ADM-R04 驳回：PENDING|CLAIMED → REJECTED，原因码必填且必须命中枚举。 */
    @Transactional
    public Task reject(AuthPrincipal principal, Long taskId, String reasonCode, String reasonText,
                       String itemId, String field) {
        Long actor = actorId(principal);
        if (reasonCode == null || reasonCode.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "reason_code", "驳回原因码必填");
        }
        String code = reasonCode.trim().toUpperCase();
        if (!REASON_CODES.contains(code)) {
            throw ApiException.field(ErrorCode.E_1001, "reason_code",
                    "驳回原因码非法：" + reasonCode + "（可选 " + String.join("/", REASON_CODES) + "）");
        }
        ReviewTaskEntity task = requireTask(taskId);
        String before = task.getStatus();
        if (!REVIEWABLE.contains(before)) {
            throw new ApiException(ErrorCode.E_1601, "该审核任务已出结论（当前：" + before + "），不可重复驳回");
        }
        if (jdbc.update(REJECT_SQL, reasonText, code, reasonText, actor, taskId) != 1) {
            throw new ApiException(ErrorCode.E_1601, "该审核任务状态已变化，请刷新后重试");
        }
        QuoteEntity quote = requireQuote(task.getQuoteId());
        quote.setStatus("REJECTED");
        quote.setReviewedBy(actor);
        quote.setReviewedAt(OffsetDateTime.now(ZoneOffset.UTC));
        quote.setRejectReasonCode(code);
        quote.setRejectReasonText(reasonText);
        if (quoteMapper.update(quote) != 1) {
            throw new ApiException(ErrorCode.E_1601, "报价单状态已变化，驳回未生效");
        }
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("reason_code", code);
        snapshot.put("item_id", itemId);
        snapshot.put("field", field);
        record(task, "REJECT", before, "REJECTED", reasonText, snapshot, actor, principal);
        auditService.record(AuditService.AuditAction.QUOTE_REJECT, "quote", quote.getId(),
                "驳回报价单 " + quote.getQuoteNo() + "（原因 " + code + "）",
                Map.of("status", before), Map.of("status", "REJECTED"), "NORMAL");
        log.info("审核驳回 task_id={} quote_id={} reason={} actor={}", taskId, quote.getId(), code, actor);
        return loadTask(taskId);
    }

    // ------------------------------------------------------------------ ADM-R05

    /** ADM-R05 审核记录（可按 quoteId 过滤，按时间正序 = 时间线）。 */
    public RecordList records(Long quoteId) {
        StringBuilder sql = new StringBuilder("""
                select id, quote_id, task_id, action, operator_id, operator_name,
                       before_status, after_status, comment, created_at
                  from aap_review_record
                 where deleted = false
                """);
        List<Object> args = new ArrayList<>();
        if (quoteId != null) {
            sql.append(" and quote_id = ?");
            args.add(quoteId);
        }
        sql.append(" order by created_at, id");
        return new RecordList(jdbc.query(sql.toString(), ReviewService::mapRecord, args.toArray()));
    }

    // ------------------------------------------------------------------ 内部

    private ReviewTaskEntity requireTask(Long taskId) {
        ReviewTaskEntity task = taskId == null ? null : taskMapper.selectOneById(taskId);
        if (task == null) {
            throw new ApiException(ErrorCode.E_1406, "审核任务不存在：" + taskId);
        }
        return task;
    }

    private QuoteEntity requireQuote(Long quoteId) {
        QuoteEntity quote = quoteId == null ? null : quoteMapper.selectOneById(quoteId);
        if (quote == null) {
            throw new ApiException(ErrorCode.E_1406, "报价单不存在：" + quoteId);
        }
        return quote;
    }

    /** 领取时报价单进入 REVIEWING（SUBMITTED → REVIEWING）；其他状态说明数据不一致，直接拒绝。 */
    private void moveQuoteToReviewing(Long quoteId) {
        QuoteEntity quote = requireQuote(quoteId);
        if (!"SUBMITTED".equals(quote.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "报价单不在待审状态（当前：" + quote.getStatus() + "）");
        }
        String before = quote.getStatus();
        quote.setStatus("REVIEWING");
        if (quoteMapper.update(quote) != 1) {
            throw new ApiException(ErrorCode.E_1601, "报价单状态已变化，领取未生效");
        }
        auditService.record(AuditService.AuditAction.QUOTE_SAVE, "quote", quoteId,
                "报价单进入审核中（" + before + "→REVIEWING）",
                Map.of("status", before), Map.of("status", "REVIEWING"), "NORMAL");
    }

    /** A9：通过即生成合同（CREATED），金额口径按实际用量结算 → 不写死金额字段。 */
    private ContractEntity createContract(QuoteEntity quote) {
        ContractEntity contract = new ContractEntity();
        contract.setContractNo(docNoGenerator.contractNo());
        contract.setQuoteId(quote.getId());
        contract.setProviderId(quote.getProviderId());
        contract.setTitle("渠道合作合同 " + quote.getQuoteNo());
        contract.setStatus("CREATED");
        contract.setSignChannel("OFFLINE");
        contract.setCurrency(quote.getCurrency() == null ? "USD" : quote.getCurrency());
        contract.setValidFrom(quote.getValidFrom());
        contract.setValidTo(quote.getValidTo());
        contractMapper.insert(contract);
        return contract;
    }

    /** 最新一份检测报告结论快照（审核台左栏证据区；无报告则 null，不编造结论）。 */
    private String techSnapshotJson(Long providerId) {
        if (providerId == null) {
            return null;
        }
        List<Map<String, Object>> rows = jdbc.query("""
                select total_score, result, confidence, veto_triggered, detected_at
                  from aap_report
                 where provider_id = ? and deleted = false
                 order by detected_at desc nulls last, created_at desc, id desc
                 limit 1
                """, (rs, rowNum) -> {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("total_score", rs.getBigDecimal("total_score"));
            row.put("result", rs.getString("result"));
            row.put("confidence", rs.getString("confidence"));
            row.put("veto_triggered", rs.getBoolean("veto_triggered"));
            row.put("detected_at", rfc3339(rs.getObject("detected_at", OffsetDateTime.class)));
            return row;
        }, providerId);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Object> snapshot = rows.get(0);
        // detected_at 为 null 时从快照里剔除，避免下游把 "detected_at": null 当"检测未完成"以外的含义
        if (snapshot.get("detected_at") == null) {
            snapshot.remove("detected_at");
        }
        return JsonCodec.toJson(snapshot);
    }

    private void record(ReviewTaskEntity task, String action, String before, String after, String comment,
                        Map<String, Object> snapshot, Long actor, AuthPrincipal principal) {
        ReviewRecordEntity record = new ReviewRecordEntity();
        record.setQuoteId(task.getQuoteId());
        record.setTaskId(task.getId());
        record.setAction(action);
        record.setOperatorId(actor);
        record.setOperatorName(principal == null ? null : principal.name());
        record.setBeforeStatus(before);
        record.setAfterStatus(after);
        record.setComment(comment);
        record.setSnapshot(snapshot == null ? null : JsonCodec.toJson(snapshot));
        recordMapper.insert(record);
    }

    private Task loadTask(Long taskId) {
        List<Task> rows = jdbc.query(TASK_SELECT + " where t.id = ? and t.deleted = false",
                ReviewService::mapTask, taskId);
        if (rows.isEmpty()) {
            throw new ApiException(ErrorCode.E_1406, "审核任务不存在：" + taskId);
        }
        return rows.get(0);
    }

    private static Task mapTask(ResultSet rs, int rowNum) throws SQLException {
        String id = idText(rs.getObject("id", Long.class));
        return new Task(id, id, idText(rs.getObject("quote_id", Long.class)), rs.getString("quote_no"),
                idText(rs.getObject("provider_id", Long.class)), rs.getString("provider_name"),
                rs.getString("status"), idText(rs.getObject("claimed_by", Long.class)),
                rfc3339(rs.getObject("claimed_at", OffsetDateTime.class)), rs.getString("review_comment"),
                rs.getString("reject_reason_code"), JsonCodec.readTree(rs.getString("tech_metrics_snapshot")),
                rfc3339(rs.getObject("created_at", OffsetDateTime.class)),
                rfc3339(rs.getObject("updated_at", OffsetDateTime.class)));
    }

    private static Record mapRecord(ResultSet rs, int rowNum) throws SQLException {
        return new Record(idText(rs.getObject("id", Long.class)),
                idText(rs.getObject("quote_id", Long.class)), idText(rs.getObject("task_id", Long.class)),
                rs.getString("action"), idText(rs.getObject("operator_id", Long.class)),
                rs.getString("operator_name"), rs.getString("before_status"), rs.getString("after_status"),
                rs.getString("comment"), rfc3339(rs.getObject("created_at", OffsetDateTime.class)));
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
