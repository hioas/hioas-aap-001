package com.hioas.aap.settlement;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.settlement.PaymentViews.Payment;
import com.hioas.aap.settlement.PaymentViews.Statement;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
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
