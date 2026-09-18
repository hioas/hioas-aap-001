package com.hioas.aap.provider;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.iam.AuthPrincipal;
import com.hioas.aap.iam.ProviderAccountEntity;
import com.hioas.aap.iam.ProviderAccountMapper;
import com.hioas.aap.support.AuditService;
import com.mybatisflex.core.paginate.Page;
import com.mybatisflex.core.query.QueryWrapper;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 供应商档案与资质（接口 PROV-01…05；AC-06）。
 *
 * <p>关键规则：
 * <ul>
 *   <li>uscc 全平台唯一 → 冲突 {@code E-1104}</li>
 *   <li>联系手机号密文 + hash + mask 三件套，**接口只回脱敏值**（R-48）</li>
 *   <li>人工放行 {@code manual_override=true} 时必须给 {@code override_reason}（R-47a）</li>
 *   <li>{@code If-Match} 与当前 version 不一致 → {@code E-1601}（不覆盖他人改动）</li>
 *   <li>资质文件：扩展名白名单（jpg/jpeg/png/pdf）+ 单文件 ≤10MB</li>
 * </ul>
 */
@Service
public class ProviderService {

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("jpg", "jpeg", "png", "pdf");
    private static final long MAX_FILE_BYTES = 10L * 1024 * 1024;
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    /** 完整度口径（服务端唯一口径，避免前后端各算一套）：全部填齐 = 100。 */
    private static final List<String> COMPLETENESS_FIELDS = List.of(
            "short_name", "company_name", "uscc", "industry_category", "province", "city", "address",
            "contact_name", "contact_phone", "contact_email", "company_intro");

    private final ProviderMapper providerMapper;
    private final QualificationMapper qualificationMapper;
    private final ProviderAccountMapper accountMapper;
    private final CryptoService crypto;
    private final AuditService auditService;
    private final org.springframework.jdbc.core.JdbcTemplate jdbc;

    public ProviderService(ProviderMapper providerMapper, QualificationMapper qualificationMapper,
                           ProviderAccountMapper accountMapper, CryptoService crypto, AuditService auditService,
                           org.springframework.jdbc.core.JdbcTemplate jdbc) {
        this.providerMapper = providerMapper;
        this.qualificationMapper = qualificationMapper;
        this.accountMapper = accountMapper;
        this.crypto = crypto;
        this.auditService = auditService;
        this.jdbc = jdbc;
    }

    /** PROV-01 档案查询。 */
    public ProviderProfileResponse profile(AuthPrincipal principal) {
        return toResponse(requireProvider(principal));
    }

    /** PROV-01（管理端）按 id 查询。 */
    public ProviderProfileResponse profileById(Long providerId) {
        ProviderEntity provider = providerMapper.selectOneById(providerId);
        if (provider == null) {
            throw new ApiException(ErrorCode.E_1406, "供应商不存在");
        }
        return toResponse(provider);
    }

    /**
     * PROV-02 保存档案。
     *
     * @param ifMatch 若提供，必须与当前 version 相等（乐观锁）
     */
    @Transactional
    public ProviderProfileResponse updateProfile(AuthPrincipal principal, UpdateProfileCommand command, String ifMatch) {
        ProviderEntity provider = requireProvider(principal);

        if (ifMatch != null && !ifMatch.isBlank()
                && !ifMatch.trim().equals(String.valueOf(provider.getVersion()))) {
            throw new ApiException(ErrorCode.E_1601, "档案已被更新，请刷新后重试");
        }
        if (command.uscc() != null && !command.uscc().isBlank()) {
            ensureUsccUnique(command.uscc(), provider.getId());
        }
        if (Boolean.TRUE.equals(command.manualOverride())
                && (command.overrideReason() == null || command.overrideReason().isBlank())) {
            throw new ApiException(ErrorCode.E_1001, "人工放行必须填写理由",
                    List.of(new ApiErrorDetail("override_reason", "人工放行必须填写理由")));
        }

        Map<String, Object> before = snapshot(provider);

        applyText(command.shortName(), provider::setShortName);
        applyText(command.companyName(), provider::setCompanyName);
        applyText(command.uscc(), provider::setUscc);
        applyText(command.industryCategory(), provider::setIndustryCategory);
        applyText(command.province(), provider::setProvince);
        applyText(command.city(), provider::setCity);
        applyText(command.address(), provider::setAddress);
        applyText(command.website(), provider::setWebsite);
        applyText(command.contactName(), provider::setContactName);
        applyText(command.contactTitle(), provider::setContactTitle);
        applyText(command.contactEmail(), provider::setContactEmail);
        applyText(command.companyIntro(), provider::setCompanyIntro);
        if (command.recheckIntervalDays() != null) {
            provider.setRecheckIntervalDays(command.recheckIntervalDays());
        }
        if (command.manualOverride() != null) {
            provider.setManualOverride(command.manualOverride());
        }
        if (command.overrideReason() != null) {
            provider.setOverrideReason(command.overrideReason());
        }
        if (command.contactPhone() != null && !command.contactPhone().isBlank()) {
            provider.setContactPhoneCipher(crypto.encrypt(command.contactPhone()));
            provider.setContactPhoneHash(crypto.sha256Hex(command.contactPhone()));
            provider.setContactPhoneMask(crypto.maskPhone(command.contactPhone()));
        }
        if (provider.getShortCode() == null && provider.getShortName() != null) {
            provider.setShortCode(provider.getShortName());
        }
        provider.setCompleteness((short) computeCompleteness(provider));

        providerMapper.update(provider);

        auditService.record(AuditService.AuditAction.PROFILE_UPDATE, "provider", provider.getId(),
                "更新供应商档案", before, snapshot(provider), "NORMAL");

        return toResponse(provider);
    }

