package com.hioas.aap.quote;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 报价单接口（QT-01…11；真源 `10-报价与合同结算PRD.md` + `18-API设计OpenAPI.md`「Quote」Tag）。
 *
 * <p>请求体键名与客户端 `aap-client/src/api/quote.ts` 的构造体**逐字一致**（snake_case）；
 * 幂等由 {@code IdempotencyFilter} 统一处理（带 `Idempotency-Key` 时写接口保证同键同响应）。
 */
@RestController
@RequestMapping("/api/v1/quotes")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class QuoteController {

    private final QuoteService quoteService;

    public QuoteController(QuoteService quoteService) {
        this.quoteService = quoteService;
    }

    // ------------------------------------------------------------------ 请求体

    /** QT-02 创建报价单（客户端 buildQuotePayload：name/provider_id/credential_id）。 */
    public record CreateRequest(
            @Size(max = 64, message = "报价单名称最多 64 字") String name,
            String provider_id,
            String credential_id,
            String currency,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime valid_from,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime valid_to,
            @Size(max = 500, message = "备注最多 500 字") String remark) {
    }

    /** QT-05 明细行写入（客户端 buildItemsPayload：items[].model_name）。 */
    public record ItemsRequest(@NotEmpty(message = "请至少选择一个模型") List<ItemRef> items) {
    }

    /** 明细行引用。 */
    public record ItemRef(String model_name, String model_alias) {
    }

    /** 时段片段。 */
    public record RangeRequest(String start, String end) {
    }

    /** 时段规则（客户端与 Schema 都用 peak_ranges 命名）。 */
    public record TimeRuleRequest(String tz, String weekday_scope, List<RangeRequest> peak_ranges,
                                  BigDecimal peak_multiplier, BigDecimal offpeak_multiplier,
                                  BigDecimal peak_price_override) {
    }

    /** 阶梯档位。 */
    public record TierRequest(Integer seq, BigDecimal min, BigDecimal max, String label,
                              BigDecimal input_price, BigDecimal output_price, BigDecimal cache_read_price,
                              BigDecimal multiplier) {
    }

    /** 阶梯规则。 */
    public record TierRuleRequest(String tier_field, String price_strategy, List<TierRequest> tiers) {
    }

    /** 请求规则（客户端 buildItemPayload 的形状）。 */
    public record RequestRuleRequest(String when, String when_expr, BigDecimal multiplier,
                                     String field, String granularity, String tz, String op, String value) {
    }

    /** QT-08 保存单行定价（八大单价 + 档位/计价方式/规则）。 */
    public record SaveItemRequest(
            BigDecimal input_price,
            BigDecimal output_price,
            BigDecimal cache_read_price,
            BigDecimal cache_write_price,
            BigDecimal cache_write_1h_price,
            BigDecimal image_input_price,
            BigDecimal image_output_price,
            BigDecimal audio_input_price,
            BigDecimal audio_output_price,
            String model_alias,
            String tier,
            String billing_mode,
            String note,
            TimeRuleRequest price_time_rule,
            TierRuleRequest price_tier_rule,
            List<RequestRuleRequest> request_rules) {
    }

    // ------------------------------------------------------------------ QT-01/02/03/04

    /** QT-01 列表（status 支持逗号分隔多值：DRAFT / SUBMITTED,REVIEWING / REJECTED / APPROVED,CONTRACT_CREATED / CONVERTED）。 */
    @GetMapping
    public ApiEnvelope<PageResult<QuoteViews.Row>> list(@AuthenticationPrincipal AuthPrincipal principal,
                                                        @RequestParam(required = false) Integer page,
                                                        @RequestParam(required = false) Integer pageSize,
                                                        @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(quoteService.list(principal, page, pageSize, status));
    }

    /** QT-02 创建报价单（E-1602：凭证未通过检测）。 */
    @PostMapping
    public ApiEnvelope<QuoteViews.Created> create(@AuthenticationPrincipal AuthPrincipal principal,
                                                  @Valid @RequestBody CreateRequest request) {
        Long credentialId = parseId(request.credential_id());
        return ApiEnvelope.ok(quoteService.create(principal, new QuoteService.CreateCommand(
                request.name(), credentialId, request.currency(), request.valid_from(), request.valid_to(),
                request.remark())));
    }

    /** QT-03 详情。 */
    @GetMapping("/{quoteId}")
    public ApiEnvelope<QuoteViews.Detail> detail(@AuthenticationPrincipal AuthPrincipal principal,
                                                 @PathVariable Long quoteId) {
        return ApiEnvelope.ok(quoteService.detail(principal, quoteId));
    }

    /** QT-04 作废（客户端「删除」按钮，PRD 口径 VOID）。 */
    @DeleteMapping("/{quoteId}")
    public ApiEnvelope<Void> delete(@AuthenticationPrincipal AuthPrincipal principal,
                                    @PathVariable Long quoteId,
                                    @RequestParam(required = false) String reason) {
        quoteService.voidQuote(principal, quoteId, reason);
        return ApiEnvelope.ok();
    }

    // ------------------------------------------------------------------ QT-05/06

    /** QT-05 写入明细行。 */
    @PostMapping("/{quoteId}/items")
    public ApiEnvelope<QuoteViews.Items> setItems(@AuthenticationPrincipal AuthPrincipal principal,
                                                 @PathVariable Long quoteId,
                                                 @Valid @RequestBody ItemsRequest request) {
        List<QuoteService.ItemRef> refs = new ArrayList<>();
        for (ItemRef item : request.items()) {
            refs.add(new QuoteService.ItemRef(item.model_name(), item.model_alias()));
        }
        return ApiEnvelope.ok(quoteService.setItems(principal, quoteId, refs));
    }

    /** QT-06 明细行列表。 */
    @GetMapping("/{quoteId}/items")
    public ApiEnvelope<QuoteViews.Items> listItems(@AuthenticationPrincipal AuthPrincipal principal,
                                                   @PathVariable Long quoteId) {
        return ApiEnvelope.ok(quoteService.listItems(principal, quoteId));
    }

    // ------------------------------------------------------------------ QT-07/08

    /** QT-07 单行详情。 */
    @GetMapping("/items/{itemId}")
    public ApiEnvelope<QuoteViews.Item> getItem(@AuthenticationPrincipal AuthPrincipal principal,
                                                @PathVariable Long itemId) {
        return ApiEnvelope.ok(quoteService.getItem(principal, itemId));
    }

    /** QT-08 保存定价（可选 `If-Match: <version>` 乐观锁）。 */
    @PutMapping("/items/{itemId}")
    public ApiEnvelope<QuoteViews.Item> saveItem(@AuthenticationPrincipal AuthPrincipal principal,
                                                 @PathVariable Long itemId,
                                                 @RequestBody SaveItemRequest request,
                                                 @RequestHeader(value = "If-Match", required = false) String ifMatch) {
        return ApiEnvelope.ok(quoteService.saveItem(principal, itemId, toCommand(request), ifMatch,
                principal != null && principal.isAdmin()));
    }

    // ------------------------------------------------------------------ QT-09/10/11

    /** QT-09 提交（V1–V17 全量校验）。 */
    @PostMapping("/{quoteId}/submit")
    public ApiEnvelope<QuoteViews.Detail> submit(@AuthenticationPrincipal AuthPrincipal principal,
                                                 @PathVariable Long quoteId) {
        return ApiEnvelope.ok(quoteService.submit(principal, quoteId));
    }

    /** QT-10 撤回（仅审核前）。 */
    @PostMapping("/{quoteId}/withdraw")
    public ApiEnvelope<QuoteViews.Detail> withdraw(@AuthenticationPrincipal AuthPrincipal principal,
                                                   @PathVariable Long quoteId) {
        return ApiEnvelope.ok(quoteService.withdraw(principal, quoteId));
    }

    /** QT-11 版本列表。 */
    @GetMapping("/{quoteId}/versions")
    public ApiEnvelope<PageResult<QuoteViews.Version>> versions(@AuthenticationPrincipal AuthPrincipal principal,
                                                                @PathVariable Long quoteId,
                                                                @RequestParam(required = false) Integer page,
                                                                @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(quoteService.versions(principal, quoteId, page, pageSize));
    }

    // ------------------------------------------------------------------ 映射

    private static QuoteService.SaveItemCommand toCommand(SaveItemRequest request) {
        return new QuoteService.SaveItemCommand(request.input_price(), request.output_price(),
                request.cache_read_price(), request.cache_write_price(), request.cache_write_1h_price(),
                request.image_input_price(), request.audio_input_price(),
                request.image_output_price(), request.audio_output_price(),
                request.tier(), request.billing_mode(), request.note(), request.model_alias(),
                toTimeRule(request.price_time_rule()), toTierRule(request.price_tier_rule()),
                toRequestRules(request.request_rules()));
    }

    private static QuoteValidation.TimeRule toTimeRule(TimeRuleRequest request) {
        if (request == null) {
            return null;
        }
        List<QuoteValidation.Segment> segments = new ArrayList<>();
        for (RangeRequest range : request.peak_ranges() == null ? List.<RangeRequest>of() : request.peak_ranges()) {
            segments.add(new QuoteValidation.Segment(range.start(), range.end()));
        }
        return new QuoteValidation.TimeRule(request.tz(), request.weekday_scope(), request.peak_multiplier(),
                request.offpeak_multiplier(), request.peak_price_override(), segments);
    }

    private static QuoteValidation.TierRule toTierRule(TierRuleRequest request) {
        if (request == null) {
            return null;
        }
        List<QuoteValidation.Tier> tiers = new ArrayList<>();
        for (TierRequest tier : request.tiers() == null ? List.<TierRequest>of() : request.tiers()) {
            tiers.add(new QuoteValidation.Tier(tier.seq(), tier.min(), tier.max(), tier.label(),
                    tier.input_price(), tier.output_price(), tier.cache_read_price(), tier.multiplier()));
        }
        return new QuoteValidation.TierRule(request.tier_field(), request.price_strategy(), tiers);
    }

    private static List<QuoteValidation.RequestRule> toRequestRules(List<RequestRuleRequest> requests) {
        if (requests == null) {
            return List.of();
        }
        List<QuoteValidation.RequestRule> rules = new ArrayList<>();
        for (RequestRuleRequest request : requests) {
            rules.add(new QuoteValidation.RequestRule(request.field(), request.granularity(), request.tz(),
                    request.op(), request.value(), request.multiplier(), request.when_expr()));
        }
        return rules;
    }

    private static Long parseId(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            // 客户端可能传字符串型雪花 ID；非数字直接当作「无效 ID」交给服务层报参数错误
            throw new com.hioas.aap.common.ApiException(com.hioas.aap.common.ErrorCode.E_1001,
                    "credential_id 非法：" + value);
        }
    }
}
