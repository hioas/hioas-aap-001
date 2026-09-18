package com.hioas.aap.review;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.detection.DetectionService;
import com.hioas.aap.detection.ProbeScoring;
import com.hioas.aap.iam.AuthTokenEntity;
import com.hioas.aap.iam.AuthTokenMapper;
import com.hioas.aap.iam.JwtService;
import com.hioas.aap.support.ApiTestBase;
import com.hioas.aap.support.SchemaAssert;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * T10 · 审核（ADM-R01…R05：待审报价池 / 领取 / 通过 / 驳回 / 审核记录）。
 *
 * <p>契约真源：`docs/backend/endpoints.json` + `docs/backend/json-schema/{models/review-task,models/review-record,requests/review-approve,requests/review-reject}.schema.json`
 * + `13-管理端PRD.md` §5（M8 审核）+ `10-报价与合同结算PRD.md` §3.6/§4.1（状态-动作矩阵、A9 通过自动生成合同）。
 *
 * <p>硬口径（每条都对应断言）：
 * <ul>
 *   <li>**待审池由提交驱动**：报价单提交（QT-09）即入池；驳回后重提**复用同一任务**（uq_review_quote 唯一索引，不允许插第二条）</li>
 *   <li>**乐观锁 E1**：领取/通过/驳回都是条件更新，终态或已被他人领取 → E-1601（409），不得静默覆盖他人</li>
 *   <li>**A9**：通过 = 同事务生成合同（CREATED）并回写 `quote.contract_id`，不产生“通过但无合同”的中间态</li>
 *   <li>**必填原因**：驳回缺 `reason_code`/非法枚举 → E-1001；`reason_text` 落库</li>
 *   <li>**权限差异**（PRD §5）：技术运营只看（R01/R05），领取/通过/驳回仅运营商务+超管</li>
 * </ul>
 */
class ReviewContractTest extends ApiTestBase {

    private static final String PHONE = "13800000080";
    private static final String OTHER_PHONE = "13800000081";

    private static final long BIZ_OPS_ID = 950001L;
    private static final long BIZ_OPS2_ID = 950002L;
    private static final long TECH_OPS_ID = 950003L;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private AuthTokenMapper authTokenMapper;

    @Autowired
    private DetectionService detectionService;

