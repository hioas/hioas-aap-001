package com.hioas.aap.detection;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 复测调度（AC-49）。
 *
 * <p>默认**关闭**（`app.detection.recheck-enabled=false`）：本机与 CI 都是共享开发库，
 * 定时任务会与测试用例抢数据。生产开启后每小时扫描一次 {@link RecheckService#runOnce()}。
 */
@Component
@ConditionalOnProperty(name = "app.detection.recheck-enabled", havingValue = "true")
public class RecheckScheduler {

    private static final Logger log = LoggerFactory.getLogger(RecheckScheduler.class);

    private final RecheckService recheckService;

    public RecheckScheduler(RecheckService recheckService) {
        this.recheckService = recheckService;
    }

    @Scheduled(cron = "${app.detection.recheck-cron:0 15 * * * *}")
    public void scan() {
        try {
            recheckService.runOnce();
        } catch (RuntimeException e) {
            log.error("复测扫描异常", e);
        }
    }
}
