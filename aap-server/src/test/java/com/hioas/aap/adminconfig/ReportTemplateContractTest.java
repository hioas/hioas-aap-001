package com.hioas.aap.adminconfig;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

/**
 * T14 · 报告模板配置（ADM-CFG06…10）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4 + `json-schema/models/report-template.schema.json`
 * + `13-管理端PRD.md` §…（"报告模板：Logo/标题/章节顺序/…/免责声明文案；**保存时校验不得出现
 * 「保证为真模型」措辞**"）+ `09-检测验证引擎PRD` §（模板可配）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>状态机 `DRAFT → PUBLISHED`，被替代的活版 → `SUPERSEDED`；**非 DRAFT 不可改、不可重复发布**（409 E-1601）</li>
 *   <li>措辞红线是**字符串级**判定（R-26）：免责声明不得出现「保证为真」等保证性断言（400 E-1001）</li>
 *   <li>章节顺序只能取报告章节枚举 A–F（与 ReportService 的章节划分同源）</li>
 *   <li>发布要留痕：`published_at/published_by` 落库 + `CONFIG_PUBLISH` 审计（可经 ADM-A01 检索）</li>
 * </ul>
 */
class ReportTemplateContractTest extends ApiTestBase {

    private static final String PHONE = "13800000090";

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    // ------------------------------------------------------------------ 工具

    private String supplierToken() {
        HttpResult send = post("/auth/sms/send", """
                {"phone":"%s","captcha":"AB12"}
                """.formatted(PHONE));
        assertThat(send.status()).as(send.body()).isEqualTo(200);
        HttpResult login = post("/auth/sms/login", """
                {"phone":"%s","smsCode":"%s"}
                """.formatted(PHONE, send.data().path("dev_code").asText()));
        assertThat(login.status()).as(login.body()).isEqualTo(200);
        return login.data().path("token").asText();
    }

