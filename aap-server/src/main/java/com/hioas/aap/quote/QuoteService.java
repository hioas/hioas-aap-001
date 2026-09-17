package com.hioas.aap.quote;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.credential.CredentialEntity;
import com.hioas.aap.credential.CredentialMapper;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.provider.ProviderEntity;
import com.hioas.aap.provider.ProviderMapper;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 报价单与明细定价（接口 QT-01…11；真源 `10-报价与合同结算PRD.md`）。
 *
 * <p>状态机（10-PRD §4.1）：`DRAFT`→`SUBMITTED`→（撤回 `DRAFT` | `REVIEWING`）→（`REJECTED`→`DRAFT` | `APPROVED`）；
 * `VOID` 作废。可编辑状态仅 `DRAFT`/`REJECTED`。
 *
 * <p>跨模块口径：
 * <ul>
 *   <li>QT-02 前置（E-1602）：凭证必须已通过预检（ACTIVE）**且**检测结论为通过（`detection_status=PASS`）——报价只能报已验过的通道。</li>
 *   <li>V17：明细行的 model_name 必须在凭证检测通过的模型清单内。</li>
 *   <li>V15：`request_rules` 仅管理端可写（供应商写 → E-1001，字段级定位到 `request_rules`）。</li>
 * </ul>
 */
@Service
public class QuoteService {

    private static final Logger log = LoggerFactory.getLogger(QuoteService.class);
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 供应商可编辑的报价单状态。 */
    private static final Set<String> EDITABLE = Set.of("DRAFT", "REJECTED");
    /** 供应商可提交的状态。 */
    private static final Set<String> SUBMITTABLE = Set.of("DRAFT", "REJECTED");
    /** 可作废的状态（10-PRD §4.1：DRAFT 可作废、SUBMITTED 可撤回/作废）。 */
    private static final Set<String> VOIDABLE = Set.of("DRAFT", "SUBMITTED", "REJECTED");

    private final QuoteMapper quoteMapper;
    private final QuoteItemMapper itemMapper;
    private final QuoteVersionMapper versionMapper;
    private final PriceTimeRuleMapper timeRuleMapper;
    private final PriceTimeSegmentMapper segmentMapper;
    private final PriceTierRuleMapper tierRuleMapper;
    private final PriceTierMapper tierMapper;
    private final PriceRequestRuleMapper requestRuleMapper;
    private final CredentialMapper credentialMapper;
    private final ProviderMapper providerMapper;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;

    public QuoteService(QuoteMapper quoteMapper, QuoteItemMapper itemMapper, QuoteVersionMapper versionMapper,
                        PriceTimeRuleMapper timeRuleMapper, PriceTimeSegmentMapper segmentMapper,
                        PriceTierRuleMapper tierRuleMapper, PriceTierMapper tierMapper,
                        PriceRequestRuleMapper requestRuleMapper, CredentialMapper credentialMapper,
                        ProviderMapper providerMapper, DocNoGenerator docNoGenerator, AuditService auditService) {
        this.quoteMapper = quoteMapper;
        this.itemMapper = itemMapper;
        this.versionMapper = versionMapper;
        this.timeRuleMapper = timeRuleMapper;
        this.segmentMapper = segmentMapper;
        this.tierRuleMapper = tierRuleMapper;
        this.tierMapper = tierMapper;
        this.requestRuleMapper = requestRuleMapper;
        this.credentialMapper = credentialMapper;
        this.providerMapper = providerMapper;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
    }

    // ------------------------------------------------------------------ 命令模型

    /** 创建报价单命令（客户端 body：name/provider_id/credential_id + 可选有效期与币种）。 */
    public record CreateCommand(String name, Long credentialId, String currency,
                                OffsetDateTime validFrom, OffsetDateTime validTo, String remark) {
    }

    /** 明细行（仅模型名，单价在下一步设置）。 */
    public record ItemRef(String modelName, String modelAlias) {
    }

    /** 保存单行定价命令。 */
    public record SaveItemCommand(BigDecimal inputPrice, BigDecimal outputPrice,
                                  BigDecimal cacheReadPrice, BigDecimal cacheWritePrice,
                                  BigDecimal cacheWrite1hPrice,
                                  BigDecimal imageInputPrice, BigDecimal audioInputPrice,
                                  BigDecimal imageOutputPrice, BigDecimal audioOutputPrice,
                                  String tier, String billingMode, String note, String modelAlias,
                                  QuoteValidation.TimeRule timeRule, QuoteValidation.TierRule tierRule,
                                  List<QuoteValidation.RequestRule> requestRules) {
    }

    // ------------------------------------------------------------------ QT-01

