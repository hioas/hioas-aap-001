package com.hioas.aap.usage;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;

/**
 * T12 · 用量聚合降级路径（A16「用量任务故障不阻塞主流程」/ E-1801）。
 *
 * <p>单独一个类是因为要把 `app.usage.log-file` **置空**（未配置日志源）——属性覆盖会新建
 * 一个 Spring 上下文；混在 {@link UsageContractTest} 里会让整类的源都变成未配置。
 *
 * <p>为什么必须留这条用例：聚合失败必须是**可诊断的明确错误**（E-1801 + 503 + 说明），
 * 而不是把空结果当「本月零用量」返回——那会让工作台显示 0 而不是占位符，
 * 正是 §0「禁止用 0 冒充没有数据」反例。
 */
@TestPropertySource(properties = "app.usage.log-file=")
class UsageRefreshDegradedTest extends ApiTestBase {

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    private String techOpsToken() {
        Long accountId = 940002L;
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, 'techops-usage-degraded', 'x', '技术运营', 'TECH_OPS', 'ACTIVE')
                """, accountId);
        var issued = jwtService.issueAccessToken(accountId, "TECH_OPS", "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    @Test
    @DisplayName("ADM-U02 日志源未配置：E-1801 + 503 + 可诊断文案，且不写入任何用量行（降级不污染数据）")
    void refreshWithoutSourceFailsLoudly() {
        String admin = techOpsToken();

        HttpResult res = post("/admin/usage/refresh", """
                {"from":"2026-06-03T00:00:00Z","to":"2026-06-04T00:00:00Z"}
                """, admin);

        assertThat(res.status()).isEqualTo(503);
        assertThat(res.code()).isEqualTo("E-1801");
        assertThat(res.message()).contains("未配置");
        assertThat(jdbc.queryForObject("select count(*) from aap_usage_hourly", Long.class)).isZero();
    }
}
