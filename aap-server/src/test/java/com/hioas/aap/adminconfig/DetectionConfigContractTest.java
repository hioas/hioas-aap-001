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
 * T14 · 检测配置版本（ADM-CFG01…05）验收。
 *
 * <p>契约真源：`docs/backend/02-API接口模型清单.md` §2.4（`ADM-CFG01` 列表 / `ADM-CFG02` 新建 /
 * `ADM-CFG03` 详情 / `ADM-CFG04` 修改（DRAFT 可改）/ `ADM-CFG05` 发布（旧版置 SUPERSEDED））
 * + `json-schema/models/detection-config.schema.json` + `requests/detection-config-save.schema.json`
 * + `01-ER数据模型.md` §`aap_detection_config` / §`aap_detection_config_probe`
 * （`probe_code`(D1–D8)、`weight` **归一化前**、`timeout_seconds` D1–D3/D6–D8=180、D4/D5=600）。
 *
 * <p>硬口径：
 * <ul>
 *   <li>状态机 `DRAFT → PUBLISHED`，被替代的活版 → `SUPERSEDED`；**非 DRAFT 不可改、不可重复发布**（409 E-1601）</li>
 *   <li>`version_no` 全表唯一（`uq_detection_config_version`）→ 每次新建即新版本号（`V{n}` 单调递增）</li>
 *   <li>检测项只能取 D1–D8（与 `ProbeScoring.PROBE_NAMES` 同源），缺省名取同表、缺省超时按 ER 规则，
 *       `weight` 存**归一化前**原始权重（归一化在任务打分时按计分项做）</li>
 *   <li>修改是 **coalesce 语义**：请求省略的字段保持原值（省略≠清空，`pass_score` 列 NOT NULL）</li>
 *   <li>发布要留痕：`published_at/published_by` 落库 + `CONFIG_PUBLISH` 审计（可经 ADM-A01 检索）</li>
 * </ul>
 */
class DetectionConfigContractTest extends ApiTestBase {

