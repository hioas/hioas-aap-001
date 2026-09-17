package com.hioas.aap.support;

import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ErrorCode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 测试专用控制器：只在测试上下文存在，用来验证统一契约（包体/错误码/traceId/校验）。
 * 生产代码里没有这些路径。
 */
@RestController
@RequestMapping("/api/v1/__test")
public class TestErrorController {

    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(TestErrorController.class);

    public record DemoSmsRequest(@NotBlank String phone,
                                 @Pattern(regexp = "\\d{6}", message = "验证码须为 6 位数字") String smsCode) {
    }

    @GetMapping("/echo")
    public ApiEnvelope<Map<String, Object>> echo() {
        log.info("T01-ECHO 契约探针（traceId 应随日志落盘）");
        return ApiEnvelope.ok(Map.of("hello", "world", "n", 1));
    }

    @GetMapping("/empty")
    public ApiEnvelope<Void> empty() {
        return ApiEnvelope.ok(null);
    }

    @GetMapping("/business-error")
    public ApiEnvelope<Void> businessError(@RequestParam(defaultValue = "E-1001") String code) {
        throw new ApiException(ErrorCode.of(code), "业务失败：" + code);
    }

    @GetMapping("/boom")
    public ApiEnvelope<Void> boom() {
        throw new IllegalStateException("模拟未捕获异常，含敏感内容 sk-secret-should-not-leak");
    }

    @PostMapping("/validate")
    public ApiEnvelope<Map<String, Object>> validate(@Valid @RequestBody DemoSmsRequest request) {
        return ApiEnvelope.ok(Map.of("phone", request.phone()));
    }
}
