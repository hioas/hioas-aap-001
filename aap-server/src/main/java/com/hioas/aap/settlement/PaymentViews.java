package com.hioas.aap.settlement;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;

/**
 * 打款 / 结算响应模型（契约真源：`docs/backend/json-schema/models/payment.schema.json` +
 * `models/settlement-statement.schema.json`；分页包体 `common/page.schema.json`）。
 *
 * <p>口径：字段 snake_case；雪花 ID 对外 string；时间戳 RFC3339 UTC；金额 numeric(18,6) 回 number。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public final class PaymentViews {

    private PaymentViews() {
    }

    /** PAY-01 / ADM-PAY01/02 的打款记录视图。 */
    public record Payment(
            String id,
            @JsonProperty("payment_id") String paymentId,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("contract_id") String contractId,
            @JsonProperty("contract_no") String contractNo,
            @JsonProperty("statement_id") String statementId,
            BigDecimal amount,
            String currency,
            String status,
            @JsonProperty("voucher_file_id") String voucherFileId,
            @JsonProperty("paid_at") String paidAt,
            @JsonProperty("confirmed_by") String confirmedBy,
            @JsonProperty("confirmed_at") String confirmedAt,
            String remark,
            @JsonProperty("created_at") String createdAt) {
    }

    /**
     * PAY-01 响应体：分页包体 + 钱包三项（清单 §1.3：{@code {items,page,pageSize,total,available_balance?,
     * pending_settlement?,total_settled?}}）。
     *
     * <p><b>口径（清单标注「约定，无 PRD 依据」）</b>：三态互斥，合计 = 全部有效打款金额，不重复计数——
     * {@code pending_settlement}=UNSETTLED（未结算）、{@code available_balance}=PAYMENT_RECORDED（已打款待确认）、
     * {@code total_settled}=CONFIRMED（已确认结算）；VOID 不计入任何一项。偏差记 D-API-04。
     */
    public record PaymentPage(
            List<Payment> items,
            int page,
            int pageSize,
            long total,
            @JsonProperty("available_balance") BigDecimal availableBalance,
            @JsonProperty("pending_settlement") BigDecimal pendingSettlement,
            @JsonProperty("total_settled") BigDecimal totalSettled) {
    }

    /** ADM-PAY03 结算单视图。 */
    public record Statement(
            String id,
            @JsonProperty("statement_no") String statementNo,
            @JsonProperty("provider_id") String providerId,
            @JsonProperty("period_from") String periodFrom,
            @JsonProperty("period_to") String periodTo,
            @JsonProperty("total_amount") BigDecimal totalAmount,
            @JsonProperty("platform_fee") BigDecimal platformFee,
            String status,
            @JsonProperty("created_at") String createdAt) {
    }
}
