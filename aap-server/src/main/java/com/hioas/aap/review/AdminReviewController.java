package com.hioas.aap.review;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.review.ReviewViews.RecordList;
import com.hioas.aap.review.ReviewViews.Task;
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
 * 管理端报价审核（ADM-R01…R05；清单 `02-API接口模型清单.md` §2.4 / `18-API设计OpenAPI.md` Review Tag）。
 *
 * <p>权限差异（`13-管理端PRD.md` §5）：技术运营（TECH_OPS）**只读**——可看待审池与审核记录，
 * 领取/通过/驳回一律 403；决策类动作仅运营商务（BIZ_OPERATOR）+ 超管（SUPER_ADMIN）。
 * 与「不提供批量通过」同理：通过会链式生成合同，必须逐单确认。
 */
@RestController
@RequestMapping("/api/v1/admin/reviews")
@PreAuthorize("hasAnyRole('BIZ_OPERATOR','TECH_OPS','SUPER_ADMIN')")
public class AdminReviewController {

    private final ReviewService reviewService;

    public AdminReviewController(ReviewService reviewService) {
        this.reviewService = reviewService;
    }

    /** ADM-R01 待审报价池（`status` 可选：PENDING/CLAIMED/APPROVED/REJECTED）。 */
    @GetMapping
    public ApiEnvelope<PageResult<Task>> list(@RequestParam(required = false) String status,
                                             @RequestParam(required = false) Integer page,
                                             @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(reviewService.list(status, page, pageSize));
    }

    /** ADM-R02 领取（并发下失败方拿 E-1601）。 */
    @PostMapping("/{id}/claim")
    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    public ApiEnvelope<Task> claim(@AuthenticationPrincipal AuthPrincipal principal,
                                   @PathVariable String id) {
        return ApiEnvelope.ok(reviewService.claim(principal, parseId(id)));
    }

    /** ADM-R03 通过（→ APPROVED，自动生成合同）。 */
    @PostMapping("/{id}/approve")
    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    public ApiEnvelope<Task> approve(@AuthenticationPrincipal AuthPrincipal principal,
                                     @PathVariable String id,
                                     @RequestBody(required = false) ApproveRequest request) {
        String comment = request == null ? null : request.comment();
        return ApiEnvelope.ok(reviewService.approve(principal, parseId(id), comment));
    }

    /** ADM-R04 驳回（`reason_code` 必填、必须命中枚举；`reason_text` 建议填写）。 */
    @PostMapping("/{id}/reject")
    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    public ApiEnvelope<Task> reject(@AuthenticationPrincipal AuthPrincipal principal,
                                    @PathVariable String id,
                                    @RequestBody(required = false) RejectRequest request) {
        RejectRequest body = request == null ? new RejectRequest(null, null, null, null) : request;
        return ApiEnvelope.ok(reviewService.reject(principal, parseId(id), body.reason_code(),
                body.reason_text(), body.item_id(), body.field()));
    }

    /** ADM-R05 审核记录（时间线；`quoteId` 可选过滤）。 */
    @GetMapping("/records")
    public ApiEnvelope<RecordList> records(@RequestParam(required = false) String quoteId) {
        return ApiEnvelope.ok(reviewService.records(parseId(quoteId)));
    }

    /** 非法 ID 一律 E-1001（不静默当 null 变成「查全量」，那会让过滤失效）。 */
    private static Long parseId(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw com.hioas.aap.common.ApiException.field(
                    com.hioas.aap.common.ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }

    /** ADM-R03 请求体：{@code {comment?}}（review-approve.schema.json）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record ApproveRequest(String comment) {
    }

    /** ADM-R04 请求体：{@code {reason_code, reason_text?, item_id?, field?}}（review-reject.schema.json）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record RejectRequest(String reason_code, String reason_text, String item_id, String field) {
    }
}
