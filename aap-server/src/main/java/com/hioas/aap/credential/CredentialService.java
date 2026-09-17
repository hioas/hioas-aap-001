package com.hioas.aap.credential;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.AuditContext;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.DocNoGenerator;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.OutboundUrlGuard;
import com.hioas.aap.common.PageQuery;
import com.hioas.aap.common.PageResult;
import com.hioas.aap.detection.DetectionJobEntity;
import com.hioas.aap.detection.DetectionJobMapper;
import com.hioas.aap.iam.AuthPrincipal;
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
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 测试凭证服务（接口 CRED-01…07；AC-07…13、AC-29/30/48）。
 *
 * <p>安全要点：
 * <ul>
 *   <li>api_key 以 AES-256-GCM 密文落库，指纹 SHA-256 去重，接口只回 {@code sk-****abcd}</li>
 *   <li>base_url 规范化（去尾斜杠、保留 {@code /v1}，R-04）+ SSRF 校验（R-07）</li>
 *   <li>同供应商同指纹重复 → {@code E-1104}；同供应商仅 1 条主凭证（C1，新主凭证自动降级旧主）</li>
 *   <li>预检 401/403 不重试；预检通过即建检测任务（C2 互斥 → {@code E-1301}）</li>
 *   <li>明文读取仅超管 + 短信二次验证 + 写 SENSITIVE 审计（R-05/AC-30）</li>
 * </ul>
 */
@Service
public class CredentialService {

    private static final Logger log = LoggerFactory.getLogger(CredentialService.class);
    private static final DateTimeFormatter RFC3339 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private final CredentialMapper credentialMapper;
    private final CredentialPrecheckMapper precheckMapper;
    private final CredentialPrecheckRecorder precheckRecorder;
    private final DetectionJobMapper detectionJobMapper;
    private final CryptoService crypto;
    private final OutboundUrlGuard urlGuard;
    private final UpstreamProbe upstreamProbe;
    private final DocNoGenerator docNoGenerator;
    private final AuditService auditService;
    private final com.hioas.aap.iam.SmsService smsService;
    private final com.hioas.aap.iam.AdminUserMapper adminUserMapper;
    private final int probeTimeoutSeconds;

    public CredentialService(CredentialMapper credentialMapper, CredentialPrecheckMapper precheckMapper,
                             CredentialPrecheckRecorder precheckRecorder,
                             DetectionJobMapper detectionJobMapper, CryptoService crypto,
                             OutboundUrlGuard urlGuard, UpstreamProbe upstreamProbe,
                             DocNoGenerator docNoGenerator, AuditService auditService,
                             com.hioas.aap.iam.SmsService smsService,
                             com.hioas.aap.iam.AdminUserMapper adminUserMapper,
                             @org.springframework.beans.factory.annotation.Value("${app.detection.probe-timeout-seconds:10}")
                             int probeTimeoutSeconds) {
        this.credentialMapper = credentialMapper;
        this.precheckMapper = precheckMapper;
        this.precheckRecorder = precheckRecorder;
        this.detectionJobMapper = detectionJobMapper;
        this.crypto = crypto;
        this.urlGuard = urlGuard;
        this.upstreamProbe = upstreamProbe;
        this.docNoGenerator = docNoGenerator;
        this.auditService = auditService;
        this.smsService = smsService;
        this.adminUserMapper = adminUserMapper;
        this.probeTimeoutSeconds = probeTimeoutSeconds;
    }

    /** 请求体命令（创建/更新共用可写子集）。 */
    public record CredentialCommand(String alias, String baseUrl, String apiKey, Boolean primaryFlag,
                                    String declaredVendor, Integer declaredRpm, Integer declaredTpm,
                                    Integer declaredContextWindow, List<Map<String, Object>> modelList,
                                    String envTag) {
    }

    // ------------------------------------------------------------------ CRED-01/02/03/04