    private HttpServer upstream;

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    private String startUpstream() throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/v1/models", exchange -> {
            byte[] body = "{\"data\":[{\"id\":\"gpt-4o\"}]}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        upstream.start();
        return "http://127.0.0.1:" + upstream.getAddress().getPort() + "/v1";
    }

    // ------------------------------------------------------------------ 供应商侧前置

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

    private String credential(String token) throws Exception {
        HttpResult created = post("/credentials", """
                {
                  "alias":"审核凭证","base_url":"%s","api_key":"***review-%d","primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o"}]
                }
                """.formatted(startUpstream(), System.nanoTime()), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        return created.data().path("id").asText();
    }

    private String passedCredential(String token) throws Exception {
        String credentialId = credential(token);
        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(precheck.status()).as(precheck.body()).isEqualTo(200);
        String jobId = precheck.data().path("job_id").asText();
        detectionService.recordProbeResults(Long.valueOf(jobId), List.of(
                ProbeScoring.scoreTtft(List.of(200, 205, 210)),
                ProbeScoring.scoreThroughput(82.4),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 95.0, "tokenizer", 93.0,
                        "self_awareness", 90.0, "probability", 85.0, "context", 80.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA")), Map.of(), Map.of());
        return credentialId;
    }

    /** 造一张已通过检测、已提交（SUBMITTED）的报价单，返回 [quoteId, providerId]。 */
    private long[] submittedQuote(String token) throws Exception {
        String credentialId = passedCredential(token);
        HttpResult created = post("/quotes", """
                {
                  "name":"审核用报价","credential_id":"%s","currency":"USD",
                  "valid_from":"2026-10-01T00:00:00Z","valid_to":"2026-12-31T00:00:00Z"
                }
                """.formatted(credentialId), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String quoteId = created.data().path("quote_id").asText();

        HttpResult items = post("/quotes/" + quoteId + "/items", """
                {"items":[{"model_name":"gpt-4o"}]}
                """, token);
        assertThat(items.status()).as(items.body()).isEqualTo(200);
        String itemId = items.data().path("items").get(0).path("item_id").asText();

        HttpResult priced = put("/quotes/items/" + itemId, """
                {"input_price":1.2,"output_price":3.6}
                """, token);
        assertThat(priced.status()).as(priced.body()).isEqualTo(200);

        HttpResult submitted = post("/quotes/" + quoteId + "/submit", null, token);
        assertThat(submitted.status()).as(submitted.body()).isEqualTo(200);

        Long providerId = jdbc.queryForObject("select provider_id from aap_quote where id = ?::bigint",
                Long.class, quoteId);
        return new long[]{Long.parseLong(quoteId), providerId == null ? -1L : providerId};
    }

    // ------------------------------------------------------------------ 管理端前置

    /** 管理端 token（真源：T03 管理端登录用 admin 表 + JWT，测试内直插账号，与 UsageContractTest 一致）。 */
    private String adminToken(long accountId, String username, String role) {
        jdbc.update("delete from aap_admin_user where id = ?", accountId);
        jdbc.update("""
                insert into aap_admin_user (id, username, password_hash, display_name, role, status)
                values (?, ?, 'x', ?, ?, 'ACTIVE')
                """, accountId, username, role, role);
        var issued = jwtService.issueAccessToken(accountId, role, "ADMIN", null);
        AuthTokenEntity record = new AuthTokenEntity();
        record.setAccountId(accountId);
        record.setSubjectType("ADMIN");
        record.setJti(issued.jti());
        record.setExpireAt(OffsetDateTime.now(ZoneOffset.UTC).plusDays(1));
        authTokenMapper.insert(record);
        return issued.token();
    }

    private String bizOpsToken() {
        return adminToken(BIZ_OPS_ID, "bizops-review", "BIZ_OPERATOR");
    }

    private String techOpsToken() {
        return adminToken(TECH_OPS_ID, "techops-review", "TECH_OPS");
    }

    private String providerName(long providerId) {
        return jdbc.queryForObject("""
                select coalesce(short_name, company_name, provider_no) from aap_provider where id = ?
                """, String.class, providerId);
    }

    /** 待审池里唯一那条任务的 id。 */
    private String poolTaskId(String adminToken, long quoteId) {
        HttpResult list = get("/admin/reviews?status=PENDING", adminToken);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        for (var node : list.data().path("items")) {
            if (node.path("quote_id").asText().equals(String.valueOf(quoteId))) {
                return node.path("id").asText();
            }
        }
        throw new AssertionError("待审池里没有 quote_id=" + quoteId + " 的任务：" + list.body());
    }

    // ================================================================== ADM-R01

    @Test
    @DisplayName("ADM-R01 待审池：提交即入池（quote_no/provider_name/PENDING），分页契约与 status 过滤一致")
    void pendingPoolListsSubmittedQuote() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();

        HttpResult list = get("/admin/reviews?page=1&pageSize=20", adminToken);
        assertThat(list.status()).as(list.body()).isEqualTo(200);
        assertThat(list.data().path("total").asLong()).isEqualTo(1L);
        assertThat(list.data().path("items").size()).isEqualTo(1);
        SchemaAssert.assertPageMeta(json(list.data()));

        var task = list.data().path("items").get(0);
        SchemaAssert.assertModel("review-task", json(task));
        assertThat(task.path("status").asText()).isEqualTo("PENDING");
        assertThat(task.path("quote_id").asText()).isEqualTo(String.valueOf(quote[0]));
        assertThat(task.path("provider_id").asText()).isEqualTo(String.valueOf(quote[1]));
        assertThat(task.path("provider_name").asText()).isEqualTo(providerName(quote[1]));
        assertThat(task.path("quote_no").asText()).startsWith("Q");
        assertThat(task.path("created_at").asText()).isNotBlank();
        assertThat(task.path("claimed_by").isNull()).isTrue();

        // status 过滤：PENDING 命中、CLAIMED 为空（不得忽略筛选参数返回全量）
        assertThat(get("/admin/reviews?status=CLAIMED", adminToken).data().path("total").asLong()).isZero();
        assertThat(get("/admin/reviews?status=PENDING", adminToken).data().path("total").asLong()).isEqualTo(1L);

        // 分页：pageSize=1 只回 1 条但 total 仍是全量
        HttpResult paged = get("/admin/reviews?page=2&pageSize=1", adminToken);
        assertThat(paged.data().path("items").size()).isZero();
        assertThat(paged.data().path("total").asLong()).isEqualTo(1L);
    }

    @Test
    @DisplayName("ADM-R01 权限：未认证 401；供应商主体 403（管理端接口不得对供应商可见）")
    void pendingPoolDeniesNonAdmin() throws Exception {
        submittedQuote(token(PHONE));
        assertThat(get("/admin/reviews").status()).isEqualTo(401);
        assertThat(get("/admin/reviews", token(OTHER_PHONE)).status()).isEqualTo(403);
    }

    // ================================================================== ADM-R02

    @Test
    @DisplayName("ADM-R02 领取：PENDING→CLAIMED（记录领取人/时间），报价单同步进入 REVIEWING")
    void claimMovesTaskAndQuote() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);

        HttpResult claimed = post("/admin/reviews/" + taskId + "/claim", null, adminToken);
        assertThat(claimed.status()).as(claimed.body()).isEqualTo(200);
        SchemaAssert.assertModel("review-task", json(claimed.data()));
        assertThat(claimed.data().path("status").asText()).as(claimed.body()).isEqualTo("CLAIMED");
        assertThat(claimed.data().path("claimed_by").asText()).as(claimed.body()).isEqualTo(String.valueOf(BIZ_OPS_ID));
        assertThat(claimed.data().path("claimed_at").asText()).as(claimed.body()).isNotBlank();

        assertThat(jdbc.queryForObject("select status from aap_review_task where id = ?::bigint",
                String.class, taskId)).isEqualTo("CLAIMED");
        assertThat(jdbc.queryForObject("select status from aap_quote where id = ?::bigint",
                String.class, String.valueOf(quote[0]))).isEqualTo("REVIEWING");
        // 领取留痕（action=ASSIGN，PENDING→CLAIMED）
        assertThat(jdbc.queryForList("""
                select action from aap_review_record where task_id = ?::bigint order by created_at, id
                """, String.class, taskId)).containsExactly("ASSIGN");
    }

    @Test
    @DisplayName("ADM-R02 乐观锁 E1：已被他人领取的任务再领取 → 409 E-1601，且不覆盖原领取人")
    void claimIsOptimisticLocked() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String first = bizOpsToken();
        String taskId = poolTaskId(first, quote[0]);
        assertThat(post("/admin/reviews/" + taskId + "/claim", null, first).status()).isEqualTo(200);

        String second = adminToken(BIZ_OPS2_ID, "bizops-review-2", "BIZ_OPERATOR");
        HttpResult again = post("/admin/reviews/" + taskId + "/claim", null, second);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
        SchemaAssert.assertError(again.body());
        assertThat(jdbc.queryForObject("select claimed_by from aap_review_task where id = ?::bigint",
                Long.class, taskId)).isEqualTo(BIZ_OPS_ID);
    }

    @Test
    @DisplayName("ADM-R02 技术指标快照：领取冻结**最近一份**检测报告结论（总分/三态/置信度/A7 否决）")
    void claimSnapshotsLatestReport() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        // 两份报告：旧的一份（1 小时前，60 分）+ 新的一份（1 小时后，91.5 分）→ 必须取新的那份。
        // 只插一份会让「按检测时间取最新」这条口径失去检验力（曾把无 detected_at 的报告当成最新，测红）。
        jdbc.update("""
                insert into aap_report (id, report_no, job_id, provider_id, total_score, result, confidence,
                    veto_triggered, provider_name, status, detected_at)
                values (960000, 'RPTEST0000', 990000, ?, 60.00, 'FAIL', 'LOW', false, '审核快照供应商', 'GENERATED',
                        now() - interval '1 hour')
                """, quote[1]);
        jdbc.update("""
                insert into aap_report (id, report_no, job_id, provider_id, total_score, result, confidence,
                    veto_triggered, provider_name, status, detected_at)
                values (960001, 'RPTEST0001', 990001, ?, 91.50, 'PASS', 'HIGH', false, '审核快照供应商', 'GENERATED',
                        now() + interval '1 hour')
                """, quote[1]);
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);

        HttpResult claimed = post("/admin/reviews/" + taskId + "/claim", null, adminToken);
        assertThat(claimed.status()).as(claimed.body()).isEqualTo(200);
        var snapshot = claimed.data().path("tech_metrics_snapshot");
        assertThat(snapshot.path("total_score").asDouble()).as(claimed.body()).isEqualTo(91.5);
        assertThat(snapshot.path("result").asText()).as(claimed.body()).isEqualTo("PASS");
        assertThat(snapshot.path("confidence").asText()).as(claimed.body()).isEqualTo("HIGH");
        assertThat(snapshot.path("veto_triggered").asBoolean()).as(claimed.body()).isFalse();
    }

    // ================================================================== ADM-R03

    @Test
    @DisplayName("ADM-R03 通过：CLAIMED→APPROVED，A9 同事务生成合同（CREATED + quote.contract_id 回写）")
    void approveGeneratesContract() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);
        post("/admin/reviews/" + taskId + "/claim", null, adminToken);

        HttpResult approved = post("/admin/reviews/" + taskId + "/approve", """
                {"comment":"价格与检测均达标"}
                """, adminToken);
        assertThat(approved.status()).as(approved.body()).isEqualTo(200);
        SchemaAssert.assertModel("review-task", json(approved.data()));
        assertThat(approved.data().path("status").asText()).as(approved.body()).isEqualTo("APPROVED");
        assertThat(approved.data().path("review_comment").asText()).as(approved.body())
                .isEqualTo("价格与检测均达标");

        // 报价单：APPROVED + 审核人/时间/合同回写
        Map<String, Object> q = jdbc.queryForMap("""
                select status, reviewed_by, reviewed_at, contract_id, approved_quote_version
                  from aap_quote where id = ?::bigint
                """, String.valueOf(quote[0]));
        assertThat(q.get("status")).isEqualTo("APPROVED");
        assertThat(q.get("reviewed_by")).isEqualTo(BIZ_OPS_ID);
        assertThat(q.get("reviewed_at")).isNotNull();
        assertThat(q.get("contract_id")).isNotNull();

        // 合同：HT 单号、CREATED、归属正确
        Map<String, Object> c = jdbc.queryForMap("""
                select contract_no, quote_id, provider_id, status, currency from aap_contract
                 where id = ?
                """, q.get("contract_id"));
        assertThat((String) c.get("contract_no")).startsWith("HT");
        assertThat(c.get("quote_id")).isEqualTo(quote[0]);
        assertThat(c.get("provider_id")).isEqualTo(quote[1]);
        assertThat(c.get("status")).isEqualTo("CREATED");
        assertThat(c.get("currency")).isEqualTo("USD");

        // 审计与审核记录
        assertThat(jdbc.queryForList("""
                select action from aap_review_record where task_id = ?::bigint order by created_at, id
                """, String.class, taskId)).containsExactly("ASSIGN", "APPROVE");
        assertThat(jdbc.queryForList("select action from aap_audit_log where target_type = 'quote'",
                String.class)).contains("QUOTE_APPROVE");
    }

    @Test
    @DisplayName("ADM-R03 终态不可再流转：已通过的任务再通过 → 409 E-1601，且不重复生成合同")
    void approveTwiceIsRejected() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);
        post("/admin/reviews/" + taskId + "/claim", null, adminToken);
        assertThat(post("/admin/reviews/" + taskId + "/approve", null, adminToken).status()).isEqualTo(200);

        HttpResult again = post("/admin/reviews/" + taskId + "/approve", null, adminToken);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
        assertThat(jdbc.queryForObject("select count(*) from aap_contract", Long.class)).isEqualTo(1L);
    }

    // ================================================================== ADM-R04

    @Test
    @DisplayName("ADM-R04 驳回：reason_code 必填（缺 → E-1001、非法枚举 → E-1001），合法则 REJECTED + 原因落库")
    void rejectRequiresReasonCode() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);
        post("/admin/reviews/" + taskId + "/claim", null, adminToken);

        HttpResult missing = post("/admin/reviews/" + taskId + "/reject", """
                {"reason_text":"价格偏高"}
                """, adminToken);
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.code()).isEqualTo("E-1001");

        HttpResult badCode = post("/admin/reviews/" + taskId + "/reject", """
                {"reason_code":"NOT_A_CODE","reason_text":"乱填的枚举"}
                """, adminToken);
        assertThat(badCode.status()).isEqualTo(400);
        assertThat(badCode.code()).isEqualTo("E-1001");
        // 两次失败都不得改变状态
        assertThat(jdbc.queryForObject("select status from aap_review_task where id = ?::bigint",
                String.class, taskId)).isEqualTo("CLAIMED");

        HttpResult rejected = post("/admin/reviews/" + taskId + "/reject", """
                {"reason_code":"PRICE_TOO_HIGH","reason_text":"输入价高于基准价 18%"}
                """, adminToken);
        assertThat(rejected.status()).as(rejected.body()).isEqualTo(200);
        assertThat(rejected.data().path("status").asText()).as(rejected.body()).isEqualTo("REJECTED");
        assertThat(rejected.data().path("reject_reason_code").asText()).as(rejected.body())
                .isEqualTo("PRICE_TOO_HIGH");

        Map<String, Object> q = jdbc.queryForMap("""
                select status, reject_reason_code, reject_reason_text from aap_quote where id = ?::bigint
                """, String.valueOf(quote[0]));
        assertThat(q.get("status")).isEqualTo("REJECTED");
        assertThat(q.get("reject_reason_code")).isEqualTo("PRICE_TOO_HIGH");
        assertThat(q.get("reject_reason_text")).isEqualTo("输入价高于基准价 18%");
        assertThat(jdbc.queryForList("""
                select action from aap_review_record where task_id = ?::bigint order by created_at, id
                """, String.class, taskId)).containsExactly("ASSIGN", "REJECT");
    }

    @Test
    @DisplayName("ADM-R04 终态不可再流转：已驳回的任务再驳回 → 409 E-1601")
    void rejectTwiceIsRejected() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);
        post("/admin/reviews/" + taskId + "/claim", null, adminToken);
        post("/admin/reviews/" + taskId + "/reject", """
                {"reason_code":"TECH_RISK"}
                """, adminToken);

        HttpResult again = post("/admin/reviews/" + taskId + "/reject", """
                {"reason_code":"OTHER"}
                """, adminToken);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.code()).isEqualTo("E-1601");
    }

    @Test
    @DisplayName("重提复用同一任务：驳回后再次提交 → 待审池仍是同一条任务且回到 PENDING（不触发唯一索引冲突）")
    void resubmitReusesSameTask() throws Exception {
        String supplier = token(PHONE);
        long[] quote = submittedQuote(supplier);
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);
        post("/admin/reviews/" + taskId + "/claim", null, adminToken);
        post("/admin/reviews/" + taskId + "/reject", """
                {"reason_code":"PRICE_TOO_HIGH","reason_text":"再谈谈"}
                """, adminToken);

        HttpResult resubmitted = post("/quotes/" + quote[0] + "/submit", null, supplier);
        assertThat(resubmitted.status()).as(resubmitted.body()).isEqualTo(200);

        assertThat(jdbc.queryForObject("select count(*) from aap_review_task where quote_id = ?::bigint",
                Long.class, String.valueOf(quote[0]))).isEqualTo(1L);
        // 重提把版本号再推一档（2 → 3）：曾因同一实体连续两次 update 被乐观锁挡下而丢版本，
        // 表现为 uq_quote_version 冲突（500 E-2001）——这条断言把该缺陷钉住。
        assertThat(jdbc.queryForObject("select current_version from aap_quote where id = ?::bigint",
                Integer.class, String.valueOf(quote[0]))).isEqualTo(3);
        assertThat(poolTaskId(adminToken, quote[0])).isEqualTo(taskId);
        Map<String, Object> row = jdbc.queryForMap("""
                select status, claimed_by, reject_reason_code from aap_review_task where id = ?::bigint
                """, taskId);
        assertThat(row.get("status")).isEqualTo("PENDING");
        assertThat(row.get("claimed_by")).isNull();
        assertThat(row.get("reject_reason_code")).isNull();
    }

    // ================================================================== ADM-R05

    @Test
    @DisplayName("ADM-R05 审核记录：按 quoteId 过滤返回行动时间线（before/after 状态），无匹配则空数组")
    void recordsTimeline() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String adminToken = bizOpsToken();
        String taskId = poolTaskId(adminToken, quote[0]);
        post("/admin/reviews/" + taskId + "/claim", null, adminToken);
        post("/admin/reviews/" + taskId + "/approve", """
                {"comment":"通过"}
                """, adminToken);

        HttpResult records = get("/admin/reviews/records?quoteId=" + quote[0], adminToken);
        assertThat(records.status()).as(records.body()).isEqualTo(200);
        assertThat(records.data().path("items").size()).isEqualTo(2);
        var assign = records.data().path("items").get(0);
        var approve = records.data().path("items").get(1);
        SchemaAssert.assertModel("review-record", json(assign));
        assertThat(assign.path("action").asText()).isEqualTo("ASSIGN");
        assertThat(assign.path("before_status").asText()).isEqualTo("PENDING");
        assertThat(assign.path("after_status").asText()).isEqualTo("CLAIMED");
        assertThat(assign.path("operator_id").asText()).isEqualTo(String.valueOf(BIZ_OPS_ID));
        assertThat(assign.path("quote_id").asText()).isEqualTo(String.valueOf(quote[0]));
        assertThat(approve.path("action").asText()).isEqualTo("APPROVE");
        assertThat(approve.path("before_status").asText()).isEqualTo("CLAIMED");
        assertThat(approve.path("after_status").asText()).isEqualTo("APPROVED");
        assertThat(approve.path("comment").asText()).isEqualTo("通过");

        HttpResult none = get("/admin/reviews/records?quoteId=123456789", adminToken);
        assertThat(none.status()).isEqualTo(200);
        assertThat(none.data().path("items").size()).isZero();
    }

    @Test
    @DisplayName("ADM-R05 权限：技术运营可读（R01/R05），但领取/通过/驳回一律 403")
    void techOpsReadOnly() throws Exception {
        long[] quote = submittedQuote(token(PHONE));
        String techToken = techOpsToken();
        String taskId = poolTaskId(techToken, quote[0]);

        assertThat(get("/admin/reviews/records?quoteId=" + quote[0], techToken).status()).isEqualTo(200);
        assertThat(post("/admin/reviews/" + taskId + "/claim", null, techToken).status()).isEqualTo(403);
        assertThat(post("/admin/reviews/" + taskId + "/approve", null, techToken).status()).isEqualTo(403);
        assertThat(post("/admin/reviews/" + taskId + "/reject", """
                {"reason_code":"OTHER"}
                """, techToken).status()).isEqualTo(403);
        // 被拒的三次调用不得留任何状态痕迹
        assertThat(jdbc.queryForObject("select status from aap_review_task where id = ?::bigint",
                String.class, taskId)).isEqualTo("PENDING");
        assertThat(jdbc.queryForObject("select count(*) from aap_review_record", Long.class)).isZero();
    }
}
