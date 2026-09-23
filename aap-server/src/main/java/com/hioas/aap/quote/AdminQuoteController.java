package com.hioas.aap.quote;

import com.hioas.aap.common.ApiEnvelope;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端报价（ADM-Q02；清单 §2.4）。
 *
 * <p>权限：运营商务（`BIZ_OPERATOR`）+ 超管（`SUPER_ADMIN`）——与 `13-管理端PRD.md` §5.6
 * 「查看历史报价对比 ✅ 运营商务 / ✅ 技术运营 / ✅ 超管」相比，**技术运营按冻结清单不放行**
 * （清单 ADM-Q02 只列 BIZ_OPERATOR；与 D-API-26 的能力矩阵口径一致 → 403 `E-1901`，见偏差 D-ADM-03）。
 *
 * <p>编译类管理端接口（ADM-Q01 等）在 {@code CompilationController}，与本控制器同前缀不同路径，互不遮挡。
 */
@RestController
@RequestMapping("/api/v1/admin/quotes")
@PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
public class AdminQuoteController {

    private final AdminQuoteCompareService adminQuoteCompareService;
    private final QuoteService quoteService;

    public AdminQuoteController(AdminQuoteCompareService adminQuoteCompareService, QuoteService quoteService) {
        this.adminQuoteCompareService = adminQuoteCompareService;
        this.quoteService = quoteService;
    }

    /**
     * ADM-Q03 报价明细（管理端跨供应商只读；**报价审核页消费**）。
     *
     * <p>补这条端点的原因：审核页原先调供应商端点 {@code GET /quotes/{id}/items} → 管理端令牌 403 →
     * 审核员看不到逐模型价格（2026-09-23 运行态实测）。
     */
    @GetMapping("/{id}/items")
    public ApiEnvelope<QuoteViews.Items> items(@PathVariable Long id) {
        // QuoteViews 与本类同包（com.hioas.aap.quote），无需 import
        return ApiEnvelope.ok(quoteService.listItemsForAdmin(id));
    }

    /** ADM-Q02 报价历史对比（`quoteIds` 逗号分隔、旧 → 新）。 */
    @GetMapping("/compare")
    public ApiEnvelope<QuoteViews.CompareList> compare(@RequestParam(required = false) String quoteIds) {
        return ApiEnvelope.ok(adminQuoteCompareService.compare(quoteIds));
    }
}