    /** CRED-02 创建凭证。 */
    @Transactional
    public CredentialViews.Detail create(AuthPrincipal principal, CredentialCommand command) {
        Long providerId = requireProviderId(principal);
        String baseUrl = normalizeBaseUrl(command.baseUrl());
        urlGuard.verify(baseUrl);

        String apiKey = command.apiKey();
        String fingerprint = crypto.sha256Hex(apiKey);
        ensureFingerprintUnique(providerId, fingerprint, null);

        CredentialEntity entity = new CredentialEntity();
        entity.setProviderId(providerId);
        entity.setAlias(command.alias());
        entity.setBaseUrl(baseUrl);
        entity.setApiKeyCipher(crypto.encrypt(apiKey));
        entity.setApiKeyMask(crypto.maskApiKey(apiKey));
        entity.setApiKeyFingerprint(fingerprint);
        entity.setDeclaredVendor(command.declaredVendor());
        entity.setDeclaredRpm(command.declaredRpm());
        entity.setDeclaredTpm(command.declaredTpm());
        entity.setDeclaredContextWindow(command.declaredContextWindow());
        entity.setModelList(command.modelList() == null ? null : JsonCodec.toJson(command.modelList()));
        entity.setEnvTag(command.envTag());
        entity.setStatus("PENDING_PRECHECK");
        entity.setDetectionStatus("PENDING");
        entity.setPrecheckPassed(false);
        boolean primary = Boolean.TRUE.equals(command.primaryFlag());
        entity.setPrimaryFlag(primary);
        if (primary) {
            demoteExistingPrimary(providerId);
        }
        credentialMapper.insert(entity);

        log.info("凭证创建 credential_id={} provider_id={} mask={}", entity.getId(), providerId, entity.getApiKeyMask());
        return toDetail(entity);
    }

    /** CRED-03 详情。 */
    public CredentialViews.Detail detail(AuthPrincipal principal, Long credentialId) {
        return toDetail(requireOwned(principal, credentialId));
    }

    /** CRED-01 列表（最近接入优先）。 */
    public PageResult<CredentialViews.Row> list(AuthPrincipal principal, Integer page, Integer pageSize,
                                                String status) {
        Long providerId = requireProviderId(principal);
        PageQuery pageQuery = PageQuery.of(page, pageSize);
        QueryWrapper query = QueryWrapper.create()
                .where("provider_id = ?", providerId)
                .orderBy("created_at desc, id desc");
        if (status != null && !status.isBlank()) {
            query.and("detection_status = ?", status.toUpperCase(Locale.ROOT));
        }
        Page<CredentialEntity> result = credentialMapper.paginate(
                Page.of(pageQuery.page(), pageQuery.pageSize()), query);
        List<CredentialViews.Row> rows = result.getRecords().stream().map(CredentialService::toRow).toList();
        return PageResult.of(rows, pageQuery.page(), pageQuery.pageSize(), result.getTotalRow());
    }

    /** CRED-04 更新（可轮换 api_key）。 */
    @Transactional
    public CredentialViews.Detail update(AuthPrincipal principal, Long credentialId, CredentialCommand command,
                                        String ifMatch) {
        CredentialEntity entity = requireOwned(principal, credentialId);
        if (ifMatch != null && !ifMatch.isBlank()
                && !ifMatch.trim().equals(String.valueOf(entity.getVersion()))) {
            throw new ApiException(ErrorCode.E_1601, "凭证已被更新，请刷新后重试");
        }
        if (command.baseUrl() != null && !command.baseUrl().isBlank()) {
            String baseUrl = normalizeBaseUrl(command.baseUrl());
            urlGuard.verify(baseUrl);
            entity.setBaseUrl(baseUrl);
        }
        if (command.apiKey() != null && !command.apiKey().isBlank()) {
            String fingerprint = crypto.sha256Hex(command.apiKey());
            ensureFingerprintUnique(entity.getProviderId(), fingerprint, entity.getId());
            entity.setApiKeyCipher(crypto.encrypt(command.apiKey()));
            entity.setApiKeyMask(crypto.maskApiKey(command.apiKey()));
            entity.setApiKeyFingerprint(fingerprint);
            // 轮换密钥后需重新预检
            entity.setPrecheckPassed(false);
            entity.setStatus("PENDING_PRECHECK");
        }
        if (command.alias() != null) {
            entity.setAlias(command.alias());
        }
        if (command.declaredVendor() != null) {
            entity.setDeclaredVendor(command.declaredVendor());
        }
        if (command.declaredRpm() != null) {
            entity.setDeclaredRpm(command.declaredRpm());
        }
        if (command.declaredTpm() != null) {
            entity.setDeclaredTpm(command.declaredTpm());
        }
        if (command.declaredContextWindow() != null) {
            entity.setDeclaredContextWindow(command.declaredContextWindow());
        }
        if (command.modelList() != null) {
            entity.setModelList(JsonCodec.toJson(command.modelList()));
        }
        if (command.envTag() != null) {
            entity.setEnvTag(command.envTag());
        }
        if (Boolean.TRUE.equals(command.primaryFlag()) && !Boolean.TRUE.equals(entity.getPrimaryFlag())) {
            demoteExistingPrimary(entity.getProviderId());
            entity.setPrimaryFlag(true);
        }
        credentialMapper.update(entity);
        return toDetail(entity);
    }