    /** PROV-03 资质列表。 */
    public PageResult<Map<String, Object>> qualifications(AuthPrincipal principal, Integer page, Integer pageSize) {
        ProviderEntity provider = requireProvider(principal);
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        Page<QualificationEntity> result = qualificationMapper.paginate(Page.of(pageQuery.page(), pageQuery.pageSize()),
                QueryWrapper.create()
                        .where("provider_id = ?", provider.getId())
                        .orderBy("created_at desc, id desc"));
        List<Map<String, Object>> items = result.getRecords().stream().map(ProviderService::toQualificationView).toList();
        return PageResult.of(items, pageQuery.page(), pageQuery.pageSize(), result.getTotalRow());
    }

    /** PROV-04 资质登记（只登记元数据；文件本体走对象存储，本期不入库）。 */
    @Transactional
    public Map<String, Object> addQualification(AuthPrincipal principal, QualificationCommand command) {
        ProviderEntity provider = requireProvider(principal);
        String fileName = command.fileName() == null ? "" : command.fileName().trim();
        String extension = extensionOf(fileName);
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            throw new ApiException(ErrorCode.E_1001, "仅支持 jpg / jpeg / png / pdf 格式的资质文件",
                    List.of(new ApiErrorDetail("file_name", "仅支持 jpg / jpeg / png / pdf")));
        }
        if (command.fileSize() != null && command.fileSize() > MAX_FILE_BYTES) {
            throw new ApiException(ErrorCode.E_1001, "单个文件不超过 10MB",
                    List.of(new ApiErrorDetail("file_size", "单个文件不超过 10MB")));
        }

        QualificationEntity entity = new QualificationEntity();
        entity.setProviderId(provider.getId());
        entity.setCategory(command.category());
        entity.setFileId(command.fileId());
        entity.setFileName(fileName);
        entity.setFileSize(command.fileSize());
        entity.setContentType(command.contentType());
        entity.setStatus("UPLOADED");
        entity.setUploadedAt(OffsetDateTime.now(ZoneOffset.UTC));
        qualificationMapper.insert(entity);

