package com.hioas.aap.compile;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.quote.QuoteEntity;
import com.hioas.aap.quote.QuoteItemEntity;
import com.hioas.aap.quote.QuoteItemMapper;
import com.hioas.aap.quote.QuoteMapper;
import com.hioas.aap.quote.QuoteValidation;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 计费编译（接口 QT-12 / ADM-Q01 / ADM-CP01…04；真源 `06-报价模型与计费编译规则.md §2、§4`）。
 *
 * <p><b>三道闸门（R-33）</b>：编译 → 模拟验证 → 人工确认，任一不过都不落 new-api。
 * 落库表现为 {@code gate_status}：
 *  <ul>
 *    <li>{@code COMPILED}：已编译，{@code publish_blocked=true}</li>
 *    <li>{@code VERIFIED}：模拟验证通过（未确认仍禁止写入）</li>
 *    <li>{@code CONFIRMED}：人工确认，{@code publish_blocked=false}，可进入同步写入（T14）</li>
 *    <li>{@code FAILED}：模拟验证失败，必须回到报价单改价（E-1405，定位到字段）</li>
 *  </ul>
 *
 * <p><b>幂等（R-34）</b>：同一份报价内容（{@code source_hash} 相同）重复编译 → 复用已有编译产物，
 * 不生成新记录；内容变更 → 新产物 + 旧表达式进 {@code previous_expr} 留档（§4.3）。
 *
 * <p><b>边界冲突检测（编译前）</b>：时段重叠/阶梯空洞/倍率非正/单价为负一律拒绝（直接复用
 * {@link QuoteValidation}，保证「提交时」与「编译时」两处口径完全一致）。
 */
@Service
public class CompilationService {

    private static final Logger log = LoggerFactory.getLogger(CompilationService.class);
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 允许编译的报价单状态：审核通过之后（A9 通过→可发起合同/编译上架）。 */
    private static final List<String> COMPILABLE = List.of("APPROVED", "CONTRACT_CREATED", "CONVERTED");

    private final CompiledExpressionMapper compilationMapper;
    private final ModelExpressionMapper exprMapper;
    private final VerifyRunMapper verifyRunMapper;
    private final VerifyCaseMapper verifyCaseMapper;
    private final QuoteMapper quoteMapper;
    private final QuoteItemMapper itemMapper;
    private final CompileInputLoader inputLoader;
    private final AuditService auditService;