    /** QT-01 列表（status 支持逗号分隔多值，客户端 chip → 值集合）。 */
    public PageResult<QuoteViews.Row> list(AuthPrincipal principal, Integer page, Integer pageSize, String status) {
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        QueryWrapper query = QueryWrapper.create()
                .where("provider_id = ?", principal.providerId())
                .and("deleted = false")
                .orderBy("updated_at desc, id desc");
        if (status != null && !status.isBlank()) {
            List<String> values = new ArrayList<>();
            for (String part : status.split(",")) {
                String value = part.trim().toUpperCase();
                if (!value.isEmpty()) {
                    values.add(value);
                }
            }
            if (!values.isEmpty()) {
                query.and("status in (" + String.join(",", values.stream().map(v -> "?").toList()) + ")",
                        values.toArray());
            }
        }
        Page<QuoteEntity> result = quoteMapper.paginate(Page.of(pageQuery.page(), pageQuery.pageSize()), query);
        return PageResult.of(result.getRecords().stream().map(this::toRow).toList(),
                pageQuery.page(), pageQuery.pageSize(), result.getTotalRow());
    }

    // ------------------------------------------------------------------ QT-02

    /** QT-02 创建报价单（DRAFT）。 */
    @Transactional
    public QuoteViews.Created create(AuthPrincipal principal, CreateCommand command) {
        if (command.credentialId() == null) {
            throw new ApiException(ErrorCode.E_1001, "请选择接入凭证", List.of(
                    new ApiErrorDetail("credential_id", "credential_id 必填")));
        }
        CredentialEntity credential = credentialMapper.selectOneById(command.credentialId());
        if (credential == null || !credential.getProviderId().equals(principal.providerId())) {
            throw new ApiException(ErrorCode.E_1406, "凭证不存在");
        }
        // E-1602 报价前置：预检通过 + 检测通过
        if (!"ACTIVE".equals(credential.getStatus()) || !"PASS".equals(credential.getDetectionStatus())) {
            throw new ApiException(ErrorCode.E_1602,
                    "凭证尚未通过检测，暂不能报价（当前 凭证状态=" + credential.getStatus()
                            + "，检测状态=" + credential.getDetectionStatus() + "）");
        }
        QuoteEntity quote = new QuoteEntity();
        quote.setQuoteNo(docNoGenerator.quoteNo());
        quote.setProviderId(principal.providerId());
        quote.setCredentialId(credential.getId());
        quote.setName(command.name());
        quote.setStatus("DRAFT");
        quote.setCurrentVersion(1);
        // 币种默认 USD（10-PRD §3.1）；设计样例为 CNY —— 服务端以 PRD 为默认，允许请求显式覆盖
        quote.setCurrency(command.currency() == null || command.currency().isBlank()
                ? "USD" : command.currency().toUpperCase());
        quote.setValidFrom(command.validFrom());
        quote.setValidTo(command.validTo());
        quote.setItemCount(0);
        quote.setRemark(command.remark());
        quoteMapper.insert(quote);
        auditService.record(AuditService.AuditAction.QUOTE_CREATE, "quote", quote.getId(),
                "创建报价单 " + quote.getQuoteNo());
        log.info("报价单创建 quote_no={} provider_id={} credential_id={}",
                quote.getQuoteNo(), quote.getProviderId(), credential.getId());
        return new QuoteViews.Created(String.valueOf(quote.getId()), String.valueOf(quote.getId()),
                quote.getQuoteNo(), quote.getStatus(), List.of());
    }

    // ------------------------------------------------------------------ QT-03

    /** QT-03 详情（报价单 + 明细行 + 规则）。 */
    public QuoteViews.Detail detail(AuthPrincipal principal, Long quoteId) {
        QuoteEntity quote = requireOwned(principal, quoteId);
        List<QuoteViews.Item> items = items(quoteId);
        return toDetail(quote, items, List.of());
    }

    // ------------------------------------------------------------------ QT-04

    /** QT-04 作废（客户端「删除」按钮；PRD 口径为 VOID，冲突已记清单备注）。 */
    @Transactional
    public void voidQuote(AuthPrincipal principal, Long quoteId, String reason) {
        QuoteEntity quote = requireOwned(principal, quoteId);
        if (!VOIDABLE.contains(quote.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "当前状态不可作废：" + quote.getStatus());
        }
        String before = quote.getStatus();
        quote.setStatus("VOID");
        // 作废 ≠ 软删除：记录保留（状态终态 VOID，可审计、可按 status=VOID 查询），
        // 但客户端全部筛选 chip 都不含 VOID，因此对用户表现为「已从列表消失」。
        // 取舍理由：作废是 10-PRD §4.1 的状态机终态，抹掉记录会破坏 A13（全状态流转可审计）。
        quoteMapper.update(quote);
        auditService.record(AuditService.AuditAction.QUOTE_VOID, "quote", quoteId,
                "作废报价单（" + before + "→VOID）"
                        + (reason == null || reason.isBlank() ? "" : "：" + reason),
                java.util.Map.of("status", before), java.util.Map.of("status", "VOID"), "NORMAL");
        log.info("报价单作废 quote_no={} {}→VOID", quote.getQuoteNo(), before);
    }

