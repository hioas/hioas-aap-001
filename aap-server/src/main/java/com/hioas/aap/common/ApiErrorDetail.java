package com.hioas.aap.common;

/**
 * 字段级错误定位（校验失败时返回，前端可直接高亮字段）。
 *
 * @param field  字段名（dotted path，如 {@code price_tier_rule.tiers[1].max}）
 * @param reason 人类可读原因
 */
public record ApiErrorDetail(String field, String reason) {
}