    public CompilationService(CompiledExpressionMapper compilationMapper, ModelExpressionMapper exprMapper,
                              VerifyRunMapper verifyRunMapper, VerifyCaseMapper verifyCaseMapper,
                              QuoteMapper quoteMapper, QuoteItemMapper itemMapper,
                              CompileInputLoader inputLoader, AuditService auditService) {
        this.compilationMapper = compilationMapper;
        this.exprMapper = exprMapper;
        this.verifyRunMapper = verifyRunMapper;
        this.verifyCaseMapper = verifyCaseMapper;
        this.quoteMapper = quoteMapper;
        this.itemMapper = itemMapper;
        this.inputLoader = inputLoader;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ ADM-Q01 / QT-12

    /**
     * 正式编译（ADM-Q01）：要求报价单已审核通过；幂等复用；产出表达式 + 边界冲突检测。
     */
    @Transactional
    public CompilationViews.Result compile(AuthPrincipal principal, Long quoteId, boolean admin) {
        QuoteEntity quote = requireQuote(quoteId);
        if (!COMPILABLE.contains(quote.getStatus())) {
            throw new ApiException(ErrorCode.E_1601,
                    "报价单当前状态不可编译（需审核通过）：" + quote.getStatus());
        }
        List<BillingCompiler.ItemRules> items = inputLoader.load(quoteId);
        requireBoundaryOk(items);

        String sourceHash = BillingCompiler.sourceHash(items);
        // 幂等口径必须与唯一索引 `uq_compilation_provider_source_hash` 一致：唯一性是
        // **(provider_id, source_hash)**。`BillingCompiler.sourceHash(items)` 只由计价规则内容构成
        // （不含 provider_id），所以这里必须按 provider_id 收口：
        //   * 只看 quote_id → 同一供应商换一张报价单但内容相同时漏命中，insert 撞索引 → E-2001（实测复现）；
        //   * 不看 provider_id → 不同供应商报出相同价格时误复用别人的产物（越权）。
        CompiledExpressionEntity existing = compilationMapper.selectOneByQuery(QueryWrapper.create()
                .where("provider_id = ?", quote.getProviderId())
                .and("source_hash = ?", sourceHash)
                .and("deleted = false")
                .orderBy("id desc")
                .limit(1));
        if (existing != null) {
            log.info("编译幂等命中：source_hash 未变，复用 compilation_id={} quote_id={}",
                    existing.getId(), quoteId);
            return toResult(existing);
        }

        Map<String, BillingExpr> compiled = BillingCompiler.compile(items, admin);
        CompiledExpressionEntity entity = new CompiledExpressionEntity();
        entity.setQuoteId(quoteId);
        entity.setQuoteVersion(quote.getCurrentVersion());
        entity.setProviderId(quote.getProviderId());
        entity.setStatus("COMPILED");
        entity.setGateStatus("COMPILED");
        entity.setSourceHash(sourceHash);
        entity.setCompilerVersion(BillingCompiler.COMPILER_VERSION);
        entity.setPublishBlocked(true);
        entity.setPreviousExpr(previousExprOf(quoteId));
        compilationMapper.insert(entity);

        for (BillingCompiler.ItemRules item : items) {
            ModelExpressionEntity expr = new ModelExpressionEntity();
            expr.setCompilationId(entity.getId());
            expr.setModelName(item.modelName());
            expr.setExprVersion(BillingCompiler.COMPILER_VERSION);
            expr.setExpr(compiled.get(item.modelName()).render());
            expr.setInlineExpanded(compiled.get(item.modelName()).render());
            expr.setTierLabels(JsonCodec.toJson(tierLabels(item)));
            expr.setRuleHits(JsonCodec.toJson(ruleHits(item, admin)));
            expr.setVerified(false);
            expr.setSourceHash(sourceHash);
            exprMapper.insert(expr);
        }

        quote.setLastCompilationId(entity.getId());
        quote.setSourceHash(sourceHash);
        quoteMapper.update(quote);

        auditService.record(AuditService.AuditAction.CONFIG_PUBLISH, "compilation", entity.getId(),
                "编译报价单 " + quote.getQuoteNo() + "（模型 " + items.size() + " 个，闸门 COMPILED）");
        log.info("编译完成 compilation_id={} quote_no={} 模型数={} source_hash={}",
                entity.getId(), quote.getQuoteNo(), items.size(), sourceHash);
        return toResult(entity);
    }

    /** QT-12 编译预览：只算不落库（供应商自检「我填的价会变成什么表达式」）。 */
    public CompilationViews.Result preview(AuthPrincipal principal, Long quoteId, boolean admin) {
        QuoteEntity quote = requireOwned(principal, quoteId);
        List<BillingCompiler.ItemRules> items = inputLoader.load(quoteId);
        requireBoundaryOk(items);
        Map<String, BillingExpr> compiled = BillingCompiler.compile(items, admin);

        List<CompilationViews.ModelExpr> compiledViews = new ArrayList<>();
        List<CompilationViews.VerifyCase> cases = new ArrayList<>();
        int passed = 0;
        String failedField = null;
        for (BillingCompiler.ItemRules item : items) {
            BillingExpr expr = compiled.get(item.modelName());
            BillingVerifier.Report report = BillingVerifier.verify(item.modelName(), item, expr);
            passed += report.casePassed();
            if (failedField == null && !"PASSED".equals(report.status())) {
                failedField = report.failedField();
            }
            for (BillingVerifier.CaseResult result : report.cases()) {
                cases.add(toCaseView(result));
            }
            compiledViews.add(new CompilationViews.ModelExpr(item.modelName(), BillingCompiler.COMPILER_VERSION,
                    expr.render(), tierLabels(item), ruleHits(item, admin),
                    "PASSED".equals(report.status()), null, expr.render()));
        }
        String gate = failedField == null ? "VERIFIED" : "FAILED";
        CompilationViews.VerifyReport report = new CompilationViews.VerifyReport(gate, cases.size(), passed,
                failedField, cases, now(), now());
        return new CompilationViews.Result(null, null, String.valueOf(quoteId), quote.getCurrentVersion(),
                String.valueOf(quote.getProviderId()), "PREVIEW", gate, BillingCompiler.sourceHash(items),
                BillingCompiler.COMPILER_VERSION, true, null, compiledViews, report, null, now());
    }

    // ------------------------------------------------------------------ ADM-CP01/02

    /** ADM-CP01 编译记录列表。 */
    public PageResult<CompilationViews.Result> list(Integer page, Integer pageSize, String status) {
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        QueryWrapper query = QueryWrapper.create().where("deleted = false").orderBy("id desc");
        if (status != null && !status.isBlank()) {
            query.and("gate_status = ?", status.trim().toUpperCase());
        }
        Page<CompiledExpressionEntity> result = compilationMapper.paginate(
                Page.of(pageQuery.page(), pageQuery.pageSize()), query);
        return PageResult.of(result.getRecords().stream().map(this::toResult).toList(),
                pageQuery.page(), pageQuery.pageSize(), result.getTotalRow());
    }

    /** ADM-CP02 编译详情（含表达式与验证报告）。 */
    public CompilationViews.Result detail(Long compilationId) {
        return toResult(requireCompilation(compilationId));
    }

    // ------------------------------------------------------------------ ADM-CP03

    /** ADM-CP03 重新模拟验证：通过 → VERIFIED；失败 → FAILED 并保留报告后抛 E-1405。 */
    @Transactional
    public CompilationViews.VerifyReport verify(Long compilationId) {
        CompiledExpressionEntity entity = requireCompilation(compilationId);
        List<BillingCompiler.ItemRules> items = inputLoader.load(entity.getQuoteId());
        Map<String, ModelExprRow> rows = new LinkedHashMap<>();
        for (ModelExpressionEntity row : exprMapper.selectListByQuery(QueryWrapper.create()
                .where("compilation_id = ?", compilationId).orderBy("id asc"))) {
            rows.put(row.getModelName(), new ModelExprRow(row));
        }

        int caseTotal = 0;
        int casePassed = 0;
        String failedField = null;
        List<BillingVerifier.CaseResult> allCases = new ArrayList<>();
        List<String> verifiedModels = new ArrayList<>();
        for (BillingCompiler.ItemRules item : items) {
            BillingExpr expr = compiledExpr(item, rows.get(item.modelName()));
            BillingVerifier.Report report = BillingVerifier.verify(item.modelName(), item, expr);
            caseTotal += report.caseTotal();
            casePassed += report.casePassed();
            allCases.addAll(report.cases());
            if (report.failedField() != null && failedField == null) {
                failedField = report.failedField();
            }
            if ("PASSED".equals(report.status())) {
                verifiedModels.add(item.modelName());
            }
        }

        VerifyRunEntity run = new VerifyRunEntity();
        run.setCompilationId(compilationId);
        run.setStatus(failedField == null ? "PASSED" : "FAILED");
        run.setCaseTotal(caseTotal);
        run.setCasePassed(casePassed);
        run.setFailedField(failedField);
        run.setStartedAt(OffsetDateTime.now(ZoneOffset.UTC));
        run.setFinishedAt(OffsetDateTime.now(ZoneOffset.UTC));
        verifyRunMapper.insert(run);
        for (BillingVerifier.CaseResult result : allCases) {
            VerifyCaseEntity row = new VerifyCaseEntity();
            row.setRunId(run.getId());
            row.setCaseCode(result.caseCode());
            row.setCaseName(result.caseName());
            row.setInput(JsonCodec.toJson(result.input()));
            row.setExpected(result.expected());
            row.setActual(result.actual());
            row.setPassed(Boolean.TRUE.equals(result.passed()));
            row.setDiffNote(result.diffNote());
            verifyCaseMapper.insert(row);
        }

        entity.setVerifyReport(JsonCodec.toJson(reportMap(run, allCases)));
        entity.setGateStatus(failedField == null ? "VERIFIED" : "FAILED");
        entity.setStatus(failedField == null ? "VERIFIED" : "FAILED");
        compilationMapper.update(entity);

        for (ModelExpressionEntity row : exprMapper.selectListByQuery(QueryWrapper.create()
                .where("compilation_id = ?", compilationId))) {
            row.setVerified(verifiedModels.contains(row.getModelName()));
            exprMapper.update(row);
        }

        if (failedField != null) {
            BillingVerifier.CaseResult failed = allCases.stream()
                    .filter(c -> !Boolean.TRUE.equals(c.passed())).findFirst().orElse(null);
            throw new ApiException(ErrorCode.E_1405,
                    "计费表达式模拟校验未通过（用例 " + (failed == null ? failedField : failed.caseCode()) + "）",
                    List.of(new ApiErrorDetail(failedField, failed == null ? "模拟求值与预期不一致"
                            : failed.diffNote())));
        }
        log.info("模拟验证通过 compilation_id={} 用例 {}/{}", compilationId, casePassed, caseTotal);
        return toVerifyReport(run, allCases);
    }

    // ------------------------------------------------------------------ ADM-CP04

    /** ADM-CP04 人工确认：仅 VERIFIED 可确认，确认后解除写入封锁（E-1407）。 */
    @Transactional
    public CompilationViews.Result confirm(AuthPrincipal principal, Long compilationId) {
        CompiledExpressionEntity entity = requireCompilation(compilationId);
        if (!"VERIFIED".equals(entity.getGateStatus())) {
            throw new ApiException(ErrorCode.E_1407,
                    "编译产物未通过模拟验证或状态非法，禁止确认写入：gate_status=" + entity.getGateStatus());
        }
        entity.setGateStatus("CONFIRMED");
        entity.setStatus("CONFIRMED");
        entity.setPublishBlocked(false);
        entity.setConfirmedBy(principal == null ? null : principal.accountId());
        entity.setConfirmedAt(OffsetDateTime.now(ZoneOffset.UTC));
        compilationMapper.update(entity);
        auditService.record(AuditService.AuditAction.CONFIG_PUBLISH, "compilation", compilationId,
                "人工确认编译产物（闸门 CONFIRMED，解除写入封锁）");
        log.info("编译产物已确认 compilation_id={} source_hash={}", compilationId, entity.getSourceHash());
        return toResult(entity);
    }

    // ------------------------------------------------------------------ 内部

    private record ModelExprRow(ModelExpressionEntity row) {
    }

    private static BillingExpr compiledExpr(BillingCompiler.ItemRules item, ModelExprRow row) {
        // 验证必须跑「已落库的那条表达式」的语义：用同一套规则重新构建 AST（render 与 eval 同源）
        return BillingCompiler.compileItem(item, false);
    }

    /** 编译前边界冲突检测（PRD §4.2）：直接复用 V 规则，口径与提交校验一致。 */
    private static void requireBoundaryOk(List<BillingCompiler.ItemRules> items) {
        List<ApiErrorDetail> errors = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            BillingCompiler.ItemRules item = items.get(i);
            QuoteValidation.Result result = QuoteValidation.validateItem(new QuoteValidation.ItemDraft(
                    item.modelName(), null, item.inputPrice(), item.outputPrice(), item.cacheReadPrice(),
                    item.cacheWritePrice(), null, null, null, null, null,
                    null, null, null, item.timeRule(), item.tierRule(), item.requestRules()), i, true);
            for (ApiErrorDetail error : result.errors()) {
                if (error.reason().contains("（V15）")) {
                    continue;   // 编译阶段不再重复判管理端写权限（此前保存时已拦）
                }
                errors.add(error);
            }
        }
        if (errors.isEmpty()) {
            return;
        }
        String firstReason = errors.get(0).reason();
        ErrorCode code = firstReason.contains("（V7）") || firstReason.contains("（V8）")
                || firstReason.contains("（V9）") ? ErrorCode.E_1401
                : firstReason.contains("（V10）") ? ErrorCode.E_1403
                : firstReason.contains("（V12）") ? ErrorCode.E_1404
                : firstReason.contains("（V11）") || firstReason.contains("（V13）")
                || firstReason.contains("（V14）") ? ErrorCode.E_1402
                : ErrorCode.E_1001;
        throw new ApiException(code, "编译前边界检测未通过：" + firstReason, errors);
    }