    // ------------------------------------------------------------------ QT-05/06/07

    /** QT-05 写入明细行（只带模型名；重复模型名拒绝 V2）。 */
    @Transactional
    public QuoteViews.Items setItems(AuthPrincipal principal, Long quoteId, List<ItemRef> refs) {
        QuoteEntity quote = requireEditable(principal, quoteId);
        if (refs == null || refs.isEmpty()) {
            throw new ApiException(ErrorCode.E_1001, "请至少选择一个模型", List.of(
                    new ApiErrorDetail("items", "items 不能为空（V1）")));
        }
        Set<String> seen = new LinkedHashSet<>();
        List<ApiErrorDetail> errors = new ArrayList<>();
        for (int i = 0; i < refs.size(); i++) {
            String name = refs.get(i).modelName() == null ? "" : refs.get(i).modelName().trim();
            if (name.isEmpty()) {
                errors.add(new ApiErrorDetail("items[" + i + "].model_name", "模型名不能为空"));
            } else if (!seen.add(name)) {
                errors.add(new ApiErrorDetail("items[" + i + "].model_name", "模型名重复：" + name + "（V2）"));
            }
        }
        if (!errors.isEmpty()) {
            throw new ApiException(ErrorCode.E_1001, errors.get(0).reason(), errors);
        }
        for (String modelName : seen) {
            QuoteItemEntity existing = itemMapper.selectOneByQuery(QueryWrapper.create()
                    .where("quote_id = ?", quoteId)
                    .and("model_name = ?", modelName)
                    .and("deleted = false")
                    .limit(1));
            if (existing == null) {
                QuoteItemEntity item = new QuoteItemEntity();
                item.setQuoteId(quoteId);
                item.setModelName(modelName);
                item.setCompileStatus("NOT_COMPILED");
                itemMapper.insert(item);
            }
        }
        long count = itemMapper.selectCountByQuery(QueryWrapper.create()
                .where("quote_id = ?", quoteId).and("deleted = false"));
        quote.setItemCount((int) count);
        quoteMapper.update(quote);
        return new QuoteViews.Items(items(quoteId), (int) count, List.of());
    }

    /** QT-06 明细行列表。 */
    public QuoteViews.Items listItems(AuthPrincipal principal, Long quoteId) {
        requireOwned(principal, quoteId);
        List<QuoteViews.Item> items = items(quoteId);
        return new QuoteViews.Items(items, items.size(), List.of());
    }

    /** QT-07 单行详情。 */
    public QuoteViews.Item getItem(AuthPrincipal principal, Long itemId) {
        QuoteItemEntity item = itemMapper.selectOneById(itemId);
        if (item == null) {
            throw new ApiException(ErrorCode.E_1406, "明细行不存在");
        }
        requireOwned(principal, item.getQuoteId());
        return toItem(item, List.of());
    }

    // ------------------------------------------------------------------ QT-08

    /** QT-08 保存单行定价（If-Match 可选：给了就做乐观锁校验）。 */
    @Transactional
    public QuoteViews.Item saveItem(AuthPrincipal principal, Long itemId, SaveItemCommand command,
                                    String ifMatch, boolean admin) {
        QuoteItemEntity item = itemMapper.selectOneById(itemId);
        if (item == null) {
            throw new ApiException(ErrorCode.E_1406, "明细行不存在");
        }
        QuoteEntity quote = requireEditable(principal, item.getQuoteId());
        if (ifMatch != null && !ifMatch.isBlank()) {
            String expected = ifMatch.replace("\"", "").trim();
            if (!expected.equals(String.valueOf(item.getVersion()))) {
                throw new ApiException(ErrorCode.E_1104,
                        "明细行已被其他会话修改（当前版本 " + item.getVersion() + "），请刷新后重试");
            }
        }

        QuoteValidation.ItemDraft draft = toDraft(item, command);
        QuoteValidation.Result validation = QuoteValidation.validateItem(draft, -1, admin);
        // 错误码优先级：规则族（V7–V14 → E-1401/E-1402/E-1403/E-1404）> 通用参数校验（E-1001）
        requireRuleCodesOk(validation);
        QuoteValidation.requireOk(validation, ErrorCode.E_1001);

        item.setModelAlias(command.modelAlias() == null ? item.getModelAlias() : command.modelAlias());
        item.setInputPrice(command.inputPrice());
        item.setOutputPrice(command.outputPrice());
        item.setCacheReadPrice(command.cacheReadPrice());
        item.setCacheWritePrice(command.cacheWritePrice());
        item.setCacheWrite1hPrice(command.cacheWrite1hPrice());
        item.setImageInputPrice(command.imageInputPrice());
        item.setImageOutputPrice(command.imageOutputPrice());
        item.setAudioInputPrice(command.audioInputPrice());
        item.setAudioOutputPrice(command.audioOutputPrice());
        item.setTierLabel(command.tier());
        item.setBillingMode(command.billingMode());
        item.setNote(command.note());
        itemMapper.update(item);

        saveTimeRule(item.getId(), command.timeRule());
        saveTierRule(item.getId(), command.tierRule(), admin);
        saveRequestRules(item.getId(), command.requestRules());

        // 规则变更后报价内容已变 → 报价单 source_hash 失效（T09 编译幂等的依据）
        quote.setSourceHash(null);
        quoteMapper.update(quote);
        return toItem(itemMapper.selectOneById(itemId), validation.warnings());
    }

