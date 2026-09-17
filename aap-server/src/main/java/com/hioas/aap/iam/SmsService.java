package com.hioas.aap.iam;

import com.hioas.aap.common.ApiErrorDetail;
import com.hioas.aap.common.ApiException;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.config.AppProperties;
import com.mybatisflex.core.query.QueryWrapper;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 短信验证码服务（真源：R-02 与 AC-03/AC-04）。
 *
 * <p>规则：
 * <ul>
 *   <li>验证码 6 位、有效期 300s（{@code app.sms.ttl-seconds}）</li>
 *   <li>同手机号 60s 内不可重复发送 → {@code E-1903}</li>
 *   <li>连续 5 次校验失败 → 锁定 15 分钟（其间即使码正确也拒绝，{@code E-1903}）</li>
 *   <li>只存 {@code SHA-256(code)}，不落明文；用后即置 {@code used_at}（一次性）</li>
 * </ul>
 */
@Service
public class SmsService {

    private static final Logger log = LoggerFactory.getLogger(SmsService.class);

    private final SmsCodeMapper smsCodeMapper;
    private final SmsAttemptRecorder attemptRecorder;
    private final CryptoService crypto;
    private final AppProperties.Sms config;

    public SmsService(SmsCodeMapper smsCodeMapper, SmsAttemptRecorder attemptRecorder,
                      CryptoService crypto, AppProperties properties) {
        this.smsCodeMapper = smsCodeMapper;
        this.attemptRecorder = attemptRecorder;
        this.crypto = crypto;
        this.config = properties.sms();
    }

    /** 发送验证码：写库 + 交给短信网关（本期为日志适配器，不接真实通道）。 */
    @Transactional
    public SentCode send(String phone, String clientIp) {
        String phoneHash = crypto.sha256Hex(phone);
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);

        latest(phoneHash).ifPresent(latest -> {
            if (latest.getLockedUntil() != null && latest.getLockedUntil().isAfter(now)) {
                throw new ApiException(ErrorCode.E_1903, "尝试过于频繁，请 15 分钟后再试");
            }
            if (latest.getSentAt() != null
                    && latest.getSentAt().plusSeconds(config.resendIntervalSeconds()).isAfter(now)) {
                throw new ApiException(ErrorCode.E_1903,
                        "验证码发送过于频繁，请 " + config.resendIntervalSeconds() + " 秒后重试");
            }
        });

        String code = crypto.randomNumericCode(6);
        SmsCodeEntity entity = new SmsCodeEntity();
        entity.setPhoneHash(phoneHash);
        entity.setPhoneMasked(crypto.maskPhone(phone));
        entity.setScene("LOGIN");
        entity.setCodeHash(crypto.sha256Hex(code));
        entity.setSentAt(now);
        entity.setExpireAt(now.plusSeconds(config.ttlSeconds()));
        entity.setAttemptCount(0);
        entity.setClientIp(clientIp);
        smsCodeMapper.insert(entity);

        // 网关适配：真实通道接入前只记录「已下发」，绝不把验证码写进日志
        log.info("短信验证码已下发 phone={} scene=LOGIN ttl={}s (不记录验证码)", entity.getPhoneMasked(), config.ttlSeconds());
        return new SentCode(config.ttlSeconds(), entity.getExpireAt(), config.exposeCode() ? code : null);
    }

    /**
     * 校验验证码：成功则标记已用；失败累计次数并在达到上限时锁定。
     *
     * <p>★ 本方法**不加 {@code @Transactional}**，且失败/成功的落库都交给
     * {@link SmsAttemptRecorder}（REQUIRES_NEW 独立事务）。原因：本方法通常被
     * {@code AuthService.smsLogin}（外层事务）调用，而失败路径必须「先落库错误次数与锁定，再抛业务异常」；
     * 若与登录同事务，异常回滚会把计数与锁定一起抹掉，AC-04 永不生效。
     */
    public void verify(String phone, String code) {
        String phoneHash = crypto.sha256Hex(phone);
        OffsetDateTime now = OffsetDateTime.now(ZoneOffset.UTC);

        SmsCodeEntity record = latestUsable(phoneHash, now)
                .orElseThrow(() -> new ApiException(ErrorCode.E_1001, "验证码不存在或已过期，请重新获取"));

        if (record.getLockedUntil() != null && record.getLockedUntil().isAfter(now)) {
            throw new ApiException(ErrorCode.E_1903, "验证码错误次数过多，请 15 分钟后再试");
        }

        if (!crypto.sha256Hex(code).equals(record.getCodeHash())) {
            int attempts = (record.getAttemptCount() == null ? 0 : record.getAttemptCount()) + 1;
            boolean lock = attempts >= config.maxAttempts();
            OffsetDateTime lockedUntil = lock ? now.plusMinutes(config.lockMinutes()) : null;
            attemptRecorder.recordFailure(record.getId(), attempts, lockedUntil, lock);
            if (lock) {
                log.warn("验证码连续错误达 {} 次，锁定 {} 分钟 phone={}",
                        attempts, config.lockMinutes(), record.getPhoneMasked());
            }
            throw new ApiException(ErrorCode.E_1001, "验证码不正确",
                    List.of(new ApiErrorDetail("smsCode", "验证码不正确")));
        }

        attemptRecorder.markUsed(record.getId(), now);
    }

    private Optional<SmsCodeEntity> latest(String phoneHash) {
        return Optional.ofNullable(smsCodeMapper.selectOneByQuery(QueryWrapper.create()
                .where("phone_hash = ?", phoneHash)
                .orderBy("sent_at desc")
                .limit(1)));
    }

    /** 最近一条「未使用」的验证码（含已锁定记录——锁定判断在调用处）。 */
    private Optional<SmsCodeEntity> latestUsable(String phoneHash, OffsetDateTime now) {
        return Optional.ofNullable(smsCodeMapper.selectOneByQuery(QueryWrapper.create()
                .where("phone_hash = ?", phoneHash)
                .and("used_at is null")
                .orderBy("sent_at desc")
                .limit(1)));
    }

    /** 发送结果；{@code devCode} 仅在 {@code app.sms.expose-code=true}（测试环境）时非空。 */
    public record SentCode(int ttl, OffsetDateTime expireAt, String devCode) {
    }
}