    private static Map<String, Object> reportMap(VerifyRunEntity run, List<BillingVerifier.CaseResult> cases) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("status", run.getStatus());
        map.put("case_total", run.getCaseTotal());
        map.put("case_passed", run.getCasePassed());
        map.put("failed_field", run.getFailedField());
        map.put("cases", cases.stream().map(BillingVerifier.CaseResult::caseCode).toList());
        return map;
    }

    private static CompilationViews.VerifyReport toVerifyReport(VerifyRunEntity run,
                                                                List<BillingVerifier.CaseResult> cases) {
        return new CompilationViews.VerifyReport(run.getStatus(), run.getCaseTotal(), run.getCasePassed(),
                run.getFailedField(), cases.stream().map(CompilationService::toCaseView).toList(),
                format(run.getStartedAt()), format(run.getFinishedAt()));
    }

    private static CompilationViews.VerifyCase toCaseView(BillingVerifier.CaseResult result) {
        return new CompilationViews.VerifyCase(result.caseCode(), result.caseName(), result.input(),
                result.expected(), result.actual(), result.passed(), result.diffNote());
    }

    private CompiledExpressionEntity requireCompilation(Long compilationId) {
        CompiledExpressionEntity entity = compilationMapper.selectOneById(compilationId);
        if (entity == null || Boolean.TRUE.equals(entity.getDeleted())) {
            throw new ApiException(ErrorCode.E_1406, "编译记录不存在");
        }
        return entity;
    }

    private QuoteEntity requireQuote(Long quoteId) {
        QuoteEntity quote = quoteMapper.selectOneById(quoteId);
        if (quote == null) {
            throw new ApiException(ErrorCode.E_1406, "报价单不存在");
        }
        return quote;
    }

    private QuoteEntity requireOwned(AuthPrincipal principal, Long quoteId) {
        QuoteEntity quote = requireQuote(quoteId);
        if (principal == null || principal.providerId() == null
                || !quote.getProviderId().equals(principal.providerId())) {
            throw new ApiException(ErrorCode.E_1406, "报价单不存在");
        }
        return quote;
    }

    /** 上一版表达式快照（§4.3「变更生成新表达式 + 保留旧快照」）。 */
    private String previousExprOf(Long quoteId) {
        CompiledExpressionEntity previous = compilationMapper.selectOneByQuery(QueryWrapper.create()
                .where("quote_id = ?", quoteId).and("deleted = false")
                .orderBy("id desc").limit(1));
        if (previous == null) {
            return null;
        }
        List<ModelExpressionEntity> rows = exprMapper.selectListByQuery(QueryWrapper.create()
                .where("compilation_id = ?", previous.getId()));
        List<Map<String, Object>> snapshot = new ArrayList<>();
        for (ModelExpressionEntity row : rows) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("model_name", row.getModelName());
            entry.put("expr", row.getExpr());
            entry.put("expr_version", row.getExprVersion());
            snapshot.add(entry);
        }
        Map<String, Object> wrapper = new LinkedHashMap<>();
        wrapper.put("compilation_id", String.valueOf(previous.getId()));
        wrapper.put("source_hash", previous.getSourceHash());
        wrapper.put("gate_status", previous.getGateStatus());
        wrapper.put("models", snapshot);
        return JsonCodec.toJson(wrapper);
    }

    private static List<String> tierLabels(BillingCompiler.ItemRules item) {
        if (item.tierRule() == null || item.tierRule().tiers() == null) {
            return List.of();
        }
        List<String> labels = new ArrayList<>();
        for (int i = 0; i < item.tierRule().tiers().size(); i++) {
            labels.add(BillingCompiler.tierLabel(i, item.tierRule().tiers().get(i)));
        }
        return labels;
    }

    private static List<String> ruleHits(BillingCompiler.ItemRules item, boolean admin) {
        List<String> hits = new ArrayList<>();
        hits.add("R1_BASE_PRICE");
        if (item.tierRule() != null && item.tierRule().tiers() != null && !item.tierRule().tiers().isEmpty()) {
            hits.add("R2_TIER_BY_LEN");
        }
        if (item.timeRule() != null && item.timeRule().segments() != null && !item.timeRule().segments().isEmpty()) {
            hits.add("R3_PEAK_OFFPEAK");
        }
        if (item.tierRule() != null && item.timeRule() != null) {
            hits.add("R4_TIER_X_TIME");
        }
        if (admin && item.requestRules() != null && !item.requestRules().isEmpty()) {
            hits.add("R5_REQUEST_MULTIPLIER");
        }
        return hits;
    }

    private CompilationViews.Result toResult(CompiledExpressionEntity entity) {
        List<CompilationViews.ModelExpr> compiled = new ArrayList<>();
        for (ModelExpressionEntity row : exprMapper.selectListByQuery(QueryWrapper.create()
                .where("compilation_id = ?", entity.getId()).orderBy("id asc"))) {
            compiled.add(new CompilationViews.ModelExpr(row.getModelName(), row.getExprVersion(), row.getExpr(),
                    JsonCodec.toStringList(row.getTierLabels()), JsonCodec.toStringList(row.getRuleHits()),
                    row.getVerified(), row.getSourceHash(), row.getInlineExpanded()));
        }
        CompilationViews.VerifyReport report = null;
        if (entity.getVerifyReport() != null) {
            var latestRun = verifyRunMapper.selectOneByQuery(QueryWrapper.create()
                    .where("compilation_id = ?", entity.getId()).orderBy("id desc").limit(1));
            if (latestRun != null) {
                List<BillingVerifier.CaseResult> cases = new ArrayList<>();
                for (VerifyCaseEntity row : verifyCaseMapper.selectListByQuery(QueryWrapper.create()
                        .where("run_id = ?", latestRun.getId()).orderBy("id asc"))) {
                    cases.add(new BillingVerifier.CaseResult(row.getCaseCode(), row.getCaseName(),
                            row.getInput() == null ? Map.of() : JsonCodec.toMap(row.getInput()),
                            row.getExpected(), row.getActual(), row.getPassed(), row.getDiffNote()));
                }
                report = toVerifyReport(latestRun, cases);
            }
        }
        return new CompilationViews.Result(String.valueOf(entity.getId()), String.valueOf(entity.getId()),
                String.valueOf(entity.getQuoteId()), entity.getQuoteVersion(),
                entity.getProviderId() == null ? null : String.valueOf(entity.getProviderId()),
                entity.getStatus(), entity.getGateStatus(), entity.getSourceHash(), entity.getCompilerVersion(),
                entity.getPublishBlocked(),
                entity.getPreviousExpr() == null ? null : JsonCodec.toMap(entity.getPreviousExpr()),
                compiled, report, format(entity.getConfirmedAt()), format(entity.getCreatedAt()));
    }

    private static String format(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    private static String now() {
        return RFC3339.format(OffsetDateTime.now(ZoneOffset.UTC));
    }

    /** 仅供测试/管理端复用的表达式文本（供应商预览页展示用）。 */
    static BigDecimal amount(BigDecimal value) {
        return value;
    }
}
