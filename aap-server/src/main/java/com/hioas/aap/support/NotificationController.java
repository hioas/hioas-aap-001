package com.hioas.aap.support;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.support.NotificationViews.ListResult;
import com.hioas.aap.support.NotificationViews.ReadResult;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 站内信（NTF-01/02；清单 §1.7，客户端 `aap-client/src/api/notification.ts`）。
 *
 * <p>鉴权口径：清单标注「authenticated」——**供应商端与管理端同一端点**，按主体分作用域：
 * 供应商看 `recipient_type=PROVIDER` + 本人 provider；管理端看 `ADMIN` + 本人账号。
 * 因此这里不加 {@code @PreAuthorize}（默认安全链已要求认证），越权由收件人作用域隔离挡住。
 *
 * <p>未实现（不臆造，台账已记）：18-API 无「全部已读」批量端点 → 页面按列表逐条调 /read。
 */
@RestController
@RequestMapping("/api/v1/notifications")
public class NotificationController {

    private final NotificationService notificationService;

    public NotificationController(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    /** NTF-01 站内信列表（`unread`/`category` 可选过滤；`unread_count` 为本人未读总数）。 */
    @GetMapping
    public ApiEnvelope<ListResult> list(@AuthenticationPrincipal AuthPrincipal principal,
                                        @RequestParam(required = false) Integer page,
                                        @RequestParam(required = false) Integer pageSize,
                                        @RequestParam(required = false) String unread,
                                        @RequestParam(required = false) String category) {
        return ApiEnvelope.ok(notificationService.list(recipientType(principal), recipientId(principal),
                page, pageSize, unread, category));
    }

    /** NTF-02 标记单条已读（幂等；他人/不存在的通知同回 403 E-1901）。 */
    @PostMapping("/{id}/read")
    public ApiEnvelope<ReadResult> markRead(@AuthenticationPrincipal AuthPrincipal principal,
                                            @PathVariable String id) {
        return ApiEnvelope.ok(notificationService.markRead(recipientType(principal), recipientId(principal),
                parseId(id)));
    }

    private static String recipientType(AuthPrincipal principal) {
        return principal != null && principal.isAdmin() ? "ADMIN" : "PROVIDER";
    }

    /** 收件人主键：管理端 = 账号 id；供应商 = provider 主体 id（缺失即无权访问站内信）。 */
    private static Long recipientId(AuthPrincipal principal) {
        Long id = principal == null ? null : (principal.isAdmin() ? principal.accountId() : principal.providerId());
        if (id == null) {
            throw new ApiException(ErrorCode.E_1901, "当前账号未绑定供应商主体，无法访问站内信");
        }
        return id;
    }

    /** 非法 ID 一律 E-1001（不静默当 null）。 */
    private static Long parseId(String value) {
        try {
            return Long.valueOf(value.trim());
        } catch (RuntimeException e) {
            throw ApiException.field(ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }
}
