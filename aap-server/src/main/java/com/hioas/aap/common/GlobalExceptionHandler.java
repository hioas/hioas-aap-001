package com.hioas.aap.common;

import jakarta.validation.ConstraintViolationException;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * 全局异常处理：把一切异常翻译成统一包体。
 *
 * <p>分类原则（SOUL「异常保留上下文与根因，按调用方能否恢复分类」）：
 * <ul>
 *   <li>业务异常 {@link ApiException} → 其错误码与 HTTP 状态，日志 WARN 不打堆栈</li>
 *   <li>参数类异常 → E-1001 + 字段级 details（400）</li>
 *   <li>路由/资源不存在 → E-1406（404）、方法不支持 → E-1406（405）</li>
 *   <li>未捕获 → E-2001（500），**对调用方不泄漏根因**，ERROR 日志带 traceId 与堆栈进告警链路</li>
 * </ul>
 */
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleApiException(ApiException ex) {
        ErrorCode code = ex.errorCode();
        if (code.httpStatus() >= 500) {
            log.error("业务异常按系统错误处理 code={} msg={}", code.code(), ex.getMessage(), ex);
        } else {
            log.warn("业务失败 code={} msg={} details={}", code.code(), ex.getMessage(), ex.details());
        }
        return ResponseEntity.status(code.httpStatus()).body(ApiEnvelope.fail(code, ex.getMessage(), ex.details()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleBeanValidation(MethodArgumentNotValidException ex) {
        List<ApiErrorDetail> details = ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> new ApiErrorDetail(fe.getField(), fe.getDefaultMessage()))
                .toList();
        log.warn("参数校验失败 details={}", details);
        return badRequest(details);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleConstraintViolation(ConstraintViolationException ex) {
        List<ApiErrorDetail> details = ex.getConstraintViolations().stream()
                .map(v -> new ApiErrorDetail(v.getPropertyPath().toString(), v.getMessage()))
                .toList();
        log.warn("参数约束失败 details={}", details);
        return badRequest(details);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleMissingParam(MissingServletRequestParameterException ex) {
        return badRequest(List.of(new ApiErrorDetail(ex.getParameterName(), "缺少必填参数")));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        return badRequest(List.of(new ApiErrorDetail(ex.getName(), "参数类型不正确")));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleUnreadable(HttpMessageNotReadableException ex) {
        log.warn("请求体不可解析: {}", ex.getMessage());
        return badRequest(List.of(new ApiErrorDetail("body", "请求体不是合法 JSON 或字段类型不匹配")));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleNotFound(NoResourceFoundException ex) {
        return ResponseEntity.status(ErrorCode.E_1406.httpStatus())
                .body(ApiEnvelope.fail(ErrorCode.E_1406, "接口或资源不存在"));
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ApiEnvelope<Void>> handleMethodNotSupported(HttpRequestMethodNotSupportedException ex) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED)
                .body(ApiEnvelope.fail(ErrorCode.E_1406, "请求方法不被支持：" + ex.getMethod()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiEnvelope<Void>> handleUnexpected(Exception ex) {
        // 根因只进日志/告警，不出接口（不泄漏堆栈、SQL、密钥）
        log.error("未捕获异常，已按 E-2001 处理: {}", ex.toString(), ex);
        return ResponseEntity.status(ErrorCode.E_2001.httpStatus())
                .body(ApiEnvelope.fail(ErrorCode.E_2001, ErrorCode.E_2001.defaultMessage()));
    }

    private ResponseEntity<ApiEnvelope<Void>> badRequest(List<ApiErrorDetail> details) {
        return ResponseEntity.status(ErrorCode.E_1001.httpStatus())
                .body(ApiEnvelope.fail(ErrorCode.E_1001, ErrorCode.E_1001.defaultMessage(), details));
    }
}
