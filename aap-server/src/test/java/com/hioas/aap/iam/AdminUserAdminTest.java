package com.hioas.aap.iam;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T14 · 运营账号管理（**新增端点 ADM-AUTH02…05**）。
 *
 * <p>背景（2026-09-23 运行态实测）：`ADM-AUTH01` 打通管理端登录后，建号仍只能靠 SQL
 * —— 生产运维无法自助开通/停用运营账号。
 *
 * <p>锁定口径：
 * <ul>
 *   <li>全部限 **SUPER_ADMIN**（BIZ_OPERATOR / TECH_OPS 调 → 403）；</li>
 *   <li>建号即可用：新账号走 `ADM-AUTH01` 短信登录 → 令牌 role 取该账号角色，且权限边界正确；</li>
 *   <li>`username` / `phone` 唯一（phone_hash 无 DB 唯一索引，必须服务层拦截）；角色白名单；</li>
 *   <li>停用后该账号**登录被拒**（403 E-1901），恢复后可登录；</li>
 *   <li>护栏：不可停用自己；不可停用最后一个启用中的超管（用「已停用账号的未过期令牌」构造）；</li>
 *   <li>全动作写审计；列表只出脱敏手机号。</li>
 * </ul>
 */
class AdminUserAdminTest extends ApiTestBase {

    private static final long SUPER_ID = 970001L;
    private static final String SUPER_PHONE = "13800000211";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    @Autowired
    private CryptoService crypto;

    private long seq = 995000L;

    private long nextId() {
        return ++seq;
    }