    private static final String PHONE = "13800000120";

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
                values (?, ?, 'x', '技术运营', ?, 'ACTIVE')
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
        return adminToken(970001L, "TECH_OPS");
    }

    private HttpResult create(String token, String body) {
        return post("/admin/detection-configs", body, token);
    }

    /** 一份含三类检测项的完整配置：默认名/默认超时（缺少时由服务端按 ER 规则补全）。 */
    private static String standardBody(String name) {
        return """
                {"name":"%s","pass_score":70,"veto_rule":{"probe":"D7","lt":40},
                 "probes":[{"probe_code":"D1","enabled":true,"weight":0.10},
                           {"probe_code":"D7","probe_name":"模型指纹","weight":0.35},
                           {"probe_code":"D4","enabled":true,"weight":0.10,"timeout_seconds":600}]}
                """.formatted(name);
    }

    private HttpResult createStandard(String token, String name) {
        HttpResult created = create(token, standardBody(name));
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        return created;
    }

    private static JsonNode probe(JsonNode config, String code) {
        for (JsonNode row : config.path("probes")) {
            if (code.equals(row.path("probe_code").asText())) {
                return row;
            }
        }
        throw new AssertionError("响应中缺少检测项 " + code + "：" + config);
    }

    // ------------------------------------------------------------------ 契约

    @Test
    @DisplayName("ADM-CFG01/02/03 新建-详情-列表：DRAFT 落库、检测项补全、分页与状态过滤、不存在 404 E-1406")
    void createDetailList() {
        String admin = techOps();
        HttpResult created = createStandard(admin, "标准检测配置");
        SchemaAssert.assertEnvelope(created.body());
        JsonNode data = created.data();
        SchemaAssert.assertModel("detection-config", json(data));
        assertThat(data.path("id").asText()).isNotBlank();
        assertThat(data.path("config_id").asText()).as("config_id 是 id 的兼容别名").isEqualTo(data.path("id").asText());
        assertThat(data.path("version_no").asText()).startsWith("V");
        assertThat(data.path("name").asText()).isEqualTo("标准检测配置");
        assertThat(data.path("pass_score").asInt()).isEqualTo(70);
        assertThat(data.path("veto_rule").path("probe").asText()).isEqualTo("D7");
        assertThat(data.path("status").asText()).isEqualTo("DRAFT");
        assertThat(data.path("published_at").isNull()).isTrue();
        assertThat(data.path("created_at").asText()).isNotBlank();

        // 检测项：缺省名取 ProbeScoring.PROBE_NAMES；缺省超时按 ER 规则（D1–D3/D6–D8=180，D4/D5=600）
        assertThat(data.path("probes").size()).isEqualTo(3);
        JsonNode d1 = probe(data, "D1");
        assertThat(d1.path("probe_name").asText()).isEqualTo("TTFT");
        assertThat(d1.path("enabled").asBoolean()).isTrue();
        assertThat(d1.path("weight").asDouble()).isEqualTo(0.10);
        assertThat(d1.path("timeout_seconds").asInt()).isEqualTo(180);
        JsonNode d7 = probe(data, "D7");
        assertThat(d7.path("probe_name").asText()).as("显式提供的名称优先").isEqualTo("模型指纹");
        assertThat(d7.path("timeout_seconds").asInt()).isEqualTo(180);
        JsonNode d4 = probe(data, "D4");
        assertThat(d4.path("probe_name").asText()).isEqualTo("RPM");
        assertThat(d4.path("timeout_seconds").asInt()).isEqualTo(600);
        String id = data.path("id").asText();
        String versionNo = data.path("version_no").asText();

        // 库值与响应同源（weight 存归一化前的原始权重）
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_config_probe where config_id = " + id,
                Long.class)).isEqualTo(3L);
        assertThat(jdbc.queryForObject(
                "select weight from aap_detection_config_probe where config_id = " + id + " and probe_code = 'D7'",
                java.math.BigDecimal.class)).isEqualByComparingTo("0.35");

        HttpResult detail = get("/admin/detection-configs/" + id, admin);
        assertThat(detail.status()).as(detail.body()).isEqualTo(200);
        SchemaAssert.assertModel("detection-config", json(detail.data()));
        assertThat(detail.data().path("version_no").asText()).isEqualTo(versionNo);
        assertThat(detail.data().path("probes").size()).isEqualTo(3);

        HttpResult list = get("/admin/detection-configs", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        SchemaAssert.assertPageMeta(json(list.data()));
        assertThat(list.data().path("total").asLong()).isEqualTo(1L);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(20);
        assertThat(list.data().path("items").get(0).path("probes").size())
                .as("列表也要带检测项明细（否则管理端列表页无法展示启停/权重）").isEqualTo(3);
        assertThat(get("/admin/detection-configs?status=PUBLISHED", admin).data().path("total").asLong()).isZero();
        assertThat(get("/admin/detection-configs?status=draft", admin).data().path("total").asLong())
                .as("状态过滤大小写不敏感").isEqualTo(1L);

        // 不存在 → 404 E-1406（资源型错误码，清单口径）
        HttpResult missing = get("/admin/detection-configs/999999", admin);
        assertThat(missing.status()).as(missing.body()).isEqualTo(404);
        assertThat(missing.code()).isEqualTo("E-1406");
        assertThat(put("/admin/detection-configs/999999", standardBody("x"), admin).status())
                .as("不存在的配置不可改").isEqualTo(404);
        assertThat(post("/admin/detection-configs/999999/publish", null, admin).status())
                .as("不存在的配置不可发布").isEqualTo(404);
    }

    @Test
    @DisplayName("ADM-CFG01 分页与版本号唯一：多次新建各自成版本（version_no 单调且不重复）")
    void versionNumberingAndPaging() {
        String admin = techOps();
        for (int i = 1; i <= 3; i++) {
            createStandard(admin, "配置" + i);
        }
        HttpResult list = get("/admin/detection-configs?page=1&pageSize=2", admin);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).isEqualTo(3L);
        assertThat(list.data().path("pageSize").asInt()).isEqualTo(2);
        assertThat(list.data().path("items").size()).isEqualTo(2);

        List<String> versions = jdbc.queryForList("select version_no from aap_detection_config order by id",
                String.class);
        assertThat(versions).as("version_no 全表唯一（uq_detection_config_version）").doesNotHaveDuplicates();
        assertThat(versions.stream().map(v -> v.substring(1)).map(Integer::parseInt).toList())
                .as("version_no 单调递增").isSorted();
    }

    @Test
    @DisplayName("ADM-CFG02 入参校验：缺/超长名称、分值越界、非法或重复检测项、负权重 → 400 E-1001")
    void createValidation() {
        String admin = techOps();
        List<String> badBodies = List.of(
                "{\"pass_score\":70,\"probes\":[{\"probe_code\":\"D1\"}]}",
                "{\"name\":\"\",\"pass_score\":70}",
                "{\"name\":\"%s\"}".formatted("名".repeat(65)),
                "{\"name\":\"配置\",\"pass_score\":101}",
                "{\"name\":\"配置\",\"pass_score\":-1}",
                "{\"name\":\"配置\",\"probes\":[{\"probe_code\":\"D9\"}]}",
                "{\"name\":\"配置\",\"probes\":[{\"probe_code\":\"d1\"}]}",
                "{\"name\":\"配置\",\"probes\":[{\"probe_code\":\"D1\"},{\"probe_code\":\"D1\"}]}",
                "{\"name\":\"配置\",\"probes\":[{\"probe_code\":\"D1\",\"weight\":-0.5}]}",
                "{\"name\":\"配置\",\"status\":\"PUBLISHED\"}");
        for (String bad : badBodies) {
            HttpResult res = create(admin, bad);
            assertThat(res.status()).as("%s → %s", bad, res.body()).isEqualTo(400);
            assertThat(res.code()).as(bad).isEqualTo("E-1001");
        }
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_config", Long.class))
                .as("校验失败不得落库").isZero();
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_config_probe", Long.class))
                .as("校验失败不得落检测项").isZero();
    }

    @Test
    @DisplayName("ADM-CFG04 更新：DRAFT 可改且省略字段保持原值（coalesce）；已发布 → 409 E-1601")
    void updateOnlyDraft() {
        String admin = techOps();
        HttpResult created = createStandard(admin, "初版配置");
        String id = created.data().path("id").asText();

        // 只改 pass_score：name/probes 必须保持原值（省略≠清空）
        HttpResult updated = put("/admin/detection-configs/" + id, """
                {"pass_score":85}
                """, admin);
        assertThat(updated.status()).as(updated.body()).isEqualTo(200);
        SchemaAssert.assertModel("detection-config", json(updated.data()));
        assertThat(updated.data().path("pass_score").asInt()).isEqualTo(85);
        assertThat(updated.data().path("name").asText()).as("省略 name 不得清空").isEqualTo("初版配置");
        assertThat(updated.data().path("status").asText()).isEqualTo("DRAFT");
        assertThat(updated.data().path("probes").size()).as("省略 probes 不得清空检测项").isEqualTo(3);

        // 响应与库值同钉
        assertThat(jdbc.queryForObject("select pass_score from aap_detection_config where id = " + id, Integer.class))
                .isEqualTo(85);
        assertThat(jdbc.queryForObject("select name from aap_detection_config where id = " + id, String.class))
                .isEqualTo("初版配置");
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_config_probe where config_id = " + id,
                Long.class)).isEqualTo(3L);

        // 显式替换检测项：整体替换且校验同一套规则
        HttpResult replaced = put("/admin/detection-configs/" + id, """
                {"probes":[{"probe_code":"D2","weight":0.15},{"probe_code":"D8","enabled":false,"weight":0}]}
                """, admin);
        assertThat(replaced.status()).as(replaced.body()).isEqualTo(200);
        assertThat(replaced.data().path("probes").size()).isEqualTo(2);
        assertThat(probe(replaced.data(), "D8").path("enabled").asBoolean()).isFalse();
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_config_probe where config_id = " + id
                + " and deleted = false", Long.class)).isEqualTo(2L);

        HttpResult badProbe = put("/admin/detection-configs/" + id, """
                {"probes":[{"probe_code":"D9"}]}
                """, admin);
        assertThat(badProbe.status()).as(badProbe.body()).isEqualTo(400);
        assertThat(badProbe.code()).isEqualTo("E-1001");
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_config_probe where config_id = " + id
                + " and deleted = false", Long.class)).as("非法更新不得破坏既有检测项").isEqualTo(2L);

        // 发布后不可再改
        assertThat(post("/admin/detection-configs/" + id + "/publish", null, admin).status()).isEqualTo(200);
        HttpResult rejected = put("/admin/detection-configs/" + id, """
                {"pass_score":10}
                """, admin);
        assertThat(rejected.status()).as(rejected.body()).isEqualTo(409);
        assertThat(rejected.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select pass_score from aap_detection_config where id = " + id, Integer.class))
                .as("非法更新不得改动已发布配置").isEqualTo(85);
    }

    @Test
    @DisplayName("ADM-CFG05 发布：DRAFT→PUBLISHED、published_at/by 落库、CONFIG_PUBLISH 审计可检索；重复发布 409")
    void publishWithAuditTrail() {
        String admin = techOps();
        String id = createStandard(admin, "待发布配置").data().path("id").asText();

        HttpResult published = post("/admin/detection-configs/" + id + "/publish", null, admin);
        assertThat(published.status()).as(published.body()).isEqualTo(200);
        SchemaAssert.assertModel("detection-config", json(published.data()));
        assertThat(published.data().path("status").asText()).isEqualTo("PUBLISHED");
        assertThat(published.data().path("published_at").asText()).isNotBlank();
        assertThat(published.data().path("probes").size()).as("发布响应仍带检测项明细").isEqualTo(3);

        // 响应与库值同钉（发布留痕：时间 + 操作人）
        assertThat(jdbc.queryForObject("select status from aap_detection_config where id = " + id, String.class))
                .isEqualTo("PUBLISHED");
        assertThat(jdbc.queryForObject("select published_at from aap_detection_config where id = " + id,
                OffsetDateTime.class)).isNotNull();
        assertThat(jdbc.queryForObject("select published_by from aap_detection_config where id = " + id, Long.class))
                .isEqualTo(970001L);

        // 重复发布 → 状态非法
        HttpResult again = post("/admin/detection-configs/" + id + "/publish", null, admin);
        assertThat(again.status()).as(again.body()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");

        // 审计留痕：CONFIG_PUBLISH 可经 ADM-A01 检索（配置发布不是“悄悄生效”）
        HttpResult logs = get("/admin/audit-logs?action=CONFIG_PUBLISH", admin);
        assertThat(logs.status()).as(logs.body()).isEqualTo(200);
        assertThat(logs.data().path("total").asLong()).isEqualTo(1L);
        JsonNode row = logs.data().path("items").get(0);
        assertThat(row.path("target_type").asText()).isEqualTo("detection_config");
        assertThat(row.path("target_id").asText()).isEqualTo(id);
        assertThat(row.path("summary").asText()).contains("检测配置");
    }

    @Test
    @DisplayName("ADM-CFG05 活版唯一：新配置发布后旧的 PUBLISHED 置 SUPERSEDED（同表只留一份活版）")
    void publishSupersedesPrevious() {
        String admin = techOps();
        // 夹具：已有一份生效中的配置（模拟历史版本）
        jdbc.update("""
                insert into aap_detection_config (id, version_no, name, pass_score, status, published_at,
                    published_by, created_at, updated_at, deleted, version)
                values (900101, 'V900', '旧版配置', 70, 'PUBLISHED', '2026-01-01T00:00:00Z', 970001,
                        '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', false, 0)
                """);
        String id = createStandard(admin, "新版配置").data().path("id").asText();

        HttpResult published = post("/admin/detection-configs/" + id + "/publish", null, admin);
        assertThat(published.status()).as(published.body()).isEqualTo(200);
        assertThat(published.data().path("status").asText()).isEqualTo("PUBLISHED");

        assertThat(jdbc.queryForObject("select status from aap_detection_config where id = 900101", String.class))
                .as("旧活版必须被替代，否则“当前配置是哪一份”不确定").isEqualTo("SUPERSEDED");
        assertThat(jdbc.queryForObject(
                "select count(*) from aap_detection_config where status = 'PUBLISHED'", Long.class)).isEqualTo(1L);
    }

    @Test
    @DisplayName("ADM-CFG01…05 权限：仅 TECH_OPS/SUPER_ADMIN；运营商务与供应商 403、未认证 401")
    void permissions() {
        String supplier = supplierToken();
        String techOps = techOps();
        String superAdmin = adminToken(970002L, "SUPER_ADMIN");
        String bizOperator = adminToken(970003L, "BIZ_OPERATOR");

        assertThat(get("/admin/detection-configs", techOps).status()).isEqualTo(200);
        assertThat(get("/admin/detection-configs", superAdmin).status()).isEqualTo(200);
        HttpResult bizDenied = get("/admin/detection-configs", bizOperator);
        assertThat(bizDenied.status()).as("运营商务不参与检测配置").isEqualTo(403);
        assertThat(bizDenied.code()).isEqualTo("E-1901");

        HttpResult supplierDenied = create(supplier, standardBody("越权配置"));
        assertThat(supplierDenied.status()).as(supplierDenied.body()).isEqualTo(403);
        assertThat(supplierDenied.code()).isEqualTo("E-1901");
        assertThat(get("/admin/detection-configs").status()).isEqualTo(401);
        assertThat(post("/admin/detection-configs/1/publish", null, null).status()).isEqualTo(401);
    }
}
