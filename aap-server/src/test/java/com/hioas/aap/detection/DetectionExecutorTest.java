package com.hioas.aap.detection;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * 缺陷 1 · 检测执行器端到端：{@code QUEUED} 的检测任务必须被消费、必须回写结果。
 *
 * <p>缺陷 1 的实测证据（2026-09-23）：{@code aap_detection_job} 里 {@code status='QUEUED'} 且
 * {@code updated_at == created_at} —— 插入后再没被任何代码碰过（{@code recordProbeResults} 全仓零调用方），
 * 凭证卡在 {@code detection_status='RUNNING'}，再预检报 {@code E-1301}，永久无法重试，QUEUED 无限堆积。
 *
 * <p>本类走**真实链路**：凭证创建 → 预检（建 QUEUED 任务，正是缺陷现场）→ 执行器 {@code scan()}
 * → 断言任务被消费、结果落库、凭证状态解锁、报告产出。
 *
 * <p>方法名里的 DET-EXEC 是本次修复的标识；用例与 {@code DetectionContractTest} 不重叠：
 * 那里覆盖任务生命周期/权限，这里覆盖「谁来执行」。
 */
class DetectionExecutorTest extends ApiTestBase {

    /** 一个固定、结构完整的 chat/completions 响应（含 usage，D2 才算得出来）。 */
    private static final String CHAT_OK_BODY = """
            {"id":"chatcmpl-test","object":"chat.completion","created":1,
             "choices":[{"index":0,"message":{"role":"assistant","content":"1，2，3，4，5"},"finish_reason":"stop"}],
             "usage":{"prompt_tokens":20,"completion_tokens":40,"total_tokens":60}}
            """;

    @Autowired
    private DetectionExecutor executor;

    @Autowired
    private DetectionService detectionService;

    private HttpServer upstream;
    private final AtomicInteger chatCalls = new AtomicInteger();
    private final AtomicReference<String> lastChatBody = new AtomicReference<>();

    @AfterEach
    void stopUpstream() {
        if (upstream != null) {
            upstream.stop(0);
            upstream = null;
        }
    }

