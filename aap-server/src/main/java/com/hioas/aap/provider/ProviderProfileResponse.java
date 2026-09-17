package com.hioas.aap.provider;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * 供应商档案响应（契约：docs/backend/json-schema/models/provider-profile.schema.json）。
 *
 * <p>同时输出 camelCase 与 snake_case 关键字段：
 * `aap-client` 的工作台/档案页读 `companyName`、`providerCode`（camel），
 * 而项目决策 D-JSON-01 要求与数据字典同名（snake_case）。
 */
public class ProviderProfileResponse {

    public record ContactInfo(@JsonProperty("name") String name,
                              @JsonProperty("phone_masked") String phoneMasked,
                              @JsonProperty("email") String email,
                              @JsonProperty("title") String title) {
    }

    public record AccountInfo(@JsonProperty("phone_masked") String phoneMasked,
                              @JsonProperty("role") String role,
                              @JsonProperty("wx_bound") boolean wxBound) {
    }

    public record FileAsset(@JsonProperty("file_id") String fileId,
                            @JsonProperty("file_name") String fileName,
                            @JsonProperty("size") Long size,
                            @JsonProperty("content_type") String contentType,
                            @JsonProperty("uploaded_at") String uploadedAt,
                            @JsonProperty("type") String type) {
    }

    private final String providerId;
    private final String providerNo;
    private final String providerCode;
    private final String shortName;
    private final String shortCode;
    private final String companyName;
    private final String uscc;
    private final String industryCategory;
    private final String province;
    private final String city;
    private final String address;
    private final String website;
    private final String contactName;
    private final String contactTitle;
    private final String contactPhoneMasked;
    private final String contactEmail;
    private final String companyIntro;
    private final int completeness;
    private final List<FileAsset> qualificationFiles;
    private final String status;
    private final int recheckIntervalDays;
    private final boolean manualOverride;
    private final String overrideReason;
    private final ContactInfo contact;
    private final AccountInfo account;
    private final String createdAt;
    private final String updatedAt;
    private final int version;

    @SuppressWarnings("checkstyle:ParameterNumber")
    public ProviderProfileResponse(String providerId, String providerNo, String providerCode, String shortName,
                                    String shortCode, String companyName, String uscc, String industryCategory,
                                    String province, String city, String address, String website,
                                    String contactName, String contactTitle, String contactPhoneMasked,
                                    String contactEmail, String companyIntro, int completeness,
                                    List<FileAsset> qualificationFiles, String status, int recheckIntervalDays,
                                    boolean manualOverride, String overrideReason, ContactInfo contact,
                                    AccountInfo account, String createdAt, String updatedAt, int version) {
        this.providerId = providerId;
        this.providerNo = providerNo;
        this.providerCode = providerCode;
        this.shortName = shortName;
        this.shortCode = shortCode;
        this.companyName = companyName;
        this.uscc = uscc;
        this.industryCategory = industryCategory;
        this.province = province;
        this.city = city;
        this.address = address;
        this.website = website;
        this.contactName = contactName;
        this.contactTitle = contactTitle;
        this.contactPhoneMasked = contactPhoneMasked;
        this.contactEmail = contactEmail;
        this.companyIntro = companyIntro;
        this.completeness = completeness;
        this.qualificationFiles = qualificationFiles;
        this.status = status;
        this.recheckIntervalDays = recheckIntervalDays;
        this.manualOverride = manualOverride;
        this.overrideReason = overrideReason;
        this.contact = contact;
        this.account = account;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.version = version;
    }

    @JsonProperty("provider_id")
    public String getProviderId() {
        return providerId;
    }

    @JsonProperty("id")
    public String getId() {
        return providerId;
    }

    @JsonProperty("provider_no")
    public String getProviderNo() {
        return providerNo;
    }

    @JsonProperty("provider_code")
    public String getProviderCode() {
        return providerCode;
    }

    /** 客户端读 providerCode（camel）。 */
    @JsonProperty("providerCode")
    public String getProviderCodeCamel() {
        return providerCode;
    }

    @JsonProperty("short_name")
    public String getShortName() {
        return shortName;
    }

    @JsonProperty("short_code")
    public String getShortCode() {
        return shortCode;
    }

    @JsonProperty("company_name")
    public String getCompanyName() {
        return companyName;
    }

    /** 客户端读 companyName（camel）。 */
    @JsonProperty("companyName")
    public String getCompanyNameCamel() {
        return companyName;
    }

    @JsonProperty("uscc")
    public String getUscc() {
        return uscc;
    }

    @JsonProperty("unified_social_credit_code")
    public String getUnifiedSocialCreditCode() {
        return uscc;
    }

    @JsonProperty("industry_category")
    public String getIndustryCategory() {
        return industryCategory;
    }

    public String getProvince() {
        return province;
    }

    public String getCity() {
        return city;
    }

    public String getAddress() {
        return address;
    }

    public String getWebsite() {
        return website;
    }

    @JsonProperty("contact_name")
    public String getContactName() {
        return contactName;
    }

    @JsonProperty("contact_title")
    public String getContactTitle() {
        return contactTitle;
    }

    @JsonProperty("contact_phone_masked")
    public String getContactPhoneMasked() {
        return contactPhoneMasked;
    }

    /** 客户端档案页读 contact_phone（此处回脱敏值，后端永不回明文）。 */
    @JsonProperty("contact_phone")
    public String getContactPhone() {
        return contactPhoneMasked;
    }

    @JsonProperty("contact_email")
    public String getContactEmail() {
        return contactEmail;
    }

    @JsonProperty("company_intro")
    public String getCompanyIntro() {
        return companyIntro;
    }

    public int getCompleteness() {
        return completeness;
    }

    @JsonProperty("qualification_files")
    public List<FileAsset> getQualificationFiles() {
        return qualificationFiles;
    }

    public String getStatus() {
        return status;
    }

    @JsonProperty("recheck_interval_days")
    public int getRecheckIntervalDays() {
        return recheckIntervalDays;
    }

    @JsonProperty("manual_override")
    public boolean isManualOverride() {
        return manualOverride;
    }

    @JsonProperty("override_reason")
    public String getOverrideReason() {
        return overrideReason;
    }

    public ContactInfo getContact() {
        return contact;
    }

    public AccountInfo getAccount() {
        return account;
    }

    @JsonProperty("created_at")
    public String getCreatedAt() {
        return createdAt;
    }

    @JsonProperty("updated_at")
    public String getUpdatedAt() {
        return updatedAt;
    }

    @JsonProperty("version")
    public int getVersion() {
        return version;
    }

    /** 乐观锁令牌：PUT 时用 {@code If-Match: <etag>} 提交，过期则 409 E-1601。 */
    @JsonProperty("etag")
    public String getEtag() {
        return String.valueOf(version);
    }
}
