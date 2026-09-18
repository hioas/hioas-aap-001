package com.hioas.aap.contract;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;

/**
 * 合同响应模型（契约真源：`docs/backend/json-schema/models/contract.schema.json` +
 * `models/report-export.schema.json`，由 `tools/gen-backend-models.py` 从冻结清单生成）。
 *
 * <p>口径（与全项目一致）：
 * <ul>
 *   <li>字段一律 snake_case；雪花 ID 对外**一律 string**（避免 JS 精度丢失）</li>
 *   <li>时间戳 RFC3339 UTC；金额 numeric(18,6) 原样回 number</li>
 *   <li>缺值回 null（前端渲染占位符），不用空串/0 冒充</li>
 *   <li>{@code id} 与 {@code contract_id} 同值（模型里两个别名并存，不引入第二套主键语义）</li>
 * </ul>
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class ContractViews {

    private ContractViews() {
    }

    /** 签署时间轴一条（客户端 15 合同签署页 records[]）。 */
    public record SignRecord(
            String title,
            String time,
            String tone,
            @JsonProperty("at") String at,
            @JsonProperty("signer_type") String signerType,
            @JsonProperty("sign_method") String signMethod) {
    }

    /** CON-01/02/04、ADM-CT01/02/03 的合同视图。列表接口不回 {@code terms}/{@code records}（详情才带，避免 N+1）。 */
    public record Contract(
            String id,
            @JsonProperty("contract_id") String contractId,
            @JsonProperty("contract_no") String contractNo,
            @JsonProperty("quote_id") String quoteId,
            @JsonProperty("quote_no") String quoteNo,
            @JsonProperty("provider_id") String providerId,
            String title,
            String name,
            @JsonProperty("contract_name") String contractName,
            String status,
            @JsonProperty("sign_channel") String signChannel,
            @JsonProperty("cooperation_mode") String cooperationMode,
            @JsonProperty("valid_from") String validFrom,
            @JsonProperty("valid_to") String validTo,
            @JsonProperty("settlement_cycle") String settlementCycle,
            @JsonProperty("platform_fee_rate") BigDecimal platformFeeRate,
            String currency,
            @JsonProperty("min_settlement_amount") BigDecimal minSettlementAmount,
            @JsonProperty("sign_deadline") String signDeadline,
            @JsonProperty("supplier_name") String supplierName,
            @JsonProperty("signer_name") String signerName,
            @JsonProperty("signer_phone_masked") String signerPhoneMasked,
            @JsonProperty("sign_method") String signMethod,
            List<String> terms,
            List<SignRecord> records,
            @JsonProperty("file_id") String fileId,
            @JsonProperty("file_name") String fileName,
            @JsonProperty("signed_at") String signedAt,
            @JsonProperty("archived_at") String archivedAt,
            @JsonProperty("created_at") String createdAt,
            @JsonProperty("updated_at") String updatedAt,
            Integer version) {
    }

    /**
     * CON-03 合同文件下载信息（复用 {@code report-export.schema.json}：{@code {url,file_name,expire_at}}）。
     *
     * <p><b>取舍</b>：对象存储签名未接线（同 RPT-04 PDF 未接线的处理），{@code url} 回文件资产的
     * {@code file_key}（存储键），由前端按存储前缀拼接；接线后替换为限时签名 URL。偏差记于
     * `.agents/state/aap-server-tdd-state.md`（D-API-02）。
     */
    public record File(
            @JsonProperty("url") String url,
            @JsonProperty("file_url") String fileUrl,
            @JsonProperty("file_name") String fileName,
            @JsonProperty("expire_at") String expireAt) {
    }
}