        return toQualificationView(entity);
    }

    /** PROV-05 删除资质（逻辑删除）。 */
    @Transactional
    public void removeQualification(AuthPrincipal principal, Long qualificationId) {
        ProviderEntity provider = requireProvider(principal);
        QualificationEntity entity = qualificationMapper.selectOneById(qualificationId);
        if (entity == null || !entity.getProviderId().equals(provider.getId())) {
            throw new ApiException(ErrorCode.E_1406, "资质不存在");
        }
        qualificationMapper.deleteById(qualificationId);
    }

    // ------------------------------------------------------------------ ADM-P01…03（管理端）

    /**
     * ADM-P01 管理端供应商列表（分页 + `status` / `keyword` 过滤）。
     *
     * <p>为什么用 JdbcTemplate 而不是 QueryWrapper：关键字要跨 5 列 `ilike` 的 OR 组合，
     * 显式 SQL 比链式条件更可读、也避免多占位符片段在不同版本上的行为差异；
     * 行的**映射**仍走 {@link #toResponse}（与 PROV-01 同一口径，不出现第二套字段映射）。
     * 逻辑删除由 SQL 显式过滤（`deleted = false`），与 ORM 侧同口径。
     */
    public PageResult<ProviderProfileResponse> adminList(Integer page, Integer pageSize, String status, String keyword) {
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        StringBuilder where = new StringBuilder(" where deleted = false");
        List<Object> filters = new ArrayList<>();
        if (status != null && !status.isBlank()) {
            where.append(" and upper(status) = ?");
            filters.add(status.trim().toUpperCase(Locale.ROOT));
        }
        if (keyword != null && !keyword.isBlank()) {
            where.append(" and (short_name ilike ? or company_name ilike ? or provider_no ilike ?"
                    + " or provider_code ilike ? or uscc ilike ?)");
            String like = "%" + keyword.trim() + "%";
            for (int i = 0; i < 5; i++) {
                filters.add(like);
            }
        }
        Long total = jdbc.queryForObject("select count(*) from aap_provider" + where, Long.class, filters.toArray());
        List<Object> pageParams = new ArrayList<>(filters);
        pageParams.add(pageQuery.pageSize());
        pageParams.add(pageQuery.offset());
        List<Long> ids = jdbc.queryForList("select id from aap_provider" + where
                + " order by created_at desc, id desc limit ? offset ?", Long.class, pageParams.toArray());
        if (ids.isEmpty()) {
            return PageResult.of(List.of(), pageQuery.page(), pageQuery.pageSize(), total == null ? 0L : total);
        }
        Map<Long, ProviderEntity> byId = new LinkedHashMap<>();
        for (ProviderEntity entity : providerMapper.selectListByIds(ids)) {
            byId.put(entity.getId(), entity);
        }
        List<ProviderProfileResponse> items = ids.stream()
                .map(byId::get)
                .filter(java.util.Objects::nonNull)
                .map(this::toResponse)
                .toList();
        return PageResult.of(items, pageQuery.page(), pageQuery.pageSize(), total == null ? 0L : total);
    }

    /**
     * ADM-P02 暂停供应商。
     *
     * <p>状态机：`SUSPENDED`（重复暂停）与 `TERMINATED`（已终止）一律 409 `E-1601`；
     * 其余状态可暂停，暂停前状态写入 `status_before_suspend` 供 ADM-P03 回填。
     * 响应取**写后重读**的库值（tdd-state 踩坑 17/18：乐观锁一挡就可能「响应说改了、库里没改」）。
     */
    @Transactional
    public ProviderProfileResponse suspend(AuthPrincipal principal, Long providerId, String suspendReason) {
        ProviderEntity provider = requireById(providerId);
        if ("SUSPENDED".equals(provider.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "供应商已处于暂停状态，无需重复暂停");
        }
        if ("TERMINATED".equals(provider.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "已终止的供应商不可暂停");
        }
        Map<String, Object> before = snapshot(provider);
        before.put("status", provider.getStatus());

        provider.setStatusBeforeSuspend(provider.getStatus());
        provider.setStatus("SUSPENDED");
        provider.setSuspendedAt(OffsetDateTime.now(ZoneOffset.UTC));
        provider.setSuspendReason(suspendReason.trim());
        // ignoreNulls=false：本次要写的字段全部非空，但保持与 resume 对称，避免下次改动踩空写陷阱
        if (providerMapper.update(provider, false) != 1) {
            throw new ApiException(ErrorCode.E_1601, "供应商状态已被他人改动，请刷新后重试");
        }
        ProviderEntity fresh = requireById(providerId);

        Map<String, Object> after = snapshot(fresh);
        after.put("status", fresh.getStatus());
        after.put("suspend_reason", fresh.getSuspendReason());
        auditService.record(AuditService.AuditAction.PROVIDER_SUSPEND, "provider", providerId,
                "暂停供应商：" + fresh.getSuspendReason(), before, after, "NORMAL");
        return toResponse(fresh);
    }

    /**
     * ADM-P03 恢复供应商：回到**暂停前状态**（`status_before_suspend`）并清空暂停留痕。
     *
     * <p>遗留数据（暂停前状态缺失，如迁移前被暂停的行）回退口径：有 `published_at` → `PUBLISHED`，
     * 否则 → `DETECT_PASSED`（偏差 `D-ADM-01`，见 tdd-state）。
     */
    @Transactional
    public ProviderProfileResponse resume(AuthPrincipal principal, Long providerId) {
        ProviderEntity provider = requireById(providerId);
        if (!"SUSPENDED".equals(provider.getStatus())) {
            throw new ApiException(ErrorCode.E_1601, "仅暂停中的供应商可恢复");
        }
        String restore = provider.getStatusBeforeSuspend();
        if (restore == null || restore.isBlank()) {
            restore = provider.getPublishedAt() != null ? "PUBLISHED" : "DETECT_PASSED";
        }
        Map<String, Object> before = snapshot(provider);
        before.put("status", provider.getStatus());

        provider.setStatus(restore);
        provider.setStatusBeforeSuspend(null);
        provider.setSuspendedAt(null);
        // ignoreNulls=false：必须把 status_before_suspend / suspended_at 真正清成 NULL
        // （默认的 update(entity) 会忽略 null 字段 → 留痕清不掉、下次暂停复用旧值）
        if (providerMapper.update(provider, false) != 1) {
            throw new ApiException(ErrorCode.E_1601, "供应商状态已被他人改动，请刷新后重试");
        }
        ProviderEntity fresh = requireById(providerId);

        Map<String, Object> after = snapshot(fresh);
        after.put("status", fresh.getStatus());
        auditService.record(AuditService.AuditAction.PROVIDER_RESUME, "provider", providerId,
                "恢复供应商（回 " + restore + "）", before, after, "NORMAL");
        return toResponse(fresh);
    }

    private ProviderEntity requireById(Long providerId) {
        ProviderEntity provider = providerMapper.selectOneById(providerId);
        if (provider == null) {
            throw new ApiException(ErrorCode.E_1406, "供应商不存在");
        }
        return provider;
    }

    // ------------------------------------------------------------------ 内部

    private ProviderEntity requireProvider(AuthPrincipal principal) {
        if (principal == null) {
            throw new ApiException(ErrorCode.E_1902, "未认证或登录已过期");
        }
        ProviderEntity provider = principal.providerId() == null ? null : providerMapper.selectOneById(principal.providerId());
        if (provider == null) {
            provider = providerMapper.selectOneByQuery(QueryWrapper.create()
                    .where("account_id = ?", principal.accountId())
                    .limit(1));
        }
        if (provider == null) {
            throw new ApiException(ErrorCode.E_1406, "供应商主体不存在");
        }
        return provider;
    }

    private void ensureUsccUnique(String uscc, Long selfId) {
        long count = providerMapper.selectCountByQuery(QueryWrapper.create()
                .where("uscc = ?", uscc)
                .and("id <> ?", selfId));
        if (count > 0) {
            throw new ApiException(ErrorCode.E_1104, "统一社会信用代码已被其他供应商使用",
                    List.of(new ApiErrorDetail("uscc", "统一社会信用代码已被占用")));
        }
    }

    private int computeCompleteness(ProviderEntity provider) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("short_name", provider.getShortName());
        values.put("company_name", provider.getCompanyName());
        values.put("uscc", provider.getUscc());
        values.put("industry_category", provider.getIndustryCategory());
        values.put("province", provider.getProvince());
        values.put("city", provider.getCity());
        values.put("address", provider.getAddress());
        values.put("contact_name", provider.getContactName());
        values.put("contact_phone", provider.getContactPhoneCipher());
        values.put("contact_email", provider.getContactEmail());
        values.put("company_intro", provider.getCompanyIntro());
        long filled = COMPLETENESS_FIELDS.stream()
                .filter(field -> {
                    Object value = values.get(field);
                    return value instanceof String s ? !s.isBlank() : value != null;
                })
                .count();
        return (int) Math.round(filled * 100.0 / COMPLETENESS_FIELDS.size());
    }

    private Map<String, Object> snapshot(ProviderEntity provider) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("company_name", provider.getCompanyName());
        map.put("uscc", provider.getUscc());
        map.put("short_name", provider.getShortName());
        map.put("contact_name", provider.getContactName());
        // 脱敏后入审计（禁止明文，R-05/R-48）
        map.put("contact_phone_masked", provider.getContactPhoneMask());
        map.put("contact_email", provider.getContactEmail());
        map.put("recheck_interval_days", provider.getRecheckIntervalDays());
        map.put("manual_override", provider.getManualOverride());
        map.put("completeness", provider.getCompleteness());
        return map;
    }

    private ProviderProfileResponse toResponse(ProviderEntity provider) {
        ProviderAccountEntity account = provider.getAccountId() == null ? null
                : accountMapper.selectOneById(provider.getAccountId());
        List<ProviderProfileResponse.FileAsset> files = qualificationMapper.selectListByQuery(QueryWrapper.create()
                        .where("provider_id = ?", provider.getId())
                        .orderBy("created_at desc, id desc"))
                .stream()
                .map(q -> new ProviderProfileResponse.FileAsset(
                        q.getId() == null ? null : String.valueOf(q.getId()),
                        q.getFileName(), q.getFileSize(), q.getContentType(),
                        q.getUploadedAt() == null ? null : RFC3339.format(q.getUploadedAt().withOffsetSameInstant(ZoneOffset.UTC)),
                        q.getCategory()))
                .toList();

        return new ProviderProfileResponse(
                String.valueOf(provider.getId()),
                provider.getProviderNo(),
                provider.getProviderCode(),
                provider.getShortName(),
                provider.getShortCode(),
                provider.getCompanyName(),
                provider.getUscc(),
                provider.getIndustryCategory(),
                provider.getProvince(),
                provider.getCity(),
                provider.getAddress(),
                provider.getWebsite(),
                provider.getContactName(),
                provider.getContactTitle(),
                provider.getContactPhoneMask(),
                provider.getContactEmail(),
                provider.getCompanyIntro(),
                provider.getCompleteness() == null ? 0 : provider.getCompleteness(),
                files,
                provider.getStatus(),
                provider.getRecheckIntervalDays() == null ? 30 : provider.getRecheckIntervalDays(),
                Boolean.TRUE.equals(provider.getManualOverride()),
                provider.getOverrideReason(),
                new ProviderProfileResponse.ContactInfo(provider.getContactName(), provider.getContactPhoneMask(),
                        provider.getContactEmail(), provider.getContactTitle()),
                account == null ? null : new ProviderProfileResponse.AccountInfo(
                        account.getPhoneMasked(), account.getRole(), account.getWxOpenid() != null),
                provider.getCreatedAt() == null ? null : RFC3339.format(provider.getCreatedAt().withOffsetSameInstant(ZoneOffset.UTC)),
                provider.getUpdatedAt() == null ? null : RFC3339.format(provider.getUpdatedAt().withOffsetSameInstant(ZoneOffset.UTC)),
                provider.getVersion() == null ? 0 : provider.getVersion());
    }

    private static Map<String, Object> toQualificationView(QualificationEntity entity) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", String.valueOf(entity.getId()));
        map.put("qualification_id", String.valueOf(entity.getId()));
        map.put("category", entity.getCategory());
        map.put("file_id", entity.getFileId() == null ? null : String.valueOf(entity.getFileId()));
        map.put("file_name", entity.getFileName());
        map.put("file_size", entity.getFileSize());
        map.put("content_type", entity.getContentType());
        map.put("status", entity.getStatus());
        map.put("uploaded_at", entity.getUploadedAt() == null ? null
                : RFC3339.format(entity.getUploadedAt().withOffsetSameInstant(ZoneOffset.UTC)));
        return map;
    }

    private static String extensionOf(String fileName) {
        int dot = fileName.lastIndexOf('.');
        return dot > 0 ? fileName.substring(dot + 1).toLowerCase(Locale.ROOT) : "";
    }

    private static void applyText(String value, java.util.function.Consumer<String> setter) {
        if (value != null) {
            setter.accept(value.isBlank() ? null : value.trim());
        }
    }

    /** 档案写命令（对应 PUT /provider/profile 的请求体）。 */
    public record UpdateProfileCommand(
            String shortName, String companyName, String uscc, String industryCategory,
            String province, String city, String address, String website,
            String contactName, String contactTitle, String contactPhone, String contactEmail,
            String companyIntro, Integer recheckIntervalDays, Boolean manualOverride, String overrideReason) {
    }

    /** 资质登记命令（对应 POST /provider/qualifications）。 */
    public record QualificationCommand(
            String category, Long fileId, String fileName, Long fileSize, String contentType) {
    }
}
