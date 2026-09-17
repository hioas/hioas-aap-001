package com.hioas.aap.provider;

import com.hioas.aap.common.AuditListeners;
import com.hioas.aap.common.BaseEntity;
import com.hioas.aap.common.JsonbTypeHandler;
import com.mybatisflex.annotation.Column;
import com.mybatisflex.annotation.Table;
import java.time.OffsetDateTime;

/**
 * 供应商主体（表 {@code aap_provider}，见 docs/backend/01-ER数据模型.md §4.2）。
 *
 * <p>字段名与列名的映射：MyBatis-Flex {@code camelToUnderline} 默认开启，
 * {@code providerCode → provider_code}；jsonb 列显式挂 {@link JsonbTypeHandler}。
 */
@Table(value = "aap_provider", onInsert = AuditListeners.Insert.class, onUpdate = AuditListeners.Update.class)
public class ProviderEntity extends BaseEntity {

    private String providerNo;
    private String providerCode;
    private Long accountId;
    private String shortName;
    private String shortCode;
    private String companyName;
    private String uscc;
    private String industryCategory;
    private String province;
    private String city;
    private String address;
    private String website;
    private String contactName;
    private String contactTitle;
    private String contactPhoneCipher;
    private String contactPhoneHash;
    private String contactPhoneMask;
    private String contactEmail;
    private String companyIntro;
    private Short completeness;
    private String status;
    private Integer recheckIntervalDays;
    private Boolean manualOverride;
    private String overrideReason;

    @Column(typeHandler = JsonbTypeHandler.class)
    private String operatorTags;

    private Long lastDetectionJobId;
    private OffsetDateTime publishedAt;
    private OffsetDateTime suspendedAt;
    private String suspendReason;

    public String getProviderNo() {
        return providerNo;
    }

    public void setProviderNo(String providerNo) {
        this.providerNo = providerNo;
    }

    public String getProviderCode() {
        return providerCode;
    }

    public void setProviderCode(String providerCode) {
        this.providerCode = providerCode;
    }

    public Long getAccountId() {
        return accountId;
    }

    public void setAccountId(Long accountId) {
        this.accountId = accountId;
    }

    public String getShortName() {
        return shortName;
    }

    public void setShortName(String shortName) {
        this.shortName = shortName;
    }

    public String getShortCode() {
        return shortCode;
    }

    public void setShortCode(String shortCode) {
        this.shortCode = shortCode;
    }

    public String getCompanyName() {
        return companyName;
    }

    public void setCompanyName(String companyName) {
        this.companyName = companyName;
    }

    public String getUscc() {
        return uscc;
    }

    public void setUscc(String uscc) {
        this.uscc = uscc;
    }

    public String getIndustryCategory() {
        return industryCategory;
    }

    public void setIndustryCategory(String industryCategory) {
        this.industryCategory = industryCategory;
    }

    public String getProvince() {
        return province;
    }

    public void setProvince(String province) {
        this.province = province;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getWebsite() {
        return website;
    }

    public void setWebsite(String website) {
        this.website = website;
    }

    public String getContactName() {
        return contactName;
    }

    public void setContactName(String contactName) {
        this.contactName = contactName;
    }

    public String getContactTitle() {
        return contactTitle;
    }

    public void setContactTitle(String contactTitle) {
        this.contactTitle = contactTitle;
    }

    public String getContactPhoneCipher() {
        return contactPhoneCipher;
    }

    public void setContactPhoneCipher(String contactPhoneCipher) {
        this.contactPhoneCipher = contactPhoneCipher;
    }

    public String getContactPhoneHash() {
        return contactPhoneHash;
    }

    public void setContactPhoneHash(String contactPhoneHash) {
        this.contactPhoneHash = contactPhoneHash;
    }

    public String getContactPhoneMask() {
        return contactPhoneMask;
    }

    public void setContactPhoneMask(String contactPhoneMask) {
        this.contactPhoneMask = contactPhoneMask;
    }

    public String getContactEmail() {
        return contactEmail;
    }

    public void setContactEmail(String contactEmail) {
        this.contactEmail = contactEmail;
    }

    public String getCompanyIntro() {
        return companyIntro;
    }

    public void setCompanyIntro(String companyIntro) {
        this.companyIntro = companyIntro;
    }

    public Short getCompleteness() {
        return completeness;
    }

    public void setCompleteness(Short completeness) {
        this.completeness = completeness;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getRecheckIntervalDays() {
        return recheckIntervalDays;
    }

    public void setRecheckIntervalDays(Integer recheckIntervalDays) {
        this.recheckIntervalDays = recheckIntervalDays;
    }

    public Boolean getManualOverride() {
        return manualOverride;
    }

    public void setManualOverride(Boolean manualOverride) {
        this.manualOverride = manualOverride;
    }

    public String getOverrideReason() {
        return overrideReason;
    }

    public void setOverrideReason(String overrideReason) {
        this.overrideReason = overrideReason;
    }

    public String getOperatorTags() {
        return operatorTags;
    }

    public void setOperatorTags(String operatorTags) {
        this.operatorTags = operatorTags;
    }

    public Long getLastDetectionJobId() {
        return lastDetectionJobId;
    }

    public void setLastDetectionJobId(Long lastDetectionJobId) {
        this.lastDetectionJobId = lastDetectionJobId;
    }

    public OffsetDateTime getPublishedAt() {
        return publishedAt;
    }

    public void setPublishedAt(OffsetDateTime publishedAt) {
        this.publishedAt = publishedAt;
    }

    public OffsetDateTime getSuspendedAt() {
        return suspendedAt;
    }

    public void setSuspendedAt(OffsetDateTime suspendedAt) {
        this.suspendedAt = suspendedAt;
    }

    public String getSuspendReason() {
        return suspendReason;
    }

    public void setSuspendReason(String suspendReason) {
        this.suspendReason = suspendReason;
    }
}
