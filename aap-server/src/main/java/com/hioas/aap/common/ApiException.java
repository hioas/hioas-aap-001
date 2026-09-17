package com.hioas.aap.common;

import java.util.List;

/**
 * 业务异常：携带统一错误码与可选字段级定位。
 *
 * <p>区分「业务可恢复错误」（用本类，携带稳定错误码）与「系统故障」（未捕获异常 → E-2001 + 告警）。
 * 异常信息必须对调用方安全：不得包含密钥、密文、堆栈。
 */
public class ApiException extends RuntimeException {

    private final ErrorCode errorCode;
    private final List<ApiErrorDetail> details;

    public ApiException(ErrorCode errorCode) {
        this(errorCode, errorCode.defaultMessage(), null);
    }

    public ApiException(ErrorCode errorCode, String message) {
        this(errorCode, message, null);
    }

    public ApiException(ErrorCode errorCode, String message, List<ApiErrorDetail> details) {
        super(message);
        this.errorCode = errorCode;
        this.details = details == null ? List.of() : List.copyOf(details);
    }

    public ErrorCode errorCode() {
        return errorCode;
    }

    public List<ApiErrorDetail> details() {
        return details;
    }

    public static ApiException of(ErrorCode code) {
        return new ApiException(code);
    }

    public static ApiException field(ErrorCode code, String field, String reason) {
        return new ApiException(code, code.defaultMessage(), List.of(new ApiErrorDetail(field, reason)));
    }
}