    // ------------------------------------------------------------------ QT-09/10/11

    /** QT-09 提交（V1–V17 全量校验）。 */
    @Transactional
    public QuoteViews.Detail submit(AuthPrincipal principal, Long quoteId) {
        QuoteEntity quote = requireOwned(principal, quoteId);
        if (!SUBMITTABLE.contains(quote.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "当前状态不可提交：" + quote.getStatus());
        }
        List<QuoteItemEntity> rows = itemEntities(quoteId);
        Set<String> detected = detectedModels(quote.getCredentialId());
        List<QuoteValidation.ItemDraft> drafts = new ArrayList<>();
        for (QuoteItemEntity row : rows) {
            QuoteValidation.TimeRule timeRule = loadTimeRule(row.getId());
            QuoteValidation.TierRule tierRule = loadTierRule(row.getId());
            drafts.add(toDraft(row, timeRule, tierRule, new ArrayList<>()));
        }
        QuoteValidation.Result validation = QuoteValidation.validateForSubmit(
                drafts, quote.getValidFrom(), quote.getValidTo(), detected, false);
        if (!validation.ok()) {
            // 错误码优先级：V17 前置条件（E-1602）> 规则族（E-1401/E-1402/E-1403/E-1404）> 通用参数校验（E-1001）
            var v17 = validation.errors().stream()
                    .filter(e -> e.reason().contains("（V17）")).findFirst();
            if (v17.isPresent()) {
                throw new ApiException(ErrorCode.E_1602, v17.get().reason(), validation.errors());
            }
            requireRuleCodesOk(validation);
            var first = validation.errors().get(0);
            throw new ApiException(ErrorCode.E_1001, first.reason(), validation.errors());
        }

        String before = quote.getStatus();
        quote.setStatus("SUBMITTED");
        quote.setSubmittedAt(OffsetDateTime.now(ZoneOffset.UTC));
        quote.setSubmittedBy(principal == null ? null : principal.accountId());
        quote.setItemCount(rows.size());
        quoteMapper.update(quote);

        // 版本快照（不可变 C9）：提交即冻结当前内容
        QuoteVersionEntity snapshot = new QuoteVersionEntity();
        snapshot.setQuoteId(quoteId);
        snapshot.setVersionNo(quote.getCurrentVersion());
        snapshot.setSnapshot(JsonCodec.toJson(snapshotMap(quote, rows)));
        versionMapper.insert(snapshot);
        quote.setCurrentVersion(quote.getCurrentVersion() + 1);
        quoteMapper.update(quote);

        auditService.record(AuditService.AuditAction.QUOTE_SUBMIT, "quote", quoteId,
                "提交报价（" + before + "→SUBMITTED，version=" + snapshot.getVersionNo() + "）",
                java.util.Map.of("status", before), java.util.Map.of("status", "SUBMITTED"), "NORMAL");
        log.info("报价单提交 quote_no={} version={} items={}",
                quote.getQuoteNo(), snapshot.getVersionNo(), rows.size());
        List<QuoteViews.Item> items = items(quoteId);
        return toDetail(quote, items, validation.warnings());
    }

    /** QT-10 撤回（A6 仅审核前可撤回）。 */
    @Transactional
    public QuoteViews.Detail withdraw(AuthPrincipal principal, Long quoteId) {
        QuoteEntity quote = requireOwned(principal, quoteId);
        if (!"SUBMITTED".equals(quote.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "仅「已提交」可撤回，当前：" + quote.getStatus());
        }
        quote.setStatus("DRAFT");
        quote.setWithdrawnAt(OffsetDateTime.now(ZoneOffset.UTC));
        quoteMapper.update(quote);
        auditService.record(AuditService.AuditAction.QUOTE_WITHDRAW, "quote", quoteId, "撤回报价",
                java.util.Map.of("status", "SUBMITTED"), java.util.Map.of("status", "DRAFT"), "NORMAL");
        return toDetail(quote, items(quoteId), List.of());
    }

