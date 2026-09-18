package com.hioas.aap.contract;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.contract.ContractViews.Contract;
import com.hioas.aap.contract.ContractViews.File;
import com.hioas.aap.iam.AuthPrincipal;
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
 * 合同接口（供应商端 CON-01…04；`docs/backend/endpoints.json` + `02-API接口模型清单.md` §1.3）。
 *
 * <p>路径与权限：`/api/v1/contracts`（PROVIDER）；写入支持 {@code Idempotency-Key}（由
 * {@code IdempotencyFilter} 统一处理：同键同响应，签署不会落两条记录）。业务规则在 {@link ContractService}。
 */
@RestController
@RequestMapping("/api/v1/contracts")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER')")
public class ContractController {

    private final ContractService contractService;

    public ContractController(ContractService contractService) {
        this.contractService = contractService;
    }

    /** CON-01 合同列表（q：page/pageSize/status?）。 */
    @GetMapping
    public ApiEnvelope<PageResult<Contract>> list(@AuthenticationPrincipal AuthPrincipal principal,
                                                 @RequestParam(required = false) String status,
                                                 @RequestParam(required = false) Integer page,
                                                 @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(contractService.listForProvider(principal, page, pageSize, status));
    }

    /** CON-02 合同详情（含 terms[] 与 records[] 时间轴）。 */
    @GetMapping("/{id}")
    public ApiEnvelope<Contract> detail(@AuthenticationPrincipal AuthPrincipal principal,
                                        @PathVariable String id) {
        return ApiEnvelope.ok(contractService.detailForProvider(principal, parseId(id)));
    }

    /** CON-03 合同文件下载信息（未签发 → 409 E-1701）。 */
    @GetMapping("/{id}/file")
    public ApiEnvelope<File> file(@AuthenticationPrincipal AuthPrincipal principal,
                                  @PathVariable String id) {
        return ApiEnvelope.ok(contractService.file(principal, parseId(id)));
    }

    /** CON-04 供应商签署（body {sign_method?, smsCode?}）。 */
    @PostMapping("/{id}/sign")
    public ApiEnvelope<Contract> sign(@AuthenticationPrincipal AuthPrincipal principal,
                                      @PathVariable String id,
                                      @RequestBody(required = false) SignRequest request) {
        SignRequest body = request == null ? new SignRequest(null, null) : request;
        return ApiEnvelope.ok(contractService.signForProvider(principal, parseId(id),
                body.sign_method(), body.smsCode()));
    }

    /** 非法 ID 一律 E-1001（不静默当 null，避免变成「查全量」）。 */
    private static Long parseId(String value) {
        if (value == null || value.isBlank()) {
            throw ApiException.field(ErrorCode.E_1001, "id", "合同 ID 必填");
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "id", "不是合法的雪花 ID：" + value);
        }
    }

    /** CON-04 请求体：{@code {sign_method?, smsCode?}}（requests/contract-sign.schema.json）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record SignRequest(String sign_method, String smsCode) {
    }
}
