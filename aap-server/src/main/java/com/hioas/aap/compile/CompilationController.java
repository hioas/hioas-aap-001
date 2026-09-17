package com.hioas.aap.compile;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 计费编译管理端接口（ADM-Q01、ADM-CP01…04；真源 `06-报价模型与计费编译规则.md`）。
 *
 * <p>三道闸门（R-33）在此暴露：编译（ADM-Q01）→ 模拟验证（ADM-CP03）→ 人工确认（ADM-CP04）。
 * 未确认的产物 {@code publish_blocked=true}，同步写入方（T14）必须以此为准。
 */
@RestController
@RequestMapping("/api/v1/admin")
public class CompilationController {

    private final CompilationService compilationService;

    public CompilationController(CompilationService compilationService) {
        this.compilationService = compilationService;
    }

    /** ADM-Q01 发起编译（仅技术运营/超管）。 */
    @PostMapping("/quotes/{id}/compile")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<CompilationViews.Result> compile(@AuthenticationPrincipal AuthPrincipal principal,
                                                        @PathVariable Long id) {
        return ApiEnvelope.ok(compilationService.compile(principal, id, principal != null && principal.isAdmin()));
    }

    /** ADM-CP01 编译记录列表。 */
    @GetMapping("/compilations")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<PageResult<CompilationViews.Result>> list(@RequestParam(required = false) Integer page,
                                                                 @RequestParam(required = false) Integer pageSize,
                                                                 @RequestParam(required = false) String status) {
        return ApiEnvelope.ok(compilationService.list(page, pageSize, status));
    }

    /** ADM-CP02 编译详情（含表达式与模拟验证报告）。 */
    @GetMapping("/compilations/{id}")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<CompilationViews.Result> detail(@PathVariable Long id) {
        return ApiEnvelope.ok(compilationService.detail(id));
    }

    /** ADM-CP03 重新模拟验证（失败返回 E-1405 并保留报告）。 */
    @PostMapping("/compilations/{id}/verify")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<CompilationViews.VerifyReport> verify(@PathVariable Long id) {
        return ApiEnvelope.ok(compilationService.verify(id));
    }

    /** ADM-CP04 人工确认（未验证 → E-1407；确认后解除写入封锁）。 */
    @PostMapping("/compilations/{id}/confirm")
    @PreAuthorize("hasAnyRole('TECH_OPS','SUPER_ADMIN')")
    public ApiEnvelope<CompilationViews.Result> confirm(@AuthenticationPrincipal AuthPrincipal principal,
                                                       @PathVariable Long id) {
        return ApiEnvelope.ok(compilationService.confirm(principal, id));
    }
}