    /** QT-11 版本列表。 */
    public PageResult<QuoteViews.Version> versions(AuthPrincipal principal, Long quoteId,
                                                   Integer page, Integer pageSize) {
        requireOwned(principal, quoteId);
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        Page<QuoteVersionEntity> result = versionMapper.paginate(Page.of(pageQuery.page(), pageQuery.pageSize()),
                QueryWrapper.create().where("quote_id = ?", quoteId).orderBy("version_no desc"));
        List<QuoteViews.Version> items = new ArrayList<>();
        for (QuoteVersionEntity entity : result.getRecords()) {
            items.add(new QuoteViews.Version(String.valueOf(entity.getId()), String.valueOf(quoteId),
                    entity.getVersionNo(), JsonCodec.toMap(entity.getSnapshot()), entity.getSourceHash(),
                    format(entity.getCreatedAt())));
        }
        return PageResult.of(items, pageQuery.page(), pageQuery.pageSize(), result.getTotalRow());
    }

    // ------------------------------------------------------------------ 内部：读取与转换

    /** 检测通过的模型清单（V17 依据）；凭证没有模型清单时返回空集表示「无依据可校验」。 */
    public Set<String> detectedModels(Long credentialId) {
        if (credentialId == null) {
            return Set.of();
        }
        CredentialEntity credential = credentialMapper.selectOneById(credentialId);
        if (credential == null || credential.getModelList() == null) {
            return Set.of();
        }
        Set<String> models = new HashSet<>();
        try {
            List<Map<String, Object>> raw = JsonCodec.fromJson(credential.getModelList(),
                    new tools.jackson.core.type.TypeReference<>() {
                    });
            if (raw != null) {
                for (Map<String, Object> entry : raw) {
                    Object name = entry.get("model_name");
                    if (name != null) {
                        models.add(String.valueOf(name));
                    }
                }
            }
        } catch (RuntimeException e) {
            log.warn("解析凭证模型清单失败 credential_id={} err={}", credentialId, e.getMessage());
        }
        return models;
    }

    private List<QuoteViews.Item> items(Long quoteId) {
        List<QuoteViews.Item> views = new ArrayList<>();
        for (QuoteItemEntity row : itemEntities(quoteId)) {
            views.add(toItem(row, List.of()));
        }
        return views;
    }

    private List<QuoteItemEntity> itemEntities(Long quoteId) {
        return itemMapper.selectListByQuery(QueryWrapper.create()
                .where("quote_id = ?", quoteId)
                .and("deleted = false")
                .orderBy("id asc"));
    }

    private QuoteViews.Row toRow(QuoteEntity quote) {
        return new QuoteViews.Row(String.valueOf(quote.getId()), String.valueOf(quote.getId()),
                quote.getName(), quote.getName(), quote.getQuoteNo(), quote.getStatus(), quote.getCurrency(),
                quote.getItemCount(), List.of(), null, format(quote.getUpdatedAt()), format(quote.getCreatedAt()),
                quote.getContractId() == null ? null : String.valueOf(quote.getContractId()),
                format(quote.getValidFrom()), format(quote.getValidTo()),
                quote.getCredentialId() == null ? null : String.valueOf(quote.getCredentialId()));
    }

    private QuoteViews.Detail toDetail(QuoteEntity quote, List<QuoteViews.Item> items, List<String> warnings) {
        return new QuoteViews.Detail(String.valueOf(quote.getId()), String.valueOf(quote.getId()),
                quote.getQuoteNo(), quote.getName(), quote.getName(),
                String.valueOf(quote.getProviderId()),
                quote.getCredentialId() == null ? null : String.valueOf(quote.getCredentialId()),
                quote.getStatus(), quote.getCurrentVersion(), quote.getCurrency(),
                format(quote.getValidFrom()), format(quote.getValidTo()), quote.getItemCount(),
                quote.getRemark(), quote.getRejectReasonCode(), quote.getRejectReasonText(),
                format(quote.getSubmittedAt()), format(quote.getReviewedAt()),
                quote.getContractId() == null ? null : String.valueOf(quote.getContractId()),
                quote.getSourceHash(), items.size(), items, null,
                format(quote.getUpdatedAt()), format(quote.getCreatedAt()),
                quote.getVersion(), warnings);
    }

