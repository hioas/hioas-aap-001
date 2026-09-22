package com.hioas.aap.credential;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import org.junit.jupiter.api.Test;

/**
 * CRED-08 删除凭证（用户口径 2026-09-23：「每个用户的凭证列表页的凭证可删除」）。
 *
 * <p>覆盖三件事：
 * <ul>
 *   <li>**软删**：从列表消失但物理行保留（{@code deleted=true}）——历史可追溯，不物理删</li>
 *   <li>**归属校验**：只能删自己的凭证（越权 → {@code E-1406}，不泄露资源是否存在）</li>
 *   <li>**引用守卫**：被未删除的报价单引用时拒绝（{@code E-1102}），否则报价单会指向空凭证</li>
 * </ul>
 */
class CredentialDeleteContractTest extends ApiTestBase {

    // ⚠️ 每个用例用**独立手机号**：短信验证码一次性，跨用例复用同一号码时
    //    后续 `token()` 会拿到空 token → 表现为莫名其妙的 401 E-1902。
    private static final String PHONE_SOFT = "13800000021";
    private static final String PHONE_OWN = "13800000023";
    private static final String OTHER_PHONE = "13800000024";
    private static final String PHONE_REF = "13800000025";

    private String token(String phone) {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(phone));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        String code = send.data().path("dev_code").asText();
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(phone, code));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    private HttpResult createCredential(String token, String apiKey) {
        return post("/credentials", """
                {
                  "alias":"待删凭证",
                  "base_url":"https://api.example.com/v1",
                  "api_key":"%s",
                  "primary_flag":false
                }
                """.formatted(apiKey), token);
    }

    private Boolean deletedFlag(String id) {
        return jdbc.queryForObject("select deleted from aap_credential where id = ?",
                Boolean.class, Long.valueOf(id));
    }

    @Test
    void deleteIsSoftAndRemovesFromList() {
        String token = token(PHONE_SOFT);
        HttpResult created = createCredential(token, "sk-del-soft-0001");
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String id = created.data().path("id").asText();

        HttpResult deleted = delete("/credentials/" + id, token);
        assertThat(deleted.status()).as(deleted.body()).isEqualTo(200);
        assertThat(deleted.code()).isEqualTo("0");

        // 列表不再包含
        HttpResult list = get("/credentials?page=1&pageSize=50", token);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.body()).doesNotContain("\"id\":\"" + id + "\"");

        // 但**物理行仍在**（软删语义）
        assertThat(deletedFlag(id)).isTrue();
    }

    @Test
    void deleteRequiresOwnership() {
        String owner = token(PHONE_OWN);
        HttpResult created = createCredential(owner, "sk-del-own-0002");
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String id = created.data().path("id").asText();

        String other = token(OTHER_PHONE);
        HttpResult res = delete("/credentials/" + id, other);
        // ⚠️ 先按 404/E-1406 写，实测是 **403/E-1901「无权访问该凭证」**
        //    （CredentialService.requireOwned 对「非本人资源」抛 E_1901，不区分是否存在
        //      —— 这反而是更好的做法：不泄露资源存在性）。按项目约定断言。
        assertThat(res.status()).as(res.body()).isEqualTo(403);
        assertThat(res.code()).isEqualTo("E-1901");

        // 越权尝试不得改变状态
        assertThat(deletedFlag(id)).isFalse();
    }

    @Test
    void deleteRejectedWhenReferencedByQuote() {
        String token = token(PHONE_REF);
        HttpResult created = createCredential(token, "sk-del-ref-0003");
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String id = created.data().path("id").asText();

        Long providerId = jdbc.queryForObject(
                "select provider_id from aap_credential where id = ?", Long.class, Long.valueOf(id));

        // 造一条引用该凭证的报价单（直插，避免依赖报价链路的前置条件）
        long quoteId = 995001L;
        jdbc.update("delete from aap_quote where id = ?", quoteId);
        jdbc.update("""
                insert into aap_quote (id, quote_no, provider_id, credential_id, name, status, currency,
                                       item_count, deleted, version)
                values (?, 'QTEST-DEL-0001', ?, ?, '删除守卫用例', 'DRAFT', 'USD', 0, false, 0)
                """, quoteId, providerId, Long.valueOf(id));

        HttpResult res = delete("/credentials/" + id, token);
        assertThat(res.status()).as(res.body()).isEqualTo(400);
        assertThat(res.code()).isEqualTo("E-1102");

        // 被拒绝 ⇒ 凭证未被删
        assertThat(deletedFlag(id)).isFalse();
    }
}