    // ------------------------------------------------------------------ CRED-05/06

    /** CRED-05 提交检测（预检 + 建任务入队）。 */
    public CredentialViews.PrecheckResult precheck(AuthPrincipal principal, Long credentialId) {
        CredentialEntity entity = requireOwned(principal, credentialId);
        String baseUrl = entity.getBaseUrl();
        urlGuard.verify(baseUrl);

        // C2：同凭证同时仅 1 个活跃检测任务（E-1301）
        if (hasActiveJob(entity.getId())) {
            throw new ApiException(ErrorCode.E_1301, "该凭证已有进行中的检测任务，请等待完成或取消后再提交");
        }

        String apiKey = crypto.decrypt(entity.getApiKeyCipher());
        UpstreamProbe.ProbeResult probe = upstreamProbe.probe(baseUrl, apiKey, probeTimeoutSeconds);

        CredentialPrecheckEntity record = new CredentialPrecheckEntity();
        record.setCredentialId(entity.getId());
        record.setStatus(probe.connectivityOk() && probe.authOk() ? "PASSED" : "FAILED");
        record.setConnectivityOk(probe.connectivityOk());
        record.setAuthOk(probe.authOk());
        record.setModelsOk(probe.modelsOk());
        record.setErrorCode(probe.errorCode());
        record.setErrorMsg(probe.errorMsg());
        record.setLatencyMs(probe.latencyMs());
        record.setCheckedAt(OffsetDateTime.now(ZoneOffset.UTC));

        // ★ 失败与成功都走独立事务落库（见 CredentialPrecheckRecorder 注释）：
        //   失败要「先落库再抛 E-1101」，成功要「凭证状态 + 任务入队同事务」。
        if (!"PASSED".equals(record.getStatus())) {
            precheckRecorder.recordFailure(entity.getId(), record);
            throw new ApiException(ErrorCode.E_1101,
                    probe.errorMsg() == null ? "凭证预检失败" : probe.errorMsg());
        }

        DetectionJobEntity job = precheckRecorder.recordSuccess(entity.getId(), entity.getProviderId(), record);
        return new CredentialViews.PrecheckResult(
                String.valueOf(job.getId()), String.valueOf(job.getId()), job.getJobNo(),
                "PASSED", "ACTIVE", probe.models());
    }

    /** CRED-06 最新预检记录。 */
    public CredentialViews.Precheck latestPrecheck(AuthPrincipal principal, Long credentialId) {
        CredentialEntity entity = requireOwned(principal, credentialId);
        CredentialPrecheckEntity record = precheckMapper.selectOneByQuery(QueryWrapper.create()
                .where("credential_id = ?", entity.getId())
                .orderBy("checked_at desc, id desc")
                .limit(1));
        if (record == null) {
            throw new ApiException(ErrorCode.E_1101, "尚无预检记录");
        }
        return new CredentialViews.Precheck(
                String.valueOf(record.getId()), String.valueOf(record.getCredentialId()), record.getStatus(),
                record.getConnectivityOk(), record.getAuthOk(), record.getModelsOk(),
                record.getErrorCode(), record.getErrorMsg(), record.getLatencyMs(),
                RFC3339.format(record.getCheckedAt().withOffsetSameInstant(ZoneOffset.UTC)));
    }

