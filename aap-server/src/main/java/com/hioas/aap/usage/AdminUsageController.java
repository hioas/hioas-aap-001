package com.hioas.aap.usage;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.AuditService;
import com.hioas.aap.usage.UsageViews.Bucket;
import com.hioas.aap.usage.UsageViews.RefreshResult;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端用量（ADM-U01/02；清单 §2.5）。
 *
 * <p>与供应商端的差别：
 * <ul>
 *   <li>**跨供应商可见**（对账要供应商×渠道×模型×小时四维下钻），因此可按
 *       `providerId`/`channelId`/`model` 过滤；供应商端固定只看本人。</li>
 *   <li>多了聚合触发（ADM-U02）：拉日志源 → 小时桶 UPSERT（AC-43/44/45），只有 TECH_OPS/SUPER_ADMIN 可触发。</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/admin/usage")
@PreAuthorize("hasAnyRole('TECH_OPS','BIZ_OPERATOR','SUPER_ADMIN')")
public class AdminUsageController {

    private final UsageService usageService;
    private final AuditService auditService;

    public AdminUsageController(UsageService usageService, AuditService auditService) {
        this.usageService = usageService;
        this.auditService = auditService;
    }

    /** ADM-U01 分时用量（全量 + 四维下钻）。 */
    @GetMapping("/hourly")
    public ApiEnvelope<PageResult<Bucket>> hourly(@RequestParam(required = false) String from,
                                                  @RequestParam(required = false) String to,
                                                  @RequestParam(required = false) String providerId,
                                                  @RequestParam(required = false) String channelId,
                                                  @RequestParam(required = false) String model,
                                                  @RequestParam(required = false) Integer page,
                                                  @RequestParam(required = false) Integer pageSize) {
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        return ApiEnvelope.ok(usageService.hourly(parseId(providerId, "providerId"),
                parseId(channelId, "channelId"), from, to, model, null,
                pageQuery.page(), pageQuery.pageSize()));
    }

    /** ADM-U02 聚合刷新（幂等 UPSERT；阈值告警按 11-PRD §4 ±5%）。 */
    @PostMapping("/refresh")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<RefreshResult> refresh(@AuthenticationPrincipal AuthPrincipal principal,
                                             @RequestBody(required = false) RefreshRequest request) {
        RefreshRequest body = request == null ? new RefreshRequest(null, null) : request;
        RefreshResult result = usageService.refresh(body.from(), body.to());
        auditService.record(AuditService.AuditAction.SYNC_EXECUTE, "usage_hourly",
                Long.valueOf(result.batchId()), "用量聚合批次 " + result.batchId() + "：新增 "
                        + result.inserted() + " 条、更新 " + result.updated() + " 条、缓存解析 "
                        + result.cacheParseStatus());
        return ApiEnvelope.ok(result);
    }

    /** 非法 ID 一律 E-1001（不静默当 null 变成「查全量」，那会让越权过滤失效）。 */
    private static Long parseId(String value, String field) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw new com.hioas.aap.common.ApiException(com.hioas.aap.common.ErrorCode.E_1001,
                    field + " 不是合法的雪花 ID");
        }
    }

    /** ADM-U02 请求体：窗口缺省 = 最近一个已结束的整点小时。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record RefreshRequest(String from, String to) {
    }
}
