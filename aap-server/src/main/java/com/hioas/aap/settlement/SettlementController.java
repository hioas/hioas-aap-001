package com.hioas.aap.settlement;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.settlement.PaymentViews.Detail;
import com.hioas.aap.settlement.PaymentViews.Statement;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 结算单（供应商端 SET-01 / SET-02）——对账视图。
 *
 * <p>为什么新增：供应商侧此前**零结算端点**（`.calicat/prd/12-供应商端PRD.md` 是 18 字节的空壳，
 * 全文不提用量/结算/对账），而管理端已能出账 ⇒ 供应商看不到自己被结算的明细，
 * 「打款 → 结算单 → 对账单」这条链对供应商不可见。本控制器按管理端口径对齐，**只读本人数据**。
 *
 * <p>越权口径：读他人单与读不存在的单**返回同样的 404 `E-1406`** —— 不因错误码差异泄露
 * 「该单存在但不属于你」这一信息。
 */
@RestController
@RequestMapping("/api/v1/settlements")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class SettlementController {

    private final SettlementService settlementService;

    public SettlementController(SettlementService settlementService) {
        this.settlementService = settlementService;
    }

    /** SET-01 本供应商结算单列表（q：page/pageSize）。 */
    @GetMapping
    public ApiEnvelope<PageResult<Statement>> list(@AuthenticationPrincipal AuthPrincipal principal,
                                                  @RequestParam(required = false) Integer page,
                                                  @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(settlementService.statementsForProvider(principal, page, pageSize));
    }

    /** SET-02 结算单详情（含明细行；只读本人单，越权/不存在一律 404 E-1406）。 */
    @GetMapping("/{id}")
    public ApiEnvelope<Detail> detail(@AuthenticationPrincipal AuthPrincipal principal,
                                      @PathVariable String id) {
        return ApiEnvelope.ok(settlementService.detailForProvider(principal, parseId(id)));
    }

    private static Long parseId(String value) {
        if (value == null || value.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "id", "结算单 ID 必填");
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }
}