    // ------------------------------------------------------------------ CRED-07

    /** CRED-07 明文读取（仅超管 + 短信二次验证 + 审计）。 */
    public CredentialViews.Reveal reveal(AuthPrincipal principal, Long credentialId, String smsCode,
                                         String clientIp) {
        if (principal == null || !"SUPER_ADMIN".equals(principal.role())) {
            throw new ApiException(ErrorCode.E_1901, "仅超级管理员可访问凭证明文");
        }
        AdminAccount admin = requireAdminPhone(principal.accountId());
        smsService.verifyByPhoneHash(admin.phoneHash(), smsCode);

        CredentialEntity entity = credentialMapper.selectOneById(credentialId);
        if (entity == null) {
            throw new ApiException(ErrorCode.E_1406, "凭证不存在");
        }
        Map<String, Object> after = new LinkedHashMap<>();
        after.put("credential_id", String.valueOf(entity.getId()));
        after.put("api_key_mask", entity.getApiKeyMask());
        after.put("reason", "超管二次验证后读取明文");
        AuditContext.set(new AuditContext.Actor(principal.accountId(), "ADMIN", "SUPER_ADMIN", clientIp));
        auditService.record(AuditService.AuditAction.CREDENTIAL_REVEAL, "credential", entity.getId(),
                "读取凭证 api_key 明文（mask=" + entity.getApiKeyMask() + "）", null, after, "SENSITIVE");

        String plain = crypto.decrypt(entity.getApiKeyCipher());
        return new CredentialViews.Reveal(plain,
                RFC3339.format(OffsetDateTime.now(ZoneOffset.UTC).plusMinutes(5)));
    }

    /** 供其它上下文（检测/同步）复用：按 id 取解密后的 api_key，并刷新 last_used_at。 */
    @Transactional
    public String secretOf(Long credentialId) {
        CredentialEntity entity = credentialMapper.selectOneById(credentialId);
        if (entity == null) {
            throw new ApiException(ErrorCode.E_1303, "凭证不存在");
        }
        entity.setLastUsedAt(OffsetDateTime.now(ZoneOffset.UTC));
        credentialMapper.update(entity);
        return crypto.decrypt(entity.getApiKeyCipher());
    }

    // ------------------------------------------------------------------ 内部

    private boolean hasActiveJob(Long credentialId) {
        return detectionJobMapper.selectCountByQuery(QueryWrapper.create()
                .where("credential_id = ?", credentialId)
                .and("active_flag = true")) > 0;
    }

    private void ensureFingerprintUnique(Long providerId, String fingerprint, Long selfId) {
        QueryWrapper query = QueryWrapper.create()
                .where("provider_id = ?", providerId)
                .and("api_key_fingerprint = ?", fingerprint);
        if (selfId != null) {
            query.and("id <> ?", selfId);
        }
        if (credentialMapper.selectCountByQuery(query) > 0) {
            throw new ApiException(ErrorCode.E_1104, "该 APIKey 已提交过（指纹重复）",
                    List.of(new ApiErrorDetail("api_key", "同一供应商下 APIKey 不可重复提交")));
        }
    }

    private void demoteExistingPrimary(Long providerId) {
        List<CredentialEntity> primaries = credentialMapper.selectListByQuery(QueryWrapper.create()
                .where("provider_id = ?", providerId)
                .and("primary_flag = true"));
        for (CredentialEntity primary : primaries) {
            primary.setPrimaryFlag(false);
            credentialMapper.update(primary);
        }
    }

