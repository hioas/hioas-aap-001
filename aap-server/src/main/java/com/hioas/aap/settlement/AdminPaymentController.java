package com.hioas.aap.settlement;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.settlement.PaymentViews.Payment;
import com.hioas.aap.settlement.PaymentViews.Statement;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端打款与结算接口（ADM-PAY01…03；`02-API接口模型清单.md` §2.5）。
 *
 * <p>权限：运营商务（BIZ_OPERATOR）+ 超管（SUPER_ADMIN）。确认打款受 **AC-40 合同未签署禁打款**
 * 约束（409 E-1701），规则在 {@link SettlementService#confirm}。
 */
@RestController
@RequestMapping("/api/v1/admin")
@PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
public class AdminPaymentController {

    private final SettlementService settlementService;

    public AdminPaymentController(SettlementService settlementService) {
        this.settlementService = settlementService;
    }

    /** ADM-PAY01 打款列表（跨供应商；q：page/pageSize/status?）。 */
    @GetMapping("/payments")
    public ApiEnvelope<PageResult<Payment>> list(@RequestParam(required = false) String status,
                                                @RequestParam(required = false) Integer page,
                                                @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(settlementService.listForAdmin(page, pageSize, status));
    }

    /** ADM-PAY02 确认打款：PAYMENT_RECORDED → CONFIRMED（合同未签署 → 409 E-1701）。 */
    @PostMapping("/payments/{id}/confirm")
    public ApiEnvelope<Payment> confirm(@AuthenticationPrincipal AuthPrincipal principal,
                                        @PathVariable String id) {
        return ApiEnvelope.ok(settlementService.confirm(principal, parseId(id)));
    }

    /** ADM-PAY03 结算单列表（q：page/pageSize）。 */
    @GetMapping("/settlements")
    public ApiEnvelope<PageResult<Statement>> settlements(@RequestParam(required = false) Integer page,
                                                         @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(settlementService.statements(page, pageSize));
    }

    /**
     * ADM-PAY04 记录打款（运营线下打款后留痕；不产生资金流水，R-42）。
     *
     * <p>真源 PRD 10 §4.3/§5.3：`UNSETTLED → PAYMENT_RECORDED`，C4 金额&gt;0 且币种一致、C5 需凭证截图。
     */
    @PostMapping("/payments")
    public ApiEnvelope<Payment> record(@AuthenticationPrincipal AuthPrincipal principal,
                                       @Valid @RequestBody RecordRequest request) {
        return ApiEnvelope.ok(settlementService.recordPayment(principal, new SettlementService.RecordCommand(
                parseIdOrNull(request.contract_id(), "contract_id"),
                request.amount(),
                request.currency(),
                parseIdOrNull(request.voucher_file_id(), "voucher_file_id"),
                request.paid_at(),
                request.remark())));
    }

    /** ADM-PAY05 作废打款：`PAYMENT_RECORDED/CONFIRMED → VOID`（必填理由；作废后可重录）。 */
    @PostMapping("/payments/{id}/void")
    public ApiEnvelope<Payment> voidPayment(@AuthenticationPrincipal AuthPrincipal principal,
                                            @PathVariable String id,
                                            @Valid @RequestBody VoidRequest request) {
        return ApiEnvelope.ok(settlementService.voidPayment(principal, parseId(id), request.reason()));
    }

    /** ADM-PAY04 请求体（与 `payment-record.schema.json` 一致）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record RecordRequest(
            @NotBlank(message = "合同必填") String contract_id,
            @NotNull(message = "打款金额必填") @DecimalMin(value = "0", inclusive = false, message = "打款金额必须大于 0")
            BigDecimal amount,
            @Pattern(regexp = "^[A-Za-z]{3}$", message = "币种为 3 位字母代码") String currency,
            @NotBlank(message = "打款凭证必填（C5）") String voucher_file_id,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime paid_at,
            @Size(max = 255, message = "备注不超过 255 字") String remark) {
    }

    /** ADM-PAY05 请求体（与 `payment-void.schema.json` 一致）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record VoidRequest(
            @NotBlank(message = "作废必须填写理由") @Size(max = 255, message = "理由不超过 255 字") String reason) {
    }

    /** 非法 ID 一律 E-1001（不静默当 null，避免变成「查全量」）；null/空串返回 null。 */
    private static Long parseIdOrNull(String value, String field) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, field, "不是合法的雪花 ID：" + value);
        }
    }

    /** 非法 ID 一律 E-1001（不静默当 null，避免变成「查全量」）。 */
    private static Long parseId(String value) {
        if (value == null || value.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "id", "打款记录 ID 必填");
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }
}
