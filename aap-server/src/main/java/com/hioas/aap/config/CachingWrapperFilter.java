package com.hioas.aap.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingRequestWrapper;
import org.springframework.web.util.ContentCachingResponseWrapper;

/**
 * 把请求/响应包装成可重复读取的形式，供幂等拦截器回放首次响应。
 *
 * <p>顺序：紧跟 traceId 过滤器之后、安全链之前。
 *
 * <p>两个坑（本机 Spring 7 实测）：
 * <ol>
 *   <li>{@code ContentCachingRequestWrapper} 只有 (request, cacheLimit) 双参构造；
 *       缓存上限别太小，否则请求体被截断、幂等键的 request_hash 失真（这里给 1MB）。</li>
 *   <li>响应包装必须无条件 {@code copyBodyToResponse()} 写回，否则响应体会被"吞掉"。
 *       注意要保留**具体类型**（{@code HttpServletResponse} 接口上没有该方法）。</li>
 * </ol>
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class CachingWrapperFilter extends OncePerRequestFilter {

    private static final int REQUEST_CACHE_LIMIT = 1024 * 1024;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        ContentCachingRequestWrapper requestWrapper =
                new ContentCachingRequestWrapper(request, REQUEST_CACHE_LIMIT);
        ContentCachingResponseWrapper responseWrapper = new ContentCachingResponseWrapper(response);
        try {
            chain.doFilter(requestWrapper, responseWrapper);
        } finally {
            responseWrapper.copyBodyToResponse();
        }
    }
}
