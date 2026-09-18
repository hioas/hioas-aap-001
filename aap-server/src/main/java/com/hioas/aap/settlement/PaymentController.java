package com.hioas.aap.settlement;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.settlement.PaymentViews.PaymentPage;
import com.hioas.aap.iam.AuthPrincipal;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 打款接口（供应商端 PAY-01；`02-API接口模型清单.md` §1.3）。
 *
 * <p>只读端：R-42 打款仅记录，供应商不发起打款；钱包三项口径见
 * {@link PaymentViews.PaymentPage}（清单标注「约定，无 PRD 依据」）。
 */
@RestController
@RequestMapping("/api/v1/payments")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class PaymentController {

    private final SettlementService settlementService;

    public PaymentController(SettlementService settlementService) {
        this.settlementService = settlementService;
    }

    /** PAY-01 本供应商打款列表（q：page/pageSize）。 */
    @GetMapping
    public ApiEnvelope<PaymentPage> list(@AuthenticationPrincipal AuthPrincipal principal,
                                        @RequestParam(required = false) Integer page,
                                        @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(settlementService.listForProvider(principal, page, pageSize));
    }
}
