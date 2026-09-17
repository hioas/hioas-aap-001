package com.hioas.aap.iam;

import java.time.OffsetDateTime;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * 验证码校验的「留痕写入」：**独立事务**（REQUIRES_NEW）。
 *
 * <p>为什么必须独立：登录（{@code AuthService.smsLogin}）本身跑在一个事务里，
 * 而校验失败要抛业务异常终止登录——若失败计数与锁定跟外层同事务，异常一回滚就全丢了，
 * AC-04「连续 5 次错锁 15 分钟」永远不生效。这里用 REQUIRES_NEW 挂起外层事务，
 * 让「错误次数 + 锁定时间」先落库提交，再由调用方抛异常。
 */
@Component
public class SmsAttemptRecorder {

    private final SmsCodeMapper smsCodeMapper;

    public SmsAttemptRecorder(SmsCodeMapper smsCodeMapper) {
        this.smsCodeMapper = smsCodeMapper;
    }

    /** 记录一次校验失败（含达到上限时的锁定时间）。 */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordFailure(Long smsCodeId, int attempts, OffsetDateTime lockedUntil, boolean locked) {
        SmsCodeEntity record = smsCodeMapper.selectOneById(smsCodeId);
        if (record == null) {
            return;
        }
        record.setAttemptCount(attempts);
        if (locked) {
            record.setLockedUntil(lockedUntil);
        }
        smsCodeMapper.update(record);
    }

    /** 标记验证码已使用（一次性）。 */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void markUsed(Long smsCodeId, OffsetDateTime usedAt) {
        SmsCodeEntity record = smsCodeMapper.selectOneById(smsCodeId);
        if (record == null) {
            return;
        }
        record.setUsedAt(usedAt);
        smsCodeMapper.update(record);
    }
}