    private String adminToken(long accountId, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', '配置管理员', ?, 'ACTIVE')
                """, accountId, role.toLowerCase() + "-" + accountId, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String techOps() {
        return adminToken(960001L, "TECH_OPS");
    }

    private HttpResult create(String token, String body) {
        return post("/admin/report-templates", body, token);
    }

    private static String body(String title, String sections, String disclaimer) {
        return """
                {"title":"%s","section_order":%s,"disclaimer":"%s"}
                """.formatted(title, sections, disclaimer);
    }

    private static final String SAFE_DISCLAIMER =
            "本报告输出证据与置信度，不构成对模型来源或授权状态的担保。";

    // ------------------------------------------------------------------ 契约

    @Test
    @DisplayName("ADM-CFG06/07/08 创建-详情-列表：DRAFT 落库、模板编号/版本号齐备、分页与状态过滤")
    void createDetailList() {
        String admin = techOps();
        HttpResult created = create(admin, body("标准检测报告", "[\"A\",\"B\",\"C\",\"D\",\"E\",\"F\"]", SAFE_DISCLAIMER));
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        SchemaAssert.assertEnvelope(created.body());
        JsonNode data = created.data();
        SchemaAssert.assertModel("report-template", json(data));
        assertThat(data.path("id").asText()).isNotBlank();
        assertThat(data.path("template_id").asText()).isEqualTo(data.path("id").asText());
        assertThat(data.path("template_no").asText()).startsWith("TPL");
        assertThat(data.path("version_no").asText()).isNotBlank();
        assertThat(data.path("title").asText()).isEqualTo("标准检测报告");
        assertThat(data.path("section_order").size()).isEqualTo(6);
        assertThat(data.path("section_order").get(0).asText()).isEqualTo("A");
        assertThat(data.path("disclaimer").asText()).isEqualTo(SAFE_DISCLAIMER);
        assertThat(data.path("status").asText()).isEqualTo("DRAFT");
        assertThat(data.path("published_at").isNull()).isTrue();
        assertThat(data.path("created_at").asText()).isNotBlank();
        String id = data.path("id").asText();

        HttpResult detail = get("/admin/report-templates/" + id, admin);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("report-template", json(detail.data()));
        assertThat(detail.data().path("title").asText()).isEqualTo("标准检测报告");
        assertThat(detail.data().path("template_no").asText()).isEqualTo(data.path("template_no").asText());

        HttpResult list = get("/admin/report-templates", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).isEqualTo(1L);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(20);

        assertThat(get("/admin/report-templates?status=PUBLISHED", admin).data().path("total").asLong()).isZero();
        assertThat(get("/admin/report-templates?status=DRAFT", admin).data().path("total").asLong()).isEqualTo(1L);
        assertThat(get("/admin/report-templates?status=draft", admin).data().path("total").asLong())
                .as("状态过滤大小写不敏感").isEqualTo(1L);
        // 不存在 → 404 E-1406（资源型错误码，清单口径）
        HttpResult missing = get("/admin/report-templates/999999", admin);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
    }

    @Test
    @DisplayName("ADM-CFG07 入参校验：缺标题/标题超长/章节非法/章节重复/免责声明含 R-26 禁用词 → 400 E-1001")
    void createValidation() {
        String admin = techOps();
        List<String> badBodies = List.of(
                body("", "[\"A\"]", SAFE_DISCLAIMER),
                body("A".repeat(129), "[\"A\"]", SAFE_DISCLAIMER),
                body("标题", "[]", SAFE_DISCLAIMER),
                body("标题", "[\"A\",\"Z\"]", SAFE_DISCLAIMER),
                body("标题", "[\"A\",\"A\"]", SAFE_DISCLAIMER),
                body("标题", "[\"A\"]", "本报告保证为真模型，可直接对外宣称。"),
                body("标题", "[\"A\"]", "检测结论保证正品，请放心引用。"));
        for (String bad : badBodies) {
            HttpResult res = create(admin, bad);
            assertThat(res.status()).as("%s → %s", bad, res.body()).isEqualTo(400);
            assertThat(res.code()).as(bad).isEqualTo("E-1001");
        }
        assertThat(jdbc.queryForObject("select count(*) from aap_report_template", Long.class))
                .as("校验失败不得落库").isZero();
    }

    @Test
    @DisplayName("ADM-CFG09 更新：DRAFT 可改且响应与库值同源；已发布/已替代 → 409 E-1601")
    void updateOnlyDraft() {
        String admin = techOps();
        String id = create(admin, body("初版标题", "[\"A\",\"B\"]", SAFE_DISCLAIMER)).data().path("id").asText();

        HttpResult updated = put("/admin/report-templates/" + id, """
                {"title":"修订标题","section_order":["C","D"],"disclaimer":"修订后的免责声明：输出证据与置信度。"}
                """, admin);
        assertThat(updated.status()).as(updated.body()).isEqualTo(200);
        SchemaAssert.assertModel("report-template", json(updated.data()));
        assertThat(updated.data().path("title").asText()).isEqualTo("修订标题");
        assertThat(updated.data().path("section_order").get(0).asText()).isEqualTo("C");
        assertThat(updated.data().path("status").asText()).isEqualTo("DRAFT");
        // 响应与库值同钉
        assertThat(jdbc.queryForObject("select title from aap_report_template where id = " + id, String.class))
                .isEqualTo("修订标题");
        assertThat(jdbc.queryForObject("select section_order->>0 from aap_report_template where id = " + id, String.class))
                .isEqualTo("C");

        // 发布后不可再改
        assertThat(post("/admin/report-templates/" + id + "/publish", null, admin).status()).isEqualTo(200);
        HttpResult rejected = put("/admin/report-templates/" + id, """
                {"title":"再改一次"}
                """, admin);
        assertThat(rejected.status()).as(rejected.body()).isEqualTo(409);
        assertThat(rejected.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select title from aap_report_template where id = " + id, String.class))
                .as("非法更新不得改动已发布模板").isEqualTo("修订标题");

        // 更新接口的入参校验与创建一致（措辞红线）
        String draft2 = create(admin, body("第二份", "[\"A\"]", SAFE_DISCLAIMER)).data().path("id").asText();
        HttpResult badWording = put("/admin/report-templates/" + draft2, """
                {"disclaimer":"本模型保证为真。"}
                """, admin);
        assertThat(badWording.status()).as(badWording.body()).isEqualTo(400);
        assertThat(badWording.code()).isEqualTo("E-1001");
    }

    @Test
    @DisplayName("ADM-CFG10 发布：DRAFT→PUBLISHED、published_at/by 落库、CONFIG_PUBLISH 审计可检索；重复发布 409")
    void publishWithAuditTrail() {
        String admin = techOps();
        String id = create(admin, body("待发布模板", "[\"A\",\"D\"]", SAFE_DISCLAIMER)).data().path("id").asText();

        HttpResult published = post("/admin/report-templates/" + id + "/publish", null, admin);
        assertThat(published.status()).as(published.body()).isEqualTo(200);
        SchemaAssert.assertModel("report-template", json(published.data()));
        assertThat(published.data().path("status").asText()).isEqualTo("PUBLISHED");
        assertThat(published.data().path("published_at").asText()).isNotBlank();

        // 响应与库值同钉（发布留痕：时间 + 操作人）
        assertThat(jdbc.queryForObject("select status from aap_report_template where id = " + id, String.class))
                .isEqualTo("PUBLISHED");
        assertThat(jdbc.queryForObject("select published_at from aap_report_template where id = " + id,
                OffsetDateTime.class)).isNotNull();
        assertThat(jdbc.queryForObject("select published_by from aap_report_template where id = " + id, Long.class))
                .isEqualTo(960001L);

        // 重复发布 → 状态非法
        HttpResult again = post("/admin/report-templates/" + id + "/publish", null, admin);
        assertThat(again.status()).as(again.body()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");

        // 审计留痕：CONFIG_PUBLISH 可经 ADM-A01 检索（发布不是“悄悄生效”）
        HttpResult logs = get("/admin/audit-logs?action=CONFIG_PUBLISH", admin);
        assertThat(logs.status()).as(logs.body()).isEqualTo(200);
        assertThat(logs.data().path("total").asLong()).isEqualTo(1L);
        JsonNode row = logs.data().path("items").get(0);
        assertThat(row.path("target_type").asText()).isEqualTo("report_template");
        assertThat(row.path("target_id").asText()).isEqualTo(id);
        assertThat(row.path("summary").asText()).contains("报告模板");
    }

    @Test
    @DisplayName("ADM-CFG10 活版唯一：新模板发布后旧的 PUBLISHED 置 SUPERSEDED（同表只留一份活版）")
    void publishSupersedesPrevious() {
        String admin = techOps();
        // 夹具：已有一份生效中的模板（模拟历史版本）
        jdbc.update("""
                insert into aap_report_template (id, template_no, version_no, title, section_order, status,
                    published_at, published_by, created_at, updated_at, deleted, version)
                values (900001, 'TPL202601010001', 'V1', '旧版模板', '["A"]'::jsonb, 'PUBLISHED',
                        '2026-01-01T00:00:00Z', 960001, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', false, 0)
                """);
        String id = create(admin, body("新版模板", "[\"A\",\"B\"]", SAFE_DISCLAIMER)).data().path("id").asText();

        HttpResult published = post("/admin/report-templates/" + id + "/publish", null, admin);
        assertThat(published.status()).as(published.body()).isEqualTo(200);
        assertThat(published.data().path("status").asText()).isEqualTo("PUBLISHED");

        assertThat(jdbc.queryForObject("select status from aap_report_template where id = 900001", String.class))
                .as("旧活版必须被替代，否则报告用哪一份不确定").isEqualTo("SUPERSEDED");
        assertThat(jdbc.queryForObject(
                "select count(*) from aap_report_template where status = 'PUBLISHED'", Long.class)).isEqualTo(1L);
    }

    @Test
    @DisplayName("ADM-CFG06…10 权限：仅 TECH_OPS/SUPER_ADMIN；供应商与运营商务 403、未认证 401")
    void permissions() {
        String supplier = supplierToken();
        String techOps = techOps();
        String superAdmin = adminToken(960002L, "SUPER_ADMIN");
        String bizOperator = adminToken(960003L, "BIZ_OPERATOR");

        assertThat(get("/admin/report-templates", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/report-templates", superAdmin).status()).isEqualTo(200);
        HttpResult bizDenied = get("/admin/report-templates", bizOperator);
        assertThat(bizDenied.status()).as("运营商务不参与检测配置/报告模板").isEqualTo(403);
        assertThat(bizDenied.code()).isEqualTo("E-1901");

        HttpResult supplierDenied = create(supplier, body("越权模板", "[\"A\"]", SAFE_DISCLAIMER));
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        assertThat(get("/admin/report-templates").status()).isEqualTo(401);
        assertThat(post("/admin/report-templates/1/publish", null, null).status()).isEqualTo(401);
    }
}
