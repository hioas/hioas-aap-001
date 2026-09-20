package com.hioas.aap.catalog;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.mybatisflex.annotation.Table;

/**
 * 模型厂商（表 {@code aap_vendor}）。
 *
 * <p>真源：Calicat 设计 page-3-1「新增厂商」+ {@code .calicat/prd/13-管理端PRD.md}。
 * 字段顺序与设计稿的字段顺序一致，便于与原型逐项对账。
 *
 * <p>{@code vendorType} 取值：{@code DIRECT} 官方直连 / {@code THIRD_PARTY} 第三方代理 /
 * {@code SELF_GATEWAY} 自建网关（设计稿三个单选）。
 *
 * <p>{@code apiKeyCipher} 是**加密后**的密文，绝不明文落库；对外一律脱敏（见 {@link CatalogViews}）。
 */
@Table(value = "aap_vendor", onInsert = AuditListeners.Insert.class,
        onUpdate = AuditListeners.Update.class)
public class VendorEntity extends BaseEntity {

    /** 厂商名称（设计：如 Mistral AI） */
    private String name;

    /** 厂商标识（英文 key，如 mistral）—— 唯一，模型标识的命名前缀来源 */
    private String vendorKey;

    /** 厂商类型：DIRECT / THIRD_PARTY / SELF_GATEWAY */
    private String vendorType;

    /** 所属地区：中国 / 美国 / 欧洲 / 其他 */
    private String region;

    /** 官网地址 */
    private String website;

    /** API Base URL（必填） */
    private String baseUrl;

    /** 默认 API Key（密文，可在单模型覆盖） */
    private String apiKeyCipher;

    /** 默认并发限流（QPS） */
    private Integer defaultQps;

    /** 结算币种：CNY / USD —— ⚠️ 与价格单位的口径见 V9 迁移头部 D-ADM-4 */
    private String currency;

    /** 启用该厂商（启用后可在新增模型时选择该厂商） */
    private Boolean enabled;

    /** 厂商描述 */
    private String description;

    public String getName() {
        return name;
    }

    public void setName(String v) {
        this.name = v;
    }

    public String getVendorKey() {
        return vendorKey;
    }

    public void setVendorKey(String v) {
        this.vendorKey = v;
    }

    public String getVendorType() {
        return vendorType;
    }

    public void setVendorType(String v) {
        this.vendorType = v;
    }

    public String getRegion() {
        return region;
    }

    public void setRegion(String v) {
        this.region = v;
    }

    public String getWebsite() {
        return website;
    }

    public void setWebsite(String v) {
        this.website = v;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String v) {
        this.baseUrl = v;
    }

    public String getApiKeyCipher() {
        return apiKeyCipher;
    }

    public void setApiKeyCipher(String v) {
        this.apiKeyCipher = v;
    }

    public Integer getDefaultQps() {
        return defaultQps;
    }

    public void setDefaultQps(Integer v) {
        this.defaultQps = v;
    }

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String v) {
        this.currency = v;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public void setEnabled(Boolean v) {
        this.enabled = v;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String v) {
        this.description = v;
    }
}