    private QuoteViews.Item toItem(QuoteItemEntity item, List<String> warnings) {
        return new QuoteViews.Item(String.valueOf(item.getId()), String.valueOf(item.getId()),
                String.valueOf(item.getQuoteId()), String.valueOf(item.getQuoteId()),
                item.getModelName(), item.getModelName(), item.getModelAlias(),
                item.getInputPrice(), item.getOutputPrice(), item.getCacheReadPrice(),
                item.getCacheWritePrice(), item.getCacheWrite1hPrice(),
                item.getImageInputPrice(), item.getImageOutputPrice(),
                item.getAudioInputPrice(), item.getAudioOutputPrice(),
                item.getTierLabel(), item.getBillingMode(), item.getCompileStatus(), item.getNote(),
                toTimeRuleView(loadTimeRule(item.getId())), toTierRuleView(loadTierRule(item.getId())),
                loadRequestRules(item.getId()).stream().map(QuoteService::toRequestRuleView).toList(),
                format(item.getCreatedAt()), format(item.getUpdatedAt()), item.getVersion(),
                warnings == null || warnings.isEmpty() ? null : warnings);
    }

    private QuoteValidation.ItemDraft toDraft(QuoteItemEntity item, SaveItemCommand command) {
        return new QuoteValidation.ItemDraft(item.getModelName(),
                command.modelAlias() == null ? item.getModelAlias() : command.modelAlias(),
                command.inputPrice(), command.outputPrice(), command.cacheReadPrice(),
                command.cacheWritePrice(), command.cacheWrite1hPrice(),
                command.imageInputPrice(), command.audioInputPrice(),
                command.imageOutputPrice(), command.audioOutputPrice(),
                command.tier(), command.billingMode(), command.note(),
                command.timeRule(), command.tierRule(), command.requestRules());
    }

    private QuoteValidation.ItemDraft toDraft(QuoteItemEntity item, QuoteValidation.TimeRule timeRule,
                                              QuoteValidation.TierRule tierRule,
                                              List<QuoteValidation.RequestRule> requestRules) {
        return new QuoteValidation.ItemDraft(item.getModelName(), item.getModelAlias(),
                item.getInputPrice(), item.getOutputPrice(), item.getCacheReadPrice(),
                item.getCacheWritePrice(), item.getCacheWrite1hPrice(),
                item.getImageInputPrice(), item.getAudioInputPrice(),
                item.getImageOutputPrice(), item.getAudioOutputPrice(),
                item.getTierLabel(), item.getBillingMode(), item.getNote(),
                timeRule, tierRule, requestRules);
    }

    private Map<String, Object> snapshotMap(QuoteEntity quote, List<QuoteItemEntity> rows) {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("quote_no", quote.getQuoteNo());
        snapshot.put("status", "SUBMITTED");
        snapshot.put("currency", quote.getCurrency());
        snapshot.put("valid_from", format(quote.getValidFrom()));
        snapshot.put("valid_to", format(quote.getValidTo()));
        List<Map<String, Object>> items = new ArrayList<>();
        for (QuoteItemEntity row : rows) {
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("model_name", row.getModelName());
            QuoteValidation.priceMap(toDraft(row, loadTimeRule(row.getId()), loadTierRule(row.getId()), List.of()))
                    .forEach((key, value) -> entry.put(key, value == null ? null : value.toPlainString()));
            entry.put("tier", row.getTierLabel());
            entry.put("billing_mode", row.getBillingMode());
            items.add(entry);
        }
        snapshot.put("items", items);
        return snapshot;
    }

    // ------------------------------------------------------------------ 内部：规则读写

    private void saveTimeRule(Long itemId, QuoteValidation.TimeRule rule) {
        segmentMapper.deleteByQuery(QueryWrapper.create().where("time_rule_id in "
                + "(select id from aap_price_time_rule where item_id = ?)", itemId));
        timeRuleMapper.deleteByQuery(QueryWrapper.create().where("item_id = ?", itemId));
        if (rule == null) {
            return;
        }
        PriceTimeRuleEntity entity = new PriceTimeRuleEntity();
        entity.setItemId(itemId);
        entity.setTz(rule.tz() == null ? "Asia/Shanghai" : rule.tz());
        entity.setWeekdayScope(rule.weekdayScope() == null ? "ALL" : rule.weekdayScope());
        entity.setPeakMultiplier(rule.peakMultiplier());
        entity.setOffpeakMultiplier(rule.offpeakMultiplier());
        entity.setPeakPriceOverride(rule.peakPriceOverride());
        timeRuleMapper.insert(entity);
        int seq = 0;
        for (QuoteValidation.Segment segment : rule.segments() == null ? List.<QuoteValidation.Segment>of()
                : rule.segments()) {
            PriceTimeSegmentEntity row = new PriceTimeSegmentEntity();
            row.setTimeRuleId(entity.getId());
            row.setStartTime(LocalTime.parse(segment.start()));
            row.setEndTime(LocalTime.parse(segment.end()));
            row.setSeq(seq++);
            segmentMapper.insert(row);
        }
    }

