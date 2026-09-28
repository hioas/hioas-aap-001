package com.hioas.aap.supply;

import java.util.Locale;

/**
 * 批量配置批次的执行模式（`aap_config_batch.mode`；ADM-CB01 的请求字段）。
 *
 * <p>取值真源：`specs/001-intake-automation/contracts/intake-automation.openapi.yaml`
 * （requestBody `mode` enum：`DRY_RUN`/`APPLY`）+ V16 列注释（`DRY_RUN（只出差异清单、零写入）/ APPLY`）。
 */
public enum ConfigBatchMode {

    /**
     * 预演：产出差异清单、**生产零写入**（FR-6.3 / AC-10）。
     *
     * <p>零写入不是「尽力而为」：明细一律落 `SKIPPED`，且批次里出现任何非 `SKIPPED` 项都会让创建失败
     * （与 `SupplyUnitAdminService` 同口径的零写入自证）。
     */
    DRY_RUN,

    /**
     * 实际执行。
     *
     * <p>现状：上游执行器（T-M4-08~11：限速/写后回读/单模型隔离与回滚）尚未落地 ⇒ 只**登记受理**
     * （批次与明细落 `PENDING`），**不写上游**、不谎报已执行（R-58「不得静默成功」）。
     */
    APPLY;

    /** 解析模式字符串（大小写与首尾空白容错）；未知值一律拒绝（不回落默认值）。 */
    public static ConfigBatchMode of(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new IllegalArgumentException("批次模式为空");
        }
        try {
            return ConfigBatchMode.valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("未知批次模式：" + raw);
        }
    }
}
