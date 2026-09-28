package com.hioas.aap.supply;

import java.util.Locale;

/**
 * 批量配置批次的类型（`aap_config_batch.batch_type`；ADM-CB01 的请求字段）。
 *
 * <p>取值真源：`specs/001-intake-automation/contracts/intake-automation.openapi.yaml`
 * （`POST /admin/config-batches` 的 requestBody enum）+ V16 的列注释 + `data-model.md` §9 注释 ——
 * 三处一致，故此处**不新增取值**；未知值一律拒绝（{@link #of}），不回落默认值。
 *
 * <p>为什么显式建枚举而不是用字符串常量集合：与 `SupplyUnitStatus` 同口径（宪法 C-05「状态/取值流转
 * 必须经领域方法」）—— 取值域集中一处，校验与语义（如「是否把渠道置为不可用」）都挂在这里，
 * 避免在服务层散落字符串比较。
 */
public enum ConfigBatchType {

    /** 新增渠道（PER_MODEL：一个供给单元一条渠道，R-56）。 */
    ADD_CHANNEL,
    /** 更新既有渠道（命名/优先级/权重等）。 */
    UPDATE_CHANNEL,
    /** 写价（编译产物路径，T-M5；本轮只登记批次，不写上游）。 */
    WRITE_PRICE,
    /** 重配置（INNOV-7 / FR-2.9：凭证/价格/策略变更后重算差异）。 */
    RECONFIG,
    /** 下线（FR-2.10：把某模型的渠道置为禁用/删除，并留痕 —— 下架前须过 R-65 影响面校验）。 */
    OFFLINE,
    /** 启用。 */
    ENABLE,
    /** 停用。 */
    DISABLE;

    /**
     * 解析类型字符串（大小写与首尾空白容错）。
     *
     * @throws IllegalArgumentException 未知或空值（不猜测、不回落默认值 —— 静默回落会把拼错的类型
     *         变成「合法批次」，与 `SupplyUnitStatus.of` 同一纪律）
     */
    public static ConfigBatchType of(String raw) {
        if (raw == null || raw.isBlank()) {
            throw new IllegalArgumentException("批次类型为空");
        }
        try {
            return ConfigBatchType.valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("未知批次类型：" + raw);
        }
    }

    /**
     * 该类型是否把目标单元的渠道**置为不可用**（下架 / 停用）。
     *
     * <p>差异计算据此把目标单元放进 `offlineUnits`（FR-2.10）：有现存绑定 → `DISABLE`，
     * 无绑定 → `SKIP`（无动作可做），而不是照常算成「需要创建渠道」。
     */
    public boolean withdrawsChannel() {
        return this == OFFLINE || this == DISABLE;
    }
}