    /** 阶梯规则属于报价定价本身，供应商可写；**仅 request_rules 受 V15 限制（管理端专属）**。 */
    private void saveTierRule(Long itemId, QuoteValidation.TierRule rule, boolean admin) {
        List<PriceTierRuleEntity> existing = tierRuleMapper.selectListByQuery(
                QueryWrapper.create().where("item_id = ?", itemId));
        for (PriceTierRuleEntity row : existing) {
            tierMapper.deleteByQuery(QueryWrapper.create().where("tier_rule_id = ?", row.getId()));
        }
        tierRuleMapper.deleteByQuery(QueryWrapper.create().where("item_id = ?", itemId));
        if (rule == null) {
            return;
        }
        PriceTierRuleEntity entity = new PriceTierRuleEntity();
        entity.setItemId(itemId);
        entity.setTierField(rule.tierField() == null ? QuoteValidation.TIER_FIELD_LEN : rule.tierField());
        entity.setPriceStrategy(rule.priceStrategy() == null ? QuoteValidation.STRATEGY_OVERRIDE : rule.priceStrategy());
        tierRuleMapper.insert(entity);
        int seq = 0;
        for (QuoteValidation.Tier tier : rule.tiers() == null ? List.<QuoteValidation.Tier>of() : rule.tiers()) {
            PriceTierEntity row = new PriceTierEntity();
            row.setTierRuleId(entity.getId());
            row.setSeq(seq++);
            row.setMinValue(tier.min());
            row.setMaxValue(tier.max());
            row.setLabel(tier.label());
            row.setInputPrice(tier.inputPrice());
            row.setOutputPrice(tier.outputPrice());
            row.setCacheReadPrice(tier.cacheReadPrice());
            row.setMultiplier(tier.multiplier());
            tierMapper.insert(row);
        }
    }

    private void saveRequestRules(Long itemId, List<QuoteValidation.RequestRule> rules) {
        requestRuleMapper.deleteByQuery(QueryWrapper.create().where("item_id = ?", itemId));
        if (rules == null) {
            return;
        }
        for (QuoteValidation.RequestRule rule : rules) {
            PriceRequestRuleEntity entity = new PriceRequestRuleEntity();
            entity.setItemId(itemId);
            entity.setWhenExpr(whenExpr(rule));
            entity.setMultiplier(rule.multiplier() == null ? BigDecimal.ONE : rule.multiplier());
            entity.setEnabled(true);
            requestRuleMapper.insert(entity);
        }
    }

    private static String whenExpr(QuoteValidation.RequestRule rule) {
        if (rule.whenExpr() != null && !rule.whenExpr().isBlank()) {
            return rule.whenExpr();
        }
        // 客户端发 {field,granularity,tz,op,value} → 归一为可读表达式
        List<String> parts = new ArrayList<>();
        if (rule.field() != null) {
            parts.add(rule.field());
        }
        if (rule.op() != null) {
            parts.add(rule.op());
        }
        if (rule.value() != null) {
            parts.add(rule.value());
        }
        return parts.isEmpty() ? "always" : String.join(" ", parts);
    }

    private QuoteValidation.TimeRule loadTimeRule(Long itemId) {
        PriceTimeRuleEntity rule = timeRuleMapper.selectOneByQuery(
                QueryWrapper.create().where("item_id = ?", itemId).limit(1));
        if (rule == null) {
            return null;
        }
        List<QuoteValidation.Segment> segments = new ArrayList<>();
        for (PriceTimeSegmentEntity row : segmentMapper.selectListByQuery(QueryWrapper.create()
                .where("time_rule_id = ?", rule.getId()).orderBy("seq asc"))) {
            segments.add(new QuoteValidation.Segment(String.valueOf(row.getStartTime()),
                    String.valueOf(row.getEndTime())));
        }
        return new QuoteValidation.TimeRule(rule.getTz(), rule.getWeekdayScope(), rule.getPeakMultiplier(),
                rule.getOffpeakMultiplier(), rule.getPeakPriceOverride(), segments);
    }

