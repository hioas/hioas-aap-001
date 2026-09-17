package com.hioas.aap.support.idempotency;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.mybatisflex.core.query.QueryWrapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingRequestWrapper;
import org.springframework.web.util.ContentCachingResponseWrapper;

/**
 * 幂等过滤器：非幂等写（POST/PUT/DELETE）带 {@code Idempotency-Key} 时保证「同键同响应」。
 *
 * <p>语义（18-API §通用约定）：
 * <ul>
 *   <li>首次：正常执行，把**完整响应包体**与状态码存进 {@code aap_idempotency_record}（24h）</li>
 *   <li>重放：直接回放首次响应（含 traceId），调用方看不到"第二次执行"的结果</li>
 *   <li>同键不同请求体：400 {@code E-1001}（防键复用导致语义错乱）</li>
 *   <li>并发首写：靠幂等键唯一索引兜底，撞键方转为重放</li>
 *   <li>未带键的写请求不受影响（幂等是可选能力）</li>
 * </ul>
 *
 * <p>★ 为什么是**过滤器**而不是 {@code HandlerInterceptor}：Spring Security 的
 * {@code HeaderWriterFilter} 会在 MVC 之前再包一层响应，拦截器里
 * {@code response instanceof ContentCachingResponseWrapper} 恒为 false，
 * 响应体永远存不下来（实测踩过：记录一直停在 IN_PROGRESS，第二次请求照样重复执行）。
 * 在过滤器里包装对象由自己掌握，判定是确定的。
 *
 * <p>顺序：紧跟 {@code CachingWrapperFilter}（+10）之后、Spring Security 链（-100）之前。
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class IdempotencyFilter extends OncePerRequestFilter {

    public static final String HEADER = "Idempotency-Key";

    private static final Logger log = LoggerFactory.getLogger(IdempotencyFilter.class);
    private static final long TTL_HOURS = 24;

    private final IdempotencyRecordMapper mapper;
    private final CryptoService crypto;

    public IdempotencyFilter(IdempotencyRecordMapper mapper, CryptoService crypto) {
        this.mapper = mapper;
        this.crypto = crypto;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String key = request.getHeader(HEADER);
        if (key == null || key.isBlank() || !isWrite(request.getMethod()) || !isApiPath(request)) {
            chain.doFilter(request, response);
            return;
        }
        String endpoint = request.getMethod() + " " + request.getRequestURI();
        byte[] rawBody = request.getInputStream().readAllBytes();
        String requestHash = crypto.sha256Hex(new String(rawBody, StandardCharsets.UTF_8));
        // 读完必须回放：下游控制器还要读同一个请求体
        HttpServletRequest replayable = new CachedBodyRequestWrapper(request, rawBody);

        Optional<IdempotencyRecordEntity> existing = find(key);
        if (existing.isPresent()) {
            IdempotencyRecordEntity record = existing.get();
            if (!record.getRequestHash().equals(requestHash)) {
                write(response, ErrorCode.E_1001, "Idempotency-Key 已用于不同的请求体，请换一个键");
                return;
            }
            if ("DONE".equals(record.getState()) && record.getResponseBody() != null) {
                log.info("幂等重放 key={} endpoint={}", key, endpoint);
                response.setStatus(record.getResponseStatus() == null ? 200 : record.getResponseStatus());
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write(record.getResponseBody());
                return;
            }
        } else {
            insertPlaceholder(key, endpoint, requestHash);
        }

        ContentCachingResponseWrapper responseWrapper = response instanceof ContentCachingResponseWrapper wrapper
                ? wrapper : null;
        try {
            chain.doFilter(replayable, response);
        } finally {
            if (responseWrapper != null) {
                String body = new String(responseWrapper.getContentAsByteArray(), StandardCharsets.UTF_8);
                store(key, responseWrapper.getStatus(), body);
            }
        }
    }

    private void insertPlaceholder(String key, String endpoint, String requestHash) {
        IdempotencyRecordEntity record = new IdempotencyRecordEntity();
        record.setIdempotencyKey(key);
        record.setActor(actor());
        record.setEndpoint(endpoint);
        record.setRequestHash(requestHash);
        record.setState("IN_PROGRESS");
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusHours(TTL_HOURS));
        try {
            mapper.insert(record);
        } catch (DuplicateKeyException race) {
            log.info("幂等键并发插入冲突 key={}（由后续请求重放）", key);
        }
    }

    private void store(String key, int status, String body) {
        if (body == null || body.isBlank()) {
            return;
        }
        IdempotencyRecordEntity record = find(key).orElse(null);
        if (record == null || !"IN_PROGRESS".equals(record.getState())) {
            return;
        }
        record.setResponseStatus(status);
        record.setResponseBody(body);
        record.setState("DONE");
        mapper.update(record);
    }

    private Optional<IdempotencyRecordEntity> find(String key) {
        return Optional.ofNullable(mapper.selectOneByQuery(QueryWrapper.create()
                .where("idempotency_key = ?", key)
                .limit(1)));
    }

    private static void write(HttpServletResponse response, ErrorCode code, String message) throws IOException {
        response.setStatus(code.httpStatus());
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write(JsonCodec.toJson(ApiEnvelope.fail(code, message)));
    }

    private static boolean isWrite(String method) {
        return "POST".equals(method) || "PUT".equals(method) || "DELETE".equals(method) || "PATCH".equals(method);
    }

    private static boolean isApiPath(HttpServletRequest request) {
        return request.getRequestURI().startsWith("/api/");
    }

    private static String actor() {
        return com.hioas.aap.common.AuditContext.current()
                .map(a -> a.type() + ":" + (a.id() == null ? "-" : a.id()))
                .orElse("SYSTEM");
    }
}
