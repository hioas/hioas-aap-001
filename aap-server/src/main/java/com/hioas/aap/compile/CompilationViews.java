package com.hioas.aap.compile;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * 编译响应模型（契约：`docs/backend/json-schema/models/compilation-result.schema.json`、
 * `model-expression`、`verify-report`、`verify-case`；客户端页面：模型定价/报价预览/运营编译台）。
 */
public final class CompilationViews {

    private CompilationViews() {
    }

    /** 单模型表达式（model-expression）。 */
    public record ModelExpr(String model_name, String expr_version, String expr, List<String> tier_labels,
                            List<String> rule_hits, Boolean verified, String source_hash,
                            String inline_expanded) {
    }

    /** 模拟验证报告（verify-report）。 */
    public record VerifyReport(String status, Integer case_total, Integer case_passed, String failed_field,
                               List<VerifyCase> cases, String started_at, String finished_at) {
    }

    /** 验证用例（verify-case）。 */
    public record VerifyCase(String case_code, String case_name, Map<String, Object> input,
                             BigDecimal expected, BigDecimal actual, Boolean passed, String diff_note) {
    }

    /** 编译产物（compilation-result）。 */
    public record Result(String compilation_id, String id, String quote_id, Integer quote_version,
                         String provider_id, String status, String gate_status, String source_hash,
                         String compiler_version, Boolean publish_blocked, Map<String, Object> previous_expr,
                         List<ModelExpr> compiled, VerifyReport verify_report, String confirmed_at,
                         String created_at) {
    }
}
