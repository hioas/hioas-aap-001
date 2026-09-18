package com.hioas.aap.support;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.support.AuditLogViews.Page;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端审计日志查询（ADM-A01；清单 §2.4）。
 *
 * <p>权限：技术运营（TECH_OPS）与超管（SUPER_ADMIN）可读——审计是技术侧合规视图
 * （R-47 / AC-48 四类必录操作的回查入口）；运营商务（BIZ_OPERATOR）与供应商一律 403 E-1901。
 *
 * <p>只读：审计表 append-only（C8），本控制器不提供任何写/删接口。
 */
@RestController
@RequestMapping("/api/v1/admin/audit-logs")
@PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
public class AuditLogController {

    private final AuditLogQueryService auditLogQueryService;

    public AuditLogController(AuditLogQueryService auditLogQueryService) {
        this.auditLogQueryService = auditLogQueryService;
    }

    /** ADM-A01 审计检索（`actorType/action/traceId/from/to` 可选；时间窗半开 `[from,to)`）。 */
    @GetMapping
    public ApiEnvelope<Page> list(@RequestParam(required = false) Integer page,
                                  @RequestParam(required = false) Integer pageSize,
                                  @RequestParam(required = false) String actorType,
                                  @RequestParam(required = false) String action,
                                  @RequestParam(required = false) String traceId,
                                  @RequestParam(required = false) String from,
                                  @RequestParam(required = false) String to) {
        return ApiEnvelope.ok(auditLogQueryService.list(page, pageSize, actorType, action, traceId, from, to));
    }
}
