package com.hioas.aap.usage;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.usage.UsageViews.Bucket;
import com.hioas.aap.usage.UsageViews.Summary;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用量统计（供应商端 USE-01/02；清单 §1.8、`docs/api/接口字段级schema.md` §1/§2）。
 *
 * <p>作用域：**只回本人 provider 的用量**（`aap_usage_hourly.provider_id`）——
 * 供应商之间互相不可见，管理端另有 {@link AdminUsageController}。
 *
 * <p>`/usage/summary` 是超集响应：工作台（序号 2）与用量概览页（序号 22）共用同一端点。
 */
@RestController
@RequestMapping("/api/v1/usage")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class UsageController {

    private final UsageService usageService;

    public UsageController(UsageService usageService) {
        this.usageService = usageService;
    }

    /** USE-01 用量概览（`month` 或 `startHour`/`endHour` 半开窗口；缺省 = 当月整月）。 */
    @GetMapping("/summary")
    public ApiEnvelope<Summary> summary(@AuthenticationPrincipal AuthPrincipal principal,
                                        @RequestParam(required = false) String startHour,
                                        @RequestParam(required = false) String endHour,
                                        @RequestParam(required = false) String month) {
        return ApiEnvelope.ok(usageService.summary(requireProvider(principal), startHour, endHour, month));
    }

    /** USE-02 分时用量（峰谷着色数据源；`from`/`to` 必填）。 */
    @GetMapping("/hourly")
    public ApiEnvelope<PageResult<Bucket>> hourly(@AuthenticationPrincipal AuthPrincipal principal,
                                                  @RequestParam(required = false) String from,
                                                  @RequestParam(required = false) String to,
                                                  @RequestParam(required = false) String model,
                                                  @RequestParam(required = false) String group,
                                                  @RequestParam(required = false) Integer page,
                                                  @RequestParam(required = false) Integer pageSize) {
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        return ApiEnvelope.ok(usageService.hourly(requireProvider(principal), null, from, to, model, group,
                pageQuery.page(), pageQuery.pageSize()));
    }

    /** 供应商主体必须存在：用量是供应商私有数据，账号未关联主体时不得回空数据（回 403 更可诊断）。 */
    private static Long requireProvider(AuthPrincipal principal) {
        if (principal == null || principal.providerId() == null) {
            throw new ApiException(ErrorCode.E_1901, "账号未关联供应商主体，无法查看用量");
        }
        return principal.providerId();
    }
}