    private QuoteValidation.TierRule loadTierRule(Long itemId) {
        PriceTierRuleEntity rule = tierRuleMapper.selectOneByQuery(
                QueryWrapper.create().where("item_id = ?", itemId).limit(1));
        if (rule == null) {
            return null;
        }
        List<QuoteValidation.Tier> tiers = new ArrayList<>();
        for (PriceTierEntity row : tierMapper.selectListByQuery(QueryWrapper.create()
                .where("tier_rule_id = ?", rule.getId()).orderBy("seq asc"))) {
            tiers.add(new QuoteValidation.Tier(row.getSeq(), row.getMinValue(), row.getMaxValue(), row.getLabel(),
                    row.getInputPrice(), row.getOutputPrice(), row.getCacheReadPrice(), row.getMultiplier()));
        }
        return new QuoteValidation.TierRule(rule.getTierField(), rule.getPriceStrategy(), tiers);
    }

    private List<QuoteValidation.RequestRule> loadRequestRules(Long itemId) {
        List<QuoteValidation.RequestRule> rules = new ArrayList<>();
        for (PriceRequestRuleEntity row : requestRuleMapper.selectListByQuery(QueryWrapper.create()
                .where("item_id = ?", itemId).orderBy("id asc"))) {
            rules.add(new QuoteValidation.RequestRule(null, null, null, null, null,
                    row.getMultiplier(), row.getWhenExpr()));
        }
        return rules;
    }

    private static QuoteViews.TimeRule toTimeRuleView(QuoteValidation.TimeRule rule) {
        if (rule == null) {
            return null;
        }
        List<QuoteViews.Range> ranges = (rule.segments() == null ? List.<QuoteValidation.Segment>of()
                : rule.segments()).stream()
                .map(s -> new QuoteViews.Range(s.start(), s.end())).toList();
        return new QuoteViews.TimeRule(rule.tz(), rule.weekdayScope(), ranges, rule.peakMultiplier(),
                rule.offpeakMultiplier(), rule.peakPriceOverride());
    }

    private static QuoteViews.TierRule toTierRuleView(QuoteValidation.TierRule rule) {
        if (rule == null) {
            return null;
        }
        List<QuoteViews.Tier> tiers = (rule.tiers() == null ? List.<QuoteValidation.Tier>of() : rule.tiers())
                .stream().map(t -> new QuoteViews.Tier(t.seq(), t.min(), t.max(), t.label(),
                        t.inputPrice(), t.outputPrice(), t.cacheReadPrice(), t.multiplier())).toList();
        return new QuoteViews.TierRule(rule.tierField(), rule.priceStrategy(), tiers);
    }

    private static QuoteViews.RequestRule toRequestRuleView(QuoteValidation.RequestRule rule) {
        String expr = rule.whenExpr();
        return new QuoteViews.RequestRule(expr, expr, rule.multiplier(), Boolean.TRUE,
                rule.field(), rule.granularity(), rule.tz(), rule.op(), rule.value());
    }

    // ------------------------------------------------------------------ 内部：权限与错误码

    private QuoteEntity requireOwned(AuthPrincipal principal, Long quoteId) {
        QuoteEntity quote = quoteMapper.selectOneById(quoteId);
        if (quote == null || Boolean.TRUE.equals(quote.getDeleted())) {
            throw new ApiException(ErrorCode.E_1406, "报价单不存在");
        }
        if (principal == null || principal.providerId() == null
                || !quote.getProviderId().equals(principal.providerId())) {
            throw new ApiException(ErrorCode.E_1406, "报价单不存在");
        }
        return quote;
    }

    private QuoteEntity requireEditable(AuthPrincipal principal, Long quoteId) {
        QuoteEntity quote = requireOwned(principal, quoteId);
        if (!EDITABLE.contains(quote.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "当前状态不可编辑：" + quote.getStatus());
        }
        return quote;
    }

    /** V7/V8/V9 → E-1401，V10 → E-1403，V11–V14 → E-1402/E-1404（与清单里的错误码逐条对应）。 */
    private static void requireRuleCodesOk(QuoteValidation.Result validation) {
        List<ApiErrorDetail> errors = validation.errors();
        for (ApiErrorDetail error : errors) {
            if (error.reason().contains("（V7）") || error.reason().contains("（V8）") || error.reason().contains("（V9）")) {
                throw new ApiException(ErrorCode.E_1401, error.reason(), errors);
            }
            if (error.reason().contains("（V10）")) {
                throw new ApiException(ErrorCode.E_1403, error.reason(), errors);
            }
            if (error.reason().contains("（V12）")) {
                throw new ApiException(ErrorCode.E_1404, error.reason(), errors);
            }
            if (error.reason().contains("（V11）") || error.reason().contains("（V13）")
                    || error.reason().contains("（V14）")) {
                throw new ApiException(ErrorCode.E_1402, error.reason(), errors);
            }
        }
    }

    private static String format(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    /** 金额展示（报价单层无「总额」定义 → 保留工具方法给审查页复用）。 */
    static String amountText(BigDecimal value) {
        return value == null ? null : value.setScale(2, RoundingMode.HALF_UP).toPlainString();
    }
}
