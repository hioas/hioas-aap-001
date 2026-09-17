package com.hioas.aap.provider;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 供应商档案与资质接口（PROV-01…05）。
 *
 * <p>幂等与乐观锁：写接口支持 {@code Idempotency-Key}（由 {@code IdempotencyInterceptor} 统一处理）
 * 与 {@code If-Match}（本控制器解析后交给 Service 校验）。
 */
@RestController
@RequestMapping("/api/v1/provider")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class ProviderController {

    private final ProviderService providerService;

    public ProviderController(ProviderService providerService) {
        this.providerService = providerService;
    }

    public record UpdateProfileRequest(
            @Size(max = 64, message = "简称最多 64 字") String short_name,
            @Size(max = 128, message = "企业全称最多 128 字") String company_name,
            @Pattern(regexp = "^[0-9A-Z]{18}$", message = "统一社会信用代码需为 18 位大写字母或数字") String uscc,
            @Pattern(regexp = "^(ORIGINAL|RESELLER|AGGREGATOR)$", message = "供应商类型不合法") String industry_category,
            String province, String city, String address, String website,
            String contact_name, String contact_title,
            @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确") String contact_phone,
            @Email(message = "邮箱格式不正确") String contact_email,
            String company_intro,
            @Min(value = 1, message = "复测间隔至少 1 天") @Max(value = 365, message = "复测间隔最多 365 天")
            Integer recheck_interval_days,
            Boolean manual_override, String override_reason) {
    }

    public record QualificationRequest(
            @Pattern(regexp = "^(BUSINESS_LICENSE|AUTHORIZATION|OTHER)$", message = "资质类型不合法") String category,
            String file_name, Long file_size, String content_type, Long file_id) {
    }

    /** PROV-01 查询本人档案。 */
    @GetMapping("/profile")
    public ApiEnvelope<ProviderProfileResponse> profile(@AuthenticationPrincipal AuthPrincipal principal) {
        return ApiEnvelope.ok(providerService.profile(principal));
    }

    /** PROV-02 保存档案（支持 Idempotency-Key 与 If-Match）。 */
    @PutMapping("/profile")
    public ApiEnvelope<ProviderProfileResponse> updateProfile(
            @AuthenticationPrincipal AuthPrincipal principal,
            @Valid @RequestBody UpdateProfileRequest request,
            @RequestHeader(value = "If-Match", required = false) String ifMatch) {
        ProviderService.UpdateProfileCommand command = new ProviderService.UpdateProfileCommand(
                request.short_name(), request.company_name(), request.uscc(), request.industry_category(),
                request.province(), request.city(), request.address(), request.website(),
                request.contact_name(), request.contact_title(), request.contact_phone(), request.contact_email(),
                request.company_intro(), request.recheck_interval_days(), request.manual_override(),
                request.override_reason());
        return ApiEnvelope.ok(providerService.updateProfile(principal, command, ifMatch));
    }

    /** PROV-03 资质列表。 */
    @GetMapping("/qualifications")
    public ApiEnvelope<PageResult<Map<String, Object>>> qualifications(
            @AuthenticationPrincipal AuthPrincipal principal,
            @RequestParam(required = false) Integer page,
            @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(providerService.qualifications(principal, page, pageSize));
    }

    /** PROV-04 资质登记。 */
    @PostMapping("/qualifications")
    public ApiEnvelope<Map<String, Object>> addQualification(
            @AuthenticationPrincipal AuthPrincipal principal,
            @Valid @RequestBody QualificationRequest request) {
        return ApiEnvelope.ok(providerService.addQualification(principal,
                new ProviderService.QualificationCommand(request.category(), request.file_id(),
                        request.file_name(), request.file_size(), request.content_type())));
    }

    /** PROV-05 删除资质。 */
    @DeleteMapping("/qualifications/{id}")
    public ApiEnvelope<Void> removeQualification(@AuthenticationPrincipal AuthPrincipal principal,
                                                 @PathVariable Long id) {
        providerService.removeQualification(principal, id);
        return ApiEnvelope.ok();
    }
}