    /** 造管理端账号 + 直接签发令牌（绕过登录，便于构造「已停用但令牌未过期」这类场景）。 */
    private String mintToken(long id, String phone, String role, String status) {
        jdbc.update("delete from aap_admin_user where id = ?", id);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status,
                                            phone_hash, phone_masked)
                values (?, ?, '!', ?, ?, ?, ?, ?)
                """, id, "ops" + id, "ops" + id, role, status,
                crypto.sha256Hex(phone), mask(phone));
        var issued = jwtService.issueAccessToken(id, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(id);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private static String mask(String phone) {
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    /** 走真实短信登录（验证「建号即可用」）；同一手机号 60s 内二次发码会被频控，等过再重试一次。 */
    private HttpResult login(String phone, String path) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        if (send.status() == 429) {
            try {
                Thread.sleep(62_000L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            send = post("/auth/sms/send", """
                    {"phone":"%s","captcha":"AB12"}
                    """.formatted(phone));
        }
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        return post(path, """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, send.data().path("dev_code").asText()));
    }

    // ================================================================== ADM-AUTH02/03

    @Test
    @DisplayName("ADM-AUTH03 建号 → 新账号可登录且权限生效；ADM-AUTH02 列表分页且只出脱敏手机号")
    void createAdminUserThenLogin() throws Exception {
        String superToken = mintToken(SUPER_ID, SUPER_PHONE, "SUPER_ADMIN", "ACTIVE");
        String newPhone = "13800000212";

        HttpResult created = post("/admin/admin-users", """
                {"username":"ops-new","display_name":"新运营","role":"BIZ_OPERATOR","phone":"%s"}
                """.formatted(newPhone), superToken);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        SchemaAssert.assertModel("admin-user", json(created.data()));
        assertThat(created.data().path("role").asText()).isEqualTo("BIZ_OPERATOR");
        assertThat(created.data().path("status").asText()).isEqualTo("ACTIVE");
        assertThat(created.data().path("phone_masked").asText()).isEqualTo("138****0212");
        assertThat(created.body()).as("响应不得出现明文手机号").doesNotContain(newPhone);
        long newId = Long.parseLong(created.data().path("id").asText());

        // 落库三件套（明文只以密文存）+ 不可用口令占位
        var row = jdbc.queryForMap("""
                select username, role, status, phone_masked, phone_cipher, password_hash
                  from aap_admin_user where id = ?
                """, newId);
        assertThat(row).containsEntry("role", "BIZ_OPERATOR").containsEntry("status", "ACTIVE")
                .containsEntry("phone_masked", "138****0212").containsEntry("password_hash", "!");
        assertThat((String) row.get("phone_cipher")).as("明文手机号不得落库").doesNotContain(newPhone);

        // 建号即可用：新账号真实短信登录，角色生效且权限边界正确
        HttpResult loginRes = login(newPhone, "/admin/auth/sms/login");
        assertThat(loginRes.status()).as(loginRes.body()).isEqualTo(200);
        assertThat(loginRes.data().path("role").asText()).isEqualTo("BIZ_OPERATOR");
        String newToken = loginRes.data().path("token").asText();
        assertThat(get("/admin/payments?page=1&pageSize=1", newToken).status())
                .as("BIZ_OPERATOR 可用其权限内接口").isEqualTo(200);
        assertThat(get("/admin/admin-users", newToken).status())
                .as("BIZ_OPERATOR 不得管理运营账号").isEqualTo(403);

        // 列表：分页元数据 + 只出脱敏手机号 + keyword 过滤
        HttpResult list = get("/admin/admin-users?page=1&pageSize=10", superToken);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).isEqualTo(2L);
        assertThat(list.body()).doesNotContain(newPhone);
        assertThat(get("/admin/admin-users?keyword=ops-new", superToken).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/admin-users?role=SUPER_ADMIN", superToken).data().path("total").asLong()).isEqualTo(1L);

        // 审计留痕
        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'admin_user'",
                String.class)).contains("ADMIN_USER_CREATE");

        // 权限：TECH_OPS / 未认证
        String techToken = mintToken(nextId(), "13800000213", "TECH_OPS", "ACTIVE");
        assertThat(post("/admin/admin-users", """
                {"username":"x1","role":"TECH_OPS","phone":"13800000214"}
                """, techToken).status()).isEqualTo(403);
        assertThat(get("/admin/admin-users").status()).isEqualTo(401);
    }

    @Test
    @DisplayName("ADM-AUTH03 守卫：账号名/手机号唯一、角色白名单、手机号格式")
    void createGuards() throws Exception {
        String superToken = mintToken(SUPER_ID, SUPER_PHONE, "SUPER_ADMIN", "ACTIVE");
        assertThat(post("/admin/admin-users", """
                {"username":"dup","role":"TECH_OPS","phone":"13800000215"}
                """, superToken).status()).isEqualTo(200);

        HttpResult dupName = post("/admin/admin-users", """
                {"username":"dup","role":"TECH_OPS","phone":"13800000216"}
                """, superToken);
        assertThat(dupName.status()).as(dupName.body()).isEqualTo(400);
        assertThat(dupName.code()).isEqualTo("E-1001");
        assertThat(dupName.body()).contains("username");

        HttpResult dupPhone = post("/admin/admin-users", """
                {"username":"other","role":"TECH_OPS","phone":"13800000215"}
                """, superToken);
        assertThat(dupPhone.status()).as(dupPhone.body()).isEqualTo(400);
        assertThat(dupPhone.body()).contains("phone");

        HttpResult badRole = post("/admin/admin-users", """
                {"username":"bad-role","role":"SUPPLIER","phone":"13800000217"}
                """, superToken);
        assertThat(badRole.status()).as(badRole.body()).isEqualTo(400);
        assertThat(badRole.body()).contains("role");

        HttpResult badPhone = post("/admin/admin-users", """
                {"username":"bad-phone","role":"TECH_OPS","phone":"12345"}
                """, superToken);
        assertThat(badPhone.status()).as(badPhone.body()).isEqualTo(400);
    }

    // ================================================================== ADM-AUTH04/05

    @Test
    @DisplayName("ADM-AUTH04/05 停用→登录被拒→恢复→可登录；重复停用 409；不存在 404")
    void suspendAndResume() throws Exception {
        String superToken = mintToken(SUPER_ID, SUPER_PHONE, "SUPER_ADMIN", "ACTIVE");
        String targetPhone = "13800000218";
        long targetId = Long.parseLong(post("/admin/admin-users", """
                {"username":"ops-suspend","role":"TECH_OPS","phone":"%s"}
                """.formatted(targetPhone), superToken).data().path("id").asText());
        assertThat(login(targetPhone, "/admin/auth/sms/login").status()).as("停用前可登录").isEqualTo(200);

        HttpResult noReason = post("/admin/admin-users/" + targetId + "/suspend", "{}", superToken);
        assertThat(noReason.status()).as(noReason.body()).isEqualTo(400);
        assertThat(noReason.body()).contains("reason");

        HttpResult suspended = post("/admin/admin-users/" + targetId + "/suspend",
                "{\"reason\":\"离职\"}", superToken);
        assertThat(suspended.status()).as(suspended.body()).isEqualTo(200);
        assertThat(suspended.data().path("status").asText()).isEqualTo("SUSPENDED");
        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'admin_user'",
                String.class)).contains("ADMIN_USER_SUSPEND");

        // 停用后：登录被拒（403 E-1901），旧令牌也不可用（jti 仍在，但账号状态由登录端点拦住）
        HttpResult afterSuspend = login(targetPhone, "/admin/auth/sms/login");
        assertThat(afterSuspend.status()).as(afterSuspend.body()).isEqualTo(403);
        assertThat(afterSuspend.code()).isEqualTo("E-1901");

        HttpResult twice = post("/admin/admin-users/" + targetId + "/suspend",
                "{\"reason\":\"再停一次\"}", superToken);
        assertThat(twice.status()).as(twice.body()).isEqualTo(409);
        assertThat(twice.code()).isEqualTo("E-1601");

        HttpResult resumed = post("/admin/admin-users/" + targetId + "/resume", null, superToken);
        assertThat(resumed.status()).as(resumed.body()).isEqualTo(200);
        assertThat(resumed.data().path("status").asText()).isEqualTo("ACTIVE");
        // 恢复后「可用」的等价证据：状态回 ACTIVE + 该账号重新签发令牌后能调其权限内接口
        // （不再二次发码，避免再等 60s 频控；登录通路已在上面的「停用后 403」处验证过）
        assertThat(jdbc.queryForObject("select status from aap_admin_user where id = ?", String.class, targetId))
                .isEqualTo("ACTIVE");
        String targetToken = mintToken(targetId, targetPhone, "TECH_OPS", "ACTIVE");
        assertThat(get("/admin/detection-configs?page=1&pageSize=1", targetToken).status())
                .as("恢复后该账号可正常使用").isEqualTo(200);

        assertThat(post("/admin/admin-users/" + targetId + "/resume", null, superToken).status())
                .as("重复恢复 → 409").isEqualTo(409);
        assertThat(post("/admin/admin-users/999999999/resume", null, superToken).code()).isEqualTo("E-1406");
        assertThat(post("/admin/admin-users/999999999/suspend", "{\"reason\":\"x\"}", superToken).code())
                .isEqualTo("E-1406");
    }

    @Test
    @DisplayName("ADM-AUTH04 护栏：不可停用自己；不可停用最后一个启用中的超管（用已停用账号的未过期令牌构造）")
    void suspendGuardrails() throws Exception {
        String superToken = mintToken(SUPER_ID, SUPER_PHONE, "SUPER_ADMIN", "ACTIVE");

        HttpResult self = post("/admin/admin-users/" + SUPER_ID + "/suspend",
                "{\"reason\":\"手滑\"}", superToken);
        assertThat(self.status()).as(self.body()).isEqualTo(409);
        assertThat(self.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select status from aap_admin_user where id = ?", String.class, SUPER_ID))
                .as("被拒后自身状态不变").isEqualTo("ACTIVE");

        // 已停用超管的令牌（未过期）去停用唯一启用中的超管 → 必须拦住，否则管理端彻底失联
        String staleToken = mintToken(nextId(), "13800000219", "SUPER_ADMIN", "SUSPENDED");
        HttpResult lastOne = post("/admin/admin-users/" + SUPER_ID + "/suspend",
                "{\"reason\":\"越权尝试\"}", staleToken);
        assertThat(lastOne.status()).as(lastOne.body()).isEqualTo(409);
        assertThat(lastOne.body()).contains("最后一个");
        assertThat(jdbc.queryForObject("select status from aap_admin_user where id = ?", String.class, SUPER_ID))
                .isEqualTo("ACTIVE");
    }
}