    /**
     * 上游桩：{@code /v1/models} 返回 200（供预检通过），{@code /v1/chat/completions} 按参数返回。
     *
     * @param chatStatus chat 端点状态码（500 用于「上游不可用」场景）
     */
    private String startUpstream(int chatStatus) throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/v1/models", exchange -> {
            byte[] body = "{\"data\":[{\"id\":\"gpt-4o\"}]}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        upstream.createContext("/v1/chat/completions", exchange -> {
            chatCalls.incrementAndGet();
            lastChatBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] body = chatStatus == 200
                    ? CHAT_OK_BODY.getBytes(StandardCharsets.UTF_8)
                    : "{\"error\":\"upstream unavailable\"}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(chatStatus, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        upstream.start();
        return "http://127.0.0.1:" + upstream.getAddress().getPort() + "/v1";
    }

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

    /** 建凭证 + 预检通过（预检本身会建一条 QUEUED 的检测任务——缺陷现场）。返回 jobId。 */
    private String credentialAndQueuedJob(String token, String baseUrl) {
        HttpResult created = post("/credentials", """
                {
                  "alias":"检测执行器凭证","base_url":"%s","api_key":"sk-probe-e2e-fixture-0001",
                  "primary_flag":true,
                  "model_list":[{"model_name":"gpt-4o","context_window":128000,"rpm":60}]
                }
                """.formatted(baseUrl), token);
        assertThat(created.status()).as(created.body()).isEqualTo(200);
        String credentialId = created.data().path("id").asText();

        HttpResult precheck = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(precheck.status()).as(precheck.body()).isEqualTo(200);
        return precheck.data().path("job_id").asText();
    }

    @Test
    @DisplayName("DET-EXEC-01 QUEUED 任务被执行器消费：置 RUNNING → 跑 3 轮探针 → 全项落库 + 报 COMPLETED + 凭证解锁")
    void executorConsumesQueuedJob() throws Exception {
        String token = token("13800000030");
        String baseUrl = startUpstream(200);
        String jobId = credentialAndQueuedJob(token, baseUrl);
        String credentialId = jdbc.queryForObject(
                "select credential_id from aap_detection_job where id = ?::bigint", String.class, jobId);

        // 缺陷现场：任务建好就停在 QUEUED，且 updated_at 与 created_at 完全相同（插入后再没被碰过）
        assertThat(jdbc.queryForObject("select status from aap_detection_job where id = ?::bigint",
                String.class, jobId)).isEqualTo("QUEUED");
        assertThat(jdbc.queryForObject(
                "select updated_at = created_at from aap_detection_job where id = ?::bigint",
                Boolean.class, jobId)).as("尚未被任何代码碰过").isTrue();

        executor.scan();

        // ① 任务被消费：状态流转 + 时间戳被触碰（缺陷 1 的直接反证）
        assertThat(jdbc.queryForObject("select status from aap_detection_job where id = ?::bigint",
                String.class, jobId)).isEqualTo("COMPLETED");
        assertThat(jdbc.queryForObject("select updated_at > created_at from aap_detection_job where id = ?::bigint",
                Boolean.class, jobId)).as("任务必须被真正更新过").isTrue();
        assertThat(jdbc.queryForObject("select finished_at is not null from aap_detection_job where id = ?::bigint",
                Boolean.class, jobId)).isTrue();
        assertThat(jdbc.queryForObject("select active_flag from aap_detection_job where id = ?::bigint",
                Boolean.class, jobId)).as("完成后不得再占用互斥位").isFalse();
        assertThat(jdbc.queryForObject("select progress_percent from aap_detection_job where id = ?::bigint",
                java.math.BigDecimal.class, jobId)).isEqualByComparingTo("100");

        // 结论：D4/D5（不压测配额）+ D6（上游无缓存字段）= 3 项不可测 ⇒ 按 R-25 走人工复核，不自动判通过
        assertThat(jdbc.queryForObject("select result from aap_detection_job where id = ?::bigint",
                String.class, jobId)).isEqualTo("MANUAL_REVIEW");
        assertThat(jdbc.queryForObject("select total_score from aap_detection_job where id = ?::bigint",
                java.math.BigDecimal.class, jobId).doubleValue()).as("测得项全满分 → 归一化后接近 100")
                .isGreaterThan(95.0);

        // ② 逐项结果落库：8 项齐全，且状态与「测得/未测得」一致
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_result where job_id = ?::bigint",
                Integer.class, jobId)).isEqualTo(8);
        for (String code : List.of("D1", "D2", "D3", "D7")) {
            assertThat(jdbc.queryForObject("select status from aap_detection_result "
                            + "where job_id = ?::bigint and probe_code = ?", String.class, jobId, code))
                    .as("%s 应为实测成功", code).isEqualTo("SUCCESS");
            assertThat(jdbc.queryForObject("select score from aap_detection_result "
                            + "where job_id = ?::bigint and probe_code = ?", java.math.BigDecimal.class, jobId, code))
                    .as("%s 必须真有分数", code).isNotNull();
        }
        for (String code : List.of("D4", "D5", "D6")) {
            assertThat(jdbc.queryForObject("select status from aap_detection_result "
                            + "where job_id = ?::bigint and probe_code = ?", String.class, jobId, code))
                    .as("%s 未实测 ⇒ 必须标 NOT_MEASURABLE，不得填示意分", code).isEqualTo("NOT_MEASURABLE");
            assertThat(jdbc.queryForObject("select score from aap_detection_result "
                            + "where job_id = ?::bigint and probe_code = ?", java.math.BigDecimal.class, jobId, code))
                    .as("%s 不可测项不得有分数", code).isNull();
        }
        // 每项都带原始指标、证据与四段式解释（PRD A2，不可测项也不例外）
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_result "
                + "where job_id = ?::bigint and metrics is not null and evidence is not null "
                + "and explanation is not null and length(explanation) > 60",
                Integer.class, jobId)).as("8 项都必须有指标+证据+四段解释").isEqualTo(8);

        // ③ 凭证状态解锁：不再是 RUNNING（RUNNING 会让再预检恒报 E-1301）
        assertThat(jdbc.queryForObject("select detection_status from aap_credential where id = ?::bigint",
                String.class, credentialId)).as("人工复核 ⇒ PENDING，且必须离开 RUNNING").isEqualTo("PENDING");

        // ④ 报告 1:1 产出（AC-18）；站内信**只在 PASS 时**发（AC-21，本次结果是人工复核）
        assertThat(jdbc.queryForObject("select count(*) from aap_report where job_id = ?::bigint",
                Integer.class, jobId)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "select count(*) from aap_notification where recipient_type = 'PROVIDER' and event_code = 'DETECTION_PASSED'",
                Integer.class)).as("非 PASS 不发通过通知").isZero();

        // ⑤ 探针真的发了 3 轮，且按 D3 规格带 temperature=0、用凭证里的模型
        assertThat(chatCalls.get()).isEqualTo(3);
        assertThat(lastChatBody.get()).contains("\"model\":\"gpt-4o\"").contains("\"temperature\":0");

        // ⑥ 解锁后可重新发起（AC-19 重测）：这条预检不再报 E-1301
        HttpResult again = post("/credentials/" + credentialId + "/precheck", null, token);
        assertThat(again.status()).as("凭证解锁后必须能重试：" + again.body()).isEqualTo(200);
    }

    @Test
    @DisplayName("DET-EXEC-02 上游不可用：仍必须回写（全项 FAILED）—— 任务不得留在 QUEUED/RUNNING 死区")
    void executorWritesBackWhenUpstreamFails() throws Exception {
        String token = token("13800000031");
        String baseUrl = startUpstream(500);
        String jobId = credentialAndQueuedJob(token, baseUrl);
        String credentialId = jdbc.queryForObject(
                "select credential_id from aap_detection_job where id = ?::bigint", String.class, jobId);

        executor.scan();

        assertThat(jdbc.queryForObject("select status from aap_detection_job where id = ?::bigint",
                String.class, jobId)).as("失败也必须收敛，不能永远 QUEUED").isEqualTo("COMPLETED");
        assertThat(jdbc.queryForObject("select result from aap_detection_job where id = ?::bigint",
                String.class, jobId)).isEqualTo("FAIL");
        assertThat(jdbc.queryForObject("select count(*) from aap_detection_result where job_id = ?::bigint "
                + "and status = 'FAILED'", Integer.class, jobId)).as("8 项全部标 FAILED").isEqualTo(8);
        assertThat(jdbc.queryForObject("select detection_status from aap_credential where id = ?::bigint",
                String.class, credentialId)).isEqualTo("FAIL");
        // AC-18：失败任务同样「有任务必有报告」，否则报告页会出现有结论查不到报告的空洞
        assertThat(jdbc.queryForObject("select count(*) from aap_report where job_id = ?::bigint",
                Integer.class, jobId)).isEqualTo(1);
        assertThat(jdbc.queryForObject(
                "select count(*) from aap_notification where recipient_type = 'PROVIDER' and event_code = 'DETECTION_PASSED'",
                Integer.class)).as("FAIL 不发通过通知").isZero();
        // 首轮即失败 ⇒ 不再浪费取样轮次
        assertThat(chatCalls.get()).isEqualTo(1);
    }

    @Test
    @DisplayName("DET-EXEC-03 回写链路（执行器的依赖）：全项可测且满分 ⇒ PASS 且发 DETECTION_PASSED 站内信")
    void passPathNotifies() throws Exception {
        String token = token("13800000032");
        String baseUrl = startUpstream(200);
        String jobId = credentialAndQueuedJob(token, baseUrl);

        // 与执行器调的是同一个入口；这里给「8 项全可测」的分数（配额项带申报值），
        // 证明 PASS 分支的站内信没被改动破坏，也说明 01/02 里断言「无通知」是因为结论不是 PASS。
        detectionService.recordProbeResults(Long.valueOf(jobId), List.of(
                ProbeScoring.scoreTtft(List.of(200, 200, 200)),
                ProbeScoring.scoreThroughput(80),
                ProbeScoring.scoreDeterminism(8, 8),
                ProbeScoring.scoreQuota("D4", 60.0, 60),
                ProbeScoring.scoreQuota("D5", 200000.0, 200000),
                ProbeScoring.scoreCache(true, true),
                ProbeScoring.scoreFingerprint(Map.of("behavior", 90.0, "tokenizer", 90.0,
                        "self_awareness", 90.0, "probability", 90.0, "context", 90.0)),
                ProbeScoring.scoreUpstreamOrigin("TLS issuer=TestCA")), Map.of(), Map.of());

        assertThat(jdbc.queryForObject("select result from aap_detection_job where id = ?::bigint",
                String.class, jobId)).isEqualTo("PASS");
        assertThat(jdbc.queryForObject(
                "select count(*) from aap_notification where recipient_type = 'PROVIDER' "
                        + "and event_code = 'DETECTION_PASSED' and category = 'DETECTION'",
                Integer.class)).as("AC-21 检测通过通知").isEqualTo(1);
    }
}
