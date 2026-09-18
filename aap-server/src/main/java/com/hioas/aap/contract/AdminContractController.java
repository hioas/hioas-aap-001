package com.hioas.aap.contract;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.contract.ContractViews.Contract;
import com.hioas.aap.iam.AuthPrincipal;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
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
 * 管理端合同接口（ADM-CT01…03；`02-API接口模型清单.md` §2.5）。
 *
 * <p>权限：运营商务（BIZ_OPERATOR）+ 超管（SUPER_ADMIN）——签发与确认签署都代表平台方，
 * 技术运营无权代替平台盖章。业务规则与状态机在 {@link ContractService}。
 */
@RestController
@RequestMapping("/api/v1/admin/contracts")
@PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
public class AdminContractController {

    private final ContractService contractService;

    public AdminContractController(ContractService contractService) {
        this.contractService = contractService;
    }

    /** ADM-CT01 合同列表（跨供应商；q：page/pageSize/status?）。 */
    @GetMapping
    public ApiEnvelope<PageResult<Contract>> list(@RequestParam(required = false) String status,
                                                 @RequestParam(required = false) Integer page,
                                                 @RequestParam(required = false) Integer pageSize) {
        return ApiEnvelope.ok(contractService.listForAdmin(page, pageSize, status));
    }

    /** ADM-CT02 签发：CREATED → PENDING_SIGN（补全文件/有效期/费率/条款）。 */
    @PostMapping("/{id}/issue")
    public ApiEnvelope<Contract> issue(@AuthenticationPrincipal AuthPrincipal principal,
                                       @PathVariable String id,
                                       @RequestBody(required = false) IssueRequest request) {
        IssueRequest body = request == null ? new IssueRequest(null, null, null, null, null, null, null, null,
                null, null) : request;
        return ApiEnvelope.ok(contractService.issue(principal, parseId(id),
                new ContractService.IssueCommand(body.file_id() == null ? null : parseFileId(body.file_id()),
                        body.valid_from(), body.valid_to(), body.cooperation_mode(), body.settlement_cycle(),
                        body.platform_fee_rate(), body.currency(), body.min_settlement_amount(),
                        body.terms(), body.sign_deadline())));
    }

    /** ADM-CT03 平台确认签署：SUPPLIER_SIGNED → SIGNED。 */
    @PostMapping("/{id}/confirm-sign")
    public ApiEnvelope<Contract> confirmSign(@AuthenticationPrincipal AuthPrincipal principal,
                                             @PathVariable String id) {
        return ApiEnvelope.ok(contractService.confirmSign(principal, parseId(id)));
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

    private static Long parseFileId(String value) {
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            throw ApiException.field(ErrorCode.E_1001, "file_id", "不是合法的雪花 ID：" + value);
        }
    }

    /** ADM-CT02 请求体（requests/contract-issue.schema.json；{@code file_id} 必填，额度在服务层校验）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record IssueRequest(
            String file_id,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime valid_from,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime valid_to,
            String cooperation_mode,
            String settlement_cycle,
            BigDecimal platform_fee_rate,
            String currency,
            BigDecimal min_settlement_amount,
            List<String> terms,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime sign_deadline) {
    }
}
