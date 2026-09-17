package com.hioas.aap.common;

import java.util.List;

/**
 * 统一响应包体：{@code {"code":"0|E-xxxx","message":"...","data":{...},"traceId":"..."}}。
 *
 * <p>契约（`docs/backend/02-API接口模型清单.md` §0）：
 * <ul>
 *   <li>{@code code} 恒为字符串（客户端按 {@code typeof body.code === 'string'} 做形状校验）</li>
 *   <li>失败时 {@code data} 为 {@code null} 但字段**保留**（禁止缺字段导致前端形状判断走偏）</li>
 *   <li>{@code traceId} 取自 MDC，与响应头 {@code X-Trace-Id} 一致</li>
 *   <li>禁止用 0 冒充"没有数据"</li>
 * </ul>
 */
public record ApiEnvelope<T>(String code, String message, T data, String traceId, List<ApiErrorDetail> details) {

    public static final String TRACE_ID = "traceId";

    public static <T> ApiEnvelope<T> ok(T data) {
        return new ApiEnvelope<>(ErrorCode.SUCCESS.code(), ErrorCode.SUCCESS.defaultMessage(), data, currentTraceId(), null);
    }

    public static ApiEnvelope<Void> ok() {
        return ok(null);
    }

    public static <T> ApiEnvelope<T> fail(ErrorCode code, String message) {
        return fail(code, message, null);
    }

    public static <T> ApiEnvelope<T> fail(ErrorCode code, String message, List<ApiErrorDetail> details) {
        String msg = message == null || message.isBlank() ? code.defaultMessage() : message;
        return new ApiEnvelope<>(code.code(), msg, null, currentTraceId(), details);
    }

    /** 单字段校验失败的便捷构造。 */
    public static <T> ApiEnvelope<T> invalid(String field, String reason) {
        return fail(ErrorCode.E_1001, ErrorCode.E_1001.defaultMessage(), List.of(new ApiErrorDetail(field, reason)));
    }

    private static String currentTraceId() {
        return org.slf4j.MDC.get(TRACE_ID);
    }
}