    private CredentialEntity requireOwned(AuthPrincipal principal, Long credentialId) {
        Long providerId = requireProviderId(principal);
        CredentialEntity entity = credentialMapper.selectOneById(credentialId);
        if (entity == null) {
            throw new ApiException(ErrorCode.E_1406, "凭证不存在");
        }
        if (!entity.getProviderId().equals(providerId)) {
            throw new ApiException(ErrorCode.E_1901, "无权访问该凭证");
        }
        return entity;
    }

    private Long requireProviderId(AuthPrincipal principal) {
        if (principal == null || principal.providerId() == null) {
            throw new ApiException(ErrorCode.E_1901, "当前账号未绑定供应商主体");
        }
        return principal.providerId();
    }

    /** R-04：小写化、去尾斜杠，但保留 {@code /v1} 路径段。 */
    static String normalizeBaseUrl(String raw) {
        if (raw == null) {
            return null;
        }
        String url = raw.trim();
        if (url.isEmpty()) {
            return url;
        }
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        // scheme://host 小写化（路径大小写敏感，保留原样）
        int schemeEnd = url.indexOf("://");
        if (schemeEnd > 0) {
            String scheme = url.substring(0, schemeEnd).toLowerCase(Locale.ROOT);
            String rest = url.substring(schemeEnd + 3);
            int slash = rest.indexOf('/');
            if (slash < 0) {
                rest = rest.toLowerCase(Locale.ROOT);
            } else {
                rest = rest.substring(0, slash).toLowerCase(Locale.ROOT) + rest.substring(slash);
            }
            url = scheme + "://" + rest;
        }
        return url;
    }

    private CredentialViews.Detail toDetail(CredentialEntity entity) {
        return new CredentialViews.Detail(
                String.valueOf(entity.getId()),
                entity.getProviderId() == null ? null : String.valueOf(entity.getProviderId()),
                entity.getAlias(), entity.getBaseUrl(), entity.getApiKeyMask(), entity.getApiKeyMask(),
                Boolean.TRUE.equals(entity.getPrimaryFlag()), Boolean.TRUE.equals(entity.getPrimaryFlag()),
                entity.getDeclaredVendor(), entity.getDeclaredRpm(), entity.getDeclaredTpm(),
                entity.getDeclaredContextWindow(), parseModelList(entity.getModelList()), entity.getEnvTag(),
                entity.getStatus(), entity.getDetectionStatus(),
                entity.getLatestReportId() == null ? null : String.valueOf(entity.getLatestReportId()),
                entity.getPrecheckPassed(), format(entity.getPrecheckAt()),
                format(entity.getCreatedAt()), format(entity.getUpdatedAt()), entity.getVersion());
    }

    private static CredentialViews.Row toRow(CredentialEntity entity) {
        return new CredentialViews.Row(
                String.valueOf(entity.getId()), entity.getAlias(), entity.getBaseUrl(), entity.getApiKeyMask(),
                parseModelList(entity.getModelList()), format(entity.getCreatedAt()),
                entity.getDetectionStatus(),
                entity.getLatestReportId() == null ? null : String.valueOf(entity.getLatestReportId()),
                entity.getStatus(), Boolean.TRUE.equals(entity.getPrimaryFlag()));
    }

    private static List<Map<String, Object>> parseModelList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<Map<String, Object>> parsed = JsonCodec.fromJson(json, new tools.jackson.core.type.TypeReference<>() {
            });
            return parsed == null ? List.of() : new ArrayList<>(parsed);
        } catch (RuntimeException e) {
            return List.of();
        }
    }

    private static String format(OffsetDateTime value) {
        return value == null ? null : RFC3339.format(value.withOffsetSameInstant(ZoneOffset.UTC));
    }

    private record AdminAccount(String phoneHash) {
    }

    private AdminAccount requireAdminPhone(Long accountId) {
        var admin = adminUserMapper.selectOneById(accountId);
        if (admin == null || admin.getPhoneHash() == null) {
            throw new ApiException(ErrorCode.E_1901, "当前管理员未绑定手机号，无法完成二次验证");
        }
        return new AdminAccount(admin.getPhoneHash());
    }
}
